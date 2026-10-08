"""Resume registered frozen studies; publish checkpoints only with an explicit flag."""
from __future__ import annotations

import argparse
from datetime import datetime
from hashlib import sha256
import json
from pathlib import Path
import re
import subprocess
import sys
from zoneinfo import ZoneInfo

from research_inventory import complete_study
from research_support import check_baseline
from research_variants import STRUCTURAL_VARIANTS
from summarize_robustness_research import MAPPINGS, record_inventory

ROOT=Path(__file__).resolve().parents[1]
REPORT=ROOT/'data/reports/robustness_research'
HELPERS=('scripts/research_inventory.py','scripts/research_structure_cache.py',
         'scripts/run_robustness_research.py','scripts/restore_research_checkpoint.py',
         'scripts/run_exit_research.py','scripts/run_research_execution_scenarios.py',
         'scripts/summarize_robustness_research.py','scripts/continue_robustness_research.py',
         'tests/test_research_windows.py','tests/test_research_variants.py',
         'tests/test_research_exit_management.py')


def run_script(name,*args):
    subprocess.run([sys.executable,str(ROOT/'scripts'/name),*map(str,args)],cwd=ROOT,check=True)


def checkpoint(paths,label,publish):
    lock=check_baseline(ROOT)
    record_inventory(REPORT,True)
    if not publish:
        return
    log=REPORT/'continuation_full_tests.log'
    with log.open('w') as handle:
        subprocess.run([sys.executable,'-m','unittest','discover','-s','tests','-v'],
                       cwd=ROOT,stdout=handle,stderr=subprocess.STDOUT,check=True)
    count=re.search(r'Ran (\d+) tests',log.read_text())
    assert count is not None and int(count[1])>0,'No executed tests'
    subprocess.run([sys.executable,'-m','ruff','check','src','scripts','tests','--select','E9,F'],cwd=ROOT,check=True)
    subprocess.run([sys.executable,'-m','mypy','--no-incremental','--python-executable',sys.executable,'src','scripts'],cwd=ROOT,check=True)
    stage=dict(timestamp=datetime.now(ZoneInfo('Asia/Yekaterinburg')).isoformat(),phase=label,
               tests=int(count[1]),tests_status='PASS',lint_status='PASS',mypy_status='PASS',
               protected_source_config_hashes=lock['code_hashes'],canonical_changed=False,
               research_helper_hashes={name:sha256((ROOT/name).read_bytes()).hexdigest() for name in HELPERS},
               all_checkpoint_restored=json.loads((REPORT/'checkpoint_restoration_receipt.json').read_text())['complete'],
               trade_entry_allowed=False)
    status=REPORT/'continuation_stage_checks.json'
    status.write_text(json.dumps(stage,indent=2)+'\n')
    names=[*map(str,paths),*HELPERS,str(log),str(status),str(REPORT/'research_completion_inventory.json')]
    subprocess.run(['git','add','--',*names],cwd=ROOT,check=True)
    run_script('check_research_publication.py')
    subprocess.run(['git','add','--',str(REPORT/'research_publication_scan.json')],cwd=ROOT,check=True)
    subprocess.run(['git','diff','--cached','--check'],cwd=ROOT,check=True)
    if subprocess.run(['git','diff','--cached','--quiet'],cwd=ROOT).returncode:
        subprocess.run(['git','commit','-m',label],cwd=ROOT,check=True)
    subprocess.run(['git','push','origin','HEAD:main'],cwd=ROOT,check=True)
    local=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT).decode().strip()
    remote=subprocess.check_output(['git','ls-remote','origin','refs/heads/main'],cwd=ROOT).decode().split()[0]
    assert local==remote,'Checkpoint main verification failed'
    print('PUBLISHED_CHECKPOINT',label,local,flush=True)


def continue_studies(workers,publish):
    run_script('restore_research_checkpoint.py','--workers',workers)
    checkpoint([REPORT/'canonical/binance_15_5',REPORT/'canonical/binance_60_5',
                REPORT/'structural_sensitivity',
                REPORT/'restoration_diagnostics',REPORT/'checkpoint_restoration_receipt.json',
                ROOT/'CONTINUATION_STATUS.md',*REPORT.glob('*.csv')],
               'Recover all 21 original replay fingerprints with historical audit schema',publish)
    for cohort,mappings in MAPPINGS.items():
        split=json.loads((REPORT/f'{cohort}_temporal_split.json').read_text())
        for htf,ltf in mappings:
            folder=REPORT/'canonical'/f'{cohort}_{htf}_{ltf}'
            if not complete_study(folder,split)[0]:
                run_script('run_robustness_research.py','--cohort',cohort,'--htf',htf,'--ltf',ltf,
                           '--workers',workers,'--resume-existing','--output',folder)
                assert complete_study(folder,split)[0],folder
                checkpoint([folder],f'Complete frozen canonical {cohort} {htf}/{ltf} windows and segments',publish)
    split=json.loads((REPORT/'binance_temporal_split.json').read_text())
    for variant in STRUCTURAL_VARIANTS:
        folder=REPORT/'structural_sensitivity'/variant
        if not complete_study(folder,split,['VALIDATION'])[0]:
            run_script('run_robustness_research.py','--cohort','binance','--htf',60,'--ltf',5,
                       '--windows','VALIDATION','--variant',variant,'--workers',workers,
                       '--resume-existing','--output',folder)
            assert complete_study(folder,split,['VALIDATION'])[0],folder
    checkpoint([REPORT/'structural_sensitivity'],'Complete registered POI OTE and midpoint sensitivity',publish)
    for cohort,mappings in MAPPINGS.items():
        for htf,ltf in mappings:
            mapping=f'{cohort}_{htf}_{ltf}'
            source=REPORT/'canonical'/mapping
            target=REPORT/'execution_sensitivity'/mapping
            expected={p.parent.name for p in source.glob('*/summary.json') if json.loads(p.read_text())['window']['name']!='REFERENCE'}
            required={(name,case) for name in ('BASE_VERIFY','COST_150','COST_200','RISK_021','RISK_025','REENTRY_SCORE_80') for case in expected}
            actual={(r['scenario'],f"{r['window']}_SEGMENT_{r['segment']:02}") for r in json.loads((target/'results.json').read_text())} if (target/'results.json').exists() else set()
            if actual!=required:
                run_script('run_research_execution_scenarios.py','--source',source,'--output',target,'--resume-existing')
                checkpoint([target],f'Complete frozen cost risk and reentry sensitivity {mapping}',publish)
            run_script('run_exit_research.py','--source',source,'--output',REPORT/'exit_management'/mapping,
                       '--role','EXTERNAL','--resume-existing')
            checkpoint([REPORT/'exit_management'/mapping],f'Complete paired exit allocation and BE sensitivity {mapping}',publish)
    # Preserved development and reserve studies already exist; verify and add
    # reusable byte manifests without recomputing their simulation outcomes.
    for results in sorted((REPORT/'exit_management').glob('development_*/*/results.json')):
        receipt=json.loads(results.read_text())[0]
        run_script('run_exit_research.py','--source',ROOT/receipt['source'],'--output',results.parent.parent,
                   '--role','DEVELOPMENT','--resume-existing')
    run_script('run_exit_research.py','--source',REPORT/'exit_reserve/canonical_btc_2019',
               '--output',REPORT/'exit_management/exit_untouched_btc_2019',
               '--role','EXIT_UNTOUCHED_RESERVE','--resume-existing')
    run_script('audit_external_execution.py')
    run_script('summarize_robustness_research.py')
    run_script('write_research_reports.py')
    checkpoint([REPORT,ROOT/'ROBUSTNESS_RESEARCH_REPORT.md',ROOT/'EXIT_MANAGEMENT_RESEARCH_REPORT.md',
                ROOT/'CONTINUATION_STATUS.md'],'Finish frozen real-history robustness and exit research',publish)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workers',type=int,default=4)
    parser.add_argument('--checkpoint-main',action='store_true',help='Run full checks, commit each stable phase and push HEAD to main. Requires user authorization.')
    args=parser.parse_args()
    if args.workers<1:
        parser.error('workers must be positive')
    continue_studies(args.workers,args.checkpoint_main)
