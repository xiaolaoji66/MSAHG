from __future__ import print_function

import ast
import hashlib
import json
from pathlib import Path
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]
REGISTRATION = "4dd32f64440687c5f65c659b7e28b0b83b90d713"
PARENT_RESULT = "9bb6248b7cd8730b9c05676926f213afe3e476fc"
REGISTRY = (
    ROOT
    / "reproduction"
    / "MSAHG_ON_STHGCN_CAUSAL_MATERIALIZER_V1R1_IMPLEMENTATION_REGISTRY.json"
)
REGISTRY_RAW_SHA = "f9ff7c5ffe4affc4ccf4ff0d44dd9089274b4e416437f34219fa6b5c33ddc1ba"
REGISTRY_SEMANTIC_SHA = "0ad117c6165a8d3e2f62352fdc4698579e1f3b7f9c58db5e93c5d957ee7ed391"
SCOPE = (
    ROOT
    / "reproduction"
    / "MSAHG_ON_STHGCN_CAUSAL_MATERIALIZER_V1R1_IMPLEMENTATION_SCOPE.md"
)
SCOPE_SHA = "1192d00dc626f6a4eb4ab1c94807bb227c4bb68efba9948abb94959801a3c755"
PRODUCTION = ROOT / "reproduction" / "msahg_on_sthgcn_causal_materializer_v1r1.py"
RUNNER = ROOT / "scripts" / "run_msahg_on_sthgcn_causal_materializer_v1r1_target_free.sh"
IMPLEMENTATION_ALLOWLIST = {
    "reproduction/audit_msahg_on_sthgcn_causal_materializer_v1r1_target_free.py",
    "reproduction/msahg_on_sthgcn_causal_materializer_v1r1.py",
    "scripts/run_msahg_on_sthgcn_causal_materializer_v1r1_target_free.sh",
    "tests/test_msahg_on_sthgcn_causal_materializer_v1r1.py",
    "tests/test_msahg_on_sthgcn_causal_materializer_v1r1_governance.py",
}


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def imports(path):
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module.split(".")[0])
    return names


class CausalMaterializerV1R1GovernanceTest(unittest.TestCase):
    def test_registry_scope_and_semantic_identity_are_exact(self):
        self.assertEqual(sha256(REGISTRY), REGISTRY_RAW_SHA)
        self.assertEqual(sha256(SCOPE), SCOPE_SHA)
        registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
        semantic = json.dumps(
            registry, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
        self.assertEqual(hashlib.sha256(semantic).hexdigest(), REGISTRY_SEMANTIC_SHA)
        self.assertEqual(registry["parent_commit"], PARENT_RESULT)
        self.assertEqual(registry["format"]["variant"], "MARGINAL_AXIS_V1")

    def test_authority_is_target_free_and_real_execution_closed(self):
        registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
        for name in (
            "documentation",
            "materializer_implementation",
            "synthetic_tests",
            "server_target_free_qualification",
            "target_free_receipt_archive",
        ):
            self.assertTrue(registry["authorization"][name])
        for name in (
            "real_public_csv_access",
            "real_provenance_sidecar_access",
            "real_materialization_authorized",
            "scenario_label_materialization",
            "activity_center_materialization",
            "graph_materialization",
            "support_adjudication",
            "data_loader_implementation",
            "aps_implementation",
            "model_implementation",
            "training",
            "inference",
            "loss",
            "optimizer",
            "checkpoint_access",
            "metric_computation",
            "target_evaluation",
            "automatic_retry",
        ):
            self.assertFalse(registry["authorization"][name])

    def test_production_import_boundary_excludes_model_and_data_stacks(self):
        self.assertEqual(
            imports(PRODUCTION),
            {
                "__future__",
                "argparse",
                "csv",
                "datetime",
                "hashlib",
                "io",
                "json",
                "math",
                "pathlib",
                "struct",
                "subprocess",
                "sys",
                "zipfile",
            },
        )
        source = PRODUCTION.read_text(encoding="utf-8").lower()
        for forbidden in (
            "import torch",
            "import numpy",
            "import pandas",
            "import scipy",
        ):
            self.assertNotIn(forbidden, source)

    def test_real_cli_requires_a_later_positive_runtime_authority(self):
        source = PRODUCTION.read_text(encoding="utf-8")
        self.assertIn("--runtime-authority", source)
        self.assertIn("--runtime-authority-sha256", source)
        self.assertIn('authority.get("real_materialization_authorized") is not True', source)
        registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
        self.assertFalse(registry["authorization"]["real_materialization_authorized"])

    def test_target_free_runner_has_no_real_or_score_bearing_action(self):
        source = RUNNER.read_text(encoding="utf-8").lower()
        self.assertIn("audit_msahg_on_sthgcn_causal_materializer_v1r1_target_free.py", source)
        for forbidden in (
            "sample.csv",
            "record_split_provenance.csv",
            "label_encoding.json",
            "--runtime-authority",
            "train_nash",
            "model_devide",
            "evaluate.py",
        ):
            self.assertNotIn(forbidden, source)

    def test_implementation_is_one_add_only_allowlisted_commit(self):
        head = subprocess.check_output(
            ["git", "-C", str(ROOT), "rev-parse", "HEAD"],
            universal_newlines=True,
        ).strip()
        parent = subprocess.check_output(
            ["git", "-C", str(ROOT), "rev-parse", "HEAD^"],
            universal_newlines=True,
        ).strip()
        self.assertEqual(parent, REGISTRATION)
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


if __name__ == "__main__":
    unittest.main()
