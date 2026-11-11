"""Author: Thanh Dat Nguyen
Student ID: 23857030
Date: 25/09/2026
Purpose: Load the shared farm CSV into the manual hash table, without a dict index.
"""

from manual_structures import LinkedList

import csv
from dataclasses import dataclass
from pathlib import Path

from .hash_table import HashTable, HashTableError
from .records import FarmRecord, RecordValidationError

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DATASET = PROJECT_ROOT / "data" / "dataset.csv"


class HashDataError(ValueError):
    """A source file cannot supply valid, unique WA farm records."""


@dataclass(frozen=True)
class LoadedLookup:
    table: HashTable
    records: tuple
    load_samples: tuple
    resize_events: tuple
    insertion_probes: int


def read_farm_records(path=DEFAULT_DATASET):
    """Read all original fields using positional csv.reader, including source blanks."""
    path = Path(path)
    try:
        with path.open(encoding="utf-8-sig", newline="") as stream:
            reader = csv.reader(stream, strict=True)
            header = None
            for first_row in reader:
                header = first_row
                break
            if header is None:
                raise HashDataError("{}: missing CSV header.".format(path.name))
            records = LinkedList()
            for row in reader:
                if row:
                    try:
                        record = FarmRecord.from_csv_row(header, row)
                        if record.state != "WA" or record.country != "Australia":
                            raise RecordValidationError("The selected project region is WA, Australia.")
                        records.append(record)
                    except RecordValidationError as error:
                        raise HashDataError("{}:{}: {}".format(path.name, reader.line_num, error)) from error
            if not records:
                raise HashDataError("{}: no farm records.".format(path.name))
            return tuple(records)
    except (OSError, UnicodeError, csv.Error) as error:
        raise HashDataError("Cannot read {}: {}".format(path, error)) from error


def load_lookup(path=DEFAULT_DATASET, initial_capacity=11):
    """Return a fresh table and loading evidence; a failed load changes no live table."""
    records = read_farm_records(path)
    table = HashTable(initial_capacity)
    loads, resizes = LinkedList(), LinkedList()
    probes = 0
    for number, record in enumerate(records, start=1):
        try:
            table.insert(record)
        except HashTableError as error:
            raise HashDataError("{}: record {}: {}".format(Path(path).name, number, error)) from error
        probes += table.last_trace.probe_count
        if table.pre_resize_trace is not None:
            probes += table.pre_resize_trace.probe_count
        if table.last_load_sample is not None:
            loads.append(table.last_load_sample)
        if table.last_resize is not None:
            resizes.append(table.last_resize)
    return LoadedLookup(table, records, tuple(loads), tuple(resizes), probes)
