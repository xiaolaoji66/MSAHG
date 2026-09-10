from __future__ import print_function

import ast
import hashlib
import json
from pathlib import Path
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]
REGISTRATION = "efdb7490155ca5006592506a4347425880ecb1cd"
PARENT = "d7e2706d82656c718e70df621efbc90e29e74d6f"
REGISTRY = ROOT / "reproduction/MSAHG_ON_STHGCN_CAUSAL_MATERIALIZER_V1R1_REAL_RUNTIME_REGISTRY.json"
AUTHORITY = ROOT / "reproduction/MSAHG_ON_STHGCN_CAUSAL_MATERIALIZER_V1R1_REAL_RUNTIME_AUTHORITY.json"
SCOPE = ROOT / "reproduction/MSAHG_ON_STHGCN_CAUSAL_MATERIALIZER_V1R1_REAL_RUNTIME_SCOPE.md"
AUDITOR = ROOT / "reproduction/audit_msahg_on_sthgcn_causal_materializer_v1r1_real.py"
RUNNER = ROOT / "scripts/run_msahg_on_sthgcn_causal_materializer_v1r1_real.sh"
IMPLEMENTATION_ALLOWLIST = {
    "reproduction/audit_msahg_on_sthgcn_causal_materializer_v1r1_real.py",
    "scripts/run_msahg_on_sthgcn_causal_materializer_v1r1_real.sh",
    "tests/test_msahg_on_sthgcn_causal_materializer_v1r1_real.py",
    "tests/test_msahg_on_sthgcn_causal_materializer_v1r1_real_governance.py",
}


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class RealCausalMaterializerGovernanceTest(unittest.TestCase):
    def test_authority_material_is_exact(self):
        self.assertEqual(sha256(SCOPE), "63e4e1a9d841807398e6a3a68cb28676497dc2b4cf5b8c8cb6098be9cbf371a2")
        self.assertEqual(sha256(REGISTRY), "6e3c4d003355d26efb34b28d9b0c1c1508c5bdd3073f216cad24353c0a37d1a4")
        self.assertEqual(sha256(AUTHORITY), "6b72ebdc704312a8703e6bca8184de1843e27f7372182393adace65728bb2ba0")
        registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
        semantic = hashlib.sha256(
            json.dumps(registry, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        ).hexdigest()
        self.assertEqual(semantic, "9447026f26e4e6ca79dba87eb7d7401b3287a3558d9234ff2dd2deb8ce231591")
        self.assertEqual(registry["parent_commit"], PARENT)

    def test_authority_opens_only_materialization_and_audit(self):
        registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
        authority = json.loads(AUTHORITY.read_text(encoding="utf-8"))
        for name in (
            "real_public_csv_access",
            "real_provenance_sidecar_access",
            "real_materialization",
            "scenario_label_materialization",
            "activity_center_materialization",
            "graph_materialization",
            "support_computation",
            "independent_audit",
        ):
            self.assertTrue(registry["authorization"][name])
        for name in (
            "model_implementation",
            "data_loader_implementation",
            "aps_implementation",
            "training",
            "inference",
            "loss",
            "optimizer",
            "checkpoint_access",
            "recommendation_metric_computation",
            "target_evaluation",
            "threshold_search",
            "posthoc_group_merge",
            "automatic_retry",
        ):
            self.assertFalse(registry["authorization"][name])
        self.assertTrue(authority["real_materialization_authorized"])
        self.assertFalse(authority["automatic_retry_authorized"])

    def test_auditor_is_independent_of_production_builder(self):
        source = AUDITOR.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(AUDITOR))
        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module)
        self.assertNotIn("msahg_on_sthgcn_causal_materializer_v1r1", imports)
        self.assertNotIn("build_material", source)
        self.assertIn("cKDTree", source)

    def test_runner_has_exact_two_materializations_and_one_audit_no_retry(self):
        source = RUNNER.read_text(encoding="utf-8")
        self.assertIn("for dataset in nyc tky", source)
        self.assertEqual(source.count('"$python_bin" "$materializer"'), 1)
        self.assertEqual(source.count('"$python_bin" "$auditor"'), 1)
        self.assertNotIn("retry", source.lower())
        for forbidden in ("train_nash", "model_devide", "evaluate.py", "checkpoint"):
            self.assertNotIn(forbidden, source.lower())

    def test_implementation_is_one_add_only_allowlisted_commit(self):
        head = subprocess.check_output(
            ["git", "-C", str(ROOT), "rev-parse", "HEAD"], universal_newlines=True
        ).strip()
        parent = subprocess.check_output(
            ["git", "-C", str(ROOT), "rev-parse", "HEAD^"], universal_newlines=True
        ).strip()
        self.assertEqual(parent, REGISTRATION)
        changed = subprocess.check_output(
            ["git", "-C", str(ROOT), "diff", "--name-only", REGISTRATION, head], universal_newlines=True
        ).splitlines()
        statuses = subprocess.check_output(
            ["git", "-C", str(ROOT), "diff", "--name-status", REGISTRATION, head], universal_newlines=True
        ).splitlines()
        self.assertEqual(set(changed), IMPLEMENTATION_ALLOWLIST)
        self.assertTrue(all(line.startswith("A\t") for line in statuses))


if __name__ == "__main__":
    unittest.main()
