from __future__ import print_function

import ast
import hashlib
import json
from pathlib import Path
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]
REGISTRATION = "af081053d06318ef72473859f462dbfef5ba22e0"
PARENT = "cc1abb0d35626ec89d4b189e3674d29d3288c670"
REGISTRY = (
    ROOT
    / "reproduction"
    / "STHGCN_SAMPLE_MATERIALIZER_V1R3_AUDIT_REPAIR_REGISTRY.json"
)
REGISTRY_RAW_SHA = "37e7377563e987e006a1085e9be559a2d48d218bf828981f810957cc8ceeac3e"
REGISTRY_SEMANTIC_SHA = (
    "7c0691090eee03acdac96cf26c4fc452e6339f3c094198805fb81974874d9fd0"
)
SCOPE = (
    ROOT / "reproduction" / "STHGCN_SAMPLE_MATERIALIZER_V1R3_AUDIT_REPAIR_SCOPE.md"
)
SCOPE_SHA = "04705537c72963664f35678011df45994c11c93940e241b234f66d09066166e1"
V1R2_AUDITOR = (
    ROOT / "reproduction" / "audit_sthgcn_sample_materializer_v1r2_provenance.py"
)
V1R2_MATERIALIZER = (
    ROOT / "reproduction" / "sthgcn_sample_materializer_v1r2_provenance.py"
)
IMPLEMENTATION_ALLOWLIST = {
    "reproduction/audit_sthgcn_sample_materializer_v1r3_provenance.py",
    "reproduction/audit_sthgcn_sample_materializer_v1r3_target_free.py",
    "scripts/run_sthgcn_sample_materializer_v1r3_provenance_audit.sh",
    "scripts/run_sthgcn_sample_materializer_v1r3_target_free.sh",
    "tests/test_sthgcn_sample_materializer_v1r3_audit.py",
    "tests/test_sthgcn_sample_materializer_v1r3_governance.py",
}


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class V1R3GovernanceTest(unittest.TestCase):
    def test_registration_and_frozen_sources_are_exact(self):
        self.assertEqual(sha256(REGISTRY), REGISTRY_RAW_SHA)
        self.assertEqual(sha256(SCOPE), SCOPE_SHA)
        self.assertEqual(
            sha256(V1R2_AUDITOR),
            "4c0439546c9cebe1bfc973724f60526b5bb5c7afa5a84f0b2ee288b86b668e23",
        )
        self.assertEqual(
            sha256(V1R2_MATERIALIZER),
            "2cd6d32cc8742e6e1f3f6e95e57ff262df24c02bcf4f80d778f8d6ba0f37a91c",
        )
        registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
        semantic = json.dumps(
            registry, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
        self.assertEqual(hashlib.sha256(semantic).hexdigest(), REGISTRY_SEMANTIC_SHA)

    def test_registry_authorizes_only_auditor_repair(self):
        registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
        self.assertEqual(registry["parent_commit"], PARENT)
        for key in (
            "documentation",
            "auditor_implementation",
            "synthetic_qualification",
            "server_target_free_qualification",
            "one_preserved_v1r2_audit_execution",
            "failure_or_pass_archive",
        ):
            self.assertTrue(registry["authorization"][key])
        for key in (
            "modify_v1",
            "modify_v1r1",
            "modify_v1r2",
            "regenerate_sidecars",
            "materializer_execution",
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

    def test_v1r2_false_negative_source_is_frozen(self):
        old_audit = V1R2_AUDITOR.read_text(encoding="utf-8")
        producer = V1R2_MATERIALIZER.read_text(encoding="utf-8")
        self.assertIn(
            '"gate_set": tuple(receipt.get("gates", {})) == EXPECTED_GATES',
            old_audit,
        )
        self.assertIn("sort_keys=True", producer)

    def test_new_auditor_import_boundary(self):
        path = (
            ROOT
            / "reproduction"
            / "audit_sthgcn_sample_materializer_v1r3_provenance.py"
        )
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module.split(".")[0])
        self.assertEqual(
            imports,
            {
                "__future__",
                "argparse",
                "hashlib",
                "json",
                "pandas",
                "pathlib",
                "subprocess",
                "sys",
            },
        )

    def test_implementation_is_one_add_only_allowlisted_commit(self):
        head = subprocess.check_output(
            ["git", "-C", str(ROOT), "rev-parse", "HEAD"],
            universal_newlines=True,
        ).strip()
        self.assertEqual(
            subprocess.check_output(
                ["git", "-C", str(ROOT), "rev-parse", "HEAD^"],
                universal_newlines=True,
            ).strip(),
            REGISTRATION,
        )
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

    def test_real_runner_never_invokes_materializer(self):
        text = (
            ROOT
            / "scripts"
            / "run_sthgcn_sample_materializer_v1r3_provenance_audit.sh"
        ).read_text(encoding="utf-8")
        self.assertNotIn("sthgcn_sample_materializer_v1r2_provenance.py", text)
        self.assertIn("audit_sthgcn_sample_materializer_v1r3_provenance.py", text)
        lowered = text.lower()
        for forbidden in ("train_nash", "model_devide", "evaluate.py"):
            self.assertNotIn(forbidden, lowered)


if __name__ == "__main__":
    unittest.main()
