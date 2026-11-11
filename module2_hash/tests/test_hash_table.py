"""Author: Thanh Dat Nguyen
Student ID: 23857030
Date: 26/09/2026
Purpose: Core hashing, collision clusters, tombstones, growth and a manual node-sequence oracle test.
"""

from manual_structures import LinkedList, manual_any, manual_contains, manual_map
from test_support import SequenceTestCase


import ast
from dataclasses import FrozenInstanceError, replace
from pathlib import Path
import random
import unittest

from module2_hash.hash_table import DuplicateFarmError, HashTable, HashTableError, is_prime, next_prime
from module2_hash.records import FarmRecord, RecordValidationError


def farm(farm_id, name="Synthetic unit-test farm"):
    return FarmRecord(farm_id, name, "Pigs", -32.5, 115.8, "", "Test Road", "Test Town", "WA", "6000", "Australia")


def keys_at_home(table, home, count):
    keys = LinkedList()
    number = 0
    while len(keys) < count:
        key = format(number, "05x")
        if table.hash_index(key) == home:
            keys.append(key)
        number += 1
    return keys


class RecordTests(SequenceTestCase):
    def test_complete_record_has_all_eleven_required_fields(self):
        record = farm("00001")
        self.assertEqual(len(record.fields()), 11)
        self.assertEqual(record.fields()[0], ("Id", "00001"))
        self.assertEqual(record.postcode, "6000")

    def test_immutable_record(self):
        with self.assertRaises(FrozenInstanceError):
            farm("00001").name = "Changed"

    def test_ids_are_exact_text_without_normalisation(self):
        for bad in ("", "    ", "abcd", "abcdef", "ABC12", " a123", "a123 ",
                    "6.00E+64", "ab-12", "é1234", 12345, None):
            with self.subTest(bad=bad):
                with self.assertRaises(RecordValidationError):
                    farm(bad)

    def test_name_and_species_cannot_be_blank(self):
        for field in ("name", "species"):
            for value in ("", "   ", None, 1):
                with self.subTest(field=field, value=value):
                    with self.assertRaises(RecordValidationError):
                        replace(farm("00001"), **manual_map(((field, value),)))

    def test_coordinate_validation(self):
        for field, value in (("lat", "text"), ("lat", float("nan")), ("lat", 91),
                             ("lat", -91), ("lng", 181), ("lng", -181),
                             ("lng", float("inf")), ("lat", None), ("lat", True),
                             ("lat", 10 ** 1000), ("lat", complex(1, 1))):
            with self.subTest(field=field, value=repr(value)[:30]):
                with self.assertRaises(RecordValidationError):
                    replace(farm("00001"), **manual_map(((field, value),)))

    def test_numerical_csv_text_and_boundary_coordinates(self):
        record = replace(farm("00001"), lat="-90", lng="180")
        self.assertEqual((record.lat, record.lng), (-90.0, 180.0))

    def test_source_address_blanks_are_preserved(self):
        record = replace(farm("00001"), street_num="", street="", suburb="", postcode="")
        self.assertEqual((record.street_num, record.street, record.suburb, record.postcode), ("", "", "", ""))

    def test_extra_field_contract(self):
        valid = replace(farm("00001"), extra_fields=(("Tags", "Feedlot"),))
        self.assertEqual(valid.fields()[-1], ("Tags", "Feedlot"))
        for extra in (LinkedList((('Tags', 'Feedlot'),)), (("Id", "00001"),), (("Tags", "a"), ("Tags", "b")),
                      (("Tags", 1),), (("Tags",),)):
            with self.assertRaises(RecordValidationError):
                replace(valid, extra_fields=extra)


class HashTableTests(SequenceTestCase):
    def test_core_has_no_builtin_dictionary_map_set_or_hash(self):
        source = Path(__file__).resolve().parents[1] / "hash_table.py"
        tree = ast.parse(source.read_text(encoding="utf-8"))
        forbidden = (ast.Dict, ast.DictComp, ast.Set, ast.SetComp)
        self.assertFalse(manual_any(isinstance(node, forbidden) for node in ast.walk(tree)))
        calls = LinkedList((node.func.id for node in ast.walk(tree) if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)))
        self.assertFalse(manual_any(manual_contains(("dict", "map", "set", "hash"), name) for name in calls))

    def test_default_empty_table(self):
        table = HashTable()
        self.assertEqual((table.size, table.capacity, table.tombstones, table.load_factor), (0, 11, 0, 0))
        self.assertIsNone(table.search("00001"))
        self.assertIsNone(table.delete("00001"))

    def test_table_size_selection_uses_next_prime(self):
        self.assertEqual(HashTable(12).capacity, 13)
        self.assertTrue(is_prime(197))
        self.assertFalse(is_prime(1))
        self.assertFalse(is_prime(9))
        self.assertEqual(next_prime(22), 23)

    def test_invalid_constructor_parameters(self):
        for capacity in (0, 1, 2, -1, True, "11", 11.0):
            with self.assertRaises(HashTableError):
                HashTable(capacity)
        for threshold in (0, -1, 1, 2, None, True, "0.7", float("nan"), float("inf"), 10 ** 1000):
            with self.assertRaises(HashTableError):
                HashTable(max_load=threshold)

    def test_polynomial_modulo_hash_known_value(self):
        # 3d8af is a real source key; its five-character polynomial modulo 11 is 5.
        self.assertEqual(HashTable(11).hash_index("3d8af"), 5)
        self.assertEqual(HashTable(11).hash_index("71a14"), 5)

    def test_insert_and_return_complete_record(self):
        table = HashTable()
        record = farm("00001")
        self.assertTrue(table.insert(record))
        self.assertIs(table.search("00001"), record)
        self.assertEqual(table.size, 1)

    def test_insert_rejects_non_record_object(self):
        table = HashTable()
        for invalid in (None, "00001", 1, manual_map((("Id", "00001"),))):
            with self.assertRaises(HashTableError):
                table.insert(invalid)
            self.assertEqual(table.size, 0)

    def test_duplicate_retains_original_and_counts(self):
        table = HashTable()
        original = farm("00001", "Original name")
        table.insert(original)
        before = table.slot_views()
        with self.assertRaises(DuplicateFarmError):
            table.insert(farm("00001", "Replacement name"))
        self.assertEqual(table.last_trace.result, "DUPLICATE")
        self.assertEqual((table.size, table.successful_insertions), (1, 1))
        self.assertEqual(table.slot_views(), before)
        self.assertIs(table.search("00001"), original)

    def test_duplicate_at_threshold_does_not_resize(self):
        table = HashTable()
        records = LinkedList((farm(format(i, "05x")) for i in range(7)))
        for record in records:
            table.insert(record)
        with self.assertRaises(DuplicateFarmError):
            table.insert(records[0])
        self.assertEqual((table.capacity, table.resize_count), (11, 0))

    def test_collision_sequence_is_explicit(self):
        table = HashTable()
        keys = keys_at_home(table, 5, 2)
        table.insert(farm(keys[0]))
        table.insert(farm(keys[1]))
        trace = table.last_trace
        self.assertEqual(LinkedList((step.index for step in trace.steps)), LinkedList((5, 6)))
        self.assertEqual(LinkedList((step.state for step in trace.steps)), LinkedList(("OCCUPIED", "EMPTY")))
        self.assertEqual(trace.collisions, 1)

    def test_wraparound_probe_visits_end_then_zero(self):
        table = HashTable()
        keys = keys_at_home(table, 10, 3)
        for key in keys:
            table.insert(farm(key))
        self.assertEqual(LinkedList((step.index for step in table.last_trace.steps)), LinkedList((10, 0, 1)))
        self.assertEqual(table.search(keys[-1]).farm_id, keys[-1])

    def test_delete_cluster_head_preserves_survivor_search(self):
        table = HashTable()
        first, second = keys_at_home(table, 5, 2)
        table.insert(farm(first))
        table.insert(farm(second))
        self.assertEqual(table.delete(first).farm_id, first)
        self.assertIsNone(table.search(first))
        self.assertEqual(table.search(second).farm_id, second)
        self.assertEqual(LinkedList((step.state for step in table.last_trace.steps)), LinkedList(("DELETED", "OCCUPIED")))

    def test_delete_middle_of_wrapped_cluster_preserves_tail(self):
        table = HashTable()
        keys = keys_at_home(table, 10, 3)
        for key in keys:
            table.insert(farm(key))
        table.delete(keys[1])
        self.assertEqual(table.search(keys[2]).farm_id, keys[2])
        self.assertEqual(LinkedList((step.index for step in table.last_trace.steps)), LinkedList((10, 0, 1)))

    def test_duplicate_after_tombstone_is_rejected(self):
        table = HashTable()
        first, second = keys_at_home(table, 5, 2)
        table.insert(farm(first))
        table.insert(farm(second))
        table.delete(first)
        before = table.slot_views()
        with self.assertRaises(DuplicateFarmError):
            table.insert(farm(second))
        self.assertEqual(table.slot_views(), before)
        self.assertEqual((table.size, table.tombstones), (1, 1))

    def test_reinsertion_reuses_tombstone(self):
        table = HashTable()
        first, second = keys_at_home(table, 5, 2)
        table.insert(farm(first))
        table.insert(farm(second))
        table.delete(first)
        table.insert(farm(first))
        self.assertEqual(table.last_trace.slot, 5)
        self.assertEqual((table.size, table.tombstones, table.successful_insertions), (2, 0, 3))

    def test_missing_deletion_changes_no_slots_or_counts(self):
        table = HashTable()
        table.insert(farm("00001"))
        before = table.slot_views()
        self.assertIsNone(table.delete("zzzzz"))
        self.assertEqual(table.slot_views(), before)
        self.assertEqual((table.size, table.tombstones), (1, 0))

    def test_search_and_delete_validate_bad_ids(self):
        table = HashTable()
        for action in (table.search, table.delete):
            for key in ("bad", "UPPER", None, 12345):
                with self.assertRaises(RecordValidationError):
                    action(key)

    def test_load_factor_after_deletion_differs_from_occupied_load(self):
        table = HashTable()
        table.insert(farm("00001"))
        table.insert(farm("00002"))
        table.delete("00001")
        self.assertAlmostEqual(table.load_factor, 1 / 11)
        self.assertAlmostEqual(table.occupied_factor, 2 / 11)

    def test_growth_occurs_before_threshold_is_crossed(self):
        table = HashTable()
        for number in range(8):
            table.insert(farm(format(number, "05x")))
        self.assertEqual((table.capacity, table.size), (23, 8))
        self.assertEqual((table.last_resize.old_capacity, table.last_resize.records_moved), (11, 7))
        self.assertEqual(table.last_resize.insertion_number, 8)
        for number in range(8):
            self.assertIsNotNone(table.search(format(number, "05x")))

    def test_load_samples_are_only_every_ten_successful_user_insertions(self):
        table = HashTable()
        samples = LinkedList()
        for number in range(25):
            table.insert(farm(format(number, "05x")))
            if table.last_load_sample:
                samples.append(table.last_load_sample)
        self.assertEqual(LinkedList((sample.successful_insertions for sample in samples)), LinkedList((10, 20)))
        self.assertEqual(table.successful_insertions, 25)
        self.assertEqual(LinkedList((sample.capacity for sample in samples)), LinkedList((23, 47)))

    def test_tombstone_cleanup_at_same_capacity(self):
        table = HashTable()
        # Seven separate home slots occupy 7/11. Delete three of them.
        keys = LinkedList((keys_at_home(table, home, 1)[0] for home in range(10)))
        for key in keys[:7]:
            table.insert(farm(key))
        for key in keys[:3]:
            table.delete(key)
        # The 0.85 occupied threshold avoids expensive immediate cleanup.
        for key in keys[7:9]:
            table.insert(farm(key))
            self.assertIsNone(table.last_resize)
        table.insert(farm(keys[9]))
        event = table.last_resize
        self.assertIsNotNone(event)
        self.assertEqual((event.old_capacity, event.new_capacity, event.tombstones_removed), (11, 11, 3))
        self.assertEqual((table.size, table.tombstones), (7, 0))
        for key in keys[3:]:
            self.assertIsNotNone(table.search(key))

    def test_growth_omits_deleted_records(self):
        table = HashTable()
        for number in range(7):
            table.insert(farm(format(number, "05x")))
        table.delete("00000")
        for number in range(7, 10):
            table.insert(farm(format(number, "05x")))
        self.assertGreater(table.capacity, 11)
        self.assertIsNone(table.search("00000"))
        self.assertEqual(table.size, 9)

    def test_arbitrary_valid_threshold_keeps_projected_load_bounded(self):
        table = HashTable(max_load=0.10)
        for number in range(20):
            table.insert(farm(format(number, "05x")))
            self.assertLessEqual(table.load_factor, 0.10)

    def test_latest_diagnostic_records_are_immutable(self):
        table = HashTable()
        table.insert(farm("00001"))
        with self.assertRaises(FrozenInstanceError):
            table.last_trace.result = "BAD"
        self.assertIsInstance(table.slot_views(), tuple)

    def test_seeded_mixed_operations_against_manual_sequence_oracle(self):
        rng = random.Random(23857030)
        table = HashTable()
        pool = LinkedList((farm(format(number, "05x")) for number in range(60)))
        model = LinkedList()
        for step in range(1000):
            record = rng.choice(pool)
            expected = None
            for item in model:
                if item.farm_id == record.farm_id:
                    expected = item
                    break
            action = rng.randrange(3)
            if action == 0:
                if expected is None:
                    table.insert(record)
                    model.append(record)
                else:
                    with self.assertRaises(DuplicateFarmError):
                        table.insert(record)
            elif action == 1:
                self.assertEqual(table.search(record.farm_id), expected)
            else:
                self.assertEqual(table.delete(record.farm_id), expected)
                if expected is not None:
                    model[:] = LinkedList((item for item in model if item is not expected))
            self.assertEqual(table.size, len(model))
            self.assertLessEqual(table.load_factor, 0.70)
            self.assertLessEqual(table.occupied_factor, table.max_occupied)
            self.assertEqual(sum(view.state == "OCCUPIED" for view in table.slot_views()), len(model))
            if step % 25 == 0:
                for candidate in pool:
                    expected = None
                    for item in model:
                        if item.farm_id == candidate.farm_id:
                            expected = item
                            break
                    self.assertEqual(table.search(candidate.farm_id), expected)


if __name__ == "__main__":
    unittest.main()
