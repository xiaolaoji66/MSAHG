from __future__ import print_function

import importlib.util
from pathlib import Path
import tempfile
import unittest

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "reproduction" / "sthgcn_sample_materializer_v1r1_provenance.py"
SPEC = importlib.util.spec_from_file_location("sthgcn_sample_materializer_v1r1_provenance", str(MODULE_PATH))
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class SplitProvenanceV1R1Test(unittest.TestCase):
    def test_sidecar_recovers_ignored_original_splits_without_inference(self):
        sample, source = MODULE._synthetic_frames()
        sidecar = MODULE.build_sidecar(sample, source)
        self.assertEqual(list(sidecar.columns), MODULE.SIDECAR_COLUMNS)
        self.assertEqual(
            sidecar["OriginalSplitTag"].tolist(),
            ["train", "train", "validation", "validation", "test"],
        )
        self.assertEqual(sidecar["SplitTag"].tolist(), sample["SplitTag"].tolist())

    def test_visible_split_mismatch_is_rejected(self):
        sample, source = MODULE._synthetic_frames()
        source.loc[source["_source_ordinal"].eq(1), "_split_original"] = "test"
        with self.assertRaises(MODULE.ProvenanceError):
            MODULE.build_sidecar(sample, source)

    def test_illegal_or_missing_original_split_is_rejected(self):
        sample, source = MODULE._synthetic_frames()
        source.loc[source.index[0], "_split_original"] = "future"
        with self.assertRaises(MODULE.ProvenanceError):
            MODULE.build_sidecar(sample, source)
        sample, source = MODULE._synthetic_frames()
        source = source.iloc[:-1].copy()
        with self.assertRaises(MODULE.ProvenanceError):
            MODULE.build_sidecar(sample, source)

    def test_duplicate_ordinals_are_rejected_on_both_surfaces(self):
        sample, source = MODULE._synthetic_frames()
        sample.loc[1, "source_ordinal"] = sample.loc[0, "source_ordinal"]
        with self.assertRaises(MODULE.ProvenanceError):
            MODULE.build_sidecar(sample, source)
        sample, source = MODULE._synthetic_frames()
        source.loc[source.index[1], "_source_ordinal"] = source.loc[
            source.index[0], "_source_ordinal"
        ]
        with self.assertRaises(MODULE.ProvenanceError):
            MODULE.build_sidecar(sample, source)

    def test_row_order_and_raw_trajectory_identity_are_exact(self):
        sample, source = MODULE._synthetic_frames()
        sidecar = MODULE.build_sidecar(sample, source)
        for column in ("check_ins_id", "source_ordinal", "raw_trajectory_id", "SplitTag"):
            self.assertTrue(sample[column].equals(sidecar[column]))

    def test_two_run_witness_is_byte_exact(self):
        witness = MODULE.synthetic_determinism_witness()
        self.assertTrue(witness["pass"])
        self.assertEqual(witness["first"], witness["second"])
        self.assertEqual(witness["rows"], 5)

    def test_existing_output_is_rejected_without_mutation(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "existing"
            output.mkdir()
            args = type(
                "Args",
                (),
                {
                    "sthgcn_root": "missing",
                    "v1_output_root": "missing",
                    "registry": "missing",
                    "output_root": str(output),
                },
            )()
            self.assertEqual(MODULE.main([
                "--sthgcn-root", args.sthgcn_root,
                "--v1-output-root", args.v1_output_root,
                "--registry", args.registry,
                "--output-root", args.output_root,
            ]), 2)
            self.assertEqual(list(output.iterdir()), [])

    def test_gate_set_and_expected_counts_are_exact(self):
        self.assertEqual(len(MODULE.GATE_NAMES), 14)
        self.assertEqual(len(set(MODULE.GATE_NAMES)), 14)
        self.assertEqual(MODULE.EXPECTED_ROWS, {"nyc": 103941, "tky": 405000})


if __name__ == "__main__":
    unittest.main()
