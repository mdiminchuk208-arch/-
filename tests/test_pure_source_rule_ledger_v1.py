from __future__ import annotations

import csv
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from crypto_bot.strategy.pure_source_rule_ledger_v1 import validate_source_rule_ledger

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
        with self.assertRaisesRegex(ValueError, "text linkage"):
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
            p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in self.path.iterdir()
        }
        self.assertEqual(self.validate(), self.validate())
        self.assertEqual(
            before,
            {
                p.name: (p.read_bytes(), p.stat().st_mtime_ns)
                for p in self.path.iterdir()
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
        with self.assertRaisesRegex(ValueError, "text linkage"):
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
