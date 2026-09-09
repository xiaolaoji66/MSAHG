from __future__ import annotations

import unittest


class PaperMathR1StaticTest(unittest.TestCase):
    def test_registered_task_identity(self):
        from reproduction.msahg_paper_math_r1 import TASKS

        self.assertEqual(
            TASKS,
            ("User/0", "User/1", "Time/0", "Time/1", "POI/0", "POI/1"),
        )

    def test_graph_identity_is_exact(self):
        from reproduction.msahg_paper_math_r1 import GRAPH_KEYS

        self.assertEqual(len(GRAPH_KEYS), 9)
        self.assertEqual(len(GRAPH_KEYS), len(set(GRAPH_KEYS)))

    def test_split_threshold_is_strict(self):
        import torch

        from reproduction.msahg_paper_math_r1 import AdaptiveSplitMSAHG, MSAHGPaperMathCore

        wrapper = AdaptiveSplitMSAHG(MSAHGPaperMathCore(2, 3, 4, 0, 0.0), conflict_threshold=-0.5)
        similarities = torch.tensor(
            [[1.0, -0.5, -0.50001], [-0.5, 1.0, 0.0], [-0.50001, 0.0, 1.0]]
        )
        self.assertEqual(wrapper.conflicting_pairs(similarities), ((0, 2),))

    def test_split_requires_exact_partition(self):
        from reproduction.msahg_paper_math_r1 import AdaptiveSplitMSAHG, MSAHGPaperMathCore

        wrapper = AdaptiveSplitMSAHG(MSAHGPaperMathCore(2, 3, 4, 0, 0.0))
        with self.assertRaises(ValueError):
            wrapper.split_parameter(
                "user_view_gates.collaborative.weight",
                (("User/0",), ("User/0", "User/1")),
            )


if __name__ == "__main__":
    unittest.main()
