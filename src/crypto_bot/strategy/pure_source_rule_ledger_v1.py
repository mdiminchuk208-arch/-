"""Non-financial source citation and paragraph-coverage QA, never trade logic."""

from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

LEDGER_VERSION = "PURE_SOURCE_STAGE19_RULE_LEDGER_V1"


def _read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _hash(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _normal(text: str) -> str:
    return " ".join(text.split())


def _source_path(root: Path, name: str) -> Path:
    path = (root / name).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError("source path escapes repository")
    return path


def _paragraphs(path: Path) -> tuple[dict[str, str], dict[str, int]]:
    blocks, lines = {}, {}
    current = None
    active = False
    for index, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if line.startswith("PART "):
            active = line == "PART word/document.xml"
            current = None
            continue
        if not active:
            continue
        match = re.match(r"^(P\d{4})\s+(.*)", line)
        if match:
            current = match[1]
            if current in blocks:
                raise ValueError("duplicate source paragraph ID")
            blocks[current], lines[current] = match[2], index
        elif current:
            blocks[current] += " " + line
    return {key: _normal(value) for key, value in blocks.items()}, lines


def _audit_safety(value) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if (
                key
                in {
                    "trade_entry_allowed",
                    "financial_backtest_allowed",
                    "paper_allowed",
                    "live_allowed",
                    "private_api_allowed",
                    "runtime_change",
                }
                and child is not False
            ):
                raise ValueError("audit safety metadata must remain false")
            if (
                key in {"project_policy_applied", "ranked_or_selected_variants"}
                and child is not False
                and child != []
            ):
                raise ValueError("project/ranking metadata is forbidden")
            _audit_safety(child)
    elif isinstance(value, list):
        for child in value:
            _audit_safety(child)


def _primary_blocks(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    markers = list(
        re.finditer(r"^===== (SW\d+) PAGE (\d+) =====\n", text, re.MULTILINE)
    )
    blocks = {}
    for index, marker in enumerate(markers):
        offset = marker.end()
        content = text[
            offset : markers[index + 1].start()
            if index + 1 < len(markers)
            else len(text)
        ]
        cursor, paragraph = 0, 0
        for block in re.split(r"\n\s*\n", content):
            start = content.find(block, cursor)
            cursor = start + len(block)
            if not block.strip():
                continue
            paragraph += 1
            value = block.strip()
            begin = offset + start + block.index(value)
            end = begin + len(value) - 1
            blocks[(int(marker[2]), paragraph)] = (
                value,
                text[:begin].count("\n") + 1,
                text[:end].count("\n") + 1,
            )
    return blocks


@dataclass(frozen=True)
class SourceLedgerValidation:
    version: str
    methodichka_rules: int
    methodichka_paragraphs: int
    exact_quote_checks: int
    methodichka_distinct_figures: int
    methodichka_image_references: int
    verified_source_files: tuple[tuple[str, str], ...]
    artifact_sha256: tuple[tuple[str, str], ...]
    trade_entry_allowed: bool = False
    financial_backtest_allowed: bool = False


def validate_source_rule_ledger(
    ledger: Path, *, repository: Path
) -> SourceLedgerValidation:
    """Check retained source bytes/citations, not the truth of market annotations.

    Raw DOCX/archive visual inspections remain named human audit receipts. CI can
    verify their original entry/text/image hashes against the frozen manifests;
    it does not pretend to rediscover semantic meaning with OCR or a backtest.
    """
    root = repository.resolve()
    for path in ledger.glob("*.json"):
        _audit_safety(_read(path))
    frozen = _read(root / "docs/source_freeze_v1/source_manifest.json")
    source_hashes = {row["source_id"]: row["sha256"] for row in frozen["sources"]}
    archive = _read(root / "data/source_materials/cryptology_2026_10_09/manifest.json")
    materials = {str(row["id"]): row for row in archive["materials"]}
    entries = {row["name"]: row for row in archive["entries"]}
    verified = {}

    def check_file(name: str, expected: str) -> Path:
        path = _source_path(root, name)
        if _hash(path) != expected:
            raise ValueError("source byte hash mismatch: " + name)
        verified[name] = expected
        return path

    method = _read(ledger / "METHODICHKA_RULE_LEDGER.json")
    source = method["source"]
    if source["raw_entry_sha256"] != source_hashes["SRC_METHOD_001"]:
        raise ValueError("Methodichka raw entry differs from priority-1 freeze")
    if entries[source["raw_entry_name"]]["sha256"] != source["raw_entry_sha256"]:
        raise ValueError("Methodichka archive-entry linkage mismatch")
    if materials["19"]["text_sha256"] != source["actual_text_sha256"]:
        raise ValueError("Methodichka text linkage mismatch")
    method_path = check_file(source["clean_text_path"], source["actual_text_sha256"])
    paragraphs, line_map = _paragraphs(method_path)
    rules = method["rules"]
    ids = [row["rule_id"] for row in rules]
    if not rules or len(ids) != len(set(ids)):
        raise ValueError("source rule identities must be nonempty and unique")
    quote_checks = 0
    for row in rules:
        if (
            row["classification"] != "SOURCE_RULE"
            or row["machine_state"] not in {"EXPLICIT", "ALTERNATIVES", "UNKNOWN"}
            or row["operational_input_state"] != "UNKNOWN"
            or row["executable_trade_rule_identified"] is not False
            or row["causal_output"]["trade_entry_allowed"] is not False
        ):
            raise ValueError(
                "source meaning must remain separate from executable qualification"
            )
        if (
            row["lifecycle"]["technical_normalization"]["classification"]
            != "TECHNICAL_NORMALIZATION"
        ):
            raise ValueError("software timestamp mapping is not SOURCE_RULE")
        if set(row["paragraph_ids"]) != {c["paragraph_id"] for c in row["citations"]}:
            raise ValueError("Methodichka rule/citation coverage mismatch")
        for citation in row["citations"]:
            pid = citation["paragraph_id"]
            if (
                not _normal(citation["short_exact_quote"])
                or pid not in row["paragraph_ids"]
                or line_map[pid] != citation["clean_file_line"]
                or _normal(citation["short_exact_quote"]) not in paragraphs[pid]
            ):
                raise ValueError("Methodichka citation mismatch")
            quote_checks += 1

    with (ledger / "METHODICHKA_PARAGRAPH_COVERAGE.csv").open(
        newline="", encoding="utf-8"
    ) as handle:
        coverage = list(csv.DictReader(handle))
    if len(coverage) != len(paragraphs) or {
        row["paragraph_id"] for row in coverage
    } != set(paragraphs):
        raise ValueError("Methodichka coverage is incomplete or duplicated")
    # Hash the exact extracted paragraph text before whitespace normalization.
    raw_blocks = {}
    for line in method_path.read_text(encoding="utf-8").splitlines():
        match = re.match(r"^(P\d{4})\s+(.*)", line)
        if match:
            raw_blocks[match[1]] = match[2]
    for row in coverage:
        pid = row["paragraph_id"]
        if (
            int(row["clean_file_line"]) != line_map[pid]
            or sha256(raw_blocks[pid].encode()).hexdigest() != row["paragraph_sha256"]
            or set(filter(None, row["rule_ids"].split("|")))
            != {rule["rule_id"] for rule in rules if pid in rule["paragraph_ids"]}
            or row["executable_trade_rule_identified"] != "False"
        ):
            raise ValueError("Methodichka coverage content mismatch")

    with (ledger / "METHODICHKA_RULE_TABLE.csv").open(
        newline="", encoding="utf-8"
    ) as handle:
        table = list(csv.DictReader(handle))
    by_id = {row["rule_id"]: row for row in rules}
    if len(table) != len(rules) or {row["rule_id"] for row in table} != set(ids):
        raise ValueError("rule table coverage mismatch")
    for row in table:
        expected = by_id[row["rule_id"]]
        if (
            row["exact_source_meaning"] != expected["stated_semantic"]
            or row["classification"] != expected["classification"]
            or row["machine_state"] != expected["machine_state"]
            or row["paragraph_page"] != "|".join(expected["paragraph_ids"])
            or json.loads(row["causal_inputs"]) != expected["causal_inputs"]
            or json.loads(row["output"]) != expected["causal_output"]
            or json.loads(row["known_at"]) != expected["lifecycle"]
            or json.loads(row["unresolved"]) != expected["unresolved"]
        ):
            raise ValueError("rule table semantics/lifecycle mismatch")

    visual = _read(ledger / "METHODICHKA_VISUAL_LEDGER.json")
    if visual["source"]["raw_entry_sha256"] != source_hashes["SRC_METHOD_001"]:
        raise ValueError("visual evidence has wrong source document")
    image_pins = {row["path"]: row["sha256"] for row in materials["19"]["images"]}
    figures = visual["figures"]
    if len(figures) != len({row["sha256"] for row in figures}) or {
        row["sha256"] for row in figures
    } != set(image_pins.values()):
        raise ValueError("distinct visual coverage mismatch")
    for row in figures:
        if (
            image_pins[row["image_manifest_key"]] != row["sha256"]
            or row["inspection"]["actual_asset_viewed"] is not True
            or row["trade_entry_allowed"] is not False
            or row["source_evidence_classification"] != "SOURCE_RULE"
        ):
            raise ValueError("visual provenance mismatch")
    references = visual["document_image_reference_inventory"]
    if len(references) != len(image_pins) or {
        row["image_asset_manifest_key"] for row in references
    } != set(image_pins):
        raise ValueError("image relationship coverage mismatch")
    for row in references:
        if image_pins[row["image_asset_manifest_key"]] != row["sha256"]:
            raise ValueError("image relationship hash mismatch")

    primary = _read(ledger / "PRIMARY_SOURCE_COMPARISON.json")
    primary_manifest = {
        row["source"]: row
        for row in _read(
            root / "data/source_materials/primary_pdf_2026_10_09/manifest.json"
        )
    }
    primary_sources, page_blocks = {}, {}
    if {row["source"] for row in primary["sources"]} != {
        "SW5",
        "SW9",
        "SW11",
        "SW12",
        "SW22",
    } or len(primary["sources"]) != 5:
        raise ValueError("primary source set mismatch")
    for row in primary["sources"]:
        if row["pdf_sha256"] != source_hashes["SRC_" + row["source"] + "_001"]:
            raise ValueError("primary PDF differs from source freeze")
        trusted = primary_manifest[row["source"]]
        prefix = "data/source_materials/primary_pdf_2026_10_09/" + row["source"]
        if (
            row["text_sha256"] != trusted["text_sha256"]
            or row["pdf_sha256"] != trusted["sha256"]
            or row["text_path"] != prefix + ".txt"
            or row["pdf_path"] != prefix + ".pdf"
        ):
            raise ValueError("primary extraction manifest linkage mismatch")
        check_file(row["pdf_path"], row["pdf_sha256"])
        path = check_file(row["text_path"], row["text_sha256"])
        primary_sources[row["source"]] = row
        page_blocks[row["source"]] = _primary_blocks(path)
    for row in primary["evidence"].values():
        origin = primary_sources.get(row["source"])
        block = page_blocks.get(row["source"], {}).get(
            (row["page"], row["paragraph_index"])
        )
        expected_locator = (
            f"{row['source']}:p{row['page']:02d}:¶{row['paragraph_index']:02d}"
        )
        if (
            origin is None
            or block is None
            or row["text_path"] != origin["text_path"]
            or row["locator"] != expected_locator
            or (row["line_start"], row["line_end"]) != block[1:]
        ):
            raise ValueError("primary source/page/locator mismatch")
        if not _normal(row["quote"]) or _normal(row["quote"]) not in _normal(block[0]):
            raise ValueError("primary quote mismatch")
        quote_checks += 1

    secondary = _read(ledger / "SECONDARY_SOURCE_COMPARISON.json")
    secondary_blocks = {}
    secondary_frozen = {
        "SW6": "SRC_SW6_001",
        "SW8": "SRC_SW8_001",
        "SW10": "SRC_SW10_001",
        "DemandSupply": "SRC_DS_001",
    }
    for row in secondary["sources"]:
        if (
            row["archive_member_sha256"]
            != source_hashes[secondary_frozen[row["source_id"]]]
        ):
            raise ValueError("secondary entry differs from source freeze")
        if entries[row["archive_member"]]["sha256"] != row["archive_member_sha256"]:
            raise ValueError("secondary raw entry linkage mismatch")
        material = materials[str(row["manifest_entry_id"])]
        if (
            material["text_sha256"] != row["clean_text_sha256"]
            or material["name"] != row["archive_member"]
        ):
            raise ValueError("secondary text linkage mismatch")
        path = check_file(row["clean_text_path"], row["clean_text_sha256"])
        secondary_blocks[row["source_id"]] = _paragraphs(path)[0]
    for row in secondary["evidence"]:
        chunk = " ".join(
            secondary_blocks[row["source_id"]][pid] for pid in row["paragraphs"]
        )
        if (
            not _normal(row["short_quote_ru"])
            or row["classification"] != "SOURCE_RULE"
            or row["trade_entry_allowed"] is not False
            or _normal(row["short_quote_ru"]) not in _normal(chunk)
        ):
            raise ValueError("secondary citation mismatch")
        quote_checks += 1

    conflicts = _read(ledger / "SOURCE_CONFLICT_REGISTRY.json")
    for document in (primary, secondary):
        if not isinstance(document.get("safety"), dict) or any(
            document["safety"].get(flag) is not False
            for flag in (
                "trade_entry_allowed",
                "financial_backtest_allowed",
                "paper_allowed",
                "live_allowed",
                "private_api_allowed",
            )
        ):
            raise ValueError("report root safety contract missing or invalid")
    if (
        conflicts["classification"] != "TECHNICAL_NORMALIZATION"
        or conflicts["trade_entry_allowed"] is not False
        or conflicts["financial_backtest_allowed"] is not False
        or conflicts["project_policy_applied"] != []
        or conflicts["source_priority"] != frozen["rules"]["source_priority"]
    ):
        raise ValueError("source conflict register must preserve authority and safety")
    artifacts = tuple(
        sorted(
            (p.name, _hash(p))
            for p in ledger.iterdir()
            if p.is_file() and p.suffix in {".json", ".csv"}
        )
    )
    return SourceLedgerValidation(
        LEDGER_VERSION,
        len(rules),
        len(paragraphs),
        quote_checks,
        len(figures),
        len(references),
        tuple(sorted(verified.items())),
        artifacts,
    )
