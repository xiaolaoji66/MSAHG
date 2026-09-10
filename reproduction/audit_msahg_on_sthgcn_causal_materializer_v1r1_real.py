#!/usr/bin/env python3
"""Independent real-data audit for the V1R1 Marginal-Axis materializer."""

from __future__ import print_function

import argparse
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys
import zipfile

import numpy as np
import pandas as pd
from scipy.spatial import cKDTree


REGISTRATION_COMMIT = "efdb7490155ca5006592506a4347425880ecb1cd"
PARENT_RESULT_COMMIT = "d7e2706d82656c718e70df621efbc90e29e74d6f"
MATERIALIZER_COMMIT = "1f6fce9505eae929a8f131fc67556e513c4d1100"
STHGCN_COMMIT = "27b595846d29019799485985bff49f9ed02c4ade"
REGISTRY_SHA256 = "6e3c4d003355d26efb34b28d9b0c1c1508c5bdd3073f216cad24353c0a37d1a4"
REGISTRY_SEMANTIC_SHA256 = "9447026f26e4e6ca79dba87eb7d7401b3287a3558d9234ff2dd2deb8ce231591"
AUTHORITY_SHA256 = "6b72ebdc704312a8703e6bca8184de1843e27f7372182393adace65728bb2ba0"
SCOPE_SHA256 = "63e4e1a9d841807398e6a3a68cb28676497dc2b4cf5b8c8cb6098be9cbf371a2"
MATERIALIZER_REGISTRY_SHA256 = "f9ff7c5ffe4affc4ccf4ff0d44dd9089274b4e416437f34219fa6b5c33ddc1ba"
TARGET_FREE_RECEIPT_SHA256 = "a0bda148878cc1bff1e5e549d21ba3e9e3d83ed8c98f3209ebe20ab51f8e10df"
EARTH_RADIUS_KM = 6371.0088
REGION_RADIUS_KM = 10.0
GEOGRAPHY_RADIUS_KM = 2.5
LEGAL_SPLITS = ("train", "validation", "test")
AXIS_TASKS = ("User/0", "User/1", "Time/0", "Time/1", "POI/0", "POI/1")
AUDIT_GATES = (
    "R0_AUTHORITY",
    "R1_INPUT_IDENTITY",
    "R2_OUTPUT_INVENTORY",
    "R3_MATERIALIZATION_RECEIPT",
    "R4_SCENARIO_IDENTITY",
    "R5_PREFIX_RECONSTRUCTION",
    "R6_USER_RECONSTRUCTION",
    "R7_TIME_RECONSTRUCTION",
    "R8_SPATIAL_RECONSTRUCTION",
    "R9_MARGINAL_ROUTING",
    "R10_SUPPORT_REPRODUCTION",
    "R11_COLLABORATIVE_RECONSTRUCTION",
    "R12_TEMPORAL_RECONSTRUCTION",
    "R13_GEOGRAPHY_RECONSTRUCTION",
    "R14_TRANSITION_RECONSTRUCTION",
    "R15_SPARSE_NORMALIZATION_AND_FORMAT",
    "R16_SOURCE_IMMUTABLE",
    "R17_SCORE_FREE",
    "R18_SUPPORT_DECISION",
)
IMPLEMENTATION_ALLOWLIST = {
    "reproduction/audit_msahg_on_sthgcn_causal_materializer_v1r1_real.py",
    "scripts/run_msahg_on_sthgcn_causal_materializer_v1r1_real.sh",
    "tests/test_msahg_on_sthgcn_causal_materializer_v1r1_real.py",
    "tests/test_msahg_on_sthgcn_causal_materializer_v1r1_real_governance.py",
}
TASK_ROUTING = {
    "User/0": {"collaborative": "local", "temporal": "global", "geography": "global", "transition": "shared"},
    "User/1": {"collaborative": "tourist", "temporal": "global", "geography": "global", "transition": "shared"},
    "Time/0": {"collaborative": "global", "temporal": "workday", "geography": "global", "transition": "shared"},
    "Time/1": {"collaborative": "global", "temporal": "weekend", "geography": "global", "transition": "shared"},
    "POI/0": {"collaborative": "global", "temporal": "global", "geography": "central", "transition": "shared"},
    "POI/1": {"collaborative": "global", "temporal": "global", "geography": "peripheral", "transition": "shared"},
}


class RealAuditError(RuntimeError):
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
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _git(root, *args):
    return subprocess.check_output(
        ["git", "-C", str(root)] + list(args), stderr=subprocess.STDOUT
    ).decode("utf-8").strip()


def load_json(path):
    with open(str(path), "r", encoding="utf-8") as handle:
        return json.load(handle)


def load_jsonl(path):
    rows = []
    with open(str(path), "r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.endswith("\n"):
                raise RealAuditError("JSONL line lacks terminal newline: {}".format(line_number))
            rows.append(json.loads(line))
    return rows


def verify_git_state(root, expected_commit, label):
    root = Path(root).resolve()
    if _git(root, "rev-parse", "HEAD") != expected_commit:
        raise RealAuditError("{} commit mismatch".format(label))
    if _git(root, "status", "--porcelain=v1", "--untracked-files=all"):
        raise RealAuditError("{} worktree is not clean".format(label))
    return str(root)


def verify_audit_implementation(root):
    root = Path(root).resolve()
    head = _git(root, "rev-parse", "HEAD")
    if _git(root, "rev-parse", "HEAD^") != REGISTRATION_COMMIT:
        raise RealAuditError("real auditor is not the direct registration child")
    if _git(root, "rev-parse", REGISTRATION_COMMIT + "^") != PARENT_RESULT_COMMIT:
        raise RealAuditError("real runtime registration parent mismatch")
    if _git(root, "status", "--porcelain=v1", "--untracked-files=all"):
        raise RealAuditError("real auditor worktree is not clean")
    changed = set(_git(root, "diff", "--name-only", REGISTRATION_COMMIT, head).splitlines())
    statuses = _git(root, "diff", "--name-status", REGISTRATION_COMMIT, head).splitlines()
    if changed != IMPLEMENTATION_ALLOWLIST or not all(line.startswith("A\t") for line in statuses):
        raise RealAuditError("real auditor implementation allowlist mismatch")
    return head


def verify_authorities(args):
    audit_root = Path(__file__).resolve().parents[1]
    registry_path = Path(args.registry).resolve()
    authority_path = Path(args.runtime_authority).resolve()
    scope_path = audit_root / "reproduction/MSAHG_ON_STHGCN_CAUSAL_MATERIALIZER_V1R1_REAL_RUNTIME_SCOPE.md"
    target_free_path = audit_root / "reproduction/results/msahg_on_sthgcn_causal_materializer_v1r1_target_free_1f6fce9/target_free_receipt.json"
    if sha256_file(registry_path) != REGISTRY_SHA256:
        raise RealAuditError("real runtime registry identity mismatch")
    registry = load_json(registry_path)
    if semantic_sha256(registry) != REGISTRY_SEMANTIC_SHA256:
        raise RealAuditError("real runtime registry semantic identity mismatch")
    if sha256_file(authority_path) != AUTHORITY_SHA256:
        raise RealAuditError("real runtime authority identity mismatch")
    authority = load_json(authority_path)
    if sha256_file(scope_path) != SCOPE_SHA256:
        raise RealAuditError("real runtime scope identity mismatch")
    if sha256_file(target_free_path) != TARGET_FREE_RECEIPT_SHA256:
        raise RealAuditError("target-free result identity mismatch")
    if tuple(registry.get("audit_gates", ())) != AUDIT_GATES:
        raise RealAuditError("real audit gate set mismatch")
    if registry.get("parent_commit") != PARENT_RESULT_COMMIT:
        raise RealAuditError("real runtime parent mismatch")
    if (
        authority.get("implementation_commit") != MATERIALIZER_COMMIT
        or authority.get("registry_sha256") != REGISTRY_SHA256
        or authority.get("real_materialization_authorized") is not True
        or authority.get("independent_audit_authorized") is not True
        or authority.get("automatic_retry_authorized") is not False
    ):
        raise RealAuditError("real runtime authorization fields mismatch")
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
            raise RealAuditError("score-bearing authority unexpectedly open: " + forbidden)
    if Path(args.v1_root).resolve() != Path(registry["server_paths"]["v1_input_root"]):
        raise RealAuditError("V1 input root is not registered")
    if Path(args.v1r2_root).resolve() != Path(registry["server_paths"]["v1r2_provenance_root"]):
        raise RealAuditError("V1R2 provenance root is not registered")
    if Path(args.materialization_root).resolve() != Path(registry["server_paths"]["output_root"]):
        raise RealAuditError("materialization output root is not registered")
    implementation_head = verify_audit_implementation(audit_root)
    materializer_root = verify_git_state(args.materializer_root, MATERIALIZER_COMMIT, "materializer")
    sthgcn_root = verify_git_state(args.sthgcn_root, STHGCN_COMMIT, "STHGCN source")
    materializer_registry = Path(materializer_root) / "reproduction/MSAHG_ON_STHGCN_CAUSAL_MATERIALIZER_V1R1_IMPLEMENTATION_REGISTRY.json"
    if sha256_file(materializer_registry) != MATERIALIZER_REGISTRY_SHA256:
        raise RealAuditError("materializer registry identity mismatch")
    return {
        "registry": registry,
        "authority": authority,
        "audit_implementation_commit": implementation_head,
        "materializer_root": materializer_root,
        "sthgcn_root": sthgcn_root,
    }


def frozen_input_paths(registry, v1_root, v1r2_root, dataset):
    v1_root = Path(v1_root).resolve()
    v1r2_root = Path(v1r2_root).resolve()
    return {
        "sample.csv": v1_root / dataset / "sample.csv",
        "label_encoding.json": v1_root / dataset / "label_encoding.json",
        "record_split_provenance.csv": v1r2_root / dataset / "record_split_provenance.csv",
    }


def verify_input_hashes(registry, v1_root, v1r2_root):
    observed = {}
    for dataset in ("nyc", "tky"):
        expected = registry["frozen_real_inputs"][dataset]
        paths = frozen_input_paths(registry, v1_root, v1r2_root, dataset)
        observed[dataset] = {}
        for name, path in paths.items():
            if not path.is_file():
                raise RealAuditError("missing frozen input: {}/{}".format(dataset, name))
            actual = sha256_file(path)
            observed[dataset][name] = actual
            if actual != expected[name]:
                raise RealAuditError("frozen input hash mismatch: {}/{}".format(dataset, name))
    return observed


def haversine_km(left, right):
    lat1, lon1 = left
    lat2, lon2 = right
    phi1 = math.radians(float(lat1))
    phi2 = math.radians(float(lat2))
    dphi = math.radians(float(lat2) - float(lat1))
    dlambda = math.radians(float(lon2) - float(lon1))
    value = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2
    return 2.0 * EARTH_RADIUS_KM * math.asin(math.sqrt(min(1.0, max(0.0, value))))


def reconstruct_input(sample_path, provenance_path, encoding_path):
    sample = pd.read_csv(str(sample_path), low_memory=False)
    provenance = pd.read_csv(str(provenance_path), low_memory=False)
    if len(sample) != len(provenance):
        raise RealAuditError("sample/provenance row count mismatch")
    for field in ("check_ins_id", "source_ordinal", "raw_trajectory_id", "SplitTag"):
        left = sample[field].astype(str).tolist()
        right = provenance[field].astype(str).tolist()
        if left != right:
            raise RealAuditError("sample/provenance identity mismatch: " + field)
    sample = sample.copy()
    sample["OriginalSplitTag"] = provenance["OriginalSplitTag"].astype(str)
    encoding = load_json(encoding_path)
    for field, destination in (("UserId", "_user_index"), ("PoiId", "_poi_index")):
        offset = int(encoding[field]["offset"])
        size = len(encoding[field]["classes"])
        values = pd.to_numeric(sample[field], errors="raise").astype("int64") - offset
        sample[destination] = values
        eligible = sample["SplitTag"].isin(LEGAL_SPLITS) | sample["OriginalSplitTag"].eq("train")
        if bool(((values < 0) | (values >= size))[eligible].any()):
            raise RealAuditError("train/eligible record uses unknown {}".format(field))
    sample["_timestamp"] = pd.to_datetime(sample["UTCTimeOffset"], format="%Y-%m-%d %H:%M:%S", errors="raise")
    if sample["source_ordinal"].duplicated().any():
        raise RealAuditError("duplicate source ordinal")
    if sample[["check_ins_id", "source_ordinal"]].duplicated().any():
        raise RealAuditError("duplicate stable record identity")
    return sample, encoding


def fit_train_objects(frame, encoding):
    train = frame.loc[frame["OriginalSplitTag"].eq("train")].copy()
    user_count = len(encoding["UserId"]["classes"])
    poi_count = len(encoding["PoiId"]["classes"])
    totals = train.groupby("_user_index", sort=True).size().reindex(range(user_count), fill_value=0)
    hotels = train.loc[train["PoiCategoryName"].eq("Hotel")].groupby("_user_index", sort=True).size().reindex(range(user_count), fill_value=0)
    if bool((totals == 0).any()):
        raise RealAuditError("train-known user has no training event")
    shares = hotels.astype("float64") / totals.astype("float64")
    user_labels = (shares > 0.05).astype("int64").to_dict()
    grouped = train.groupby("_poi_index", sort=True)
    latitudes = grouped["Latitude"].median().reindex(range(poi_count))
    longitudes = grouped["Longitude"].median().reindex(range(poi_count))
    if latitudes.isna().any() or longitudes.isna().any():
        raise RealAuditError("train-known POI has no training coordinate")
    if not np.isfinite(latitudes.to_numpy()).all() or not np.isfinite(longitudes.to_numpy()).all():
        raise RealAuditError("non-finite POI coordinate")
    poi_coordinates = np.column_stack((latitudes.to_numpy(dtype=np.float64), longitudes.to_numpy(dtype=np.float64)))
    center = (float(np.median(poi_coordinates[:, 0])), float(np.median(poi_coordinates[:, 1])))
    poi_labels = {
        poi: 0 if haversine_km(poi_coordinates[poi], center) <= REGION_RADIUS_KM else 1
        for poi in range(poi_count)
    }
    return train, user_labels, shares.to_dict(), poi_coordinates, center, poi_labels


def previous_records(frame):
    records = frame.to_dict("records")
    records.sort(key=lambda row: (str(row["pseudo_session_trajectory_id"]), int(row["pseudo_session_trajectory_rank"]), int(row["source_ordinal"])))
    previous = {}
    last_by_trajectory = {}
    seen = set()
    for row in records:
        trajectory = str(row["pseudo_session_trajectory_id"])
        rank = int(row["pseudo_session_trajectory_rank"])
        key = (trajectory, rank)
        if key in seen:
            raise RealAuditError("duplicate trajectory rank")
        seen.add(key)
        candidate = last_by_trajectory.get(trajectory)
        if candidate is not None and int(candidate["pseudo_session_trajectory_rank"]) + 1 == rank:
            previous[int(row["source_ordinal"])] = candidate
        last_by_trajectory[trajectory] = row
    return previous


def reconstruct_scenarios(frame, user_labels, poi_labels):
    previous = previous_records(frame)
    scenarios = []
    for row in frame.loc[frame["SplitTag"].isin(LEGAL_SPLITS)].to_dict("records"):
        ordinal = int(row["source_ordinal"])
        prefix = previous.get(ordinal)
        if prefix is None:
            raise RealAuditError("eligible target has no immediate prefix")
        user = int(row["_user_index"])
        prefix_poi = int(prefix["_poi_index"])
        if user not in user_labels or prefix_poi not in poi_labels:
            raise RealAuditError("eligible target is not train-vocabulary admissible")
        timestamp = prefix["_timestamp"]
        if hasattr(timestamp, "to_pydatetime"):
            timestamp = timestamp.to_pydatetime()
        user_group = int(user_labels[user])
        time_group = 0 if timestamp.weekday() <= 4 else 1
        poi_group = int(poi_labels[prefix_poi])
        scenarios.append(
            {
                "check_ins_id": int(row["check_ins_id"]),
                "source_ordinal": ordinal,
                "raw_trajectory_id": str(row["raw_trajectory_id"]),
                "SplitTag": str(row["SplitTag"]),
                "user_graph_index": user,
                "prefix_poi_graph_index": prefix_poi,
                "prefix_source_ordinal": int(prefix["source_ordinal"]),
                "UserGroup": user_group,
                "UserLabel": "local" if user_group == 0 else "tourist",
                "TimeGroup": time_group,
                "TimeLabel": "workday" if time_group == 0 else "weekend",
                "POIGroup": poi_group,
                "POILabel": "central" if poi_group == 0 else "peripheral",
                "joint_triple": "{}|{}|{}".format(user_group, time_group, poi_group),
                "marginal_tasks": [
                    "User/{}".format(user_group),
                    "Time/{}".format(time_group),
                    "POI/{}".format(poi_group),
                ],
            }
        )
    return sorted(scenarios, key=lambda row: row["source_ordinal"])


def support_from_scenarios(scenarios):
    support = {}
    for split in LEGAL_SPLITS:
        rows = [row for row in scenarios if row["SplitTag"] == split]
        marginal = {}
        for task in AXIS_TASKS:
            members = [row for row in rows if task in row["marginal_tasks"]]
            marginal[task] = {
                "targets": len(members),
                "distinct_users": len(set(row["user_graph_index"] for row in members)),
            }
        joint = {}
        for user in (0, 1):
            for time in (0, 1):
                for poi in (0, 1):
                    key = "{}|{}|{}".format(user, time, poi)
                    members = [row for row in rows if row["joint_triple"] == key]
                    joint[key] = {
                        "targets": len(members),
                        "distinct_users": len(set(row["user_graph_index"] for row in members)),
                    }
        support[split] = {"marginal": marginal, "joint_cells": joint}
    return support


def support_floor_pass(support, floors):
    failures = []
    for split in LEGAL_SPLITS:
        for task in AXIS_TASKS:
            observed = support[split]["marginal"][task]
            required = floors[split]
            for measure in ("targets", "distinct_users"):
                if int(observed[measure]) < int(required[measure]):
                    failures.append(
                        {
                            "split": split,
                            "task": task,
                            "measure": measure,
                            "observed": int(observed[measure]),
                            "required": int(required[measure]),
                        }
                    )
    return not failures, failures


def matrix(shape, coordinates, dtype, normalized=False):
    coordinates = sorted(set((int(row), int(column)) for row, column in coordinates))
    values = np.ones(len(coordinates), dtype=np.uint8 if dtype == "uint8" else np.float64)
    if normalized and coordinates:
        degrees = {}
        for row, _ in coordinates:
            degrees[row] = degrees.get(row, 0) + 1
        values = np.asarray([1.0 / float(degrees[row]) for row, _ in coordinates], dtype=np.float64)
    return {"shape": tuple(shape), "coordinates": coordinates, "dtype": dtype, "values": values}


def transpose_coordinates(coordinates):
    return [(column, row) for row, column in coordinates]


def geography_coordinates(poi_coordinates):
    radians = np.radians(poi_coordinates)
    xyz = np.column_stack(
        (
            np.cos(radians[:, 0]) * np.cos(radians[:, 1]),
            np.cos(radians[:, 0]) * np.sin(radians[:, 1]),
            np.sin(radians[:, 0]),
        )
    )
    angular = GEOGRAPHY_RADIUS_KM / EARTH_RADIUS_KM
    chord = np.nextafter(2.0 * math.sin(angular / 2.0), math.inf)
    pairs = cKDTree(xyz).query_pairs(chord, output_type="ndarray")
    edges = set((poi, poi) for poi in range(len(poi_coordinates)))
    for left, right in pairs.tolist() if len(pairs) else []:
        if haversine_km(poi_coordinates[left], poi_coordinates[right]) <= GEOGRAPHY_RADIUS_KM:
            edges.add((int(left), int(right)))
            edges.add((int(right), int(left)))
    return sorted(edges)


def expected_graphs(train, user_count, poi_count, user_labels, poi_coordinates, poi_labels):
    graphs = {}
    collaborative = {"global": set(), "local": set(), "tourist": set()}
    temporal_poi = {"global": set(), "workday": set(), "weekend": set()}
    temporal_user = {"global": set(), "workday": set(), "weekend": set()}
    for row in train.to_dict("records"):
        user = int(row["_user_index"])
        poi = int(row["_poi_index"])
        timestamp = row["_timestamp"]
        slot = int(2 * timestamp.hour + timestamp.minute // 30)
        time_name = "workday" if timestamp.weekday() <= 4 else "weekend"
        user_name = "local" if user_labels[user] == 0 else "tourist"
        collaborative["global"].add((poi, user))
        collaborative[user_name].add((poi, user))
        temporal_poi["global"].add((slot, poi))
        temporal_poi[time_name].add((slot, poi))
        temporal_user["global"].add((slot, user))
        temporal_user[time_name].add((slot, user))
    for name in ("global", "local", "tourist"):
        raw = sorted(collaborative[name])
        graphs["collaborative_{}_raw".format(name)] = matrix((poi_count, user_count), raw, "uint8")
        graphs["collaborative_{}_user_to_poi".format(name)] = matrix((poi_count, user_count), raw, "float64", True)
        graphs["collaborative_{}_poi_to_user".format(name)] = matrix((user_count, poi_count), transpose_coordinates(raw), "float64", True)
    for name in ("global", "workday", "weekend"):
        raw_poi = sorted(temporal_poi[name])
        raw_user = sorted(temporal_user[name])
        graphs["temporal_poi_{}_raw".format(name)] = matrix((48, poi_count), raw_poi, "uint8")
        graphs["temporal_poi_{}_time_to_poi".format(name)] = matrix((48, poi_count), raw_poi, "float64", True)
        graphs["temporal_poi_{}_poi_to_time".format(name)] = matrix((poi_count, 48), transpose_coordinates(raw_poi), "float64", True)
        graphs["temporal_user_{}_raw".format(name)] = matrix((48, user_count), raw_user, "uint8")
        graphs["temporal_user_{}_time_to_user".format(name)] = matrix((48, user_count), raw_user, "float64", True)
        graphs["temporal_user_{}_user_to_time".format(name)] = matrix((user_count, 48), transpose_coordinates(raw_user), "float64", True)
    global_geo = geography_coordinates(poi_coordinates)
    central = [edge for edge in global_geo if poi_labels[edge[0]] == poi_labels[edge[1]] == 0]
    peripheral = [edge for edge in global_geo if poi_labels[edge[0]] == poi_labels[edge[1]] == 1]
    for name, coordinates in (("global", global_geo), ("central", central), ("peripheral", peripheral)):
        graphs["geography_{}_raw".format(name)] = matrix((poi_count, poi_count), coordinates, "uint8")
        graphs["geography_{}_poi_to_poi".format(name)] = matrix((poi_count, poi_count), coordinates, "float64", True)
    transition_pairs = set()
    ordered = train.sort_values(
        ["pseudo_session_trajectory_id", "pseudo_session_trajectory_rank", "source_ordinal"],
        kind="mergesort",
    )
    for trajectory in ordered.groupby("pseudo_session_trajectory_id", sort=False):
        rows = trajectory[1].to_dict("records")
        for left, right in zip(rows, rows[1:]):
            if int(left["pseudo_session_trajectory_rank"]) + 1 == int(right["pseudo_session_trajectory_rank"]):
                transition_pairs.add((int(left["_poi_index"]), int(right["_poi_index"])))
    transition_pairs = sorted(transition_pairs)
    source = [(source, edge) for edge, (source, _) in enumerate(transition_pairs)]
    target = [(target, edge) for edge, (_, target) in enumerate(transition_pairs)]
    graphs["transition_source_raw"] = matrix((poi_count, len(transition_pairs)), source, "uint8")
    graphs["transition_target_raw"] = matrix((poi_count, len(transition_pairs)), target, "uint8")
    graphs["transition_source_read"] = matrix((len(transition_pairs), poi_count), transpose_coordinates(source), "float64", True)
    graphs["transition_target_write"] = matrix((poi_count, len(transition_pairs)), target, "float64", True)
    return graphs, transition_pairs


def checksum_manifest(directory):
    manifest_path = Path(directory) / "SHA256SUMS"
    entries = {}
    with open(str(manifest_path), "r", encoding="utf-8") as handle:
        for line in handle:
            digest, name = line.rstrip("\n").split("  ", 1)
            if name in entries:
                raise RealAuditError("duplicate SHA256SUMS path")
            entries[name] = digest
    actual_files = sorted(
        str(path.relative_to(directory))
        for path in Path(directory).rglob("*")
        if path.is_file() and path.name != "SHA256SUMS"
    )
    if sorted(entries) != actual_files:
        raise RealAuditError("materialized output inventory mismatch")
    if any(sha256_file(Path(directory) / name) != digest for name, digest in entries.items()):
        raise RealAuditError("materialized output checksum mismatch")
    return entries


def load_sparse(path):
    with zipfile.ZipFile(str(path), "r") as archive:
        if archive.namelist() != ["indices.npy", "values.npy", "shape.npy"]:
            raise RealAuditError("NPZ entry order mismatch: " + str(path))
        if not all(item.date_time == (1980, 1, 1, 0, 0, 0) for item in archive.infolist()):
            raise RealAuditError("NPZ timestamp mismatch: " + str(path))
        if not all(item.compress_type == zipfile.ZIP_STORED for item in archive.infolist()):
            raise RealAuditError("NPZ compression mismatch: " + str(path))
    with np.load(str(path), allow_pickle=False) as payload:
        if payload.files != ["indices", "values", "shape"]:
            raise RealAuditError("NPZ logical keys mismatch: " + str(path))
        return payload["indices"].copy(), payload["values"].copy(), payload["shape"].copy()


def compare_graphs(output, manifest, expected):
    family = {"collaborative": True, "temporal": True, "geography": True, "transition": True}
    sparse_ok = True
    if set(manifest["graphs"]) != set(expected):
        return {name: False for name in family}, False
    for name in sorted(expected):
        item = expected[name]
        metadata = manifest["graphs"][name]
        path = output / metadata["file"]
        indices, values, shape = load_sparse(path)
        expected_indices = np.asarray(item["coordinates"], dtype=np.int64)
        if expected_indices.size:
            expected_indices = expected_indices.T
        else:
            expected_indices = np.empty((2, 0), dtype=np.int64)
        expected_dtype = np.uint8 if item["dtype"] == "uint8" else np.float64
        exact = (
            sha256_file(path) == metadata["sha256"]
            and list(item["shape"]) == metadata["shape"]
            and int(metadata["nnz"]) == len(item["coordinates"])
            and metadata["value_dtype"] == item["dtype"]
            and indices.dtype == np.dtype("int64")
            and values.dtype == np.dtype(expected_dtype)
            and shape.dtype == np.dtype("int64")
            and tuple(shape.tolist()) == item["shape"]
            and np.array_equal(indices, expected_indices)
            and np.array_equal(values, item["values"])
        )
        family_name = (
            "collaborative" if name.startswith("collaborative_") else
            "temporal" if name.startswith("temporal_") else
            "geography" if name.startswith("geography_") else
            "transition"
        )
        family[family_name] = family[family_name] and exact
        sparse_ok = sparse_ok and exact
    return family, sparse_ok


def audit_dataset(dataset, registry, v1_root, v1r2_root, materialization_root):
    input_paths = frozen_input_paths(registry, v1_root, v1r2_root, dataset)
    frame, encoding = reconstruct_input(
        input_paths["sample.csv"],
        input_paths["record_split_provenance.csv"],
        input_paths["label_encoding.json"],
    )
    expected_rows = int(registry["frozen_real_inputs"][dataset]["rows"])
    if len(frame) != expected_rows:
        raise RealAuditError("{} row count mismatch".format(dataset))
    train, user_labels, hotel_shares, poi_coordinates, center, poi_labels = fit_train_objects(frame, encoding)
    expected_scenarios = reconstruct_scenarios(frame, user_labels, poi_labels)
    output = Path(materialization_root) / dataset
    manifest_entries = checksum_manifest(output)
    actual_scenarios = load_jsonl(output / "scenario_labels.jsonl")
    activity = load_json(output / "activity_center.json")
    support_payload = load_json(output / "group_support.json")
    graph_manifest = load_json(output / "graph_manifest.json")
    materialization_receipt = load_json(output / "materialization_receipt.json")
    expected_support = support_from_scenarios(expected_scenarios)
    expected_graph_map, transition_pairs = expected_graphs(
        train,
        len(encoding["UserId"]["classes"]),
        len(encoding["PoiId"]["classes"]),
        user_labels,
        poi_coordinates,
        poi_labels,
    )
    family, sparse_ok = compare_graphs(output, graph_manifest, expected_graph_map)
    identity_fields = ("check_ins_id", "source_ordinal", "raw_trajectory_id", "SplitTag")
    scenario_identity = [tuple(row[name] for name in identity_fields) for row in actual_scenarios] == [tuple(row[name] for name in identity_fields) for row in expected_scenarios]
    prefix_fields = ("prefix_source_ordinal", "prefix_poi_graph_index")
    prefix_ok = [tuple(row[name] for name in prefix_fields) for row in actual_scenarios] == [tuple(row[name] for name in prefix_fields) for row in expected_scenarios]
    user_fields = ("UserGroup", "UserLabel")
    time_fields = ("TimeGroup", "TimeLabel")
    poi_fields = ("POIGroup", "POILabel")
    user_ok = [tuple(row[name] for name in user_fields) for row in actual_scenarios] == [tuple(row[name] for name in user_fields) for row in expected_scenarios]
    time_ok = [tuple(row[name] for name in time_fields) for row in actual_scenarios] == [tuple(row[name] for name in time_fields) for row in expected_scenarios]
    poi_ok = [tuple(row[name] for name in poi_fields) for row in actual_scenarios] == [tuple(row[name] for name in poi_fields) for row in expected_scenarios]
    activity_ok = (
        activity["latitude_binary64_decimal"] == repr(center[0])
        and activity["longitude_binary64_decimal"] == repr(center[1])
        and all(
            activity["poi_coordinates"][str(poi)]["group"] == poi_labels[poi]
            and activity["poi_coordinates"][str(poi)]["latitude_binary64_decimal"] == repr(float(poi_coordinates[poi, 0]))
            and activity["poi_coordinates"][str(poi)]["longitude_binary64_decimal"] == repr(float(poi_coordinates[poi, 1]))
            for poi in range(len(poi_coordinates))
        )
    )
    routing_ok = (
        actual_scenarios == expected_scenarios
        and graph_manifest["task_routing"] == TASK_ROUTING
        and graph_manifest["joint_composite_forward"] is False
        and all(len(row["marginal_tasks"]) == 3 for row in actual_scenarios)
    )
    support_ok = support_payload["support"] == expected_support
    floor_pass, floor_failures = support_floor_pass(expected_support, registry["support_floors"])
    score_free = all(materialization_receipt.get(name) is False for name in (
        "model_executed",
        "training_performed",
        "inference_performed",
        "loss_computed",
        "checkpoint_accessed",
        "recommendation_metrics_computed",
        "target_evaluation_performed",
    ))
    receipt_ok = (
        materialization_receipt.get("dataset") == dataset
        and materialization_receipt.get("decision") == "MATERIALIZED_PENDING_INDEPENDENT_AUDIT"
        and materialization_receipt.get("implementation_commit") == MATERIALIZER_COMMIT
        and materialization_receipt.get("registry_sha256") == MATERIALIZER_REGISTRY_SHA256
        and materialization_receipt.get("rows") == len(frame)
        and materialization_receipt.get("eligible_targets") == len(expected_scenarios)
        and score_free
    )
    graph_manifest_ok = (
        graph_manifest["user_count"] == len(encoding["UserId"]["classes"])
        and graph_manifest["poi_count"] == len(encoding["PoiId"]["classes"])
        and graph_manifest["time_slot_count"] == 48
        and graph_manifest["transition_pairs"] == [list(pair) for pair in transition_pairs]
    )
    return {
        "dataset": dataset,
        "rows": len(frame),
        "training_rows": len(train),
        "eligible_targets": len(expected_scenarios),
        "input_hashes": {name: sha256_file(path) for name, path in input_paths.items()},
        "output_manifest_sha256": sha256_file(output / "SHA256SUMS"),
        "materialization_receipt_sha256": sha256_file(output / "materialization_receipt.json"),
        "graph_manifest_sha256": sha256_file(output / "graph_manifest.json"),
        "group_support_sha256": sha256_file(output / "group_support.json"),
        "scenario_labels_sha256": sha256_file(output / "scenario_labels.jsonl"),
        "scenario_identity": scenario_identity,
        "prefix_reconstruction": prefix_ok,
        "user_reconstruction": user_ok,
        "time_reconstruction": time_ok,
        "spatial_reconstruction": poi_ok and activity_ok,
        "marginal_routing": routing_ok,
        "support_reproduction": support_ok,
        "materialization_receipt": receipt_ok,
        "score_free": score_free,
        "graph_manifest": graph_manifest_ok,
        "graph_families": family,
        "sparse_normalization_and_format": sparse_ok,
        "support_floor_pass": floor_pass,
        "support_floor_failures": floor_failures,
        "support_decision_consistent": floor_pass == (len(floor_failures) == 0),
        "support": expected_support,
        "hotel_share_min": repr(min(float(value) for value in hotel_shares.values())),
        "hotel_share_max": repr(max(float(value) for value in hotel_shares.values())),
        "activity_center": [repr(center[0]), repr(center[1])],
        "output_file_count": len(manifest_entries) + 1,
    }


def run_audit(args):
    authority = verify_authorities(args)
    before = verify_input_hashes(authority["registry"], args.v1_root, args.v1r2_root)
    datasets = [
        audit_dataset(
            dataset,
            authority["registry"],
            args.v1_root,
            args.v1r2_root,
            args.materialization_root,
        )
        for dataset in ("nyc", "tky")
    ]
    after = verify_input_hashes(authority["registry"], args.v1_root, args.v1r2_root)
    source_immutable = (
        before == after
        and verify_git_state(args.materializer_root, MATERIALIZER_COMMIT, "materializer")
        and verify_git_state(args.sthgcn_root, STHGCN_COMMIT, "STHGCN source")
    )
    gates = {
        "R0_AUTHORITY": bool(authority["audit_implementation_commit"]),
        "R1_INPUT_IDENTITY": before == after,
        "R2_OUTPUT_INVENTORY": all(item["output_file_count"] == 43 for item in datasets),
        "R3_MATERIALIZATION_RECEIPT": all(item["materialization_receipt"] for item in datasets),
        "R4_SCENARIO_IDENTITY": all(item["scenario_identity"] for item in datasets),
        "R5_PREFIX_RECONSTRUCTION": all(item["prefix_reconstruction"] for item in datasets),
        "R6_USER_RECONSTRUCTION": all(item["user_reconstruction"] for item in datasets),
        "R7_TIME_RECONSTRUCTION": all(item["time_reconstruction"] for item in datasets),
        "R8_SPATIAL_RECONSTRUCTION": all(item["spatial_reconstruction"] for item in datasets),
        "R9_MARGINAL_ROUTING": all(item["marginal_routing"] for item in datasets),
        "R10_SUPPORT_REPRODUCTION": all(item["support_reproduction"] for item in datasets),
        "R11_COLLABORATIVE_RECONSTRUCTION": all(item["graph_families"]["collaborative"] for item in datasets),
        "R12_TEMPORAL_RECONSTRUCTION": all(item["graph_families"]["temporal"] for item in datasets),
        "R13_GEOGRAPHY_RECONSTRUCTION": all(item["graph_families"]["geography"] for item in datasets),
        "R14_TRANSITION_RECONSTRUCTION": all(item["graph_families"]["transition"] and item["graph_manifest"] for item in datasets),
        "R15_SPARSE_NORMALIZATION_AND_FORMAT": all(item["sparse_normalization_and_format"] for item in datasets),
        "R16_SOURCE_IMMUTABLE": bool(source_immutable),
        "R17_SCORE_FREE": all(item["score_free"] for item in datasets),
        "R18_SUPPORT_DECISION": all(item["support_decision_consistent"] for item in datasets),
    }
    if tuple(gates) != AUDIT_GATES:
        raise RealAuditError("audit gate sequence mismatch")
    protocol_pass = all(value is True for value in gates.values())
    support_pass = all(item["support_floor_pass"] for item in datasets)
    if not protocol_pass:
        decision = "PROTOCOL_FAILURE"
    elif not support_pass:
        decision = "DATA_NOT_ADMISSIBLE_FOR_SIX_TASK_SCORE"
    else:
        decision = "MATERIALIZATION_QUALIFIED_ONLY"
    return {
        "schema": "msahg.on-sthgcn.causal-materializer-v1r1-real-audit.v1",
        "decision": decision,
        "protocol_pass": protocol_pass,
        "support_pass": support_pass,
        "gates": gates,
        "failed_gates": [name for name, value in gates.items() if value is not True],
        "datasets": {item["dataset"]: item for item in datasets},
        "authorities": {
            "registration_commit": REGISTRATION_COMMIT,
            "audit_implementation_commit": authority["audit_implementation_commit"],
            "materializer_commit": MATERIALIZER_COMMIT,
            "parent_result_commit": PARENT_RESULT_COMMIT,
            "registry_sha256": REGISTRY_SHA256,
            "authority_sha256": AUTHORITY_SHA256,
            "target_free_receipt_sha256": TARGET_FREE_RECEIPT_SHA256,
        },
        "input_hashes_before": before,
        "input_hashes_after": after,
        "model_executed": False,
        "training_performed": False,
        "inference_performed": False,
        "loss_computed": False,
        "checkpoint_accessed": False,
        "recommendation_metrics_computed": False,
        "target_evaluation_performed": False,
        "automatic_retry_performed": False,
        "interpretation": "This decision qualifies only real scenario/graph materialization and registered support; it is not a predictive-performance result or model authorization.",
        "runtime": {
            "python": sys.version.split()[0],
            "numpy": np.__version__,
            "pandas": pd.__version__,
        },
    }


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", required=True)
    parser.add_argument("--runtime-authority", required=True)
    parser.add_argument("--materializer-root", required=True)
    parser.add_argument("--sthgcn-root", required=True)
    parser.add_argument("--v1-root", required=True)
    parser.add_argument("--v1r2-root", required=True)
    parser.add_argument("--materialization-root", required=True)
    parser.add_argument("--output", required=True)
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    output = Path(args.output).resolve()
    if output.exists():
        print("PROTOCOL_FAILURE=audit output already exists", file=sys.stderr)
        return 2
    try:
        receipt = run_audit(args)
    except Exception as error:
        receipt = {
            "schema": "msahg.on-sthgcn.causal-materializer-v1r1-real-audit-failure.v1",
            "decision": "PROTOCOL_FAILURE",
            "reason": str(error),
            "automatic_retry_performed": False,
            "model_executed": False,
            "training_performed": False,
            "recommendation_metrics_computed": False,
        }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(canonical_json_bytes(receipt))
    print("REAL_AUDIT_RECEIPT={}".format(output))
    print("DECISION={}".format(receipt["decision"]))
    return 0 if receipt["decision"] != "PROTOCOL_FAILURE" else 2


if __name__ == "__main__":
    sys.exit(main())
