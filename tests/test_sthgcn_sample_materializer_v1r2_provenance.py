from __future__ import print_function

import importlib.util
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = (
    ROOT / "reproduction" / "sthgcn_sample_materializer_v1r2_provenance.py"
)
SPEC = importlib.util.spec_from_file_location(
    "sthgcn_sample_materializer_v1r2_provenance", str(MODULE_PATH)
)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class SplitProvenanceV1R2Test(unittest.TestCase):
    def test_replay_directory_handoff_closes_v1r1_failure(self):
        witness = MODULE.replay_directory_witness()
        self.assertEqual(
            set(witness),
            {
                "temporary_parent_exists",
                "replay_child_absent_before_write",
                "replay_child_created_once",
                "preexisting_replay_child_rejected",
                "v1r1_failure_reproduced",
                "repair_delta_exact",
            },
        )
        self.assertTrue(all(witness.values()))

    def test_fresh_child_remains_strict(self):
        v1 = MODULE._load_v1_module()
        sample = MODULE.pd.DataFrame({"x": [1]})
        eligible = {
            "train": sample.copy(),
            "validation": sample.iloc[0:0].copy(),
            "test": sample.iloc[0:0].copy(),
        }
        with tempfile.TemporaryDirectory() as temporary:
            replay = Path(temporary) / "replay"
            MODULE._write_replay(v1, replay, sample, eligible, {"x": {"1": 0}})
            with self.assertRaises(FileExistsError):
                MODULE._write_replay(
                    v1, replay, sample, eligible, {"x": {"1": 0}}
                )

    def test_sidecar_semantics_are_unchanged(self):
        sample, source = MODULE._synthetic_frames()
        sidecar = MODULE.build_sidecar(sample, source)
        self.assertEqual(list(sidecar.columns), MODULE.SIDECAR_COLUMNS)
        self.assertEqual(
            sidecar["OriginalSplitTag"].tolist(),
            ["train", "train", "validation", "validation", "test"],
        )
        self.assertTrue(sidecar["source_ordinal"].is_unique)

    def test_bad_provenance_still_fails_closed(self):
        sample, source = MODULE._synthetic_frames()
        source.loc[source.index[0], "_split_original"] = "future"
        with self.assertRaises(MODULE.ProvenanceError):
            MODULE.build_sidecar(sample, source)
        sample, source = MODULE._synthetic_frames()
        source.loc[source.index[1], "_source_ordinal"] = source.loc[
            source.index[0], "_source_ordinal"
        ]
        with self.assertRaises(MODULE.ProvenanceError):
            MODULE.build_sidecar(sample, source)

    def test_two_run_sidecar_witness_is_byte_exact(self):
        witness = MODULE.synthetic_determinism_witness()
        self.assertTrue(witness["pass"])
        self.assertEqual(witness["first"], witness["second"])

    def test_existing_root_is_rejected_without_mutation(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "existing"
            output.mkdir()
            result = MODULE.main(
                [
                    "--sthgcn-root",
                    "missing",
                    "--v1-output-root",
                    "missing",
                    "--registry",
                    "missing",
                    "--output-root",
                    str(output),
                ]
            )
            self.assertEqual(result, 2)
            self.assertEqual(list(output.iterdir()), [])

    def test_real_gate_set_and_counts_are_exact(self):
        self.assertEqual(len(MODULE.GATE_NAMES), 17)
        self.assertEqual(len(set(MODULE.GATE_NAMES)), 17)
        self.assertEqual(MODULE.EXPECTED_ROWS, {"nyc": 103941, "tky": 405000})


if __name__ == "__main__":
    unittest.main()
