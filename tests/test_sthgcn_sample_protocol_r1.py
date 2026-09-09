from __future__ import annotations

import hashlib
import tempfile
import unittest
import zipfile
from pathlib import Path

from reproduction.audit_sthgcn_sample_protocol_r1 import (
    REQUIRED_GATES,
    called_names,
    imported_roots,
    reduce_decision,
    sha256_bytes,
    sha256_file,
)


class STHGCNSampleProtocolR1Test(unittest.TestCase):
    def test_gate_set_and_positive_reducer(self):
        gates = {name: True for name in REQUIRED_GATES}
        self.assertEqual(len(gates), 13)
        self.assertEqual(reduce_decision(gates), "PASS")

    def test_reducer_fails_closed(self):
        gates = {name: True for name in REQUIRED_GATES}
        gates["Q7_SPLIT_ASSIGNMENT_AUDIT"] = False
        self.assertEqual(reduce_decision(gates), "PROTOCOL_FAILURE")

        gates = {name: True for name in REQUIRED_GATES}
        gates["EXTRA"] = True
        self.assertEqual(reduce_decision(gates), "PROTOCOL_FAILURE")

        gates = {name: True for name in REQUIRED_GATES[:-1]}
        self.assertEqual(reduce_decision(gates), "PROTOCOL_FAILURE")

    def test_hash_helpers(self):
        payload = b"registered public protocol\n"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "payload"
            path.write_bytes(payload)
            expected = hashlib.sha256(payload).hexdigest()
            self.assertEqual(sha256_bytes(payload), expected)
            self.assertEqual(sha256_file(path), expected)

    def test_production_auditor_has_no_model_runtime(self):
        source = (
            Path(__file__).parents[1]
            / "reproduction"
            / "audit_sthgcn_sample_protocol_r1.py"
        ).read_text(encoding="utf-8")
        self.assertTrue(imported_roots(source).isdisjoint({"torch", "dgl", "model", "gugen"}))
        self.assertTrue(
            called_names(source).isdisjoint(
                {"accuracy_score", "mean_reciprocal_rank", "cross_entropy", "backward"}
            )
        )

    def test_registry_keeps_execution_closed(self):
        import json

        registry = json.loads(
            (
                Path(__file__).parents[1]
                / "reproduction"
                / "MSAHG_ON_STHGCN_PROTOCOL_R1_REGISTRY.json"
            ).read_text(encoding="utf-8")
        )
        authorization = registry["authorization"]
        self.assertTrue(authorization["score_free_data_identity_qualification"])
        self.assertTrue(authorization["raw_data_identity_access"])
        for key in (
            "sample_materialization",
            "scenario_label_materialization",
            "graph_materialization",
            "training",
            "metric_computation",
            "validation_target_evaluation",
            "test_target_evaluation",
            "hyperparameter_tuning",
        ):
            self.assertFalse(authorization[key])


if __name__ == "__main__":
    unittest.main()
