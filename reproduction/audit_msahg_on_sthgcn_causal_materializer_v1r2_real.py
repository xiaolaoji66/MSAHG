#!/usr/bin/env python3
"""V1R2 dual-binding repair for the independent real-data audit."""

from __future__ import print_function

from pathlib import Path
import sys

import audit_msahg_on_sthgcn_causal_materializer_v1r1_real as base


REGISTRATION_COMMIT = "14b4de54aef4e1cf6640601b87655c4bb4934314"
PARENT_FAILURE_ARCHIVE = "515c72a01eb76b859e48f82af24d504a6b7b3ad5"
SUPERSEDED_REGISTRATION = "efdb7490155ca5006592506a4347425880ecb1cd"
REGISTRY_SHA256 = "53efa4342aff9e2f8e6067a472996041961c25826407d3a0a3a7d36f507363ff"
REGISTRY_SEMANTIC_SHA256 = "d9d546dc6be7162cfd4ca0b17c619594c6cdb08dcfe37c87090b9572523bd500"
AUTHORITY_SHA256 = "8eca4f83de89dab57a4f8dc4e52e55913c627b6b7ce82a47e5f1ba9718d88254"
SCOPE_SHA256 = "3f530b07ccd4e755715c18a35857882c857c15bf4e167557dc50bc70b459a6ab"
IMPLEMENTATION_ALLOWLIST = {
    "reproduction/audit_msahg_on_sthgcn_causal_materializer_v1r2_real.py",
    "scripts/run_msahg_on_sthgcn_causal_materializer_v1r2_real.sh",
    "tests/test_msahg_on_sthgcn_causal_materializer_v1r2_real.py",
    "tests/test_msahg_on_sthgcn_causal_materializer_v1r2_real_governance.py",
}


# The reconstruction mathematics stays in the immutable V1 independent auditor.
# Only its repository-lineage constants and authority verifier are superseded.
base.REGISTRATION_COMMIT = REGISTRATION_COMMIT
base.PARENT_RESULT_COMMIT = PARENT_FAILURE_ARCHIVE
base.REGISTRY_SHA256 = REGISTRY_SHA256
base.REGISTRY_SEMANTIC_SHA256 = REGISTRY_SEMANTIC_SHA256
base.AUTHORITY_SHA256 = AUTHORITY_SHA256
base.SCOPE_SHA256 = SCOPE_SHA256
base.IMPLEMENTATION_ALLOWLIST = IMPLEMENTATION_ALLOWLIST


def verify_authorities(args):
    audit_root = Path(__file__).resolve().parents[1]
    registry_path = Path(args.registry).resolve()
    authority_path = Path(args.runtime_authority).resolve()
    scope_path = audit_root / "reproduction/MSAHG_ON_STHGCN_CAUSAL_MATERIALIZER_V1R2_REAL_RUNTIME_SCOPE.md"
    target_free_path = audit_root / "reproduction/results/msahg_on_sthgcn_causal_materializer_v1r1_target_free_1f6fce9/target_free_receipt.json"
    if base.sha256_file(registry_path) != REGISTRY_SHA256:
        raise base.RealAuditError("V1R2 real runtime registry identity mismatch")
    registry = base.load_json(registry_path)
    if base.semantic_sha256(registry) != REGISTRY_SEMANTIC_SHA256:
        raise base.RealAuditError("V1R2 real runtime registry semantic identity mismatch")
    if base.sha256_file(authority_path) != AUTHORITY_SHA256:
        raise base.RealAuditError("V1R2 real runtime authority identity mismatch")
    authority = base.load_json(authority_path)
    if base.sha256_file(scope_path) != SCOPE_SHA256:
        raise base.RealAuditError("V1R2 real runtime scope identity mismatch")
    if base.sha256_file(target_free_path) != base.TARGET_FREE_RECEIPT_SHA256:
        raise base.RealAuditError("target-free result identity mismatch")
    if tuple(registry.get("audit_gates", ())) != base.AUDIT_GATES:
        raise base.RealAuditError("V1R2 real audit gate set mismatch")
    if registry.get("parent_commit") != PARENT_FAILURE_ARCHIVE:
        raise base.RealAuditError("V1R2 parent failure archive mismatch")
    repair = registry.get("repair", {})
    if (
        repair.get("production_registry_field") != "registry_sha256"
        or repair.get("outer_runtime_registry_field") != "real_runtime_registry_sha256"
        or repair.get("materialization_math_changed") is not False
        or repair.get("inputs_changed") is not False
        or repair.get("support_floors_changed") is not False
        or repair.get("automatic_retry_of_v1") is not False
    ):
        raise base.RealAuditError("V1R2 repair boundary mismatch")
    if (
        authority.get("schema") != "msahg.on-sthgcn.causal-materializer-real-runtime.v1"
        or authority.get("implementation_commit") != base.MATERIALIZER_COMMIT
        or authority.get("registry_sha256") != base.MATERIALIZER_REGISTRY_SHA256
        or authority.get("real_runtime_registry_sha256") != REGISTRY_SHA256
        or authority.get("parent_failure_archive") != PARENT_FAILURE_ARCHIVE
        or authority.get("supersedes_registration_commit") != SUPERSEDED_REGISTRATION
        or authority.get("real_materialization_authorized") is not True
        or authority.get("independent_audit_authorized") is not True
        or authority.get("automatic_retry_authorized") is not False
    ):
        raise base.RealAuditError("V1R2 dual registry authorization mismatch")
    for forbidden in (
        "model_implementation_authorized",
        "training_authorized",
        "inference_authorized",
        "loss_authorized",
        "checkpoint_access_authorized",
        "recommendation_metric_computation_authorized",
        "target_evaluation_authorized",
    ):
        if authority.get(forbidden) is not False:
            raise base.RealAuditError("score-bearing authority unexpectedly open: " + forbidden)
    if Path(args.v1_root).resolve() != Path(registry["server_paths"]["v1_input_root"]):
        raise base.RealAuditError("V1 input root is not registered")
    if Path(args.v1r2_root).resolve() != Path(registry["server_paths"]["v1r2_provenance_root"]):
        raise base.RealAuditError("V1R2 provenance root is not registered")
    if Path(args.materialization_root).resolve() != Path(registry["server_paths"]["output_root"]):
        raise base.RealAuditError("V1R2 materialization output root is not registered")
    implementation_head = base.verify_audit_implementation(audit_root)
    materializer_root = base.verify_git_state(
        args.materializer_root, base.MATERIALIZER_COMMIT, "materializer"
    )
    sthgcn_root = base.verify_git_state(
        args.sthgcn_root, base.STHGCN_COMMIT, "STHGCN source"
    )
    materializer_registry = Path(materializer_root) / "reproduction/MSAHG_ON_STHGCN_CAUSAL_MATERIALIZER_V1R1_IMPLEMENTATION_REGISTRY.json"
    if base.sha256_file(materializer_registry) != base.MATERIALIZER_REGISTRY_SHA256:
        raise base.RealAuditError("materializer registry identity mismatch")
    return {
        "registry": registry,
        "authority": authority,
        "audit_implementation_commit": implementation_head,
        "materializer_root": materializer_root,
        "sthgcn_root": sthgcn_root,
    }


base.verify_authorities = verify_authorities
_run_audit_v1 = base.run_audit


def run_audit(args):
    receipt = _run_audit_v1(args)
    receipt["schema"] = "msahg.on-sthgcn.causal-materializer-v1r2-real-audit.v1"
    receipt["authorities"]["production_registry_sha256"] = base.MATERIALIZER_REGISTRY_SHA256
    receipt["authorities"]["real_runtime_registry_sha256"] = REGISTRY_SHA256
    receipt["authorities"]["prior_protocol_failure_archive"] = PARENT_FAILURE_ARCHIVE
    receipt["v1_automatic_retry_performed"] = False
    receipt["repair_boundary"] = "DUAL_REGISTRY_BINDING_ONLY"
    return receipt


base.run_audit = run_audit


def main(argv=None):
    args = base.parse_args(argv)
    output = Path(args.output).resolve()
    if output.exists():
        print("PROTOCOL_FAILURE=audit output already exists", file=sys.stderr)
        return 2
    try:
        receipt = run_audit(args)
    except Exception as error:
        receipt = {
            "schema": "msahg.on-sthgcn.causal-materializer-v1r2-real-audit-failure.v1",
            "decision": "PROTOCOL_FAILURE",
            "reason": str(error),
            "automatic_retry_performed": False,
            "v1_automatic_retry_performed": False,
            "model_executed": False,
            "training_performed": False,
            "recommendation_metrics_computed": False,
        }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(base.canonical_json_bytes(receipt))
    print("V1R2_REAL_AUDIT_RECEIPT={}".format(output))
    print("DECISION={}".format(receipt["decision"]))
    return 0 if receipt["decision"] != "PROTOCOL_FAILURE" else 2


if __name__ == "__main__":
    sys.exit(main())
