"""Read-only TECHNICAL_NORMALIZATION of retained archive and DOCX provenance.

This verifies bytes and locators, not the semantic truth of visual annotations.
The retained extraction archive and the separate original-freeze archive have
*different* identities; only the five audited DOCX member identities coincide.
"""

from __future__ import annotations

import io
import json
import posixpath
import re
import zipfile
from hashlib import sha256
from pathlib import Path
from xml.etree import ElementTree as ET

ARCHIVE_PATH = "data/source_materials/cryptology_2026_10_09/cryptology.zip"
# Independent pins: retained blob introduced by this commit, not manifest claims.
ARCHIVE_COMMIT = "649687364dd75c165e5cd55077d18e0eadfd1297"
ARCHIVE_GIT_BLOB = "dd942fa66ef047539f65c488d715413b3abdf9f1"
ARCHIVE_SHA256 = "33cee26232d90fe26840bb4fced2e75551a5368d59359ffecc4b72d92c3870b9"
EXTRACTION_MANIFEST_SHA256 = (
    "652e5e83d793be3f567c9007241357d593d7df49aebdc684968738586b8f7136"
)
SOURCE_FREEZE_MANIFEST_SHA256 = (
    "2ab9fa44808503bbfb93cf0abd28e2d5c3de1cf825d0c7666824c1ff6128a123"
)
ORIGINAL_FREEZE_ARCHIVE_SHA256 = (
    "2b9de082079d8e85eac13444626289b6a37b7733b668ff773e1598909bd873b8"
)
# source ID, frozen ID, extraction material ID, exact unique ZIP name, byte pin.
DOCX_PINS = (
    (
        "Methodichka",
        "SRC_METHOD_001",
        19,
        "Криптология/Методичка.docx",
        "032a314046cc5dba220f698da567387e9f0dd30b35e4ff1add6328ea41e4e9d1",
    ),
    (
        "SW6",
        "SRC_SW6_001",
        14,
        "Криптология/Smart money/[SW.BAND]6. Ликвидность.docx",
        "8587a15f68f4214c27a7bcd66ae85058571ed95369bc96f32d41bf3ef4a35178",
    ),
    (
        "SW8",
        "SRC_SW8_001",
        16,
        "Криптология/Smart money/[SW.BAND]8. Торговые инструменты (Base).docx",
        "88d40f60f201de5ffe7da6591b59c6fd88a1fd7f9c64c281a2f099d84f52ac23",
    ),
    (
        "SW10",
        "SRC_SW10_001",
        6,
        "Криптология/Smart money/[SW.BAND]10. Боковое движение.docx",
        "628cb1caa97138bc5470687e3743127cd147ac20c5cb39144345764be537e631",
    ),
    (
        "DemandSupply",
        "SRC_DS_001",
        18,
        "Криптология/Зоны_спроса_и_предложения_Demand_and_Supply.docx",
        "824a8a97902d84f85099aa10db6c13c8c008c6f818b188453af8ede6ccdbb020",
    ),
)
_W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
_R = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
_A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
_V = "{urn:schemas-microsoft-com:vml}"
_MC = "{http://schemas.openxmlformats.org/markup-compatibility/2006}"
_REL = "{http://schemas.openxmlformats.org/package/2006/relationships}"


def _read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _normal(text: str) -> str:
    return " ".join(text.split())


def _unique(rows: list, key: str, label: str) -> dict:
    result = {row[key]: row for row in rows}
    if len(result) != len(rows):
        raise ValueError("duplicate " + label)
    return result


def _member(archive: zipfile.ZipFile, name: str) -> bytes:
    matches = [info for info in archive.infolist() if info.filename == name]
    if len(matches) != 1:
        raise ValueError("missing or duplicate exact ZIP member: " + name)
    return archive.read(matches[0])


def _clean_paragraphs(path: Path) -> dict[str, str]:
    result = {}
    active = False
    current = None
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("PART "):
            active = line == "PART word/document.xml"
            current = None
        elif active:
            match = re.match(r"^(P\d{4})\s+(.*)", line)
            if match:
                current = match[1]
                if current in result:
                    raise ValueError("duplicate clean paragraph ID")
                result[current] = match[2]
            elif current:
                result[current] += " " + line
    return {key: _normal(text) for key, text in result.items()}


def _paragraph_mapping(paragraphs: list, clean: dict) -> tuple[list, list]:
    """Both indices are 1-based; repeated raw101 maps to clean P0095.

    The only removed raw paragraph is explicitly identified, not inferred by an
    arbitrary similarity alignment. Raw102 onwards maps to clean index raw-1.
    """
    texts = [
        _normal("".join(node.text or "" for node in p.iter(_W + "t")))
        for p in paragraphs
    ]
    if len(clean) != 171 or list(clean) != [f"P{i:04d}" for i in range(1, 172)]:
        raise ValueError("Methodichka clean paragraph identity/count mismatch")
    result = []
    for xml_index, text in enumerate(texts, 1):
        if not text:
            continue
        raw_index = len(result) + 1
        clean_index = 95 if raw_index == 101 else raw_index - (raw_index > 101)
        pid = f"P{clean_index:04d}"
        if text != clean.get(pid):
            raise ValueError("raw DOCX to clean paragraph mapping mismatch")
        result.append(
            {
                "raw_nonempty_index": raw_index,
                "xml_paragraph_index": xml_index,
                "clean_paragraph_id": pid,
                "text": text,
                "duplicate_of_raw_nonempty_index": 95 if raw_index == 101 else None,
            }
        )
    if len(result) != 172 or result[100]["text"] != result[94]["text"]:
        raise ValueError("Methodichka raw172/clean171 duplicate mapping mismatch")
    return result, texts


def _audit_methodichka(docx: bytes, clean: dict, visual: dict, material: dict) -> dict:
    """Reconstruct actual XML relationships, media and paragraph placement."""
    with zipfile.ZipFile(io.BytesIO(docx)) as document:
        names = document.namelist()
        if len(names) != len(set(names)):
            raise ValueError("duplicate internal DOCX ZIP member")
        xml = _member(document, "word/document.xml")
        rels_xml = _member(document, "word/_rels/document.xml.rels")
        tree = ET.fromstring(xml)
        paragraphs = list(tree.iter(_W + "p"))
        mapping, texts = _paragraph_mapping(paragraphs, clean)
        rels = _unique(
            [
                dict(node.attrib)
                for node in ET.fromstring(rels_xml).findall(_REL + "Relationship")
            ],
            "Id",
            "DOCX relationship ID",
        )
        images = _unique(material["images"], "path", "extraction image key")
        media = {name for name in names if name.startswith("word/media/")}
        if media != {"word/media/" + key.split("/", 1)[1] for key in images}:
            raise ValueError("raw DOCX/extraction media coverage mismatch")
        actual_assets = {}
        for name in sorted(media):
            value = _member(document, name)
            key = "19/" + name.removeprefix("word/media/")
            digest = sha256(value).hexdigest()
            if images[key]["sha256"] != digest:
                raise ValueError("actual DOCX media hash mismatch")
            actual_assets[name] = (digest, len(value))
        by_xml_index = {row["xml_paragraph_index"]: row for row in mapping}
        actual_refs = []
        for xml_index, paragraph in enumerate(paragraphs, 1):
            before = [row for row in mapping if row["xml_paragraph_index"] <= xml_index]
            after = [row for row in mapping if row["xml_paragraph_index"] > xml_index]
            preceding = before[-1] if before else None
            following = after[0] if after else None

            def visit(
                node,
                branch="PRIMARY_INLINE",
                xml_index=xml_index,
                before=before,
                preceding=preceding,
                following=following,
            ):
                if node.tag == _MC + "Choice":
                    branch = "PRIMARY_CHOICE"
                elif node.tag == _MC + "Fallback":
                    branch = "FALLBACK_DUPLICATE"
                if node.tag in {_A + "blip", _V + "imagedata"}:
                    rid = (
                        node.get(_R + "embed")
                        if node.tag == _A + "blip"
                        else node.get(_R + "id")
                    )
                    relation = rels.get(rid)
                    if relation is None or relation.get("TargetMode") == "External":
                        raise ValueError("DOCX image has missing/external relationship")
                    target = relation["Target"]
                    asset = posixpath.normpath(posixpath.join("word", target))
                    if (
                        asset not in actual_assets
                        or target != asset.removeprefix("word/")
                        or not relation.get("Type", "").endswith("/image")
                    ):
                        raise ValueError("DOCX image relationship target mismatch")
                    digest, size = actual_assets[asset]
                    actual_refs.append(
                        {
                            "drawing_order": len(actual_refs) + 1,
                            "relationship_id": rid,
                            "relationship_target": target,
                            "image_asset_manifest_key": "19/"
                            + asset.removeprefix("word/media/"),
                            "sha256": digest,
                            "bytes": size,
                            "xml_element": "blip"
                            if node.tag == _A + "blip"
                            else "imagedata",
                            "xml_paragraph_index": xml_index,
                            "rendering_branch": branch,
                            "paragraph_text": texts[xml_index - 1],
                            "raw_nonempty_paragraphs_before_or_containing": len(before),
                            "paragraph_location_relation": "WITHIN_TEXT_PARAGRAPH"
                            if xml_index in by_xml_index
                            else "BETWEEN_PRECEDING_AND_NEXT_TEXT_PARAGRAPHS",
                            "preceding_or_containing_clean_paragraph": preceding[
                                "clean_paragraph_id"
                            ]
                            if preceding
                            else None,
                            "preceding_or_containing_clean_text": preceding["text"]
                            if preceding
                            else None,
                            "next_clean_paragraph": following["clean_paragraph_id"]
                            if following
                            else None,
                            "next_clean_text": following["text"] if following else None,
                        }
                    )
                for child in node:
                    visit(child, branch)

            visit(paragraph)
        inventory = visual["document_image_reference_inventory"]
        if len(inventory) != 41 or len(actual_refs) != 41:
            raise ValueError("actual DOCX image reference coverage mismatch")
        for expected, actual in zip(inventory, actual_refs, strict=True):
            if any(expected.get(key) != value for key, value in actual.items()):
                raise ValueError("actual DOCX image relationship/location mismatch")
        if {r["image_asset_manifest_key"] for r in actual_refs} != set(images):
            raise ValueError("actual DOCX images are not completely referenced")
        figures = visual["figures"]
        if len(figures) != 31 or len({f["sha256"] for f in figures}) != 31:
            raise ValueError("distinct visual figure identity mismatch")
        if {f["sha256"] for f in figures} != {a[0] for a in actual_assets.values()}:
            raise ValueError("distinct visual figure coverage mismatch")
        for figure in figures:
            asset = figure["source_asset"]
            if (
                asset not in actual_assets
                or actual_assets[asset][0] != figure["sha256"]
            ):
                raise ValueError("visual figure actual asset mismatch")
            if figure["image_manifest_key"] != "19/" + asset.removeprefix(
                "word/media/"
            ):
                raise ValueError("visual figure manifest asset mismatch")
            refs = [r for r in actual_refs if r["sha256"] == figure["sha256"]]
            references = [
                {
                    "branch": r["rendering_branch"],
                    "relationship_id": r["relationship_id"],
                    "target": r["relationship_target"],
                }
                for r in refs
            ]
            if figure["source_relationship_references"] != references:
                raise ValueError("visual figure actual relationship mismatch")
            location = {
                key: refs[0][key]
                for key in (
                    "xml_paragraph_index",
                    "paragraph_location_relation",
                    "preceding_or_containing_clean_paragraph",
                    "next_clean_paragraph",
                )
            }
            if figure["source_location"] != location:
                raise ValueError("visual figure actual paragraph location mismatch")
        return {
            "raw_paragraph_mapping": mapping,
            "clean_paragraphs": clean,
            "raw_nonempty_paragraph_count": len(mapping),
            "clean_paragraph_count": len(clean),
            "xml_paragraph_count": len(paragraphs),
            "document_xml_sha256": sha256(xml).hexdigest(),
            "document_rels_sha256": sha256(rels_xml).hexdigest(),
            "methodichka_media_assets": len(actual_assets),
            "methodichka_distinct_figures": len(figures),
            "methodichka_image_references": len(actual_refs),
        }


def audit_archive_provenance(repository: Path, ledger: Path) -> dict:
    """Return verified byte/locator receipts; raise ValueError on inconsistency.

    raw_paragraph_mapping includes all172 raw nonempty paragraphs with 1-based
    raw and XML indices. Only raw101 is a repeated P0095; raw102 maps to P0101.
    This function performs no extraction writes and no SOURCE interpretation.
    """
    repository = repository.resolve()
    archive_bytes = (repository / ARCHIVE_PATH).read_bytes()
    if sha256(archive_bytes).hexdigest() != ARCHIVE_SHA256:
        raise ValueError("retained archive bytes differ from independent commit pin")
    extraction_path = (
        repository / "data/source_materials/cryptology_2026_10_09/manifest.json"
    )
    frozen_path = repository / "docs/source_freeze_v1/source_manifest.json"
    for path, digest in (
        (extraction_path, EXTRACTION_MANIFEST_SHA256),
        (frozen_path, SOURCE_FREEZE_MANIFEST_SHA256),
    ):
        if sha256(path.read_bytes()).hexdigest() != digest:
            raise ValueError(
                "baseline manifest bytes differ from independent pin: " + path.name
            )
    extraction = _read(extraction_path)
    frozen = _read(frozen_path)
    if extraction["archive_sha256"] != ARCHIVE_SHA256:
        raise ValueError("extraction archive identity differs from independent pin")
    if frozen["verification"]["archive_sha256"] != ORIGINAL_FREEZE_ARCHIVE_SHA256:
        raise ValueError(
            "original freeze archive identity differs from independent pin"
        )
    entries = _unique(extraction["entries"], "name", "extraction entry name")
    materials = _unique(extraction["materials"], "id", "extraction material ID")
    sources = _unique(frozen["sources"], "source_id", "frozen source ID")
    method = _read(ledger / "METHODICHKA_RULE_LEDGER.json")["source"]
    visual = _read(ledger / "METHODICHKA_VISUAL_LEDGER.json")
    secondary = _unique(
        _read(ledger / "SECONDARY_SOURCE_COMPARISON.json")["sources"],
        "source_id",
        "secondary source ID",
    )
    if set(secondary) != {"SW6", "SW8", "SW10", "DemandSupply"}:
        raise ValueError("secondary DOCX source set mismatch")
    verified_members = []
    method_bytes = None
    with zipfile.ZipFile(io.BytesIO(archive_bytes)) as archive:
        for source_id, frozen_id, material_id, name, digest in DOCX_PINS:
            value = _member(archive, name)
            entry, material, source = (
                entries.get(name),
                materials.get(material_id),
                sources.get(frozen_id),
            )
            if (
                sha256(value).hexdigest() != digest
                or entry is None
                or material is None
                or source is None
                or entry["sha256"] != digest
                or entry["id"] != material_id
                or entry["bytes"] != len(value)
                or material["name"] != name
                or source["filename"] != name
                or source["sha256"] != digest
                or source["recorded_sha256_from_archive_manifest"] != digest
            ):
                raise ValueError(
                    "actual DOCX/extraction/frozen member identity mismatch: " + name
                )
            if source_id == "Methodichka":
                method_bytes = value
                if (
                    method["raw_entry_name"] != name
                    or method["raw_entry_sha256"] != digest
                    or visual["source"]["raw_entry"] != name
                    or visual["source"]["raw_entry_sha256"] != digest
                    or visual["source"]["document_part"] != "word/document.xml"
                    or visual["source"]["relationship_part"]
                    != "word/_rels/document.xml.rels"
                ):
                    raise ValueError("Methodichka ledger raw source identity mismatch")
            else:
                row = secondary[source_id]
                if (
                    row["archive_member"] != name
                    or row["archive_member_sha256"] != digest
                    or row["manifest_entry_id"] != material_id
                ):
                    raise ValueError("secondary ledger raw source identity mismatch")
            verified_members.append(
                {
                    "source_id": source_id,
                    "name": name,
                    "sha256": digest,
                    "bytes": len(value),
                }
            )
    clean_path = repository / "data/source_materials/cryptology_2026_10_09/19.clean.txt"
    if sha256(clean_path.read_bytes()).hexdigest() != materials[19]["text_sha256"]:
        raise ValueError("Methodichka clean extraction byte hash mismatch")
    if method["actual_text_sha256"] != materials[19]["text_sha256"]:
        raise ValueError("Methodichka clean extraction linkage mismatch")
    try:
        result = _audit_methodichka(
            method_bytes, _clean_paragraphs(clean_path), visual, materials[19]
        )
    except (zipfile.BadZipFile, ET.ParseError, KeyError, IndexError, TypeError) as exc:
        raise ValueError("malformed archive DOCX audit input") from exc
    return {
        "status": "PASS",
        "classification": "TECHNICAL_NORMALIZATION",
        "archive_path": ARCHIVE_PATH,
        "archive_commit": ARCHIVE_COMMIT,
        "archive_git_blob": ARCHIVE_GIT_BLOB,
        "archive_sha256": ARCHIVE_SHA256,
        "extraction_manifest_sha256": EXTRACTION_MANIFEST_SHA256,
        "source_freeze_manifest_sha256": SOURCE_FREEZE_MANIFEST_SHA256,
        "original_freeze_archive_sha256": ORIGINAL_FREEZE_ARCHIVE_SHA256,
        "whole_archives_byte_identical": False,
        "audited_docx_member_identities_match_original_freeze": True,
        "verified_docx_members": verified_members,
        **result,
        "trade_entry_allowed": False,
        "financial_backtest_allowed": False,
        "paper_allowed": False,
        "live_allowed": False,
        "private_api_allowed": False,
        "runtime_change": False,
    }
