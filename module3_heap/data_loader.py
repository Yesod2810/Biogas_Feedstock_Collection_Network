"""Author: Thanh Dat Nguyen
Student ID: 23857030
Date: 3/10/2026
Purpose: Read user-designed educational request quantities, never manual priorities.
"""

from manual_structures import LinkedList, ManualSet, manual_any, manual_contains
from manual_io import CSVReader


import csv
from dataclasses import dataclass
from pathlib import Path

DEFAULT_REQUESTS = Path(__file__).resolve().parent.parent / "data" / "collection_requests.csv"


class RequestDataError(ValueError):
    """The request CSV cannot be parsed."""


@dataclass(frozen=True)
class RequestInput:
    request_id: str
    farm_id: str
    estimated_feedstock: str


def read_requests(path=DEFAULT_REQUESTS):
    path = Path(path)
    try:
        with path.open(encoding="utf-8-sig", newline="") as stream:
            reader = CSVReader(stream, strict=True)
            required = ("RequestID", "FarmID", "EstimatedFeedstock", "Unit")
            if reader.fieldnames is None or manual_any(not manual_contains(reader.fieldnames, name) for name in required):
                raise RequestDataError("Request CSV needs RequestID, FarmID, EstimatedFeedstock and Unit.")
            if len(ManualSet(reader.fieldnames)) != len(reader.fieldnames):
                raise RequestDataError("Duplicate request CSV column.")
            if manual_any(manual_contains(("priority", "collectionpriority"), name.lower()) for name in reader.fieldnames):
                raise RequestDataError("Do not enter priorities; the program calculates them.")
            requests = LinkedList()
            for row in reader:
                if manual_contains(row, None) or manual_any(value is None for value in row.values()):
                    raise RequestDataError("{}:{}: malformed request row.".format(path.name, reader.line_num))
                if row["Unit"] != "tonnes":
                    raise RequestDataError("{}:{}: Unit must be tonnes.".format(path.name, reader.line_num))
                requests.append(RequestInput(row["RequestID"], row["FarmID"], row["EstimatedFeedstock"]))
            if not requests:
                raise RequestDataError("Request CSV has no records.")
            return tuple(requests)
    except (OSError, UnicodeError, csv.Error) as error:
        raise RequestDataError("Cannot read {}: {}".format(path, error)) from error
