"""Author: Thanh Dat Nguyen
Student ID: 23857030
Date: 16/10/2026
Purpose: Explicit linked-list, stack, queue, array and open-addressing primitives.
"""

import numpy as np


class _Node:
    def __init__(self, value):
        self.value = value
        self.next_node = None
        self.prev_node = None


class LinkedList:
    def __init__(self, values=()):
        self._head = None
        self._tail = None
        self._count = 0
        self.extend(values)

    def __len__(self):
        return self._count

    def __bool__(self):
        return self._count != 0

    def append(self, value):
        node = _Node(value)
        if self._tail is None:
            self._head = node
        else:
            self._tail.next_node = node
            node.prev_node = self._tail
        self._tail = node
        self._count += 1

    def extend(self, values):
        """Insert values through our own nodes, never a Python list."""
        if values is self:
            values = tuple(values)
        for value in values:
            self.append(value)

    def __reversed__(self):
        node = self._tail
        while node is not None:
            yield node.value
            node = node.prev_node

    def __contains__(self, value):
        for item in self:
            if item == value:
                return True
        return False

    def __eq__(self, other):
        if not hasattr(other, '__len__') or len(self) != len(other):
            return False
        for first, second in zip(self, other):
            if first != second:
                return False
        return True

    def __repr__(self):
        return 'LinkedList((' + ', '.join(repr(value) for value in self) + '))'

    def __add__(self, other):
        result = LinkedList(self)
        result.extend(other)
        return result

    def __iadd__(self, other):
        self.extend(other)
        return self

    def __mul__(self, repetitions):
        result = LinkedList()
        for _ in range(repetitions):
            result.extend(self)
        return result

    __rmul__ = __mul__

    def reverse(self):
        """Reverse links explicitly; no built-in sequence reversal."""
        node = self._head
        while node is not None:
            following = node.next_node
            node.next_node, node.prev_node = node.prev_node, node.next_node
            node = following
        self._head, self._tail = self._tail, self._head

    def prepend(self, value):
        node = _Node(value)
        if self._head is None:
            self._tail = node
        else:
            node.next_node = self._head
            self._head.prev_node = node
        self._head = node
        self._count += 1

    def take_first(self):
        if self._head is None:
            raise IndexError('Linked list is empty')
        node = self._head
        self._head = node.next_node
        if self._head is None:
            self._tail = None
        else:
            self._head.prev_node = None
        self._count -= 1
        return node.value

    def take_last(self):
        if self._tail is None:
            raise IndexError('Linked list is empty')
        node = self._tail
        self._tail = node.prev_node
        if self._tail is None:
            self._head = None
        else:
            self._tail.next_node = None
        self._count -= 1
        return node.value

    def peek_last(self):
        if self._tail is None:
            raise IndexError('Linked list is empty')
        return self._tail.value

    def replace_last(self, value):
        if self._tail is None:
            raise IndexError('Linked list is empty')
        self._tail.value = value

    def __iter__(self):
        node = self._head
        while node is not None:
            yield node.value
            node = node.next_node

    def _node_at(self, index):
        if not isinstance(index, int):
            raise TypeError('Linked-list index must be an integer')
        if index < 0:
            index += self._count
        if index < 0 or index >= self._count:
            raise IndexError('Linked-list index out of range')
        if index < self._count // 2:
            node = self._head
            for _ in range(index):
                node = node.next_node
        else:
            node = self._tail
            for _ in range(self._count - index - 1):
                node = node.prev_node
        return node

    def __getitem__(self, index):
        if isinstance(index, slice):
            start, stop, step = index.indices(self._count)
            result = LinkedList()
            if len(range(start, stop, step)):
                node = self._node_at(start)
                for _ in range(start, stop, step):
                    result.append(node.value)
                    for _ in range(abs(step)):
                        if node is not None:
                            node = node.next_node if step > 0 else node.prev_node
            return result
        return self._node_at(index).value

    def __setitem__(self, index, value):
        if isinstance(index, slice):
            if index.start is not None or index.stop is not None or index.step is not None:
                raise TypeError('Only complete linked-list replacement is supported')
            replacement = LinkedList(value)
            self._head, self._tail, self._count = replacement._head, replacement._tail, replacement._count
        else:
            self._node_at(index).value = value


class LinkedStack:
    def __init__(self):
        self._items = LinkedList()

    def __bool__(self):
        return bool(self._items)

    @property
    def count(self):
        return len(self._items)

    def push(self, value):
        self._items.append(value)

    def take(self):
        return self._items.take_last()

    def peek(self):
        return self._items.peek_last()

    def replace_top(self, value):
        self._items.replace_last(value)

    def __iter__(self):
        return iter(self._items)


class LinkedQueue:
    def __init__(self):
        self._items = LinkedList()

    def __bool__(self):
        return bool(self._items)

    def enqueue(self, value):
        self._items.append(value)

    def dequeue(self):
        return self._items.take_first()


class OpenAddressMap:
    """Own modulo-hash, linear-probe map; insertion-order traversal via linked list.

    _keys and _values are NumPy object arrays. Tombstones
    preserve probe sequences on deletion. Does not call Python dict/set.
    """
    _TOMBSTONE = object()
    _EMPTY = object()

    def __init__(self, capacity=11, track_order=True):
        self._track_order = track_order
        self._capacity = 11 if capacity < 11 else capacity
        self._keys = np.empty(self._capacity, dtype=object)
        self._values = np.empty(self._capacity, dtype=object)
        self._keys.fill(self._EMPTY)
        self._values.fill(None)
        self._size = 0
        self._ordered_keys = LinkedList()

    def __len__(self):
        return self._size

    def _hash(self, key):
        if key is None:
            return 0
        if isinstance(key, (int, float)):
            if isinstance(key, float):
                numerator, denominator = key.as_integer_ratio()
                return (numerator + (denominator - 1) * 31) % self._capacity
            return key % self._capacity
        if isinstance(key, tuple):
            result = 0
            for part in key:
                result = (result * 31 + self._hash(part)) % self._capacity
            return result
        if not isinstance(key, str):
            raise TypeError('Manual map keys must be text, numbers, tuples or None')
        result = 0
        for character in key:
            result = (result * 31 + ord(character)) % self._capacity
        return result

    def _slot(self, key, insert=False):
        start = self._hash(key)
        free = None
        for offset in range(self._capacity):
            pos = (start + offset) % self._capacity
            existing = self._keys[pos]
            if existing is self._EMPTY:
                return free if insert and free is not None else pos
            if existing is self._TOMBSTONE:
                if free is None:
                    free = pos
            elif existing == key:
                return pos
        return free if insert else None

    def __contains__(self, key):
        pos = self._slot(key)
        return pos is not None and self._keys[pos] is not self._EMPTY and self._keys[pos] is not self._TOMBSTONE

    def __getitem__(self, key):
        pos = self._slot(key)
        if pos is None or self._keys[pos] is self._EMPTY or self._keys[pos] is self._TOMBSTONE:
            raise KeyError(key)
        return self._values[pos]

    def __setitem__(self, key, value):
        if (self._size + 1) * 10 > self._capacity * 7 and key not in self:
            self._grow()
        pos = self._slot(key, insert=True)
        if pos is None:
            self._grow()
            pos = self._slot(key, insert=True)
        if self._keys[pos] is self._EMPTY or self._keys[pos] is self._TOMBSTONE:
            if self._track_order:
                self._ordered_keys.append(key)
            self._size += 1
        self._keys[pos] = key
        self._values[pos] = value

    def _grow(self):
        old_keys, old_values, old_capacity = self._keys, self._values, self._capacity
        self._capacity = old_capacity * 2 + 1
        self._keys = np.empty(self._capacity, dtype=object)
        self._values = np.empty(self._capacity, dtype=object)
        self._keys.fill(self._EMPTY)
        self._values.fill(None)
        for pos in range(old_capacity):
            key = old_keys[pos]
            if key is not self._EMPTY and key is not self._TOMBSTONE:
                target = self._slot(key, insert=True)
                self._keys[target] = key
                self._values[target] = old_values[pos]

    def discard(self, key):
        pos = self._slot(key)
        if pos is None or self._keys[pos] is self._EMPTY or self._keys[pos] is self._TOMBSTONE:
            return False
        self._keys[pos] = self._TOMBSTONE
        self._values[pos] = None
        self._size -= 1
        if self._track_order:
            # Ordered maps rebuild the linked list after deletion.
            # Unordered maps skip that rebuild, but probing may still scan the table.
            updated = LinkedList()
            for existing in self._ordered_keys:
                if existing != key:
                    updated.append(existing)
            self._ordered_keys = updated
        return True

    def __iter__(self):
        if not self._track_order:
            raise TypeError('Iteration is disabled on this membership-only map')
        return iter(self._ordered_keys)

    def items(self):
        for key in self:
            yield key, self[key]

    def keys(self):
        return tuple(self)

    def values(self):
        for key in self:
            yield self[key]

    def get(self, key, default=None):
        if key in self:
            return self[key]
        return default

    def __eq__(self, other):
        if not isinstance(other, OpenAddressMap) or len(self) != len(other):
            return False
        for key in self:
            if key not in other or self[key] != other[key]:
                return False
        return True

    def __repr__(self):
        return 'OpenAddressMap((' + ', '.join(repr(pair) for pair in self.items()) + '))'


def manual_map(pairs=()):
    """Build our modulo/probing table from explicit key/value pairs."""
    result = OpenAddressMap()
    if isinstance(pairs, OpenAddressMap):
        pairs = pairs.items()
    for key, value in pairs:
        result[key] = value
    return result


class ManualSet:
    """Diagnostic distinct values using explicit node traversal, without set().

    Used by validation and test oracles, never as the graph/heap's core index.
    Membership is O(n); graph/heap membership uses OpenAddressMap instead.
    """
    def __init__(self, values=()):
        self._values = LinkedList()
        for value in values:
            self.add(value)

    def __len__(self):
        return len(self._values)

    def __iter__(self):
        return iter(self._values)

    def __contains__(self, value):
        return self._values.__contains__(value)

    def add(self, value):
        if not self.__contains__(value):
            self._values.append(value)

    def __or__(self, other):
        result = ManualSet(self)
        for value in other:
            result.add(value)
        return result

    def __eq__(self, other):
        if not isinstance(other, ManualSet) or len(self) != len(other):
            return False
        for value in self:
            if not other.__contains__(value):
                return False
        return True

    def __repr__(self):
        return 'ManualSet((' + ', '.join(repr(value) for value in self) + '))'


def object_array(values=()):
    """Copy an iterable into a one-dimensional NumPy object array.

    Assign one slot at a time: np.array(tuple_records) can unintentionally
    create a two-dimensional array. Unknown-length iterators use our nodes.
    """
    if not hasattr(values, '__len__'):
        values = LinkedList(values)
    result = np.empty(len(values), dtype=object)
    for position, value in enumerate(values):
        result[position] = value
    return result


def _text_at(text, target, start):
    for offset in range(len(target)):
        if text[start + offset] != target[offset]:
            return False
    return True


def manual_contains(values, target):
    """Explicit scans; custom map membership retains manual linear probing."""
    if isinstance(values, (OpenAddressMap, ManualSet, LinkedList)):
        return values.__contains__(target)
    if isinstance(values, str):
        if not isinstance(target, str):
            raise TypeError('Text membership requires text')
        for start in range(len(values) - len(target) + 1):
            if _text_at(values, target, start):
                return True
        return False
    for value in values:
        if value == target:
            return True
    return False


def manual_count(values, target):
    """Explicit frequency scan; text matches follow non-overlapping semantics."""
    count = 0
    if isinstance(values, str):
        if not target:
            return len(values) + 1
        position = 0
        while position <= len(values) - len(target):
            if _text_at(values, target, position):
                count += 1
                position += len(target)
            else:
                position += 1
    else:
        for value in values:
            if value == target:
                count += 1
    return count


def _extreme(arguments, key, largest):
    values = arguments[0] if len(arguments) == 1 else arguments
    found = False
    result = None
    for value in values:
        score = value if key is None else key(value)
        if not found or (score > best if largest else score < best):
            result, best, found = value, score, True
    if not found:
        raise ValueError('An extreme needs at least one value')
    return result


def manual_min(*values, key=None):
    return _extreme(values, key, False)


def manual_max(*values, key=None):
    return _extreme(values, key, True)


def manual_shuffle(values, rng):
    """Fisher-Yates shuffle with explicit index swaps."""
    for right in range(len(values) - 1, 0, -1):
        left = rng.randrange(right + 1)
        values[left], values[right] = values[right], values[left]


def manual_sample(values, count, rng):
    """Sample without replacement using a partial Fisher-Yates shuffle."""
    pool = object_array(values)
    if not 0 <= count <= len(pool):
        raise ValueError('Invalid sample size')
    for first in range(count):
        second = rng.randrange(first, len(pool))
        pool[first], pool[second] = pool[second], pool[first]
    result = np.empty(count, dtype=object)
    for position in range(count):
        result[position] = pool[position]
    return result


def manual_any(values):
    """Explicit predicate scan, without automatic searching helpers."""
    for value in values:
        if value:
            return True
    return False


def manual_all(values):
    """Explicit validation scan, without automatic searching helpers."""
    for value in values:
        if not value:
            return False
    return True
