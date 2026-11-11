"""Author: Thanh Dat Nguyen
Student ID: 23857030
Date: 25/09/2026
Purpose: Readable logs; the core table has no print/input/file side effects.
"""

from .records import record_text


def trace_text(trace):
    if trace is None:
        return "No probe was performed."
    steps = " -> ".join("{}:{}{}".format(step.index, step.state,
        "({})".format(step.farm_id) if step.farm_id else "") for step in trace.steps)
    return ("{} {} | home={} m={} | {} | {}{}".format(
        trace.operation, trace.farm_id, trace.home, trace.capacity, steps, trace.result,
        " slot={}".format(trace.slot) if trace.slot is not None else ""))


def load_text(sample):
    return ("LOAD after {:3d} successful insertions | active={} m={} tombstones={} "
            "| alpha={:.4f} occupied={:.4f}".format(sample.successful_insertions,
                sample.active_records, sample.capacity, sample.tombstones,
                sample.load_factor, sample.occupied_factor))


def resize_text(event):
    action = "COMPACT" if event.old_capacity == event.new_capacity else "GROW"
    return ("{} before insertion {}: {} -> {} slots | moved={} removed_tombstones={} "
            "rehash_probes={} | {}".format(action, event.insertion_number, event.old_capacity,
                event.new_capacity, event.records_moved, event.tombstones_removed,
                event.rehash_probes, event.reason))


def table_text(table, include_empty=True):
    return "\n".join("[{:3d}] {}{}".format(step.index, step.state,
        " " + step.farm_id if step.farm_id else "") for step in table.slot_views()
        if include_empty or step.state != "EMPTY")


def summary_text(table):
    return ("Records={} | slots={} | tombstones={} | alpha={:.4f} | occupied={:.4f} "
            "| thresholds={:.2f}/{:.2f} | successful_insertions={} | rehashes={}".format(
                table.size, table.capacity, table.tombstones, table.load_factor,
                table.occupied_factor, table.max_load, table.max_occupied,
                table.successful_insertions, table.resize_count))


def search_text(table, farm_id):
    record = table.search(farm_id)
    message = "FarmID {} not found.".format(farm_id) if record is None else record_text(record)
    return trace_text(table.last_trace) + "\n" + message


def delete_text(table, farm_id):
    removed = table.delete(farm_id)
    message = ("FarmID {} not found; nothing deleted.".format(farm_id) if removed is None
               else "Deleted {} | {}.".format(farm_id, removed.name))
    return trace_text(table.last_trace) + "\n" + message + "\n" + summary_text(table)
