from __future__ import print_function

import json
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "reproduction"))

import msahg_on_sthgcn_causal_materializer_v1r1 as production
try:
    import audit_msahg_on_sthgcn_causal_materializer_v1r2_real as auditor
except ModuleNotFoundError:
    auditor = None


AUTHORITY = ROOT / "reproduction/MSAHG_ON_STHGCN_CAUSAL_MATERIALIZER_V1R2_REAL_RUNTIME_AUTHORITY.json"
AUTHORITY_SHA = "8eca4f83de89dab57a4f8dc4e52e55913c627b6b7ce82a47e5f1ba9718d88254"
MATERIALIZER_COMMIT = "1f6fce9505eae929a8f131fc67556e513c4d1100"
PRODUCTION_REGISTRY_SHA = "f9ff7c5ffe4affc4ccf4ff0d44dd9089274b4e416437f34219fa6b5c33ddc1ba"
REAL_RUNTIME_REGISTRY_SHA = "53efa4342aff9e2f8e6067a472996041961c25826407d3a0a3a7d36f507363ff"


class RealCausalMaterializerV1R2Test(unittest.TestCase):
    def test_corrected_authority_is_accepted_by_immutable_production_verifier(self):
        observed = production.verify_runtime_authority(
            AUTHORITY, AUTHORITY_SHA, MATERIALIZER_COMMIT
        )
        self.assertEqual(observed["registry_sha256"], PRODUCTION_REGISTRY_SHA)
        self.assertEqual(
            observed["real_runtime_registry_sha256"], REAL_RUNTIME_REGISTRY_SHA
        )

    def test_overloaded_outer_registry_identity_is_rejected_by_production(self):
        payload = json.loads(AUTHORITY.read_text(encoding="utf-8"))
        payload["registry_sha256"] = payload["real_runtime_registry_sha256"]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "invalid.json"
            path.write_text(
                json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
            )
            invalid_sha = production.sha256_file(path)
            with self.assertRaisesRegex(
                production.CausalMaterializerError,
                "real materialization is not authorized",
            ):
                production.verify_runtime_authority(
                    path, invalid_sha, MATERIALIZER_COMMIT
                )

    @unittest.skipIf(auditor is None, "NumPy/pandas/SciPy runtime is unavailable")
    def test_v1r2_wrapper_freezes_v1_reconstruction_math(self):
        self.assertIs(auditor.base.run_audit, auditor.run_audit)
        self.assertEqual(
            auditor.base.MATERIALIZER_REGISTRY_SHA256, PRODUCTION_REGISTRY_SHA
        )
        matrix = auditor.base.matrix(
            (2, 3), [(0, 2), (0, 1), (1, 0)], "float64", True
        )
        self.assertEqual(matrix["coordinates"], [(0, 1), (0, 2), (1, 0)])
        self.assertEqual(matrix["values"].tolist(), [0.5, 0.5, 1.0])

    def test_repair_opens_no_score_bearing_surface(self):
        authority = json.loads(AUTHORITY.read_text(encoding="utf-8"))
        for name in (
            "model_implementation_authorized",
            "training_authorized",
            "inference_authorized",
            "loss_authorized",
            "checkpoint_access_authorized",
            "recommendation_metric_computation_authorized",
            "target_evaluation_authorized",
            "automatic_retry_authorized",
        ):
            self.assertIs(authority[name], False)


if __name__ == "__main__":
    unittest.main()
