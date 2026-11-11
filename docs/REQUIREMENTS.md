# Final Integration Requirements

| Requirement | Submitted evidence |
|---|---|
| Four modules interact | `integration_demo.py`; root options 10-13; `sample_output/integration/` |
| UML interaction/data flow | `docs/module_integration_uml.puml`, `.svg`, `.png`; report Section 4 |
| Required folder structure | `module1_graph/`, `module2_hash/`, `module3_heap/`, `module4_sorting/`, `data/`, `sample_output/` |
| Modular source and tests | Separate data structures, validation/loaders, menus, drivers and tests; `integration_tests/` checks the complete flow |
| Author/date/purpose headers | All 47 Python source/test/checker files have a module header; editable UML has matching comments |
| Error handling and validation | Typed graph/hash/request/storage errors; invalid IDs/weights/F; duplicate, missing, isolated, empty and stale-state cases |
| Nine report sections | System Overview; Dataset and Data Preparation; Data-Structure Justification; Module Integration; Algorithm Complexity; Experimental Results; Reflection; Limitations; AI Declaration |
| Page limit and A4 format | 18 A4 pages total: declaration p. 1, main report p. 2-16, references p. 17, appendix p. 18 |
| Complete experimental evidence | Graph/BFS/DFS/Dijkstra; 125 hash records and collisions/load checkpoints; 10 heap insertions/extractions; 9 sorting cases and 18 sorted outputs |
| Passing checks | 239 tests: original graph 62, hash 52, heap 63, sorting 54, complete integration 8|

The technical report uses clear numbered headings, consistent formatting and
page numbers. Exact benchmark inputs, raw timing samples, output CSVs, SQLite
examples and full logs remain in the ZIP; the report presents the results
without exceeding the page limit.

Data provenance is explicit: the source is the provided public-website CSV
snapshot, whose farm data was gathered on 19th September 2026 from the Farm Transparency Project website via the interactive map.
The record URLs and five spot-checks document the checks actually
performed. Hub, network times, feedstock and priority are educational modelling
attributes rather than public-source production measurements.