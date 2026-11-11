"""Author: Thanh Dat Nguyen
Student ID: 23857030
Date: 20/09/2026
Purpose: Strict CSV validation and loading, separate from graph algorithms.
"""

from manual_structures import (
    LinkedList, ManualSet, OpenAddressMap, manual_all, manual_any,
    manual_contains, manual_map
)
from manual_io import CSVReader, query_values


import csv
from math import isfinite
from pathlib import Path
import re
from urllib.parse import urlparse

from .graph import Graph, GraphError, Location

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DATA_DIR = PROJECT_ROOT / "data"
HUB_ID = "HUB_PINJARRA"
ISOLATED_ID = "gslqa"
REQUIRED_FARM_FIELDS = ("Id", "Name", "Species", "Lat", "Lng", "Street Num",
                        "Street", "Suburb", "State", "Postcode", "Country")


class DataError(ValueError):
    """An input file is missing or contains an invalid record."""


def read_csv(path, required_fields):
    path = Path(path)
    try:
        with path.open(encoding="utf-8-sig", newline="") as stream:
            reader = CSVReader(stream)
            if reader.fieldnames is None:
                raise DataError("{}: missing CSV header.".format(path.name))
            if len(ManualSet(reader.fieldnames)) != len(reader.fieldnames):
                raise DataError("{}: duplicate CSV column name.".format(path.name))
            missing = LinkedList((field for field in required_fields if not manual_contains(reader.fieldnames, field)))
            if missing:
                raise DataError("{}: missing columns: {}.".format(path.name, ", ".join(missing)))
            rows = LinkedList()
            for line_number, row in enumerate(reader, start=2):
                if manual_contains(row, None) or manual_any(value is None for value in row.values()):
                    raise DataError("{}:{}: malformed CSV record.".format(path.name, line_number))
                rows.append(row)
            if not rows:
                raise DataError("{}: no data records.".format(path.name))
            return rows
    except (OSError, UnicodeError, csv.Error) as error:
        raise DataError("Cannot read {}: {}".format(path, error)) from error


def coordinate(text, minimum, maximum, label):
    try:
        value = float(text)
    except (TypeError, ValueError, OverflowError) as error:
        raise DataError("Invalid {}: {!r}.".format(label, text)) from error
    if not isfinite(value) or not minimum <= value <= maximum:
        raise DataError("Invalid {}: {!r}.".format(label, text))
    return value


def source_ids(row):
    """Extract and compare the IDs encoded in the map and profile URLs."""
    map_url = urlparse(row.get("Map URL", ""))
    profile_url = urlparse(row.get("Profile URL", ""))
    allowed = ManualSet(("farmtransparency.org", "www.farmtransparency.org"))
    if (map_url.scheme != "https" or profile_url.scheme != "https"
            or not manual_contains(allowed, map_url.netloc) or not manual_contains(allowed, profile_url.netloc)):
        raise DataError("Missing or invalid Farm Transparency source URLs.")
    map_ids = query_values(map_url.query, "location")
    match = re.match(r"^/facilities/([a-z0-9]{5})(?:-|/|$)", profile_url.path)
    if len(map_ids) != 1 or match is None or map_ids[0] != match.group(1):
        raise DataError("Map and profile URL identifiers disagree.")
    return map_ids[0], match.group(1)


def read_farms(path=DEFAULT_DATA_DIR / "dataset.csv"):
    rows = read_csv(path, REQUIRED_FARM_FIELDS)
    farms = OpenAddressMap()
    for line_number, row in enumerate(rows, start=2):
        try:
            farm_id = row["Id"]
            if re.fullmatch(r"[a-z0-9]{5}", farm_id) is None:
                raise DataError("Invalid website FarmID {!r}; IDs must remain text.".format(farm_id))
            if manual_contains(farms, farm_id):
                raise DataError("Duplicate FarmID {}.".format(farm_id))
            if not row["Name"].strip() or not row["Species"].strip():
                raise DataError("Name and Species must not be blank.")
            if row["State"] != "WA" or row["Country"] != "Australia":
                raise DataError("This project's region is WA, Australia.")
            if manual_contains(row, "Map URL") or manual_contains(row, "Profile URL"):
                map_id, profile_id = source_ids(row)
                if farm_id != map_id or farm_id != profile_id:
                    raise DataError("FarmID does not match its source URLs.")
            farms[farm_id] = Location(farm_id, row["Name"],
                coordinate(row["Lat"], -90, 90, "latitude"),
                coordinate(row["Lng"], -180, 180, "longitude"),
                row["Species"], row["Suburb"], "farm")
        except DataError as error:
            raise DataError("{}:{}: {}".format(Path(path).name, line_number, error)) from error
    return farms


def read_hub(path=DEFAULT_DATA_DIR / "hub.csv"):
    rows = read_csv(path, ("Id", "Name", "Lat", "Lng", "State", "Country"))
    if len(rows) != 1:
        raise DataError("hub.csv must define exactly one proposed hub.")
    row = rows[0]
    if row["Id"] != HUB_ID or not row["Name"].strip():
        raise DataError("Invalid proposed hub ID or name.")
    if row["State"] != "WA" or row["Country"] != "Australia":
        raise DataError("The proposed hub must be in WA, Australia.")
    return Location(row["Id"], row["Name"],
                    coordinate(row["Lat"], -90, 90, "hub latitude"),
                    coordinate(row["Lng"], -180, 180, "hub longitude"),
                    suburb=row.get("Suburb", ""), kind="hub")


def load_network(mode="test", data_dir=DEFAULT_DATA_DIR):
    """Load fully into a new graph, so a failed load cannot alter a live graph."""
    if not manual_contains(("test", "full"), mode):
        raise DataError("Network must be 'test' or 'full'.")
    data_dir = Path(data_dir)
    farms = read_farms(data_dir / "dataset.csv")
    hub = read_hub(data_dir / "hub.csv")
    graph = Graph()
    graph.add_vertex(hub)
    selected = tuple(farms)
    if mode == "test":
        rows = read_csv(data_dir / "test_vertices.csv", ("FarmID",))
        selected = tuple(row["FarmID"] for row in rows)
    try:
        for farm_id in selected:
            if not manual_contains(farms, farm_id):
                raise DataError("Selected FarmID {} is not in dataset.csv.".format(farm_id))
            graph.add_vertex(farms[farm_id])
        edges_path = data_dir / (mode + "_edges.csv")
        rows = read_csv(edges_path, ("FromID", "ToID", "TransportTime"))
        for line_number, row in enumerate(rows, start=2):
            try:
                minutes = float(row["TransportTime"])
                graph.add_edge(row["FromID"], row["ToID"], minutes)
            except (ValueError, OverflowError) as error:
                raise DataError("{}:{}: {}".format(edges_path.name, line_number, error)) from error
    except GraphError as error:
        raise DataError(str(error)) from error
    return graph


def check_specification(graph, source=HUB_ID):
    dfs = graph.dfs(source)
    disconnected = graph.bfs(source).unreachable
    positive = manual_all(isfinite(weight) and weight > 0 for _, _, weight in graph.edges())
    return manual_map((
        ("At least 10 vertices", graph.vertex_count >= 10),
        ("At least 12 undirected weighted edges", graph.edge_count >= 12),
        ("At least one cycle", dfs.has_cycle),
        ("At least one disconnected or isolated location", bool(disconnected)),
        ("All edge weights are finite and positive", positive),
    ))
