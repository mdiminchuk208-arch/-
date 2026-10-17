from __future__ import annotations

import copy
import io
import json
import shutil
import tempfile
import unittest
import warnings
import zipfile
from hashlib import sha256
from pathlib import Path

from crypto_bot.strategy.pure_source_archive_audit_v1 import (
    ARCHIVE_PATH,
    ARCHIVE_SHA256,
    ORIGINAL_FREEZE_ARCHIVE_SHA256,
    _audit_methodichka,
    _clean_paragraphs,
    _member,
    audit_archive_provenance,
)

ROOT = Path(__file__).resolve().parents[1]
LEDGER = Path("docs/pure_source_stage19_ledger_v1")
MATERIALS = Path("data/source_materials/cryptology_2026_10_09")
METHOD = "Криптология/Методичка.docx"


class ArchiveProvenanceTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        paths = [
            Path(ARCHIVE_PATH),
            MATERIALS / "manifest.json",
            MATERIALS / "19.clean.txt",
            Path("docs/source_freeze_v1/source_manifest.json"),
            LEDGER / "METHODICHKA_RULE_LEDGER.json",
            LEDGER / "METHODICHKA_VISUAL_LEDGER.json",
            LEDGER / "SECONDARY_SOURCE_COMPARISON.json",
        ]
        for path in paths:
            target = self.root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / path, target)

    def audit(self):
        return audit_archive_provenance(self.root, self.root / LEDGER)

    def edit(self, relative, change):
        path = self.root / relative
        value = json.loads(path.read_text(encoding="utf-8"))
        change(value)
        path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")

    def rewrite_archive(self, change):
        path = self.root / ARCHIVE_PATH
        with zipfile.ZipFile(path) as archive:
            entries = [
                (info.filename, archive.read(info)) for info in archive.infolist()
            ]
        with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for name, value in change(entries):
                archive.writestr(name, value)

    def document_inputs(self):
        with zipfile.ZipFile(self.root / ARCHIVE_PATH) as archive:
            docx = _member(archive, METHOD)
        clean = _clean_paragraphs(self.root / MATERIALS / "19.clean.txt")
        visual = json.loads(
            (self.root / LEDGER / "METHODICHKA_VISUAL_LEDGER.json").read_text()
        )
        manifest = json.loads((self.root / MATERIALS / "manifest.json").read_text())
        material = next(row for row in manifest["materials"] if row["id"] == 19)
        return docx, clean, visual, material

    @staticmethod
    def rewrite_docx(docx, change):
        with zipfile.ZipFile(io.BytesIO(docx)) as archive:
            entries = [
                (info.filename, archive.read(info)) for info in archive.infolist()
            ]
        output = io.BytesIO()
        with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for name, value in change(entries):
                archive.writestr(name, value)
        return output.getvalue()

    def test_actual_archive_and_all_five_members_are_verified_read_only(self):
        before = {
            path: sha256(path.read_bytes()).hexdigest()
            for path in self.root.rglob("*")
            if path.is_file()
        }
        result = self.audit()
        self.assertEqual(result, self.audit())
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["classification"], "TECHNICAL_NORMALIZATION")
        self.assertEqual(len(result["verified_docx_members"]), 5)
        self.assertEqual(result["archive_sha256"], ARCHIVE_SHA256)
        self.assertEqual(
            result["original_freeze_archive_sha256"], ORIGINAL_FREEZE_ARCHIVE_SHA256
        )
        self.assertNotEqual(
            result["archive_sha256"], result["original_freeze_archive_sha256"]
        )
        self.assertIs(result["whole_archives_byte_identical"], False)
        self.assertTrue(result["audited_docx_member_identities_match_original_freeze"])
        for flag in (
            "trade_entry_allowed",
            "financial_backtest_allowed",
            "paper_allowed",
            "live_allowed",
            "private_api_allowed",
            "runtime_change",
        ):
            self.assertIs(result[flag], False)
        self.assertEqual(result["methodichka_media_assets"], 41)
        self.assertEqual(result["methodichka_distinct_figures"], 31)
        self.assertEqual(result["methodichka_image_references"], 41)
        self.assertEqual(
            before,
            {
                path: sha256(path.read_bytes()).hexdigest()
                for path in self.root.rglob("*")
                if path.is_file()
            },
        )

    def test_raw172_clean171_mapping_preserves_removed_duplicate_identity(self):
        result = self.audit()
        rows = result["raw_paragraph_mapping"]
        self.assertEqual(result["raw_nonempty_paragraph_count"], 172)
        self.assertEqual(result["clean_paragraph_count"], 171)
        self.assertEqual(result["xml_paragraph_count"], 193)
        self.assertEqual([r["raw_nonempty_index"] for r in rows], list(range(1, 173)))
        self.assertEqual(rows[94]["clean_paragraph_id"], "P0095")
        self.assertEqual(rows[100]["clean_paragraph_id"], "P0095")
        self.assertEqual(rows[100]["xml_paragraph_index"], 108)
        self.assertEqual(rows[100]["duplicate_of_raw_nonempty_index"], 95)
        self.assertEqual(rows[100]["text"], rows[94]["text"])
        self.assertEqual(rows[101]["clean_paragraph_id"], "P0101")
        self.assertEqual(rows[108]["clean_paragraph_id"], "P0108")
        self.assertEqual(rows[-1]["clean_paragraph_id"], "P0171")

    def test_member_bytes_and_coordinated_manifest_rehash_cannot_replace_pin(self):
        self.rewrite_archive(
            lambda entries: [
                (name, value + b"altered" if name == METHOD else value)
                for name, value in entries
            ]
        )
        actual = sha256((self.root / ARCHIVE_PATH).read_bytes()).hexdigest()
        self.edit(
            MATERIALS / "manifest.json", lambda x: x.update(archive_sha256=actual)
        )
        with self.assertRaisesRegex(ValueError, "independent commit pin"):
            self.audit()

    def test_changed_member_bytes_with_original_json_manifests_fail(self):
        extraction = (self.root / MATERIALS / "manifest.json").read_bytes()
        frozen = (self.root / "docs/source_freeze_v1/source_manifest.json").read_bytes()
        self.rewrite_archive(
            lambda entries: [
                (name, value + b"modified-member" if name == METHOD else value)
                for name, value in entries
            ]
        )
        self.assertEqual(
            (self.root / MATERIALS / "manifest.json").read_bytes(), extraction
        )
        self.assertEqual(
            (self.root / "docs/source_freeze_v1/source_manifest.json").read_bytes(),
            frozen,
        )
        with self.assertRaisesRegex(ValueError, "independent commit pin"):
            self.audit()

    def test_unchanged_archive_rejects_manifest_only_member_hash_tampering(self):
        self.edit(
            MATERIALS / "manifest.json",
            lambda x: next(row for row in x["entries"] if row["id"] == 19).update(
                sha256="0" * 64
            ),
        )
        with self.assertRaisesRegex(ValueError, "baseline manifest.*independent pin"):
            self.audit()

    def test_frozen_original_archive_must_not_be_relabelled_as_retained_archive(self):
        self.edit(
            Path("docs/source_freeze_v1/source_manifest.json"),
            lambda x: x["verification"].update(archive_sha256=ARCHIVE_SHA256),
        )
        with self.assertRaisesRegex(ValueError, "baseline manifest.*independent pin"):
            self.audit()

    def test_frozen_member_and_extraction_metadata_cannot_be_coordinately_rewritten(
        self,
    ):
        self.edit(
            MATERIALS / "manifest.json",
            lambda x: next(row for row in x["entries"] if row["id"] == 14).update(
                sha256="f" * 64
            ),
        )
        self.edit(
            Path("docs/source_freeze_v1/source_manifest.json"),
            lambda x: next(
                row for row in x["sources"] if row["source_id"] == "SRC_SW6_001"
            ).update(sha256="f" * 64, recorded_sha256_from_archive_manifest="f" * 64),
        )
        with self.assertRaisesRegex(ValueError, "independent pin"):
            self.audit()

    def test_missing_or_duplicated_archive_member_is_rejected(self):
        for mode in ("missing", "duplicate"):
            with self.subTest(mode=mode):
                shutil.copyfile(ROOT / ARCHIVE_PATH, self.root / ARCHIVE_PATH)
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", UserWarning)
                    self.rewrite_archive(
                        lambda entries, mode=mode: (
                            [(n, v) for n, v in entries if n != METHOD]
                            if mode == "missing"
                            else entries + [(METHOD, dict(entries)[METHOD])]
                        )
                    )
                with self.assertRaisesRegex(ValueError, "independent commit pin"):
                    self.audit()

    def test_exact_zip_member_lookup_cannot_use_basename_or_choose_duplicate(self):
        output = io.BytesIO()
        with zipfile.ZipFile(output, "w") as archive:
            archive.writestr("other/Методичка.docx", b"decoy")
        with (
            zipfile.ZipFile(io.BytesIO(output.getvalue())) as archive,
            self.assertRaisesRegex(ValueError, "missing or duplicate exact"),
        ):
            _member(archive, METHOD)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            with zipfile.ZipFile(output, "a") as archive:
                archive.writestr(METHOD, b"one")
                archive.writestr(METHOD, b"two")
        with (
            zipfile.ZipFile(io.BytesIO(output.getvalue())) as archive,
            self.assertRaisesRegex(ValueError, "missing or duplicate exact"),
        ):
            _member(archive, METHOD)

    def test_each_secondary_ledger_identity_is_bound_to_exact_member(self):
        for source in ("SW6", "SW8", "SW10", "DemandSupply"):
            with self.subTest(source=source):
                shutil.copyfile(
                    ROOT / LEDGER / "SECONDARY_SOURCE_COMPARISON.json",
                    self.root / LEDGER / "SECONDARY_SOURCE_COMPARISON.json",
                )
                self.edit(
                    LEDGER / "SECONDARY_SOURCE_COMPARISON.json",
                    lambda x, source=source: next(
                        row for row in x["sources"] if row["source_id"] == source
                    ).update(archive_member=METHOD),
                )
                with self.assertRaisesRegex(
                    ValueError, "secondary ledger raw source identity"
                ):
                    self.audit()

    def test_inventory_fake_rid_target_index_and_neighbors_are_rejected(self):
        changes = {
            "relationship_id": "rId999",
            "relationship_target": "media/image2.jpg",
            "image_asset_manifest_key": "19/image2.jpg",
            "xml_paragraph_index": 64,
            "raw_nonempty_paragraphs_before_or_containing": 61,
            "preceding_or_containing_clean_paragraph": "P0061",
            "next_clean_paragraph": "P0064",
            "next_clean_text": "fabricated adjacency",
            "rendering_branch": "FALLBACK_DUPLICATE",
            "paragraph_location_relation": "WITHIN_TEXT_PARAGRAPH",
            "paragraph_text": "fabricated paragraph",
        }
        docx, clean, visual, material = self.document_inputs()
        for field, replacement in changes.items():
            with self.subTest(field=field):
                edited = copy.deepcopy(visual)
                edited["document_image_reference_inventory"][0][field] = replacement
                with self.assertRaisesRegex(ValueError, "relationship/location"):
                    _audit_methodichka(docx, clean, edited, material)

    def test_relinking_existing_asset_cannot_fake_the_document_relationship(self):
        docx, clean, visual, material = self.document_inputs()
        inventory = visual["document_image_reference_inventory"]
        for key in (
            "relationship_id",
            "relationship_target",
            "image_asset_manifest_key",
            "sha256",
            "bytes",
        ):
            inventory[0][key] = inventory[1][key]
        with self.assertRaisesRegex(ValueError, "relationship/location"):
            _audit_methodichka(docx, clean, visual, material)

    def test_figure_relationship_asset_and_location_are_verified_against_xml(self):
        docx, clean, visual, material = self.document_inputs()
        for mode in ("rid", "target", "location", "missing_location", "asset"):
            with self.subTest(mode=mode):
                edited = copy.deepcopy(visual)
                figure = edited["figures"][0]
                if mode == "rid":
                    figure["source_relationship_references"][0]["relationship_id"] = (
                        "rId999"
                    )
                elif mode == "target":
                    figure["source_relationship_references"][0]["target"] = (
                        "media/image2.jpg"
                    )
                elif mode == "location":
                    figure["source_location"]["next_clean_paragraph"] = "P0064"
                elif mode == "missing_location":
                    figure["source_location"] = {}
                else:
                    figure["source_asset"] = "word/media/image2.jpg"
                with self.assertRaisesRegex(ValueError, "visual figure actual"):
                    _audit_methodichka(docx, clean, edited, material)

    def test_raw_media_bytes_are_recomputed(self):
        docx, clean, visual, material = self.document_inputs()
        edited = self.rewrite_docx(
            docx,
            lambda entries: [
                (name, value + b"altered" if name == "word/media/image1.jpg" else value)
                for name, value in entries
            ],
        )
        with self.assertRaisesRegex(ValueError, "actual DOCX media hash"):
            _audit_methodichka(edited, clean, visual, material)

    def test_raw_xml_rid_and_relationship_target_are_read_from_actual_bytes(self):
        docx, clean, visual, material = self.document_inputs()
        for mode in ("rid", "target"):
            with self.subTest(mode=mode):

                def change(entries, mode=mode):
                    result = []
                    for name, value in entries:
                        if mode == "rid" and name == "word/document.xml":
                            value = value.replace(
                                b'r:embed="rId5"', b'r:embed="rId999"', 1
                            )
                        if mode == "target" and name == "word/_rels/document.xml.rels":
                            value = value.replace(
                                b'Target="media/image1.jpg"',
                                b'Target="media/absent.jpg"',
                                1,
                            )
                        result.append((name, value))
                    return result

                edited = self.rewrite_docx(docx, change)
                self.assertNotEqual(edited, docx)
                with self.assertRaisesRegex(ValueError, "DOCX image.*relationship"):
                    _audit_methodichka(edited, clean, visual, material)

    def test_raw_xml_paragraph_text_cannot_be_replaced_by_clean_metadata(self):
        docx, clean, visual, material = self.document_inputs()
        edited = self.rewrite_docx(
            docx,
            lambda entries: [
                (
                    name,
                    value.replace("Схкма".encode(), b"FAKE", 1)
                    if name == "word/document.xml"
                    else value,
                )
                for name, value in entries
            ],
        )
        with self.assertRaisesRegex(ValueError, "raw DOCX to clean paragraph"):
            _audit_methodichka(edited, clean, visual, material)

    def test_internal_xml_member_must_be_unique_and_present(self):
        docx, clean, visual, material = self.document_inputs()
        for mode in ("missing", "duplicate"):
            with self.subTest(mode=mode), warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                edited = self.rewrite_docx(
                    docx,
                    lambda entries, mode=mode: (
                        [(n, v) for n, v in entries if n != "word/document.xml"]
                        if mode == "missing"
                        else entries
                        + [("word/document.xml", dict(entries)["word/document.xml"])]
                    ),
                )
                with self.assertRaisesRegex(
                    ValueError, "missing or duplicate|duplicate internal"
                ):
                    _audit_methodichka(edited, clean, visual, material)


if __name__ == "__main__":
    unittest.main()
