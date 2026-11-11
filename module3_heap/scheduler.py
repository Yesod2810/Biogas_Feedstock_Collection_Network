"""Author: Thanh Dat Nguyen
Student ID: 23857030
Date: 3/10/2026
Purpose: Request scheduling obtains real records from Module 2 and routes from Module 1.
"""

from manual_structures import LinkedList, OpenAddressMap, manual_contains

from module1_graph.data_loader import HUB_ID
from module1_graph.graph import Graph
from module2_hash.hash_table import HashTable
from module2_hash.records import validate_id

from .max_heap import MaxHeap
from .requests import ScheduledRequest, calculation_text, feedstock_value, validate_request_id

class SchedulingError(ValueError):
    """A request cannot currently be accepted or dispatched."""


class CollectionScheduler:
    """One pending request per farm; unique RequestID throughout the session.

    Priorities are route snapshots for one network configuration. This Graph's
    public mutations only add vertices/edges, so count changes detect stale
    route snapshots in O(1). Reset the scheduling session after such a change.
    Dispatch rechecks the shared hash table and skips deleted/changed records.
    """

    def __init__(self, lookup, graph, hub_id=HUB_ID, emit=print, archive=None):
        if not isinstance(lookup, HashTable) or not isinstance(graph, Graph):
            raise SchedulingError("Use the Module 2 HashTable and Module 1 Graph.")
        if not graph.has_vertex(hub_id):
            raise SchedulingError("The processing hub is not a graph vertex.")
        self.lookup = lookup
        self.graph = graph
        self.hub_id = hub_id
        self._graph_counts = (graph.vertex_count, graph.edge_count)
        self._emit = emit
        self.heap = MaxHeap(emit=emit)
        self._seen_request_ids = OpenAddressMap(track_order=False)
        self._pending_farms = OpenAddressMap(track_order=False)
        self.last_skipped = ()
        self.collected_count = 0
        self.archive = archive

    def _archive(self, request, status, detail=''):
        """An optional Module 4 recorder persists a snapshot before queue mutation."""
        if self.archive is not None:
            try:
                self.archive.record(request, status, detail)
            except ValueError as error:
                raise SchedulingError("Collection archive: {}".format(error)) from error

    def cancel_pending(self, detail='Scheduling session reset.'):
        """Retain cancelled request history when a UI explicitly clears the queue."""
        for request in self.heap.snapshot():
            self._archive(request, 'cancelled', detail)

    def _message(self, text):
        if self._emit is not None:
            self._emit(text)

    def rebind_lookup(self, lookup):
        """A Module 2 reload replaces the shared index, without trusting old records."""
        if not isinstance(lookup, HashTable):
            raise SchedulingError("The lookup must be the Module 2 HashTable.")
        self.lookup = lookup

    def _require_current_graph(self):
        if self._graph_counts != (self.graph.vertex_count, self.graph.edge_count):
            raise SchedulingError("Network changed: reset the scheduling session before using queued priorities.")

    def submit(self, request_id, farm_id, estimated_feedstock):
        """Lookup -> locate -> Dijkstra(farm, hub) -> calculate -> heap insertion."""
        self._require_current_graph()
        validate_request_id(request_id)
        validate_id(farm_id)
        quantity = feedstock_value(estimated_feedstock)
        if manual_contains(self._seen_request_ids, request_id):
            raise SchedulingError("Duplicate collection RequestID {}.".format(request_id))
        farm = self.lookup.search(farm_id)
        if farm is None:
            raise SchedulingError("Farm record {} is missing or has been deleted from the hash table.".format(farm_id))
        if manual_contains(self._pending_farms, farm_id):
            raise SchedulingError("Farm {} already has a pending collection request.".format(farm_id))
        if not self.graph.has_vertex(farm_id):
            raise SchedulingError("Farm {} is not in the selected graph; no valid collection route can currently be calculated.".format(farm_id))
        location = self.graph.location(farm_id)
        if location.lat != farm.lat or location.lng != farm.lng:
            raise SchedulingError("Hash and graph coordinates disagree for FarmID {}.".format(farm_id))
        route = self.graph.dijkstra(farm_id, self.hub_id)
        if not route.reachable:
            raise SchedulingError("Unreachable farm {}: a valid collection route cannot currently be calculated.".format(farm_id))
        request = ScheduledRequest(request_id, farm, quantity, route.minutes, route.path)
        self._archive(request, 'pending')
        self._message(calculation_text(request))
        self.heap.insert(request)
        self._seen_request_ids[request_id] = True
        self._pending_farms[farm_id] = True
        return request

    def _record_problem(self, request):
        current = self.lookup.search(request.farm_id)
        if current is None:
            return "farm record missing/deleted from the hash table"
        if current != request.farm:
            return "farm information changed since priority calculation"
        return None

    def peek(self):
        """Inspect without removing; report a deleted/changed root without hiding it."""
        self._require_current_graph()
        request = self.heap.peek()
        if request is not None:
            problem = self._record_problem(request)
            if problem is not None:
                raise SchedulingError("Highest request {} is stale: {}; extraction will skip it.".format(
                    request.request_id, problem))
        return request

    def extract_priority(self):
        """Remove highest entries; skip stale farms and return the next eligible one."""
        self._require_current_graph()
        skipped = LinkedList()
        self.last_skipped = ()
        if self.heap.size == 0:
            self.heap.extract_priority()
        while self.heap.size > 0:
            request = self.heap.peek()
            problem = self._record_problem(request)
            self._archive(request, 'collected' if problem is None else 'skipped', problem or '')
            self.heap.extract_priority()
            self._pending_farms.discard(request.farm_id)
            if problem is None:
                self.last_skipped = tuple(skipped)
                self.collected_count += 1
                self._message("COLLECT {} | farm={} | P={:.6f} | F={:g} tonnes | T={:g} minutes".format(
                    request.request_id, request.farm_id, request.priority,
                    request.feedstock, request.transport_minutes))
                return request
            skipped.append((request.request_id, request.farm_id, problem))
            self._message("SKIP {} | farm={} | {}".format(request.request_id, request.farm_id, problem))
        self.last_skipped = tuple(skipped)
        self._message("Empty heap: no eligible collection request remains.")
        return None
