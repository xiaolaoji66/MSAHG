#!/usr/bin/env python3
"""Independent score-free audit for STHGCN materializer R1 outputs."""

from __future__ import print_function

import argparse
import json
from pathlib import Path
import subprocess
import sys

import pandas as pd


EXPECTED = {
    "nyc": {"users": 1048, "pois": 4981, "post_filter_events": 103941, "trajectories": 14130},
    "tky": {"users": 2282, "pois": 7833, "post_filter_events": 405000, "trajectories": 65499},
}


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--audit-output", required=True)
    return parser.parse_args(argv)


def _checksum_ok(directory):
    result = subprocess.run(
        ["shasum", "-a", "256", "-c", "SHA256SUMS"],
        cwd=str(directory),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True,
    )
    return result.returncode == 0, result.stdout


def audit_dataset(root, dataset):
    directory = root / dataset
    checksum_ok, checksum_output = _checksum_ok(directory)
    sample = pd.read_csv(str(directory / "sample.csv"))
    train = pd.read_csv(str(directory / "train_sample.csv"))
    validation = pd.read_csv(str(directory / "validate_sample.csv"))
    test = pd.read_csv(str(directory / "test_sample.csv"))
    with open(str(directory / "label_encoding.json"), "r", encoding="utf-8") as handle:
        mappings = json.load(handle)
    with open(str(directory / "materialization_receipt.json"), "r", encoding="utf-8") as handle:
        receipt = json.load(handle)

    counts = {
        "users": int(sample["UserId"].nunique(dropna=False)),
        "pois": int(sample["PoiId"].nunique(dropna=False)),
        "post_filter_events": int(len(sample)),
        "trajectories": int(sample["pseudo_session_trajectory_id"].nunique(dropna=False)),
    }
    endpoint_ok = True
    for frame in (validation, test):
        endpoint_ok = endpoint_ok and bool(
            (frame["pseudo_session_trajectory_rank"] == frame["pseudo_session_trajectory_count"]).all()
        )
        endpoint_ok = endpoint_ok and bool((frame["pseudo_session_trajectory_rank"] > 1).all())
    train_first_ok = bool((train["pseudo_session_trajectory_rank"] > 1).all())
    cold_start_ok = True
    for frame in (validation, test):
        cold_start_ok = cold_start_ok and not bool(
            frame["UserId"].eq(mappings["UserId"]["padding_id"]).any()
        )
        cold_start_ok = cold_start_ok and not bool(
            frame["PoiId"].eq(mappings["PoiId"]["padding_id"]).any()
        )
    forbidden_names = [
        path.name for path in directory.iterdir()
        if "graph" in path.name.lower() or "scenario" in path.name.lower()
    ]
    checks = {
        "checksums": checksum_ok,
        "reported_counts": counts == EXPECTED[dataset],
        "receipt_counts": receipt["counts"]["post_filter_events"] == len(sample),
        "train_first_event_excluded": train_first_ok,
        "validation_test_final_event_only": endpoint_ok,
        "cold_start_excluded": cold_start_ok,
        "no_graph_or_scenario_output": not forbidden_names,
        "receipt_score_free": (
            receipt["recommendation_metrics_computed"] is False
            and receipt["training_performed"] is False
            and receipt["checkpoint_accessed"] is False
        ),
    }
    return {
        "dataset": dataset,
        "checks": checks,
        "counts": counts,
        "checksum_output": checksum_output,
        "forbidden_names": forbidden_names,
        "pass": all(checks.values()),
    }


def main(argv=None):
    args = parse_args(argv)
    root = Path(args.output_root).resolve()
    audit_path = Path(args.audit_output).resolve()
    if audit_path.exists():
        raise RuntimeError("audit output already exists")
    results = [audit_dataset(root, dataset) for dataset in ("nyc", "tky")]
    receipt = {
        "schema": "msahg.sthgcn-sample-materialization-independent-audit.v1",
        "decision": "PASS" if all(item["pass"] for item in results) else "HOLD",
        "datasets": {item["dataset"]: item for item in results},
        "training_performed": False,
        "recommendation_metrics_computed": False,
        "graph_materialized": False,
        "scenario_labels_materialized": False,
    }
    with open(str(audit_path), "w", encoding="utf-8", newline="\n") as handle:
        json.dump(receipt, handle, indent=2, sort_keys=True)
        handle.write("\n")
    print("INDEPENDENT_AUDIT={}".format(receipt["decision"]))
    return 0 if receipt["decision"] == "PASS" else 2


if __name__ == "__main__":
    sys.exit(main())
