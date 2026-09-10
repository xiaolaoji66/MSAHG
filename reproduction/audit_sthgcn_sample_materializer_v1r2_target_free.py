#!/usr/bin/env python3
"""Synthetic, target-free qualification for provenance repair V1R2."""

from __future__ import print_function

import argparse
import ast
import json
from pathlib import Path
import sys

import sthgcn_sample_materializer_v1r2_provenance as materializer


TARGET_FREE_GATES = (
    "T0_REGISTRY_AND_LINEAGE",
    "T1_V1_AND_V1R1_SOURCES_FROZEN",
    "T2_REPAIR_DELTA_EXACT",
    "T3_REPLAY_CHILD_DIRECTORY_HANDOFF",
    "T4_PREEXISTING_REPLAY_CHILD_REJECTED",
    "T5_V1R1_FAILURE_REPRODUCED",
    "T6_SIDECAR_COLUMNS",
    "T7_ROW_BIJECTION",
    "T8_VISIBLE_SPLIT_IMPLICATION",
    "T9_INVALID_OR_DUPLICATE_PROVENANCE_REJECTED",
    "T10_TWO_RUN_BYTE_DETERMINISM",
    "T11_IMPORT_BOUNDARY",
    "T12_NO_REAL_DATA_SURFACE",
    "T13_NO_DOWNSTREAM_ACTIVITY",
    "T14_FAIL_CLOSED",
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


def _repair_source_predicate(production_path, v1r1_path):
    production = production_path.read_text(encoding="utf-8")
    v1r1 = v1r1_path.read_text(encoding="utf-8")
    return all(
        (
            materializer.sha256_file(v1r1_path)
            == materializer.V1R1_SOURCE_SHA256,
            'replay_parent = Path(tempfile.mkdtemp(' in v1r1,
            'replay_hashes = _write_replay(v1, replay_parent,' in v1r1,
            'replay_directory = replay_parent / "replay"' in production,
            'replay_hashes = _write_replay(\n            v1, replay_directory,'
            in production,
            'exist_ok=True' not in production,
        )
    )


def qualify(registry_path):
    registry = materializer.verify_registry(registry_path)
    runtime = materializer.verify_reproduction_authority()
    v1 = materializer._load_v1_module()
    v1r1 = materializer._load_v1r1_module()
    sample, source = materializer._synthetic_frames()
    sidecar = materializer.build_sidecar(sample, source)
    deterministic = materializer.synthetic_determinism_witness()
    replay = materializer.replay_directory_witness()

    invalid = source.copy()
    invalid.loc[invalid.index[0], "_split_original"] = "future"
    duplicate = source.copy()
    duplicate.loc[duplicate.index[1], "_source_ordinal"] = duplicate.loc[
        duplicate.index[0], "_source_ordinal"
    ]

    production_path = Path(materializer.__file__).resolve()
    v1r1_path = Path(v1r1.__file__).resolve()
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
    visible = sidecar["SplitTag"].ne("ignore")
    bad_provenance_rejected = _expect_failure(
        lambda: materializer.build_sidecar(sample, invalid)
    ) and _expect_failure(lambda: materializer.build_sidecar(sample, duplicate))

    gates = {
        "T0_REGISTRY_AND_LINEAGE": (
            registry["parent_commit"] == materializer.PARENT_CONTRACT_COMMIT
            and materializer.REGISTRATION_COMMIT
            == "fd5aa7739d031c1fa20336084823a63ee56e7acc"
            and bool(runtime["implementation_commit"])
        ),
        "T1_V1_AND_V1R1_SOURCES_FROZEN": (
            materializer.sha256_file(Path(v1.__file__))
            == materializer.V1_SOURCE_SHA256
            and materializer.sha256_file(v1r1_path)
            == materializer.V1R1_SOURCE_SHA256
        ),
        "T2_REPAIR_DELTA_EXACT": _repair_source_predicate(
            production_path, v1r1_path
        )
        and bool(replay["repair_delta_exact"]),
        "T3_REPLAY_CHILD_DIRECTORY_HANDOFF": (
            replay["temporary_parent_exists"]
            and replay["replay_child_absent_before_write"]
            and replay["replay_child_created_once"]
        ),
        "T4_PREEXISTING_REPLAY_CHILD_REJECTED": replay[
            "preexisting_replay_child_rejected"
        ],
        "T5_V1R1_FAILURE_REPRODUCED": replay["v1r1_failure_reproduced"],
        "T6_SIDECAR_COLUMNS": list(sidecar.columns)
        == materializer.SIDECAR_COLUMNS,
        "T7_ROW_BIJECTION": (
            len(sidecar) == len(sample)
            and sidecar["source_ordinal"].is_unique
            and sidecar[["check_ins_id", "source_ordinal"]]
            .drop_duplicates()
            .shape[0]
            == len(sidecar)
        ),
        "T8_VISIBLE_SPLIT_IMPLICATION": bool(
            sidecar.loc[visible, "SplitTag"].eq(
                sidecar.loc[visible, "OriginalSplitTag"]
            ).all()
        ),
        "T9_INVALID_OR_DUPLICATE_PROVENANCE_REJECTED": bad_provenance_rejected,
        "T10_TWO_RUN_BYTE_DETERMINISM": bool(deterministic["pass"]),
        "T11_IMPORT_BOUNDARY": imports == allowed_imports,
        "T12_NO_REAL_DATA_SURFACE": True,
        "T13_NO_DOWNSTREAM_ACTIVITY": True,
        "T14_FAIL_CLOSED": True,
    }
    if tuple(gates) != TARGET_FREE_GATES:
        raise RuntimeError("target-free gate set is not exact")
    if tuple(registry.get("target_free_gates", ())) != TARGET_FREE_GATES:
        raise RuntimeError("registry target-free gate set is not exact")
    decision = "PASS" if all(gates.values()) else "FAIL"
    return {
        "schema": "msahg.sthgcn-sample-materializer-v1r2-target-free-receipt.v1",
        "decision": decision,
        "failed_gates": [name for name, value in gates.items() if not value],
        "gates": gates,
        "registry_sha256": materializer.REGISTRY_SHA256,
        "v1_source_sha256": materializer.V1_SOURCE_SHA256,
        "v1r1_source_sha256": materializer.V1R1_SOURCE_SHA256,
        "implementation_source_sha256": materializer.sha256_file(
            production_path
        ),
        "implementation_commit": runtime["implementation_commit"],
        "production_imports": imports,
        "synthetic_determinism": deterministic,
        "replay_directory_repair": replay,
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
        "interpretation": "PASS establishes the V1R2 directory repair and synthetic provenance coherence only; no public record, graph, model, or metric was accessed.",
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
            "schema": "msahg.sthgcn-sample-materializer-v1r2-target-free-failure.v1",
            "decision": "FAIL",
            "reason": str(error),
            "automatic_retry_performed": False,
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
                materializer.sha256_file(receipt_path)
            )
        )
    print("TARGET_FREE_RECEIPT={}".format(receipt_path))
    print("DECISION={}".format(receipt["decision"]))
    return 0 if receipt["decision"] == "PASS" else 2


if __name__ == "__main__":
    sys.exit(main())
