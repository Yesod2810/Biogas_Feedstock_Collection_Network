"""Author: Thanh Dat Nguyen
Student ID: 23857030
Date: 11/10/2026
Purpose: SQLite persistence with application-calculated sort positions.

SQLite does not sort by TransportTime: there is no SQL ORDER BY. Python's
manual sorter calculates every position. Reading position 0, 1, ... makes
the persisted order explicit, since relational tables have no implicit order.
"""

from manual_structures import LinkedList, manual_contains
from manual_io import json_dumps, json_loads

from dataclasses import replace
from pathlib import Path
import sqlite3

from .algorithms import is_sorted, merge_sort, quick_sort
from .records import CollectionRecord, SortDataError, require_unique, write_records


class CollectionDatabase:
    def __init__(self, path=':memory:'):
        self.path = str(path)
        try:
            if self.path != ':memory:':
                Path(path).parent.mkdir(parents=True, exist_ok=True)
            self.connection = sqlite3.connect(self.path)
            self.connection.execute('CREATE TABLE IF NOT EXISTS collection_records '
                                    '(position INTEGER PRIMARY KEY, record_id TEXT UNIQUE NOT NULL, payload TEXT NOT NULL)')
            self.connection.execute('CREATE TABLE IF NOT EXISTS sessions (id INTEGER PRIMARY KEY AUTOINCREMENT)')
            self.connection.commit()
        except (OSError, sqlite3.Error) as error:
            raise SortDataError("Cannot open collection database: {}".format(error)) from error

    def close(self):
        self.connection.close()

    def records(self):
        """Read explicit integer ranks; never ask SQL to sort request data."""
        try:
            count = self.connection.execute('SELECT COUNT(*) FROM collection_records').fetchone()[0]
            records = LinkedList()
            for position in range(count):
                row = self.connection.execute('SELECT payload FROM collection_records WHERE position=?',
                                              (position,)).fetchone()
                if row is None:
                    raise SortDataError("Database sort positions are not contiguous.")
                records.append(CollectionRecord.from_row(json_loads(row[0])))
            return records
        except (sqlite3.Error, ValueError) as error:
            raise SortDataError("Cannot read collection database: {}".format(error)) from error

    def save(self, records, algorithm='merge'):
        """Validate, manually sort and atomically replace all persisted ranks."""
        values = LinkedList(records)
        require_unique(values)
        if not manual_contains(('merge', 'quick'), algorithm):
            raise SortDataError("Choose merge or quick sorting.")
        ordered = (merge_sort if algorithm == 'merge' else quick_sort)(values)
        if not is_sorted(ordered):
            raise SortDataError("Sorting failed; database was not changed.")
        rows = LinkedList(((position, record.record_id, json_dumps(record.row(), allow_nan=False)) for position, record in enumerate(ordered)))
        try:
            with self.connection:
                self.connection.execute('DELETE FROM collection_records')
                self.connection.executemany('INSERT INTO collection_records VALUES (?, ?, ?)', rows)
        except sqlite3.Error as error:
            raise SortDataError("Cannot save collection database: {}".format(error)) from error
        return ordered

    def import_records(self, records, algorithm='merge'):
        """Keep the entire previous history; duplicate RecordIDs are rejected."""
        return self.save(self.records() + LinkedList(records), algorithm)

    def export_csv(self, path):
        write_records(path, self.records())

    def new_session(self):
        try:
            with self.connection:
                cursor = self.connection.execute('INSERT INTO sessions DEFAULT VALUES')
            return SessionRecorder(self, cursor.lastrowid)
        except sqlite3.Error as error:
            raise SortDataError("Cannot create collection session: {}".format(error)) from error


class SessionRecorder:
    """A new session preserves repeated RequestIDs after a heap reset."""
    def __init__(self, database, session_id):
        self.database, self.session_id = database, session_id

    def new_session(self):
        return self.database.new_session()

    def record(self, request, status, detail=''):
        record_id = 'S{:06d}_{}'.format(self.session_id, request.request_id)
        records = self.database.records()
        existing = None
        for index, item in enumerate(records):
            if item.record_id == record_id:
                existing = index
                break
        if existing is None:
            if status != 'pending':
                raise SortDataError("Cannot update a request absent from the collection archive.")
            records.append(CollectionRecord(record_id, request, status, detail))
        else:
            old = records[existing]
            if old.request != request or status == 'pending':
                raise SortDataError("Duplicate or changed archived RequestID.")
            records[existing] = replace(old, status=status, detail=detail)
        self.database.save(records, 'merge')
