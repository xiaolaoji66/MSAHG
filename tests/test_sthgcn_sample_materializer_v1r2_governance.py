from __future__ import print_function

import ast
import hashlib
import json
from pathlib import Path
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]
REGISTRATION = "fd5aa7739d031c1fa20336084823a63ee56e7acc"
PARENT = "d7d8959eab2256d2e8153485165d11028c258025"
V1_SOURCE = ROOT / "reproduction" / "sthgcn_sample_materializer_r1.py"
V1R1_SOURCE = (
    ROOT / "reproduction" / "sthgcn_sample_materializer_v1r1_provenance.py"
)
V1_SOURCE_SHA = "288daa4ab0de251cbbb0d4d8a1735af1193d42aa0c258757443fd2a154e65f3e"
V1R1_SOURCE_SHA = "606de269b48b6d5394a292956b033b0c43daa86d703360969443ce80e1ddaf5e"
REGISTRY = (
    ROOT
    / "reproduction"
    / "STHGCN_SAMPLE_MATERIALIZER_V1R2_PROVENANCE_REGISTRY.json"
)
REGISTRY_RAW_SHA = "55eb73a7a32b36f3f99570dc802b809c31eaa2caa930bd57bed6b810414ce612"
REGISTRY_SEMANTIC_SHA = (
    "6b647d301dcd6218fe0d974e244f3065008a445b7bfe72b7dad23cb1de052a25"
)
IMPLEMENTATION_ALLOWLIST = {
    "reproduction/audit_sthgcn_sample_materializer_v1r2_provenance.py",
    "reproduction/audit_sthgcn_sample_materializer_v1r2_target_free.py",
    "reproduction/sthgcn_sample_materializer_v1r2_provenance.py",
    "scripts/run_sthgcn_sample_materializer_v1r2_provenance.sh",
    "scripts/run_sthgcn_sample_materializer_v1r2_target_free.sh",
    "tests/test_sthgcn_sample_materializer_v1r2_governance.py",
    "tests/test_sthgcn_sample_materializer_v1r2_provenance.py",
}


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class SplitProvenanceV1R2GovernanceTest(unittest.TestCase):
    def test_frozen_sources_and_registry_identity(self):
        self.assertEqual(sha256(V1_SOURCE), V1_SOURCE_SHA)
        self.assertEqual(sha256(V1R1_SOURCE), V1R1_SOURCE_SHA)
        self.assertEqual(sha256(REGISTRY), REGISTRY_RAW_SHA)
        registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
        semantic = json.dumps(
            registry, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
        self.assertEqual(hashlib.sha256(semantic).hexdigest(), REGISTRY_SEMANTIC_SHA)

    def test_registry_is_exactly_bounded(self):
        registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
        self.assertEqual(registry["parent_commit"], PARENT)
        for key in (
            "implementation",
            "synthetic_qualification",
            "server_target_free_qualification",
            "one_score_free_nyc_tky_execution",
            "failure_or_pass_archive",
        ):
            self.assertTrue(registry["authorization"][key])
        for key in (
            "modify_v1",
            "modify_v1r1",
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

    def test_repair_preserves_strict_fresh_child(self):
        old = V1R1_SOURCE.read_text(encoding="utf-8")
        new_path = (
            ROOT
            / "reproduction"
            / "sthgcn_sample_materializer_v1r2_provenance.py"
        )
        new = new_path.read_text(encoding="utf-8")
        self.assertIn("replay_parent = Path(tempfile.mkdtemp(", old)
        self.assertIn("_write_replay(v1, replay_parent,", old)
        self.assertIn('replay_directory = replay_parent / "replay"', new)
        self.assertIn("v1, replay_directory, sample, eligible, mappings", new)
        self.assertNotIn("exist_ok=True", new)

    def test_production_import_and_runtime_boundary(self):
        path = (
            ROOT
            / "reproduction"
            / "sthgcn_sample_materializer_v1r2_provenance.py"
        )
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
            ["git", "-C", str(ROOT), "rev-parse", "HEAD"],
            universal_newlines=True,
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

    def test_runners_have_no_training_or_metric_command(self):
        for name in (
            "run_sthgcn_sample_materializer_v1r2_target_free.sh",
            "run_sthgcn_sample_materializer_v1r2_provenance.sh",
        ):
            text = (ROOT / "scripts" / name).read_text(encoding="utf-8").lower()
            self.assertNotIn("train_nash", text)
            self.assertNotIn("model_devide", text)
            self.assertNotIn("evaluate.py", text)


if __name__ == "__main__":
    unittest.main()
