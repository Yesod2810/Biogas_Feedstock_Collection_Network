"""Author: Thanh Dat Nguyen
Student ID: 23857030
Date: 16/10/2026
Purpose: Run from any working directory: python /path/to/interactive_menu.py.
"""

from manual_structures import manual_all, manual_contains


import argparse
from pathlib import Path
import sys

from module1_graph.data_loader import (DEFAULT_DATA_DIR, DataError, HUB_ID,
                                      check_specification, load_network, read_farms)
from module1_graph.display import bfs_text, demo_text, dfs_text, path_text, specification_text
from module1_graph.graph import GraphError
from module2_hash.data_loader import HashDataError, load_lookup, read_farm_records
from module2_hash.display import summary_text as hash_summary_text
from module2_hash.hash_table import HashTableError
from module2_hash.interactive import hash_menu
from module2_hash.records import RecordValidationError
from module2_hash.test_driver import run_demo as hash_demo
from module3_heap.data_loader import RequestDataError
from module3_heap.interactive import heap_menu
from module3_heap.max_heap import HeapError
from module3_heap.requests import RequestValidationError
from module3_heap.scheduler import CollectionScheduler, SchedulingError
from module3_heap.test_driver import run_demo as heap_demo
from module4_sorting.benchmark import run_benchmarks, table_text
from module4_sorting.database import CollectionDatabase
from module4_sorting.interactive import sort_menu
from module4_sorting.records import SortDataError
from module4_sorting.test_driver import run_demo as sorting_demo, validate as validate_sorting
from integration_demo import run_integration_demo


def source_prompt():
    answer = input("Source ID (Enter for HUB_PINJARRA): ").strip()
    return answer if answer else HUB_ID


def menu(graph, mode, data_dir, output_dir=None):
    running = True
    lookup = None
    collection = None
    database = None
    output_dir = output_dir or data_dir.parent / 'collection_output'
    while running:
        print("\nCOMP5008 - INTEGRATED SYSTEM | {} | {} vertices, {} edges".format(
            mode.upper(), graph.vertex_count, graph.edge_count))
        print("1. List locations and check the test-graph specification")
        print("2. Display the adjacency-list graph")
        print("3. BFS levels")
        print("4. DFS cycle detection (all components)")
        print("5. Dijkstra shortest route")
        print("6. Insert a farm from dataset.csv into this session")
        print("7. Insert a weighted undirected edge into this session")
        print("8. Reload test or full network (resets graph and scheduling sessions)")
        print("9. Run all demonstration outputs")
        print("10. Module 2: hash-based farm lookup")
        print("11. Module 3: heap-based collection scheduling")
        print("12. Module 4: sorted collection database and sorting benchmarks")
        print("13. Run the end-to-end four-module demonstration (fresh session)")
        print("0. Exit")
        try:
            choice = input("Choose an option: ").strip()
            if choice == "0":
                running = False
                print("Goodbye.")
            elif choice == "1":
                print(specification_text(graph))
                for farm_id in graph.vertex_ids():
                    location = graph.location(farm_id)
                    print("{} | {} | {}".format(farm_id, location.name, location.suburb))
            elif choice == "2":
                print(graph.describe())
            elif choice == "3":
                print(bfs_text(graph, source_prompt()))
            elif choice == "4":
                print(dfs_text(graph, source_prompt()))
            elif choice == "5":
                source = source_prompt()
                destination = input("Destination ID: ").strip()
                print(path_text(graph, source, destination))
            elif choice == "6":
                farm_id = input("FarmID from dataset.csv: ").strip()
                farms = read_farms(data_dir / "dataset.csv")
                if not manual_contains(farms, farm_id):
                    raise GraphError("FarmID is not present in dataset.csv.")
                graph.add_vertex(farms[farm_id])
                print("Inserted {} as an isolated location in this session.".format(farm_id))
            elif choice == "7":
                first = input("First location ID: ").strip()
                second = input("Second location ID: ").strip()
                text = input("Estimated transport time in minutes (> 0): ").strip()
                try:
                    minutes = float(text)
                except (ValueError, OverflowError) as error:
                    raise GraphError("Transport time must be a finite positive number.") from error
                graph.add_edge(first, second, minutes)
                print("Inserted {} <-> {} ({} min) in both directions.".format(
                    first, second, format(minutes, "g")))
            elif choice == "8":
                requested = input("Network (test/full): ").strip().lower()
                replacement = load_network(requested, data_dir)
                if collection is not None:
                    collection.cancel_pending('Network reloaded; scheduling session reset.')
                graph, mode = replacement, requested
                collection = None
                print("Loaded {} network.".format(mode))
            elif choice == "9":
                print(demo_text(graph, mode))
            elif choice == "10":
                if lookup is None:
                    lookup = load_lookup(data_dir / "dataset.csv")
                lookup = hash_menu(lookup, data_dir / "dataset.csv")
                if collection is not None:
                    collection.rebind_lookup(lookup.table)
            elif choice == "11":
                if lookup is None:
                    lookup = load_lookup(data_dir / "dataset.csv")
                if collection is None:
                    if database is None:
                        database = CollectionDatabase(output_dir / 'collection_records.sqlite3')
                    collection = CollectionScheduler(lookup.table, graph, archive=database.new_session())
                collection = heap_menu(collection, data_dir, mode)
            elif choice == "12":
                if database is None:
                    database = CollectionDatabase(output_dir / 'collection_records.sqlite3')
                sort_menu(database, data_dir, output_dir)
            elif choice == "13":
                text, evidence = run_integration_demo(data_dir, mode, output_dir / 'integration')
                print(text, end='')
            else:
                print("Invalid option. Enter a number from 0 to 13.")
        except (GraphError, DataError, HashDataError, HashTableError, RecordValidationError,
                RequestDataError, RequestValidationError, SchedulingError, HeapError, SortDataError) as error:
            print("Error: {}".format(error))
        except (EOFError, KeyboardInterrupt):
            running = False
            print("\nInput ended. Goodbye.")
    if database is not None:
        try:
            if collection is not None:
                collection.cancel_pending('Application ended; queue no longer active.')
        finally:
            database.close()
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description="COMP5008: farm graph, hash lookup, heap scheduling and sorting")
    parser.add_argument("--module", choices=("graph", "hash", "heap", "sort"), default="graph")
    parser.add_argument("--network", choices=("test", "full"), default="test")
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--output-dir", type=Path, help="Persistent database and interactive exports directory")
    actions = parser.add_mutually_exclusive_group()
    actions.add_argument("--demo", action="store_true", help="Print reproducible results and exit")
    actions.add_argument("--validate", action="store_true", help="Validate the selected module and exit")
    actions.add_argument("--benchmark", action="store_true", help="Run Module 4 timing experiments")
    actions.add_argument("--integrated-demo", action="store_true", help="Run and export the complete four-module data flow")
    args = parser.parse_args(argv)
    output_dir = args.output_dir or args.data_dir.parent / 'collection_output'
    if args.benchmark and args.module != 'sort':
        parser.error('--benchmark requires --module sort')
    try:
        if args.integrated_demo:
            text, evidence = run_integration_demo(args.data_dir, args.network, output_dir / 'integration')
            print(text, end='')
            return 0
        if args.module == 'sort':
            if args.benchmark:
                rows, metadata = run_benchmarks(output_dir / 'sorting', output_dir / 'sort_inputs', args.data_dir)
                print(table_text(rows), end='')
                return 0
            if args.demo:
                text, evidence = sorting_demo(args.data_dir)
                print(text, end='')
                return 0
            if args.validate:
                checks, metadata = validate_sorting(args.data_dir)
                for row in checks:
                    print('PASS: {size} / {condition} / both algorithms'.format(**row))
                return 0
            database = CollectionDatabase(output_dir / 'collection_records.sqlite3')
            try:
                sort_menu(database, args.data_dir, output_dir)
            finally:
                database.close()
            return 0
        if args.module == "heap":
            if args.demo or args.validate:
                output, evidence = heap_demo(args.network, args.data_dir)
                if args.demo:
                    print(output, end="")
                    return 0
                checks = (evidence["main_insertions"] >= 10,
                          evidence["main_extractions"] >= 5,
                          evidence["deleted_before_insert_rejected"],
                          bool(evidence["deleted_after_queue_skipped"]),
                          evidence["zero_time_fixture"]["TransportTime"] == 0)
                for description, passed in zip(("At least ten heap insertions", "At least five extractions",
                    "Deleted farm rejected", "Stale queued farm skipped", "Zero transport time handled"), checks):
                    print("{}: {}".format("PASS" if passed else "FAIL", description))
                return 0 if manual_all(checks) else 1
            lookup = load_lookup(args.data_dir / "dataset.csv")
            graph = load_network(args.network, args.data_dir)
            database = CollectionDatabase(output_dir / 'collection_records.sqlite3')
            scheduler = CollectionScheduler(lookup.table, graph, archive=database.new_session())
            try:
                scheduler = heap_menu(scheduler, args.data_dir, args.network)
                scheduler.cancel_pending('Application ended; queue no longer active.')
            finally:
                database.close()
            return 0
        if args.module == "hash":
            dataset_path = args.data_dir / "dataset.csv"
            if args.demo:
                records = read_farm_records(dataset_path)
                output, evidence = hash_demo(records, len(records))
                print(output, end="")
                return 0
            loaded = load_lookup(dataset_path)
            if args.validate:
                print(hash_summary_text(loaded.table))
                enough = loaded.table.size >= 40
                found = manual_all(loaded.table.search(record.farm_id) == record for record in loaded.records)
                print("{}: At least 40 unique farm records".format("PASS" if enough else "FAIL"))
                print("{}: All complete inserted records are searchable".format("PASS" if found else "FAIL"))
                return 0 if enough and found else 1
            hash_menu(loaded, dataset_path)
            return 0
        graph = load_network(args.network, args.data_dir)
        if args.demo:
            print(demo_text(graph, args.network), end="")
            return 0
        if args.validate:
            print(specification_text(graph))
            return 0 if manual_all(check_specification(graph).values()) else 1
        return menu(graph, args.network, args.data_dir, output_dir)
    except (DataError, GraphError, HashDataError, HashTableError, RecordValidationError,
            RequestDataError, RequestValidationError, SchedulingError, HeapError, SortDataError) as error:
        print("Error: {}".format(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
