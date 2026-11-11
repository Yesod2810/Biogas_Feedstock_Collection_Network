"""Author: Thanh Dat Nguyen
Student ID: 23857030
Date: 26/09/2026
Purpose: Module 2 source integrity, executable evidence and menu recovery tests.
"""

from manual_structures import LinkedList, manual_contains, manual_count
from test_support import SequenceTestCase

import csv
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from module2_hash.data_loader import (DEFAULT_DATASET, PROJECT_ROOT, HashDataError,
                                      load_lookup, read_farm_records)
from module2_hash.test_driver import run_demo


class SourceAndDriverTests(SequenceTestCase):
    def test_all_125_records_are_searchable_in_full(self):
        loaded = load_lookup()
        self.assertEqual((loaded.table.size, loaded.table.capacity), (125, 197))
        for record in loaded.records:
            self.assertEqual(loaded.table.search(record.farm_id), record)
            self.assertEqual(len(record.fields()), 20)

    def test_required_and_extra_source_fields_survive_loading(self):
        with DEFAULT_DATASET.open(encoding="utf-8", newline="") as stream:
            reader = csv.reader(stream)
            first_two = LinkedList()
            for line in reader:
                first_two.append(line)
                if len(first_two) == 2:
                    break
            header, values = first_two
        record = read_farm_records()[0]
        returned = record.fields()
        for name, original in zip(header, values):
            value = None
            for label, candidate in returned:
                if label == name:
                    value = candidate
                    break
            self.assertEqual(value, float(original) if manual_contains(("Lat", "Lng"), name) else original)

    def test_load_factor_checkpoints_and_growth_events(self):
        loaded = load_lookup()
        self.assertEqual(LinkedList((sample.successful_insertions for sample in loaded.load_samples)), LinkedList(range(10, 121, 10)))
        self.assertEqual(LinkedList((event.new_capacity for event in loaded.resize_events)), LinkedList((23, 47, 97, 197)))
        self.assertEqual(LinkedList((event.insertion_number for event in loaded.resize_events)), LinkedList((8, 17, 33, 68)))
        self.assertAlmostEqual(loaded.table.load_factor, 125 / 197)

    def test_driver_demonstrates_40_real_records(self):
        text, evidence = run_demo(read_farm_records(), 40)
        self.assertEqual(evidence["records_inserted"], 40)
        self.assertEqual(len(evidence["load_samples"]), 4)
        self.assertIn("After collision resolution", text)
        self.assertIn("DELETED ->", text)
        self.assertIn("Surviving colliding farm found after deletion", text)
        self.assertIn("Duplicate beyond tombstone rejected", text)
        self.assertEqual(evidence["active_after_delete"], 39)

    def test_driver_handles_all_125_records(self):
        text, evidence = run_demo(read_farm_records())
        self.assertEqual(evidence["bulk_state"]["records"], 125)
        self.assertEqual(evidence["bulk_state"]["capacity"], 197)
        self.assertEqual(evidence["active_after_delete"], 124)
        self.assertIn("Validation error handled", text)
        self.assertIn("FarmID zzzzz not found", text)
        self.assertIn("Profile URL:", text)

    def test_driver_rejects_insufficient_record_count(self):
        for count in (0, 39, 126):
            with self.assertRaises(HashDataError):
                run_demo(read_farm_records(), count)

    def test_missing_file_and_empty_csv_are_actionable(self):
        with tempfile.TemporaryDirectory() as directory:
            missing = Path(directory) / "missing.csv"
            with self.assertRaises(HashDataError):
                read_farm_records(missing)
            missing.write_text("", encoding="utf-8")
            with self.assertRaises(HashDataError):
                read_farm_records(missing)

    def test_duplicate_source_id_is_rejected(self):
        with DEFAULT_DATASET.open(encoding="utf-8", newline="") as stream:
            rows = LinkedList(LinkedList(row) for row in csv.reader(stream))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "duplicate.csv"
            with path.open("w", encoding="utf-8", newline="") as stream:
                csv.writer(stream).writerows(LinkedList((rows[0], rows[1], rows[1])))
            with self.assertRaisesRegex(HashDataError, "Duplicate FarmID"):
                load_lookup(path)

    def test_invalid_csv_columns_row_length_name_coordinate_and_region(self):
        with DEFAULT_DATASET.open(encoding="utf-8", newline="") as stream:
            rows = LinkedList(LinkedList(row) for row in csv.reader(stream))
        header, first = rows[:2]
        variants = LinkedList((
            LinkedList((LinkedList(('Id',)), LinkedList(('00001',)))),
            LinkedList((header, first[:-1])),
            LinkedList((header + LinkedList(('Id',)), first + LinkedList((first[0],)))),
        ))
        for column, invalid in (("Name", " "), ("Lat", "nan"), ("Lng", "181"),
                                ("State", "VIC"), ("Id", "6.00E+64")):
            row = LinkedList(first)
            for position in range(len(header)):
                if header[position] == column:
                    row[position] = invalid
                    break
            variants.append(LinkedList((header, row)))
        for variant in variants:
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "invalid.csv"
                with path.open("w", encoding="utf-8", newline="") as stream:
                    csv.writer(stream).writerows(variant)
                with self.assertRaises(HashDataError):
                    read_farm_records(path)


class HashMenuTests(SequenceTestCase):
    def run_app(self, args=(), inputs=None, cwd=None):
        return subprocess.run(LinkedList((sys.executable, str(PROJECT_ROOT / "interactive_menu.py"), *args)),
                              input=inputs, text=True, capture_output=True,
                              cwd=cwd or PROJECT_ROOT, timeout=20)

    def test_hash_demo_runs_from_any_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            result = self.run_app(("--module", "hash", "--demo"), cwd=directory)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("BULK INSERTS", result.stdout)
        self.assertIn("INSERT 125", result.stdout)

    def test_hash_validation_cli(self):
        result = self.run_app(("--module", "hash", "--validate"))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(manual_count(result.stdout, "PASS:"), 2)

    def test_search_delete_repeat_delete_and_reinsert(self):
        result = self.run_app(("--module", "hash"),
            "2\n3d8af\n4\n3d8af\n2\n3d8af\n4\n3d8af\n3\n3d8af\n2\n3d8af\n0\n")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Deleted 3d8af", result.stdout)
        self.assertIn("FarmID 3d8af not found", result.stdout)
        self.assertIn("INSERTED", result.stdout)
        self.assertIn("Street Num: 310", result.stdout)

    def test_invalid_ids_duplicates_and_bad_menu_choices_do_not_crash(self):
        result = self.run_app(("--module", "hash"), "bad\n2\nBAD ID\n4\n\n3\n3d8af\n2\nzzzzz\n0\n")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Invalid hash option", result.stdout)
        self.assertIn("Invalid FarmID", result.stdout)
        self.assertIn("Duplicate FarmID", result.stdout)
        self.assertIn("FarmID zzzzz not found", result.stdout)
        self.assertNotIn("Traceback", result.stderr)

    def test_root_menu_opens_hash_module_and_returns(self):
        result = self.run_app(inputs="10\n2\n3d8af\n0\n1\n0\n")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("MODULE 2", result.stdout)
        self.assertIn("Name: Kamarah Piggery", result.stdout)
        self.assertIn("Vertices: 12 | Undirected edges: 18", result.stdout)

    def test_hash_reload_restores_deleted_record(self):
        result = self.run_app(("--module", "hash"), "4\n3d8af\n7\n2\n3d8af\n0\n")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Deleted 3d8af", result.stdout)
        self.assertIn("Name: Kamarah Piggery", result.stdout)

    def test_eof_exits_cleanly(self):
        result = self.run_app(("--module", "hash"), "")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Input ended", result.stdout)

    def test_hash_mode_does_not_require_graph_edge_files(self):
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / "dataset.csv").write_bytes(DEFAULT_DATASET.read_bytes())
            result = self.run_app(("--module", "hash", "--validate", "--data-dir", directory))
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_missing_hash_data_returns_error_without_traceback(self):
        with tempfile.TemporaryDirectory() as directory:
            result = self.run_app(("--module", "hash", "--data-dir", directory))
        self.assertEqual(result.returncode, 1)
        self.assertIn("Cannot read", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_standalone_test_driver_command(self):
        result = subprocess.run(LinkedList((sys.executable, "-m", "module2_hash.test_driver", "--count", "40")),
                                cwd=PROJECT_ROOT, text=True, capture_output=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Real source farms: 40", result.stdout)


if __name__ == "__main__":
    unittest.main()
