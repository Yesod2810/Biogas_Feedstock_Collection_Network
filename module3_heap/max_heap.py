"""Author: Thanh Dat Nguyen
Student ID: 23857030
Date: 3/10/2026
Purpose: Array-based binary max heap with manual upward/downward percolation.

The heap uses a dynamically grown NumPy object array and
student-implemented array swaps/percolation. Duplicate-ID tracking uses a
manual open-addressing index.
Printing the required full array costs O(q), separately from O(log q) sifting.
"""

from manual_structures import LinkedList, OpenAddressMap, manual_contains

from dataclasses import dataclass
import numpy as np

from .requests import ScheduledRequest


class HeapError(ValueError):
    """An invalid request would violate the heap's contract."""


@dataclass(frozen=True)
class _Entry:
    request: ScheduledRequest
    arrival: int


def _higher(first, second):
    if first.request.priority != second.request.priority:
        return first.request.priority > second.request.priority
    return first.arrival < second.arrival


class MaxHeap:
    """Highest calculated priority first; exact ties use FIFO insertion order.

    emit defaults to print, as required by the brief. Tests may pass emit=None
    or a collector. The emitted array follows every insertion and extraction,
    including an attempted extraction from an empty heap.
    """

    def __init__(self, emit=print):
        self._items = np.empty(16, dtype=object)
        self._items.fill(None)
        self._size = 0
        self._queued_ids = OpenAddressMap(track_order=False)
        self._next_arrival = 0
        self._emit = emit
        self.last_swaps = ()
        self.insertions = 0
        self.extractions = 0

    @property
    def size(self):
        return self._size

    def snapshot(self):
        """Return an immutable tuple of requests in heap-array order."""
        return tuple(self._items[index].request for index in range(self._size))

    def array_text(self):
        if self._size == 0:
            return "[]"
        lines = LinkedList(("[",))
        for index in range(self._size):
            request = self._items[index].request
            lines.append("  {}: {} | farm={} | P={:.6f}".format(
                index, request.request_id, request.farm_id, request.priority))
        lines.append("]")
        return "\n".join(lines)

    def _notify(self, operation, request_id):
        if self._emit is not None:
            swaps = ", ".join("{}<->{}".format(a, b) for a, b in self.last_swaps) or "none"
            self._emit("HEAP after {} {} | swaps={}\n{}".format(
                operation, request_id, swaps, self.array_text()))

    def insert(self, request):
        """Append and percolate upward using parent index (i-1)//2."""
        if not isinstance(request, ScheduledRequest):
            raise HeapError("insert(request) requires a validated ScheduledRequest.")
        if manual_contains(self._queued_ids, request.request_id):
            raise HeapError("Duplicate queued RequestID {}.".format(request.request_id))
        entry = _Entry(request, self._next_arrival)
        self._next_arrival += 1
        if self._size == len(self._items):
            expanded = np.empty(len(self._items) * 2, dtype=object)
            expanded.fill(None)
            for position in range(self._size):
                expanded[position] = self._items[position]
            self._items = expanded
        self._items[self._size] = entry
        self._size += 1
        self._queued_ids[request.request_id] = True
        swaps = LinkedList()
        index = self._size - 1
        moving = True
        while index > 0 and moving:
            parent = (index - 1) // 2
            if _higher(self._items[index], self._items[parent]):
                self._items[index], self._items[parent] = self._items[parent], self._items[index]
                swaps.append((index, parent))
                index = parent
            else:
                moving = False
        self.last_swaps = tuple(swaps)
        self.insertions += 1
        self._notify("INSERT", request.request_id)
        return request

    def peek(self):
        """Return the highest-priority request without changing the array."""
        return None if self._size == 0 else self._items[0].request

    def extract_priority(self):
        """Replace root with the last entry and percolate down to the higher child."""
        self.last_swaps = ()
        if self._size == 0:
            self._notify("EXTRACT", "(empty)")
            return None
        highest = self._items[0].request
        last = self._items[self._size - 1]
        self._items[self._size - 1] = None
        self._size -= 1
        self._queued_ids.discard(highest.request_id)
        swaps = LinkedList()
        if self._size > 0:
            self._items[0] = last
            index = 0
            moving = True
            while moving:
                left = 2 * index + 1
                right = left + 1
                if left >= self._size:
                    moving = False
                else:
                    child = left
                    if right < self._size and _higher(self._items[right], self._items[left]):
                        child = right
                    if _higher(self._items[child], self._items[index]):
                        self._items[index], self._items[child] = self._items[child], self._items[index]
                        swaps.append((index, child))
                        index = child
                    else:
                        moving = False
        self.last_swaps = tuple(swaps)
        self.extractions += 1
        self._notify("EXTRACT", highest.request_id)
        return highest

    def is_valid(self):
        """Diagnostic only; public operations do not scan the heap to maintain it."""
        for index in range(1, self._size):
            if _higher(self._items[index], self._items[(index - 1) // 2]):
                return False
        return True
