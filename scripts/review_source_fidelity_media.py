"""Render all unique embedded original DOCX diagrams for visual review."""
from __future__ import annotations

import io
import json
import zipfile
from collections import defaultdict
from hashlib import sha256
from pathlib import Path

from PIL import Image, ImageDraw

REPO = Path(__file__).resolve().parents[1]
ROOT = REPO / 'data/reports/source_fidelity_2026_10_11'


def main():
    materials = REPO / 'data/source_materials/source_fidelity_2026_10_11/unique_docx'
    out = ROOT / 'source_visual_review'
    out.mkdir(exist_ok=True)
    raw_images, references = {}, defaultdict(list)
    for path in sorted(materials.glob('*.docx')):
        with zipfile.ZipFile(path) as archive:
            for name in archive.namelist():
                if name.startswith('word/media/'):
                    raw = archive.read(name)
                    key = sha256(raw).hexdigest()
                    raw_images[key] = raw
                    references[key].append({'docx': path.name, 'member': name})
    ocr_root = REPO / 'data/source_materials/cryptology_2026_10_09'
    ocr = json.loads((ocr_root / 'ocr_manifest.json').read_text())
    assert set(raw_images) == {r['sha256'] for r in ocr}
    sheets, items = [], list(raw_images)
    for begin in range(0, len(items), 18):
        sheet = Image.new('RGB', (1230, 1878), 'white')
        draw = ImageDraw.Draw(sheet)
        for index, key in enumerate(items[begin:begin + 18]):
            cell = Image.open(io.BytesIO(raw_images[key])).convert('RGB')
            cell.thumbnail((402, 284))
            x, y = (index % 3) * 410, (index // 3) * 313
            sheet.paste(cell, (x + (405 - cell.width) // 2, y + 20))
            draw.text((x + 3, y + 2), str(begin + index + 1) + ' ' + key[:14], fill='black')
        path = out / f'docx_media_{begin // 18 + 1:02}.jpg'
        sheet.save(path, quality=95)
        sheets.append(str(path.relative_to(REPO)))
    receipt = {'media_occurrences': sum(map(len, references.values())),
               'unique_media': len(items), 'all_122_have_preserved_OCR': True,
               'sheets': sheets, 'references': references}
    (out / 'media_review_manifest.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n')
    print('SOURCE_MEDIA_COMPLETE', receipt['media_occurrences'], len(items), len(sheets))


if __name__ == '__main__':
    main()
