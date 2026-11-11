"""Author: Thanh Dat Nguyen
Student ID: 23857030
Date: 4/10/2026
Purpose: Manual-heap correctness and independently checked numeric priorities.
"""

from manual_structures import LinkedList, manual_all, manual_any, manual_contains, manual_max
from test_support import SequenceTestCase


import ast
import contextlib
from dataclasses import FrozenInstanceError
import io
from pathlib import Path
import random
import unittest

from module2_hash.records import FarmRecord
from module3_heap.max_heap import HeapError, MaxHeap
from module3_heap.requests import RequestValidationError, ScheduledRequest, calculate_priority


def farm():
    return FarmRecord("00001", "Synthetic unit-test farm", "Pigs", -32, 116,
                      "", "", "", "WA", "", "Australia")


def request(request_id, quantity, minutes=0):
    return ScheduledRequest(request_id, farm(), quantity, minutes, ("00001",))


class PriorityTests(SequenceTestCase):
    def test_known_calculation(self):
        self.assertEqual(calculate_priority(11, 10), 1)
        self.assertEqual(calculate_priority(15, 19), 0.75)

    def test_zero_time_has_finite_priority(self):
        self.assertEqual(calculate_priority(5, 0), 5)

    def test_more_feedstock_increases_priority(self):
        self.assertGreater(calculate_priority(20, 30), calculate_priority(10, 30))

    def test_more_time_reduces_priority_including_below_one_minute(self):
        self.assertGreater(calculate_priority(5, 0), calculate_priority(5, 0.5))
        self.assertGreater(calculate_priority(5, 0.5), calculate_priority(5, 10))

    def test_numerical_csv_values_are_accepted(self):
        self.assertEqual(calculate_priority("15.5", "30"), 0.5)

    def test_invalid_feedstock_is_rejected(self):
        for quantity in (0, -1, "", "many", None, True, LinkedList(), float("inf"), float("nan"), 10 ** 1000):
            with self.subTest(quantity=repr(quantity)[:20]):
                with self.assertRaises(RequestValidationError):
                    calculate_priority(quantity, 10)

    def test_invalid_transport_time_is_rejected(self):
        for minutes in (-1, "", "bad", None, True, float("inf"), float("nan")):
            with self.assertRaises(RequestValidationError):
                calculate_priority(5, minutes)

    def test_numeric_underflow_is_rejected(self):
        with self.assertRaises(RequestValidationError):
            calculate_priority(5e-324, 1e300)

    def test_priority_is_calculated_and_cannot_be_supplied(self):
        self.assertEqual(request("R1", 11, 10).priority, 1)
        with self.assertRaises(TypeError):
            ScheduledRequest("R1", farm(), 11, 10, ("00001",), priority=999)

    def test_immutable_scheduled_request(self):
        with self.assertRaises(FrozenInstanceError):
            request("R1", 5).priority = 99

    def test_invalid_request_ids_paths_and_record_types(self):
        for request_id in ("", "bad id", "a" * 33, None, "réq"):
            with self.assertRaises(RequestValidationError):
                request(request_id, 5)
        for route in ((), LinkedList(), ("wrong",), ("00001", "")):
            with self.assertRaises(RequestValidationError):
                ScheduledRequest("R1", farm(), 5, 0, route)
        with self.assertRaises(RequestValidationError):
            ScheduledRequest("R1", None, 5, 0, ("00001",))


class HeapTests(SequenceTestCase):
    def test_no_ready_made_heap_or_sorting_algorithm_in_core(self):
        path = Path(__file__).resolve().parents[1] / "max_heap.py"
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imports = LinkedList((node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)))
        imports += LinkedList((alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names))
        self.assertFalse(manual_any(manual_contains(("heapq", "queue"), name) for name in imports))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                self.assertFalse(isinstance(node.func, ast.Name) and node.func.id == "sorted")
                self.assertFalse(isinstance(node.func, ast.Attribute) and node.func.attr == "sort")

    def test_empty_operations_are_safe(self):
        heap = MaxHeap(emit=None)
        self.assertIsNone(heap.peek())
        self.assertIsNone(heap.extract_priority())
        self.assertEqual(heap.snapshot(), ())
        self.assertEqual(heap.extractions, 0)

    def test_singleton_insert_peek_extract(self):
        heap = MaxHeap(emit=None)
        item = request("R1", 5)
        heap.insert(item)
        self.assertIs(heap.peek(), item)
        self.assertIs(heap.extract_priority(), item)
        self.assertEqual(heap.size, 0)

    def test_upward_percolation_can_cross_multiple_levels(self):
        heap = MaxHeap(emit=None)
        for number in range(1, 5):
            heap.insert(request("R" + str(number), number))
        self.assertEqual(heap.peek().priority, 4)
        self.assertEqual(len(heap.last_swaps), 2)
        self.assertTrue(heap.is_valid())

    def test_downward_percolation_selects_higher_right_child(self):
        heap = MaxHeap(emit=None)
        for number in (8, 4, 7, 3, 2, 6, 5):
            heap.insert(request("R" + str(number), number))
        self.assertEqual(heap.extract_priority().priority, 8)
        self.assertEqual(heap.last_swaps, ((0, 2), (2, 5)))
        self.assertEqual(heap.peek().priority, 7)
        self.assertTrue(heap.is_valid())

    def test_only_left_child_after_extraction(self):
        heap = MaxHeap(emit=None)
        for number in (3, 2, 1):
            heap.insert(request("R" + str(number), number))
        heap.extract_priority()
        self.assertEqual(heap.peek().priority, 2)
        self.assertTrue(heap.is_valid())

    def test_equal_priorities_are_fifo(self):
        heap = MaxHeap(emit=None)
        for request_id in ("Z", "A", "M"):
            heap.insert(request(request_id, 5))
        self.assertEqual(LinkedList((heap.extract_priority().request_id for _ in range(3))), LinkedList(("Z", "A", "M")))

    def test_comparisons_use_full_precision(self):
        heap = MaxHeap(emit=None)
        heap.insert(request("EARLY", 1))
        heap.insert(request("LATER", 1.0000000001))
        self.assertEqual(heap.peek().request_id, "LATER")

    def test_peek_preserves_array_and_counts(self):
        heap = MaxHeap(emit=None)
        heap.insert(request("R1", 1))
        heap.insert(request("R2", 2))
        before = heap.snapshot()
        heap.peek()
        heap.peek()
        self.assertEqual(heap.snapshot(), before)
        self.assertEqual((heap.insertions, heap.extractions), (2, 0))

    def test_duplicate_queued_id_is_atomic(self):
        heap = MaxHeap(emit=None)
        heap.insert(request("R1", 1))
        before = heap.snapshot()
        with self.assertRaises(HeapError):
            heap.insert(request("R1", 100))
        self.assertEqual(heap.snapshot(), before)
        self.assertEqual(heap.insertions, 1)

    def test_invalid_insert_does_not_change_heap(self):
        heap = MaxHeap(emit=None)
        for invalid in (None, "R1", 7):
            with self.assertRaises(HeapError):
                heap.insert(invalid)
        self.assertEqual(heap.size, 0)

    def test_required_array_prints_after_every_mutation(self):
        messages = LinkedList()
        heap = MaxHeap(emit=messages.append)
        heap.insert(request("R1", 1))
        heap.insert(request("R2", 2))
        heap.peek()
        heap.extract_priority()
        heap.extract_priority()
        self.assertEqual(len(messages), 4)
        self.assertIn("HEAP after INSERT R1", messages[0])
        self.assertIn("HEAP after EXTRACT R2", messages[2])
        self.assertTrue(messages[-1].endswith("[]"))

    def test_default_output_prints_without_a_custom_collector(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            heap = MaxHeap()
            heap.insert(request("R1", 1))
            heap.extract_priority()
        self.assertIn("HEAP after INSERT", output.getvalue())
        self.assertIn("HEAP after EXTRACT", output.getvalue())

    def test_snapshot_is_an_immutable_tuple(self):
        heap = MaxHeap(emit=None)
        heap.insert(request("R1", 1))
        self.assertIsInstance(heap.snapshot(), tuple)

    def test_thousand_mixed_operations_match_independent_sequence_oracle(self):
        rng = random.Random(23857030)
        heap = MaxHeap(emit=None)
        model = LinkedList()
        next_number = 0
        for _ in range(1000):
            if not model or rng.random() < 0.58:
                item = request("R" + str(next_number), rng.randint(1, 30))
                heap.insert(item)
                model.append((item, next_number))
                next_number += 1
            else:
                expected = manual_max(model, key=lambda pair: (pair[0].priority, -pair[1]))
                self.assertEqual(heap.extract_priority(), expected[0])
                model[:] = LinkedList((item for item in model if item is not expected))
            self.assertEqual(heap.size, len(model))
            self.assertTrue(heap.is_valid())
            if model:
                expected = manual_max(model, key=lambda pair: (pair[0].priority, -pair[1]))[0]
                self.assertEqual(heap.peek(), expected)


if __name__ == "__main__":
    unittest.main()
