#!/usr/bin/env python3
"""Audit preserved V1R2 provenance with order-independent exact gate semantics."""

from __future__ import print_function

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys


REGISTRATION_COMMIT = "af081053d06318ef72473859f462dbfef5ba22e0"
PARENT_COMMIT = "cc1abb0d35626ec89d4b189e3674d29d3288c670"
V1R2_REGISTRATION_COMMIT = "fd5aa7739d031c1fa20336084823a63ee56e7acc"
V1R2_IMPLEMENTATION_COMMIT = "d73f118afa9b51a1418acd5c1fa5eb32b5b0818b"
V1R1_FAILURE_ARCHIVE_COMMIT = "d7d8959eab2256d2e8153485165d11028c258025"
REGISTRY_SHA256 = "37e7377563e987e006a1085e9be559a2d48d218bf828981f810957cc8ceeac3e"
SCOPE_SHA256 = "04705537c72963664f35678011df45994c11c93940e241b234f66d09066166e1"
V1R2_AUDITOR_SHA256 = "4c0439546c9cebe1bfc973724f60526b5bb5c7afa5a84f0b2ee288b86b668e23"
V1R2_MATERIALIZER_SHA256 = "2cd6d32cc8742e6e1f3f6e95e57ff262df24c02bcf4f80d778f8d6ba0f37a91c"
V1R2_FAILED_AUDIT_SHA256 = "2ac3e73a87035d951036f50b3e44c87452dc63cc913d07c6de23c67f8f870349"
EXPECTED_ROWS = {"nyc": 103941, "tky": 405000}
EXPECTED_V1_SAMPLE_SHA256 = {
    "nyc": "4923e232f04e6a1d28de73a2545240e021066087706a824bcb01f6b0cf9f8f65",
    "tky": "b50fbd66c09463f1e2258a3fda33f3d4a11cd33cb2c20e1ede8873dab7cb47b0",
}
EXPECTED_FROZEN_FILES = {
    "provenance_summary.json": "db8f952b5f6b0e2a88554997df59773144f04f23b0161a63b7aadb71e9b44a98",
    "nyc/provenance_receipt.json": "e67b5bf7f373ae9b5fb859981ddc116694d99f72726292e707c6ff7decf81f22",
    "nyc/record_split_provenance.csv": "57c0b434918d5cd1bb421f2654c430a572e3e70f6c587ad398e078c8fd0f93d3",
    "tky/provenance_receipt.json": "1cc91cf9e30834eb43f39e34a1d402a358264788e146579466816dbc29b51a7f",
    "tky/record_split_provenance.csv": "5f287bb802943a3e8f99ff307acf2f8c47f5c4e46eab62fd62ff00c7a0de211d",
}
EXPECTED_GATES = (
    "R0_AUTHORITY",
    "R1_FRESH_OUTPUT",
    "R2_V1_INPUT_IMMUTABLE",
    "R3_EXACT_V1_REPLAY",
    "R4_ROW_BIJECTION",
    "R5_LEGAL_ORIGINAL_SPLIT",
    "R6_VISIBLE_SPLIT_IMPLICATION",
    "R7_IDENTITY_STABILITY",
    "R8_COUNT_CONSERVATION",
    "R9_TWO_RUN_DETERMINISM",
    "R10_SOURCE_IMMUTABLE",
    "R11_NO_DOWNSTREAM_MATERIAL",
    "R12_SCORE_FREE",
    "R13_FAIL_CLOSED",
    "R14_REPLAY_CHILD_DIRECTORY_HANDOFF",
    "R15_V1R1_FAILURE_REPRODUCED",
    "R16_REPAIR_DELTA_EXACT",
)
SIDECAR_COLUMNS = [
    "check_ins_id",
    "source_ordinal",
    "raw_trajectory_id",
    "SplitTag",
    "OriginalSplitTag",
]


class AuditError(RuntimeError):
    pass


class DuplicateKeyError(AuditError):
    pass


def sha256_file(path):
    digest = hashlib.sha256()
    with open(str(path), "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _reject_duplicate_keys(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise DuplicateKeyError("duplicate JSON object key: " + str(key))
        value[key] = item
    return value


def load_json_exact(path):
    with open(str(path), "r", encoding="utf-8") as handle:
        return json.load(handle, object_pairs_hook=_reject_duplicate_keys)


def loads_json_exact(text):
    return json.loads(text, object_pairs_hook=_reject_duplicate_keys)


def exact_gate_map(gates, expected=EXPECTED_GATES):
    if not isinstance(gates, dict):
        return False
    keys = tuple(gates)
    return (
        len(keys) == len(expected)
        and set(keys) == set(expected)
        and all(value is True for value in gates.values())
    )


def old_order_sensitive_gate_predicate(gates, expected=EXPECTED_GATES):
    return isinstance(gates, dict) and tuple(gates) == tuple(expected)


def _git(root, *args):
    return subprocess.check_output(
        ["git", "-C", str(root)] + list(args), stderr=subprocess.STDOUT
    ).decode("utf-8").strip()


def _load_pandas():
    import pandas as pd

    return pd


def verify_registry(registry_path):
    path = Path(registry_path).resolve()
    if sha256_file(path) != REGISTRY_SHA256:
        raise AuditError("V1R3 registry identity mismatch")
    registry = load_json_exact(path)
    root = Path(__file__).resolve().parents[1]
    scope = root / registry["authorities"]["scope_path"]
    if sha256_file(scope) != SCOPE_SHA256:
        raise AuditError("V1R3 scope identity mismatch")
    if registry.get("parent_commit") != PARENT_COMMIT:
        raise AuditError("V1R3 parent identity mismatch")
    if tuple(registry.get("expected_real_gate_names", ())) != EXPECTED_GATES:
        raise AuditError("V1R3 expected gate registry mismatch")
    if registry.get("frozen_files") != EXPECTED_FROZEN_FILES:
        raise AuditError("V1R3 frozen output registry mismatch")
    if registry.get("v1_sample_sha256") != EXPECTED_V1_SAMPLE_SHA256:
        raise AuditError("V1R3 V1 sample registry mismatch")
    return registry


def verify_reproduction_authority():
    root = Path(__file__).resolve().parents[1]
    head = _git(root, "rev-parse", "HEAD")
    if _git(root, "status", "--porcelain=v1", "--untracked-files=all"):
        raise AuditError("V1R3 worktree is not clean")
    if _git(root, "rev-parse", "HEAD^") != REGISTRATION_COMMIT:
        raise AuditError("V1R3 implementation must directly follow registration")
    if _git(root, "rev-parse", REGISTRATION_COMMIT + "^") != PARENT_COMMIT:
        raise AuditError("V1R3 registration parent mismatch")
    return {"root": root, "implementation_commit": head}


def _checksum_manifest_ok(directory):
    manifest = directory / "SHA256SUMS"
    if not manifest.is_file():
        return False
    observed = set()
    for line in manifest.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        parts = line.split("  ", 1)
        if len(parts) != 2 or parts[1] in observed:
            return False
        expected, relative = parts
        observed.add(relative)
        path = directory / relative
        if not path.is_file() or sha256_file(path) != expected:
            return False
    return True


def frozen_input_hashes(output_root, v1_root):
    hashes = {
        "v1r2/" + relative: sha256_file(output_root / relative)
        for relative in sorted(EXPECTED_FROZEN_FILES)
    }
    hashes.update(
        {
            "v1/{}/sample.csv".format(dataset): sha256_file(
                v1_root / dataset / "sample.csv"
            )
            for dataset in ("nyc", "tky")
        }
    )
    return hashes


def verify_frozen_hashes(output_root, v1_root):
    observed = frozen_input_hashes(output_root, v1_root)
    expected = {
        "v1r2/" + relative: value
        for relative, value in EXPECTED_FROZEN_FILES.items()
    }
    expected.update(
        {
            "v1/{}/sample.csv".format(dataset): value
            for dataset, value in EXPECTED_V1_SAMPLE_SHA256.items()
        }
    )
    if observed != expected:
        raise AuditError("preserved V1R2 or V1 input identity mismatch")
    return observed


def audit_dataset(root, v1_root, dataset, pd):
    directory = root / dataset
    expected_names = {
        "record_split_provenance.csv",
        "provenance_receipt.json",
        "SHA256SUMS",
    }
    actual_names = (
        set(path.name for path in directory.iterdir())
        if directory.is_dir()
        else set()
    )
    sidecar = pd.read_csv(str(directory / "record_split_provenance.csv"))
    sample = pd.read_csv(str(v1_root / dataset / "sample.csv"))
    receipt = load_json_exact(directory / "provenance_receipt.json")

    visible = sidecar["SplitTag"].ne("ignore")
    identity = ["check_ins_id", "source_ordinal", "raw_trajectory_id", "SplitTag"]
    identity_equal = all(
        sample[column]
        .reset_index(drop=True)
        .equals(sidecar[column].reset_index(drop=True))
        for column in identity
    )
    no_downstream = all(
        receipt.get(name) is False
        for name in (
            "scenario_labels_materialized",
            "activity_center_materialized",
            "graph_materialized",
            "model_executed",
            "training_performed",
            "inference_performed",
            "loss_computed",
            "checkpoint_accessed",
            "recommendation_metrics_computed",
            "target_evaluation_performed",
        )
    )
    repair = receipt.get("replay_directory_repair", {})
    gates = receipt.get("gates")
    checks = {
        "receipt_schema": receipt.get("schema")
        == "msahg.sthgcn-sample-materializer-v1r2-provenance-receipt.v1",
        "file_allowlist": actual_names == expected_names,
        "checksums": _checksum_manifest_ok(directory),
        "decision": receipt.get("decision") == "PASS",
        "gate_name_set": exact_gate_map(gates),
        "gate_values_exact_boolean_true": isinstance(gates, dict)
        and all(value is True for value in gates.values()),
        "old_order_sensitive_failure_reproduced": not old_order_sensitive_gate_predicate(
            gates
        ),
        "columns": list(sidecar.columns) == SIDECAR_COLUMNS,
        "row_count": len(sidecar) == len(sample) == EXPECTED_ROWS[dataset],
        "unique_ordinal": bool(sidecar["source_ordinal"].is_unique),
        "unique_identity_pair": (
            sidecar[["check_ins_id", "source_ordinal"]]
            .drop_duplicates()
            .shape[0]
            == len(sidecar)
        ),
        "original_split_complete": (
            not bool(sidecar["OriginalSplitTag"].isna().any())
            and set(sidecar["OriginalSplitTag"].unique())
            <= {"train", "validation", "test"}
        ),
        "visible_split_implication": bool(
            sidecar.loc[visible, "SplitTag"].eq(
                sidecar.loc[visible, "OriginalSplitTag"]
            ).all()
        ),
        "identity_equal": identity_equal,
        "sidecar_sha": receipt.get("sidecar_sha256")
        == sha256_file(directory / "record_split_provenance.csv"),
        "v1_sample_sha": receipt.get("v1_input_sha256", {}).get("sample.csv")
        == EXPECTED_V1_SAMPLE_SHA256[dataset],
        "v1_replay_equals_input": receipt.get("v1_replay_sha256")
        == receipt.get("v1_input_sha256"),
        "repair_witness": (
            repair.get("temporary_parent_exists") is True
            and repair.get("replay_child_absent_before_write") is True
            and repair.get("replay_child_created_once") is True
            and repair.get("preexisting_replay_child_rejected") is True
            and repair.get("v1r1_failure_reproduced") is True
            and repair.get("repair_delta_exact") is True
        ),
        "v1r2_authority": (
            receipt.get("authorities", {}).get("registration_commit")
            == V1R2_REGISTRATION_COMMIT
            and receipt.get("authorities", {}).get("implementation_commit")
            == V1R2_IMPLEMENTATION_COMMIT
        ),
        "failure_superseded": receipt.get(
            "supersedes_v1r1_failure_archive_commit"
        )
        == V1R1_FAILURE_ARCHIVE_COMMIT,
        "no_downstream": no_downstream,
    }
    return {
        "dataset": dataset,
        "checks": checks,
        "pass": all(checks.values()),
        "rows": int(len(sidecar)),
        "observed_gate_order": list(gates) if isinstance(gates, dict) else None,
        "original_split_counts": {
            str(key): int(value)
            for key, value in sidecar["OriginalSplitTag"]
            .value_counts(sort=False)
            .sort_index()
            .items()
        },
    }


def run_audit(registry_path, output_root, v1_root):
    registry = verify_registry(registry_path)
    runtime = verify_reproduction_authority()
    pd = _load_pandas()
    before = verify_frozen_hashes(output_root, v1_root)

    results = [
        audit_dataset(output_root, v1_root, dataset, pd)
        for dataset in ("nyc", "tky")
    ]
    root_names = set(path.name for path in output_root.iterdir())
    root_ok = root_names == {
        "nyc",
        "tky",
        "provenance_summary.json",
        "SHA256SUMS",
    }
    summary_ok = _checksum_manifest_ok(output_root)
    summary = load_json_exact(output_root / "provenance_summary.json")
    summary_identity = (
        summary.get("schema")
        == "msahg.sthgcn-sample-materializer-v1r2-provenance-summary.v1"
        and summary.get("decision") == "PASS"
        and summary.get("registration_commit") == V1R2_REGISTRATION_COMMIT
        and summary.get("implementation_commit") == V1R2_IMPLEMENTATION_COMMIT
        and summary.get("supersedes_v1r1_failure_archive_commit")
        == V1R1_FAILURE_ARCHIVE_COMMIT
        and summary.get("replay_directory_repair", {}).get("repair_delta_exact")
        is True
    )
    after = verify_frozen_hashes(output_root, v1_root)
    input_immutable = before == after
    passed = (
        root_ok
        and summary_ok
        and summary_identity
        and input_immutable
        and all(item["pass"] for item in results)
    )
    return {
        "schema": "msahg.sthgcn-sample-materializer-v1r3-independent-audit.v1",
        "decision": "PASS" if passed else "FAIL",
        "reason_codes": [] if passed else ["ONE_OR_MORE_AUDIT_CHECKS_FAILED"],
        "authorities": {
            "registration_commit": REGISTRATION_COMMIT,
            "implementation_commit": runtime["implementation_commit"],
            "parent_commit": PARENT_COMMIT,
            "registry_sha256": REGISTRY_SHA256,
            "scope_sha256": SCOPE_SHA256,
            "v1r2_registration_commit": V1R2_REGISTRATION_COMMIT,
            "v1r2_implementation_commit": V1R2_IMPLEMENTATION_COMMIT,
            "v1r2_auditor_sha256": V1R2_AUDITOR_SHA256,
            "v1r2_materializer_sha256": V1R2_MATERIALIZER_SHA256,
            "v1r2_failed_audit_sha256": V1R2_FAILED_AUDIT_SHA256,
        },
        "root_file_allowlist": root_ok,
        "root_checksums": summary_ok,
        "summary_identity": summary_identity,
        "input_hashes_before": before,
        "input_hashes_after": after,
        "input_immutable": input_immutable,
        "datasets": {item["dataset"]: item for item in results},
        "repair_semantics": {
            "gate_order_ignored": True,
            "exact_gate_name_set_required": True,
            "every_gate_value_exact_boolean_true_required": True,
            "duplicate_json_keys_rejected": True,
        },
        "real_audit_execution_count_for_version": 1,
        "automatic_retry_performed": False,
        "materializer_executed": False,
        "sidecars_regenerated": False,
        "scenario_labels_materialized": False,
        "activity_center_materialized": False,
        "graph_materialized": False,
        "model_executed": False,
        "training_performed": False,
        "inference_performed": False,
        "loss_computed": False,
        "checkpoint_accessed": False,
        "recommendation_metrics_computed": False,
        "target_evaluation_performed": False,
        "interpretation": "PASS qualifies the preserved V1R2 original-split provenance only; it is not graph, model, or predictive evidence.",
        "registry_status": registry["status"],
        "runtime": {"python": sys.version.split()[0], "pandas": pd.__version__},
    }


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", required=True)
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--v1-output-root", required=True)
    parser.add_argument("--audit-output", required=True)
    return parser.parse_args(argv)


def _write_json(path, value):
    with open(str(path), "w", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, indent=2, sort_keys=True, ensure_ascii=False)
        handle.write("\n")


def main(argv=None):
    args = parse_args(argv)
    audit_output = Path(args.audit_output).resolve()
    if audit_output.exists():
        print("PROTOCOL_FAILURE=audit output already exists", file=sys.stderr)
        return 2
    try:
        receipt = run_audit(
            args.registry,
            Path(args.output_root).resolve(),
            Path(args.v1_output_root).resolve(),
        )
    except Exception as error:
        receipt = {
            "schema": "msahg.sthgcn-sample-materializer-v1r3-independent-audit-failure.v1",
            "decision": "FAIL",
            "reason_codes": ["AUDIT_EXCEPTION"],
            "reason": str(error),
            "real_audit_execution_count_for_version": 1,
            "automatic_retry_performed": False,
            "materializer_executed": False,
            "sidecars_regenerated": False,
            "graph_materialized": False,
            "model_executed": False,
            "training_performed": False,
            "recommendation_metrics_computed": False,
            "target_evaluation_performed": False,
        }
    audit_output.parent.mkdir(parents=True, exist_ok=True)
    _write_json(audit_output, receipt)
    print("INDEPENDENT_AUDIT={}".format(receipt["decision"]))
    print("AUDIT_OUTPUT={}".format(audit_output))
    return 0 if receipt["decision"] == "PASS" else 2


if __name__ == "__main__":
    sys.exit(main())
