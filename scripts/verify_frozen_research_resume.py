"""Verify completed research against its original runtime without rewinding main.

The baseline hash guard is never weakened. Frozen source is reconstructed from
Git into an ignored temporary runtime, while reports are copied and history is
read through a symlink. Only the new validation receipt/log is published.
"""
from __future__ import annotations

import argparse
from hashlib import sha1, sha256
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory


def digest(path):
    value = sha256()
    with path.open('rb') as reader:
        for block in iter(lambda: reader.read(1024 * 1024), b''):
            value.update(block)
    return value.hexdigest()


def protected_bytes(repo, lock):
    commit = lock['baseline_commit']
    subprocess.run(['git', 'rev-parse', '--verify', commit + '^{commit}'],
                   cwd=repo, check=True, stdout=subprocess.DEVNULL)
    result = {}
    for name, expected in lock['code_hashes'].items():
        path = Path(name)
        if path.is_absolute() or '..' in path.parts:
            raise ValueError('Unsafe baseline path: ' + name)
        blob = subprocess.check_output(['git', 'show', f'{commit}:{name}'], cwd=repo)
        if sha256(blob).hexdigest() != expected:
            raise ValueError('Git baseline does not match registered hash: ' + name)
        result[name] = blob
    return result


def manifest(repo, output):
    return {p.relative_to(repo).as_posix(): digest(p)
            for directory in (repo / 'src', repo / 'scripts', repo / 'config',
                              repo / 'data/history', repo / 'data/reports')
            for p in directory.rglob('*') if p.is_file()
            and '__pycache__' not in p.parts and not p.is_relative_to(output)}


def verify_saved_artifacts(report):
    """Verify every saved byte manifest, including completed execution variants."""
    cases = 0
    files = 0
    for path in sorted(report.rglob('artifact_hashes.json')):
        hashes = json.loads(path.read_text())
        for name, expected in hashes.items():
            relative = Path(name)
            if relative.is_absolute() or '..' in relative.parts:
                raise ValueError('Unsafe artifact path: ' + name)
            if digest(path.parent / name) != expected:
                raise ValueError('Saved artifact hash mismatch: ' + str(path.parent / name))
            files += 1
        fingerprint = sha256(json.dumps(hashes, sort_keys=True, allow_nan=False).encode()).hexdigest()
        if (path.parent / 'fingerprint.sha256').read_text().strip() != fingerprint:
            raise ValueError('Saved artifact fingerprint mismatch: ' + str(path.parent))
        cases += 1
    return dict(verified_artifact_manifests=cases, verified_artifact_files=files)


def verify_git_artifacts(repo):
    """Use published Git blobs as independent receipts for legacy hashless cases."""
    entries = subprocess.check_output([
        'git', 'ls-tree', '-rz', 'HEAD', '--', 'data/history', 'data/reports'], cwd=repo)
    count = 0
    for entry in entries.split(b'\0'):
        if not entry:
            continue
        metadata, name = entry.split(b'\t', 1)
        mode, kind, expected = metadata.split()
        if kind != b'blob' or mode not in (b'100644', b'100755'):
            raise ValueError('Unsupported historical Git object: ' + os.fsdecode(name))
        path = repo / os.fsdecode(name)
        value = sha1(b'blob ' + str(path.stat().st_size).encode() + b'\0')
        with path.open('rb') as reader:
            for block in iter(lambda: reader.read(1024 * 1024), b''):
                value.update(block)
        if value.hexdigest().encode() != expected:
            raise ValueError('Historical file differs from saved Git blob: ' + str(path))
        count += 1
    return dict(verified_historical_git_blobs=count)


def verify_execution_sources(report):
    checked = 0
    for mapping in sorted((report / 'execution_sensitivity').iterdir()):
        for path in sorted(mapping.glob('*/*/summary.json')):
            saved = json.loads(path.read_text())
            source = report / 'canonical' / mapping.name / path.parent.name
            original = json.loads((source / 'summary.json').read_text())
            if saved['source_signal_sha256'] != digest(source / 'signals.jsonl.gz'):
                raise ValueError('Execution source signal changed: ' + str(path))
            if saved['source_input_hashes'] != original['input_hashes']:
                raise ValueError('Execution source inputs changed: ' + str(path))
            for name in ('cohort', 'htf', 'ltf', 'window', 'segment', 'start', 'end', 'baseline_commit'):
                if saved[name] != original[name]:
                    raise ValueError('Execution source context mismatch: ' + str(path) + ':' + name)
            if saved['trade_entry_allowed']:
                raise ValueError('Unsafe execution receipt: ' + str(path))
            checked += 1
    return dict(verified_execution_source_contexts=checked)


def verify(repo, output, workers):
    repo = repo.resolve()
    output = output.resolve()
    if output.exists():
        raise ValueError('Use a fresh validation output directory')
    report = repo / 'data/reports/robustness_research'
    lock = json.loads((report / 'baseline_lock.json').read_text())
    frozen = protected_bytes(repo, lock)
    artifacts = verify_saved_artifacts(report)
    artifacts.update(verify_git_artifacts(repo))
    artifacts.update(verify_execution_sources(report))
    main_differences = [name for name, blob in frozen.items()
                        if (repo / name).read_bytes() != blob]
    before = manifest(repo, output)
    output.mkdir(parents=True)
    cache = repo / '.research_cache'
    cache.mkdir(exist_ok=True)
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=repo).decode().strip()
    with TemporaryDirectory(prefix='resume-validation-', dir=cache) as directory:
        runtime = Path(directory)
        for name in ('src', 'scripts', 'config'):
            shutil.copytree(repo / name, runtime / name,
                            ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        for path in repo.glob('*.md'):
            shutil.copy2(path, runtime / path.name)
        for name, blob in frozen.items():
            path = runtime / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(blob)
        data = runtime / 'data'
        data.mkdir()
        (data / 'history').symlink_to(repo / 'data/history', target_is_directory=True)
        (data / 'reports').mkdir()
        for path in (repo / 'data/reports').iterdir():
            if path.name == 'robustness_research':
                shutil.copytree(path, data / 'reports' / path.name)
            elif path.is_dir() and path.resolve() != output:
                (data / 'reports' / path.name).symlink_to(path, target_is_directory=True)
        environment = dict(os.environ, PYTHONPATH=str(runtime / 'src'),
                           PYTHONDONTWRITEBYTECODE='1')
        command = [sys.executable, str(runtime / 'scripts/continue_robustness_research.py'),
                   '--workers', str(workers)]
        with (output / 'frozen_resume.log').open('w') as log:
            completed = subprocess.run(command, cwd=runtime, env=environment,
                                       stdout=log, stderr=subprocess.STDOUT)
        copied = data / 'reports/robustness_research'
        inventory = json.loads((copied / 'research_completion_inventory.json').read_text())
        after = manifest(repo, output)
        changed_originals = [name for name, value in before.items() if after.get(name) != value]
        receipt = dict(main_commit=head, baseline_commit=lock['baseline_commit'],
                       protected_source_config_files=len(frozen),
                       current_main_baseline_differences=main_differences,
                       historical_runtime_hash_guard='PASS',
                       continuation_exit_code=completed.returncode,
                       complete=inventory['complete'] and completed.returncode == 0 and not changed_originals,
                       missing=inventory['missing'],
                       studies=len(inventory['studies']),
                       canonical_changed=False, trade_entry_allowed=False,
                       original_files_unchanged=not changed_originals,
                       changed_original_paths=changed_originals,
                       added_paths_during_validation=sorted(after.keys() - before.keys()),
                       **artifacts)
        (output / 'resume_validation.json').write_text(json.dumps(receipt, indent=2) + '\n')
        if not receipt['original_files_unchanged']:
            raise ValueError('Original source/history/reports changed during validation')
        if completed.returncode:
            raise subprocess.CalledProcessError(completed.returncode, command)
        if not receipt['complete']:
            raise ValueError('Registered studies remain incomplete')
    print(json.dumps(receipt, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--workers', type=int, default=4)
    args = parser.parse_args()
    if args.workers < 1:
        parser.error('workers must be positive')
    verify(Path(__file__).resolve().parents[1], args.output, args.workers)
