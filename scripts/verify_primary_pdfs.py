"""Read-only verification of original PDF payloads and complete text extraction."""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import subprocess


def verify(root: Path) -> dict:
    manifest = json.loads((root / 'manifest.json').read_text())
    pages = 0
    for row in manifest:
        name = row['source']
        pdf = root / f'{name}.pdf'
        payload = pdf.read_bytes()
        if not payload.startswith(b'%PDF-') or sha256(payload).hexdigest() != row['sha256']:
            raise ValueError(f'original PDF hash/header differs: {name}')
        raw = subprocess.check_output(['pdftotext', '-layout', str(pdf), '-']).decode()
        extracted = raw.split('\f')
        if not extracted[-1].strip():
            extracted = extracted[:-1]
        text = '\n'.join(f'\n===== {name} PAGE {i+1} =====\n{x}' for i, x in enumerate(extracted))
        if len(extracted) != row['pages'] or text != (root / f'{name}.txt').read_text():
            raise ValueError(f'incomplete/changed page extraction: {name}')
        if sha256(text.encode()).hexdigest() != row['text_sha256']:
            raise ValueError('text checksum differs')
        info = subprocess.check_output(['pdfinfo', str(pdf)]).decode()
        actual = int(next(line.split(':')[1] for line in info.splitlines() if line.startswith('Pages:')))
        if actual != len(extracted):
            raise ValueError('PDF page count differs from complete text')
        pages += actual
    return {'documents': len(manifest), 'all_pages': pages, 'original_pdf_and_full_text': 'VERIFIED',
            'trade_entry_allowed': False}


if __name__ == '__main__':
    print(json.dumps(verify(Path(__file__).resolve().parents[1] / 'data/source_materials/primary_pdf_2026_10_09'), indent=2))
