"""Reproducible, non-executing DOCX extraction; Windows links are inventory only."""
from __future__ import annotations

import argparse
from hashlib import sha256
import io
import json
from pathlib import Path
import xml.etree.ElementTree as ET
import zipfile

W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
MC = '{http://schemas.openxmlformats.org/markup-compatibility/2006}'


def extract(archive: Path, output: Path) -> dict:
    output.mkdir(parents=True, exist_ok=False)
    manifest: dict = {'archive_sha256': sha256(archive.read_bytes()).hexdigest(),
                      'entries': [], 'materials': []}
    with zipfile.ZipFile(archive) as bundle:
        if bundle.testzip() is not None:
            raise ValueError('ZIP CRC failure')
        for index, entry in enumerate(bundle.infolist()):
            name = entry.filename if entry.flag_bits & 0x800 else entry.filename.encode('cp437').decode('cp866')
            if entry.is_dir():
                continue
            payload = bundle.read(entry)
            kind = 'DOCX' if name.lower().endswith('.docx') else 'SHORTCUT' if name.lower().endswith('.lnk') else 'OTHER'
            manifest['entries'].append({'id': index, 'name': name, 'kind': kind,
                                        'bytes': len(payload), 'sha256': sha256(payload).hexdigest()})
            if kind != 'DOCX':
                continue
            folder = output / f'{index:02d}'
            folder.mkdir()
            (folder / 'original.docx').write_bytes(payload)
            texts = []
            images = []
            paragraph = 0
            with zipfile.ZipFile(io.BytesIO(payload)) as doc:
                for part in doc.namelist():
                    if part.startswith('word/media/'):
                        blob = doc.read(part)
                        target = folder / Path(part).name
                        target.write_bytes(blob)
                        images.append({'path': target.relative_to(output).as_posix(), 'sha256': sha256(blob).hexdigest()})
                    if not part.startswith('word/') or not part.endswith('.xml'):
                        continue
                    tree = ET.fromstring(doc.read(part))
                    for alternate in tree.iter(MC + 'AlternateContent'):
                        # Choice and fallback contain the same text/diagram. Keep the choice.
                        for child in list(alternate)[1:]:
                            alternate.remove(child)
                    parents = {child: parent for parent in tree.iter() for child in parent}
                    seen = set()
                    lines = []
                    part_paragraph = 0
                    for p in tree.iter(W + 'p'):
                        runs = []
                        for t in p.iter(W + 't'):
                            ancestor = parents.get(t)
                            while ancestor is not None and ancestor.tag != W + 'p':
                                ancestor = parents.get(ancestor)
                            if ancestor is p:
                                runs.append(t.text or '')
                        value = ''.join(runs).strip()
                        if not value or value in seen:
                            continue
                        seen.add(value)
                        paragraph += 1
                        part_paragraph += 1
                        lines.append(f'P{part_paragraph:04d} {value}')
                    if lines:
                        texts.append('PART ' + part + '\n' + '\n'.join(lines))
            target = output / f'{index:02d}.clean.txt'
            target.write_text('\n'.join(texts) + '\n', encoding='utf-8')
            manifest['materials'].append({'id': index, 'name': name, 'paragraphs': paragraph,
                                          'text': target.name, 'text_sha256': sha256(target.read_bytes()).hexdigest(),
                                          'images': images})
    (output / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    result = extract(args.archive, args.output)
    print(json.dumps({'documents': len(result['materials']), 'entries': len(result['entries'])}))
