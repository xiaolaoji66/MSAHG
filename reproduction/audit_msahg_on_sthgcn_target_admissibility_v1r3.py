#!/usr/bin/env python3
"""Score-free real-data admissibility audit for the V1R3 reconstruction."""

from __future__ import print_function

import argparse
import csv
from datetime import datetime
import hashlib
import json
import math
from pathlib import Path
import statistics
import subprocess
import sys


REGISTRATION_COMMIT = "80a0dfccc306d961d95e77334188a93e7a624ad3"
PARENT_FAILURE = "727c82e8e1c822fa1acc8bab7f1511c2a2388b3e"
REGISTRY_SHA256 = "fc5f5efe379efb77fb17bd5cb90a306a85106e95b7f220a3e4e190be73d47b13"
SCOPE_SHA256 = "db82773ddd18c1a203604d9d59aa3b019ff12d1bd972ce7399592a68e40760dd"
REGISTRY_RELATIVE = "reproduction/MSAHG_ON_STHGCN_TARGET_ADMISSIBILITY_V1R3_REGISTRY.json"
SCOPE_RELATIVE = "reproduction/MSAHG_ON_STHGCN_TARGET_ADMISSIBILITY_V1R3_SCOPE.md"
AUTHORITY_RELATIVE = "reproduction/MSAHG_ON_STHGCN_TARGET_ADMISSIBILITY_V1R3_EXECUTION_AUTHORITY.json"
IMPLEMENTATION_ALLOWLIST = {
    "reproduction/audit_msahg_on_sthgcn_target_admissibility_v1r3.py",
    "scripts/run_msahg_on_sthgcn_target_admissibility_v1r3.sh",
    "tests/test_msahg_on_sthgcn_target_admissibility_v1r3.py",
    "tests/test_msahg_on_sthgcn_target_admissibility_v1r3_governance.py",
}
LEGAL_SPLITS = ("train", "validation", "test")
TASKS = ("User/0", "User/1", "Time/0", "Time/1", "POI/0", "POI/1")
GATES = (
    "A0_AUTHORITY_AND_LINEAGE",
    "A1_STHGCN_SOURCE_IDENTITY",
    "A2_FROZEN_INPUT_IDENTITY",
    "A3_SAMPLE_PROVENANCE_ROW_IDENTITY",
    "A4_OFFICIAL_CURRENT_ENDPOINT_RULE",
    "A5_EXACT_OFFICIAL_SPLIT_COUNTS",
    "A6_UNIQUE_IMMEDIATE_PREFIX",
    "A7_PREFIX_POI_TRAIN_KNOWN",
    "A8_TRAIN_ONLY_USER_LABELS",
    "A9_TRAIN_ONLY_POI_LABELS",
    "A10_EXACT_AXIS_PARTITIONS",
    "A11_SUPPORT_FLOORS",
    "A12_SOURCE_AND_INPUT_IMMUTABLE",
    "A13_SCORE_FREE",
)
EARTH_RADIUS_KM = 6371.0088
REGION_RADIUS_KM = 10.0


class AuditError(RuntimeError):
    pass


def sha256_file(path):
    digest = hashlib.sha256()
    with open(str(path), "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json_bytes(value):
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")


def semantic_sha256(value):
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def load_json(path):
    with open(str(path), "r", encoding="utf-8") as handle:
        return json.load(handle)


def _git(root, *args):
    return subprocess.check_output(
        ["git", "-C", str(root)] + list(args), stderr=subprocess.STDOUT
    ).decode("utf-8").strip()


def _inside_vocabulary(value, item):
    encoded = int(value)
    offset = int(item["offset"])
    return offset <= encoded < offset + len(item["classes"])


def _graph_index(value, item):
    if not _inside_vocabulary(value, item):
        return None
    return int(value) - int(item["offset"])


def _parse_timestamp(value):
    try:
        return datetime.strptime(str(value), "%Y-%m-%d %H:%M:%S")
    except ValueError as error:
        raise AuditError("invalid local timestamp: {}".format(value)) from error


def haversine_km(left, right):
    latitude_1, longitude_1 = left
    latitude_2, longitude_2 = right
    phi_1 = math.radians(latitude_1)
    phi_2 = math.radians(latitude_2)
    delta_phi = math.radians(latitude_2 - latitude_1)
    delta_lambda = math.radians(longitude_2 - longitude_1)
    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi_1) * math.cos(phi_2) * math.sin(delta_lambda / 2.0) ** 2
    )
    return EARTH_RADIUS_KM * 2.0 * math.atan2(math.sqrt(a), math.sqrt(max(0.0, 1.0 - a)))


def join_sample_and_provenance(sample_path, provenance_path):
    with open(str(sample_path), "r", encoding="utf-8", newline="") as handle:
        sample_rows = list(csv.DictReader(handle))
    with open(str(provenance_path), "r", encoding="utf-8", newline="") as handle:
        provenance_rows = list(csv.DictReader(handle))
    if len(sample_rows) != len(provenance_rows):
        raise AuditError("sample/provenance row count mismatch")
    joined = []
    for index, (sample, provenance) in enumerate(zip(sample_rows, provenance_rows)):
        for field in ("check_ins_id", "source_ordinal", "raw_trajectory_id", "SplitTag"):
            if str(sample.get(field)) != str(provenance.get(field)):
                raise AuditError("sample/provenance identity mismatch at row {}: {}".format(index, field))
        row = dict(sample)
        row["OriginalSplitTag"] = provenance.get("OriginalSplitTag")
        joined.append(row)
    return joined


def canonicalize_for_audit(rows, encoding):
    required = {
        "check_ins_id",
        "source_ordinal",
        "pseudo_session_trajectory_id",
        "pseudo_session_trajectory_rank",
        "raw_trajectory_id",
        "UserId",
        "PoiId",
        "PoiCategoryName",
        "Latitude",
        "Longitude",
        "UTCTimeOffset",
        "SplitTag",
        "OriginalSplitTag",
    }
    records = []
    ordinals = set()
    identities = set()
    for raw in rows:
        if not required.issubset(set(raw)):
            raise AuditError("record is missing registered columns")
        ordinal = int(raw["source_ordinal"])
        identity = (int(raw["check_ins_id"]), ordinal)
        if ordinal in ordinals or identity in identities:
            raise AuditError("duplicate stable record identity")
        ordinals.add(ordinal)
        identities.add(identity)
        latitude = float(raw["Latitude"])
        longitude = float(raw["Longitude"])
        if (
            not math.isfinite(latitude)
            or not math.isfinite(longitude)
            or latitude < -90.0
            or latitude > 90.0
            or longitude < -180.0
            or longitude > 180.0
        ):
            raise AuditError("invalid coordinate")
        split = str(raw["SplitTag"])
        original_split = str(raw["OriginalSplitTag"])
        if split not in LEGAL_SPLITS + ("ignore",) or original_split not in LEGAL_SPLITS:
            raise AuditError("illegal split provenance")
        records.append(
            {
                "check_ins_id": identity[0],
                "source_ordinal": ordinal,
                "trajectory_id": str(raw["pseudo_session_trajectory_id"]),
                "trajectory_rank": int(raw["pseudo_session_trajectory_rank"]),
                "raw_trajectory_id": str(raw["raw_trajectory_id"]),
                "user_encoded": int(raw["UserId"]),
                "poi_encoded": int(raw["PoiId"]),
                "user_index": _graph_index(raw["UserId"], encoding["UserId"]),
                "poi_index": _graph_index(raw["PoiId"], encoding["PoiId"]),
                "category_name": str(raw["PoiCategoryName"]),
                "latitude": latitude,
                "longitude": longitude,
                "timestamp": _parse_timestamp(raw["UTCTimeOffset"]),
                "split": split,
                "original_split": original_split,
            }
        )
    return sorted(records, key=lambda item: item["source_ordinal"])


def official_targets(records):
    targets = []
    excluded = {split: {"unknown_user": 0, "unknown_poi": 0, "either": 0} for split in LEGAL_SPLITS}
    for record in records:
        if record["split"] not in LEGAL_SPLITS:
            continue
        user_missing = record["user_index"] is None
        poi_missing = record["poi_index"] is None
        if user_missing or poi_missing:
            bucket = excluded[record["split"]]
            bucket["unknown_user"] += int(user_missing)
            bucket["unknown_poi"] += int(poi_missing)
            bucket["either"] += 1
            continue
        targets.append(record)
    return targets, excluded


def previous_by_trajectory(records):
    groups = {}
    for record in records:
        groups.setdefault(record["trajectory_id"], []).append(record)
    previous = {}
    duplicate_rank = []
    for trajectory_id, trajectory in groups.items():
        ordered = sorted(trajectory, key=lambda item: (item["trajectory_rank"], item["source_ordinal"]))
        seen = set()
        for index, record in enumerate(ordered):
            rank = record["trajectory_rank"]
            if rank in seen:
                duplicate_rank.append({"trajectory_id": trajectory_id, "rank": rank})
            seen.add(rank)
            if index and ordered[index - 1]["trajectory_rank"] + 1 == rank:
                previous[record["source_ordinal"]] = ordered[index - 1]
    return previous, duplicate_rank


def fit_user_labels(train_records, user_count):
    totals = [0] * user_count
    hotels = [0] * user_count
    for record in train_records:
        if record["user_index"] is None:
            raise AuditError("OriginalSplitTag=train contains unknown user")
        totals[record["user_index"]] += 1
        if record["category_name"] == "Hotel":
            hotels[record["user_index"]] += 1
    if any(value == 0 for value in totals):
        raise AuditError("train-known user has no OriginalSplitTag=train event")
    return {index: int(float(hotels[index]) / float(total) > 0.05) for index, total in enumerate(totals)}


def fit_poi_labels(train_records, poi_count):
    coordinates = {index: {"latitude": [], "longitude": []} for index in range(poi_count)}
    for record in train_records:
        if record["poi_index"] is None:
            raise AuditError("OriginalSplitTag=train contains unknown POI")
        item = coordinates[record["poi_index"]]
        item["latitude"].append(record["latitude"])
        item["longitude"].append(record["longitude"])
    poi_coordinates = {}
    for index in range(poi_count):
        item = coordinates[index]
        if not item["latitude"]:
            raise AuditError("train-known POI has no OriginalSplitTag=train event")
        poi_coordinates[index] = (
            statistics.median(item["latitude"]),
            statistics.median(item["longitude"]),
        )
    center = (
        statistics.median(value[0] for value in poi_coordinates.values()),
        statistics.median(value[1] for value in poi_coordinates.values()),
    )
    labels = {
        index: int(haversine_km(coordinate, center) > REGION_RADIUS_KM)
        for index, coordinate in poi_coordinates.items()
    }
    return labels, center


def build_support(targets, records, user_labels, poi_labels):
    previous, duplicate_rank = previous_by_trajectory(records)
    missing_prefix = []
    unknown_prefix_poi = []
    scenarios = []
    for target in targets:
        prefix = previous.get(target["source_ordinal"])
        if prefix is None:
            missing_prefix.append(target["source_ordinal"])
            continue
        if prefix["poi_index"] is None:
            unknown_prefix_poi.append(
                {"target_source_ordinal": target["source_ordinal"], "prefix_source_ordinal": prefix["source_ordinal"]}
            )
            continue
        user_group = user_labels[target["user_index"]]
        time_group = int(prefix["timestamp"].weekday() > 4)
        poi_group = poi_labels[prefix["poi_index"]]
        scenarios.append(
            {
                "split": target["split"],
                "user_index": target["user_index"],
                "tasks": (
                    "User/{}".format(user_group),
                    "Time/{}".format(time_group),
                    "POI/{}".format(poi_group),
                ),
            }
        )
    support = {}
    partitions = {}
    for split in LEGAL_SPLITS:
        split_rows = [row for row in scenarios if row["split"] == split]
        support[split] = {}
        for task in TASKS:
            members = [row for row in split_rows if task in row["tasks"]]
            support[split][task] = {
                "targets": len(members),
                "distinct_users": len(set(row["user_index"] for row in members)),
            }
        partitions[split] = {
            "scenario_rows": len(split_rows),
            "user_axis_total": sum(support[split]["User/{}".format(group)]["targets"] for group in (0, 1)),
            "time_axis_total": sum(support[split]["Time/{}".format(group)]["targets"] for group in (0, 1)),
            "poi_axis_total": sum(support[split]["POI/{}".format(group)]["targets"] for group in (0, 1)),
        }
    return support, partitions, duplicate_rank, missing_prefix, unknown_prefix_poi


def support_passes(support, floors):
    failures = []
    for split in LEGAL_SPLITS:
        floor = floors[split]
        for task in TASKS:
            observed = support[split][task]
            if observed["targets"] < int(floor["targets"]) or observed["distinct_users"] < int(floor["distinct_users"]):
                failures.append({"split": split, "task": task, "observed": observed, "floor": floor})
    return not failures, failures


def verify_runtime_authority(repo_root, registry, authority_path):
    authority = load_json(authority_path)
    head = _git(repo_root, "rev-parse", "HEAD")
    implementation = _git(repo_root, "rev-parse", "HEAD^")
    if _git(repo_root, "rev-parse", "HEAD^^") != REGISTRATION_COMMIT:
        raise AuditError("authority lineage is not registration -> implementation -> authority")
    if _git(repo_root, "rev-parse", REGISTRATION_COMMIT + "^") != PARENT_FAILURE:
        raise AuditError("registration parent failure archive mismatch")
    if _git(repo_root, "status", "--porcelain=v1", "--untracked-files=all"):
        raise AuditError("audit worktree is not clean")
    implementation_changed = set(
        _git(repo_root, "diff", "--name-only", REGISTRATION_COMMIT, implementation).splitlines()
    )
    implementation_status = _git(
        repo_root, "diff", "--name-status", REGISTRATION_COMMIT, implementation
    ).splitlines()
    if implementation_changed != IMPLEMENTATION_ALLOWLIST or not all(
        line.startswith("A\t") for line in implementation_status
    ):
        raise AuditError("implementation allowlist mismatch")
    authority_changed = _git(repo_root, "diff", "--name-status", implementation, head).splitlines()
    if authority_changed != ["A\t" + AUTHORITY_RELATIVE]:
        raise AuditError("authority commit must add exactly the authority file")
    expected = {
        "schema": "msahg.on-sthgcn.target-admissibility-v1r3-execution-authority.v1",
        "status": "ONE_SCORE_FREE_REAL_AUDIT_AUTHORIZED",
        "registration_commit": REGISTRATION_COMMIT,
        "implementation_commit": implementation,
        "registry_sha256": REGISTRY_SHA256,
        "audit_invocations": 1,
        "real_public_csv_read_authorized": True,
        "real_provenance_sidecar_read_authorized": True,
        "official_source_read_authorized": True,
        "scenario_support_computation_authorized": True,
        "graph_materialization_authorized": False,
        "scenario_materialization_authorized": False,
        "model_implementation_authorized": False,
        "training_authorized": False,
        "inference_authorized": False,
        "recommendation_metric_computation_authorized": False,
        "target_evaluation_authorized": False,
        "automatic_retry_authorized": False,
    }
    for key, value in expected.items():
        if authority.get(key) != value:
            raise AuditError("authority field mismatch: {}".format(key))
    if registry["status"] != "PROSPECTIVE_SCORE_FREE_AUDIT_REGISTERED_EXECUTION_NOT_YET_AUTHORIZED":
        raise AuditError("registry prospective status mismatch")
    return {"authority_commit": head, "implementation_commit": implementation}


def audit_dataset(dataset, registry, args):
    input_root = Path(args.v1_root).resolve() / dataset
    provenance_root = Path(args.v1r2_root).resolve() / dataset
    sample_path = input_root / "sample.csv"
    encoding_path = input_root / "label_encoding.json"
    provenance_path = provenance_root / "record_split_provenance.csv"
    frozen = registry["frozen_real_inputs"][dataset]
    paths = {
        "sample.csv": sample_path,
        "label_encoding.json": encoding_path,
        "record_split_provenance.csv": provenance_path,
    }
    before = {name: sha256_file(path) for name, path in paths.items()}
    if before != {name: frozen[name] for name in paths}:
        raise AuditError("{} frozen input identity mismatch".format(dataset))
    encoding = load_json(encoding_path)
    joined = join_sample_and_provenance(sample_path, provenance_path)
    if len(joined) != int(frozen["rows"]):
        raise AuditError("{} registered row count mismatch".format(dataset))
    records = canonicalize_for_audit(joined, encoding)
    targets, excluded = official_targets(records)
    target_counts = {split: sum(row["split"] == split for row in targets) for split in LEGAL_SPLITS}
    expected_counts = registry["official_filtered_target_counts"][dataset]
    count_match = target_counts == expected_counts
    train_records = [row for row in records if row["original_split"] == "train"]
    user_labels = fit_user_labels(train_records, len(encoding["UserId"]["classes"]))
    poi_labels, center = fit_poi_labels(train_records, len(encoding["PoiId"]["classes"]))
    support, partitions, duplicate_rank, missing_prefix, unknown_prefix_poi = build_support(
        targets, records, user_labels, poi_labels
    )
    target_count_by_split = target_counts
    partitions_exact = all(
        partitions[split][axis + "_axis_total"] == target_count_by_split[split]
        for split in LEGAL_SPLITS
        for axis in ("user", "time", "poi")
    )
    floors_pass, support_failures = support_passes(support, registry["support_floors"])
    after = {name: sha256_file(path) for name, path in paths.items()}
    return {
        "dataset": dataset,
        "complete_rows": len(records),
        "input_sha256_before": before,
        "input_sha256_after": after,
        "input_immutable": before == after,
        "encoding": {
            "user_offset": int(encoding["UserId"]["offset"]),
            "user_class_count": len(encoding["UserId"]["classes"]),
            "user_padding_id": int(encoding["UserId"]["padding_id"]),
            "poi_offset": int(encoding["PoiId"]["offset"]),
            "poi_class_count": len(encoding["PoiId"]["classes"]),
            "poi_padding_id": int(encoding["PoiId"]["padding_id"]),
        },
        "official_target_counts": target_counts,
        "expected_official_target_counts": expected_counts,
        "official_target_counts_exact": count_match,
        "excluded_current_endpoints": excluded,
        "duplicate_trajectory_ranks": duplicate_rank[:20],
        "duplicate_trajectory_rank_count": len(duplicate_rank),
        "missing_immediate_prefix_count": len(missing_prefix),
        "missing_immediate_prefix_examples": missing_prefix[:20],
        "unknown_immediate_prefix_poi_count": len(unknown_prefix_poi),
        "unknown_immediate_prefix_poi_examples": unknown_prefix_poi[:20],
        "train_only_user_labels": {
            "group_0_users": sum(value == 0 for value in user_labels.values()),
            "group_1_users": sum(value == 1 for value in user_labels.values()),
        },
        "train_only_activity_center": {"latitude": center[0], "longitude": center[1]},
        "train_only_poi_labels": {
            "group_0_pois": sum(value == 0 for value in poi_labels.values()),
            "group_1_pois": sum(value == 1 for value in poi_labels.values()),
        },
        "axis_partitions": partitions,
        "axis_partitions_exact": partitions_exact,
        "support": support,
        "support_floors_pass": floors_pass,
        "support_failures": support_failures,
    }


def parse_args(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--registry", required=True)
    parser.add_argument("--runtime-authority", required=True)
    parser.add_argument("--sthgcn-root", required=True)
    parser.add_argument("--v1-root", required=True)
    parser.add_argument("--v1r2-root", required=True)
    parser.add_argument("--output", required=True)
    return parser.parse_args(argv)


def run_audit(args):
    repo_root = Path(__file__).resolve().parents[1]
    registry_path = Path(args.registry).resolve()
    scope_path = repo_root / SCOPE_RELATIVE
    authority_path = Path(args.runtime_authority).resolve()
    if sha256_file(registry_path) != REGISTRY_SHA256:
        raise AuditError("registry identity mismatch")
    if sha256_file(scope_path) != SCOPE_SHA256:
        raise AuditError("scope identity mismatch")
    registry = load_json(registry_path)
    if tuple(registry["audit_gates"]) != GATES:
        raise AuditError("registered gate set mismatch")
    if Path(args.sthgcn_root).resolve() != Path(registry["server_paths"]["sthgcn_source_root"]):
        raise AuditError("STHGCN root is not registered")
    if Path(args.v1_root).resolve() != Path(registry["server_paths"]["v1_input_root"]):
        raise AuditError("V1 input root is not registered")
    if Path(args.v1r2_root).resolve() != Path(registry["server_paths"]["v1r2_provenance_root"]):
        raise AuditError("V1R2 provenance root is not registered")
    if Path(args.output).resolve() != Path(registry["server_paths"]["output_root"]):
        raise AuditError("output root is not registered")
    lineage = verify_runtime_authority(repo_root, registry, authority_path)
    sthgcn_root = Path(args.sthgcn_root).resolve()
    if _git(sthgcn_root, "rev-parse", "HEAD") != registry["authorities"]["sthgcn_commit"]:
        raise AuditError("STHGCN source commit mismatch")
    if _git(sthgcn_root, "status", "--porcelain=v1", "--untracked-files=all"):
        raise AuditError("STHGCN source worktree is not clean")
    source_before = {
        name: sha256_file(sthgcn_root / name) for name in registry["official_source_files"]
    }
    if source_before != registry["official_source_files"]:
        raise AuditError("STHGCN source file identity mismatch")
    datasets = [audit_dataset(dataset, registry, args) for dataset in ("nyc", "tky")]
    source_after = {
        name: sha256_file(sthgcn_root / name) for name in registry["official_source_files"]
    }
    counts_exact = all(item["official_target_counts_exact"] for item in datasets)
    prefixes_unique = all(
        item["duplicate_trajectory_rank_count"] == 0 and item["missing_immediate_prefix_count"] == 0
        for item in datasets
    )
    prefix_pois_known = all(item["unknown_immediate_prefix_poi_count"] == 0 for item in datasets)
    partitions_exact = all(item["axis_partitions_exact"] for item in datasets)
    supports_pass = all(item["support_floors_pass"] for item in datasets)
    inputs_immutable = all(item["input_immutable"] for item in datasets)
    gates = {
        "A0_AUTHORITY_AND_LINEAGE": True,
        "A1_STHGCN_SOURCE_IDENTITY": source_before == source_after == registry["official_source_files"],
        "A2_FROZEN_INPUT_IDENTITY": True,
        "A3_SAMPLE_PROVENANCE_ROW_IDENTITY": True,
        "A4_OFFICIAL_CURRENT_ENDPOINT_RULE": True,
        "A5_EXACT_OFFICIAL_SPLIT_COUNTS": counts_exact,
        "A6_UNIQUE_IMMEDIATE_PREFIX": prefixes_unique,
        "A7_PREFIX_POI_TRAIN_KNOWN": prefix_pois_known,
        "A8_TRAIN_ONLY_USER_LABELS": True,
        "A9_TRAIN_ONLY_POI_LABELS": True,
        "A10_EXACT_AXIS_PARTITIONS": partitions_exact,
        "A11_SUPPORT_FLOORS": supports_pass,
        "A12_SOURCE_AND_INPUT_IMMUTABLE": inputs_immutable and source_before == source_after,
        "A13_SCORE_FREE": True,
    }
    if not gates["A5_EXACT_OFFICIAL_SPLIT_COUNTS"]:
        decision = "PROTOCOL_FAILURE"
        reason = "OFFICIAL_FILTERED_TARGET_COUNTS_NOT_REPRODUCED"
    elif not all(gates[name] for name in ("A6_UNIQUE_IMMEDIATE_PREFIX", "A7_PREFIX_POI_TRAIN_KNOWN", "A10_EXACT_AXIS_PARTITIONS", "A11_SUPPORT_FLOORS")):
        decision = "DATA_NOT_ADMISSIBLE_FOR_CURRENT_SIX_TASK_RECONSTRUCTION_STOP"
        reason = "PREFIX_OR_SUPPORT_ADMISSIBILITY_GATE_FAILED"
    elif not all(gates.values()):
        decision = "PROTOCOL_FAILURE"
        reason = "IDENTITY_OR_PROTOCOL_GATE_FAILED"
    else:
        decision = "TARGET_ADMISSIBILITY_QUALIFIED_FOR_SEPARATE_V1R3_MATERIALIZER_REPAIR"
        reason = None
    receipt = {
        "schema": "msahg.on-sthgcn.target-admissibility-v1r3-receipt.v1",
        "date": "2026-09-10",
        "decision": decision,
        "reason": reason,
        "registration_commit": REGISTRATION_COMMIT,
        "parent_failure_archive": PARENT_FAILURE,
        "registry_sha256": REGISTRY_SHA256,
        "registry_semantic_sha256": semantic_sha256(registry),
        "scope_sha256": SCOPE_SHA256,
        "authority": lineage,
        "sthgcn_source_commit": registry["authorities"]["sthgcn_commit"],
        "sthgcn_source_sha256_before": source_before,
        "sthgcn_source_sha256_after": source_after,
        "gates": gates,
        "datasets": datasets,
        "model_executed": False,
        "training_performed": False,
        "inference_performed": False,
        "recommendation_metrics_computed": False,
        "graph_materialized": False,
        "scenario_materialized": False,
        "automatic_retry_performed": False,
        "interpretation": "PASS establishes official-target and six-task data admissibility only; it is not a model or ranking result.",
    }
    return receipt


def main(argv=None):
    args = parse_args(argv)
    output = Path(args.output).resolve()
    if output.exists():
        print("PROTOCOL_FAILURE=output directory already exists", file=sys.stderr)
        return 2
    try:
        receipt = run_audit(args)
    except Exception as error:
        receipt = {
            "schema": "msahg.on-sthgcn.target-admissibility-v1r3-receipt.v1",
            "date": "2026-09-10",
            "decision": "PROTOCOL_FAILURE",
            "reason": str(error),
            "gates": {},
            "model_executed": False,
            "training_performed": False,
            "inference_performed": False,
            "recommendation_metrics_computed": False,
            "graph_materialized": False,
            "scenario_materialized": False,
            "automatic_retry_performed": False,
        }
    output.mkdir(parents=True, exist_ok=False)
    receipt_path = output / "target_admissibility_receipt.json"
    receipt_path.write_bytes(canonical_json_bytes(receipt))
    checksum = sha256_file(receipt_path)
    (output / "SHA256SUMS").write_text(
        "{}  target_admissibility_receipt.json\n".format(checksum), encoding="utf-8"
    )
    print("TARGET_ADMISSIBILITY_RECEIPT={}".format(receipt_path))
    print("DECISION={}".format(receipt["decision"]))
    return 0 if receipt["decision"] != "PROTOCOL_FAILURE" else 2


if __name__ == "__main__":
    sys.exit(main())
