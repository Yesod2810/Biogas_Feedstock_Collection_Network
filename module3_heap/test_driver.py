"""Author: Thanh Dat Nguyen
Student ID: 23857030
Date: 3/10/2026
Purpose: Executable evidence: 10 insertions, 10 collections and all requested edge cases.
"""

from manual_structures import LinkedList, manual_any, manual_map


import argparse
from pathlib import Path

from module1_graph.data_loader import DEFAULT_DATA_DIR, HUB_ID, DataError, load_network
from module1_graph.graph import Graph, GraphError
from module2_hash.data_loader import HashDataError, load_lookup
from module2_hash.hash_table import HashTable
from module2_hash.records import RecordValidationError

from .data_loader import RequestDataError, read_requests
from .requests import RequestValidationError
from .scheduler import CollectionScheduler, SchedulingError


def request_summary(request):
    return manual_map((
        ("RequestID", request.request_id),
        ("FarmID", request.farm_id),
        ("Name", request.farm.name),
        ("EstimatedFeedstock", request.feedstock),
        ("TransportTime", request.transport_minutes),
        ("CollectionPriority", request.priority),
        ("Path", LinkedList(request.path)),
    ))


def state_summary(scheduler, operation, request_id):
    return manual_map((
        ("operation", operation),
        ("RequestID", request_id),
        ("array", LinkedList((request_summary(request) for request in scheduler.heap.snapshot()))),
        ("swaps", LinkedList(scheduler.heap.last_swaps)),
    ))


def run_demo(mode="test", data_dir=DEFAULT_DATA_DIR):
    data_dir = Path(data_dir)
    lookup = load_lookup(data_dir / "dataset.csv").table
    graph = load_network(mode, data_dir)
    lines, heap_traces = LinkedList(), LinkedList()
    phase = "MAIN"

    def emit(message):
        lines.append(message)
        if message.startswith("HEAP after"):
            heap_traces.append("{}\n{}".format(phase, message))

    lines += LinkedList((
        "COMP5008 | MODULE 3 | HEAP-BASED FEEDSTOCK COLLECTION",
        "Network: {} | Formula P=F/(T+1) | F in modelled tonnes; T in minutes".format(mode),
        "Feedstock values are educational scenarios, not source website production figures.",
        "Max heap; exact priority ties use FIFO insertion order.",
        "\nMAIN REQUEST INSERTIONS",
    ))
    scheduler = CollectionScheduler(lookup, graph, emit=emit)
    accepted, states, rejections = LinkedList(), LinkedList(), LinkedList()
    for raw in read_requests(data_dir / "collection_requests.csv"):
        request = scheduler.submit(raw.request_id, raw.farm_id, raw.estimated_feedstock)
        accepted.append(request_summary(request))
        states.append(state_summary(scheduler, "INSERT", request.request_id))
        if not scheduler.heap.is_valid():
            raise SchedulingError("Heap invariant failed after insertion.")
    if len(accepted) < 10:
        raise RequestDataError("The main demonstration needs at least ten accepted requests.")
    lines.append("\nVALIDATION WHILE THE MAIN REQUESTS ARE QUEUED")
    for raw in read_requests(data_dir / "collection_request_edge_cases.csv"):
        try:
            scheduler.submit(raw.request_id, raw.farm_id, raw.estimated_feedstock)
        except (SchedulingError, RequestValidationError, RecordValidationError) as error:
            rejections.append(manual_map((
                ("RequestID", raw.request_id),
                ("FarmID", raw.farm_id),
                ("EstimatedFeedstock", raw.estimated_feedstock),
                ("reason", str(error)),
            )))
            lines.append("REJECT {} | {}".format(raw.request_id, error))
        else:
            raise SchedulingError("An intentionally invalid edge-case request was accepted.")

    before = scheduler.heap.snapshot()
    top = scheduler.peek()
    if scheduler.peek() != top or scheduler.heap.snapshot() != before:
        raise SchedulingError("peek() changed the heap.")
    lines.append("PEEK {} | P={:.6f} | heap unchanged; size={}".format(
        top.request_id, top.priority, scheduler.heap.size))
    lines.append("\nMAIN EXTRACTIONS (first five, followed by the remaining requests)")
    collection_order = LinkedList()
    while scheduler.heap.size > 0:
        request = scheduler.extract_priority()
        if request is None:
            raise SchedulingError("A main request unexpectedly became ineligible.")
        collection_order.append(request_summary(request))
        states.append(state_summary(scheduler, "EXTRACT", request.request_id))
        if not scheduler.heap.is_valid():
            raise SchedulingError("Heap invariant failed after extraction.")
        if len(collection_order) == 5:
            lines.append("First five collections: " + " -> ".join(row["RequestID"] for row in collection_order))
    if manual_any(a["CollectionPriority"] < b["CollectionPriority"]
           for a, b in zip(collection_order, collection_order[1:])):
        raise SchedulingError("Collection priorities are not non-increasing.")
    lines.append("RESULTING COLLECTION ORDER: " + " -> ".join(row["RequestID"] for row in collection_order))
    scheduler.extract_priority()
    states.append(state_summary(scheduler, "EXTRACT_EMPTY", ""))

    phase = "DELETED HASH RECORD FIXTURE"
    lines.append("\n" + phase)
    other_lookup = load_lookup(data_dir / "dataset.csv").table
    other_lookup.delete("doj25")
    deleted = CollectionScheduler(other_lookup, graph, emit=emit)
    deleted_before_insert = False
    try:
        deleted.submit("DELETED01", "doj25", 11)
    except SchedulingError as error:
        deleted_before_insert = True
        lines.append("REJECT DELETED01 | " + str(error))
    if not deleted_before_insert:
        raise SchedulingError("A deleted farm was accepted.")

    phase = "HASH RECORD DELETED AFTER QUEUING"
    lines.append("\n" + phase)
    other_lookup.insert(lookup.search("doj25"))
    stale = CollectionScheduler(other_lookup, graph, emit=emit)
    stale.submit("STALE01", "doj25", 11)
    stale.submit("LIVE01", "c96c9", 1)
    other_lookup.delete("doj25")
    old_size = stale.heap.size
    try:
        stale.peek()
    except SchedulingError as error:
        lines.append("PEEK ERROR handled without removal: " + str(error))
    else:
        raise SchedulingError("A stale highest request was not reported.")
    if stale.heap.size != old_size:
        raise SchedulingError("A stale peek changed the heap.")
    survivor = stale.extract_priority()
    skipped = stale.last_skipped
    if survivor is None or survivor.request_id != "LIVE01" or not skipped:
        raise SchedulingError("Deleted queued information was not safely skipped.")

    phase = "ZERO-TIME COLOCATION FIXTURE"
    lines += LinkedList(("\n" + phase, "Separate scenario: the real doj25 vertex is also the temporary hub. Main network unchanged."))
    zero_graph = Graph()
    zero_graph.add_vertex(graph.location("doj25"))
    zero_lookup = HashTable()
    zero_lookup.insert(lookup.search("doj25"))
    zero_scheduler = CollectionScheduler(zero_lookup, zero_graph, hub_id="doj25", emit=emit)
    zero_request = zero_scheduler.submit("ZERO01", "doj25", 5)
    if zero_request.transport_minutes != 0 or zero_request.priority != 5:
        raise SchedulingError("Zero-time priority handling failed.")
    zero_scheduler.extract_priority()

    phase = "FARM ABSENT FROM SELECTED GRAPH FIXTURE"
    lines.append("\n" + phase)
    hub_only = Graph()
    hub_only.add_vertex(graph.location(HUB_ID))
    absent = CollectionScheduler(lookup, hub_only, emit=emit)
    try:
        absent.submit("NO_VERTEX", "doj25", 5)
    except SchedulingError as error:
        lines.append("REJECT NO_VERTEX | " + str(error))
    else:
        raise SchedulingError("A farm absent from the graph was accepted.")

    evidence = manual_map((
        ("network", mode),
        ("formula", "F / (T + 1 minute)"),
        ("feedstock_unit", "tonnes"),
        ("main_insertions", scheduler.heap.insertions),
        ("main_extractions", scheduler.heap.extractions),
        ("main_collected", scheduler.collected_count),
        ("main_heap_states", states),
        ("accepted_requests", accepted),
        ("collection_order", collection_order),
        ("rejections", rejections),
        ("peek_preserves_heap", True),
        ("deleted_before_insert_rejected", deleted_before_insert),
        ("deleted_after_queue_skipped", LinkedList((LinkedList(item) for item in skipped))),
        ("survivor_after_stale_removal", survivor.request_id),
        ("zero_time_fixture", request_summary(zero_request)),
        ("heap_traces", heap_traces),
    ))
    return "\n".join(lines) + "\n", evidence


def main(argv=None):
    parser = argparse.ArgumentParser(description="Module 3 integrated heap scheduling demonstration")
    parser.add_argument("--network", choices=("test", "full"), default="test")
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    args = parser.parse_args(argv)
    try:
        text, evidence = run_demo(args.network, args.data_dir)
    except (DataError, GraphError, RequestDataError, HashDataError, SchedulingError,
            RequestValidationError, RecordValidationError) as error:
        parser.error(str(error))
    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
