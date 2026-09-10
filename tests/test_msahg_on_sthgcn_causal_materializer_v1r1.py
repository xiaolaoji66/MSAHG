from __future__ import print_function

import copy
import io
from pathlib import Path
import sys
import unittest
import zipfile


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "reproduction"))

import msahg_on_sthgcn_causal_materializer_v1r1 as materializer


class CausalMaterializerV1R1Test(unittest.TestCase):
    def setUp(self):
        self.rows, self.encoding = materializer.synthetic_fixture()
        self.material = materializer.build_material(self.rows, self.encoding)

    def test_fixture_has_exact_marginal_partition_and_joint_metadata(self):
        self.assertEqual(len(self.material["records"]), 96)
        self.assertEqual(len(self.material["train_records"]), 80)
        self.assertEqual(len(self.material["scenario_rows"]), 84)
        self.assertEqual(len(self.material["graph_manifest"]["graphs"]), 37)
        self.assertFalse(self.material["graph_manifest"]["joint_composite_forward"])
        self.assertEqual(
            set(row["joint_triple"] for row in self.material["scenario_rows"]),
            set(
                "{}|{}|{}".format(user, time, poi)
                for user in (0, 1)
                for time in (0, 1)
                for poi in (0, 1)
            ),
        )
        for row in self.material["scenario_rows"]:
            self.assertEqual(len(row["marginal_tasks"]), 3)
            self.assertEqual(
                row["marginal_tasks"],
                [
                    "User/{}".format(row["UserGroup"]),
                    "Time/{}".format(row["TimeGroup"]),
                    "POI/{}".format(row["POIGroup"]),
                ],
            )

    def test_user_time_and_spatial_boundary_rules(self):
        self.assertEqual(
            self.material["hotel_shares"],
            {0: 0.05, 1: 0.05, 2: 0.10, 3: 0.10},
        )
        self.assertEqual(self.material["user_labels"], {0: 0, 1: 0, 2: 1, 3: 1})
        self.assertEqual(self.material["activity_center"], (0.0, 0.0))
        self.assertEqual(self.material["poi_labels"], {0: 0, 1: 0, 2: 1, 3: 1})
        self.assertEqual(
            materializer.half_hour_slot(
                materializer._parse_timestamp("2024-01-03 09:29:59")
            ),
            18,
        )
        self.assertEqual(
            materializer.half_hour_slot(
                materializer._parse_timestamp("2024-01-03 09:30:00")
            ),
            19,
        )

    def test_eval_target_content_does_not_define_its_scenario(self):
        target = next(
            row
            for row in self.rows
            if row["SplitTag"] in ("validation", "test")
        )
        before = next(
            row
            for row in self.material["scenario_rows"]
            if row["source_ordinal"] == target["source_ordinal"]
        )
        changed = copy.deepcopy(self.rows)
        changed_target = next(
            row
            for row in changed
            if row["source_ordinal"] == target["source_ordinal"]
        )
        changed_target["PoiId"] = (int(changed_target["PoiId"]) + 1) % 4
        changed_target["UTCTimeOffset"] = "2024-01-07 23:59:00"
        after_material = materializer.build_material(changed, self.encoding)
        after = next(
            row
            for row in after_material["scenario_rows"]
            if row["source_ordinal"] == target["source_ordinal"]
        )
        for name in (
            "UserGroup",
            "TimeGroup",
            "POIGroup",
            "prefix_source_ordinal",
            "prefix_poi_graph_index",
        ):
            self.assertEqual(before[name], after[name])

    def test_graph_partitions_orientation_and_normalization(self):
        graphs = self.material["graphs"]
        local = set(graphs["collaborative_local_raw"]["coordinates"])
        tourist = set(graphs["collaborative_tourist_raw"]["coordinates"])
        global_graph = set(graphs["collaborative_global_raw"]["coordinates"])
        self.assertEqual(global_graph, local | tourist)
        self.assertTrue(local.isdisjoint(tourist))
        geography = set(graphs["geography_global_raw"]["coordinates"])
        self.assertTrue(all((poi, poi) in geography for poi in range(4)))
        self.assertTrue(all((right, left) in geography for left, right in geography))
        for graph in graphs.values():
            if graph["value_dtype"] != "float64":
                continue
            row_sums = {}
            for (row, _), value in zip(graph["coordinates"], graph["values"]):
                row_sums[row] = row_sums.get(row, 0.0) + float(value)
            self.assertTrue(all(abs(value - 1.0) <= 1e-12 for value in row_sums.values()))
        source, target = self.material["transition_pairs"][0]
        self.assertIsInstance(source, int)
        self.assertIsInstance(target, int)
        source_raw = materializer._binary_graph((2, 1), [(0, 0)])
        target_raw = materializer._binary_graph((2, 1), [(1, 0)])
        source_read = materializer.row_normalize(
            materializer.transpose_sparse(source_raw)
        )
        target_write = materializer.row_normalize(target_raw)
        edge_value = source_read["values"][0] * 7.0
        output = [0.0, target_write["values"][0] * edge_value]
        self.assertEqual(output, [0.0, 7.0])

    def test_npz_serialization_is_byte_deterministic_and_exactly_three_entries(self):
        first = self.material["artifacts"]
        second = materializer.build_material(
            copy.deepcopy(self.rows), copy.deepcopy(self.encoding)
        )["artifacts"]
        self.assertEqual(first, second)
        for name, payload in first.items():
            if not name.endswith(".npz"):
                continue
            with zipfile.ZipFile(io.BytesIO(payload), "r") as archive:
                self.assertEqual(
                    archive.namelist(),
                    ["indices.npy", "values.npy", "shape.npy"],
                )
                self.assertTrue(
                    all(
                        item.date_time == (1980, 1, 1, 0, 0, 0)
                        for item in archive.infolist()
                    )
                )
                self.assertTrue(
                    all(
                        archive.read(item).startswith(b"\x93NUMPY")
                        for item in archive.infolist()
                    )
                )

    def test_nonzero_encoding_offsets_and_unknown_prefix_fail_closed(self):
        shifted = copy.deepcopy(self.rows)
        for row in shifted:
            row["UserId"] = int(row["UserId"]) + 1
            row["PoiId"] = int(row["PoiId"]) + 1
        encoding = copy.deepcopy(self.encoding)
        encoding["UserId"]["offset"] = 1
        encoding["UserId"]["padding_id"] = 5
        encoding["PoiId"]["offset"] = 1
        encoding["PoiId"]["padding_id"] = 5
        shifted_material = materializer.build_material(shifted, encoding)
        self.assertEqual(shifted_material["user_labels"], self.material["user_labels"])
        self.assertEqual(shifted_material["poi_labels"], self.material["poi_labels"])

        invalid = copy.deepcopy(self.rows)
        prefix = next(
            row
            for row in invalid
            if row["OriginalSplitTag"] != "train" and row["SplitTag"] == "ignore"
        )
        prefix["PoiId"] = self.encoding["PoiId"]["padding_id"]
        with self.assertRaises(materializer.CausalMaterializerError):
            materializer.build_material(invalid, self.encoding)

    def test_malformed_identity_coordinate_and_missing_prefix_fail_closed(self):
        duplicate = copy.deepcopy(self.rows)
        duplicate[1]["source_ordinal"] = duplicate[0]["source_ordinal"]
        with self.assertRaises(materializer.CausalMaterializerError):
            materializer.build_material(duplicate, self.encoding)
        coordinate = copy.deepcopy(self.rows)
        coordinate[0]["Latitude"] = 91.0
        with self.assertRaises(materializer.CausalMaterializerError):
            materializer.build_material(coordinate, self.encoding)
        missing_prefix = copy.deepcopy(self.rows)
        target = next(row for row in missing_prefix if row["SplitTag"] == "validation")
        target["pseudo_session_trajectory_rank"] = 3
        with self.assertRaises(materializer.CausalMaterializerError):
            materializer.build_material(missing_prefix, self.encoding)


if __name__ == "__main__":
    unittest.main()
