from __future__ import print_function

import ast
import hashlib
import json
from pathlib import Path
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]
REGISTRATION = "14b4de54aef4e1cf6640601b87655c4bb4934314"
PARENT_FAILURE = "515c72a01eb76b859e48f82af24d504a6b7b3ad5"
SUPERSEDED_REGISTRATION = "efdb7490155ca5006592506a4347425880ecb1cd"
REGISTRY = ROOT / "reproduction/MSAHG_ON_STHGCN_CAUSAL_MATERIALIZER_V1R2_REAL_RUNTIME_REGISTRY.json"
AUTHORITY = ROOT / "reproduction/MSAHG_ON_STHGCN_CAUSAL_MATERIALIZER_V1R2_REAL_RUNTIME_AUTHORITY.json"
SCOPE = ROOT / "reproduction/MSAHG_ON_STHGCN_CAUSAL_MATERIALIZER_V1R2_REAL_RUNTIME_SCOPE.md"
AUDITOR = ROOT / "reproduction/audit_msahg_on_sthgcn_causal_materializer_v1r2_real.py"
RUNNER = ROOT / "scripts/run_msahg_on_sthgcn_causal_materializer_v1r2_real.sh"
IMPLEMENTATION_ALLOWLIST = {
    "reproduction/audit_msahg_on_sthgcn_causal_materializer_v1r2_real.py",
    "scripts/run_msahg_on_sthgcn_causal_materializer_v1r2_real.sh",
    "tests/test_msahg_on_sthgcn_causal_materializer_v1r2_real.py",
    "tests/test_msahg_on_sthgcn_causal_materializer_v1r2_real_governance.py",
}


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class RealCausalMaterializerV1R2GovernanceTest(unittest.TestCase):
    def test_authority_material_is_exact_and_dual_bound(self):
        self.assertEqual(sha256(SCOPE), "3f530b07ccd4e755715c18a35857882c857c15bf4e167557dc50bc70b459a6ab")
        self.assertEqual(sha256(REGISTRY), "53efa4342aff9e2f8e6067a472996041961c25826407d3a0a3a7d36f507363ff")
        self.assertEqual(sha256(AUTHORITY), "8eca4f83de89dab57a4f8dc4e52e55913c627b6b7ce82a47e5f1ba9718d88254")
        registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
        authority = json.loads(AUTHORITY.read_text(encoding="utf-8"))
        semantic = hashlib.sha256(
            json.dumps(
                registry,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
            ).encode("utf-8")
        ).hexdigest()
        self.assertEqual(semantic, "d9d546dc6be7162cfd4ca0b17c619594c6cdb08dcfe37c87090b9572523bd500")
        self.assertEqual(authority["registry_sha256"], registry["authorities"]["materializer_implementation_registry_sha256"])
        self.assertEqual(authority["real_runtime_registry_sha256"], sha256(REGISTRY))
        self.assertNotEqual(authority["registry_sha256"], authority["real_runtime_registry_sha256"])

    def test_repair_is_only_dual_binding_and_preserves_failed_v1(self):
        registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
        repair = registry["repair"]
        self.assertEqual(registry["parent_commit"], PARENT_FAILURE)
        self.assertEqual(registry["supersedes_registration_commit"], SUPERSEDED_REGISTRATION)
        self.assertEqual(repair["production_registry_field"], "registry_sha256")
        self.assertEqual(repair["outer_runtime_registry_field"], "real_runtime_registry_sha256")
        for name in (
            "materialization_math_changed",
            "inputs_changed",
            "support_floors_changed",
            "automatic_retry_of_v1",
        ):
            self.assertIs(repair[name], False)
        failure_readme = ROOT / "reproduction/results/msahg_on_sthgcn_causal_materializer_v1r1_real_protocol_failure_2db4b5f/README.md"
        self.assertTrue(failure_readme.is_file())
        self.assertIn("STOP_PRESERVE_NO_RETRY", failure_readme.read_text(encoding="utf-8"))

    def test_v1r2_auditor_reuses_only_independent_v1_auditor(self):
        source = AUDITOR.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(AUDITOR))
        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module)
        self.assertIn("audit_msahg_on_sthgcn_causal_materializer_v1r1_real", imports)
        self.assertNotIn("msahg_on_sthgcn_causal_materializer_v1r1", imports)
        self.assertNotIn("build_material", source)

    def test_runner_has_one_new_execution_and_no_retry_or_score_surface(self):
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
