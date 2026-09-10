#!/usr/bin/env python3
"""Synthetic target-free audit of the Marginal-Axis V1 causal materializer."""

from __future__ import print_function

import argparse
import ast
import copy
import hashlib
import io
import json
from pathlib import Path
import sys
import zipfile

import msahg_on_sthgcn_causal_materializer_v1r1 as materializer


def _production_imports(path):
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module.split(".")[0])
    return sorted(names)


def _coordinates(matrix):
    return set(matrix["coordinates"])


def _operator_value(matrix, row, column):
    for coordinate, value in zip(matrix["coordinates"], matrix["values"]):
        if coordinate == (row, column):
            return float(value)
    return 0.0


def _transition_orientation_witness():
    source = materializer._binary_graph((2, 1), [(0, 0)])
    target = materializer._binary_graph((2, 1), [(1, 0)])
    source_read = materializer.row_normalize(materializer.transpose_sparse(source))
    target_write = materializer.row_normalize(target)
    poi_values = [7.0, 0.0]
    edge_value = sum(
        _operator_value(source_read, 0, poi) * poi_values[poi]
        for poi in range(2)
    )
    output = [
        _operator_value(target_write, poi, 0) * edge_value
        for poi in range(2)
    ]
    return output == [0.0, 7.0]


def _expect_failure(callback):
    try:
        callback()
    except materializer.CausalMaterializerError:
        return True
    return False


def _target_label(material, source_ordinal):
    for row in material["scenario_rows"]:
        if row["source_ordinal"] == source_ordinal:
            return (
                row["UserGroup"],
                row["TimeGroup"],
                row["POIGroup"],
                row["prefix_source_ordinal"],
            )
    raise RuntimeError("synthetic target row is absent")


def _npz_format_ok(payload):
    # Inspect in memory without importing NumPy or touching real data.
    with zipfile.ZipFile(io.BytesIO(payload), "r") as archive:
        return (
            archive.namelist() == ["indices.npy", "values.npy", "shape.npy"]
            and all(item.date_time == (1980, 1, 1, 0, 0, 0) for item in archive.infolist())
            and all(item.compress_type == zipfile.ZIP_STORED for item in archive.infolist())
        )


def qualify(registry_path, sthgcn_root):
    registry = materializer.verify_registry(registry_path)
    runtime = materializer.verify_reproduction_authority()
    frozen = materializer.verify_frozen_repository_material(registry)
    source_authority = materializer.verify_source_authorities(sthgcn_root)
    rows, encoding = materializer.synthetic_fixture()
    first = materializer.build_material(rows, encoding)
    second = materializer.build_material(rows, encoding)

    perturbed = copy.deepcopy(rows)
    eval_targets = [
        row
        for row in perturbed
        if row["SplitTag"] in ("validation", "test")
    ]
    target = eval_targets[0]
    target_ordinal = int(target["source_ordinal"])
    target_before = _target_label(first, target_ordinal)
    target["PoiId"] = (int(target["PoiId"]) + 1) % 4
    target["Latitude"] = 0.0
    target["Longitude"] = 0.01
    target["UTCTimeOffset"] = "2024-01-07 23:59:00"
    target_perturbed = materializer.build_material(perturbed, encoding)
    target_after = _target_label(target_perturbed, target_ordinal)

    eval_changed = copy.deepcopy(rows)
    for row in eval_changed:
        if row["OriginalSplitTag"] != "train":
            row["PoiCategoryName"] = "Hotel"
            row["Latitude"] = min(89.0, float(row["Latitude"]) + 30.0)
            row["Longitude"] = min(179.0, float(row["Longitude"]) + 30.0)
    changed_material = materializer.build_material(eval_changed, encoding)
    train_only_rows = [row for row in rows if row["OriginalSplitTag"] == "train"]
    deleted_material = materializer.build_material(train_only_rows, encoding)

    user_gate = (
        first["hotel_shares"][0] == 0.05
        and first["hotel_shares"][1] == 0.05
        and first["hotel_shares"][2] == 0.10
        and first["hotel_shares"][3] == 0.10
        and first["user_labels"] == {0: 0, 1: 0, 2: 1, 3: 1}
    )
    center = first["activity_center"]
    spatial_gate = (
        center == (0.0, 0.0)
        and first["poi_labels"] == {0: 0, 1: 0, 2: 1, 3: 1}
        and materializer.haversine_km(first["poi_coordinates"][0], center)
        <= materializer.REGION_RADIUS_KM
        and materializer.haversine_km(first["poi_coordinates"][2], center)
        > materializer.REGION_RADIUS_KM
    )
    observed_tasks = set(
        task for row in first["scenario_rows"] for task in row["marginal_tasks"]
    )
    observed_joint = set(row["joint_triple"] for row in first["scenario_rows"])
    label_partition = all(
        row["UserGroup"] in (0, 1)
        and row["TimeGroup"] in (0, 1)
        and row["POIGroup"] in (0, 1)
        and len(row["marginal_tasks"]) == 3
        for row in first["scenario_rows"]
    ) and observed_tasks == set(materializer.AXIS_TASKS)

    graphs = first["graphs"]
    collaborative_global = _coordinates(graphs["collaborative_global_raw"])
    collaborative_local = _coordinates(graphs["collaborative_local_raw"])
    collaborative_tourist = _coordinates(graphs["collaborative_tourist_raw"])
    collaborative_gate = (
        collaborative_global == collaborative_local | collaborative_tourist
        and collaborative_local.isdisjoint(collaborative_tourist)
        and set(column for _, column in collaborative_local) == {0, 1}
        and set(column for _, column in collaborative_tourist) == {2, 3}
    )
    temporal_gate = True
    for prefix in ("temporal_poi", "temporal_user"):
        global_coordinates = _coordinates(graphs[prefix + "_global_raw"])
        workday = _coordinates(graphs[prefix + "_workday_raw"])
        weekend = _coordinates(graphs[prefix + "_weekend_raw"])
        temporal_gate = temporal_gate and global_coordinates == workday | weekend

    geography_global = _coordinates(graphs["geography_global_raw"])
    geography_central = _coordinates(graphs["geography_central_raw"])
    geography_peripheral = _coordinates(graphs["geography_peripheral_raw"])
    geography_gate = (
        all((poi, poi) in geography_global for poi in range(4))
        and all((right, left) in geography_global for left, right in geography_global)
        and geography_central
        == set(edge for edge in geography_global if first["poi_labels"][edge[0]] == first["poi_labels"][edge[1]] == 0)
        and geography_peripheral
        == set(edge for edge in geography_global if first["poi_labels"][edge[0]] == first["poi_labels"][edge[1]] == 1)
    )
    consecutive_expected = set()
    train_groups = {}
    for record in first["train_records"]:
        train_groups.setdefault(record["trajectory_id"], []).append(record)
    for trajectory in train_groups.values():
        ordered = sorted(trajectory, key=lambda item: item["trajectory_rank"])
        for left, right in zip(ordered, ordered[1:]):
            if left["trajectory_rank"] + 1 == right["trajectory_rank"]:
                consecutive_expected.add((left["poi_index"], right["poi_index"]))
    transition_gate = (
        set(first["transition_pairs"]) == consecutive_expected
        and len(first["transition_pairs"]) == len(set(first["transition_pairs"]))
        and _transition_orientation_witness()
    )

    bad_duplicate = copy.deepcopy(rows)
    bad_duplicate[1]["source_ordinal"] = bad_duplicate[0]["source_ordinal"]
    bad_coordinate = copy.deepcopy(rows)
    bad_coordinate[0]["Latitude"] = 100.0
    unknown_prefix = copy.deepcopy(rows)
    eval_prefix = next(
        row
        for row in unknown_prefix
        if row["OriginalSplitTag"] != "train" and row["SplitTag"] == "ignore"
    )
    eval_prefix["PoiId"] = encoding["PoiId"]["padding_id"]
    fail_closed = (
        _expect_failure(lambda: materializer.build_material(bad_duplicate, encoding))
        and _expect_failure(lambda: materializer.build_material(bad_coordinate, encoding))
        and _expect_failure(lambda: materializer.build_material(unknown_prefix, encoding))
        and registry["authorization"]["real_materialization_authorized"] is False
    )
    imports = _production_imports(Path(materializer.__file__).resolve())
    allowed_imports = sorted(
        [
            "__future__",
            "argparse",
            "csv",
            "datetime",
            "hashlib",
            "io",
            "json",
            "math",
            "pathlib",
            "struct",
            "subprocess",
            "sys",
            "zipfile",
        ]
    )
    determinism = first["artifacts"] == second["artifacts"] and all(
        _npz_format_ok(payload)
        for name, payload in first["artifacts"].items()
        if name.endswith(".npz")
    )
    gates = {
        "C0_AUTHORITY": (
            registry["parent_commit"] == materializer.PARENT_RESULT_COMMIT
            and registry["authorities"]["v1r3_result_commit"]
            == materializer.PARENT_RESULT_COMMIT
            and bool(runtime["implementation_commit"])
            and bool(frozen)
        ),
        "C1_NO_EVAL_FIT": first["train_derived_fingerprint"]
        == changed_material["train_derived_fingerprint"],
        "C2_PREFIX_LABEL": target_before == target_after,
        "C3_USER_RULE": user_gate,
        "C4_TIME_RULE": (
            materializer.half_hour_slot(materializer._parse_timestamp("2024-01-03 09:29:59")) == 18
            and materializer.half_hour_slot(materializer._parse_timestamp("2024-01-03 09:30:00")) == 19
            and set(row["TimeGroup"] for row in first["scenario_rows"]) == {0, 1}
        ),
        "C5_SPATIAL_RULE": spatial_gate,
        "C6_LABEL_PARTITION": label_partition,
        "C7_JOINT_METADATA_ONLY": observed_joint
        == set("{}|{}|{}".format(u, t, p) for u in (0, 1) for t in (0, 1) for p in (0, 1))
        and first["graph_manifest"]["joint_composite_forward"] is False,
        "C8_COLLABORATIVE": collaborative_gate,
        "C9_TEMPORAL": temporal_gate,
        "C10_GEOGRAPHY": geography_gate,
        "C11_TRANSITION": transition_gate,
        "C12_ROUTING": first["graph_manifest"]["task_routing"]
        == materializer.TASK_ROUTING
        and all(len(row["marginal_tasks"]) == 3 for row in first["scenario_rows"]),
        "C13_DETERMINISM": determinism,
        "C14_CAUSAL_PERTURBATION": (
            first["train_derived_fingerprint"]
            == changed_material["train_derived_fingerprint"]
            == deleted_material["train_derived_fingerprint"]
        ),
        "C15_SOURCE_IMMUTABLE": bool(source_authority),
        "C16_SCORE_FREE": imports == allowed_imports,
        "C17_FAIL_CLOSED": fail_closed,
    }
    if tuple(gates) != materializer.TARGET_FREE_GATES:
        raise RuntimeError("target-free gate sequence is not exact")
    decision = "PASS" if all(value is True for value in gates.values()) else "FAIL"
    return {
        "schema": "msahg.on-sthgcn.causal-materializer-v1r1-target-free-receipt.v1",
        "decision": decision,
        "failed_gates": [name for name, value in gates.items() if value is not True],
        "gates": gates,
        "authorities": {
            "registration_commit": materializer.REGISTRATION_COMMIT,
            "implementation_commit": runtime["implementation_commit"],
            "parent_result_commit": materializer.PARENT_RESULT_COMMIT,
            "registry_sha256": materializer.REGISTRY_SHA256,
            "scope_sha256": materializer.SCOPE_SHA256,
        },
        "production_imports": imports,
        "synthetic": {
            "records": len(first["records"]),
            "training_records": len(first["train_records"]),
            "eligible_targets": len(first["scenario_rows"]),
            "graph_shards": len(first["graph_manifest"]["graphs"]),
            "joint_cells_observed": sorted(observed_joint),
            "activity_center": [repr(center[0]), repr(center[1])],
            "train_derived_fingerprint": first["train_derived_fingerprint"],
        },
        "source_authority": source_authority,
        "real_record_content_read": False,
        "real_provenance_sidecar_read": False,
        "real_materialization_performed": False,
        "scenario_labels_materialized_from_real_data": False,
        "graph_materialized_from_real_data": False,
        "model_executed": False,
        "training_performed": False,
        "inference_performed": False,
        "loss_computed": False,
        "checkpoint_accessed": False,
        "recommendation_metrics_computed": False,
        "target_evaluation_performed": False,
        "automatic_retry_performed": False,
        "interpretation": "PASS establishes synthetic implementation coherence only; real scenario/graph materialization and all model activity remain unauthorized.",
        "runtime": {"python": sys.version.split()[0]},
    }


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", required=True)
    parser.add_argument("--sthgcn-root", required=True)
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
        receipt = qualify(args.registry, args.sthgcn_root)
    except Exception as error:
        receipt = {
            "schema": "msahg.on-sthgcn.causal-materializer-v1r1-target-free-failure.v1",
            "decision": "FAIL",
            "reason": str(error),
            "automatic_retry_performed": False,
            "real_record_content_read": False,
            "real_materialization_performed": False,
            "model_executed": False,
            "training_performed": False,
            "recommendation_metrics_computed": False,
        }
    receipt_path = output / "target_free_receipt.json"
    receipt_path.write_bytes(materializer.canonical_json_bytes(receipt))
    (output / "SHA256SUMS").write_text(
        "{}  target_free_receipt.json\n".format(materializer.sha256_file(receipt_path)),
        encoding="utf-8",
        newline="\n",
    )
    print("TARGET_FREE_RECEIPT={}".format(receipt_path))
    print("DECISION={}".format(receipt["decision"]))
    return 0 if receipt["decision"] == "PASS" else 2


if __name__ == "__main__":
    sys.exit(main())
