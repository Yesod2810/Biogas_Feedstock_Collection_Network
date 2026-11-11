"""Author: Thanh Dat Nguyen
Student ID: 23857030
Date: 4/10/2026
Purpose: Cross-module retrieval, stale/deleted farms, modelled request
data and CLI tests.
"""

from manual_structures import LinkedList, manual_all, manual_any, manual_count, manual_map
from test_support import SequenceTestCase


import csv
from dataclasses import replace
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from module1_graph.data_loader import DEFAULT_DATA_DIR, HUB_ID, PROJECT_ROOT, load_network
from module1_graph.graph import Graph, Location
from module2_hash.data_loader import load_lookup
from module3_heap.data_loader import RequestDataError, read_requests
from module3_heap.requests import RequestValidationError
from module3_heap.scheduler import CollectionScheduler, SchedulingError
from module3_heap.test_driver import run_demo


class SchedulerTests(SequenceTestCase):
    def setUp(self):
        self.lookup = load_lookup().table
        self.graph = load_network()
        self.scheduler = CollectionScheduler(self.lookup, self.graph, emit=None)

    def test_submission_calls_actual_hash_lookup_and_dijkstra(self):
        search_patch = patch.object(self.lookup, "search", wraps=self.lookup.search)
        route_patch = patch.object(self.graph, "dijkstra", wraps=self.graph.dijkstra)
        with search_patch as search, route_patch as dijkstra:
            item = self.scheduler.submit("R1", "doj25", 11)
        search.assert_called_once_with("doj25")
        dijkstra.assert_called_once_with("doj25", HUB_ID)
        self.assertEqual((item.transport_minutes, item.priority), (10, 1))
        self.assertEqual(len(item.farm.fields()), 20)
        self.assertEqual(item.path[-1], HUB_ID)

    def test_ten_real_requests_produce_expected_stable_collection_order(self):
        for raw in read_requests():
            self.scheduler.submit(raw.request_id, raw.farm_id, raw.estimated_feedstock)
        order = LinkedList((self.scheduler.extract_priority().request_id for _ in range(10)))
        self.assertEqual(order, LinkedList(("C001", "C004", "C003", "C008", "C002", "C006", "C007", "C009", "C010", "C005")))

    def test_unreachable_farm_is_not_queued(self):
        with self.assertRaisesRegex(SchedulingError, "Unreachable"):
            self.scheduler.submit("R1", "gslqa", 5)
        self.assertEqual(self.scheduler.heap.size, 0)

    def test_missing_hash_record_is_not_queued(self):
        with self.assertRaisesRegex(SchedulingError, "missing"):
            self.scheduler.submit("R1", "zzzzz", 5)

    def test_deleted_hash_record_is_rejected_before_insertion(self):
        self.lookup.delete("doj25")
        with self.assertRaisesRegex(SchedulingError, "deleted"):
            self.scheduler.submit("R1", "doj25", 5)

    def test_deleted_highest_request_peek_does_not_remove_it(self):
        self.scheduler.submit("R1", "doj25", 11)
        self.lookup.delete("doj25")
        before = self.scheduler.heap.snapshot()
        with self.assertRaisesRegex(SchedulingError, "stale"):
            self.scheduler.peek()
        self.assertEqual(self.scheduler.heap.snapshot(), before)

    def test_extraction_skips_deleted_root_and_returns_eligible_survivor(self):
        self.scheduler.submit("R1", "doj25", 11)
        self.scheduler.submit("R2", "c96c9", 1)
        self.lookup.delete("doj25")
        self.assertEqual(self.scheduler.extract_priority().request_id, "R2")
        self.assertEqual(self.scheduler.last_skipped[0][0], "R1")
        self.assertEqual(self.scheduler.collected_count, 1)
        self.assertEqual(self.scheduler.heap.extractions, 2)

    def test_all_deleted_requests_are_skipped_until_empty(self):
        self.scheduler.submit("R1", "doj25", 11)
        self.scheduler.submit("R2", "c96c9", 1)
        self.lookup.delete("doj25")
        self.lookup.delete("c96c9")
        self.assertIsNone(self.scheduler.extract_priority())
        self.assertEqual(len(self.scheduler.last_skipped), 2)
        self.assertEqual(self.scheduler.collected_count, 0)

    def test_changed_farm_information_is_not_dispatched_from_old_snapshot(self):
        self.scheduler.submit("R1", "doj25", 11)
        original = self.lookup.delete("doj25")
        self.lookup.insert(replace(original, name="Updated unit-test record"))
        self.assertIsNone(self.scheduler.extract_priority())
        self.assertIn("changed", self.scheduler.last_skipped[0][2])

    def test_duplicate_request_id_is_rejected_while_queued(self):
        self.scheduler.submit("R1", "doj25", 11)
        with self.assertRaisesRegex(SchedulingError, "Duplicate"):
            self.scheduler.submit("R1", "c96c9", 20)
        self.assertEqual(self.scheduler.heap.size, 1)

    def test_same_farm_cannot_have_two_pending_requests(self):
        self.scheduler.submit("R1", "doj25", 11)
        with self.assertRaisesRegex(SchedulingError, "pending"):
            self.scheduler.submit("R2", "doj25", 22)

    def test_processed_request_id_cannot_be_replayed(self):
        self.scheduler.submit("R1", "doj25", 11)
        self.scheduler.extract_priority()
        with self.assertRaisesRegex(SchedulingError, "Duplicate"):
            self.scheduler.submit("R1", "doj25", 11)

    def test_new_request_id_for_collected_farm_is_allowed(self):
        self.scheduler.submit("R1", "doj25", 11)
        self.scheduler.extract_priority()
        self.scheduler.submit("R2", "doj25", 22)
        self.assertEqual(self.scheduler.peek().request_id, "R2")

    def test_rejected_request_does_not_consume_its_identifier(self):
        with self.assertRaises(SchedulingError):
            self.scheduler.submit("R1", "gslqa", 5)
        self.scheduler.submit("R1", "doj25", 5)
        self.assertEqual(self.scheduler.heap.size, 1)

    def test_farm_absent_from_selected_graph(self):
        with self.assertRaisesRegex(SchedulingError, "not in the selected graph"):
            self.scheduler.submit("R1", "3d8af", 5)

    def test_hash_and_graph_coordinate_mismatch(self):
        graph = Graph()
        graph.add_vertex(self.graph.location(HUB_ID))
        graph.add_vertex(Location("doj25", "Unit-test mismatched location", -30, 115))
        graph.add_edge("doj25", HUB_ID, 5)
        scheduler = CollectionScheduler(self.lookup, graph, emit=None)
        with self.assertRaisesRegex(SchedulingError, "coordinates disagree"):
            scheduler.submit("R1", "doj25", 5)

    def test_zero_time_uses_dijkstra_source_equal_to_configured_hub(self):
        graph = Graph()
        graph.add_vertex(self.graph.location("doj25"))
        scheduler = CollectionScheduler(self.lookup, graph, hub_id="doj25", emit=None)
        item = scheduler.submit("R1", "doj25", 5)
        self.assertEqual((item.transport_minutes, item.priority, item.path), (0, 5, ("doj25",)))

    def test_empty_scheduler_peek_and_extract(self):
        self.assertIsNone(self.scheduler.peek())
        self.assertIsNone(self.scheduler.extract_priority())

    def test_network_changes_block_old_priorities_until_reset(self):
        self.scheduler.submit("R1", "doj25", 11)
        self.graph.add_vertex(Location("EXTRA", "Unit-test location"))
        for action in (self.scheduler.peek, self.scheduler.extract_priority,
                       lambda: self.scheduler.submit("R2", "c96c9", 8)):
            with self.assertRaisesRegex(SchedulingError, "Network changed"):
                action()
        self.assertEqual(self.scheduler.heap.size, 1)
        fresh = CollectionScheduler(self.lookup, self.graph, emit=None)
        fresh.submit("R1", "doj25", 11)
        self.assertIsNotNone(fresh.peek())

    def test_rebinding_after_hash_reload_uses_new_index(self):
        self.scheduler.submit("R1", "doj25", 11)
        other = load_lookup().table
        other.delete("doj25")
        self.scheduler.rebind_lookup(other)
        self.assertIsNone(self.scheduler.extract_priority())

    def test_invalid_module_instances_or_missing_hub(self):
        with self.assertRaises(SchedulingError):
            CollectionScheduler(manual_map(), self.graph, emit=None)
        with self.assertRaises(SchedulingError):
            CollectionScheduler(self.lookup, Graph(), emit=None)

    def test_full_network_routes_are_computed_separately(self):
        scheduler = CollectionScheduler(self.lookup, load_network("full"), emit=None)
        item = scheduler.submit("R1", "f4386", 27.5)
        self.assertEqual(item.transport_minutes, 53)
        self.assertEqual(item.priority, 27.5 / 54)


class DataAndDriverTests(SequenceTestCase):
    def test_main_data_contains_ten_real_farms_without_manual_priorities(self):
        raw = read_requests()
        lookup = load_lookup().table
        self.assertEqual(len(raw), 10)
        self.assertTrue(manual_all(lookup.search(row.farm_id) is not None for row in raw))
        self.assertTrue(manual_all(float(row.estimated_feedstock) > 0 for row in raw))

    def test_request_parser_rejects_malformed_schema_and_manual_priority(self):
        values = ("", "RequestID,FarmID\nR1,doj25\n",
            "RequestID,FarmID,EstimatedFeedstock,Unit\nR1,doj25,5\n",
            "RequestID,FarmID,EstimatedFeedstock,Unit\nR1,doj25,5,kg\n",
            "RequestID,FarmID,EstimatedFeedstock,Unit,Priority\nR1,doj25,5,tonnes,999\n")
        for text in values:
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "invalid.csv"
                path.write_text(text, encoding="utf-8")
                with self.assertRaises(RequestDataError):
                    read_requests(path)

    def test_missing_request_file_is_actionable(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(RequestDataError, "Cannot read"):
                read_requests(Path(directory) / "missing.csv")

    def test_driver_meets_insert_extract_trace_and_edge_case_requirements(self):
        text, evidence = run_demo()
        self.assertEqual((evidence["main_insertions"], evidence["main_extractions"]), (10, 10))
        states = evidence["main_heap_states"]
        self.assertEqual(sum(row["operation"] == "INSERT" for row in states), 10)
        self.assertEqual(sum(row["operation"] == "EXTRACT" for row in states), 10)
        self.assertEqual(len(evidence["rejections"]), 10)
        self.assertEqual(evidence["zero_time_fixture"]["TransportTime"], 0)
        self.assertTrue(evidence["deleted_before_insert_rejected"])
        self.assertTrue(evidence["deleted_after_queue_skipped"])
        self.assertIn("HEAP after INSERT C010", text)
        self.assertIn("RESULTING COLLECTION ORDER", text)

    def test_driver_works_with_full_network(self):
        text, evidence = run_demo("full")
        self.assertEqual(evidence["main_collected"], 10)
        self.assertEqual(evidence["network"], "full")


class HeapMenuTests(SequenceTestCase):
    def run_app(self, args=(), inputs=None, cwd=None):
        return subprocess.run(LinkedList((sys.executable, str(PROJECT_ROOT / "interactive_menu.py"), *args)), input=inputs, capture_output=True, text=True, cwd=cwd or PROJECT_ROOT, timeout=120)

    def test_heap_demo_runs_from_another_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            result = self.run_app(("--module", "heap", "--demo"), cwd=directory)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("HEAP after INSERT C010", result.stdout)
        self.assertIn("ZERO-TIME", result.stdout)

    def test_heap_validation_cli(self):
        result = self.run_app(("--module", "heap", "--validate"))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(manual_count(result.stdout, "PASS:"), 5)

    def test_load_peek_extract_and_drain_menu(self):
        result = self.run_app(("--module", "heap"), "1\n3\n4\n5\n4\n0\n")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Accepted 10 requests", result.stdout)
        self.assertIn("PEEK (heap unchanged)", result.stdout)
        self.assertIn("COLLECT C001", result.stdout)
        self.assertIn("Empty heap", result.stdout)

    def test_invalid_request_inputs_and_unreachable_farm_recover(self):
        result = self.run_app(("--module", "heap"),
            "bad\n2\nR1\nBAD_ID\n5\n2\nR2\ndoj25\n-3\n2\nR3\ngslqa\n5\n3\n0\n")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Invalid scheduling option", result.stdout)
        self.assertIn("Invalid FarmID", result.stdout)
        self.assertIn("greater than zero", result.stdout)
        self.assertIn("Unreachable", result.stdout)
        self.assertNotIn("Traceback", result.stderr)

    def test_shared_hash_deletion_affects_queued_requests_across_root_menus(self):
        result = self.run_app(inputs="11\n1\n0\n10\n4\ndoj25\n0\n11\n3\n4\n0\n0\n")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Deleted doj25", result.stdout)
        self.assertIn("Highest request C001 is stale", result.stdout)
        self.assertIn("SKIP C001", result.stdout)
        self.assertIn("COLLECT C004", result.stdout)

    def test_hash_reload_rebinds_the_existing_scheduling_session(self):
        result = self.run_app(inputs="11\n1\n0\n10\n4\ndoj25\n7\n0\n11\n3\n0\n0\n")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("PEEK (heap unchanged): PRIORITY C001", result.stdout)

    def test_heap_reset_clears_duplicate_request_history(self):
        result = self.run_app(("--module", "heap"), "1\n7\n1\n0\n")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(manual_count(result.stdout, "Accepted 10 requests"), 2)

    def test_eof_exits_cleanly(self):
        result = self.run_app(("--module", "heap"), "")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Input ended", result.stdout)

    def test_missing_data_returns_nonzero_without_traceback(self):
        with tempfile.TemporaryDirectory() as directory:
            result = self.run_app(("--module", "heap", "--data-dir", directory))
        self.assertEqual(result.returncode, 1)
        self.assertIn("Cannot read", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_standalone_driver_cli(self):
        result = subprocess.run(LinkedList((sys.executable, "-m", "module3_heap.test_driver")),
            cwd=PROJECT_ROOT, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("RESULTING COLLECTION ORDER", result.stdout)


if __name__ == "__main__":
    unittest.main()
