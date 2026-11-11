"""Author: Thanh Dat Nguyen
Student ID: 23857030
Date: 12/10/2026
Purpose: Tests for graph-derived modelled request data, persistence,
benchmarks and user-facing menus.
"""

from manual_structures import LinkedList, ManualSet, manual_all, manual_count, manual_map
from test_support import SequenceTestCase


from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from module1_graph.data_loader import PROJECT_ROOT, load_network
from module1_graph.graph import Graph
from module2_hash.data_loader import load_lookup
from module3_heap.scheduler import CollectionScheduler
from module4_sorting.algorithms import is_sorted, merge_sort
from module4_sorting.benchmark import run_benchmarks, verify_result
from module4_sorting.database import CollectionDatabase
from module4_sorting.datasets import CONDITIONS, SEED, SIZES, generate_records, make_condition
from module4_sorting.records import CollectionRecord, SortDataError, read_records, write_records
from module4_sorting.test_driver import run_demo


class IntegratedDatasetTests(SequenceTestCase):
    @classmethod
    def setUpClass(cls):
        cls.records, cls.metadata = generate_records()

    def test_thousand_unique_request_events_reuse_real_farms(self):
        self.assertEqual(len(self.records), 1000)
        self.assertEqual(len(ManualSet((r.record_id for r in self.records))), 1000)
        self.assertLess(len(ManualSet((r.request.farm_id for r in self.records))), 1000)
        self.assertTrue(manual_all(len(r.request.farm.fields()) == 20 for r in self.records))

    def test_every_time_and_path_matches_the_actual_dijkstra_cache(self):
        routes = manual_map(((row['FarmID'], row) for row in self.metadata['route_cache']))
        for record in self.records:
            route = routes[record.request.farm_id]
            self.assertEqual(record.transport_minutes, route['TransportTime'])
            self.assertEqual(record.request.path, tuple(route['Path']))
            self.assertEqual(record.request.priority, record.request.feedstock / (record.transport_minutes + 1))

    def test_generator_calls_real_dijkstra_for_all_125_farms(self):
        original = Graph.dijkstra
        calls = LinkedList()
        def observed(graph, source, target):
            calls.append((source, target))
            return original(graph, source, target)
        with patch.object(Graph, 'dijkstra', observed):
            records, metadata = generate_records(10)
        self.assertEqual(len(calls), 125)
        self.assertEqual(metadata['dijkstra_calls'], 125)

    def test_unreachable_farm_is_explicitly_excluded(self):
        self.assertEqual(self.metadata['excluded_unreachable'], LinkedList(('gslqa',)))
        self.assertEqual(self.metadata['reachable_farm_count'], 124)
        self.assertNotIn('gslqa', ManualSet((r.request.farm_id for r in self.records)))

    def test_seed_reproduces_records_and_arrangements(self):
        other, metadata = generate_records(1000, SEED)
        self.assertEqual(self.records, other)
        for condition in CONDITIONS:
            self.assertEqual(make_condition(self.records, condition), make_condition(other, condition))

    def test_different_seed_changes_the_modelled_requests(self):
        other, metadata = generate_records(10, SEED + 1)
        self.assertNotEqual(self.records[:10], other)

    def test_conditions_preserve_identical_multisets_at_each_size(self):
        for size in SIZES:
            for condition in CONDITIONS:
                arranged, metadata = make_condition(self.records[:size], condition, SEED + size)
                self.assertCountEqual(arranged, self.records[:size])

    def test_nearly_sorted_has_at_most_ten_percent_records_displaced(self):
        for size in SIZES:
            arranged, metadata = make_condition(self.records[:size], 'nearly_sorted')
            baseline = merge_sort(self.records[:size])
            actual = sum(a.record_id != b.record_id for a, b in zip(arranged, baseline))
            self.assertEqual(actual, metadata['displaced_records'])
            self.assertEqual(actual, size // 10)
            self.assertLessEqual(metadata['displaced_fraction'], .10)

    def test_reversed_condition_is_non_increasing(self):
        arranged, metadata = make_condition(self.records, 'reversed')
        self.assertTrue(manual_all(a.transport_minutes >= b.transport_minutes for a, b in zip(arranged, arranged[1:])))

    def test_bad_count_and_condition_are_rejected(self):
        for value in (-1, 1.5, True):
            with self.assertRaises(SortDataError):
                generate_records(value)
        with self.assertRaises(SortDataError):
            make_condition(LinkedList(), 'unsupported')

    def test_csv_round_trip_preserves_every_collection_and_farm_field(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'records.csv'
            write_records(path, self.records[:100])
            self.assertEqual(read_records(path), self.records[:100])

    def test_corrupted_priority_and_invalid_time_are_rejected(self):
        for column, value in (('CollectionPriority', '-1'), ('TransportTime', 'nan')):
            row = self.records[0].row()
            row[column] = value
            with self.assertRaises(SortDataError):
                CollectionRecord.from_row(row)

    def test_missing_csv_and_invalid_header_are_handled(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'data.csv'
            with self.assertRaises(SortDataError):
                read_records(path)
            path.write_text('bad,columns\n1,2\n')
            with self.assertRaises(SortDataError):
                read_records(path)

    def test_duplicate_record_ids_are_rejected_before_csv_write(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(SortDataError):
                write_records(Path(directory) / 'data.csv', LinkedList((self.records[0],)) * 2)


class DatabaseIntegrationTests(SequenceTestCase):
    def setUp(self):
        self.database = CollectionDatabase()
        self.scheduler = CollectionScheduler(load_lookup().table, load_network(), emit=None,
                                              archive=self.database.new_session())

    def tearDown(self):
        self.database.close()

    def test_live_submissions_are_persisted_in_ascending_time(self):
        self.scheduler.submit('R1', 'c81cd', 9)
        self.scheduler.submit('R2', 'doj25', 11)
        self.assertEqual(LinkedList((r.transport_minutes for r in self.database.records())), LinkedList((10, 30)))
        self.assertEqual(LinkedList((r.status for r in self.database.records())), LinkedList(('pending', 'pending')))

    def test_successful_collection_updates_history_without_removing_a_record(self):
        self.scheduler.submit('R1', 'doj25', 11)
        self.scheduler.extract_priority()
        records = self.database.records()
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].status, 'collected')

    def test_deleted_farm_snapshot_is_retained_as_skipped_history(self):
        self.scheduler.submit('R1', 'doj25', 11)
        self.scheduler.lookup.delete('doj25')
        self.scheduler.extract_priority()
        record = self.database.records()[0]
        self.assertEqual(record.status, 'skipped')
        self.assertEqual(record.request.farm.farm_id, 'doj25')
        self.assertIn('deleted', record.detail)

    def test_reset_cancellation_preserves_old_requests_and_allows_a_new_session(self):
        self.scheduler.submit('R1', 'doj25', 11)
        self.scheduler.cancel_pending()
        other = CollectionScheduler(load_lookup().table, load_network(), emit=None,
                                    archive=self.database.new_session())
        other.submit('R1', 'doj25', 5)
        records = self.database.records()
        self.assertEqual(len(records), 2)
        self.assertNotEqual(records[0].record_id, records[1].record_id)
        self.assertEqual(LinkedList((r.status for r in records)), LinkedList(('cancelled', 'pending')))

    def test_invalid_request_never_enters_the_database(self):
        with self.assertRaises(ValueError):
            self.scheduler.submit('R1', 'doj25', -1)
        self.assertEqual(self.database.records(), LinkedList())

    def test_duplicate_id_and_invalid_algorithm_leave_database_unchanged(self):
        self.scheduler.submit('R1', 'doj25', 11)
        before = self.database.records()
        with self.assertRaises(SortDataError):
            self.database.import_records(before)
        with self.assertRaises(SortDataError):
            self.database.save(before, 'builtin')
        self.assertEqual(self.database.records(), before)

    def test_quick_sort_can_resort_and_export_the_same_database(self):
        self.scheduler.submit('R1', 'c81cd', 9)
        self.scheduler.submit('R2', 'doj25', 11)
        ordered = self.database.save(self.database.records(), 'quick')
        self.assertTrue(is_sorted(ordered))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'export.csv'
            self.database.export_csv(path)
            self.assertEqual(read_records(path), ordered)

    def test_database_survives_close_and_reopen(self):
        self.scheduler.submit('R1', 'doj25', 11)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'collections.sqlite3'
            first = CollectionDatabase(path)
            first.save(self.database.records())
            first.close()
            second = CollectionDatabase(path)
            try:
                self.assertEqual(second.records(), self.database.records())
            finally:
                second.close()

    def test_corrupt_database_rank_is_reported(self):
        self.scheduler.submit('R1', 'doj25', 11)
        self.database.connection.execute('UPDATE collection_records SET position=10 WHERE position=0')
        with self.assertRaisesRegex(SortDataError, 'contiguous'):
            self.database.records()

    def test_archive_failure_does_not_insert_into_the_heap(self):
        with patch.object(self.scheduler.archive, 'record', side_effect=SortDataError('test write failure')):
            with self.assertRaisesRegex(ValueError, 'test write failure'):
                self.scheduler.submit('R1', 'doj25', 11)
        self.assertEqual(self.scheduler.heap.size, 0)

    def test_archive_failure_does_not_extract_from_the_heap(self):
        self.scheduler.submit('R1', 'doj25', 11)
        with patch.object(self.scheduler.archive, 'record', side_effect=SortDataError('test write failure')):
            with self.assertRaisesRegex(ValueError, 'test write failure'):
                self.scheduler.extract_priority()
        self.assertEqual(self.scheduler.heap.size, 1)

    def test_driver_retains_all_ten_records_including_a_skipped_farm(self):
        text, evidence = run_demo()
        self.assertEqual((evidence['archived'], evidence['collected'], evidence['skipped']), (10, 9, 1))
        self.assertIn('10 | skipped', text)


class BenchmarkAndMenuTests(SequenceTestCase):
    def test_benchmark_writes_all_nine_inputs_and_eighteen_valid_sorted_outputs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            rows, metadata = run_benchmarks(root/'results', root/'inputs', repeats=1, number=1)
            self.assertEqual(len(rows), 9)
            self.assertEqual(len(metadata['cases']), 9)
            self.assertEqual(len(LinkedList((root/'inputs').glob('*.csv'))), 9)
            self.assertEqual(len(LinkedList((root/'results').glob('*_sorted.csv'))), 18)
            for row in rows:
                name = '{size}_{condition}'.format(**row)
                source = read_records(root/'inputs'/(name+'.csv'))
                for algorithm in ('merge', 'quick'):
                    verify_result(source, read_records(root/'results'/(name+'_'+algorithm+'_sorted.csv')),
                                  stable=(algorithm == 'merge'))
            self.assertEqual(metadata['seed'], SEED)
            self.assertEqual(metadata['sorts_per_repeat'], 1)
            self.assertTrue(manual_all(row['merge_ms'] > 0 and row['quick_ms'] > 0 for row in rows))

    def test_benchmark_rejects_invalid_repeat_parameters(self):
        for values in (manual_map((('repeats', 0),)), manual_map((('number', 0),)), manual_map((('repeats', True),)), manual_map((('number', 1.5),))):
            with self.assertRaises(SortDataError):
                run_benchmarks(**values)

    def run_app(self, arguments, inputs=None, output_dir=None):
        args = LinkedList((sys.executable, str(PROJECT_ROOT/'interactive_menu.py'), *arguments))
        if output_dir is not None:
            args.extend(('--output-dir', str(output_dir)))
        return subprocess.run(args, input=inputs, capture_output=True, text=True,
                              cwd=output_dir or PROJECT_ROOT, timeout=30)

    def test_sort_demo_works_from_another_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            result = self.run_app(('--module', 'sort', '--demo'), output_dir=directory)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('All 10 accepted requests retained', result.stdout)

    def test_sort_validation_checks_all_nine_cases(self):
        result = self.run_app(('--module', 'sort', '--validate'))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(manual_count(result.stdout, 'PASS:'), 9)

    def test_sort_menu_import_export_and_both_algorithms(self):
        with tempfile.TemporaryDirectory() as directory:
            result = self.run_app(('--module', 'sort'), 'bad\n1\n4\n2\n3\n5\n0\n', directory)
            records = read_records(Path(directory)/'collection_records_sorted.csv')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('Empty database', result.stdout)
        self.assertIn('Invalid sorting option', result.stdout)
        self.assertEqual(len(records), 100)
        self.assertTrue(is_sorted(records))

    def test_root_menu_retains_heap_history_for_module4(self):
        with tempfile.TemporaryDirectory() as directory:
            result = self.run_app((), '11\n1\n5\n0\n12\n1\n5\n0\n0\n', directory)
            records = read_records(Path(directory)/'collection_records_sorted.csv')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(records), 10)
        self.assertTrue(manual_all(record.status == 'collected' for record in records))
        self.assertTrue(is_sorted(records))

    def test_heap_reset_keeps_both_sessions_in_database(self):
        with tempfile.TemporaryDirectory() as directory:
            result = self.run_app(('--module', 'heap'), '1\n7\n1\n0\n', directory)
            database = CollectionDatabase(Path(directory)/'collection_records.sqlite3')
            records = database.records()
            database.close()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(records), 20)
        self.assertTrue(manual_all(record.status == 'cancelled' for record in records))

    def test_missing_dataset_is_an_actionable_cli_error(self):
        with tempfile.TemporaryDirectory() as directory:
            result = self.run_app(('--module', 'sort', '--validate', '--data-dir', directory))
        self.assertEqual(result.returncode, 1)
        self.assertIn('Cannot read', result.stderr)
        self.assertNotIn('Traceback', result.stderr)


if __name__ == '__main__':
    unittest.main()
