"""Author: Thanh Dat Nguyen
Student ID: 23857030
Date: 11/10/2026
Purpose: Manage the sorted request database and run reproducible benchmarks.
"""

from manual_structures import LinkedList, manual_contains

from .benchmark import run_benchmarks, table_text
from .datasets import generate_records
from .records import SortDataError


def sort_menu(database, data_dir, output_dir):
    running = True
    while running:
        print('\nCOMP5008 - MODULE 4 | {} archived collection records'.format(len(database.records())))
        print('1. Display records in ascending transportation time')
        print('2. Re-sort the database using Merge Sort (stable)')
        print('3. Re-sort the database using Quick Sort (median-of-three, three-way)')
        print('4. Add 100 educational historic request events from the full graph')
        print('5. Export the sorted database as CSV')
        print('6. Benchmark both algorithms: 100, 500, 1000 x three conditions')
        print('0. Leave Module 4')
        try:
            choice = input('Choose a sorting option: ').strip()
            if choice == '0':
                running = False
                print('Leaving Module 4.')
            elif choice == '1':
                records = database.records()
                if not records:
                    print('Empty database: submit requests through Module 3 or use option 4.')
                for record in records:
                    print('{} | {} | {} | T={:g} min | {}'.format(record.record_id,
                        record.request.request_id, record.request.farm_id, record.transport_minutes, record.status))
            elif manual_contains(('2', '3'), choice):
                algorithm = 'merge' if choice == '2' else 'quick'
                ordered = database.save(database.records(), algorithm)
                print('{} Sort stored {} records in ascending T.'.format(algorithm.title(), len(ordered)))
            elif choice == '4':
                records, metadata = generate_records(100, data_dir=data_dir)
                from dataclasses import replace
                batch = database.new_session().session_id
                records = LinkedList((replace(record, record_id='M{:06d}_{}'.format(batch, record.record_id)) for record in records))
                database.import_records(records)
                print('Added 100 modelled historic events; times come from full-network Dijkstra routes.')
            elif choice == '5':
                path = output_dir / 'collection_records_sorted.csv'
                database.export_csv(path)
                print('Exported {} records to {}.'.format(len(database.records()), path))
            elif choice == '6':
                rows, metadata = run_benchmarks(output_dir / 'sorting', output_dir / 'sort_inputs', data_dir)
                print(table_text(rows), end='')
                print('Saved all inputs, both sorted outputs, raw timing samples and metadata.')
            else:
                print('Invalid sorting option. Enter a number from 0 to 6.')
        except (SortDataError, OSError, ValueError) as error:
            print('Error: {}'.format(error))
        except (EOFError, KeyboardInterrupt):
            running = False
            print('\nInput ended. Leaving Module 4.')
