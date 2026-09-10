from __future__ import print_function

import importlib.util
from pathlib import Path
import tempfile
import unittest

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "reproduction" / "sthgcn_sample_materializer_r1.py"
SPEC = importlib.util.spec_from_file_location("sthgcn_sample_materializer_r1", str(MODULE_PATH))
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def t(value):
    return pd.Timestamp(value)


class STHGCNSampleMaterializerR1Test(unittest.TestCase):
    def test_tky_isolation_keeps_exact_24_hour_neighbors(self):
        frame = pd.DataFrame(
            {
                "_raw_user_id": [1, 1, 1, 2, 2],
                "_local_time": [
                    t("2020-01-01 00:00:00"),
                    t("2020-01-02 00:00:00"),
                    t("2020-01-05 00:00:00"),
                    t("2020-01-01 00:00:00"),
                    t("2020-01-04 00:00:01"),
                ],
                "_source_ordinal": range(5),
            }
        )
        kept = MODULE._remove_isolated_tky(frame)
        self.assertEqual(kept["_source_ordinal"].tolist(), [0, 1])

    def test_session_break_is_strictly_greater_than_1440_minutes(self):
        frame = pd.DataFrame(
            {
                "_raw_user_id": [1, 1, 1, 2],
                "_local_time": [
                    t("2020-01-01 00:00:00"),
                    t("2020-01-02 00:00:00"),
                    t("2020-01-03 00:00:01"),
                    t("2020-01-01 00:00:00"),
                ],
                "_source_ordinal": range(4),
            }
        )
        result = MODULE._sessionize_tky(frame)
        self.assertEqual(result["_raw_trajectory_id"].tolist(), [0, 0, 1, 2])

    def test_train_only_encoding_and_padding_conventions(self):
        frame = pd.DataFrame({"x": ["b", "a", "z"], "split": [True, True, False]})
        nyc = frame.copy()
        nyc_meta = MODULE._encode_column(nyc, nyc["split"], "x", False)
        self.assertEqual(nyc["x"].tolist(), [1, 0, 2])
        self.assertEqual(nyc_meta["padding_id"], 2)
        tky = frame.copy()
        tky_meta = MODULE._encode_column(tky, tky["split"], "x", True)
        self.assertEqual(tky["x"].tolist(), [2, 1, 0])
        self.assertEqual(tky_meta["padding_id"], 0)

    def test_portable_epoch_is_host_timezone_independent_definition(self):
        values = pd.Series([t("1970-01-01 00:00:00"), t("1970-01-02 00:00:00")])
        self.assertEqual(MODULE._portable_epoch(values).tolist(), [0, 86400])

    def test_target_rules_exclude_first_and_keep_final_dev_endpoint(self):
        frame = pd.DataFrame(
            {
                "_raw_user_id": [1, 1, 1, 1],
                "_raw_poi_id": ["a", "b", "c", "d"],
                "_raw_category_id": ["x", "x", "y", "y"],
                "_raw_trajectory_id": ["s", "s", "s", "s"],
                "_category_name": ["x", "x", "y", "y"],
                "_latitude": [1.0] * 4,
                "_longitude": [2.0] * 4,
                "_local_time": pd.to_datetime(
                    ["2020-01-01", "2020-01-02", "2020-01-03", "2020-01-04"]
                ),
                "_source_ordinal": range(4),
                "_split_original": ["train", "train", "validation", "validation"],
            }
        )
        sample, eligible, _ = MODULE._finalize(frame, "nyc")
        self.assertEqual(eligible["train"]["raw_poi_id"].tolist(), ["b"])
        self.assertEqual(eligible["validation"]["raw_poi_id"].tolist(), [])
        self.assertEqual(sample["SplitTag"].tolist(), ["ignore", "train", "ignore", "validation"])

    def test_existing_output_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "exists"
            path.mkdir()
            with self.assertRaises(MODULE.MaterializationError):
                MODULE.materialize_dataset("nyc", Path("missing"), path)

    def test_csv_serialization_is_byte_deterministic(self):
        frame = pd.DataFrame(
            {
                "integer": [2, 1],
                "text": ["a,b", "line"],
                "floating": [1.25, 2.5],
            }
        )
        with tempfile.TemporaryDirectory() as temporary:
            first = Path(temporary) / "first.csv"
            second = Path(temporary) / "second.csv"
            MODULE._write_csv(first, frame)
            MODULE._write_csv(second, frame)
            self.assertEqual(first.read_bytes(), second.read_bytes())

    def test_runtime_authority_is_clean_and_contains_registration(self):
        authority = MODULE.verify_reproduction_authority()
        self.assertEqual(authority["implementation_commit"], MODULE._git(ROOT, "rev-parse", "HEAD"))

    def test_registered_count_witnesses_are_exact(self):
        self.assertEqual(
            MODULE.EXPECTED,
            {
                "nyc": {"users": 1048, "pois": 4981, "post_filter_events": 103941, "trajectories": 14130},
                "tky": {"users": 2282, "pois": 7833, "post_filter_events": 405000, "trajectories": 65499},
            },
        )

    def test_output_contract_contains_no_graph_or_scenario_file(self):
        names = set(MODULE.OUTPUT_COLUMNS)
        self.assertFalse(any("graph" in value.lower() for value in names))
        self.assertFalse(any("scenario" in value.lower() for value in names))


if __name__ == "__main__":
    unittest.main()
