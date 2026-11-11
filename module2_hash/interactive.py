"""Author: Thanh Dat Nguyen
Student ID: 23857030
Date: 25/09/2026
Purpose: Module 2 submenu, shared by the root menu and --module hash entry point.
"""

from manual_structures import LinkedList

from .data_loader import HashDataError, load_lookup, read_farm_records
from .display import (delete_text, load_text, resize_text, search_text, summary_text,
                      table_text, trace_text)
from .hash_table import DuplicateFarmError, HashTableError
from .records import RecordValidationError, validate_id
from .test_driver import run_demo


def loading_text(loaded):
    lines = LinkedList(("CSV IMPORT CHECKPOINTS (each ten successful insertions)",))
    for sample in loaded.load_samples:
        lines.append(load_text(sample))
    lines.extend(resize_text(event) for event in loaded.resize_events)
    lines.append("Current session: " + summary_text(loaded.table))
    return "\n".join(lines)


def hash_menu(loaded, dataset_path):
    """Changes affect this hash session only; source CSVs and graph stay separate."""
    print(loading_text(loaded))
    running = True
    while running:
        table = loaded.table
        print("\nCOMP5008 - MODULE 2 | " + summary_text(table))
        print("1. Display hash-table summary and original import checkpoints")
        print("2. Search FarmID (complete record and probe sequence)")
        print("3. Insert/reinsert a real farm from dataset.csv")
        print("4. Delete FarmID")
        print("5. Show slot states (including tombstones)")
        print("6. Run the independent Module 2 demonstration")
        print("7. Reload dataset.csv (resets hash-session changes)")
        print("0. Leave Module 2")
        try:
            choice = input("Choose a hash option: ").strip()
            if choice == "0":
                running = False
                print("Leaving Module 2.")
            elif choice == "1":
                print(loading_text(loaded))
            elif choice == "2":
                print(search_text(table, input("FarmID: ").strip()))
            elif choice == "3":
                farm_id = validate_id(input("FarmID from dataset.csv: ").strip())
                # Select an insertion record by scanning the already-loaded records.
                # search(FarmID) above probes the manual hash table.
                record = None
                for candidate in loaded.records:
                    if candidate.farm_id == farm_id:
                        record = candidate
                        break
                if record is None:
                    raise RecordValidationError("FarmID {} is not present in dataset.csv.".format(farm_id))
                table.insert(record)
                if table.last_resize is not None:
                    print(resize_text(table.last_resize))
                print(trace_text(table.last_trace))
                if table.last_load_sample is not None:
                    print(load_text(table.last_load_sample))
                print(summary_text(table))
            elif choice == "4":
                print(delete_text(table, input("FarmID: ").strip()))
            elif choice == "5":
                print(table_text(table))
            elif choice == "6":
                records = read_farm_records(dataset_path)
                text, evidence = run_demo(records, len(records))
                print(text, end="")
            elif choice == "7":
                replacement = load_lookup(dataset_path)
                loaded = replacement
                print(loading_text(loaded))
            else:
                print("Invalid hash option. Enter a number from 0 to 7.")
        except (RecordValidationError, HashTableError, HashDataError) as error:
            print("Error: {}".format(error))
            if isinstance(error, DuplicateFarmError) and table.last_trace is not None:
                print(trace_text(table.last_trace))
        except (EOFError, KeyboardInterrupt):
            running = False
            print("\nInput ended. Leaving Module 2.")
    return loaded
