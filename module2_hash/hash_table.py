"""Author: Thanh Dat Nguyen
Student ID: 23857030
Date: 25/09/2026
Purpose: Modulo hashing and open addressing with linear probing, written manually.

The core index is one NumPy object array. A slot is None, a private
DELETED marker, or a FarmRecord. There is no dictionary, map, set, built-in
hash(), or ready-made hash-table implementation in this module.
"""

from manual_structures import LinkedList, manual_max

from dataclasses import dataclass
from math import ceil, isfinite
import numpy as np

from .records import FarmRecord, validate_id

_DELETED = object()


class HashTableError(ValueError):
    """The hash table cannot perform the requested operation."""


class DuplicateFarmError(HashTableError):
    """An insertion would replace an existing unique FarmID."""


def is_prime(number):
    if number < 2:
        return False
    if number % 2 == 0:
        return number == 2
    divisor = 3
    while divisor * divisor <= number:
        if number % divisor == 0:
            return False
        divisor += 2
    return True


def next_prime(number):
    candidate = manual_max(3, number)
    if candidate % 2 == 0:
        candidate += 1
    while not is_prime(candidate):
        candidate += 2
    return candidate


@dataclass(frozen=True)
class ProbeStep:
    index: int
    state: str
    farm_id: str = ""


@dataclass(frozen=True)
class OperationTrace:
    operation: str
    farm_id: str
    home: int
    capacity: int
    steps: tuple
    result: str
    slot: int = None

    @property
    def probe_count(self):
        return len(self.steps)

    @property
    def collisions(self):
        return sum(step.state == "OCCUPIED" and step.farm_id != self.farm_id
                   for step in self.steps)


@dataclass(frozen=True)
class ResizeEvent:
    old_capacity: int
    new_capacity: int
    records_moved: int
    tombstones_removed: int
    rehash_probes: int
    reason: str
    insertion_number: int


@dataclass(frozen=True)
class LoadSample:
    successful_insertions: int
    active_records: int
    capacity: int
    tombstones: int
    load_factor: float
    occupied_factor: float


def _empty_slots(capacity):
    """Allocate and clear a fixed-capacity object array."""
    slots = np.empty(capacity, dtype=object)
    slots.fill(None)
    return slots


class HashTable:
    """Unique FarmID -> complete FarmRecord using linear probing.

    Reject duplicate keys. Missing search/delete returns None. Deletion leaves
    a tombstone so subsequent searches can cross a removed cluster member.
    Only the latest operation's diagnostic events are retained; callers may
    save a demonstration history separately from the core index.
    """

    def __init__(self, initial_capacity=11, max_load=0.70):
        if (isinstance(initial_capacity, bool) or not isinstance(initial_capacity, int)
                or initial_capacity < 3):
            raise HashTableError("Initial capacity must be an integer of at least 3.")
        if (isinstance(max_load, bool) or not isinstance(max_load, (int, float))
                or not 0 < max_load < 1 or not isfinite(max_load)):
            raise HashTableError("Load threshold must be finite and strictly between 0 and 1.")
        self._slots = _empty_slots(next_prime(initial_capacity))
        self._size = 0
        self._deleted = 0
        self._max_load = float(max_load)
        # A gap between active and occupied thresholds can reduce the
        # frequency of tombstone cleanup. Rehash is expected O(m) with
        # short probes, but can reach O(m^2) under severe clustering.
        self._max_occupied = self._max_load + (1.0 - self._max_load) / 2.0
        self._successful_insertions = 0
        self._resize_count = 0
        self.last_trace = None
        self.pre_resize_trace = None
        self.last_resize = None
        self.last_load_sample = None

    @property
    def capacity(self):
        return len(self._slots)

    @property
    def size(self):
        return self._size

    @property
    def tombstones(self):
        return self._deleted

    @property
    def load_factor(self):
        return self._size / self.capacity

    @property
    def occupied_factor(self):
        return (self._size + self._deleted) / self.capacity

    @property
    def max_load(self):
        return self._max_load

    @property
    def max_occupied(self):
        return self._max_occupied

    @property
    def successful_insertions(self):
        return self._successful_insertions

    @property
    def resize_count(self):
        return self._resize_count

    def _reset_events(self):
        self.last_trace = None
        self.pre_resize_trace = None
        self.last_resize = None
        self.last_load_sample = None

    def _hash(self, farm_id):
        """Polynomial accumulation, with a modulo at every character."""
        value = 0
        for character in farm_id:
            value = (31 * value + ord(character)) % self.capacity
        return value

    def hash_index(self, farm_id):
        """Return the home slot; validate but never normalise the website ID."""
        validate_id(farm_id)
        return self._hash(farm_id)

    def _probe(self, farm_id):
        """Return (found index, first usable index, complete diagnostic steps).

        Remember the first tombstone but keep probing to detect a duplicate
        later in the cluster. Only a never-used slot proves an unsuccessful
        lookup can stop early. At most capacity slots are examined.
        """
        home = self._hash(farm_id)
        first_deleted = None
        steps = LinkedList()
        for offset in range(self.capacity):
            index = (home + offset) % self.capacity
            slot = self._slots[index]
            if slot is None:
                steps.append(ProbeStep(index, "EMPTY"))
                usable = index if first_deleted is None else first_deleted
                return None, usable, tuple(steps)
            if slot is _DELETED:
                steps.append(ProbeStep(index, "DELETED"))
                if first_deleted is None:
                    first_deleted = index
            else:
                steps.append(ProbeStep(index, "OCCUPIED", slot.farm_id))
                if slot.farm_id == farm_id:
                    return index, index, tuple(steps)
        return None, first_deleted, tuple(steps)

    def _trace(self, operation, farm_id, steps, result, slot=None):
        return OperationTrace(operation, farm_id, self._hash(farm_id), self.capacity,
                              steps, result, slot)

    def _rehash(self, new_capacity, reason):
        """Reinsert live records only; internal moves are not user insertions."""
        old_slots = self._slots
        old_capacity, old_deleted = self.capacity, self._deleted
        self._slots = _empty_slots(next_prime(new_capacity))
        self._deleted = 0
        probes = 0
        for record in old_slots:
            if record is not None and record is not _DELETED:
                found, usable, steps = self._probe(record.farm_id)
                if found is not None or usable is None:
                    raise HashTableError("Internal rehash invariant failed.")
                self._slots[usable] = record
                probes += len(steps)
        self._resize_count += 1
        self.last_resize = ResizeEvent(old_capacity, self.capacity, self._size,
                                      old_deleted, probes, reason,
                                      self._successful_insertions + 1)

    def insert(self, record):
        """Insert a validated record; reject an existing FarmID without overwrite."""
        self._reset_events()
        if not isinstance(record, FarmRecord):
            raise HashTableError("insert(record) requires a validated FarmRecord.")
        found, usable, steps = self._probe(record.farm_id)
        if found is not None:
            self.last_trace = self._trace("INSERT", record.farm_id, steps, "DUPLICATE", found)
            raise DuplicateFarmError("Duplicate FarmID {}: existing record retained.".format(record.farm_id))

        reason = None
        target_capacity = self.capacity
        if (self._size + 1) / self.capacity > self._max_load or usable is None:
            required = ceil((self._size + 1) / self._max_load)
            target_capacity = next_prime(manual_max(2 * self.capacity, required))
            reason = "Projected active load would exceed {:.2f}".format(self._max_load)
        else:
            newly_occupied = 0 if self._slots[usable] is _DELETED else 1
            if (self._size + self._deleted + newly_occupied) / self.capacity > self._max_occupied:
                reason = "Projected occupied load would exceed {:.2f}; compact tombstones".format(self._max_occupied)

        if reason is not None:
            self.pre_resize_trace = self._trace("INSERT", record.farm_id, steps, "REHASH_REQUIRED")
            self._rehash(target_capacity, reason)
            found, usable, steps = self._probe(record.farm_id)
        if usable is None:
            raise HashTableError("No usable slot after resizing.")
        self.last_trace = self._trace("INSERT", record.farm_id, steps, "INSERTED", usable)
        if self._slots[usable] is _DELETED:
            self._deleted -= 1
        self._slots[usable] = record
        self._size += 1
        self._successful_insertions += 1
        if self._successful_insertions % 10 == 0:
            self.last_load_sample = LoadSample(self._successful_insertions, self._size,
                self.capacity, self._deleted, self.load_factor, self.occupied_factor)
        return True

    def search(self, farm_id):
        """Return the complete record or None, continuing across tombstones."""
        self._reset_events()
        validate_id(farm_id)
        found, usable, steps = self._probe(farm_id)
        self.last_trace = self._trace("SEARCH", farm_id, steps,
                                     "FOUND" if found is not None else "NOT_FOUND", found)
        return None if found is None else self._slots[found]

    def delete(self, farm_id):
        """Return the removed record or None; preserve the rest of its probe chain."""
        self._reset_events()
        validate_id(farm_id)
        found, usable, steps = self._probe(farm_id)
        self.last_trace = self._trace("DELETE", farm_id, steps,
                                     "DELETED" if found is not None else "NOT_FOUND", found)
        if found is None:
            return None
        record = self._slots[found]
        self._slots[found] = _DELETED
        self._size -= 1
        self._deleted += 1
        return record

    def slot_views(self):
        """Read-only slot states for collision demonstrations and inspection."""
        views = LinkedList()
        for index, record in enumerate(self._slots):
            if record is None:
                views.append(ProbeStep(index, "EMPTY"))
            elif record is _DELETED:
                views.append(ProbeStep(index, "DELETED"))
            else:
                views.append(ProbeStep(index, "OCCUPIED", record.farm_id))
        return tuple(views)

    def records(self):
        """Enumerate live records for inspection, not for implementing lookup."""
        return tuple(record for record in self._slots
                     if record is not None and record is not _DELETED)
