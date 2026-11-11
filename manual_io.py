"""Author: Thanh Dat Nguyen
Student ID: 23857030
Date: 29/10/2026
Purpose: CSV/JSON adapters that keep application records in manual containers.

Standard codecs handle quoting, escaping and bytes only. Their temporary
parser objects never implement the assignment's graph, hash table or heap.
"""

import csv
from dataclasses import fields, is_dataclass
import json
from urllib.parse import unquote_plus

from manual_structures import LinkedList, OpenAddressMap, manual_map


def query_values(query, requested):
    """Parse query fields with explicit scans, retaining repeated values."""
    values = LinkedList()
    start = 0
    while start <= len(query):
        end = start
        while end < len(query) and query[end] != '&':
            end += 1
        equals = start
        while equals < end and query[equals] != '=':
            equals += 1
        key = unquote_plus(query[start:equals])
        if key == requested:
            value = unquote_plus(query[equals + 1:end]) if equals < end else ''
            if value:
                values.append(value)
        start = end + 1
    return tuple(values)


class CSVReader:
    """Positional CSV input, mapped to our own open-addressed rows."""
    def __init__(self, stream, strict=False):
        self._reader = csv.reader(stream, strict=strict)
        header = next(self._reader, None)
        self.fieldnames = None if header is None else tuple(header)

    @property
    def line_num(self):
        return self._reader.line_num

    def __iter__(self):
        return self

    def __next__(self):
        if self.fieldnames is None:
            raise StopIteration
        row = next(self._reader)
        while len(row) == 0:
            row = next(self._reader)
        if len(row) != len(self.fieldnames):
            raise csv.Error('malformed CSV record: wrong number of fields')
        return manual_map(zip(self.fieldnames, row))


class CSVWriter:
    """Write manual mapping records using positional csv.writer."""
    def __init__(self, stream, fieldnames):
        self.fieldnames = tuple(fieldnames)
        self._writer = csv.writer(stream)

    def writeheader(self):
        return self._writer.writerow(self.fieldnames)

    def writerow(self, row):
        return self._writer.writerow(tuple(row[column] for column in self.fieldnames))

    def writerows(self, rows):
        for row in rows:
            self.writerow(row)


def dataclass_map(value):
    """Extract dataclass fields into our table, including nested trace records."""
    if is_dataclass(value):
        return manual_map((item.name, dataclass_map(getattr(value, item.name)))
                          for item in fields(value))
    if isinstance(value, OpenAddressMap):
        return manual_map((key, dataclass_map(item)) for key, item in value.items())
    if value is None or isinstance(value, (str, bool, int, float)):
        return value
    return tuple(dataclass_map(item) for item in value)


def json_dumps(value, indent=None, ensure_ascii=True, allow_nan=True):
    """Encode manual records directly; do not build a dictionary/list copy."""
    def encode(item, depth):
        if item is None or isinstance(item, (str, bool, int, float)):
            return json.dumps(item, ensure_ascii=ensure_ascii, allow_nan=allow_nan)
        if is_dataclass(item):
            item = dataclass_map(item)
        if isinstance(item, OpenAddressMap):
            entries = (json.dumps(key, ensure_ascii=ensure_ascii) + ': ' + encode(val, depth + 1)
                       for key, val in item.items())
            opening, closing = '{', '}'
        else:
            entries = (encode(val, depth + 1) for val in item)
            opening, closing = '[', ']'
        if indent is None:
            return opening + ', '.join(entries) + closing
        content = (',\n' + ' ' * (indent * (depth + 1))).join(entries)
        if not content:
            return opening + closing
        return (opening + '\n' + ' ' * (indent * (depth + 1)) + content
                + '\n' + ' ' * (indent * depth) + closing)

    return encode(value, 0)


def json_loads(text):
    """Decode object keys into our map; expose JSON arrays as immutable tuples.

    Native JSON parsing is an I/O boundary, like csv.reader in Prac07. It is
    not used for any search, sort, stack, queue, graph or heap operation.
    """
    def normalise(value):
        if isinstance(value, OpenAddressMap):
            return manual_map((key, normalise(item)) for key, item in value.items())
        if value is None or isinstance(value, (str, bool, int, float)):
            return value
        return tuple(normalise(item) for item in value)

    return normalise(json.loads(text, object_pairs_hook=manual_map))
