"""Author: Thanh Dat Nguyen
Student ID: 23857030
Date: 17/10/2026
Purpose: Check shared state, real algorithm calls, persistence and integration entry points.
"""

from manual_structures import LinkedList, ManualSet, manual_all, manual_count
from test_support import SequenceTestCase


from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from integration_demo import run_integration_demo
from module1_graph.data_loader import PROJECT_ROOT
from module1_graph.graph import Graph
from module2_hash.hash_table import HashTable
from module4_sorting.algorithms import merge_sort, quick_sort
from module4_sorting.database import CollectionDatabase
from module4_sorting.records import read_records


class FourModuleIntegrationTests(SequenceTestCase):
    def test_shared_instances_and_ten_requests_flow_through_all_four_modules(self):
        text, evidence = run_integration_demo()
        self.assertTrue(manual_all(evidence['checks'].values()))
        self.assertTrue(evidence['checks']['same_hash_graph_and_archive_instances'])
        self.assertEqual((evidence['heap_insertions'], evidence['heap_extractions']), (10, 10))
        self.assertEqual(evidence['statuses']['collected'], 10)
        self.assertEqual(evidence['collection_order'][:5], LinkedList(('C001', 'C004', 'C003', 'C008', 'C002')))
        self.assertEqual(evidence['archive_request_order'][:5], LinkedList(('C001', 'C002', 'C003', 'C004', 'C005')))
        self.assertIn('HEAP after INSERT C010', text)
        self.assertIn('ARCHIVE ORDER BY TRANSPORT TIME', text)

    def test_flow_calls_real_hash_dijkstra_and_both_manual_sorts(self):
        searches, routes = LinkedList(), LinkedList()
        original_search, original_dijkstra = HashTable.search, Graph.dijkstra
        def search(table, farm_id):
            searches.append(farm_id)
            return original_search(table, farm_id)
        def dijkstra(graph, source, destination):
            routes.append((source, destination))
            return original_dijkstra(graph, source, destination)
        merge_patch = patch('integration_demo.merge_sort', wraps=merge_sort)
        quick_patch = patch('integration_demo.quick_sort', wraps=quick_sort)
        with patch.object(HashTable, 'search', search), patch.object(Graph, 'dijkstra', dijkstra), \
                merge_patch as merge, quick_patch as quick:
            text, evidence = run_integration_demo()
        self.assertEqual(len(routes), 10)
        self.assertGreaterEqual(len(searches), 20)
        self.assertEqual(ManualSet((row['FarmID'] for row in evidence['accepted_requests'])), ManualSet((r[0] for r in routes)))
        merge.assert_called_once()
        quick.assert_called_once()

    def test_shared_hash_deletion_skips_dispatch_and_preserves_the_snapshot(self):
        text, evidence = run_integration_demo(delete_farm_id='doj25')
        self.assertEqual(evidence['shared_hash_records_final'], 124)
        self.assertEqual(evidence['skipped_requests'], LinkedList(('C001',)))
        self.assertEqual((evidence['archive_count'], evidence['statuses']['collected']), (10, 9))
        self.assertEqual(evidence['statuses']['skipped'], 1)
        self.assertIn('C001 | doj25 | T=10 min | skipped', text)

    def test_full_graph_recalculates_the_transport_time(self):
        text, evidence = run_integration_demo(mode='full')
        request = None
        for candidate in evidence['accepted_requests']:
            if candidate['FarmID'] == 'f4386':
                request = candidate
                break
        self.assertIsNotNone(request)
        self.assertEqual((evidence['vertices'], evidence['edges']), (126, 254))
        self.assertEqual(request['TransportTime'], 53)
        self.assertEqual(request['CollectionPriority'], 27.5 / 54)

    def test_exports_round_trip_without_duplicating_rows_or_clearing_the_live_archive(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory)
            normal = destination / 'collection_records.sqlite3'
            database = CollectionDatabase(normal)
            database.close()
            original_bytes = normal.read_bytes()
            for _ in range(2):
                text, evidence = run_integration_demo(output_dir=destination)
            csv_records = read_records(destination / 'integration_records_sorted.csv')
            stored = CollectionDatabase(destination / 'integration_records.sqlite3')
            try:
                self.assertEqual(stored.records(), csv_records)
            finally:
                stored.close()
            self.assertEqual(len(csv_records), 10)
            self.assertEqual(normal.read_bytes(), original_bytes)

    def test_integrated_flag_runs_from_a_different_working_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run(LinkedList((sys.executable, str(PROJECT_ROOT / 'interactive_menu.py'), '--integrated-demo', '--output-dir', directory)), cwd=directory,
                capture_output=True, text=True, timeout=30)
            self.assertTrue((Path(directory) / 'integration/integration_validation.json').is_file())
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(manual_count(result.stdout, 'PASS:'), 8)

    def test_menu_demo_preserves_the_active_scheduling_session(self):
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run(LinkedList((sys.executable, str(PROJECT_ROOT / 'interactive_menu.py'), '--output-dir', directory)), input='11\n1\n0\n13\n11\n3\n0\n0\n',
                capture_output=True, text=True, timeout=30)
            live = CollectionDatabase(Path(directory) / 'collection_records.sqlite3')
            fresh = CollectionDatabase(Path(directory) / 'integration/integration_records.sqlite3')
            try:
                self.assertTrue(manual_all(record.status == 'cancelled' for record in live.records()))
                self.assertTrue(manual_all(record.status == 'collected' for record in fresh.records()))
                self.assertEqual(len(live.records()), 10)
            finally:
                live.close()
                fresh.close()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('PEEK (heap unchanged): PRIORITY C001', result.stdout)

    def test_invalid_data_and_delete_id_are_actionable_cli_errors(self):
        with tempfile.TemporaryDirectory() as directory:
            for arguments in (('--data-dir', directory), ('--delete-farm', 'BAD_ID')):
                result = subprocess.run(LinkedList((sys.executable, str(PROJECT_ROOT / 'integration_demo.py'), *arguments, '--output-dir', directory)), capture_output=True, text=True, timeout=30)
                self.assertEqual(result.returncode, 1)
                self.assertIn('Error:', result.stderr)
                self.assertNotIn('Traceback', result.stderr)


if __name__ == '__main__':
    unittest.main()
