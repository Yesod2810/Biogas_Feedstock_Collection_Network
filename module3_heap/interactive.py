"""Author: Thanh Dat Nguyen
Student ID: 23857030
Date: 3/10/2026
Purpose: Interactive integrated request queue. All heap mutations print array states.
"""

from manual_structures import LinkedList

from module2_hash.display import delete_text
from module2_hash.records import RecordValidationError

from .data_loader import RequestDataError, read_requests
from .max_heap import HeapError
from .requests import RequestValidationError, calculation_text
from .scheduler import CollectionScheduler, SchedulingError
from .test_driver import run_demo


def heap_menu(scheduler, data_dir, mode):
    running = True
    while running:
        print("\nCOMP5008 - MODULE 3 | {} network | {} queued requests".format(mode, scheduler.heap.size))
        print("1. Load collection_requests.csv into the current queue")
        print("2. Submit a collection request")
        print("3. Peek at the highest priority (no removal)")
        print("4. Extract the highest eligible collection request")
        print("5. Extract all eligible requests and show the collection order")
        print("6. Display the current heap array")
        print("7. Reset scheduling session (clear queue and request-ID history)")
        print("8. Run independent demonstration with fresh graph/hash structures")
        print("9. Delete a farm from the shared hash table (validation scenario)")
        print("0. Leave Module 3")
        try:
            choice = input("Choose a scheduling option: ").strip()
            if choice == "0":
                running = False
                print("Leaving Module 3.")
            elif choice == "1":
                accepted = 0
                for raw in read_requests(data_dir / "collection_requests.csv"):
                    try:
                        scheduler.submit(raw.request_id, raw.farm_id, raw.estimated_feedstock)
                        accepted += 1
                    except (SchedulingError, RequestValidationError, RecordValidationError) as error:
                        print("REJECT {} | {}".format(raw.request_id, error))
                print("Accepted {} requests; {} now queued.".format(accepted, scheduler.heap.size))
            elif choice == "2":
                request_id = input("RequestID: ").strip()
                farm_id = input("FarmID: ").strip()
                quantity = input("EstimatedFeedstock (educational tonnes, > 0): ").strip()
                scheduler.submit(request_id, farm_id, quantity)
            elif choice == "3":
                request = scheduler.peek()
                print("Empty heap: no collection request." if request is None
                      else "PEEK (heap unchanged): " + calculation_text(request))
            elif choice == "4":
                scheduler.extract_priority()
            elif choice == "5":
                order = LinkedList()
                while scheduler.heap.size > 0:
                    request = scheduler.extract_priority()
                    if request is not None:
                        order.append(request.request_id)
                print("COLLECTION ORDER: " + (" -> ".join(order) if order else "[no eligible requests]"))
            elif choice == "6":
                print(scheduler.heap.array_text())
            elif choice == "7":
                scheduler.cancel_pending()
                archive = scheduler.archive.new_session() if scheduler.archive is not None else None
                scheduler = CollectionScheduler(scheduler.lookup, scheduler.graph,
                                                hub_id=scheduler.hub_id, archive=archive)
                print("Scheduling session reset. Heap is empty.")
            elif choice == "8":
                text, evidence = run_demo(mode, data_dir)
                print(text, end="")
            elif choice == "9":
                print(delete_text(scheduler.lookup, input("FarmID to delete from hash table: ").strip()))
            else:
                print("Invalid scheduling option. Enter a number from 0 to 9.")
        except (RequestDataError, RequestValidationError, RecordValidationError, SchedulingError, HeapError) as error:
            print("Error: {}".format(error))
        except (EOFError, KeyboardInterrupt):
            running = False
            print("\nInput ended. Leaving Module 3.")
    return scheduler
