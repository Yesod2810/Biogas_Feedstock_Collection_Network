# Module 3 - Heap-Based Collection Scheduling

## Strategy and formula

Use a **binary Max Heap**: larger collection-priority values should be
processed earlier. `module3_heap/max_heap.py` maintains a NumPy object array by manual upward
and downward percolation. It uses no `heapq`, ready-made priority queue or sorting routine. A manually implemented modulo-hash membership index guards duplicate RequestIDs; it does not
choose priorities or maintain heap order.

```text
F = positive EstimatedFeedstock supplied with a request, in modelled tonnes
T = Graph.dijkstra(FarmID, hub).minutes
P = F / (T + 1 minute)
```

More F increases P; more T reduces P. The one-minute allowance is an
educational model constant. It ensures that T=0 gives the finite priority
P=F. No manual priority column is accepted, and `ScheduledRequest.priority`
is calculated by the program rather than supplied to its constructor.
Comparisons use full precision; displayed priorities use six decimal places.
Exact ties use FIFO insertion order maintained by an internal arrival number.

`data/collection_requests.csv` contains ten real source FarmIDs and invented
educational quantities from 6 to 27.5 tonnes. These are not production or
availability figures reported by Farm Transparency Project. They do not add
attributes to the original farm dataset. `collection_request_edge_cases.csv`
contains deliberately invalid query scenarios, not fabricated farm records.

## Integration

`CollectionScheduler.submit(RequestID, FarmID, EstimatedFeedstock)`:

1. Validate the request ID, exact source FarmID and positive finite quantity.
2. Call the Module 2 `HashTable.search(FarmID)` for the complete farm record.
3. Resolve that FarmID in the Module 1 graph and check coordinate consistency.
4. Call the manual `Graph.dijkstra(FarmID, hub)` implementation.
5. Reject an unreachable route; otherwise calculate priority and insert into
   the Max Heap. Print the calculation, route and resulting heap array.

The root menu shares the hash-table session between Modules 2 and 3. A hash
deletion immediately affects scheduler eligibility. Reloading the hash module
rebinds the scheduler to the new table. Hash/graph source CSVs are not rewritten.

Priorities are submission-time snapshots for the current graph. Graph vertex/
edge additions invalidate the scheduling session; subsequent queue operations
ask for an explicit reset, preventing use of stale route priorities. A network
reload resets the queue. The current Graph only supports insertion, so its
vertex/edge counts are sufficient to detect its public mutations in O(1).

## Heap API and indices

| Operation | Contract |
|---|---|
| `insert(request)` | Append a validated `ScheduledRequest`, then percolate up |
| `peek()` | Highest request or None; do not remove or alter the heap |
| `extract_priority()` | Remove highest, replace with last, then percolate down; None on empty |
| `snapshot()` | Immutable tuple in heap-array order, not globally sorted order |
| `array_text()` | Readable indexed array with IDs, farm IDs and priorities |
| `last_swaps` | Index pairs swapped in the latest insertion/extraction |
| `is_valid()` | O(q) diagnostic used by tests/driver, not by heap maintenance |

At index i, the parent is `(i-1)//2`, left child `2*i+1`, and right child
`2*i+2`. Sift-down chooses the higher-ranked child, including FIFO tie order.
Default `emit=print` prints the full array after every successful insertion
and extraction, plus an empty extraction attempt. Tests can supply a collector
or `emit=None`. Peek does not change the array or print a mutation trace.

## Edge-case policies

| Case | Handling |
|---|---|
| Unreachable farm | Reject; clearly state no valid collection route can currently be calculated |
| T=0 | Calculate P=F; exercise Dijkstra with a source that is also the configured hub |
| Invalid FarmID / missing record | Reject with a clear message; no heap mutation |
| Zero/negative/non-numerical/NaN/infinite F | Reject before insertion |
| Empty heap | Peek/extract return None and the UI reports empty |
| Duplicate RequestID | Reject for the entire scheduling session, including processed requests |
| Same farm under a new RequestID while pending | Reject to avoid double-counting the same available feedstock |
| Same farm after its earlier request finishes | Allow a genuinely new RequestID |
| Farm deleted before submission | Hash lookup fails; reject |
| Farm deleted or changed after queuing | Peek reports the stale root without removal; extraction removes/skips it and continues |
| Graph missing the farm / mismatched coordinates | Reject; do not calculate a misleading route |
| Graph changes after queuing | Require reset before using old priority snapshots |

Rejected submissions do not consume their RequestID. Skipped stale requests do
not count as collections. A raw heap extraction always prints its resulting
array, including each stale request removed by the scheduler.

## Execute

From the project root:

```bash
python interactive_menu.py --module heap
python interactive_menu.py --module heap --demo
python interactive_menu.py --module heap --validate
python interactive_menu.py --module heap --network full --demo
python -m module3_heap.test_driver
python -m unittest discover -s module3_heap/tests -v
python -m unittest discover -s . -v
```

Root-menu option 11 also opens Module 3. Load requests with submenu option 1,
peek with 3, extract one with 4, or drain with 5. Option 7 explicitly resets
the queue/history after a network change. Option 9 deletes a shared hash
record to demonstrate stale queued information. Option 8 uses fresh structures
for the independent demonstration.

The default test-network order is calculated as:

```text
C001 -> C004 -> C003 -> C008 -> C002 -> C006 -> C007 -> C009 -> C010 -> C005
```

The full network has different route times and can produce a different order.
It uses the same algorithm and request quantities.

## Performance and scope

For q queued requests, heap percolation takes O(log q) and peek takes O(1).
The required full-array printing adds O(q) work/output after each mutation.
Preparing a request includes expected O(1) hash lookup and the existing
O(V^2+E) Dijkstra implementation. The scheduler's duplicate guards have
expected O(1) manual modulo/probing lookups. If k stale entries precede an eligible one,
dispatch performs k+1 heap extractions and record lookups, printing every state.

Heap storage is O(q). Stored route snapshots add O(q*V) in the worst case,
and processed RequestID history adds O(r), where r is the number accepted
during the session. This priority rule is a transparent educational heuristic;
it is not truck-capacity allocation, time-window optimisation or multi-stop
vehicle routing. T represents the shortest one-way farm-to-hub graph route.

Evidence files are `heap_demo.txt`, `heap_traces.txt`, `heap_validation.json`,
`heap_priority_calculations.csv`, `heap_collection_order.csv`,
`heap_interactive_session.txt` and `heap_initial.png` in `sample_output/`.
