"""Author: Thanh Dat Nguyen
Student ID: 23857030
Date: 25/09/2026
Purpose: Executable Module 2 evidence using at least 40 genuine source farm records.

Run from the project root: python -m module2_hash.test_driver
Reports use manual containers and JSON I/O adapters. All farm lookup operations
use the NumPy-array-backed manual HashTable, including the standalone collision experiment.
"""

from manual_structures import LinkedList, manual_any, manual_map
from manual_io import dataclass_map


import argparse
from dataclasses import replace
from pathlib import Path

from .data_loader import DEFAULT_DATASET, HashDataError, read_farm_records
from .display import (delete_text, load_text, resize_text, search_text, summary_text,
                      table_text, trace_text)
from .hash_table import DuplicateFarmError, HashTable, HashTableError
from .records import RecordValidationError, record_text


def collision_pair(records, capacity=11):
    """Choose two real different IDs with the same home slot, without fabrication."""
    table = HashTable(capacity)
    for position, first in enumerate(records):
        home = table.hash_index(first.farm_id)
        for second in records[position + 1:]:
            if second.farm_id != first.farm_id and table.hash_index(second.farm_id) == home:
                return first, second, home
    raise HashDataError("No collision pair in the selected records at this table size.")


def run_demo(records, count=125):
    """Return executed demonstration text and its machine-readable evidence."""
    if not isinstance(count, int) or count < 40 or count > len(records):
        raise HashDataError("Demonstration count must be at least 40 and no more than the CSV record count.")
    selected = records[:count]
    lines = LinkedList((
        "COMP5008 | MODULE 2 | HASH-BASED FARM LOOKUP",
        "Real source farms: {} | strategy: linear probing | initial slots: 11".format(count),
        "Hash: h = (31*h + ord(character)) % m, starting at h=0.",
        "Probe: (home + i) % m. Active threshold: 0.70; occupied threshold: 0.85.",
        "\nEXPLICIT COLLISION EXPERIMENT (separate 11-slot table)",
    ))
    first, second, home = collision_pair(selected)
    small = HashTable(11)
    lines.append("{} and {} both hash to home slot {} modulo 11.".format(
        first.farm_id, second.farm_id, home))
    lines.append("Initial state:\n" + table_text(small))
    small.insert(first)
    lines += LinkedList((trace_text(small.last_trace), "After first insertion:\n" + table_text(small)))
    small.insert(second)
    collision_trace = small.last_trace
    lines += LinkedList((trace_text(collision_trace), "After collision resolution:\n" + table_text(small)))
    lines += LinkedList((
        "\nDELETE THE HEAD OF THAT PROBE CLUSTER",
        delete_text(small, first.farm_id),
        "State with tombstone:\n" + table_text(small),
    ))
    found_after_delete = small.search(second.farm_id)
    survivor_trace = small.last_trace
    lines += LinkedList((
        trace_text(survivor_trace),
        "Surviving colliding farm found after deletion: {}".format(found_after_delete.farm_id),
    ))
    if found_after_delete != second:
        raise HashTableError("A tombstone incorrectly hid a surviving record.")
    lines.append(search_text(small, first.farm_id))
    lines.append(delete_text(small, first.farm_id))
    try:
        small.insert(second)
    except DuplicateFarmError as error:
        lines += LinkedList((trace_text(small.last_trace), "Duplicate beyond tombstone rejected: " + str(error)))
    else:
        raise HashTableError("A duplicate was inserted after a tombstone.")
    small.insert(first)
    lines += LinkedList((trace_text(small.last_trace), "Reinserted deleted record; tombstone reused:\n" + table_text(small)))

    lines.append("\nBULK INSERTS (fresh table; original CSV order)")
    table = HashTable(11)
    loads, resizes = LinkedList(), LinkedList()
    insertion_probes = 0
    collision_insertions = 0
    for number, record in enumerate(selected, start=1):
        table.insert(record)
        trace = table.last_trace
        insertion_probes += trace.probe_count
        if table.pre_resize_trace is not None:
            lines.append("Before rehash: " + trace_text(table.pre_resize_trace))
            insertion_probes += table.pre_resize_trace.probe_count
        if table.last_resize is not None:
            lines.append(resize_text(table.last_resize))
            resizes.append(dataclass_map(table.last_resize))
        sequence = "->".join(str(step.index) for step in trace.steps)
        lines.append("INSERT {:03d} {} | home={} probe={} placed={} active={} m={}".format(
            number, record.farm_id, trace.home, sequence, trace.slot, table.size, table.capacity))
        if trace.collisions:
            collision_insertions += 1
        if table.last_load_sample is not None:
            lines.append(load_text(table.last_load_sample))
            loads.append(dataclass_map(table.last_load_sample))
    bulk_state = manual_map((
        ("records", table.size),
        ("capacity", table.capacity),
        ("load_factor", table.load_factor),
        ("occupied_factor", table.occupied_factor),
        ("insertion_probes", insertion_probes),
        ("mean_insertion_probes", insertion_probes / count),
        ("rehash_probes", sum(event["rehash_probes"] for event in resizes)),
        ("inserts_with_placement_collisions", collision_insertions),
    ))
    lines += LinkedList((
        "Final bulk state: " + summary_text(table),
        "Bulk insertion probes={} (includes pre-resize duplicate checks); mean={:.3f}.".format(
                  insertion_probes, insertion_probes / count),
        "Internal rehash probes={} are counted separately.".format(bulk_state["rehash_probes"]),
    ))

    lines.append("\nSUCCESSFUL SEARCHES (complete first record shown)")
    successful_ids = (selected[0].farm_id, selected[count // 2].farm_id, selected[-1].farm_id)
    for number, farm_id in enumerate(successful_ids):
        found = table.search(farm_id)
        if found is None:
            raise HashTableError("Inserted farm could not be found.")
        lines.append(trace_text(table.last_trace))
        lines.append(record_text(found) if number == 0 else "Found {} | {}".format(farm_id, found.name))
    missing_id = "zzzzz"
    if manual_any(record.farm_id == missing_id for record in selected):
        raise HashDataError("The demo's intended missing ID unexpectedly exists in this dataset.")
    lines += LinkedList((
        "\nUNSUCCESSFUL SEARCH",
        search_text(table, missing_id),
        "\nSUCCESSFUL DELETE AND SUBSEQUENT SEARCH",
        delete_text(table, selected[0].farm_id),
        search_text(table, selected[0].farm_id),
        search_text(table, selected[-1].farm_id),
        "\nUNSUCCESSFUL DELETION ATTEMPTS",
        delete_text(table, selected[0].farm_id),
        delete_text(table, missing_id),
    ))
    lines.append("\nDUPLICATE INSERT AND INVALID-INPUT VALIDATION")
    try:
        table.insert(selected[-1])
    except DuplicateFarmError as error:
        lines += LinkedList((trace_text(table.last_trace), str(error)))
    for action in (lambda: table.search("BAD ID"),
                   lambda: table.delete(""),
                   lambda: replace(selected[0], name=" "),
                   lambda: replace(selected[0], lat="not a number"),
                   lambda: replace(selected[0], lat=float("nan")),
                   lambda: replace(selected[0], lng=181)):
        try:
            action()
        except (RecordValidationError, HashTableError) as error:
            lines.append("Validation error handled: " + str(error))
        else:
            raise HashTableError("Expected invalid input to be rejected.")
    lines.append("Final demonstration state: " + summary_text(table))
    evidence = manual_map((
        ("records_inserted", count),
        ("strategy", "linear probing"),
        ("initial_capacity", 11),
        ("threshold", 0.70),
        ("occupied_threshold", 0.85),
        ("load_samples", loads),
        ("resizes", resizes),
        ("bulk_state", bulk_state),
        ("collision", manual_map((
            ("first_id", first.farm_id),
            ("second_id", second.farm_id),
            ("home", home),
            ("capacity", 11),
            ("second_insert", dataclass_map(collision_trace)),
            ("survivor_search_after_delete", dataclass_map(survivor_trace)),
        ))),
        ("successful_search_ids", successful_ids),
        ("missing_id", missing_id),
        ("deleted_id", selected[0].farm_id),
        ("active_after_delete", table.size),
        ("tombstones_after_delete", table.tombstones),
        ("complete_fields_per_record", len(selected[0].fields())),
    ))
    return "\n".join(lines) + "\n", evidence


def main(argv=None):
    parser = argparse.ArgumentParser(description="Module 2: collision, load, search and deletion demonstration")
    parser.add_argument("--data", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--count", type=int, default=125)
    args = parser.parse_args(argv)
    try:
        text, evidence = run_demo(read_farm_records(args.data), args.count)
    except (HashDataError, RecordValidationError, HashTableError) as error:
        parser.error(str(error))
    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
