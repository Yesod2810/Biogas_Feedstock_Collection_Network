# Module 2 - Hash-Based Farm Lookup

## Short design justification

**Strategy.** Open addressing with linear probing stores complete immutable
farm records in a NumPy object array. It keeps collision handling visible and avoids
an additional linked-list implementation. The three slot states are never-used
`EMPTY`, occupied `FarmRecord`, and a `DELETED` tombstone. A disadvantage is
primary clustering: nearby occupied homes can merge into long runs. The
0.70 active-load limit, 0.85 occupied-load limit and rehashing control normal load without guaranteeing
constant performance for every possible set of IDs.

**Modulo hash.** Starting at zero, for each character of the original
five-character ID compute `h = (31*h + ord(character)) % m`. Character order
affects the result, unlike an unweighted character sum. The final `h` is the
home slot. Linear probing checks `(h + i) % m` for `i = 0, ..., m-1`.
Neither `hash()` nor a dictionary/map/set implements the index.

**Capacity and primes.** The default capacity is 11, deliberately small enough
to expose collisions and resizing. Growth uses the next prime at or above
`max(2*m, ceil((n+1)/threshold))`. The import uses 11, 23, 47, 97 and 197.
Primes are a reasonable modulo-size convention; they do not guarantee an even
distribution. Because linear probing steps by one, it visits every slot even
at a composite capacity; primality is not required for probe coverage. The
default sizes also avoid the degenerate case `m = 31` for this base-31 hash.

**Growth, cleanup and deletion.** Before projected active load `(n+1)/m`
exceeds 0.70, grow and rehash. Let `t` count tombstones: occupied load is
`(n+t)/m`. If an insertion into a never-used slot would make occupied load
exceed 0.85 while active load fits, rehash at the same capacity to remove
tombstones. Reusing a tombstone does not increase occupied load. Deletion
leaves a tombstone and does not shrink; this preserves probe chains and avoids
resize oscillation. The gap between thresholds prevents repeated cleanup near
active load 0.70; for a custom active threshold x, the occupied limit is (1+x)/2.
Every moved live record is hashed using the new capacity.

**Performance.** With fixed five-character keys, appropriate hash distribution
and bounded occupied load, search and delete are expected O(1). Insertion is
expected amortized O(1). A rehash costs expected O(m+n), including array
allocation and scanning. Growth has m proportional to n; cleanup requires
many accumulated tombstones because the thresholds differ. A normal operation
can probe O(m) slots in the worst case. Adversarial clustering can make an entire
rehash O(m+n*m), hence O(n^2) when m is proportional to n. The NumPy slot array and latest
probe traces take O(m) space; records take O(n*r)
for r source fields (r=20 here). Saved demonstration histories are outside
the core index. These are expected bounds, not claims that every run is O(1).

## API

| Method / property | Contract |
|---|---|
| `HashTable(initial_capacity=11, max_load=0.70)` | Prime-adjusted NumPy-array capacity; positive threshold below one |
| `insert(record)` | Insert a `FarmRecord`; return True; duplicate raises `DuplicateFarmError` |
| `search(FarmID)` | Complete `FarmRecord` or `None` |
| `delete(FarmID)` | Removed `FarmRecord` or `None`; leave a tombstone |
| `hash_index(FarmID)` | Modulo-based home slot at the current capacity |
| `size`, `capacity`, `tombstones` | Active count, allocated slots and deleted markers |
| `load_factor`, `occupied_factor` | `n/m` and `(n+t)/m` |
| `max_load`, `max_occupied` | Active threshold 0.70 and occupied threshold 0.85 by default |
| `last_trace` | Immutable probe sequence, result and slot for the latest operation |
| `pre_resize_trace`, `last_resize` | Original duplicate-check probe and growth/compaction event, where applicable |
| `last_load_sample` | Set on each tenth successful public insertion; rehash moves do not increment it |
| `slot_views()` | Immutable slot-state snapshot for inspection |

Invalid ID syntax, empty names, invalid/non-finite/out-of-range coordinates
and malformed input files are rejected with clear exceptions. The CLI catches
these errors and continues. Unknown, syntactically valid IDs return `None`.
Five lowercase ASCII letters/digits match the supplied website's IDs; IDs
are never numerically converted, normalised or renumbered.

The record contains ID, Name, Species, Lat, Lng, Street Num, Street, Suburb,
State, Postcode and Country, plus all nine extra source columns. Missing source
address values remain blank. Only farms are in this lookup; the model hub
belongs to Module 1. Existing corrected website IDs are shared unchanged.

## Run and inspect

From the project root:

```bash
python interactive_menu.py --module hash
python interactive_menu.py --module hash --demo
python interactive_menu.py --module hash --validate
python -m module2_hash.test_driver
python -m module2_hash.test_driver --count 40
python -m unittest discover -s module2_hash/tests -v
```

The standalone driver inserts 125 real records by default. `--count 40`
demonstrates the minimum required size. It prints successful/unsuccessful
searches, successful/repeated/missing deletions, duplicate rejection, explicit
collision states, load factors at insertions 10, 20, ... and every rehash.

For a collision at capacity 11, `3d8af` and `71a14` both hash to 5. The second
record occupies slot 6. After deleting the first record, slot 5 is `DELETED`,
and search crosses it to find `71a14` at 6. A duplicate at 6 is still rejected
before the tombstone can be reused. Reinserting the removed record probes
until absence is established, then reuses 5.

Evidence files are `sample_output/hash_demo.txt`, `hash_validation.json`,
`hash_load_factors.csv`, and `hash_interactive_session.txt`. The complete
project test log is `sample_output/test_results.txt`.
