"""Author: Thanh Dat Nguyen
Student ID: 23857030
Date: 20/09/2026
Purpose: Restore spreadsheet-corrupted IDs using the two supplied source URLs.

The input farm_dataset_red_meat_WA.csv is not modified.
The script overwrites dataset.csv and id_corrections.csv.
"""

from manual_structures import LinkedList, manual_map
from manual_io import CSVWriter

from pathlib import Path
import re

from .data_loader import DEFAULT_DATA_DIR, DataError, REQUIRED_FARM_FIELDS, read_csv, source_ids


def prepare(data_dir=DEFAULT_DATA_DIR):
    data_dir = Path(data_dir)
    rows = read_csv(data_dir / "farm_dataset_red_meat_WA.csv", REQUIRED_FARM_FIELDS)
    corrections = LinkedList()
    for row in rows:
        map_id, profile_id = source_ids(row)
        if row["Id"] != map_id:
            if re.fullmatch(r"\d+(?:\.\d+)?[Ee][+]\d+", row["Id"]) is None:
                raise DataError("Unexpected ID discrepancy for {}.".format(row["Name"]))
            corrections.append(manual_map((
                ("OriginalID", row["Id"]),
                ("RestoredFarmID", map_id),
                ("Name", row["Name"]),
                ("Map URL", row["Map URL"]),
                ("Profile URL", row["Profile URL"]),
                ("Reason", "Restored exact website ID; both source URLs agree"),
            )))
            row["Id"] = profile_id
    with (data_dir / "dataset.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = CSVWriter(stream, fieldnames=LinkedList(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    fields = ("OriginalID", "RestoredFarmID", "Name", "Map URL", "Profile URL", "Reason")
    with (data_dir / "id_corrections.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = CSVWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(corrections)
    return corrections


if __name__ == "__main__":
    changes = prepare()
    print("Prepared dataset.csv; restored {} website IDs.".format(len(changes)))
    for change in changes:
        print("{} -> {} | {}".format(change["OriginalID"], change["RestoredFarmID"], change["Name"]))
