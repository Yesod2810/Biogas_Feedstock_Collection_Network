"""Author: Thanh Dat Nguyen
Student ID: 23857030
Date: 11/10/2026
Purpose: Run all 3 sizes x 3 conditions x 2 algorithms; save data and raw timings.
"""

from manual_structures import LinkedList, manual_map, manual_max, manual_min
from manual_io import CSVWriter, dataclass_map, json_dumps


import argparse
import csv

import hashlib
from pathlib import Path
import platform
import sys
import timeit

from module1_graph.data_loader import DEFAULT_DATA_DIR, PROJECT_ROOT
from .algorithms import SortMetrics, is_sorted, merge_sort, quick_sort
from .datasets import CONDITIONS, SEED, SIZES, generate_records, make_condition
from .records import SortDataError, write_records

ALGORITHMS = (('merge', merge_sort), ('quick', quick_sort))


def median(values):
    """Use our own Merge Sort for timing statistics too."""
    ordered = merge_sort(values, key=lambda value: value)
    length = len(ordered)
    if length == 0:
        raise SortDataError("A median needs at least one sample.")
    middle = length // 2
    return ordered[middle] if length % 2 else (ordered[middle - 1] + ordered[middle]) / 2


def verify_result(original, result, stable=False):
    if not is_sorted(result) or len(original) != len(result):
        raise AssertionError("Sorting did not produce ascending T with the original length.")
    source = manual_map(((record.record_id, record) for record in original))
    output = manual_map(((record.record_id, record) for record in result))
    if len(source) != len(original) or source != output:
        raise AssertionError("Sorting changed or lost collection records.")
    positions = manual_map(((record.record_id, index) for index, record in enumerate(original)))
    ties_stable = True
    previous = None
    for record in result:
        if (previous is not None and previous.transport_minutes == record.transport_minutes
                and positions[previous.record_id] >= positions[record.record_id]):
            ties_stable = False
        previous = record
    if stable and not ties_stable:
        raise AssertionError("Merge Sort did not preserve equal-key input order.")
    return ties_stable


def table_text(rows):
    lines = LinkedList((
        'Times: median milliseconds per complete sort (copy included).',
        '| Records | Condition | Merge ms | Quick ms | Quick / Merge |',
        '|---:|---|---:|---:|---:|',
    ))
    for row in rows:
        lines.append('| {size} | {condition} | {merge_ms:.6f} | {quick_ms:.6f} | {ratio:.3f} |'.format(**row))
    return '\n'.join(lines) + '\n'


def run_benchmarks(output_dir=None, input_dir=None, data_dir=DEFAULT_DATA_DIR,
                   seed=SEED, repeats=7, number=25):
    if isinstance(repeats, bool) or not isinstance(repeats, int) or repeats < 1:
        raise SortDataError("Timing repeats must be a positive integer.")
    if isinstance(number, bool) or not isinstance(number, int) or number < 1:
        raise SortDataError("Sorts per repeat must be a positive integer.")
    output_dir = Path(output_dir or PROJECT_ROOT / 'sample_output' / 'sorting')
    input_dir = Path(input_dir or data_dir / 'sort_inputs')
    output_dir.mkdir(parents=True, exist_ok=True)
    base, generation = generate_records(manual_max(SIZES), seed, data_dir)
    timing_rows, raw_rows, validation = LinkedList(), LinkedList(), LinkedList()
    for size in SIZES:
        for condition_index, condition in enumerate(CONDITIONS):
            condition_seed = seed + size * 10 + condition_index
            records, attributes = make_condition(base[:size], condition, condition_seed)
            name = '{}_{}'.format(size, condition)
            input_path = input_dir / (name + '.csv')
            write_records(input_path, records)
            times = manual_map()
            details = manual_map((
                ('size', size),
                *attributes.items(),
                ('input_sha256', hashlib.sha256(input_path.read_bytes()).hexdigest()),
            ))
            algorithms = ALGORITHMS if condition_index % 2 == 0 else ALGORITHMS[::-1]
            for label, sorter in algorithms:
                before = tuple(records)
                result = sorter(records)  # untimed warm-up + correctness check
                tie_order = verify_result(records, result, stable=(label == 'merge'))
                timer = timeit.Timer(lambda sorter=sorter: sorter(records))
                samples = LinkedList((elapsed * 1000 / number for elapsed in timer.repeat(repeat=repeats, number=number)))
                if tuple(records) != before:
                    raise AssertionError("A sort modified the shared benchmark input.")
                times[label] = median(samples)
                metrics = SortMetrics()
                verify_result(records, sorter(records, metrics=metrics), stable=(label == 'merge'))
                details[label] = manual_map((
                    ('correct', True),
                    ('equal_time_order_preserved', tie_order),
                    ('metrics', dataclass_map(metrics)),
                    ('median_ms', times[label]),
                    ('min_ms', manual_min(samples)),
                    ('max_ms', manual_max(samples)),
                ))
                raw_rows.extend(manual_map((
                    ('size', size),
                    ('condition', condition),
                    ('algorithm', label),
                    ('repeat', index + 1),
                    ('sorts', number),
                    ('ms_per_sort', sample),
                ))
                                for index, sample in enumerate(samples))
                write_records(output_dir / (name + '_' + label + '_sorted.csv'), result)
            timing_rows.append(manual_map((
                ('size', size),
                ('condition', condition),
                ('merge_ms', times['merge']),
                ('quick_ms', times['quick']),
                ('ratio', times['quick'] / times['merge']),
            )))
            validation.append(details)
    metadata = manual_map((
        ('seed', seed),
        ('sizes', LinkedList(SIZES)),
        ('conditions', LinkedList(CONDITIONS)),
        ('repeats', repeats),
        ('sorts_per_repeat', number),
        ('statistic', 'Median of repeat batch times, divided by sorts per repeat; milliseconds.'),
        ('timed_work', 'Non-mutating sorter, including result copy; metrics disabled.'),
        ('excluded_work', 'Graph, hash lookup, dataset generation, validation, CSV/SQLite I/O, printing.'),
        ('gc', 'timeit disables cyclic garbage collection during each timed batch.'),
        ('python', sys.version),
        ('platform', platform.platform()),
        ('processor', platform.processor() or 'Not exposed by this host'),
        ('timer', timeit.default_timer.__name__),
        ('note', 'Seed reproduces records and arrangements; wall-clock measurements vary by machine and load.'),
        ('generation', generation),
        ('cases', validation),
    ))
    for path, rows in ((output_dir / 'timings.csv', timing_rows), (output_dir / 'timing_samples.csv', raw_rows)):
        with path.open('w', newline='', encoding='utf-8') as stream:
            writer = CSVWriter(stream, fieldnames=LinkedList(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    (output_dir / 'benchmark_results.md').write_text(table_text(timing_rows), encoding='utf-8')
    (output_dir / 'benchmark_metadata.json').write_text(json_dumps(metadata, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    return timing_rows, metadata


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seed', type=int, default=SEED)
    parser.add_argument('--repeats', type=int, default=7)
    parser.add_argument('--number', type=int, default=25)
    parser.add_argument('--data-dir', type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument('--output-dir', type=Path, default=PROJECT_ROOT / 'sample_output' / 'sorting')
    parser.add_argument('--input-dir', type=Path)
    args = parser.parse_args(argv)
    try:
        rows, metadata = run_benchmarks(args.output_dir, args.input_dir, args.data_dir,
                                        args.seed, args.repeats, args.number)
        print(table_text(rows), end='')
        print('PASS: 18 sorted outputs validated; all nine cases use graph-derived times.')
        return 0
    except (SortDataError, OSError, ValueError) as error:
        print('Error: {}'.format(error), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
