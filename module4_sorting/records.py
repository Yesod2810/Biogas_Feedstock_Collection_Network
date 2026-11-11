"""Author: Thanh Dat Nguyen
Student ID: 23857030
Date: 11/10/2026
Purpose: Complete collection snapshots, including the original farm record fields.
"""

from manual_structures import LinkedList, OpenAddressMap, manual_contains, manual_map
from manual_io import CSVReader, CSVWriter, json_dumps, json_loads

import csv
from dataclasses import dataclass
from pathlib import Path

from module2_hash.records import FarmRecord
from module3_heap.requests import ScheduledRequest

CSV_FIELDS = ("RecordID", "RequestID", "FarmID", "FarmName", "EstimatedFeedstock", "Unit",
              "TransportTime", "CollectionPriority", "Path", "Status", "Detail", "FarmSnapshotJSON")
STATUSES = ("pending", "collected", "skipped", "cancelled", "modelled")


class SortDataError(ValueError):
    """A collection file, record or database operation is invalid."""


@dataclass(frozen=True)
class CollectionRecord:
    record_id: str
    request: ScheduledRequest
    status: str = "modelled"
    detail: str = "Educational request; no real collection is asserted."

    def __post_init__(self):
        if not isinstance(self.record_id, str) or not self.record_id or len(self.record_id) > 96:
            raise SortDataError("RecordID must contain 1-96 characters.")
        if not isinstance(self.request, ScheduledRequest):
            raise SortDataError("A collection record requires a validated Module 3 request.")
        if not manual_contains(STATUSES, self.status) or not isinstance(self.detail, str):
            raise SortDataError("Invalid collection status or detail.")

    @property
    def transport_minutes(self):
        return self.request.transport_minutes

    def row(self):
        request = self.request
        values = (self.record_id, request.request_id, request.farm_id, request.farm.name,
                  format(request.feedstock, '.17g'), 'tonnes', format(self.transport_minutes, '.17g'),
                  format(request.priority, '.17g'), json_dumps(request.path), self.status, self.detail,
                  json_dumps(manual_map(request.farm.fields()), ensure_ascii=True, allow_nan=False))
        return manual_map(zip(CSV_FIELDS, values))

    @classmethod
    def from_row(cls, row):
        try:
            if row['Unit'] != 'tonnes':
                raise SortDataError("Feedstock Unit must be tonnes.")
            snapshot = json_loads(row['FarmSnapshotJSON'])
            header = LinkedList(snapshot)
            farm = FarmRecord.from_csv_row(header, LinkedList((snapshot[column] for column in header)))
            request = ScheduledRequest(row['RequestID'], farm, row['EstimatedFeedstock'],
                                       row['TransportTime'], tuple(json_loads(row['Path'])))
            if row['FarmID'] != farm.farm_id or row['FarmName'] != farm.name:
                raise SortDataError("Farm summary disagrees with its complete snapshot.")
            if float(row['CollectionPriority']) != request.priority:
                raise SortDataError("Stored priority disagrees with the calculated priority.")
            return cls(row['RecordID'], request, row['Status'], row['Detail'])
        except (KeyError, TypeError, ValueError) as error:
            raise SortDataError("Invalid collection record: {}".format(error)) from error


def require_unique(records):
    ids = OpenAddressMap(track_order=False)
    for record in records:
        if not isinstance(record, CollectionRecord):
            raise SortDataError("Expected CollectionRecord instances.")
        if manual_contains(ids, record.record_id):
            raise SortDataError("Duplicate RecordID {}.".format(record.record_id))
        ids[record.record_id] = True


def write_records(path, records):
    """Write in the supplied order; sorting is always the caller's explicit step."""
    records = LinkedList(records)
    require_unique(records)
    path = Path(path)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('w', newline='', encoding='utf-8') as stream:
            writer = CSVWriter(stream, fieldnames=CSV_FIELDS)
            writer.writeheader()
            writer.writerows(record.row() for record in records)
    except OSError as error:
        raise SortDataError("Cannot write collection CSV: {}".format(error)) from error


def read_records(path):
    try:
        with Path(path).open(newline='', encoding='utf-8-sig') as stream:
            reader = CSVReader(stream)
            if tuple(reader.fieldnames or ()) != CSV_FIELDS:
                raise SortDataError("Unexpected collection CSV columns.")
            records = LinkedList((CollectionRecord.from_row(row) for row in reader))
        require_unique(records)
        return records
    except (OSError, csv.Error, UnicodeError) as error:
        raise SortDataError("Cannot read collection CSV: {}".format(error)) from error
