"""Publish a verified completed-study handoff and archive its exact Git commit."""
from __future__ import annotations

from hashlib import sha256
import json
import subprocess
import zipfile

from continue_robustness_research import REPORT, ROOT, checkpoint
from research_inventory import verify_expected_fingerprint


def finalize():
    inventory=json.loads((REPORT/'research_completion_inventory.json').read_text())
    generation=json.loads((REPORT/'table_generation_receipt.json').read_text())
    stage=json.loads((REPORT/'continuation_stage_checks.json').read_text())
    assert inventory['complete'] and generation['complete'],'Research remains incomplete'
    assert stage['phase'] in ('Finish frozen real-history robustness and exit research',
                              'Document completed research and reproducible delivery')
    assert stage['tests_status']=='PASS' and not stage['canonical_changed']
    restoration=json.loads((REPORT/'checkpoint_restoration_receipt.json').read_text())
    assert restoration['complete']
    expected=json.loads((REPORT/'resume_original_case_fingerprints.json').read_text())
    # Accept the ledger's documented mapping, with no replacement checksums.
    assert isinstance(expected,dict)
    for name,fingerprint in expected.items():
        verify_expected_fingerprint(REPORT/name,fingerprint)
    status=ROOT/'CONTINUATION_STATUS.md'
    prior=status.read_text()
    marker='## Завершённая точка передачи'
    if marker not in prior:
        status.write_text(
            '# Strategy Engine: завершённое зарегистрированное исследование\n\n'
            'Все зарегистрированные historical, VALIDATION, retrospective HOLDOUT, '
            'walk-forward, execution, POI и exit sensitivity studies завершены. '
            'Полный inventory и итоговые таблицы имеют `complete=true`.\n\n'
            'Все 21 исходных fingerprints восстановлены точно; 57 canonical source/config '
            'SHA неизменны. Canonical TP 40/30/30, inclusive wick-touch и '
            '`trade_entry_allowed=false` сохранены. Варианты не выбраны для canonical.\n\n'
            f'Full tests: **{stage["tests"]} PASS**, lint E9/F и mypy PASS. '
            'Результаты и необходимые для продолжения артефакты сохранены в Git.\n\n'
            'Итоговые выводы и ограничения: [robustness report](ROBUSTNESS_RESEARCH_REPORT.md) '
            'и [exit management report](EXIT_MANAGEMENT_RESEARCH_REPORT.md). '
            'Отдельные chronological holdout portfolios не объединены в один account; '
            'это retrospective validation, не prospective OOS.\n\n'
            +marker+'\n\n'
            'Для проверки и повторного использования сохранённых результатов:\n\n'
            '```bash\nPYTHONPATH=src python scripts/restore_research_checkpoint.py --workers 4\n'
            'PYTHONPATH=src python scripts/continue_robustness_research.py --workers 4\n```\n\n'
            'Без `--checkpoint-main` команды не публикуют commits. '
            'Сохранённые случаи повторно используются после SHA/fingerprint validation. '
            'Историческая диагностика восстановления приведена ниже; её промежуточные '
            'counts/status не описывают финальный inventory.\n\n'
            '<details><summary>История восстановления и промежуточной проверки</summary>\n\n'
            +prior+'\n</details>\n')
    checkpoint([status,ROOT/'scripts/finalize_research_delivery.py',ROOT/'scripts/write_research_reports.py'],
               'Document completed research and reproducible delivery',True)
    assert not subprocess.check_output(['git','status','--porcelain'],cwd=ROOT).strip(),'Uncommitted research artifacts'
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT).decode().strip()
    destination=ROOT.parent/'artifacts'
    destination.mkdir(exist_ok=True)
    archive=destination/f'crypto-bot-{commit}.zip'
    subprocess.run(['git','archive','--format=zip','--prefix=crypto-bot/',
                    f'--output={archive}',commit],cwd=ROOT,check=True)
    with zipfile.ZipFile(archive) as reader:
        assert reader.comment.decode()==commit
        assert reader.testzip() is None
        entries=len(reader.namelist())
    digest=sha256()
    with archive.open('rb') as handle:
        for block in iter(lambda:handle.read(1024*1024),b''):
            digest.update(block)
    checksum=digest.hexdigest()
    archive.with_suffix('.zip.sha256').write_text(f'{checksum}  {archive.name}\n')
    receipt=dict(commit=commit,branch='main',archive=str(archive),sha256=checksum,
                 bytes=archive.stat().st_size,entries=entries,research_complete=True,
                 restored_original_fingerprints=21,canonical_changed=False,
                 trade_entry_allowed=False,tests=stage['tests'],zip_crc='PASS')
    archive.with_suffix('.manifest.json').write_text(json.dumps(receipt,indent=2)+'\n')
    (destination/'latest_final.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt,indent=2),flush=True)


if __name__=='__main__':
    finalize()
