from __future__ import print_function

from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "reproduction"))

try:
    import numpy as np
    import pandas as pd
    import audit_msahg_on_sthgcn_causal_materializer_v1r1_real as auditor
except ModuleNotFoundError:
    np = None
    pd = None
    auditor = None


@unittest.skipIf(auditor is None, "NumPy/pandas/SciPy runtime is unavailable")
class RealCausalMaterializerAuditTest(unittest.TestCase):
    def test_matrix_is_lexicographic_binary_or_row_normalized(self):
        raw = auditor.matrix((3, 3), [(1, 2), (0, 1), (0, 1)], "uint8")
        self.assertEqual(raw["coordinates"], [(0, 1), (1, 2)])
        self.assertEqual(raw["values"].dtype, np.dtype("uint8"))
        normalized = auditor.matrix(
            (2, 3), [(0, 2), (0, 1), (1, 0)], "float64", True
        )
        self.assertEqual(normalized["coordinates"], [(0, 1), (0, 2), (1, 0)])
        self.assertTrue(np.array_equal(normalized["values"], np.asarray([0.5, 0.5, 1.0])))

    def test_geography_reconstruction_has_self_loops_and_symmetric_radius_edges(self):
        coordinates = np.asarray(
            [[0.0, 0.0], [0.0, 0.01], [0.0, 0.20]], dtype=np.float64
        )
        edges = set(auditor.geography_coordinates(coordinates))
        self.assertTrue(all((index, index) in edges for index in range(3)))
        self.assertIn((0, 1), edges)
        self.assertIn((1, 0), edges)
        self.assertNotIn((0, 2), edges)

    def test_scenario_reconstruction_uses_immediate_prefix(self):
        frame = pd.DataFrame(
            [
                {
                    "check_ins_id": 1,
                    "source_ordinal": 10,
                    "raw_trajectory_id": "t",
                    "pseudo_session_trajectory_id": "t",
                    "pseudo_session_trajectory_rank": 1,
                    "SplitTag": "ignore",
                    "_user_index": 0,
                    "_poi_index": 1,
                    "_timestamp": pd.Timestamp("2024-01-06 09:00:00"),
                },
                {
                    "check_ins_id": 2,
                    "source_ordinal": 11,
                    "raw_trajectory_id": "t",
                    "pseudo_session_trajectory_id": "t",
                    "pseudo_session_trajectory_rank": 2,
                    "SplitTag": "validation",
                    "_user_index": 0,
                    "_poi_index": 0,
                    "_timestamp": pd.Timestamp("2024-01-08 09:00:00"),
                },
            ]
        )
        rows = auditor.reconstruct_scenarios(frame, {0: 1}, {0: 0, 1: 1})
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["prefix_source_ordinal"], 10)
        self.assertEqual(rows[0]["TimeGroup"], 1)
        self.assertEqual(rows[0]["POIGroup"], 1)
        self.assertEqual(rows[0]["marginal_tasks"], ["User/1", "Time/1", "POI/1"])

    def test_support_floor_reports_exact_failed_cells(self):
        support = {
            split: {
                "marginal": {
                    task: {"targets": 500, "distinct_users": 50}
                    for task in auditor.AXIS_TASKS
                },
                "joint_cells": {},
            }
            for split in auditor.LEGAL_SPLITS
        }
        floors = {
            "train": {"targets": 200, "distinct_users": 30},
            "validation": {"targets": 100, "distinct_users": 30},
            "test": {"targets": 100, "distinct_users": 30},
        }
        passed, failures = auditor.support_floor_pass(support, floors)
        self.assertTrue(passed)
        self.assertEqual(failures, [])
        support["test"]["marginal"]["POI/1"]["distinct_users"] = 29
        passed, failures = auditor.support_floor_pass(support, floors)
        self.assertFalse(passed)
        self.assertEqual(
            failures,
            [
                {
                    "split": "test",
                    "task": "POI/1",
                    "measure": "distinct_users",
                    "observed": 29,
                    "required": 30,
                }
            ],
        )


if __name__ == "__main__":
    unittest.main()
