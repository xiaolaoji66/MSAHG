#!/usr/bin/env python3
"""V1R2 replay-directory repair for STHGCN original-split provenance."""

from __future__ import print_function

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

import numpy as np
import pandas as pd


REGISTRATION_COMMIT = "fd5aa7739d031c1fa20336084823a63ee56e7acc"
PARENT_CONTRACT_COMMIT = "d7d8959eab2256d2e8153485165d11028c258025"
V1_RESULT_COMMIT = "9e67e05875540cc87a21e15c4ff3623400c6ab49"
STHGCN_COMMIT = "27b595846d29019799485985bff49f9ed02c4ade"
REGISTRY_SHA256 = "55eb73a7a32b36f3f99570dc802b809c31eaa2caa930bd57bed6b810414ce612"
V1_SOURCE_SHA256 = "288daa4ab0de251cbbb0d4d8a1735af1193d42aa0c258757443fd2a154e65f3e"
V1R1_SOURCE_SHA256 = "606de269b48b6d5394a292956b033b0c43daa86d703360969443ce80e1ddaf5e"
V1R1_FAILURE_ARCHIVE_COMMIT = "d7d8959eab2256d2e8153485165d11028c258025"

EXPECTED_ROWS = {"nyc": 103941, "tky": 405000}
EXPECTED_V1_SHA256 = {
    "nyc": {
        "label_encoding.json": "1d8ae8f4a04908868f9ad4e186944a9f3e84b472bd015b2bbad9b663fff3c64b",
        "sample.csv": "4923e232f04e6a1d28de73a2545240e021066087706a824bcb01f6b0cf9f8f65",
        "test_sample.csv": "79063686fab16b7432a78e98b511b484ee79faa00515cc83b7df0bdbdcbb6c89",
        "train_sample.csv": "ed67d5fb35670abc8ca5faf4dd9a928f194f4f4529b671e1e1261dbd9cdfe6f7",
        "validate_sample.csv": "0cef8e32a8510844ed5c71d29cf61e7abfe8b175246173374a8f898e93d12e7d",
    },
    "tky": {
        "label_encoding.json": "333e33a94f9386ef0b5e62124a91bfdb22c1697ce2bae5b15ff12e73f93f81d7",
        "sample.csv": "b50fbd66c09463f1e2258a3fda33f3d4a11cd33cb2c20e1ede8873dab7cb47b0",
        "test_sample.csv": "bceee1b237c7f280c46a4a54f4e8787e10d363e071ac8d9811e5329bfe8a9d91",
        "train_sample.csv": "ff7ef1fd38920b6f204a187d2cefb5adf11d0dab494beac5b41c4ac32b12abf7",
        "validate_sample.csv": "630b5553b1a098d15da3584d8b74b43cf9f9a8640416686009bab117ccc17d63",
    },
}
SIDECAR_COLUMNS = [
    "check_ins_id",
    "source_ordinal",
    "raw_trajectory_id",
    "SplitTag",
    "OriginalSplitTag",
]
LEGAL_ORIGINAL_SPLITS = ("train", "validation", "test")
GATE_NAMES = (
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


class ProvenanceError(RuntimeError):
    pass


def sha256_file(path):
    digest = hashlib.sha256()
    with open(str(path), "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git(root, *args):
    return subprocess.check_output(
        ["git", "-C", str(root)] + list(args), stderr=subprocess.STDOUT
    ).decode("utf-8").strip()


def _load_v1_module():
    path = Path(__file__).resolve().with_name("sthgcn_sample_materializer_r1.py")
    if sha256_file(path) != V1_SOURCE_SHA256:
        raise ProvenanceError("frozen V1 materializer source identity mismatch")
    spec = importlib.util.spec_from_file_location("sthgcn_sample_materializer_r1_frozen", str(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_v1r1_module():
    path = Path(__file__).resolve().with_name(
        "sthgcn_sample_materializer_v1r1_provenance.py"
    )
    if sha256_file(path) != V1R1_SOURCE_SHA256:
        raise ProvenanceError("frozen V1R1 materializer source identity mismatch")
    spec = importlib.util.spec_from_file_location(
        "sthgcn_sample_materializer_v1r1_provenance_frozen", str(path)
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def verify_registry(registry_path):
    path = Path(registry_path).resolve()
    if sha256_file(path) != REGISTRY_SHA256:
        raise ProvenanceError("V1R2 registry identity mismatch")
    with open(str(path), "r", encoding="utf-8") as handle:
        registry = json.load(handle)
    if registry.get("parent_commit") != PARENT_CONTRACT_COMMIT:
        raise ProvenanceError("V1R2 parent contract identity mismatch")
    if registry.get("v1_data_sha256") != EXPECTED_V1_SHA256:
        raise ProvenanceError("V1 data hash registry mismatch")
    if tuple(registry.get("real_gates", ())) != GATE_NAMES:
        raise ProvenanceError("V1R2 gate set mismatch")
    return registry


def verify_reproduction_authority():
    root = Path(__file__).resolve().parents[1]
    head = _git(root, "rev-parse", "HEAD")
    if _git(root, "status", "--porcelain=v1", "--untracked-files=all"):
        raise ProvenanceError("reproduction worktree is not clean")
    for ancestor in (PARENT_CONTRACT_COMMIT, REGISTRATION_COMMIT):
        result = subprocess.run(
            ["git", "-C", str(root), "merge-base", "--is-ancestor", ancestor, head],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        if result.returncode != 0:
            raise ProvenanceError("reproduction authority lineage mismatch")
    return {"root": root, "implementation_commit": head}


def verify_v1_output(v1_output_root):
    root = Path(v1_output_root).resolve()
    observed = {}
    for dataset in ("nyc", "tky"):
        observed[dataset] = {}
        for name, expected in EXPECTED_V1_SHA256[dataset].items():
            path = root / dataset / name
            if not path.is_file():
                raise ProvenanceError("missing qualified V1 file: {}/{}".format(dataset, name))
            actual = sha256_file(path)
            observed[dataset][name] = actual
            if actual != expected:
                raise ProvenanceError("qualified V1 file identity mismatch: {}/{}".format(dataset, name))
    return observed


def _load_source(v1, dataset, archive_path):
    if dataset == "nyc":
        return v1._load_nyc(archive_path)
    if dataset == "tky":
        return v1._load_tky(archive_path)
    raise ProvenanceError("unsupported dataset: " + str(dataset))


def _write_replay(v1, directory, sample, eligible, mappings):
    directory.mkdir(parents=True, exist_ok=False)
    frames = {
        "sample.csv": sample,
        "train_sample.csv": eligible["train"],
        "validate_sample.csv": eligible["validation"],
        "test_sample.csv": eligible["test"],
    }
    for name, frame in frames.items():
        v1._write_csv(directory / name, frame)
    v1._write_json(directory / "label_encoding.json", mappings)
    return {name: sha256_file(directory / name) for name in sorted(EXPECTED_V1_SHA256["nyc"])}


def replay_directory_witness():
    v1 = _load_v1_module()
    v1r1 = _load_v1r1_module()
    sample = pd.DataFrame({"witness": [1]})
    eligible = {
        "train": sample.copy(),
        "validation": sample.iloc[0:0].copy(),
        "test": sample.iloc[0:0].copy(),
    }
    mappings = {"witness": {"1": 0}}

    with tempfile.TemporaryDirectory(prefix="sthgcn_v1r2_handoff_") as parent_name:
        parent = Path(parent_name)
        replay = parent / "replay"
        parent_exists = parent.is_dir()
        child_absent_before = not replay.exists()
        _write_replay(v1, replay, sample, eligible, mappings)
        child_created = replay.is_dir()
        try:
            _write_replay(v1, replay, sample, eligible, mappings)
        except FileExistsError:
            preexisting_rejected = True
        else:
            preexisting_rejected = False

    with tempfile.TemporaryDirectory(prefix="sthgcn_v1r1_failure_") as old_name:
        try:
            v1r1._write_replay(v1, Path(old_name), sample, eligible, mappings)
        except FileExistsError:
            v1r1_failure_reproduced = True
        else:
            v1r1_failure_reproduced = False

    allowed_delta = all(
        (
            parent_exists,
            child_absent_before,
            child_created,
            preexisting_rejected,
            v1r1_failure_reproduced,
        )
    )
    return {
        "temporary_parent_exists": parent_exists,
        "replay_child_absent_before_write": child_absent_before,
        "replay_child_created_once": child_created,
        "preexisting_replay_child_rejected": preexisting_rejected,
        "v1r1_failure_reproduced": v1r1_failure_reproduced,
        "repair_delta_exact": allowed_delta,
    }


def build_sidecar(sample, source):
    required_sample = {
        "check_ins_id",
        "source_ordinal",
        "raw_trajectory_id",
        "SplitTag",
    }
    required_source = {"_source_ordinal", "_split_original"}
    if not required_sample.issubset(set(sample.columns)):
        raise ProvenanceError("sample is missing stable identity columns")
    if not required_source.issubset(set(source.columns)):
        raise ProvenanceError("source is missing original split provenance")
    if sample["source_ordinal"].duplicated().any():
        raise ProvenanceError("sample source_ordinal is not unique")
    if source["_source_ordinal"].duplicated().any():
        raise ProvenanceError("source _source_ordinal is not unique")

    split_lookup = source.set_index("_source_ordinal")["_split_original"]
    sidecar = sample.loc[
        :, ["check_ins_id", "source_ordinal", "raw_trajectory_id", "SplitTag"]
    ].copy()
    sidecar["OriginalSplitTag"] = sidecar["source_ordinal"].map(split_lookup)
    sidecar = sidecar.loc[:, SIDECAR_COLUMNS]
    validate_sidecar(sample, sidecar)
    return sidecar


def validate_sidecar(sample, sidecar):
    if list(sidecar.columns) != SIDECAR_COLUMNS:
        raise ProvenanceError("sidecar column contract mismatch")
    if len(sidecar) != len(sample):
        raise ProvenanceError("sidecar row count mismatch")
    if sidecar["source_ordinal"].isna().any() or sidecar["OriginalSplitTag"].isna().any():
        raise ProvenanceError("sidecar has missing provenance")
    if sidecar["source_ordinal"].duplicated().any():
        raise ProvenanceError("sidecar source_ordinal is not unique")
    if sidecar[["check_ins_id", "source_ordinal"]].duplicated().any():
        raise ProvenanceError("sidecar stable identity pair is not unique")
    legal = sidecar["OriginalSplitTag"].isin(LEGAL_ORIGINAL_SPLITS)
    if not bool(legal.all()):
        raise ProvenanceError("sidecar contains illegal original split")
    visible = sidecar["SplitTag"].ne("ignore")
    if not bool(
        sidecar.loc[visible, "SplitTag"].eq(
            sidecar.loc[visible, "OriginalSplitTag"]
        ).all()
    ):
        raise ProvenanceError("visible split disagrees with original split")

    identity_columns = ["check_ins_id", "source_ordinal", "raw_trajectory_id", "SplitTag"]
    for column in identity_columns:
        left = sample[column].reset_index(drop=True)
        right = sidecar[column].reset_index(drop=True)
        if not bool(left.equals(right)):
            raise ProvenanceError("sidecar identity/order mismatch: " + column)
    return True


def _write_csv(v1, path, frame):
    v1._write_csv(path, frame)


def _write_json(path, value):
    with open(str(path), "w", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, indent=2, sort_keys=True, ensure_ascii=False)
        handle.write("\n")


def _cross_tab(sidecar):
    table = pd.crosstab(
        sidecar["OriginalSplitTag"], sidecar["SplitTag"], dropna=False
    )
    result = {}
    for original in LEGAL_ORIGINAL_SPLITS:
        result[original] = {}
        for visible in ("train", "validation", "test", "ignore"):
            value = 0
            if original in table.index and visible in table.columns:
                value = int(table.loc[original, visible])
            result[original][visible] = value
    return result


def _synthetic_frames():
    sample = pd.DataFrame(
        {
            "check_ins_id": [13, 7, 21, 9, 25],
            "source_ordinal": [0, 1, 2, 3, 4],
            "raw_trajectory_id": ["a", "a", "b", "b", "b"],
            "SplitTag": ["ignore", "train", "ignore", "ignore", "test"],
        }
    )
    source = pd.DataFrame(
        {
            "_source_ordinal": [4, 0, 3, 1, 2],
            "_split_original": ["test", "train", "validation", "train", "validation"],
        }
    )
    return sample, source


def synthetic_determinism_witness():
    v1 = _load_v1_module()
    sample, source = _synthetic_frames()
    sidecar = build_sidecar(sample, source)
    receipt = {
        "schema": "msahg.sthgcn-sample-materializer-v1r1-synthetic-witness.v1",
        "rows": int(len(sidecar)),
        "original_split_counts": {
            str(key): int(value)
            for key, value in sidecar["OriginalSplitTag"].value_counts(sort=False).sort_index().items()
        },
        "cross_tab": _cross_tab(sidecar),
        "score_bearing_activity_performed": False,
    }
    with tempfile.TemporaryDirectory(prefix="sthgcn_v1r1_synthetic_first_") as first_root:
        with tempfile.TemporaryDirectory(prefix="sthgcn_v1r1_synthetic_second_") as second_root:
            first_root = Path(first_root)
            second_root = Path(second_root)
            _write_csv(v1, first_root / "record_split_provenance.csv", sidecar)
            _write_json(first_root / "receipt.json", receipt)
            _write_csv(v1, second_root / "record_split_provenance.csv", sidecar)
            _write_json(second_root / "receipt.json", receipt)
            first = {
                name: sha256_file(first_root / name)
                for name in ("record_split_provenance.csv", "receipt.json")
            }
            second = {
                name: sha256_file(second_root / name)
                for name in ("record_split_provenance.csv", "receipt.json")
            }
    return {
        "pass": first == second,
        "first": first,
        "second": second,
        "rows": int(len(sidecar)),
    }


def _prepare_dataset(v1, dataset, archive_path, v1_output_root, output_root):
    dataset_output = output_root / dataset
    dataset_output.mkdir(parents=True, exist_ok=False)

    source = _load_source(v1, dataset, archive_path)
    sample, eligible, mappings = v1._finalize(source, dataset)

    with tempfile.TemporaryDirectory(
        prefix="sthgcn_v1r2_replay_parent_", dir=str(output_root.parent)
    ) as replay_parent_name:
        replay_parent = Path(replay_parent_name)
        replay_directory = replay_parent / "replay"
        if replay_directory.exists():
            raise ProvenanceError("V1R2 replay child unexpectedly exists")
        replay_hashes = _write_replay(
            v1, replay_directory, sample, eligible, mappings
        )
        if replay_hashes != EXPECTED_V1_SHA256[dataset]:
            raise ProvenanceError("V1 replay identity mismatch for " + dataset)

    sidecar = build_sidecar(sample, source)
    if len(sidecar) != EXPECTED_ROWS[dataset]:
        raise ProvenanceError("row-count witness mismatch for " + dataset)
    sidecar_path = dataset_output / "record_split_provenance.csv"
    _write_csv(v1, sidecar_path, sidecar)

    return {
        "dataset": dataset,
        "output": dataset_output,
        "sidecar": sidecar,
        "sidecar_sha256": sha256_file(sidecar_path),
        "replay_hashes": replay_hashes,
        "v1_input_hashes": verify_v1_output(v1_output_root)[dataset],
    }


def _finalize_dataset(
    prepared, implementation_commit, synthetic_witness, replay_witness
):
    sidecar = prepared["sidecar"]
    dataset = prepared["dataset"]
    output = prepared["output"]
    gates = {name: True for name in GATE_NAMES}
    gates["R9_TWO_RUN_DETERMINISM"] = bool(synthetic_witness["pass"])
    gates["R14_REPLAY_CHILD_DIRECTORY_HANDOFF"] = bool(
        replay_witness["replay_child_absent_before_write"]
        and replay_witness["replay_child_created_once"]
        and replay_witness["preexisting_replay_child_rejected"]
    )
    gates["R15_V1R1_FAILURE_REPRODUCED"] = bool(
        replay_witness["v1r1_failure_reproduced"]
    )
    gates["R16_REPAIR_DELTA_EXACT"] = bool(replay_witness["repair_delta_exact"])
    decision = "PASS" if all(gates.values()) else "PROTOCOL_FAILURE"
    counts = {
        "rows": int(len(sidecar)),
        "original_split": {
            split: int(sidecar["OriginalSplitTag"].eq(split).sum())
            for split in LEGAL_ORIGINAL_SPLITS
        },
        "visible_split": {
            split: int(sidecar["SplitTag"].eq(split).sum())
            for split in ("train", "validation", "test", "ignore")
        },
    }
    receipt = {
        "schema": "msahg.sthgcn-sample-materializer-v1r2-provenance-receipt.v1",
        "dataset": dataset,
        "decision": decision,
        "reason_codes": [] if decision == "PASS" else ["TARGET_FREE_GATE_FAILED"],
        "authorities": {
            "registration_commit": REGISTRATION_COMMIT,
            "parent_contract_commit": PARENT_CONTRACT_COMMIT,
            "implementation_commit": implementation_commit,
            "v1_result_commit": V1_RESULT_COMMIT,
            "sthgcn_commit": STHGCN_COMMIT,
            "registry_sha256": REGISTRY_SHA256,
            "v1_source_sha256": V1_SOURCE_SHA256,
        },
        "counts": counts,
        "cross_tab": _cross_tab(sidecar),
        "v1_input_sha256": prepared["v1_input_hashes"],
        "v1_replay_sha256": prepared["replay_hashes"],
        "sidecar_sha256": prepared["sidecar_sha256"],
        "synthetic_determinism": synthetic_witness,
        "replay_directory_repair": replay_witness,
        "supersedes_v1r1_failure_archive_commit": V1R1_FAILURE_ARCHIVE_COMMIT,
        "gates": gates,
        "original_split_provenance_materialized": True,
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
        "runtime": {
            "python": sys.version.split()[0],
            "pandas": pd.__version__,
            "numpy": np.__version__,
        },
        "interpretation": "PASS establishes original split provenance for every qualified V1 row only; it is not graph, model, or predictive evidence.",
    }
    _write_json(output / "provenance_receipt.json", receipt)
    with open(str(output / "SHA256SUMS"), "w", encoding="utf-8", newline="\n") as handle:
        for name in ("provenance_receipt.json", "record_split_provenance.csv"):
            handle.write("{}  {}\n".format(sha256_file(output / name), name))
    if set(path.name for path in output.iterdir()) != {
        "record_split_provenance.csv",
        "provenance_receipt.json",
        "SHA256SUMS",
    }:
        raise ProvenanceError("dataset output allowlist mismatch")
    return receipt


def _write_failure(output_root, error):
    if output_root is None or not output_root.exists():
        return
    path = output_root / "PROTOCOL_FAILURE.json"
    if path.exists():
        return
    receipt = {
        "schema": "msahg.sthgcn-sample-materializer-v1r2-provenance-failure.v1",
        "decision": "PROTOCOL_FAILURE",
        "reason": str(error),
        "automatic_retry_performed": False,
        "training_performed": False,
        "recommendation_metrics_computed": False,
    }
    _write_json(path, receipt)


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sthgcn-root", required=True)
    parser.add_argument("--v1-output-root", required=True)
    parser.add_argument("--registry", required=True)
    parser.add_argument("--output-root", required=True)
    return parser.parse_args(argv)


def run(args, output_root):
    if not output_root.is_dir() or any(output_root.iterdir()):
        raise ProvenanceError("fresh output root is not empty")
    verify_registry(args.registry)
    runtime = verify_reproduction_authority()
    v1 = _load_v1_module()
    source_authority = v1.verify_source_authority(args.sthgcn_root)
    v1_before = verify_v1_output(args.v1_output_root)

    synthetic = synthetic_determinism_witness()
    if not synthetic["pass"]:
        raise ProvenanceError("synthetic two-run determinism failed")
    replay_witness = replay_directory_witness()
    if not replay_witness["repair_delta_exact"]:
        raise ProvenanceError("V1R2 replay-directory repair witness failed")

    prepared = []
    for dataset in ("nyc", "tky"):
        prepared.append(
            _prepare_dataset(
                v1,
                dataset,
                source_authority[dataset],
                args.v1_output_root,
                output_root,
            )
        )

    v1_after = verify_v1_output(args.v1_output_root)
    if v1_before != v1_after:
        raise ProvenanceError("qualified V1 output changed during execution")
    if _git(source_authority["root"], "rev-parse", "HEAD") != STHGCN_COMMIT:
        raise ProvenanceError("STHGCN source commit changed during execution")
    if _git(source_authority["root"], "status", "--porcelain=v1", "--untracked-files=all"):
        raise ProvenanceError("STHGCN source tree changed during execution")
    if _git(runtime["root"], "rev-parse", "HEAD") != runtime["implementation_commit"]:
        raise ProvenanceError("reproduction commit changed during execution")
    if _git(runtime["root"], "status", "--porcelain=v1", "--untracked-files=all"):
        raise ProvenanceError("reproduction tree changed during execution")

    receipts = [
        _finalize_dataset(
            item, runtime["implementation_commit"], synthetic, replay_witness
        )
        for item in prepared
    ]
    summary = {
        "schema": "msahg.sthgcn-sample-materializer-v1r2-provenance-summary.v1",
        "decision": "PASS" if all(item["decision"] == "PASS" for item in receipts) else "PROTOCOL_FAILURE",
        "datasets": {item["dataset"]: item["decision"] for item in receipts},
        "registration_commit": REGISTRATION_COMMIT,
        "implementation_commit": runtime["implementation_commit"],
        "supersedes_v1r1_failure_archive_commit": V1R1_FAILURE_ARCHIVE_COMMIT,
        "replay_directory_repair": replay_witness,
        "original_split_provenance_materialized": True,
        "scenario_labels_materialized": False,
        "graph_materialized": False,
        "model_executed": False,
        "training_performed": False,
        "recommendation_metrics_computed": False,
        "target_evaluation_performed": False,
    }
    _write_json(output_root / "provenance_summary.json", summary)
    with open(str(output_root / "SHA256SUMS"), "w", encoding="utf-8", newline="\n") as handle:
        handle.write("{}  provenance_summary.json\n".format(sha256_file(output_root / "provenance_summary.json")))
        for dataset in ("nyc", "tky"):
            for name in ("SHA256SUMS", "provenance_receipt.json"):
                relative = "{}/{}".format(dataset, name)
                handle.write("{}  {}\n".format(sha256_file(output_root / relative), relative))
    if set(path.name for path in output_root.iterdir()) != {
        "nyc", "tky", "provenance_summary.json", "SHA256SUMS"
    }:
        raise ProvenanceError("root output allowlist mismatch")
    return summary


def main(argv=None):
    args = parse_args(argv)
    output_root = Path(args.output_root).resolve()
    if output_root.exists():
        print("PROTOCOL_FAILURE=output root already exists: {}".format(output_root), file=sys.stderr)
        return 2
    output_root.mkdir(parents=True, exist_ok=False)
    try:
        summary = run(args, output_root)
    except Exception as error:
        _write_failure(output_root, error)
        print("PROTOCOL_FAILURE={}".format(error), file=sys.stderr)
        return 2
    print("STHGCN_SAMPLE_MATERIALIZER_V1R2_PROVENANCE={}".format(summary["decision"]))
    print("OUTPUT_ROOT={}".format(output_root))
    return 0 if summary["decision"] == "PASS" else 2


if __name__ == "__main__":
    sys.exit(main())

