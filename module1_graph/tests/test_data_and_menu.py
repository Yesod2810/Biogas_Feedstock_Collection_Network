"""Author: Thanh Dat Nguyen
Student ID: 23857030
Date: 21/09/2026
Purpose: Data integrity, network integration and real command-line behaviour.
"""

from manual_structures import LinkedList, ManualSet, manual_all, manual_count, manual_map
from manual_io import CSVWriter
from test_support import SequenceTestCase


import csv
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from module1_graph.build_network import build, estimate_minutes, haversine_km
from module1_graph.data_loader import (DEFAULT_DATA_DIR, DataError, HUB_ID,
    ISOLATED_ID, PROJECT_ROOT, check_specification, load_network, read_csv, read_farms, source_ids)
from module1_graph.graph import Location
from module1_graph.prepare_data import prepare


class DataTests(SequenceTestCase):
    def test_dataset_has_125_unique_wa_farm_ids(self):
        farms = read_farms()
        self.assertEqual(len(farms), 125)
        self.assertEqual(len(ManualSet(farms)), 125)

    def test_raw_to_prepared_data_changes_only_three_id_cells(self):
        raw = read_csv(DEFAULT_DATA_DIR / "farm_dataset_red_meat_WA.csv", ("Id",))
        prepared = read_csv(DEFAULT_DATA_DIR / "dataset.csv", ("Id",))
        self.assertEqual(len(raw), len(prepared))
        changed = LinkedList()
        for old, new in zip(raw, prepared):
            self.assertEqual(old.keys(), new.keys())
            for column in old:
                if old[column] != new[column]:
                    self.assertEqual(column, "Id")
                    self.assertEqual(source_ids(new), (new["Id"], new["Id"]))
                    changed.append((old[column], new[column]))
        self.assertEqual(ManualSet(changed), ManualSet((("6.50E+31", "65e30"), ("6.00E+64", "60e63"), ("8.00E+06", "80e05"))))

    def test_raw_corrupted_ids_are_rejected_by_loader(self):
        with self.assertRaisesRegex(DataError, "FarmID"):
            read_farms(DEFAULT_DATA_DIR / "farm_dataset_red_meat_WA.csv")

    def test_dataset_reconstruction_is_reproducible(self):
        with tempfile.TemporaryDirectory() as directory:
            data_dir = Path(directory)
            raw = DEFAULT_DATA_DIR / "farm_dataset_red_meat_WA.csv"
            (data_dir / raw.name).write_bytes(raw.read_bytes())
            self.assertEqual(len(prepare(data_dir)), 3)
            self.assertEqual((data_dir / "dataset.csv").read_bytes(),
                             (DEFAULT_DATA_DIR / "dataset.csv").read_bytes())

    def test_missing_file_is_actionable(self):
        with self.assertRaisesRegex(DataError, "Cannot read"):
            read_farms(DEFAULT_DATA_DIR / "not_a_file.csv")

    def test_missing_columns_empty_data_and_malformed_csv(self):
        for text in ("Id\nx\n", "Id,Name\n", "Id,Id\nx,x\n", "Id,Name\nx,Name,extra\n",
                     "Id,Name\nx\n"):
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "invalid.csv"
                path.write_text(text, encoding="utf-8")
                with self.assertRaises(DataError):
                    read_csv(path, ("Id", "Name"))

    def test_reject_bad_region_duplicate_id_and_coordinates(self):
        rows = read_csv(DEFAULT_DATA_DIR / "dataset.csv", ("Id",))
        variants = LinkedList()
        for field, value in (("State", "VIC"), ("Country", "United States"),
                             ("Lat", "nan"), ("Lng", "181"), ("Name", ""),
                             ("Species", ""), ("Id", "wrong")):
            row = manual_map(rows[0])
            row[field] = value
            variants.append(LinkedList((row,)))
        variants.append(LinkedList((manual_map(rows[0]), manual_map(rows[0]))))
        for records in variants:
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "invalid.csv"
                with path.open("w", encoding="utf-8", newline="") as stream:
                    writer = CSVWriter(stream, fieldnames=LinkedList(rows[0]))
                    writer.writeheader()
                    writer.writerows(records)
                with self.assertRaises(DataError):
                    read_farms(path)

    def test_both_urls_must_agree(self):
        row = read_csv(DEFAULT_DATA_DIR / "dataset.csv", ("Id",))[0]
        row["Map URL"] = "https://www.farmtransparency.org/map?location=wrong"
        with self.assertRaisesRegex(DataError, "disagree"):
            source_ids(row)

    def test_haversine_known_equator_arc(self):
        first = Location("A", "A", 0, 0)
        second = Location("B", "B", 0, 1)
        self.assertAlmostEqual(haversine_km(first, second), 111.1949266, places=6)
        self.assertEqual(haversine_km(first, first), 0)

    def test_time_estimation_rounds_up_and_stays_positive(self):
        self.assertEqual(estimate_minutes(10), 13)
        self.assertEqual(estimate_minutes(10.1), 14)
        self.assertEqual(estimate_minutes(0), 1)


class NetworkTests(SequenceTestCase):
    def test_test_network_counts_and_requirements(self):
        graph = load_network("test")
        self.assertEqual((graph.vertex_count, graph.edge_count), (12, 18))
        self.assertTrue(manual_all(check_specification(graph).values()))

    def test_full_network_contains_every_farm_and_hub(self):
        graph = load_network("full")
        self.assertEqual(graph.vertex_count, 126)
        self.assertEqual(ManualSet(graph.vertex_ids()), ManualSet(read_farms()) | ManualSet((HUB_ID,)))
        self.assertTrue(manual_all(check_specification(graph).values()))

    def test_exactly_one_deliberate_isolate_in_each_network(self):
        for mode in ("test", "full"):
            with self.subTest(mode=mode):
                graph = load_network(mode)
                self.assertEqual(graph.bfs(HUB_ID).unreachable, (ISOLATED_ID,))
                self.assertEqual(graph.neighbors(ISOLATED_ID), ())
                self.assertEqual(len(graph.dfs(HUB_ID).components), 2)

    def test_every_edge_is_symmetric_and_matches_estimation(self):
        for mode in ("test", "full"):
            graph = load_network(mode)
            adjacency_count = sum(len(graph.neighbors(i)) for i in graph.vertex_ids())
            self.assertEqual(adjacency_count, 2 * graph.edge_count)
            for first, second, minutes in graph.edges():
                self.assertGreater(minutes, 0)
                expected = estimate_minutes(haversine_km(graph.location(first), graph.location(second)))
                self.assertEqual(minutes, expected)
                self.assertIn((first, minutes), LinkedList(((e.destination, e.minutes) for e in graph.neighbors(second))))

    def test_invalid_network_mode(self):
        with self.assertRaises(DataError):
            load_network("wrong")

    def test_both_edge_files_rebuild_identically(self):
        with tempfile.TemporaryDirectory() as directory:
            data_dir = Path(directory)
            for filename in ("dataset.csv", "hub.csv", "test_vertices.csv"):
                (data_dir / filename).write_bytes((DEFAULT_DATA_DIR / filename).read_bytes())
            build(data_dir)
            for filename in ("test_edges.csv", "full_edges.csv"):
                self.assertEqual((data_dir / filename).read_bytes(),
                                 (DEFAULT_DATA_DIR / filename).read_bytes())

    def test_invalid_edge_records_are_rejected(self):
        for first, second, weight in ((HUB_ID, "missing", "3"), (HUB_ID, "doj25", "0"),
                                      (HUB_ID, "doj25", "nan"), (HUB_ID, "doj25", "bad")):
            with self.subTest(first=first, second=second, weight=weight):
                with tempfile.TemporaryDirectory() as directory:
                    data_dir = Path(directory)
                    for filename in ("dataset.csv", "hub.csv", "test_vertices.csv"):
                        (data_dir / filename).write_bytes((DEFAULT_DATA_DIR / filename).read_bytes())
                    (data_dir / "test_edges.csv").write_text(
                        "FromID,ToID,TransportTime\n{},{},{}\n".format(first, second, weight),
                        encoding="utf-8")
                    with self.assertRaises(DataError):
                        load_network("test", data_dir)


class MenuTests(SequenceTestCase):
    def run_app(self, args=(), inputs=None, cwd=None):
        return subprocess.run(LinkedList((sys.executable, str(PROJECT_ROOT / "interactive_menu.py"), *args)),
                              input=inputs, text=True, capture_output=True,
                              cwd=cwd or PROJECT_ROOT, timeout=20)

    def test_demo_is_runnable_from_a_different_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            result = self.run_app(("--demo",), cwd=directory)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Level 0:", result.stdout)
        self.assertIn("Detected cycle:", result.stdout)
        self.assertIn("Shortest transportation time:", result.stdout)
        self.assertIn("Unreachable location", result.stdout)
        self.assertIn("Invalid location ID", result.stdout)

    def test_full_network_validation_cli(self):
        result = self.run_app(("--network", "full", "--validate"))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(manual_count(result.stdout, "PASS:"), 5)

    def test_invalid_input_duplicate_edge_and_recovery(self):
        result = self.run_app(inputs="bad\n3\nmissing\n7\nHUB_PINJARRA\ndoj25\n5\n0\n")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Invalid option", result.stdout)
        self.assertIn("Invalid location ID", result.stdout)
        self.assertIn("Duplicate undirected edge", result.stdout)
        self.assertIn("Goodbye", result.stdout)

    def test_dynamic_insertion_then_connection(self):
        result = self.run_app(inputs="6\n3d8af\n7\nHUB_PINJARRA\n3d8af\n25\n5\n\n3d8af\n0\n")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Inserted 3d8af", result.stdout)
        self.assertIn("in both directions", result.stdout)
        self.assertIn("Shortest transportation time: 25 minutes", result.stdout)

    def test_failed_reload_keeps_current_graph(self):
        result = self.run_app(inputs="8\nwrong\n1\n0\n")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Network must be", result.stdout)
        self.assertIn("Vertices: 12 | Undirected edges: 18", result.stdout)

    def test_eof_exits_cleanly(self):
        result = self.run_app(inputs="")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Input ended", result.stdout)

    def test_missing_data_directory_returns_nonzero(self):
        with tempfile.TemporaryDirectory() as directory:
            result = self.run_app(("--data-dir", directory, "--demo"))
        self.assertEqual(result.returncode, 1)
        self.assertIn("Cannot read", result.stderr)
        self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
