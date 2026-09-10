#!/usr/bin/env python3
"""Independent audit of real V1R2 original-split provenance outputs."""

from __future__ import print_function

import argparse
import hashlib
import json
from pathlib import Path
import sys

import pandas as pd


EXPECTED_ROWS = {"nyc": 103941, "tky": 405000}
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


def sha256_file(path):
    digest = hashlib.sha256()
    with open(str(path), "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _checksum_manifest_ok(directory):
    manifest = directory / "SHA256SUMS"
    if not manifest.is_file():
        return False
    for line in manifest.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        expected, relative = line.split("  ", 1)
        path = directory / relative
        if not path.is_file() or sha256_file(path) != expected:
            return False
    return True


def audit_dataset(root, v1_root, dataset):
    directory = root / dataset
    expected_names = {
        "record_split_provenance.csv", "provenance_receipt.json", "SHA256SUMS"
    }
    actual_names = set(path.name for path in directory.iterdir()) if directory.is_dir() else set()
    sidecar = pd.read_csv(str(directory / "record_split_provenance.csv"))
    sample = pd.read_csv(str(v1_root / dataset / "sample.csv"))
    with open(str(directory / "provenance_receipt.json"), "r", encoding="utf-8") as handle:
        receipt = json.load(handle)

    visible = sidecar["SplitTag"].ne("ignore")
    identity = ["check_ins_id", "source_ordinal", "raw_trajectory_id", "SplitTag"]
    identity_equal = all(
        sample[column].reset_index(drop=True).equals(sidecar[column].reset_index(drop=True))
        for column in identity
    )
    no_downstream = all(
        receipt[name] is False
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
    checks = {
        "receipt_schema": receipt.get("schema")
        == "msahg.sthgcn-sample-materializer-v1r2-provenance-receipt.v1",
        "file_allowlist": actual_names == expected_names,
        "checksums": _checksum_manifest_ok(directory),
        "decision": receipt.get("decision") == "PASS",
        "gate_set": tuple(receipt.get("gates", {})) == EXPECTED_GATES,
        "all_gates": all(receipt.get("gates", {}).values()),
        "columns": list(sidecar.columns) == SIDECAR_COLUMNS,
        "row_count": len(sidecar) == len(sample) == EXPECTED_ROWS[dataset],
        "unique_ordinal": bool(sidecar["source_ordinal"].is_unique),
        "unique_identity_pair": (
            sidecar[["check_ins_id", "source_ordinal"]].drop_duplicates().shape[0]
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
        "failure_superseded": receipt.get(
            "supersedes_v1r1_failure_archive_commit"
        )
        == "d7d8959eab2256d2e8153485165d11028c258025",
        "no_downstream": no_downstream,
    }
    return {
        "dataset": dataset,
        "checks": checks,
        "pass": all(checks.values()),
        "rows": int(len(sidecar)),
        "original_split_counts": {
            str(key): int(value)
            for key, value in sidecar["OriginalSplitTag"].value_counts(sort=False).sort_index().items()
        },
    }


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--v1-output-root", required=True)
    parser.add_argument("--audit-output", required=True)
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    root = Path(args.output_root).resolve()
    v1_root = Path(args.v1_output_root).resolve()
    audit_output = Path(args.audit_output).resolve()
    if audit_output.exists():
        print("PROTOCOL_FAILURE=audit output already exists", file=sys.stderr)
        return 2
    results = [audit_dataset(root, v1_root, dataset) for dataset in ("nyc", "tky")]
    root_names = set(path.name for path in root.iterdir())
    root_ok = root_names == {"nyc", "tky", "provenance_summary.json", "SHA256SUMS"}
    summary_ok = _checksum_manifest_ok(root)
    with open(str(root / "provenance_summary.json"), "r", encoding="utf-8") as handle:
        summary = json.load(handle)
    summary_identity = (
        summary.get("schema")
        == "msahg.sthgcn-sample-materializer-v1r2-provenance-summary.v1"
        and summary.get("decision") == "PASS"
        and summary.get("supersedes_v1r1_failure_archive_commit")
        == "d7d8959eab2256d2e8153485165d11028c258025"
        and summary.get("replay_directory_repair", {}).get("repair_delta_exact")
        is True
    )
    passed = root_ok and summary_ok and summary_identity and all(
        item["pass"] for item in results
    )
    receipt = {
        "schema": "msahg.sthgcn-sample-materializer-v1r2-independent-audit.v1",
        "decision": "PASS" if passed else "FAIL",
        "root_file_allowlist": root_ok,
        "root_checksums": summary_ok,
        "summary_identity": summary_identity,
        "datasets": {item["dataset"]: item for item in results},
        "training_performed": False,
        "recommendation_metrics_computed": False,
        "graph_materialized": False,
        "scenario_labels_materialized": False,
    }
    audit_output.parent.mkdir(parents=True, exist_ok=True)
    with open(str(audit_output), "w", encoding="utf-8", newline="\n") as handle:
        json.dump(receipt, handle, indent=2, sort_keys=True, ensure_ascii=False)
        handle.write("\n")
    print("INDEPENDENT_AUDIT={}".format(receipt["decision"]))
    return 0 if receipt["decision"] == "PASS" else 2


if __name__ == "__main__":
    sys.exit(main())

