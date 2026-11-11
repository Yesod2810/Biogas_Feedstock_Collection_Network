"""Author: Thanh Dat Nguyen
Student ID: 23857030
Date: 21/09/2026
Purpose: Behavioural graph tests, including an independent tiny-graph path oracle.
"""

from manual_structures import LinkedList, ManualSet, manual_contains, manual_map, manual_min
from test_support import SequenceTestCase

import math
import random
import unittest

from module1_graph.graph import Graph, GraphError, Location


def graph_with(ids, edges=()):
    graph = Graph()
    for farm_id in ids:
        graph.add_vertex(Location(farm_id, "Location " + farm_id))
    for first, second, minutes in edges:
        graph.add_edge(first, second, minutes)
    return graph


class ConstructionTests(SequenceTestCase):
    def setUp(self):
        self.graph = graph_with(("A", "B", "I"))

    def test_empty_graph(self):
        graph = Graph()
        self.assertEqual((graph.vertex_count, graph.edge_count), (0, 0))
        self.assertEqual(tuple(graph.edges()), ())

    def test_dynamic_vertex_starts_isolated(self):
        self.graph.add_vertex(Location("C", "New farm"))
        self.assertEqual(self.graph.neighbors("C"), ())
        self.assertEqual(self.graph.vertex_count, 4)

    def test_undirected_edge_has_two_equal_records(self):
        self.graph.add_edge("A", "B", 7)
        self.assertEqual(self.graph.neighbors("A")[0].destination, "B")
        self.assertEqual(self.graph.neighbors("B")[0].destination, "A")
        self.assertEqual(self.graph.neighbors("B")[0].minutes, 7)
        self.assertEqual(self.graph.edge_count, 1)
        self.assertEqual(len(tuple(self.graph.edges())), 1)

    def test_duplicate_id_does_not_replace_location(self):
        with self.assertRaisesRegex(GraphError, "Duplicate location"):
            self.graph.add_vertex(Location("A", "Replacement"))
        self.assertEqual(self.graph.location("A").name, "Location A")
        self.assertEqual(self.graph.vertex_count, 3)

    def test_same_name_and_coordinates_with_different_ids_are_distinct(self):
        graph = Graph()
        graph.add_vertex(Location("one", "Unknown", -32, 116))
        graph.add_vertex(Location("two", "Unknown", -32, 116))
        self.assertEqual(graph.vertex_count, 2)

    def test_duplicate_edge_in_either_direction_is_atomic(self):
        self.graph.add_edge("A", "B", 7)
        before = self.graph.describe()
        for first, second in LinkedList((("A", "B"), ("B", "A"))):
            with self.subTest(first=first):
                with self.assertRaisesRegex(GraphError, "Duplicate undirected"):
                    self.graph.add_edge(first, second, 99)
                self.assertEqual(self.graph.describe(), before)

    def test_invalid_endpoint_does_not_insert_half_edge(self):
        for first, second in LinkedList((("A", "missing"), ("missing", "A"))):
            with self.subTest(first=first):
                with self.assertRaises(GraphError):
                    self.graph.add_edge(first, second, 5)
        self.assertEqual(self.graph.edge_count, 0)
        self.assertEqual(self.graph.neighbors("A"), ())

    def test_invalid_weights(self):
        for value in (0, -1, math.inf, -math.inf, math.nan, True, False, "5", None,
                      complex(1, 2), 10 ** 1000):
            with self.subTest(value=repr(value)[:40]):
                with self.assertRaises(GraphError):
                    self.graph.add_edge("A", "B", value)
                self.assertEqual(self.graph.edge_count, 0)

    def test_fractional_positive_weight(self):
        self.graph.add_edge("A", "B", 0.125)
        self.assertEqual(self.graph.dijkstra("A", "B").minutes, 0.125)

    def test_reject_self_loop(self):
        with self.assertRaisesRegex(GraphError, "Self-loops"):
            self.graph.add_edge("A", "A", 1)
        self.assertEqual(self.graph.edge_count, 0)

    def test_invalid_vertex_ids(self):
        for farm_id in ("", "  ", " A", "A ", 1, None, LinkedList()):
            with self.subTest(farm_id=farm_id):
                with self.assertRaises(GraphError):
                    self.graph.add_vertex(Location(farm_id, "Farm"))

    def test_invalid_vertex_object_or_name(self):
        for value in ("A", None, Location("C", ""), Location("C", None)):
            with self.subTest(value=value):
                with self.assertRaises(GraphError):
                    self.graph.add_vertex(value)

    def test_invalid_coordinates(self):
        for lat, lng in ((91, 116), (-91, 116), (-32, 181), (-32, math.nan),
                         (math.inf, 116), (None, 116), (-32, None), (True, 116)):
            with self.subTest(lat=lat, lng=lng):
                with self.assertRaises(GraphError):
                    self.graph.add_vertex(Location("C", "Farm", lat, lng))

    def test_public_neighbor_result_cannot_modify_graph(self):
        self.graph.add_edge("A", "B", 3)
        neighbors = self.graph.neighbors("A")
        self.assertIsInstance(neighbors, tuple)
        self.assertEqual(self.graph.edge_count, 1)

    def test_describe_reports_isolate(self):
        self.assertIn("I | Location I: [isolated]", self.graph.describe())


class TraversalTests(SequenceTestCase):
    def setUp(self):
        self.graph = graph_with(("A", "B", "C", "D", "E", "I"), (
            ("A", "B", 50), ("A", "C", 1), ("B", "D", 2),
            ("C", "D", 3), ("D", "E", 4)))

    def test_bfs_groups_by_hop_count(self):
        result = self.graph.bfs("A")
        self.assertEqual(result.levels, (("A",), ("B", "C"), ("D",), ("E",)))
        self.assertEqual(result.unreachable, ("I",))

    def test_bfs_does_not_repeat_shared_neighbor(self):
        flattened = LinkedList((item for group in self.graph.bfs("A").levels for item in group))
        self.assertEqual(len(flattened), len(ManualSet(flattened)))

    def test_bfs_isolated_source(self):
        result = self.graph.bfs("I")
        self.assertEqual(result.levels, (("I",),))
        self.assertEqual(len(result.unreachable), 5)

    def test_bfs_invalid_source(self):
        with self.assertRaisesRegex(GraphError, "Invalid location"):
            self.graph.bfs("missing")

    def test_dfs_cycle_is_a_valid_closed_witness(self):
        result = self.graph.dfs("A")
        self.assertTrue(result.has_cycle)
        self.assertEqual(result.cycle[0], result.cycle[-1])
        self.assertEqual(len(ManualSet(result.cycle[:-1])), len(result.cycle) - 1)
        self.assertGreaterEqual(len(result.cycle), 4)
        for first, second in zip(result.cycle, result.cycle[1:]):
            self.assertTrue(self.graph.has_edge(first, second))

    def test_dfs_visits_isolated_and_disconnected_locations(self):
        result = self.graph.dfs("A")
        self.assertEqual(ManualSet(result.order), ManualSet(self.graph.vertex_ids()))
        self.assertEqual(result.components[-1], ("I",))
        self.assertEqual(len(result.order), len(ManualSet(result.order)))

    def test_dfs_starting_at_isolate_still_checks_network(self):
        result = self.graph.dfs("I")
        self.assertEqual(result.components[0], ("I",))
        self.assertTrue(result.has_cycle)
        self.assertEqual(len(result.order), 6)

    def test_dfs_finds_cycle_in_a_different_component(self):
        graph = graph_with(("A", "B", "X", "Y", "Z", "I"), (
            ("A", "B", 1), ("X", "Y", 1), ("Y", "Z", 1), ("Z", "X", 1)))
        result = graph.dfs("A")
        self.assertTrue(result.has_cycle)
        self.assertEqual(ManualSet(result.cycle), ManualSet(("X", "Y", "Z")))
        self.assertEqual(len(result.components), 3)

    def test_dfs_component_only_scope(self):
        result = self.graph.dfs("I", all_components=False)
        self.assertFalse(result.has_cycle)
        self.assertEqual(result.order, ("I",))
        self.assertFalse(result.whole_graph)

    def test_dfs_parent_edge_is_not_a_cycle(self):
        graph = graph_with(("A", "B", "C", "I"), (("A", "B", 1), ("B", "C", 1)))
        self.assertFalse(graph.dfs("A").has_cycle)

    def test_dfs_all_isolated_graph_is_acyclic(self):
        graph = graph_with(("A", "B", "I"))
        result = graph.dfs("B")
        self.assertFalse(result.has_cycle)
        self.assertEqual(result.components, (("B",), ("A",), ("I",)))

    def test_dfs_invalid_source(self):
        with self.assertRaises(GraphError):
            self.graph.dfs("missing")

    def test_iterative_dfs_handles_long_chain(self):
        ids = LinkedList((str(number) for number in range(1500)))
        graph = graph_with(ids, ((ids[i], ids[i + 1], 1) for i in range(len(ids) - 1)))
        result = graph.dfs("0")
        self.assertEqual(len(result.order), 1500)
        self.assertFalse(result.has_cycle)


class ShortestPathTests(SequenceTestCase):
    def setUp(self):
        self.graph = graph_with(("A", "B", "C", "D", "I"), (
            ("A", "B", 10), ("A", "C", 2), ("C", "D", 2), ("D", "B", 2)))

    def test_more_hops_can_have_lower_transport_time(self):
        result = self.graph.dijkstra("A", "B")
        self.assertEqual(result.path, ("A", "C", "D", "B"))
        self.assertEqual(result.minutes, 6)
        self.assertEqual(self.graph.bfs("A").levels[1], ("B", "C"))

    def test_reverse_route(self):
        result = self.graph.dijkstra("B", "A")
        self.assertEqual(result.path, ("B", "D", "C", "A"))
        self.assertEqual(result.minutes, 6)

    def test_source_equals_destination(self):
        result = self.graph.dijkstra("A", "A")
        self.assertEqual((result.path, result.minutes), (("A",), 0))

    def test_isolated_source_equals_destination(self):
        result = self.graph.dijkstra("I", "I")
        self.assertEqual((result.path, result.minutes), (("I",), 0))

    def test_unreachable_destination(self):
        result = self.graph.dijkstra("A", "I")
        self.assertFalse(result.reachable)
        self.assertEqual(result.path, ())
        self.assertEqual(result.minutes, math.inf)

    def test_unreachable_from_isolate(self):
        self.assertFalse(self.graph.dijkstra("I", "A").reachable)

    def test_invalid_endpoints(self):
        for first, second in (("missing", "A"), ("A", "missing"), ("missing", "missing")):
            with self.subTest(first=first):
                with self.assertRaises(GraphError):
                    self.graph.dijkstra(first, second)

    def test_tie_breaking_is_repeatable(self):
        graph = graph_with(("A", "B", "C", "D"), (
            ("A", "C", 1), ("A", "B", 1), ("B", "D", 1), ("C", "D", 1)))
        self.assertEqual(graph.dijkstra("A", "D").path, ("A", "B", "D"))

    def test_late_vertex_insertion_and_connection(self):
        self.graph.add_vertex(Location("NEW", "New farm"))
        self.assertFalse(self.graph.dijkstra("A", "NEW").reachable)
        self.graph.add_edge("D", "NEW", 1)
        self.assertEqual(self.graph.dijkstra("A", "NEW").minutes, 5)

    def test_against_exhaustive_simple_path_oracle(self):
        # This independent test enumerates simple paths on six-vertex fixtures.
        # It deliberately does not call a built-in shortest-path algorithm.
        rng = random.Random(23857030)
        for fixture in range(8):
            ids = tuple("ABCDEF")
            graph = graph_with(ids)
            adjacency = manual_map(((farm_id, LinkedList()) for farm_id in ids))
            for i, first in enumerate(ids):
                for second in ids[i + 1:]:
                    if rng.random() < 0.40:
                        minutes = rng.randint(1, 20)
                        graph.add_edge(first, second, minutes)
                        adjacency[first].append((second, minutes))
                        adjacency[second].append((first, minutes))

            def enumerate_paths(current, destination, seen, cost):
                if current == destination:
                    return cost
                answer = math.inf
                for neighbor, minutes in adjacency[current]:
                    if not manual_contains(seen, neighbor):
                        answer = manual_min(answer, enumerate_paths(neighbor, destination,
                                                             seen | ManualSet((neighbor,)), cost + minutes))
                return answer

            for source in ids:
                for destination in ids:
                    with self.subTest(fixture=fixture, source=source, destination=destination):
                        expected = enumerate_paths(source, destination, ManualSet((source,)), 0)
                        result = graph.dijkstra(source, destination)
                        self.assertEqual(result.minutes, expected)
                        if result.reachable:
                            self.assertEqual(result.path[0], source)
                            self.assertEqual(result.path[-1], destination)
                            cost = 0
                            for first, second in zip(result.path, result.path[1:]):
                                for neighbor, weight in adjacency[first]:
                                    if neighbor == second:
                                        cost += weight
                                        break
                            self.assertEqual(cost, expected)


if __name__ == "__main__":
    unittest.main()
