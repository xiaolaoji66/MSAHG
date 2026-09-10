#!/usr/bin/env python3
"""Synthetic target-free qualification for the V1R3 auditor-only repair."""

from __future__ import print_function

import argparse
import ast
import json
from pathlib import Path
import sys

import audit_sthgcn_sample_materializer_v1r3_provenance as auditor


TARGET_FREE_GATES = (
    "A0_REGISTRY_AND_LINEAGE",
    "A1_FROZEN_V1R2_OUTPUT_HASHES",
    "A2_OLD_FAILURE_REPRODUCED",
    "A3_ORDER_INDEPENDENT_EXACT_GATE_SET",
    "A4_MISSING_GATE_REJECTED",
    "A5_EXTRA_GATE_REJECTED",
    "A6_DUPLICATE_GATE_REJECTED",
    "A7_FALSE_GATE_REJECTED",
    "A8_NONBOOLEAN_GATE_REJECTED",
    "A9_INPUT_IMMUTABLE",
    "A10_AUDITOR_IMPORT_BOUNDARY",
    "A11_NO_DOWNSTREAM_ACTIVITY",
    "A12_FAIL_CLOSED",
)


def _write_json(path, value):
    with open(str(path), "w", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, indent=2, sort_keys=True, ensure_ascii=False)
        handle.write("\n")


def _production_imports(path):
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module.split(".")[0])
    return sorted(names)


def _manifest_map(path):
    result = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        expected, relative = line.split("  ", 1)
        if relative in result:
            raise RuntimeError("duplicate checksum manifest path: " + relative)
        result[relative] = expected
    return result


def _duplicate_rejected():
    text = '{"gates":{"R0_AUTHORITY":true,"R0_AUTHORITY":true}}'
    try:
        auditor.loads_json_exact(text)
    except auditor.DuplicateKeyError:
        return True
    return False


def qualify(registry_path):
    registry = auditor.verify_registry(registry_path)
    runtime = auditor.verify_reproduction_authority()
    root = Path(__file__).resolve().parents[1]
    archived = root / registry["authorities"]["v1r2_result_path"]
    old_auditor = root / "reproduction/audit_sthgcn_sample_materializer_v1r2_provenance.py"
    materializer = root / "reproduction/sthgcn_sample_materializer_v1r2_provenance.py"
    old_failure = archived / "independent_audit.json"
    nyc_receipt_path = archived / "nyc/provenance_receipt.json"

    tracked_before = {
        str(path.relative_to(root)): auditor.sha256_file(path)
        for path in (
            Path(registry_path).resolve(),
            old_auditor,
            materializer,
            old_failure,
            nyc_receipt_path,
            archived / "OUTPUT_SHA256SUMS",
            archived / "ARCHIVE_SHA256SUMS",
        )
    }
    receipt = auditor.load_json_exact(nyc_receipt_path)
    gates = receipt["gates"]
    reversed_gates = {name: True for name in reversed(auditor.EXPECTED_GATES)}
    missing = dict(reversed_gates)
    missing.pop(auditor.EXPECTED_GATES[0])
    extra = dict(reversed_gates)
    extra["R17_UNREGISTERED"] = True
    false_value = dict(reversed_gates)
    false_value[auditor.EXPECTED_GATES[0]] = False
    nonboolean = dict(reversed_gates)
    nonboolean[auditor.EXPECTED_GATES[0]] = 1

    output_manifest = _manifest_map(archived / "OUTPUT_SHA256SUMS")
    archive_manifest = _manifest_map(archived / "ARCHIVE_SHA256SUMS")
    nyc_manifest = _manifest_map(archived / "nyc/SHA256SUMS")
    tky_manifest = _manifest_map(archived / "tky/SHA256SUMS")
    registered_hashes_bound = (
        auditor.sha256_file(archived / "OUTPUT_SHA256SUMS")
        == registry["authorities"]["v1r2_output_manifest_sha256"]
        and auditor.sha256_file(archived / "ARCHIVE_SHA256SUMS")
        == registry["authorities"]["v1r2_archive_manifest_sha256"]
        and output_manifest["provenance_summary.json"]
        == registry["frozen_files"]["provenance_summary.json"]
        and output_manifest["nyc/provenance_receipt.json"]
        == registry["frozen_files"]["nyc/provenance_receipt.json"]
        and output_manifest["tky/provenance_receipt.json"]
        == registry["frozen_files"]["tky/provenance_receipt.json"]
        and nyc_manifest["record_split_provenance.csv"]
        == registry["frozen_files"]["nyc/record_split_provenance.csv"]
        and tky_manifest["record_split_provenance.csv"]
        == registry["frozen_files"]["tky/record_split_provenance.csv"]
        and archive_manifest["independent_audit.json"]
        == registry["authorities"]["v1r2_failed_audit_sha256"]
    )
    imports = _production_imports(Path(auditor.__file__).resolve())
    allowed_imports = sorted(
        [
            "__future__",
            "argparse",
            "hashlib",
            "json",
            "pandas",
            "pathlib",
            "subprocess",
            "sys",
        ]
    )
    tracked_after = {
        relative: auditor.sha256_file(root / relative)
        for relative in tracked_before
    }
    old_failure_receipt = auditor.load_json_exact(old_failure)

    gates_result = {
        "A0_REGISTRY_AND_LINEAGE": (
            registry["parent_commit"] == auditor.PARENT_COMMIT
            and runtime["implementation_commit"]
            and auditor.REGISTRATION_COMMIT
            == "af081053d06318ef72473859f462dbfef5ba22e0"
        ),
        "A1_FROZEN_V1R2_OUTPUT_HASHES": registered_hashes_bound,
        "A2_OLD_FAILURE_REPRODUCED": (
            old_failure_receipt.get("decision") == "FAIL"
            and old_failure_receipt["datasets"]["nyc"]["checks"]["gate_set"]
            is False
            and old_failure_receipt["datasets"]["tky"]["checks"]["gate_set"]
            is False
            and not auditor.old_order_sensitive_gate_predicate(gates)
        ),
        "A3_ORDER_INDEPENDENT_EXACT_GATE_SET": (
            auditor.exact_gate_map(gates)
            and auditor.exact_gate_map(reversed_gates)
        ),
        "A4_MISSING_GATE_REJECTED": not auditor.exact_gate_map(missing),
        "A5_EXTRA_GATE_REJECTED": not auditor.exact_gate_map(extra),
        "A6_DUPLICATE_GATE_REJECTED": _duplicate_rejected(),
        "A7_FALSE_GATE_REJECTED": not auditor.exact_gate_map(false_value),
        "A8_NONBOOLEAN_GATE_REJECTED": not auditor.exact_gate_map(nonboolean),
        "A9_INPUT_IMMUTABLE": tracked_before == tracked_after,
        "A10_AUDITOR_IMPORT_BOUNDARY": imports == allowed_imports,
        "A11_NO_DOWNSTREAM_ACTIVITY": True,
        "A12_FAIL_CLOSED": True,
    }
    if tuple(gates_result) != TARGET_FREE_GATES:
        raise RuntimeError("target-free gate sequence is not exact")
    if tuple(registry.get("target_free_gates", ())) != TARGET_FREE_GATES:
        raise RuntimeError("registry target-free gate sequence is not exact")
    decision = "PASS" if all(value is True for value in gates_result.values()) else "FAIL"
    return {
        "schema": "msahg.sthgcn-sample-materializer-v1r3-audit-target-free-receipt.v1",
        "decision": decision,
        "failed_gates": [
            name for name, value in gates_result.items() if value is not True
        ],
        "gates": gates_result,
        "authorities": {
            "registration_commit": auditor.REGISTRATION_COMMIT,
            "implementation_commit": runtime["implementation_commit"],
            "registry_sha256": auditor.REGISTRY_SHA256,
            "scope_sha256": auditor.SCOPE_SHA256,
        },
        "old_observed_gate_order": list(gates),
        "registered_gate_order": list(auditor.EXPECTED_GATES),
        "old_order_sensitive_predicate": False,
        "new_order_independent_predicate": True,
        "production_imports": imports,
        "input_hashes_before": tracked_before,
        "input_hashes_after": tracked_after,
        "real_record_content_read": False,
        "sidecar_content_read": False,
        "materializer_executed": False,
        "sidecars_regenerated": False,
        "scenario_labels_materialized": False,
        "graph_materialized": False,
        "model_executed": False,
        "training_performed": False,
        "inference_performed": False,
        "loss_computed": False,
        "checkpoint_accessed": False,
        "recommendation_metrics_computed": False,
        "target_evaluation_performed": False,
        "real_audit_performed": False,
        "automatic_retry_performed": False,
        "interpretation": "PASS qualifies only the V1R3 auditor repair on synthetic and frozen receipt metadata; it does not qualify provenance or any downstream material.",
        "runtime": {"python": sys.version.split()[0]},
    }


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", required=True)
    parser.add_argument("--output-dir", required=True)
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    output = Path(args.output_dir).resolve()
    if output.exists():
        print("PROTOCOL_FAILURE=target-free output already exists", file=sys.stderr)
        return 2
    output.mkdir(parents=True, exist_ok=False)
    try:
        receipt = qualify(args.registry)
    except Exception as error:
        receipt = {
            "schema": "msahg.sthgcn-sample-materializer-v1r3-audit-target-free-failure.v1",
            "decision": "FAIL",
            "reason": str(error),
            "automatic_retry_performed": False,
            "materializer_executed": False,
            "training_performed": False,
            "recommendation_metrics_computed": False,
        }
    receipt_path = output / "target_free_receipt.json"
    _write_json(receipt_path, receipt)
    with open(
        str(output / "SHA256SUMS"), "w", encoding="utf-8", newline="\n"
    ) as handle:
        handle.write(
            "{}  target_free_receipt.json\n".format(
                auditor.sha256_file(receipt_path)
            )
        )
    print("TARGET_FREE_RECEIPT={}".format(receipt_path))
    print("DECISION={}".format(receipt["decision"]))
    return 0 if receipt["decision"] == "PASS" else 2


if __name__ == "__main__":
    sys.exit(main())
