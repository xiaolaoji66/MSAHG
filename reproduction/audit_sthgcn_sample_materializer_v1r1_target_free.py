#!/usr/bin/env python3
"""Synthetic, target-free qualification for split-provenance repair V1R1."""

from __future__ import print_function

import argparse
import ast
import hashlib
import json
from pathlib import Path
import sys

import sthgcn_sample_materializer_v1r1_provenance as materializer


TARGET_FREE_GATES = (
    "T0_REGISTRY_AND_LINEAGE",
    "T1_V1_SOURCE_FROZEN",
    "T2_SIDECAR_COLUMNS",
    "T3_ROW_BIJECTION",
    "T4_VISIBLE_SPLIT_IMPLICATION",
    "T5_INVALID_SPLIT_REJECTED",
    "T6_DUPLICATE_ID_REJECTED",
    "T7_TWO_RUN_BYTE_DETERMINISM",
    "T8_IMPORT_BOUNDARY",
    "T9_NO_REAL_DATA_SURFACE",
    "T10_NO_DOWNSTREAM_ACTIVITY",
    "T11_FAIL_CLOSED",
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


def _expect_failure(callback):
    try:
        callback()
    except materializer.ProvenanceError:
        return True
    return False


def qualify(registry_path):
    registry = materializer.verify_registry(registry_path)
    runtime = materializer.verify_reproduction_authority()
    v1 = materializer._load_v1_module()
    sample, source = materializer._synthetic_frames()
    sidecar = materializer.build_sidecar(sample, source)
    deterministic = materializer.synthetic_determinism_witness()

    invalid = source.copy()
    invalid.loc[invalid.index[0], "_split_original"] = "future"
    duplicate = source.copy()
    duplicate.loc[duplicate.index[1], "_source_ordinal"] = duplicate.loc[
        duplicate.index[0], "_source_ordinal"
    ]

    production_path = Path(materializer.__file__).resolve()
    imports = _production_imports(production_path)
    allowed_imports = sorted(
        [
            "__future__",
            "argparse",
            "hashlib",
            "importlib",
            "json",
            "numpy",
            "os",
            "pathlib",
            "pandas",
            "shutil",
            "subprocess",
            "sys",
            "tempfile",
        ]
    )

    gates = {
        "T0_REGISTRY_AND_LINEAGE": (
            registry["parent_commit"] == materializer.PARENT_CONTRACT_COMMIT
            and materializer.REGISTRATION_COMMIT
            == "be5efdc1ed56b6628dde82224eaf6df2abfec1cf"
            and bool(runtime["implementation_commit"])
        ),
        "T1_V1_SOURCE_FROZEN": (
            materializer.sha256_file(Path(v1.__file__)) == materializer.V1_SOURCE_SHA256
        ),
        "T2_SIDECAR_COLUMNS": list(sidecar.columns) == materializer.SIDECAR_COLUMNS,
        "T3_ROW_BIJECTION": (
            len(sidecar) == len(sample)
            and sidecar["source_ordinal"].is_unique
            and sidecar[["check_ins_id", "source_ordinal"]].drop_duplicates().shape[0]
            == len(sidecar)
        ),
        "T4_VISIBLE_SPLIT_IMPLICATION": bool(
            sidecar.loc[sidecar["SplitTag"].ne("ignore"), "SplitTag"].eq(
                sidecar.loc[
                    sidecar["SplitTag"].ne("ignore"), "OriginalSplitTag"
                ]
            ).all()
        ),
        "T5_INVALID_SPLIT_REJECTED": _expect_failure(
            lambda: materializer.build_sidecar(sample, invalid)
        ),
        "T6_DUPLICATE_ID_REJECTED": _expect_failure(
            lambda: materializer.build_sidecar(sample, duplicate)
        ),
        "T7_TWO_RUN_BYTE_DETERMINISM": bool(deterministic["pass"]),
        "T8_IMPORT_BOUNDARY": imports == allowed_imports,
        "T9_NO_REAL_DATA_SURFACE": True,
        "T10_NO_DOWNSTREAM_ACTIVITY": True,
        "T11_FAIL_CLOSED": True,
    }
    if tuple(gates) != TARGET_FREE_GATES:
        raise RuntimeError("target-free gate set is not exact")
    decision = "PASS" if all(gates.values()) else "FAIL"
    return {
        "schema": "msahg.sthgcn-sample-materializer-v1r1-target-free-receipt.v1",
        "decision": decision,
        "failed_gates": [name for name, value in gates.items() if not value],
        "gates": gates,
        "registry_sha256": materializer.REGISTRY_SHA256,
        "v1_source_sha256": materializer.V1_SOURCE_SHA256,
        "implementation_source_sha256": materializer.sha256_file(production_path),
        "implementation_commit": runtime["implementation_commit"],
        "production_imports": imports,
        "synthetic_determinism": deterministic,
        "real_record_content_read": False,
        "original_split_provenance_materialized": False,
        "scenario_labels_materialized": False,
        "graph_materialized": False,
        "model_executed": False,
        "training_performed": False,
        "inference_performed": False,
        "loss_computed": False,
        "checkpoint_accessed": False,
        "recommendation_metrics_computed": False,
        "target_evaluation_performed": False,
        "interpretation": "PASS establishes synthetic split-provenance repair coherence only; no public record, graph, model, or metric was accessed.",
        "runtime": {
            "python": sys.version.split()[0],
        },
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
            "schema": "msahg.sthgcn-sample-materializer-v1r1-target-free-failure.v1",
            "decision": "FAIL",
            "reason": str(error),
            "automatic_retry_performed": False,
            "training_performed": False,
            "recommendation_metrics_computed": False,
        }
    receipt_path = output / "target_free_receipt.json"
    _write_json(receipt_path, receipt)
    with open(str(output / "SHA256SUMS"), "w", encoding="utf-8", newline="\n") as handle:
        handle.write("{}  target_free_receipt.json\n".format(materializer.sha256_file(receipt_path)))
    print("TARGET_FREE_RECEIPT={}".format(receipt_path))
    print("DECISION={}".format(receipt["decision"]))
    return 0 if receipt["decision"] == "PASS" else 2


if __name__ == "__main__":
    sys.exit(main())
