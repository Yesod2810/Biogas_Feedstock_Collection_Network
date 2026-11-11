"""Author: Thanh Dat Nguyen
Student ID: 23857030
Date: 11/10/2026
Purpose: Untimed integration checks and a history of ten modelled
collection requests using farms from the submitted dataset.
"""

from manual_structures import LinkedList, manual_map

import argparse
from io import StringIO
from pathlib import Path

from module1_graph.data_loader import DEFAULT_DATA_DIR, load_network
from module2_hash.data_loader import load_lookup
from module3_heap.data_loader import read_requests
from module3_heap.scheduler import CollectionScheduler

from .algorithms import merge_sort, quick_sort
from .benchmark import verify_result
from .database import CollectionDatabase
from .datasets import CONDITIONS, SEED, SIZES, generate_records, make_condition


def validate(data_dir=DEFAULT_DATA_DIR):
    base, metadata = generate_records(1000, SEED, data_dir)
    checks = LinkedList()
    for size in SIZES:
        for index, condition in enumerate(CONDITIONS):
            records, attributes = make_condition(base[:size], condition, SEED + size * 10 + index)
            verify_result(records, merge_sort(records), stable=True)
            verify_result(records, quick_sort(records))
            checks.append(manual_map((
                ('size', size),
                ('condition', condition),
                ('passed', True),
                ('displaced_records', attributes['displaced_records']),
            )))
    return checks, metadata


def run_demo(data_dir=DEFAULT_DATA_DIR, database_path=':memory:', export_path=None):
    """Keep all ten submissions; deleted farms remain as skipped history."""
    output = StringIO()
    database = CollectionDatabase(database_path)
    try:
        if database.records():
            raise ValueError("Use an empty demonstration database to preserve previous records.")
        scheduler = CollectionScheduler(load_lookup(data_dir / 'dataset.csv').table,
            load_network('test', data_dir), emit=None, archive=database.new_session())
        for raw in read_requests(data_dir / 'collection_requests.csv'):
            scheduler.submit(raw.request_id, raw.farm_id, raw.estimated_feedstock)
        scheduler.lookup.delete('doj25')
        while scheduler.heap.size:
            scheduler.extract_priority()
        records = database.records()
        print('MODULE 4 - SORTED COLLECTION DATABASE', file=output)
        print('All 10 accepted requests retained: 9 collected; 1 skipped after farm deletion.', file=output)
        print('Key: estimated shortest transport time T, ascending.', file=output)
        print('RecordID | RequestID | FarmID | T minutes | Status', file=output)
        for record in records:
            print('{} | {} | {} | {:g} | {}'.format(record.record_id, record.request.request_id,
                record.request.farm_id, record.transport_minutes, record.status), file=output)
        quick = quick_sort(records)
        verify_result(records, quick)
        assert LinkedList((r.transport_minutes for r in quick)) == LinkedList((r.transport_minutes for r in records))
        if export_path is not None:
            database.export_csv(export_path)
        return output.getvalue(), manual_map((
            ('archived', len(records)),
            ('collected', sum(r.status == 'collected' for r in records)),
            ('skipped', sum(r.status == 'skipped' for r in records)),
            ('ascending_times', LinkedList((r.transport_minutes for r in records))),
        ))
    finally:
        database.close()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir', type=Path, default=DEFAULT_DATA_DIR)
    args = parser.parse_args(argv)
    output, evidence = run_demo(args.data_dir)
    print(output, end='')
    checks, metadata = validate(args.data_dir)
    for row in checks:
        print('PASS: {size} records / {condition} / both algorithms'.format(**row))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
