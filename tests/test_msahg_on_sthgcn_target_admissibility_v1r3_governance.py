from __future__ import print_function

import hashlib
import json
from pathlib import Path
import subprocess
import unittest

from reproduction import audit_msahg_on_sthgcn_target_admissibility_v1r3 as audit


ROOT = Path(__file__).resolve().parents[1]


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class TargetAdmissibilityV1R3GovernanceTest(unittest.TestCase):
    def test_registration_and_registry_are_exact(self):
        registry_path = ROOT / audit.REGISTRY_RELATIVE
        scope_path = ROOT / audit.SCOPE_RELATIVE
        self.assertEqual(sha256(registry_path), audit.REGISTRY_SHA256)
        self.assertEqual(sha256(scope_path), audit.SCOPE_SHA256)
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
        self.assertEqual(registry["parent_commit"], audit.PARENT_FAILURE)
        self.assertEqual(tuple(registry["audit_gates"]), audit.GATES)
        self.assertEqual(set(registry["implementation_allowlist"]), audit.IMPLEMENTATION_ALLOWLIST)

    def test_implementation_is_direct_add_only_child(self):
        head = subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"]).decode().strip()
        parent = subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD^"]).decode().strip()
        self.assertEqual(parent, audit.REGISTRATION_COMMIT)
        status = subprocess.check_output(
            ["git", "-C", str(ROOT), "diff", "--name-status", parent, head]
        ).decode().splitlines()
        self.assertEqual(set(line.split("\t", 1)[1] for line in status), audit.IMPLEMENTATION_ALLOWLIST)
        self.assertTrue(all(line.startswith("A\t") for line in status))

    def test_score_and_materialization_boundaries_stay_closed(self):
        registry = json.loads((ROOT / audit.REGISTRY_RELATIVE).read_text(encoding="utf-8"))
        auth = registry["authorization"]
        for name in (
            "graph_materialization",
            "scenario_materialization",
            "model_implementation",
            "training",
            "inference",
            "checkpoint_access",
            "recommendation_metric_computation",
            "target_evaluation",
            "automatic_retry",
        ):
            self.assertIs(auth[name], False)

    def test_runner_has_one_audit_and_no_score_surface(self):
        source = (ROOT / "scripts/run_msahg_on_sthgcn_target_admissibility_v1r3.sh").read_text(encoding="utf-8")
        self.assertEqual(source.count("audit_msahg_on_sthgcn_target_admissibility_v1r3.py"), 1)
        for forbidden in ("train.py", "evaluate", "checkpoint", "MRR", "Recall", "NDCG"):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
