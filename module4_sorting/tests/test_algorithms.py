"""Author: Thanh Dat Nguyen
Student ID: 23857030
Date: 12/10/2026
Purpose: manual insertion-sort is used ONLY here as an independent test oracle.
"""

from manual_structures import LinkedList, object_array
from test_support import SequenceTestCase

from math import ceil, log2
from random import Random
import unittest

from module4_sorting.algorithms import (SortMetrics, is_sorted, merge_sort,
                                     quick_sort, quick_sort_in_place)
from module4_sorting.benchmark import median


def independent_insertion_order(items):
    """Manual independent oracle; test code never delegates sorting."""
    result = object_array(items)
    for right in range(1, len(result)):
        value = result[right]
        left = right - 1
        while left >= 0 and result[left][1] > value[1]:
            result[left + 1] = result[left]
            left -= 1
        result[left + 1] = value
    return result


class SortingAlgorithmTests(SequenceTestCase):
    def check_sorts(self, values):
        expected = independent_insertion_order(values)
        for sorter in (merge_sort, quick_sort):
            with self.subTest(sorter=sorter.__name__):
                before = LinkedList(values)
                result = sorter(values, key=lambda item: item[1])
                self.assertEqual(LinkedList((item[1] for item in result)), LinkedList((item[1] for item in expected)))
                self.assertCountEqual(result, expected)
                self.assertEqual(values, before)
                self.assertIsNot(result, values)

    def test_empty_input(self):
        self.check_sorts(LinkedList())

    def test_single_record(self):
        self.check_sorts(LinkedList((('A', 0),)))

    def test_two_records_in_both_orders(self):
        self.check_sorts(LinkedList((('A', 2), ('B', 1))))
        self.check_sorts(LinkedList((('A', 1), ('B', 2))))

    def test_all_equal_keys(self):
        self.check_sorts(LinkedList(((str(i), 5) for i in range(100))))

    def test_ascending_unique_keys(self):
        self.check_sorts(LinkedList(((str(i), i) for i in range(1000))))

    def test_reversed_unique_keys(self):
        self.check_sorts(LinkedList(((str(i), 1000-i) for i in range(1000))))

    def test_duplicates_and_zero_time(self):
        self.check_sorts(LinkedList((('A', 0), ('B', 4), ('C', 4), ('D', 2), ('E', 0), ('F', 2))))

    def test_fractional_times(self):
        self.check_sorts(LinkedList((('A', 2.5), ('B', .25), ('C', 1.75), ('D', 0))))

    def test_seeded_oracle_across_many_lengths(self):
        rng = Random(23857030)
        for length in (3, 5, 7, 10, 31, 64, 99, 100, 500, 1000):
            with self.subTest(length=length):
                self.check_sorts(LinkedList(((str(i), rng.randrange(150)) for i in range(length))))

    def test_merge_sort_preserves_equal_key_order(self):
        values = LinkedList(((str(i), i % 5) for i in range(200)))
        self.assertEqual(merge_sort(values, key=lambda item: item[1]), independent_insertion_order(values))

    def test_quick_sort_instability_has_a_concrete_witness(self):
        values = LinkedList((('A', 2), ('B', 2), ('C', 1)))
        self.assertEqual(quick_sort(values, key=lambda item: item[1]), LinkedList((('C', 1), ('B', 2), ('A', 2))))

    def test_in_place_api_mutates_and_returns_the_same_array(self):
        values = object_array((5, 2, 4, 1, 3))
        self.assertIs(quick_sort_in_place(values, key=lambda value: value), values)
        self.assertEqual(values, LinkedList((1, 2, 3, 4, 5)))

    def test_in_place_api_rejects_non_array(self):
        with self.assertRaises(TypeError):
            quick_sort_in_place((1, 2, 3))

    def test_merge_accepts_an_iterator(self):
        self.assertEqual(merge_sort(iter(LinkedList((3, 1, 2))), key=lambda value: value), LinkedList((1, 2, 3)))

    def test_quick_accepts_an_iterator(self):
        self.assertEqual(quick_sort(iter(LinkedList((3, 1, 2))), key=lambda value: value), LinkedList((1, 2, 3)))

    def test_all_equal_quick_input_finishes_in_one_partition(self):
        metrics = SortMetrics()
        values = quick_sort(LinkedList((7,)) * 1000, key=lambda value: value, metrics=metrics)
        self.assertEqual(values, LinkedList((7,)) * 1000)
        self.assertEqual(metrics.partitions, 1)
        self.assertLess(metrics.comparisons, 2100)

    def test_quick_uses_bounded_stack_without_recursion(self):
        values = LinkedList(range(5000))
        metrics = SortMetrics()
        self.assertEqual(quick_sort(values, key=lambda value: value, metrics=metrics), values)
        self.assertLessEqual(metrics.max_pending_ranges, ceil(log2(len(values))))

    def test_metrics_do_not_change_either_result(self):
        for sorter in (merge_sort, quick_sort):
            metrics = SortMetrics()
            self.assertEqual(sorter(LinkedList((3, 5, 2, 1)), key=lambda value: value, metrics=metrics), LinkedList((1, 2, 3, 5)))
            self.assertGreater(metrics.comparisons, 0)

    def test_sort_check_accepts_ties_and_rejects_descent(self):
        self.assertTrue(is_sorted(LinkedList((1, 1, 2)), key=lambda value: value))
        self.assertFalse(is_sorted(LinkedList((2, 1)), key=lambda value: value))

    def test_manual_median_for_odd_even_and_empty_samples(self):
        self.assertEqual(median(LinkedList((4, 1, 3))), 3)
        self.assertEqual(median(LinkedList((4, 1, 3, 2))), 2.5)
        with self.assertRaises(ValueError):
            median(LinkedList())


if __name__ == '__main__':
    unittest.main()
