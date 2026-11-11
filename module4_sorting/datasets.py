"""Author: Thanh Dat Nguyen
Student ID: 23857030
Date: 11/10/2026
Purpose: Reproducible request scenarios whose times come from the actual farm graph.
"""

from manual_structures import (
    LinkedList, ManualSet, manual_contains, manual_map, manual_sample,
    manual_shuffle, object_array
)

from math import floor
from random import Random
import numpy as np

from module1_graph.data_loader import DEFAULT_DATA_DIR, HUB_ID, load_network
from module2_hash.data_loader import load_lookup
from module3_heap.requests import ScheduledRequest

from .algorithms import merge_sort
from .records import CollectionRecord, SortDataError

SEED = 23857030
SIZES = (100, 500, 1000)
CONDITIONS = ('random', 'nearly_sorted', 'reversed')


def generate_records(count=1000, seed=SEED, data_dir=DEFAULT_DATA_DIR):
    """Cache one Dijkstra(farm, hub) route for each reachable real farm.

    Multiple request events may refer to one farm, with unique request IDs and
    educational F values. They are historic modelling records, not simultaneous
    pending requests. Only F and farm/event selection use pseudo-random numbers;
    every T is copied from the graph's shortest-route result.
    """
    if isinstance(count, bool) or not isinstance(count, int) or count < 0:
        raise SortDataError("Record count must be a non-negative integer.")
    lookup = load_lookup(data_dir / 'dataset.csv')
    graph = load_network('full', data_dir)
    routes, excluded = LinkedList(), LinkedList()
    for source in lookup.records:
        farm = lookup.table.search(source.farm_id)
        route = graph.dijkstra(farm.farm_id, HUB_ID)
        if route.reachable:
            routes.append((farm, route))
        else:
            excluded.append(farm.farm_id)
    routes = object_array(routes)
    if count and len(routes) == 0:
        raise SortDataError("There is no reachable farm for sorting experiments.")
    rng = Random(seed)
    records = np.empty(count, dtype=object)
    for index in range(count):
        farm, route = routes[rng.randrange(len(routes))]
        quantity = rng.randint(4, 60) / 2.0
        request_id = 'B{:06d}'.format(index + 1)
        request = ScheduledRequest(request_id, farm, quantity, route.minutes, route.path)
        records[index] = CollectionRecord(request_id, request)
    metadata = manual_map((
        ('seed', seed),
        ('network', 'full'),
        ('vertices', graph.vertex_count),
        ('edges', graph.edge_count),
        ('source_farm_count', len(lookup.records)),
        ('reachable_farm_count', len(routes)),
        ('excluded_unreachable', excluded),
        ('dijkstra_calls', len(lookup.records)),
        ('requests_generated', count),
        ('priority_formula', 'F / (T + 1 minute)'),
        ('feedstock_provenance', 'Educational 2-30 tonne scenarios; not source production figures.'),
        ('route_cache', LinkedList((manual_map((
            ('FarmID', farm.farm_id),
            ('TransportTime', route.minutes),
            ('Path', LinkedList(route.path)),
        )) for farm, route in routes))),
    ))
    return records, metadata


def make_condition(records, condition, seed=SEED):
    """Rearrange records for the requested input condition.
       For the nearly_sorted condition, at most 10% of record
       identities displaced relative to the sorted baseline."""
    if not manual_contains(CONDITIONS, condition):
        raise SortDataError("Use random, nearly_sorted or reversed input.")
    baseline = merge_sort(records)
    result = object_array(baseline)
    rng = Random(seed)
    if condition == 'random':
        manual_shuffle(result, rng)
    elif condition == 'reversed':
        left, right = 0, len(result) - 1
        while left < right:
            result[left], result[right] = result[right], result[left]
            left += 1
            right -= 1
    else:
        displaced_limit = floor(len(result) / 10)
        displaced_limit -= displaced_limit % 2
        selected = manual_sample(range(len(result)), displaced_limit, rng)
        for index in range(0, displaced_limit, 2):
            first, second = selected[index], selected[index + 1]
            result[first], result[second] = result[second], result[first]
    displaced = sum(first.record_id != second.record_id for first, second in zip(result, baseline))
    if condition == 'nearly_sorted' and displaced > len(result) // 10:
        raise AssertionError("Nearly sorted displacement limit was exceeded.")
    return result, manual_map((
        ('condition', condition),
        ('condition_seed', seed),
        ('displaced_records', displaced),
        ('displaced_fraction', displaced / len(result) if len(result) else 0.0),
        ('adjacent_descents', sum(result[i - 1].transport_minutes > result[i].transport_minutes
                                             for i in range(1, len(result)))),
        ('distinct_times', len(ManualSet((record.transport_minutes for record in result)))),
    ))
