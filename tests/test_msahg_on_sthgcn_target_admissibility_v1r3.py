from __future__ import print_function

from datetime import datetime
import unittest

from reproduction import audit_msahg_on_sthgcn_target_admissibility_v1r3 as audit


class TargetAdmissibilityV1R3Test(unittest.TestCase):
    def test_vocabulary_membership_respects_offset_and_padding(self):
        item = {"offset": 1, "classes": ["a", "b"], "padding_id": 0}
        self.assertFalse(audit._inside_vocabulary(0, item))
        self.assertTrue(audit._inside_vocabulary(1, item))
        self.assertTrue(audit._inside_vocabulary(2, item))
        self.assertFalse(audit._inside_vocabulary(3, item))
        self.assertEqual(audit._graph_index(1, item), 0)
        self.assertIsNone(audit._graph_index(0, item))

    def test_official_target_rule_filters_only_current_endpoint(self):
        rows = [
            {"split": "train", "user_index": 0, "poi_index": 0},
            {"split": "validation", "user_index": None, "poi_index": 0},
            {"split": "validation", "user_index": 0, "poi_index": None},
            {"split": "ignore", "user_index": None, "poi_index": None},
        ]
        targets, excluded = audit.official_targets(rows)
        self.assertEqual(len(targets), 1)
        self.assertEqual(excluded["validation"]["either"], 2)
        self.assertEqual(excluded["validation"]["unknown_user"], 1)
        self.assertEqual(excluded["validation"]["unknown_poi"], 1)

    def test_prefix_is_immediate_and_unknown_prefix_remains_visible(self):
        records = [
            {"trajectory_id": "a", "trajectory_rank": 0, "source_ordinal": 0, "poi_index": None},
            {"trajectory_id": "a", "trajectory_rank": 1, "source_ordinal": 1, "poi_index": 0},
            {"trajectory_id": "a", "trajectory_rank": 3, "source_ordinal": 2, "poi_index": 0},
        ]
        previous, duplicate = audit.previous_by_trajectory(records)
        self.assertEqual(previous[1]["source_ordinal"], 0)
        self.assertNotIn(2, previous)
        self.assertEqual(duplicate, [])

    def test_axis_support_is_exact_partition(self):
        records = [
            {
                "trajectory_id": "a",
                "trajectory_rank": 0,
                "source_ordinal": 0,
                "poi_index": 0,
                "timestamp": datetime(2026, 9, 7, 1, 0, 0),
            },
            {
                "trajectory_id": "a",
                "trajectory_rank": 1,
                "source_ordinal": 1,
                "poi_index": 1,
                "timestamp": datetime(2026, 9, 8, 1, 0, 0),
            },
        ]
        targets = [dict(records[1], split="validation", user_index=0)]
        support, partitions, duplicate, missing, unknown = audit.build_support(
            targets, records, {0: 1}, {0: 0, 1: 1}
        )
        self.assertEqual(support["validation"]["User/1"]["targets"], 1)
        self.assertEqual(support["validation"]["Time/0"]["targets"], 1)
        self.assertEqual(support["validation"]["POI/0"]["targets"], 1)
        self.assertEqual(partitions["validation"]["user_axis_total"], 1)
        self.assertEqual(duplicate, [])
        self.assertEqual(missing, [])
        self.assertEqual(unknown, [])


if __name__ == "__main__":
    unittest.main()
