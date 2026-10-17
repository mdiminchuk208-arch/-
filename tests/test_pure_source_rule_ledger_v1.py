from __future__ import annotations

import csv
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from crypto_bot.strategy.pure_source_rule_ledger_v1 import (
    REVIEWED_REFERENCE,
    _normal,
    _paragraphs,
    _primary_blocks,
    validate_source_rule_ledger,
)

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "docs/pure_source_stage19_ledger_v1"


class SourceRuleLedgerTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.path = Path(self.temporary.name) / "ledger"
        shutil.copytree(LEDGER, self.path)

    def edit(self, name, mutate):
        path = self.path / name
        value = json.loads(path.read_text())
        mutate(value)
        path.write_text(json.dumps(value, ensure_ascii=False))

    def validate(self):
        return validate_source_rule_ledger(self.path, repository=ROOT)

    def test_complete_source_corpus_is_verified_without_trading_permission(self):
        result = self.validate()
        self.assertEqual(result.methodichka_rules, 47)
        self.assertEqual(result.methodichka_paragraphs, 171)
        self.assertEqual(result.methodichka_distinct_figures, 31)
        self.assertEqual(result.methodichka_image_references, 41)
        self.assertEqual(result.exact_quote_checks, 189)
        self.assertEqual(len(result.verified_source_files), 15)
        self.assertFalse(result.trade_entry_allowed)
        self.assertFalse(result.financial_backtest_allowed)

    def test_exact_citation_tamper_is_rejected(self):
        self.edit(
            "METHODICHKA_RULE_LEDGER.json",
            lambda x: x["rules"][0]["citations"][0].update(
                short_exact_quote="fabricated profitable source condition"
            ),
        )
        with self.assertRaisesRegex(ValueError, "citation mismatch"):
            self.validate()

    def test_paragraph_coverage_cannot_drop_or_relabel_content(self):
        path = self.path / "METHODICHKA_PARAGRAPH_COVERAGE.csv"
        lines = path.read_text().splitlines()
        path.write_text("\n".join(lines[:-1]) + "\n")
        with self.assertRaisesRegex(ValueError, "coverage"):
            self.validate()

    def test_source_meaning_cannot_become_executable_or_project_policy(self):
        self.edit(
            "METHODICHKA_RULE_LEDGER.json",
            lambda x: x["rules"][0].update(classification="PROJECT_POLICY"),
        )
        with self.assertRaisesRegex(ValueError, "executable qualification"):
            self.validate()

    def test_software_timestamps_cannot_be_relabelled_source(self):
        self.edit(
            "METHODICHKA_RULE_LEDGER.json",
            lambda x: x["rules"][0]["lifecycle"]["technical_normalization"].update(
                classification="SOURCE_RULE"
            ),
        )
        with self.assertRaisesRegex(ValueError, "timestamp mapping"):
            self.validate()

    def test_source_hash_linkage_tamper_is_rejected(self):
        self.edit(
            "METHODICHKA_RULE_LEDGER.json",
            lambda x: x["source"].update(actual_text_sha256="0" * 64),
        )
        with self.assertRaisesRegex(
            ValueError, "text linkage|clean extraction linkage"
        ):
            self.validate()

    def test_primary_and_secondary_quote_tampering_fail(self):
        self.edit(
            "PRIMARY_SOURCE_COMPARISON.json",
            lambda x: next(iter(x["evidence"].values())).update(
                quote="invented source text"
            ),
        )
        with self.assertRaisesRegex(ValueError, "primary quote"):
            self.validate()
        shutil.copy2(
            LEDGER / "PRIMARY_SOURCE_COMPARISON.json",
            self.path / "PRIMARY_SOURCE_COMPARISON.json",
        )
        self.edit(
            "SECONDARY_SOURCE_COMPARISON.json",
            lambda x: x["evidence"][0].update(short_quote_ru="invented source text"),
        )
        with self.assertRaisesRegex(ValueError, "secondary citation"):
            self.validate()

    def test_visual_coverage_and_hash_tampering_fail(self):
        self.edit(
            "METHODICHKA_VISUAL_LEDGER.json",
            lambda x: x["figures"][0].update(sha256="0" * 64),
        )
        with self.assertRaisesRegex(ValueError, "visual"):
            self.validate()

    def test_csv_table_cannot_disagree_with_rule_ledger(self):
        path = self.path / "METHODICHKA_RULE_TABLE.csv"
        with path.open(newline="") as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames
            rows = list(reader)
        rows[0]["known_at"] = '{"source":"invented pre-entry timestamp"}'
        with path.open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        with self.assertRaisesRegex(ValueError, "table semantics/lifecycle"):
            self.validate()

    def test_authority_and_safety_flags_cannot_be_overridden(self):
        self.edit(
            "SOURCE_CONFLICT_REGISTRY.json",
            lambda x: x.update(trade_entry_allowed=True),
        )
        with self.assertRaisesRegex(ValueError, "safety"):
            self.validate()

    def test_exact_repeat_is_read_only_and_visual_scope_stays_explicit(self):
        before = {
            str(p.relative_to(self.path)): (p.read_bytes(), p.stat().st_mtime_ns)
            for p in self.path.rglob("*")
            if p.is_file()
        }
        self.assertEqual(self.validate(), self.validate())
        self.assertEqual(
            before,
            {
                str(p.relative_to(self.path)): (p.read_bytes(), p.stat().st_mtime_ns)
                for p in self.path.rglob("*")
                if p.is_file()
            },
        )
        conflicts = json.loads(
            (self.path / "SOURCE_CONFLICT_REGISTRY.json").read_text()
        )
        rows = {row["id"]: row for row in conflicts["entries"]}
        self.assertIn("NOT_UNIVERSAL", rows["RANGE_CHOCH_ATTACHMENT"]["status"])
        self.assertIn(
            "UNIVERSAL_RULE_UNRESOLVED",
            rows["SFP_BODY_ENGULF_ILLUSTRATION_SCOPE"]["status"],
        )
        self.assertTrue(all(row["runtime_change"] is False for row in rows.values()))

    def test_empty_normalized_quotes_are_never_counted(self):
        for name in (
            "METHODICHKA_RULE_LEDGER.json",
            "PRIMARY_SOURCE_COMPARISON.json",
            "SECONDARY_SOURCE_COMPARISON.json",
        ):
            if name.startswith("METHOD"):
                mutate = lambda x: x["rules"][0]["citations"][0].update(
                    short_exact_quote=" "
                )
            elif name.startswith("PRIMARY"):
                mutate = lambda x: next(iter(x["evidence"].values())).update(quote=" ")
            else:
                mutate = lambda x: x["evidence"][0].update(short_quote_ru=" ")
            self.edit(name, mutate)
            with self.subTest(name=name), self.assertRaises(ValueError):
                self.validate()
            shutil.copy2(LEDGER / name, self.path / name)

    def test_source_locator_and_extraction_linkage_cannot_be_relabelled(self):
        name = "PRIMARY_SOURCE_COMPARISON.json"
        self.edit(
            name,
            lambda x: next(iter(x["evidence"].values())).update(
                source="SW22", page=999, locator="SW22:p999:¶999"
            ),
        )
        with self.assertRaisesRegex(ValueError, "source/page/locator"):
            self.validate()
        shutil.copy2(LEDGER / name, self.path / name)
        self.edit(name, lambda x: x["sources"][0].update(text_sha256="0" * 64))
        with self.assertRaisesRegex(ValueError, "extraction manifest"):
            self.validate()
        shutil.copy2(LEDGER / name, self.path / name)
        name = "SECONDARY_SOURCE_COMPARISON.json"

        def unlink(x):
            x["sources"][0].update(
                {
                    key: x["sources"][1][key]
                    for key in (
                        "manifest_entry_id",
                        "clean_text_path",
                        "clean_text_sha256",
                    )
                }
            )

        self.edit(name, unlink)
        with self.assertRaisesRegex(ValueError, "text linkage|raw source identity"):
            self.validate()

    def test_valid_substrings_cannot_replace_reviewed_excerpts(self):
        cases = []
        method = json.loads((LEDGER / "METHODICHKA_RULE_LEDGER.json").read_text())
        row = method["rules"][0]["citations"][0]
        context = _paragraphs(ROOT / method["source"]["clean_text_path"])[0][
            row["paragraph_id"]
        ]
        cases.append(
            (
                "METHODICHKA_RULE_LEDGER.json",
                "short_exact_quote",
                context,
                lambda x: x["rules"][0]["citations"][0],
            )
        )
        primary = json.loads((LEDGER / "PRIMARY_SOURCE_COMPARISON.json").read_text())
        row = next(iter(primary["evidence"].values()))
        context = _normal(
            _primary_blocks(ROOT / row["text_path"])[
                (row["page"], row["paragraph_index"])
            ][0]
        )
        cases.append(
            (
                "PRIMARY_SOURCE_COMPARISON.json",
                "quote",
                context,
                lambda x: next(iter(x["evidence"].values())),
            )
        )
        secondary = json.loads(
            (LEDGER / "SECONDARY_SOURCE_COMPARISON.json").read_text()
        )
        row = secondary["evidence"][0]
        source = next(
            s for s in secondary["sources"] if s["source_id"] == row["source_id"]
        )
        blocks = _paragraphs(ROOT / source["clean_text_path"])[0]
        context = " ".join(blocks[pid] for pid in row["paragraphs"])
        cases.append(
            (
                "SECONDARY_SOURCE_COMPARISON.json",
                "short_quote_ru",
                context,
                lambda x: x["evidence"][0],
            )
        )
        for name, field, context, target in cases:
            original = json.loads((LEDGER / name).read_text())
            quote = target(original)[field]
            # Every replacement is still a valid substring of the cited context.
            for replacement in (context[0], context.split()[-1], _normal(quote)[1:]):
                with self.subTest(name=name, replacement=replacement):
                    self.assertIn(replacement, context)
                    self.edit(
                        name,
                        lambda x, target=target, field=field, replacement=replacement: (
                            target(x).update({field: replacement})
                        ),
                    )
                    with self.assertRaises(ValueError):
                        self.validate()
                    shutil.copy2(LEDGER / name, self.path / name)

    def test_coupled_quote_and_reference_edits_do_not_redefine_review(self):
        self.edit(
            "METHODICHKA_RULE_LEDGER.json",
            lambda x: x["rules"][0]["citations"][0].update(
                short_exact_quote="Структура"
            ),
        )
        self.edit(
            REVIEWED_REFERENCE,
            lambda x: next(iter(x["citations"].values())).update(
                selected_quote="Структура"
            ),
        )
        with self.assertRaisesRegex(ValueError, "reference integrity"):
            self.validate()

    def test_every_export_column_is_authoritative(self):
        for name in (
            "METHODICHKA_PARAGRAPH_COVERAGE.csv",
            "METHODICHKA_RULE_TABLE.csv",
        ):
            original = (LEDGER / name).read_bytes()
            with (LEDGER / name).open(newline="") as handle:
                reader = csv.DictReader(handle)
                fields, rows = reader.fieldnames, list(reader)
            for field in fields:
                for operation in ("modify", "omit"):
                    with self.subTest(name=name, field=field, operation=operation):
                        columns = [
                            f for f in fields if operation != "omit" or f != field
                        ]
                        values = [
                            {k: v for k, v in r.items() if k in columns} for r in rows
                        ]
                        if operation == "modify":
                            values[0][field] = "FABRICATED"
                        with (self.path / name).open("w", newline="") as handle:
                            writer = csv.DictWriter(handle, fieldnames=columns)
                            writer.writeheader()
                            writer.writerows(values)
                        with self.assertRaises((ValueError, KeyError)):
                            self.validate()
                        (self.path / name).write_bytes(original)

    def test_raw_docx_duplicate_offset_is_checked(self):
        path = self.path / "METHODICHKA_PARAGRAPH_COVERAGE.csv"
        with path.open(newline="") as handle:
            reader = csv.DictReader(handle)
            fields, rows = reader.fieldnames, list(reader)
        row = next(row for row in rows if row["paragraph_id"] == "P0101")
        self.assertEqual(row["raw_document_nonempty_paragraph_index_1based"], "102")
        row["raw_document_nonempty_paragraph_index_1based"] = "101"
        with path.open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
        with self.assertRaisesRegex(ValueError, "coverage content"):
            self.validate()

    def test_every_conflict_citation_kind_rejects_fabricated_targets(self):
        for citation in (
            "FABRICATED",
            "Методичка P9999",
            "Методичка P0162-P0158",
            "M_FAKE_RULE",
            "E999",
            "PRIMARY_FAKE",
            "SEC_FAKE",
            "METHOD_VIS_99",
            "SW5 p999",
        ):
            with self.subTest(citation=citation):
                self.edit(
                    "SOURCE_CONFLICT_REGISTRY.json",
                    lambda x, citation=citation: x["entries"][0].update(
                        citations=[citation]
                    ),
                )
                with self.assertRaisesRegex(ValueError, "conflict citation"):
                    self.validate()
                shutil.copy2(
                    LEDGER / "SOURCE_CONFLICT_REGISTRY.json",
                    self.path / "SOURCE_CONFLICT_REGISTRY.json",
                )

    def test_real_conflict_target_substitution_is_not_a_new_review(self):
        self.edit(
            "SOURCE_CONFLICT_REGISTRY.json",
            lambda x: x["entries"][0].update(citations=["Методичка P0001"]),
        )
        with self.assertRaisesRegex(ValueError, "reviewed export"):
            self.validate()

    def test_primary_finding_cannot_reference_nonexistent_evidence(self):
        self.edit(
            "PRIMARY_SOURCE_COMPARISON.json",
            lambda x: x["findings"][0].update(evidence=["FABRICATED"]),
        )
        with self.assertRaisesRegex(ValueError, "finding identities/citations"):
            self.validate()

    def test_source_priority_cannot_be_relabelled_in_any_report(self):
        for name, mutate in (
            ("METHODICHKA_RULE_LEDGER.json", lambda x: x["source"].update(priority=7)),
            (
                "PRIMARY_SOURCE_COMPARISON.json",
                lambda x: x["scope"].update(source_priority="SW5 first"),
            ),
            (
                "SECONDARY_SOURCE_COMPARISON.json",
                lambda x: x.update(source_priority="SW6 overrides Methodichka"),
            ),
            ("METHODICHKA_VISUAL_LEDGER.json", lambda x: x.update(source_priority=7)),
            ("SOURCE_CONFLICT_REGISTRY.json", lambda x: x["source_priority"].reverse()),
        ):
            with self.subTest(name=name):
                self.edit(name, mutate)
                with self.assertRaisesRegex(ValueError, "authority"):
                    self.validate()
                shutil.copy2(LEDGER / name, self.path / name)

    def test_nonexistent_methodichka_citation_is_a_validation_error(self):
        self.edit(
            "METHODICHKA_RULE_LEDGER.json",
            lambda x: (
                x["rules"][0]["paragraph_ids"].__setitem__(0, "P9999"),
                x["rules"][0]["citations"][0].update(paragraph_id="P9999"),
            ),
        )
        with self.assertRaisesRegex(ValueError, "citation mismatch"):
            self.validate()

    def test_original_provenance_metadata_cannot_be_rewritten(self):
        groups = (
            (
                "METHODICHKA_RULE_LEDGER.json",
                ("source",),
                (
                    "archive_manifest_path",
                    "frozen_external_archive_sha256",
                    "frozen_manifest_path",
                    "local_archive_sha256",
                    "manifest_entry_id",
                    "raw_entry_bytes",
                    "recorded_archive_sha256",
                    "recorded_raw_sha256",
                    "recorded_text_sha256",
                ),
            ),
            (
                "METHODICHKA_RULE_LEDGER.json",
                ("source", "frozen_source"),
                (
                    "filename",
                    "recorded_sha256_from_archive_manifest",
                    "sha256",
                    "source_id",
                    "status",
                ),
            ),
            (
                "METHODICHKA_RULE_LEDGER.json",
                ("source", "raw_text_alignment"),
                (
                    "clean_paragraphs",
                    "raw_nonempty_paragraphs",
                    "operations",
                ),
            ),
            (
                "METHODICHKA_VISUAL_LEDGER.json",
                ("source",),
                (
                    "image_manifest_material_id",
                    "image_manifest_path",
                    "original_text_ledger_path",
                    "original_text_ledger_preserved",
                    "original_text_ledger_sha256_at_visual_analysis",
                    "raw_archive_path",
                    "raw_entry_hash_matches_frozen_methodichka",
                    "source_id",
                ),
            ),
            (
                "PRIMARY_SOURCE_COMPARISON.json",
                ("sources", 0),
                (
                    "extracted_page_count_matches",
                    "manifest_pdf_checksum_matches",
                    "manifest_text_checksum_matches",
                    "original_name",
                    "pages",
                ),
            ),
            (
                "PRIMARY_SOURCE_COMPARISON.json",
                ("scope",),
                (
                    "primary_sources_reviewed",
                    "source_directory",
                ),
            ),
            (
                "SECONDARY_SOURCE_COMPARISON.json",
                ("sources", 0),
                (
                    "archive_member_hash_match",
                    "authority_tier",
                    "manifest_hash_match",
                ),
            ),
            (
                "SECONDARY_SOURCE_COMPARISON.json",
                ("manifest",),
                (
                    "archive_manifest_hash_match",
                    "archive_path",
                    "archive_sha256",
                    "path",
                    "sha256",
                ),
            ),
        )
        for filename, path, fields in groups:
            for field in fields:
                with self.subTest(filename=filename, path=path, field=field):

                    def rewrite(value, path=path, field=field):
                        target = value
                        for key in path:
                            target = target[key]
                        original = target[field]
                        if isinstance(original, bool):
                            target[field] = not original
                        elif isinstance(original, int):
                            target[field] = original + 1
                        elif isinstance(original, list):
                            target[field] = original + ["FABRICATED"]
                        else:
                            target[field] = "FABRICATED"

                    self.edit(filename, rewrite)
                    with self.assertRaises(ValueError):
                        self.validate()
                    shutil.copy2(LEDGER / filename, self.path / filename)

    def test_visual_figure_identity_and_review_fields_are_pinned(self):
        filename = "METHODICHKA_VISUAL_LEDGER.json"
        for field, replacement in (
            ("figure_id", "FABRICATED"),
            ("related_text_rule_ids", ["FABRICATED"]),
            ("dimensions_px", [1, 1]),
            ("inspection", {"actual_asset_viewed": True, "ocr_only": True}),
        ):
            with self.subTest(field=field):
                self.edit(
                    filename,
                    lambda x, field=field, replacement=replacement: x["figures"][
                        0
                    ].update({field: replacement}),
                )
                with self.assertRaisesRegex(ValueError, "metadata/identity"):
                    self.validate()
                shutil.copy2(LEDGER / filename, self.path / filename)

        def swap_ids(value):
            first, second = value["figures"][:2]
            first["figure_id"], second["figure_id"] = (
                second["figure_id"],
                first["figure_id"],
            )

        self.edit(filename, swap_ids)
        with self.assertRaisesRegex(ValueError, "metadata/identity"):
            self.validate()

    def test_coupled_provenance_and_reference_hash_edits_are_rejected(self):
        self.edit(
            "METHODICHKA_VISUAL_LEDGER.json",
            lambda x: x["source"].update(source_id="SRC_SW5_001"),
        )
        self.edit(
            REVIEWED_REFERENCE,
            lambda x: x["reviewed_metadata_hashes"][
                "METHODICHKA_VISUAL_LEDGER.json"
            ].update(source="0" * 64),
        )
        with self.assertRaisesRegex(ValueError, "reference integrity"):
            self.validate()

    def test_duplicate_json_keys_are_rejected_by_public_audit(self):
        path = self.path / "METHODICHKA_RULE_LEDGER.json"
        original = path.read_text()
        path.write_text('{"analysis_id":"FABRICATED",' + original.lstrip()[1:])
        with self.assertRaisesRegex(ValueError, "duplicate JSON object key"):
            self.validate()

    def test_safety_in_each_report_and_runtime_change_claim_are_checked(self):
        for name in (
            "PRIMARY_SOURCE_COMPARISON.json",
            "SECONDARY_SOURCE_COMPARISON.json",
            "SOURCE_CONFLICT_REGISTRY.json",
        ):
            if name.startswith("SOURCE"):
                mutate = lambda x: x["entries"][0].update(runtime_change=True)
            else:
                mutate = lambda x: x["safety"].update(trade_entry_allowed=True)
            self.edit(name, mutate)
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, "safety"):
                self.validate()
            shutil.copy2(LEDGER / name, self.path / name)
        self.edit(
            "PRIMARY_SOURCE_COMPARISON.json",
            lambda x: x["safety"].update(project_policy_applied=["ANTI_SCALP"]),
        )
        with self.assertRaisesRegex(ValueError, "project/ranking"):
            self.validate()


if __name__ == "__main__":
    unittest.main()
