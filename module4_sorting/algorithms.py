"""Author: Thanh Dat Nguyen
Student ID: 23857030
Date: 11/10/2026
Purpose: Manual stable bottom-up Merge Sort and median-of-three, three-way Quick Sort.

Public wrappers return a new one-dimensional NumPy object array. Only quick_sort_in_place mutates its input.
No built-in sort, graph library or database sorting operation is used.
"""

from manual_structures import LinkedStack, manual_max, manual_min, object_array

from dataclasses import dataclass
import numpy as np


def transport_time(record):
    return record.transport_minutes


@dataclass
class SortMetrics:
    comparisons: int = 0
    moves: int = 0
    partitions: int = 0
    max_pending_ranges: int = 0


def merge_sort(records, key=transport_time, metrics=None):
    """Stable bottom-up merging: O(n log n) time and O(n) auxiliary space.

    Taking the left record on equality preserves its input order. Widths
    double from one, so there is no recursion or recursion-limit dependency.
    """
    source = object_array(records)
    count = len(source)
    target = np.empty(count, dtype=object)
    width = 1
    while width < count:
        start = 0
        while start < count:
            middle = manual_min(start + width, count)
            end = manual_min(start + 2 * width, count)
            left, right, out = start, middle, start
            while left < middle and right < end:
                if metrics is not None:
                    metrics.comparisons += 1
                if key(source[left]) <= key(source[right]):
                    target[out] = source[left]
                    left += 1
                else:
                    target[out] = source[right]
                    right += 1
                if metrics is not None:
                    metrics.moves += 1
                out += 1
            while left < middle:
                target[out] = source[left]
                left += 1
                out += 1
                if metrics is not None:
                    metrics.moves += 1
            while right < end:
                target[out] = source[right]
                right += 1
                out += 1
                if metrics is not None:
                    metrics.moves += 1
            start += 2 * width
        source, target = target, source
        width *= 2
    return source


def _less(first, second, metrics):
    if metrics is not None:
        metrics.comparisons += 1
    return first < second


def _median_of_three(first, middle, last, metrics):
    """Return a pivot KEY using only explicit comparisons, including ties."""
    if _less(first, middle, metrics):
        if _less(middle, last, metrics):
            return middle
        return last if _less(first, last, metrics) else first
    if _less(first, last, metrics):
        return first
    return last if _less(middle, last, metrics) else middle


def _swap(values, first, second, metrics):
    if first != second:
        values[first], values[second] = values[second], values[first]
        if metrics is not None:
            metrics.moves += 2


def quick_sort_in_place(values, key=transport_time, metrics=None):
    """Three-way partition; process the smaller side, defer the larger side.

    Equal keys form a finished middle region. An explicit stack avoids Python
    recursion limits and holds O(log n) deferred ranges even for bad pivots.
    Median-of-three helps ordered inputs but does NOT guarantee O(n log n).
    The partition algorithm is unstable and has O(n^2) worst-case time.
    """
    if not isinstance(values, np.ndarray) or values.ndim != 1:
        raise TypeError("In-place Quick Sort requires a one-dimensional NumPy array.")
    pending = LinkedStack()
    low, high = 0, len(values) - 1
    active = low < high
    while active:
        while low < high:
            middle = (low + high) // 2
            pivot = _median_of_three(key(values[low]), key(values[middle]),
                                     key(values[high]), metrics)
            if metrics is not None:
                metrics.partitions += 1
            less, scan, greater = low, low, high
            while scan <= greater:
                value = key(values[scan])
                if _less(value, pivot, metrics):
                    _swap(values, less, scan, metrics)
                    less += 1
                    scan += 1
                elif _less(pivot, value, metrics):
                    _swap(values, scan, greater, metrics)
                    greater -= 1
                else:
                    scan += 1
            left = (low, less - 1)
            right = (greater + 1, high)
            left_size, right_size = less - low, high - greater
            smaller, larger = (left, right) if left_size <= right_size else (right, left)
            if larger[0] < larger[1]:
                pending.push(larger)
                if metrics is not None:
                    metrics.max_pending_ranges = manual_max(metrics.max_pending_ranges, pending.count)
            low, high = smaller
        if pending:
            low, high = pending.take()
        else:
            active = False
    return values


def quick_sort(records, key=transport_time, metrics=None):
    """Non-mutating wrapper: O(n) output copy plus O(log n) partition stack."""
    return quick_sort_in_place(object_array(records), key, metrics)


def is_sorted(records, key=transport_time):
    """One forward scan, including when input is our node-based sequence."""
    first = True
    previous = None
    for record in records:
        current = key(record)
        if not first and previous > current:
            return False
        previous = current
        first = False
    return True
