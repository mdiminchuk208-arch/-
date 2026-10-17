"""Non-financial source citation and paragraph-coverage QA, never trade logic."""

from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

from crypto_bot.strategy.pure_source_archive_audit_v1 import audit_archive_provenance
from crypto_bot.strategy.pure_source_audit_retention_v1 import (
    validate_retained_handoffs,
)

LEDGER_VERSION = "PURE_SOURCE_STAGE19_RULE_LEDGER_V1"
REVIEWED_REFERENCE = "audit/REVIEWED_CITATION_EXPORT_REFERENCE.json"
# Independent code pin: editing a ledger and its purported reference together
# must not redefine the originally reviewed selection or historical export.
REVIEWED_REFERENCE_SHA256 = (
    "d9b5e3d7af10d5381292246c80260916984c804903945b7685e236dfbbb28cc2"
)


def _reviewed_reference(ledger: Path) -> dict:
    path = ledger / REVIEWED_REFERENCE
    if _hash(path) != REVIEWED_REFERENCE_SHA256:
        raise ValueError("reviewed citation/export reference integrity mismatch")
    return _read(path)


def _check_selected_quote(reference, seen, key, quote, context, locator, error):
    pin = reference["citations"].get(key)
    normalized, context = _normal(quote), _normal(context)
    if (
        pin is None
        or key in seen
        or quote != pin["selected_quote"]
        or locator != pin["locator"]
        or sha256(normalized.encode()).hexdigest() != pin["normalized_excerpt_sha256"]
        or sha256(context.encode()).hexdigest() != pin["context_sha256"]
        or context[pin["start_offset"] : pin["end_offset_exclusive"]] != normalized
    ):
        raise ValueError(error + ": reviewed excerpt/locator mismatch")
    seen.add(key)


def _read_export(path, reference, error):
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        columns, rows = reader.fieldnames, list(reader)
    expected = reference["historical_exports"][path.name]
    if columns != expected["columns"]:
        raise ValueError(error + ": authoritative columns mismatch")
    return rows, expected["rows"]


def _read(path: Path):
    def unique_object(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate JSON object key: " + key)
            result[key] = value
        return result

    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique_object)


def _validate_reviewed_metadata(reference: dict, documents: dict) -> None:
    """Bind original reviewed provenance assertions, after actual-source checks.

    Section hashes came from the committed review base, independently of these
    input ledgers. Historical paths/claims are retained evidence, not runtime
    source locators or substitutes for reconstructed archive/XML identities.
    """
    for filename, sections in reference["reviewed_metadata_hashes"].items():
        document = documents[filename]
        for section, expected in sections.items():
            if section not in document:
                raise ValueError("reviewed source metadata section missing")
            canonical = json.dumps(
                document[section],
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
            if sha256(canonical).hexdigest() != expected:
                raise ValueError(
                    "reviewed source metadata/identity mismatch: "
                    + filename
                    + ":"
                    + section
                )


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


def _validate_conflict_citations(
    conflicts,
    reference,
    paragraphs,
    rules,
    primary,
    secondary,
    visual,
):
    """Resolve historical citation forms to checked source identities/locators.

    Page-range aliases are transport conveniences, not extra SOURCE evidence.
    Their targets must be concrete already-checked primary excerpt records.
    """
    primary_evidence = primary["evidence"]
    findings = {row["id"]: row["evidence"] for row in primary["findings"]}
    if (
        len(findings) != len(primary["findings"])
        or findings != reference["primary_findings"]
    ):
        raise ValueError("conflict primary finding identities/citations mismatch")
    if any(
        not ids or not set(ids) <= primary_evidence.keys() for ids in findings.values()
    ):
        raise ValueError("conflict primary finding has unknown evidence IDs")
    rule_map = {row["rule_id"]: row for row in rules}
    secondary_map = {row["id"]: row for row in secondary["evidence"]}
    figures = {row["figure_id"]: row for row in visual["figures"]}
    if len(secondary_map) != len(secondary["evidence"]) or len(figures) != len(
        visual["figures"]
    ):
        raise ValueError("conflict citation identities must be unique")
    priority = reference["source_priority"]

    def source_rank(source):
        # All consulted secondary originals retain rank7; they cannot override
        # Methodichka or a primary SW source through an invented source label.
        if source in {"SW6", "SW8", "SW10", "DemandSupply"}:
            source = "other confirmed ORIGINAL SOURCE materials"
        if source not in priority:
            raise ValueError("conflict citation source authority mismatch")
        return priority.index(source) + 1

    def resolve(citation):
        match = re.fullmatch(r"Методичка (P\d{4})(?:-(P\d{4}))?", citation)
        if match:
            first, last = int(match[1][1:]), int((match[2] or match[1])[1:])
            ids = [f"P{i:04d}" for i in range(first, last + 1)]
            if not ids or not set(ids) <= paragraphs.keys():
                raise ValueError("conflict citation paragraph mismatch")
            return [(source_rank("Методичка"), pid) for pid in ids]
        if citation in rule_map:
            return [
                item
                for pid in rule_map[citation]["paragraph_ids"]
                for item in resolve("Методичка " + pid)
            ]
        if citation in primary_evidence:
            row = primary_evidence[citation]
            return [(source_rank(row["source"]), row["locator"])]
        if citation in findings:
            return [item for eid in findings[citation] for item in resolve(eid)]
        if citation in secondary_map:
            row = secondary_map[citation]
            return [
                (source_rank(row["source_id"]), row["source_id"] + ":" + pid)
                for pid in row["paragraphs"]
            ]
        if citation in figures:
            row = figures[citation]
            location = row["source_location"]
            if not set(row["related_text_rule_ids"]) <= rule_map.keys() or any(
                location[key] is not None and location[key] not in paragraphs
                for key in (
                    "preceding_or_containing_clean_paragraph",
                    "next_clean_paragraph",
                )
            ):
                raise ValueError("conflict visual rule/paragraph locator mismatch")
            return [(source_rank("Методичка"), citation)]
        match = re.fullmatch(r"(SW\d+) p(\d+)(?:-(\d+))?", citation)
        if match:
            targets = [
                eid
                for eid, row in primary_evidence.items()
                if row["source"] == match[1]
                and int(match[2]) <= row["page"] <= int(match[3] or match[2])
            ]
            if targets:
                return [item for eid in targets for item in resolve(eid)]
        raise ValueError("unknown conflict citation: " + str(citation))

    ids = [row["id"] for row in conflicts["entries"]]
    if not ids or len(ids) != len(set(ids)):
        raise ValueError("conflict identities must be nonempty and unique")
    for row in conflicts["entries"]:
        if not row["citations"] or len(row["citations"]) != len(set(row["citations"])):
            raise ValueError("conflict citations must be nonempty and unique")
        for citation in row["citations"]:
            if not resolve(citation):
                raise ValueError("empty conflict citation resolution")
        if row.get("visual_corroboration") not in (
            None,
            "METHODICHKA_VISUAL_LEDGER.json",
        ):
            raise ValueError("conflict visual corroboration locator mismatch")
    if conflicts["entries"] != reference["conflict_entries"]:
        raise ValueError("conflict citations/content differ from reviewed export")


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

    Raw archive/DOCX bytes and relationships are checked independently. Pinned
    excerpts preserve the named agents' reviewed selection, without reinterpreting SOURCE.
    """
    root = repository.resolve()
    reference = _reviewed_reference(ledger)
    validate_retained_handoffs(root, ledger)
    selected_quotes = set()
    archive_audit = audit_archive_provenance(root, ledger)
    raw_paragraph_indices = {}
    for mapping in archive_audit["raw_paragraph_mapping"]:
        raw_paragraph_indices.setdefault(
            mapping["clean_paragraph_id"], mapping["raw_nonempty_index"]
        )
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
    if (
        source["source_id"] != "SRC_METHOD_001"
        or source["source_name"] != "Методичка"
        or source["priority"] != 1
    ):
        raise ValueError("Methodichka source authority mismatch")
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
        for citation_index, citation in enumerate(row["citations"]):
            pid = citation["paragraph_id"]
            if (
                not _normal(citation["short_exact_quote"])
                or pid not in row["paragraph_ids"]
                or pid not in paragraphs
                or line_map[pid] != citation["clean_file_line"]
                or _normal(citation["short_exact_quote"]) not in paragraphs[pid]
            ):
                raise ValueError("Methodichka citation mismatch")
            _check_selected_quote(
                reference,
                selected_quotes,
                f"method:{row['rule_id']}:{citation_index}",
                citation["short_exact_quote"],
                paragraphs[pid],
                {
                    "source": "Методичка",
                    "source_id": "SRC_METHOD_001",
                    "text_path": source["clean_text_path"],
                    "paragraph_id": pid,
                    "clean_file_line": line_map[pid],
                },
                "Methodichka citation mismatch",
            )
            quote_checks += 1

    coverage, reviewed_coverage = _read_export(
        ledger / "METHODICHKA_PARAGRAPH_COVERAGE.csv",
        reference,
        "Methodichka coverage content mismatch",
    )
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
            or int(row["raw_document_nonempty_paragraph_index_1based"])
            != raw_paragraph_indices[pid]
            or sha256(raw_blocks[pid].encode()).hexdigest() != row["paragraph_sha256"]
            or set(filter(None, row["rule_ids"].split("|")))
            != {rule["rule_id"] for rule in rules if pid in rule["paragraph_ids"]}
            or row["executable_trade_rule_identified"] != "False"
        ):
            raise ValueError("Methodichka coverage content mismatch")
    if coverage != reviewed_coverage:
        raise ValueError("Methodichka coverage content mismatch: historical export")

    table, reviewed_table = _read_export(
        ledger / "METHODICHKA_RULE_TABLE.csv",
        reference,
        "rule table semantics/lifecycle mismatch",
    )
    by_id = {row["rule_id"]: row for row in rules}
    if len(table) != len(rules) or {row["rule_id"] for row in table} != set(ids):
        raise ValueError("rule table coverage mismatch")
    for row in table:
        expected = by_id[row["rule_id"]]
        if (
            row["exact_source_meaning"] != expected["stated_semantic"]
            or row["source"] != source["source_id"]
            or row["source_role"] != expected["source_role"]
            or row["classification"] != expected["classification"]
            or row["machine_state"] != expected["machine_state"]
            or row["paragraph_page"] != "|".join(expected["paragraph_ids"])
            or json.loads(row["causal_inputs"]) != expected["causal_inputs"]
            or json.loads(row["output"]) != expected["causal_output"]
            or json.loads(row["known_at"]) != expected["lifecycle"]
            or row["invalidated_at"]
            != expected["lifecycle"]["technical_normalization"]["invalidated_at"]
            or json.loads(row["unresolved"]) != expected["unresolved"]
        ):
            raise ValueError("rule table semantics/lifecycle mismatch")
    if table != reviewed_table:
        raise ValueError("rule table semantics/lifecycle mismatch: historical export")

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
    for evidence_id, row in primary["evidence"].items():
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
        _check_selected_quote(
            reference,
            selected_quotes,
            "primary:" + evidence_id,
            row["quote"],
            block[0],
            {
                key: row[key]
                for key in (
                    "source",
                    "text_path",
                    "page",
                    "paragraph_index",
                    "locator",
                    "line_start",
                    "line_end",
                )
            },
            "primary quote mismatch",
        )
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
        _check_selected_quote(
            reference,
            selected_quotes,
            "secondary:" + row["id"],
            row["short_quote_ru"],
            chunk,
            {key: row[key] for key in ("source_id", "source_part", "paragraphs")},
            "secondary citation mismatch",
        )
        quote_checks += 1
    if selected_quotes != set(reference["citations"]):
        raise ValueError("reviewed citation coverage mismatch")

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
        or conflicts["source_priority"] != reference["source_priority"]
        or primary["scope"]["source_priority"]
        != " → ".join(reference["source_priority"])
        or secondary["source_priority"]
        != reference["priority_labels"]["SECONDARY_SOURCE_COMPARISON.json"]
        or visual["source_priority"]
        != reference["priority_labels"]["METHODICHKA_VISUAL_LEDGER.json"]
    ):
        raise ValueError("source conflict register must preserve authority and safety")
    _validate_conflict_citations(
        conflicts,
        reference,
        paragraphs,
        rules,
        primary,
        secondary,
        visual,
    )
    _validate_reviewed_metadata(
        reference,
        {
            "METHODICHKA_RULE_LEDGER.json": method,
            "METHODICHKA_VISUAL_LEDGER.json": visual,
            "PRIMARY_SOURCE_COMPARISON.json": primary,
            "SECONDARY_SOURCE_COMPARISON.json": secondary,
        },
    )
    artifacts = tuple(
        sorted(
            (str(p.relative_to(ledger)), _hash(p))
            for p in ledger.rglob("*")
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
