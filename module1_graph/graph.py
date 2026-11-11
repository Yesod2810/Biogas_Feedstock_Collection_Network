"""Author: Thanh Dat Nguyen
Student ID: 23857030
Date: 20/09/2026
Purpose: Adjacency-list graph and manually implemented BFS, DFS and Dijkstra.

Graph adjacency and vertex indexes are student-implemented linked lists and
modulo-hash arrays. Traversals use custom linked queue/stack.
"""

from manual_structures import (
    LinkedList, LinkedQueue, LinkedStack, OpenAddressMap, manual_contains,
    object_array
)

from dataclasses import dataclass
from math import inf, isfinite
import numpy as np


class GraphError(ValueError):
    """A graph operation would violate the graph's public contract."""


def _finite_number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    try:
        return isfinite(value)
    except OverflowError:
        return False


@dataclass(frozen=True)
class Location:
    farm_id: str
    name: str
    lat: float = None
    lng: float = None
    species: str = ""
    suburb: str = ""
    kind: str = "farm"


@dataclass(frozen=True)
class Edge:
    destination: str
    minutes: float


@dataclass(frozen=True)
class BFSResult:
    source: str
    levels: tuple
    unreachable: tuple


@dataclass(frozen=True)
class DFSResult:
    source: str
    order: tuple
    components: tuple
    cycle: tuple
    whole_graph: bool

    @property
    def has_cycle(self):
        return len(self.cycle) > 0


@dataclass(frozen=True)
class PathResult:
    source: str
    destination: str
    minutes: float
    path: tuple
    settled: tuple

    @property
    def reachable(self):
        return isfinite(self.minutes)


class Graph:
    """A simple weighted undirected graph with dynamically inserted vertices.

    _adjacency maps each ID to a linked list of Edge records. Each logical edge has
    exactly two adjacency records. Duplicate IDs/edges and self-loops are
    rejected; separate IDs with equal names or coordinates remain separate.
    Insertion order makes traversals and equal-cost path selection repeatable.
    """

    def __init__(self):
        self._locations = OpenAddressMap()
        self._adjacency = OpenAddressMap()
        self._edge_count = 0

    @property
    def vertex_count(self):
        return len(self._locations)

    @property
    def edge_count(self):
        return self._edge_count

    def vertex_ids(self):
        return tuple(self._locations)

    def has_vertex(self, farm_id):
        return isinstance(farm_id, str) and manual_contains(self._locations, farm_id)

    def _require_vertex(self, farm_id):
        if not self.has_vertex(farm_id):
            raise GraphError("Invalid location ID: {!r}.".format(farm_id))

    def location(self, farm_id):
        self._require_vertex(farm_id)
        return self._locations[farm_id]

    def add_vertex(self, location):
        """Insert an isolated vertex; never silently overwrite existing data."""
        if not isinstance(location, Location):
            raise GraphError("A vertex must be a Location object.")
        farm_id = location.farm_id
        if not isinstance(farm_id, str) or not farm_id or farm_id != farm_id.strip():
            raise GraphError("Location ID must be a non-empty, unpadded string.")
        if not isinstance(location.name, str) or not location.name.strip():
            raise GraphError("Location name must not be blank.")
        if manual_contains(self._locations, farm_id):
            raise GraphError("Duplicate location ID: {}.".format(farm_id))
        if (location.lat is None) != (location.lng is None):
            raise GraphError("Supply both latitude and longitude, or neither.")
        if location.lat is not None:
            for value, limit, label in LinkedList(((location.lat, 90, "latitude"), (location.lng, 180, "longitude"))):
                if not _finite_number(value) or not -limit <= value <= limit:
                    raise GraphError("Invalid {}.".format(label))
        self._locations[farm_id] = location
        self._adjacency[farm_id] = LinkedList()

    def neighbors(self, farm_id):
        """Return immutable records without exposing mutable adjacency lists."""
        self._require_vertex(farm_id)
        return tuple(self._adjacency[farm_id])

    def has_edge(self, first, second):
        self._require_vertex(first)
        self._require_vertex(second)
        for edge in self._adjacency[first]:
            if edge.destination == second:
                return True
        return False

    def add_edge(self, first, second, minutes):
        """Validate everything before inserting either direction."""
        self._require_vertex(first)
        self._require_vertex(second)
        if first == second:
            raise GraphError("Self-loops are not allowed in this simple graph.")
        if not _finite_number(minutes) or minutes <= 0:
            raise GraphError("Transport time must be a finite positive number.")
        if self.has_edge(first, second):
            raise GraphError("Duplicate undirected edge: {} <-> {}.".format(first, second))
        self._adjacency[first].append(Edge(second, float(minutes)))
        self._adjacency[second].append(Edge(first, float(minutes)))
        self._edge_count += 1

    def edges(self):
        """Yield each undirected edge once, in a deterministic order."""
        for first in self._locations:
            for edge in self._adjacency[first]:
                if first < edge.destination:
                    yield first, edge.destination, edge.minutes

    def bfs(self, source):
        """Group reachable locations by minimum number of edges from source.

        A linked FIFO queue performs O(1) enqueue/dequeue.
        Marking on enqueue prevents the same vertex being queued twice.
        """
        self._require_vertex(source)
        queue = LinkedQueue()
        queue.enqueue(source)
        distance = OpenAddressMap()
        distance[source] = 0
        levels = np.empty(self.vertex_count, dtype=object)
        level_count = 1
        levels[0] = LinkedList((source,))
        while queue:
            current = queue.dequeue()
            for edge in self._adjacency[current]:
                neighbor = edge.destination
                if not manual_contains(distance, neighbor):
                    level = distance[current] + 1
                    distance[neighbor] = level
                    if level == level_count:
                        levels[level] = LinkedList()
                        level_count += 1
                    levels[level].append(neighbor)
                    queue.enqueue(neighbor)
        unreachable = tuple(farm_id for farm_id in self._locations
                            if not manual_contains(distance, farm_id))
        return BFSResult(source, tuple(tuple(levels[index]) for index in range(level_count)), unreachable)

    def dfs(self, source, all_components=True):
        """Find one cycle witness and complete the requested DFS traversal.

        By default, start at source and then visit every unvisited component.
        A stack frame stores (vertex, next-neighbor linked-list node).
        Following next pointers keeps DFS O(V+E) expected bound when operations
        on a graph map have an expected cost of O(1). Grey (1) vertices
        are on the active path; black (2) vertices are finished. Ignore only
        the parent edge, because its reverse is normal in an undirected graph.
        Set all_components=False to inspect only the source's component.
        """
        self._require_vertex(source)
        roots = LinkedList()
        roots.append(source)
        if all_components:
            for farm_id in self._locations:
                if farm_id != source:
                    roots.append(farm_id)
        color = OpenAddressMap()
        for farm_id in self._locations:
            color[farm_id] = 0
        parent = OpenAddressMap()
        order = LinkedList()
        components = LinkedList()
        cycle = ()
        for root in roots:
            if color[root] == 0:
                component = LinkedList((root,))
                order.append(root)
                color[root] = 1
                parent[root] = None
                stack = LinkedStack()
                stack.push((root, self._adjacency[root]._head))
                while stack:
                    current, neighbor_node = stack.peek()
                    if neighbor_node is None:
                        color[current] = 2
                        stack.take()
                    else:
                        edge = neighbor_node.value
                        stack.replace_top((current, neighbor_node.next_node))
                        neighbor = edge.destination
                        if color[neighbor] == 0:
                            parent[neighbor] = current
                            color[neighbor] = 1
                            component.append(neighbor)
                            order.append(neighbor)
                            stack.push((neighbor, self._adjacency[neighbor]._head))
                        elif neighbor != parent[current] and color[neighbor] == 1:
                            if not cycle:
                                active_path = object_array(frame[0] for frame in stack)
                                start = 0
                                while start < len(active_path) and active_path[start] != neighbor:
                                    start += 1
                                cycle = tuple(active_path[index] for index in range(start, len(active_path))) + (neighbor,)
                components.append(tuple(component))
        return DFSResult(source, tuple(order), tuple(components), cycle, all_components)

    def dijkstra(self, source, destination):
        """Return the minimum-minute route using manual linear selection.

        Tentative distances start at infinity except the source (zero). On
        every iteration, settle the closest unvisited finite-distance vertex,
        then relax its outgoing edges. Positive weights make settlement final.
        Stop when the destination is settled or no reachable candidate remains.
        """
        self._require_vertex(source)
        self._require_vertex(destination)
        distance = OpenAddressMap()
        previous = OpenAddressMap()
        visited = OpenAddressMap()
        for farm_id in self._locations:
            distance[farm_id] = inf
            previous[farm_id] = None
        settled = LinkedList()
        distance[source] = 0.0
        searching = True
        while searching:
            current = None
            best = inf
            for farm_id in self._locations:
                if not manual_contains(visited, farm_id) and distance[farm_id] < best:
                    current = farm_id
                    best = distance[farm_id]
            if current is None:
                searching = False
            else:
                visited[current] = True
                settled.append(current)
                if current == destination:
                    searching = False
                else:
                    for edge in self._adjacency[current]:
                        neighbor = edge.destination
                        if not manual_contains(visited, neighbor):
                            candidate = distance[current] + edge.minutes
                            if candidate < distance[neighbor]:
                                distance[neighbor] = candidate
                                previous[neighbor] = current
        path = LinkedList()
        if isfinite(distance[destination]):
            current = destination
            while current is not None:
                path.prepend(current)
                current = previous[current]
        return PathResult(source, destination, distance[destination], tuple(path),
                          tuple(settled))

    def describe(self):
        """A textual graph structure containing both directions and isolates."""
        lines = LinkedList(("Vertices: {} | Undirected edges: {}".format(
            self.vertex_count, self.edge_count),))
        for farm_id, location in self._locations.items():
            connections = "; ".join("{} ({} min)".format(e.destination, format(e.minutes, "g"))
                                     for e in self._adjacency[farm_id])
            if not connections:
                connections = "[isolated]"
            lines.append("{} | {}: {}".format(farm_id, location.name, connections))
        return "\n".join(lines)
