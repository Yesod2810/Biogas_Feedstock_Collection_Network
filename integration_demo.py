"""Author: Thanh Dat Nguyen
Student ID: 23857030
Date: 16/10/2026
Purpose: Run the four real modules in one session and export the sorted request history.
"""

from manual_structures import LinkedList, ManualSet, manual_all, manual_map
from manual_io import json_dumps


import argparse
from io import StringIO
from pathlib import Path
import sqlite3
import sys

from module1_graph.data_loader import DEFAULT_DATA_DIR, DataError, check_specification, load_network
from module1_graph.graph import GraphError
from module2_hash.data_loader import HashDataError, load_lookup
from module2_hash.records import RecordValidationError, validate_id
from module3_heap.data_loader import RequestDataError, read_requests
from module3_heap.requests import RequestValidationError
from module3_heap.scheduler import CollectionScheduler, SchedulingError
from module4_sorting.algorithms import is_sorted, merge_sort, quick_sort
from module4_sorting.benchmark import verify_result
from module4_sorting.database import CollectionDatabase
from module4_sorting.records import SortDataError, write_records


def run_integration_demo(data_dir=DEFAULT_DATA_DIR, mode='test', output_dir=None, delete_farm_id=None):
    """Share one HashTable, Graph and SQLite archive with the actual scheduler.

    A fresh memory database makes repeated demonstrations deterministic. Optional
    exports replace only derived files named integration_*. The normal interactive
    archive collection_records.sqlite3 is separate and is never cleared here.
    """
    data_dir = Path(data_dir)
    if delete_farm_id is not None:
        validate_id(delete_farm_id)
    loaded = load_lookup(data_dir / 'dataset.csv')
    graph = load_network(mode, data_dir)
    database = CollectionDatabase()
    output = StringIO()
    try:
        scheduler = CollectionScheduler(loaded.table, graph, emit=lambda text: print(text, file=output),
                                        archive=database.new_session())
        print('COMP5008 - FOUR-MODULE INTEGRATION DEMONSTRATION', file=output)
        print('Module 2: {} complete farm records in the shared manual HashTable.'.format(loaded.table.size), file=output)
        print('Module 1: {} graph with {} vertices and {} undirected edges.'.format(
              mode, graph.vertex_count, graph.edge_count), file=output)
        print('Module 3: HashTable.search -> Graph.dijkstra -> calculated priority -> MaxHeap.', file=output)
        print('Module 4: archive each accepted snapshot; manually sort T and persist explicit positions.', file=output)
        accepted = LinkedList()
        for raw in read_requests(data_dir / 'collection_requests.csv'):
            accepted.append(scheduler.submit(raw.request_id, raw.farm_id, raw.estimated_feedstock))
        if delete_farm_id is not None:
            deleted = loaded.table.delete(delete_farm_id)
            if deleted is None:
                raise SortDataError('The integration deletion scenario requires an existing FarmID.')
            print('MODULE 2 DELETE: {} removed from the shared lookup.'.format(delete_farm_id), file=output)
        collection_order, skipped = LinkedList(), LinkedList()
        while scheduler.heap.size:
            request = scheduler.extract_priority()
            skipped.extend(item[0] for item in scheduler.last_skipped)
            if request is not None:
                collection_order.append(request.request_id)
        history = database.records()
        comparison_input = LinkedList(reversed(history))
        merged, quick = merge_sort(comparison_input), quick_sort(comparison_input)
        verify_result(comparison_input, merged, stable=True)
        verify_result(comparison_input, quick)
        database.save(quick, 'quick')
        database.save(merged, 'merge')
        history = database.records()
        ordered_times = LinkedList((record.transport_minutes for record in history))
        checks = manual_map((
            ('same_hash_graph_and_archive_instances', scheduler.lookup is loaded.table and scheduler.graph is graph
                                                   and scheduler.archive.database is database),
            ('graph_meets_specification', manual_all(check_specification(graph).values())),
            ('at_least_ten_accepted_requests', len(accepted) >= 10),
            ('every_accepted_request_archived', len(history) == len(accepted)),
            ('all_request_snapshots_preserved', ManualSet((record.request for record in history)) == ManualSet(accepted)),
            ('all_dispatched_or_skipped', len(collection_order) + len(skipped) == len(accepted)),
            ('both_sorts_agree_on_ascending_times', is_sorted(history) and ordered_times == LinkedList((r.transport_minutes for r in quick))),
            ('heap_empty_after_dispatch', scheduler.heap.size == 0),
        ))
        if not manual_all(checks.values()):
            raise SortDataError('An integrated data-flow check failed: {}.'.format(checks))
        evidence = manual_map((
            ('network', mode),
            ('shared_hash_records_initial', len(loaded.records)),
            ('shared_hash_records_final', loaded.table.size),
            ('vertices', graph.vertex_count),
            ('edges', graph.edge_count),
            ('accepted_requests', LinkedList((manual_map((
                ('RequestID', request.request_id),
                ('FarmID', request.farm_id),
                ('EstimatedFeedstock', request.feedstock),
                ('TransportTime', request.transport_minutes),
                ('CollectionPriority', request.priority),
                ('Path', LinkedList(request.path)),
            )) for request in accepted))),
            ('heap_insertions', scheduler.heap.insertions),
            ('heap_extractions', scheduler.heap.extractions),
            ('collection_order', collection_order),
            ('skipped_requests', skipped),
            ('archive_count', len(history)),
            ('archive_request_order', LinkedList((record.request.request_id for record in history))),
            ('archive_times', ordered_times),
            ('statuses', manual_map(((status, sum(r.status == status for r in history)) for status in ('pending', 'collected', 'skipped', 'cancelled')))),
            ('checks', checks),
            ('artifacts', LinkedList((
                'integration_demo.txt',
                'integration_validation.json',
                'integration_records_sorted.csv',
                'integration_records.sqlite3',
            ))),
        ))
        print('\nCOLLECTION ORDER BY PRIORITY: ' + ' -> '.join(collection_order), file=output)
        print('ARCHIVE ORDER BY TRANSPORT TIME:', file=output)
        for record in history:
            print('{} | {} | T={:g} min | {}'.format(record.request.request_id, record.request.farm_id,
                                                    record.transport_minutes, record.status), file=output)
        for label, passed in checks.items():
            print('{}: {}'.format('PASS' if passed else 'FAIL', label), file=output)
        text = output.getvalue()
        if output_dir is not None:
            destination = Path(output_dir)
            try:
                destination.mkdir(parents=True, exist_ok=True)
                write_records(destination / 'integration_records_sorted.csv', history)
                disk = sqlite3.connect(str(destination / 'integration_records.sqlite3'))
                try:
                    database.connection.backup(disk)
                finally:
                    disk.close()
                (destination / 'integration_demo.txt').write_text(text, encoding='utf-8')
                (destination / 'integration_validation.json').write_text(
                    json_dumps(evidence, indent=2, allow_nan=False) + '\n', encoding='utf-8')
            except (OSError, sqlite3.Error) as error:
                raise SortDataError('Cannot export integration evidence: {}.'.format(error)) from error
        return text, evidence
    finally:
        database.close()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir', type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument('--network', choices=('test', 'full'), default='test')
    parser.add_argument('--output-dir', type=Path, default=DEFAULT_DATA_DIR.parent / 'collection_output' / 'integration')
    parser.add_argument('--delete-farm', help='Optional shared-lookup deletion after queueing, e.g. doj25')
    args = parser.parse_args(argv)
    try:
        text, evidence = run_integration_demo(args.data_dir, args.network, args.output_dir, args.delete_farm)
        print(text, end='')
        return 0
    except (DataError, GraphError, HashDataError, RecordValidationError, RequestDataError,
            RequestValidationError, SchedulingError, SortDataError) as error:
        print('Error: {}'.format(error), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
