"""Author: Thanh Dat Nguyen
Student ID: 23857030
Date: 20/09/2026
Purpose: Reproducible educational transport connections and positive minute weights.

No road API or external service is used. Great-circle distance is converted
to a road-distance estimate with factor 1.30, then to time at 60 km/h. Neither
the factor nor speed is a measured value. Only graph connections are modelled.
"""

from manual_structures import (
    LinkedList, ManualSet, manual_all, manual_contains, manual_map,
    manual_max, manual_min, object_array
)
from manual_io import CSVWriter


import csv
from math import asin, ceil, cos, radians, sin, sqrt
from pathlib import Path
import numpy as np

from .data_loader import DEFAULT_DATA_DIR, HUB_ID, ISOLATED_ID, read_csv, read_farms, read_hub

EARTH_RADIUS_KM = 6371.0
ROAD_FACTOR = 1.30
SPEED_KMH = 60.0
TEST_PAIRS = (
    (HUB_ID, "doj25"), (HUB_ID, "bcdff"), (HUB_ID, "c81cd"),
    ("doj25", "c96c9"), ("doj25", "974d7"), ("c96c9", "974d7"),
    ("974d7", "56jwf"), ("c96c9", "56jwf"), ("bcdff", "c6e42"),
    ("c6e42", "1cc85"), ("bcdff", "1cc85"), ("bcdff", "doj25"),
    ("c81cd", "0bfa4"), ("0bfa4", "56jwf"), ("c81cd", "f4386"),
    ("0bfa4", "f4386"), ("974d7", "c81cd"), ("c96c9", "0bfa4"),
)


def haversine_km(first, second):
    lat1, lat2 = radians(first.lat), radians(second.lat)
    dlat = lat2 - lat1
    dlng = radians(second.lng - first.lng)
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlng / 2) ** 2
    return 2 * EARTH_RADIUS_KM * asin(sqrt(manual_min(1.0, manual_max(0.0, a))))


def estimate_minutes(distance_km):
    return manual_max(1, ceil(60 * ROAD_FACTOR * distance_km / SPEED_KMH))


def manual_order(values):
    """Merge sort by explicit comparisons.

    Input elements are IDs or tuples; merging uses explicit comparisons.
    """
    ordered = object_array(values)
    count = len(ordered)
    work = np.empty(count, dtype=object)
    width = 1
    while width < count:
        left = 0
        while left < count:
            middle = manual_min(left + width, count)
            end = manual_min(left + 2 * width, count)
            i, j, dest = left, middle, left
            while i < middle and j < end:
                if ordered[i] <= ordered[j]:
                    work[dest] = ordered[i]
                    i += 1
                else:
                    work[dest] = ordered[j]
                    j += 1
                dest += 1
            while i < middle:
                work[dest] = ordered[i]
                i += 1
                dest += 1
            while j < end:
                work[dest] = ordered[j]
                j += 1
                dest += 1
            left += 2 * width
        ordered, work = work, ordered
        width *= 2
    return ordered


def full_pairs(locations):
    """A distance-based connected backbone plus three nearest neighbors.

    Keep the named isolated farm outside every candidate set. Maintain the
    cheapest attachment of each remaining vertex to the connected component.
    Deterministic ID tie-breaking makes generated CSVs reproducible.
    """
    eligible = manual_order(farm_id for farm_id in locations if farm_id != ISOLATED_ID)
    remaining = LinkedList((farm_id for farm_id in eligible if farm_id != HUB_ID))
    best = manual_map(((farm_id, (haversine_km(locations[HUB_ID], locations[farm_id]), HUB_ID)) for farm_id in remaining))
    pairs = manual_map()
    while remaining:
        chosen = remaining[0]
        for farm_id in remaining:
            if (best[farm_id][0], farm_id) < (best[chosen][0], chosen):
                chosen = farm_id
        distance, parent = best[chosen]
        pair = (parent, chosen) if parent <= chosen else (chosen, parent)
        pairs[pair] = "Distance backbone"
        remaining = LinkedList((farm_id for farm_id in remaining if farm_id != chosen))
        for farm_id in remaining:
            candidate = (haversine_km(locations[chosen], locations[farm_id]), chosen)
            if candidate < best[farm_id]:
                best[farm_id] = candidate
    for first in eligible:
        candidates = manual_order((haversine_km(locations[first], locations[second]), second)
                                  for second in eligible if second != first)
        for distance, second in candidates[:3]:
            pair = (first, second) if first <= second else (second, first)
            if not manual_contains(pairs, pair):
                pairs[pair] = "Three-nearest-neighbor alternative"
    return LinkedList(((first, second, pairs[(first, second)]) for first, second in manual_order(pairs)))


def write_edges(path, pairs, locations):
    fields = ("FromID", "ToID", "TransportTime", "GreatCircleKm", "RoadFactor", "SpeedKmh", "Reason")
    with Path(path).open("w", encoding="utf-8", newline="") as stream:
        writer = CSVWriter(stream, fieldnames=fields)
        writer.writeheader()
        for first, second, reason in pairs:
            distance = haversine_km(locations[first], locations[second])
            writer.writerow(manual_map((
                ("FromID", first),
                ("ToID", second),
                ("TransportTime", estimate_minutes(distance)),
                ("GreatCircleKm", format(distance, ".9f")),
                ("RoadFactor", ROAD_FACTOR),
                ("SpeedKmh", SPEED_KMH),
                ("Reason", reason),
            )))


def build(data_dir=DEFAULT_DATA_DIR):
    data_dir = Path(data_dir)
    locations = read_farms(data_dir / "dataset.csv")
    hub = read_hub(data_dir / "hub.csv")
    locations[hub.farm_id] = hub
    selected = ManualSet((row["FarmID"] for row in read_csv(data_dir / "test_vertices.csv", ("FarmID",))))
    selected.add(HUB_ID)
    if not manual_all(manual_contains(selected, first) and manual_contains(selected, second) for first, second in TEST_PAIRS):
        raise ValueError("Test connections refer to a location outside the selected subset.")
    write_edges(data_dir / "test_edges.csv",
                LinkedList(((first, second, "Explicit demonstration connection") for first, second in TEST_PAIRS)),
                locations)
    write_edges(data_dir / "full_edges.csv", full_pairs(locations), locations)


if __name__ == "__main__":
    build()
    print("Rebuilt test_edges.csv and full_edges.csv from documented modelling rules.")
