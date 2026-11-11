"""Author: Thanh Dat Nguyen
Student ID: 23857030
Date: 20/09/2026
Purpose: Readable output shared by the interactive menu and reproducible examples.
"""

from manual_structures import LinkedList

from .data_loader import HUB_ID, ISOLATED_ID, check_specification
from .graph import GraphError


def label(graph, farm_id):
    return "{} [{}]".format(graph.location(farm_id).name, farm_id)


def bfs_text(graph, source):
    result = graph.bfs(source)
    lines = LinkedList(("BFS from {}".format(label(graph, source)), "Levels count edges, not weighted transport minutes."))
    for number, group in enumerate(result.levels):
        lines.append("Level {}: {}".format(number, "; ".join(label(graph, item) for item in group)))
    if result.unreachable:
        lines.append("Unreachable: " + "; ".join(label(graph, item) for item in result.unreachable))
    else:
        lines.append("Unreachable: none")
    return "\n".join(lines)


def dfs_text(graph, source):
    result = graph.dfs(source)
    lines = LinkedList((
        "DFS starting at {} (whole graph)".format(label(graph, source)),
        "Cycle exists: {}".format("YES" if result.has_cycle else "NO"),
    ))
    if result.has_cycle:
        lines.append("Detected cycle: " + " -> ".join(label(graph, item) for item in result.cycle))
    for number, component in enumerate(result.components, start=1):
        lines.append("Component {}: {}".format(number, " -> ".join(component)))
    lines.append("Visited {} of {} locations.".format(len(result.order), graph.vertex_count))
    return "\n".join(lines)


def path_text(graph, source, destination):
    result = graph.dijkstra(source, destination)
    lines = LinkedList(("Dijkstra: {} -> {}".format(label(graph, source), label(graph, destination)),))
    if result.reachable:
        lines.append("Path: " + " -> ".join(label(graph, item) for item in result.path))
        lines.append("Shortest transportation time: {} minutes".format(format(result.minutes, "g")))
        if len(result.path) > 1:
            legs = LinkedList()
            for first, second in zip(result.path, result.path[1:]):
                weight = None
                for edge in graph.neighbors(first):
                    if edge.destination == second:
                        weight = edge.minutes
                        break
                if weight is None:
                    raise ValueError("The path includes an unconnected pair of vertices.")
                legs.append(format(weight, "g"))
            lines.append("Leg times: {} = {} minutes".format(" + ".join(legs), format(result.minutes, "g")))
    else:
        lines.append("Unreachable location: no transportation route exists.")
    return "\n".join(lines)


def specification_text(graph):
    lines = LinkedList((
        "TEST-GRAPH SPECIFICATION (Section 4.2.5)",
        "Vertices: {} | Undirected edges: {}".format(graph.vertex_count, graph.edge_count),
    ))
    for requirement, passed in check_specification(graph).items():
        lines.append("{}: {}".format("PASS" if passed else "FAIL", requirement))
    return "\n".join(lines)


def demo_text(graph, mode):
    sections = LinkedList((
        "COMP5008 | Module 1 | {} network".format(mode.upper()),
        "All transport times are educational estimates, in minutes.",
        specification_text(graph),
        "GRAPH STRUCTURE\n" + graph.describe(),
        bfs_text(graph, HUB_ID),
        dfs_text(graph, HUB_ID),
        path_text(graph, HUB_ID, "f4386"),
        path_text(graph, "f4386", HUB_ID),
        path_text(graph, HUB_ID, ISOLATED_ID),
        path_text(graph, ISOLATED_ID, ISOLATED_ID),
        "ISOLATED-SOURCE BFS\n" + bfs_text(graph, ISOLATED_ID),
    ))
    try:
        graph.dijkstra(HUB_ID, "NOT_A_LOCATION")
    except GraphError as error:
        sections.append("INVALID-LOCATION EXAMPLE\n" + str(error))
    return "\n\n".join(sections) + "\n"
