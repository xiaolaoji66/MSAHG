from __future__ import print_function

import ast
import hashlib
import json
from pathlib import Path
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]
REGISTRATION = "be5efdc1ed56b6628dde82224eaf6df2abfec1cf"
V1_SOURCE = ROOT / "reproduction" / "sthgcn_sample_materializer_r1.py"
V1_SOURCE_SHA = "288daa4ab0de251cbbb0d4d8a1735af1193d42aa0c258757443fd2a154e65f3e"
REGISTRY = ROOT / "reproduction" / "STHGCN_SAMPLE_MATERIALIZER_V1R1_PROVENANCE_REGISTRY.json"
IMPLEMENTATION_ALLOWLIST = {
    "reproduction/audit_sthgcn_sample_materializer_v1r1_provenance.py",
    "reproduction/audit_sthgcn_sample_materializer_v1r1_target_free.py",
    "reproduction/sthgcn_sample_materializer_v1r1_provenance.py",
    "scripts/run_sthgcn_sample_materializer_v1r1_provenance.sh",
    "scripts/run_sthgcn_sample_materializer_v1r1_target_free.sh",
    "tests/test_sthgcn_sample_materializer_v1r1_governance.py",
    "tests/test_sthgcn_sample_materializer_v1r1_provenance.py",
}


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class SplitProvenanceV1R1GovernanceTest(unittest.TestCase):
    def test_v1_source_is_unchanged(self):
        self.assertEqual(sha256(V1_SOURCE), V1_SOURCE_SHA)

    def test_registry_is_execution_bounded(self):
        registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
        self.assertTrue(registry["authorization"]["implementation"])
        self.assertTrue(registry["authorization"]["synthetic_qualification"])
        self.assertTrue(registry["authorization"]["one_score_free_nyc_tky_execution"])
        for key in (
            "modify_v1",
            "modify_upstream",
            "scenario_materialization",
            "graph_materialization",
            "model_implementation",
            "training",
            "inference",
            "loss",
            "checkpoint_access",
            "metric_computation",
            "target_evaluation",
            "automatic_real_retry",
        ):
            self.assertFalse(registry["authorization"][key])

    def test_production_import_boundary(self):
        path = ROOT / "reproduction" / "sthgcn_sample_materializer_v1r1_provenance.py"
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module.split(".")[0])
        self.assertFalse(imports & {"torch", "model_devide", "train_nash"})

    def test_implementation_commit_is_add_only_allowlist(self):
        head = subprocess.check_output(
            ["git", "-C", str(ROOT), "rev-parse", "HEAD"], universal_newlines=True
        ).strip()
        changed = subprocess.check_output(
            ["git", "-C", str(ROOT), "diff", "--name-only", REGISTRATION, head],
            universal_newlines=True,
        ).splitlines()
        statuses = subprocess.check_output(
            ["git", "-C", str(ROOT), "diff", "--name-status", REGISTRATION, head],
            universal_newlines=True,
        ).splitlines()
        self.assertEqual(set(changed), IMPLEMENTATION_ALLOWLIST)
        self.assertTrue(all(line.startswith("A\t") for line in statuses))

    def test_runner_has_no_training_or_metric_command(self):
        for name in (
            "run_sthgcn_sample_materializer_v1r1_target_free.sh",
            "run_sthgcn_sample_materializer_v1r1_provenance.sh",
        ):
            text = (ROOT / "scripts" / name).read_text(encoding="utf-8").lower()
            self.assertNotIn("train_nash", text)
            self.assertNotIn("model_devide", text)
            self.assertNotIn("evaluate.py", text)


if __name__ == "__main__":
    unittest.main()
