# Dataset notes

- Input: `farm_dataset_red_meat_WA.csv`.
- Region: Western Australia, Australia; 125 records, 20 columns.
- Farm origin: Farm Transparency Project public facilities/map database.
- The farm data was gathered on 19th September 2026 from the Farm Transparency Project website via the interactive map. No new bulk scraping is claimed.
- `dataset.csv` changes only three `Id` cells to restore the exact website IDs
  already contained in the source URL fields. See `id_corrections.csv`.
- CSV headers use the supplied `Id` spelling. It is the assignment's FarmID/ID
  field; IDs are strings and are never converted to numbers.
- All required columns are present. Some source address values are blank and
  are retained. Farm names, coordinates, categories, species and address data
  are not invented or filled by inference.
- Duplicate names are legitimate: e.g. different records are labelled
  `Unknown Feedlot`. Distinct FarmIDs remain distinct vertices.
- The `p2vf9` record's source category is `Farm (meat) (unconfirmed)`. This
  qualification is retained. Source statuses are not revalidated operating facts.
- All 125 rows have State `WA`, Country `Australia`, nonempty core graph fields
  and finite coordinates within global latitude/longitude bounds.
- Source URL consistency was checked for every record. Five website listings
  were spot-checked; a full website audit of every field was not performed.
- A missing street number is retained for Lake Preston even though a later
  website listing displays 5350. The dataset is a supplied snapshot. No broader
  address refresh is implied by the ID repair.

## Source columns

| Column | Meaning / handling |
|---|---|
| Id | Website FarmID, retained as text |
| Name | Source location name, not a unique key |
| Categories | Source classification and any uncertainty qualifier |
| Species | Animal species text from source |
| Lat / Lng | Supplied decimal-degree coordinates |
| Lat/Lng | Original combined coordinate display |
| Address Override | Source address override, where supplied |
| Street Num / Street / Suburb | Original address components; blanks allowed |
| State / Postcode / Country | Original regional/address fields |
| Last Known Status | Source snapshot status, not a new operational assessment |
| Tags / Owned By / Contracted To | Original source metadata |
| Map URL / Profile URL | Traceable website URLs and original identifier evidence |

## Separate modelling inputs

`hub.csv` is a hypothetical hub. `test_vertices.csv` selects records without
renumbering. The two edge CSVs contain unique undirected connections, each
listed once; the graph loader inserts both directions. Every `TransportTime`
is a positive educational estimate in minutes, derived by the documented
haversine/1.30 road factor/60 km/h model. `GreatCircleKm`, `RoadFactor`,
`SpeedKmh` and `Reason` explain each estimate.

The deliberate isolate `gslqa` tests unreachable behaviour. It does not imply
that Chapman Valley Feedlot is physically inaccessible.

## Educational collection requests (Module 3)

`collection_requests.csv` supplies ten real source FarmIDs and modelled
EstimatedFeedstock values from 6 to 27.5 tonnes. These are student-designed
scenarios, not measured farm production or reported source availability.
`collection_request_edge_cases.csv` includes invalid/missing ID queries and
invalid quantities for validation; it does not add any farm to the dataset.
RequestIDs such as C001 are scheduling identifiers, separate from FarmIDs.
The program obtains shortest T from Dijkstra and calculates P=F/(T+1).
No priority values are manually entered in these input files. Source farm
records and their provenance remain separate from educational request inputs.

## Module 4 sorting inputs

`sort_inputs/` contains the nine benchmark CSVs for the current Module 4
generator: 100, 500 and 1,000 request events, each random, nearly sorted and
reversed. The nearly-sorted files were regenerated with the current
`make_condition` implementation; do not treat older arrangements with the
same filenames as equivalent versions. Each file has the same row schema, so
the generator version is identified by the rules and seeds below, not by a CSV
column. These are historic educational request scenarios, not additional farm
observations. Source FarmIDs and full farm snapshots are retained.
The generator loads the actual Module 2 hash index and calls Module 1 Dijkstra
for all 125 farms; 124 have a route. Each event reuses one cached shortest time
and path. It uses Module 3 ScheduledRequest to calculate priority from F and T.
Feedstock is a modelled 2-30 tonnes. `gslqa` is excluded explicitly.
The three arrangements at one size contain identical records. Seed 23857030
fixes the generated events; the condition seed is seed + size*10 + condition
index (random=0, nearly_sorted=1, reversed=2). The current nearly-sorted
arrangement starts with our own stable Merge Sort by `TransportTime`, then
applies seeded pairwise swaps to exactly 10% of identities for these three
sizes. The matching sorted sample outputs were regenerated from these inputs.
No source measurements or original IDs are changed.
