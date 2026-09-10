#!/usr/bin/env python3
"""Deterministic MSAHG-on-STHGCN Marginal-Axis V1 graph materializer.

The registered V1R1 authority permits synthetic qualification only.  The real
CLI therefore requires a later, hash-bound runtime authority before it will
read public CSV material.
"""

from __future__ import print_function

import argparse
import csv
from datetime import datetime, timedelta
import hashlib
import io
import json
import math
from pathlib import Path
import struct
import subprocess
import sys
import zipfile


REGISTRATION_COMMIT = "4dd32f64440687c5f65c659b7e28b0b83b90d713"
PARENT_RESULT_COMMIT = "9bb6248b7cd8730b9c05676926f213afe3e476fc"
CONTRACT_COMMIT = "cccf03c605bb3b1d7374e34a5eac9c247ea3b48b"
MSAHG_SOURCE_COMMIT = "3d74d70c852c56adcc09d907488410be5eda2744"
STHGCN_SOURCE_COMMIT = "27b595846d29019799485985bff49f9ed02c4ade"
REGISTRY_SHA256 = "f9ff7c5ffe4affc4ccf4ff0d44dd9089274b4e416437f34219fa6b5c33ddc1ba"
SCOPE_SHA256 = "1192d00dc626f6a4eb4ab1c94807bb227c4bb68efba9948abb94959801a3c755"
CONTRACT_SHA256 = "f82fce5daac21172346a9fb788cf9675924e51497e7826324d52c85339ebc2e3"
CONTRACT_REGISTRY_SHA256 = "38c05840c16989cba0d09b21222ce705906d6ec099dc714d8d569aee67c303d8"
V1R3_PASSPORT_SHA256 = "6422bc825f4b27ea7513dc8b5b6f6ecdae3604212197eb1b5597119c60529239"
V1R3_AUDIT_SHA256 = "25e3cbda656c569ed399829243d26259aeb332ce9ad28c830243d976e1e34d9b"
V1_SOURCE_SHA256 = "288daa4ab0de251cbbb0d4d8a1735af1193d42aa0c258757443fd2a154e65f3e"
EARTH_RADIUS_KM = 6371.0088
REGION_RADIUS_KM = 10.0
GEOGRAPHY_RADIUS_KM = 2.5
LEGAL_SPLITS = ("train", "validation", "test")
AXIS_TASKS = (
    "User/0",
    "User/1",
    "Time/0",
    "Time/1",
    "POI/0",
    "POI/1",
)
TARGET_FREE_GATES = (
    "C0_AUTHORITY",
    "C1_NO_EVAL_FIT",
    "C2_PREFIX_LABEL",
    "C3_USER_RULE",
    "C4_TIME_RULE",
    "C5_SPATIAL_RULE",
    "C6_LABEL_PARTITION",
    "C7_JOINT_METADATA_ONLY",
    "C8_COLLABORATIVE",
    "C9_TEMPORAL",
    "C10_GEOGRAPHY",
    "C11_TRANSITION",
    "C12_ROUTING",
    "C13_DETERMINISM",
    "C14_CAUSAL_PERTURBATION",
    "C15_SOURCE_IMMUTABLE",
    "C16_SCORE_FREE",
    "C17_FAIL_CLOSED",
)
TASK_ROUTING = {
    "User/0": {
        "collaborative": "local",
        "temporal": "global",
        "geography": "global",
        "transition": "shared",
    },
    "User/1": {
        "collaborative": "tourist",
        "temporal": "global",
        "geography": "global",
        "transition": "shared",
    },
    "Time/0": {
        "collaborative": "global",
        "temporal": "workday",
        "geography": "global",
        "transition": "shared",
    },
    "Time/1": {
        "collaborative": "global",
        "temporal": "weekend",
        "geography": "global",
        "transition": "shared",
    },
    "POI/0": {
        "collaborative": "global",
        "temporal": "global",
        "geography": "central",
        "transition": "shared",
    },
    "POI/1": {
        "collaborative": "global",
        "temporal": "global",
        "geography": "peripheral",
        "transition": "shared",
    },
}
MSAHG_HISTORICAL_SOURCE_SHA256 = {
    "dataset.py": "9f0d8635a98af3d436ffd1fb2858f06da23311abe2cc208b4a0c93f048e74970",
    "datasets/sample.zip": "1fc176fe2e83730934724c43df0a6682bb501c81dd7ec44c1ddab27c7e78cf4c",
    "model_devide.py": "9e5c503d3e10e274ef1f28435490fd1cf88c5d2298f897be0465c16497e63bdc",
    "run.py": "f22972e0e526e777eec7f5ca8a950d780a32e54508662f423a0729073f8a742c",
    "train_nash.py": "6f62c1d82360a879a0695d6fdf5e657b0faff549cb247fa0092fbb5718449538",
    "utils.py": "b4892df839b5c2aee1c608fa54d552ebdafed6d608389cbbfd10904cb4bfdd36",
}


class CausalMaterializerError(RuntimeError):
    pass


def sha256_bytes(value):
    return hashlib.sha256(value).hexdigest()


def sha256_file(path):
    digest = hashlib.sha256()
    with open(str(path), "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json_bytes(value):
    return (
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    ).encode("utf-8")


def canonical_jsonl_bytes(rows):
    return (
        "".join(
            json.dumps(row, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
            + "\n"
            for row in rows
        )
    ).encode("utf-8")


def _git(root, *args):
    return subprocess.check_output(
        ["git", "-C", str(root)] + list(args), stderr=subprocess.STDOUT
    ).decode("utf-8").strip()


def verify_registry(registry_path):
    path = Path(registry_path).resolve()
    if sha256_file(path) != REGISTRY_SHA256:
        raise CausalMaterializerError("V1R1 implementation registry identity mismatch")
    registry = json.loads(path.read_text(encoding="utf-8"))
    if registry.get("parent_commit") != PARENT_RESULT_COMMIT:
        raise CausalMaterializerError("V1R1 parent result mismatch")
    if tuple(registry.get("target_free_gates", ())) != TARGET_FREE_GATES:
        raise CausalMaterializerError("V1R1 target-free gate sequence mismatch")
    if registry.get("format", {}).get("variant") != "MARGINAL_AXIS_V1":
        raise CausalMaterializerError("V1R1 reconstruction variant mismatch")
    return registry


def verify_frozen_repository_material(registry):
    root = Path(__file__).resolve().parents[1]
    checks = {
        registry["authorities"]["scope_path"]: SCOPE_SHA256,
        registry["authorities"]["causal_contract_path"]: CONTRACT_SHA256,
        registry["authorities"]["causal_registry_path"]: CONTRACT_REGISTRY_SHA256,
        registry["authorities"]["v1r3_result_path"]
        + "/MATERIAL_PASSPORT.json": V1R3_PASSPORT_SHA256,
        registry["authorities"]["v1r3_result_path"]
        + "/independent_audit.json": V1R3_AUDIT_SHA256,
        "reproduction/sthgcn_sample_materializer_r1.py": V1_SOURCE_SHA256,
    }
    observed = {}
    for relative, expected in checks.items():
        path = root / relative
        if not path.is_file():
            raise CausalMaterializerError("missing frozen authority: " + relative)
        actual = sha256_file(path)
        observed[relative] = actual
        if actual != expected:
            raise CausalMaterializerError("frozen authority mismatch: " + relative)
    return observed


def verify_reproduction_authority():
    root = Path(__file__).resolve().parents[1]
    head = _git(root, "rev-parse", "HEAD")
    if _git(root, "status", "--porcelain=v1", "--untracked-files=all"):
        raise CausalMaterializerError("V1R1 implementation worktree is not clean")
    if _git(root, "rev-parse", "HEAD^") != REGISTRATION_COMMIT:
        raise CausalMaterializerError("V1R1 implementation must directly follow registration")
    if _git(root, "rev-parse", REGISTRATION_COMMIT + "^") != PARENT_RESULT_COMMIT:
        raise CausalMaterializerError("V1R1 registration parent mismatch")
    if subprocess.run(
        ["git", "-C", str(root), "merge-base", "--is-ancestor", CONTRACT_COMMIT, head],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    ).returncode != 0:
        raise CausalMaterializerError("causal contract is not an ancestor")
    return {"root": root, "implementation_commit": head}


def verify_source_authorities(sthgcn_root):
    root = Path(__file__).resolve().parents[1]
    historical = {}
    for relative, expected in sorted(MSAHG_HISTORICAL_SOURCE_SHA256.items()):
        value = subprocess.check_output(
            ["git", "-C", str(root), "show", MSAHG_SOURCE_COMMIT + ":" + relative],
            stderr=subprocess.STDOUT,
        )
        actual = sha256_bytes(value)
        historical[relative] = actual
        if actual != expected:
            raise CausalMaterializerError("frozen MSAHG source mismatch: " + relative)
    sthgcn = Path(sthgcn_root).resolve()
    if _git(sthgcn, "rev-parse", "HEAD") != STHGCN_SOURCE_COMMIT:
        raise CausalMaterializerError("STHGCN source commit mismatch")
    if _git(sthgcn, "status", "--porcelain=v1", "--untracked-files=all"):
        raise CausalMaterializerError("STHGCN source worktree is not clean")
    return {"msahg_historical": historical, "sthgcn_commit": STHGCN_SOURCE_COMMIT}


def median(values):
    ordered = sorted(float(value) for value in values)
    if not ordered or not all(math.isfinite(value) for value in ordered):
        raise CausalMaterializerError("median input is empty or non-finite")
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / 2.0


def haversine_km(left, right):
    lat1, lon1 = left
    lat2, lon2 = right
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    value = (
        math.sin(dphi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2
    )
    value = min(1.0, max(0.0, value))
    return 2.0 * EARTH_RADIUS_KM * math.asin(math.sqrt(value))


def _npy_bytes(flat_values, shape, dtype):
    descriptors = {"int64": ("<i8", "q"), "uint8": ("|u1", "B"), "float64": ("<f8", "d")}
    if dtype not in descriptors:
        raise CausalMaterializerError("unsupported NPY dtype: " + str(dtype))
    descriptor, code = descriptors[dtype]
    expected = 1
    for size in shape:
        expected *= int(size)
    values = list(flat_values)
    if len(values) != expected:
        raise CausalMaterializerError("NPY value count mismatch")
    shape_text = "({},{})".format(shape[0], shape[1]) if len(shape) == 2 else "({},)".format(shape[0])
    header = "{'descr': '%s', 'fortran_order': False, 'shape': %s, }" % (
        descriptor,
        shape_text,
    )
    prefix_length = 10
    padding = (64 - ((prefix_length + len(header) + 1) % 64)) % 64
    header_bytes = (header + " " * padding + "\n").encode("latin-1")
    if len(header_bytes) >= 65536:
        raise CausalMaterializerError("NPY header too large")
    body = bytearray()
    packer = struct.Struct("<" + code)
    for value in values:
        body.extend(packer.pack(value))
    return b"\x93NUMPY" + b"\x01\x00" + struct.pack("<H", len(header_bytes)) + header_bytes + bytes(body)


def make_sparse(shape, coordinates, value_dtype="uint8", values=None):
    rows, columns = int(shape[0]), int(shape[1])
    unique = sorted(set((int(row), int(column)) for row, column in coordinates))
    for row, column in unique:
        if row < 0 or row >= rows or column < 0 or column >= columns:
            raise CausalMaterializerError("sparse coordinate outside shape")
    if values is None:
        payload = [1] * len(unique)
    else:
        if len(values) != len(coordinates):
            raise CausalMaterializerError("explicit sparse value count mismatch")
        value_map = {}
        for coordinate, value in zip(coordinates, values):
            key = (int(coordinate[0]), int(coordinate[1]))
            if key in value_map:
                raise CausalMaterializerError("normalized sparse coordinate duplicated")
            value_map[key] = float(value)
        payload = [value_map[key] for key in unique]
    return {
        "shape": (rows, columns),
        "coordinates": unique,
        "values": payload,
        "value_dtype": value_dtype,
    }


def transpose_sparse(matrix):
    return make_sparse(
        (matrix["shape"][1], matrix["shape"][0]),
        [(column, row) for row, column in matrix["coordinates"]],
        matrix["value_dtype"],
        list(matrix["values"]),
    )


def row_normalize(matrix):
    row_sums = [0.0] * matrix["shape"][0]
    for (row, _), value in zip(matrix["coordinates"], matrix["values"]):
        row_sums[row] += float(value)
    values = [
        float(value) / row_sums[row] if row_sums[row] > 0.0 else 0.0
        for (row, _), value in zip(matrix["coordinates"], matrix["values"])
    ]
    return make_sparse(
        matrix["shape"],
        list(matrix["coordinates"]),
        "float64",
        values,
    )


def serialize_sparse(matrix):
    coordinates = matrix["coordinates"]
    row_values = [row for row, _ in coordinates]
    column_values = [column for _, column in coordinates]
    entries = (
        ("indices.npy", _npy_bytes(row_values + column_values, (2, len(coordinates)), "int64")),
        ("values.npy", _npy_bytes(matrix["values"], (len(coordinates),), matrix["value_dtype"])),
        ("shape.npy", _npy_bytes(matrix["shape"], (2,), "int64")),
    )
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, mode="w", compression=zipfile.ZIP_STORED) as archive:
        for name, payload in entries:
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_STORED
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, payload)
    return stream.getvalue()


def _parse_timestamp(value):
    try:
        return datetime.strptime(str(value), "%Y-%m-%d %H:%M:%S")
    except ValueError as error:
        raise CausalMaterializerError("invalid local timestamp: " + str(value)) from error


def _graph_index(encoded, encoding, field):
    item = encoding[field]
    offset = int(item["offset"])
    size = len(item["classes"])
    value = int(encoded) - offset
    if value < 0 or value >= size:
        raise CausalMaterializerError("unknown train-fitted {} id".format(field))
    return value


def canonicalize_records(rows, encoding):
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
    result = []
    ordinals = set()
    identities = set()
    for raw in rows:
        if not required.issubset(set(raw)):
            raise CausalMaterializerError("record is missing registered columns")
        ordinal = int(raw["source_ordinal"])
        identity = (int(raw["check_ins_id"]), ordinal)
        if ordinal in ordinals or identity in identities:
            raise CausalMaterializerError("duplicate stable record identity")
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
            raise CausalMaterializerError("invalid coordinate")
        split = str(raw["SplitTag"])
        original_split = str(raw["OriginalSplitTag"])
        if split not in LEGAL_SPLITS + ("ignore",) or original_split not in LEGAL_SPLITS:
            raise CausalMaterializerError("illegal split provenance")
        record = {
            "check_ins_id": int(raw["check_ins_id"]),
            "source_ordinal": ordinal,
            "trajectory_id": str(raw["pseudo_session_trajectory_id"]),
            "trajectory_rank": int(raw["pseudo_session_trajectory_rank"]),
            "raw_trajectory_id": str(raw["raw_trajectory_id"]),
            "user_encoded": int(raw["UserId"]),
            "poi_encoded": int(raw["PoiId"]),
            "category_name": str(raw["PoiCategoryName"]),
            "latitude": latitude,
            "longitude": longitude,
            "timestamp": _parse_timestamp(raw["UTCTimeOffset"]),
            "split": split,
            "original_split": original_split,
        }
        for encoded_name, index_name, field in (
            ("user_encoded", "user_index", "UserId"),
            ("poi_encoded", "poi_index", "PoiId"),
        ):
            try:
                record[index_name] = _graph_index(record[encoded_name], encoding, field)
            except CausalMaterializerError:
                # An ignored non-training record may contain a padding or
                # otherwise unseen ID.  Keep it representable so that an
                # eligible target can later fail specifically when such a
                # record is its immediate prefix.  Training and target rows
                # remain strictly train-vocabulary bound here.
                if original_split == "train" or split in LEGAL_SPLITS:
                    raise
                record[index_name] = None
        result.append(record)
    return sorted(result, key=lambda item: item["source_ordinal"])


def fit_user_labels(train_records, user_count):
    totals = [0] * user_count
    hotels = [0] * user_count
    for record in train_records:
        user = record["user_index"]
        totals[user] += 1
        if record["category_name"] == "Hotel":
            hotels[user] += 1
    labels = {}
    shares = {}
    for user in range(user_count):
        if totals[user] == 0:
            raise CausalMaterializerError("train-known user has no training event")
        share = float(hotels[user]) / float(totals[user])
        labels[user] = 1 if share > 0.05 else 0
        shares[user] = share
    return labels, shares


def fit_poi_coordinates(train_records, poi_count):
    values = {poi: {"lat": [], "lon": []} for poi in range(poi_count)}
    for record in train_records:
        item = values[record["poi_index"]]
        item["lat"].append(record["latitude"])
        item["lon"].append(record["longitude"])
    coordinates = {}
    for poi in range(poi_count):
        if not values[poi]["lat"]:
            raise CausalMaterializerError("train-known POI has no training coordinate")
        coordinates[poi] = (
            median(values[poi]["lat"]),
            median(values[poi]["lon"]),
        )
    center = (
        median([coordinates[poi][0] for poi in range(poi_count)]),
        median([coordinates[poi][1] for poi in range(poi_count)]),
    )
    labels = {
        poi: 0 if haversine_km(coordinates[poi], center) <= REGION_RADIUS_KM else 1
        for poi in range(poi_count)
    }
    return coordinates, center, labels


def half_hour_slot(timestamp):
    return int(2 * timestamp.hour + timestamp.minute // 30)


def _previous_by_trajectory(records):
    groups = {}
    for record in records:
        groups.setdefault(record["trajectory_id"], []).append(record)
    previous = {}
    for trajectory in groups.values():
        ordered = sorted(trajectory, key=lambda item: (item["trajectory_rank"], item["source_ordinal"]))
        seen_ranks = set()
        for index, record in enumerate(ordered):
            if record["trajectory_rank"] in seen_ranks:
                raise CausalMaterializerError("duplicate trajectory rank")
            seen_ranks.add(record["trajectory_rank"])
            if index:
                candidate = ordered[index - 1]
                if candidate["trajectory_rank"] + 1 == record["trajectory_rank"]:
                    previous[record["source_ordinal"]] = candidate
    return previous


def build_scenario_rows(records, user_labels, poi_labels):
    previous = _previous_by_trajectory(records)
    rows = []
    for record in records:
        if record["split"] not in LEGAL_SPLITS:
            continue
        prefix = previous.get(record["source_ordinal"])
        if prefix is None:
            raise CausalMaterializerError("eligible target has no immediate observed prefix")
        if prefix["poi_index"] is None:
            raise CausalMaterializerError("eligible target prefix POI is not train-known")
        if record["user_index"] is None or record["user_index"] not in user_labels:
            raise CausalMaterializerError("eligible target user is not train-known")
        user_group = user_labels[record["user_index"]]
        time_group = 0 if prefix["timestamp"].weekday() <= 4 else 1
        poi_group = poi_labels[prefix["poi_index"]]
        tasks = [
            "User/{}".format(user_group),
            "Time/{}".format(time_group),
            "POI/{}".format(poi_group),
        ]
        rows.append(
            {
                "check_ins_id": record["check_ins_id"],
                "source_ordinal": record["source_ordinal"],
                "raw_trajectory_id": record["raw_trajectory_id"],
                "SplitTag": record["split"],
                "user_graph_index": record["user_index"],
                "prefix_poi_graph_index": prefix["poi_index"],
                "prefix_source_ordinal": prefix["source_ordinal"],
                "UserGroup": user_group,
                "UserLabel": "local" if user_group == 0 else "tourist",
                "TimeGroup": time_group,
                "TimeLabel": "workday" if time_group == 0 else "weekend",
                "POIGroup": poi_group,
                "POILabel": "central" if poi_group == 0 else "peripheral",
                "joint_triple": "{}|{}|{}".format(user_group, time_group, poi_group),
                "marginal_tasks": tasks,
            }
        )
    return sorted(rows, key=lambda item: item["source_ordinal"])


def _binary_graph(shape, coordinates):
    return make_sparse(shape, coordinates, "uint8")


def _geography_coordinates(poi_coordinates):
    if not poi_coordinates:
        return []
    minimum_cosine = min(max(1e-12, abs(math.cos(math.radians(value[0])))) for value in poi_coordinates.values())
    latitude_step = GEOGRAPHY_RADIUS_KM / 111.0
    longitude_step = GEOGRAPHY_RADIUS_KM / (111.0 * minimum_cosine)
    buckets = {}
    positions = {}
    for poi, (latitude, longitude) in sorted(poi_coordinates.items()):
        cell = (
            int(math.floor((latitude + 90.0) / latitude_step)),
            int(math.floor((longitude + 180.0) / longitude_step)),
        )
        positions[poi] = cell
        buckets.setdefault(cell, []).append(poi)
    edges = set()
    for poi in sorted(poi_coordinates):
        cell = positions[poi]
        candidates = []
        for delta_lat in range(-2, 3):
            for delta_lon in range(-2, 3):
                candidates.extend(buckets.get((cell[0] + delta_lat, cell[1] + delta_lon), ()))
        for other in sorted(set(candidates)):
            if other < poi:
                continue
            if haversine_km(poi_coordinates[poi], poi_coordinates[other]) <= GEOGRAPHY_RADIUS_KM:
                edges.add((poi, other))
                edges.add((other, poi))
    return sorted(edges)


def build_graphs(train_records, user_count, poi_count, user_labels, poi_coordinates, poi_labels):
    graphs = {}
    collaborative = {
        "global": set(),
        "local": set(),
        "tourist": set(),
    }
    temporal_poi = {"global": set(), "workday": set(), "weekend": set()}
    temporal_user = {"global": set(), "workday": set(), "weekend": set()}
    for record in train_records:
        user = record["user_index"]
        poi = record["poi_index"]
        slot = half_hour_slot(record["timestamp"])
        time_name = "workday" if record["timestamp"].weekday() <= 4 else "weekend"
        user_name = "local" if user_labels[user] == 0 else "tourist"
        collaborative["global"].add((poi, user))
        collaborative[user_name].add((poi, user))
        temporal_poi["global"].add((slot, poi))
        temporal_poi[time_name].add((slot, poi))
        temporal_user["global"].add((slot, user))
        temporal_user[time_name].add((slot, user))

    for name in ("global", "local", "tourist"):
        raw = _binary_graph((poi_count, user_count), collaborative[name])
        graphs["collaborative_{}_raw".format(name)] = raw
        graphs["collaborative_{}_poi_to_user".format(name)] = row_normalize(transpose_sparse(raw))
        graphs["collaborative_{}_user_to_poi".format(name)] = row_normalize(raw)
    for name in ("global", "workday", "weekend"):
        raw_poi = _binary_graph((48, poi_count), temporal_poi[name])
        raw_user = _binary_graph((48, user_count), temporal_user[name])
        graphs["temporal_poi_{}_raw".format(name)] = raw_poi
        graphs["temporal_poi_{}_time_to_poi".format(name)] = row_normalize(raw_poi)
        graphs["temporal_poi_{}_poi_to_time".format(name)] = row_normalize(transpose_sparse(raw_poi))
        graphs["temporal_user_{}_raw".format(name)] = raw_user
        graphs["temporal_user_{}_time_to_user".format(name)] = row_normalize(raw_user)
        graphs["temporal_user_{}_user_to_time".format(name)] = row_normalize(transpose_sparse(raw_user))

    geography_global = set(_geography_coordinates(poi_coordinates))
    geography_groups = {
        "central": set(
            edge for edge in geography_global if poi_labels[edge[0]] == 0 and poi_labels[edge[1]] == 0
        ),
        "peripheral": set(
            edge for edge in geography_global if poi_labels[edge[0]] == 1 and poi_labels[edge[1]] == 1
        ),
    }
    for name, coordinates in (
        ("global", geography_global),
        ("central", geography_groups["central"]),
        ("peripheral", geography_groups["peripheral"]),
    ):
        raw = _binary_graph((poi_count, poi_count), coordinates)
        graphs["geography_{}_raw".format(name)] = raw
        graphs["geography_{}_poi_to_poi".format(name)] = row_normalize(raw)

    transition_pairs = set()
    groups = {}
    for record in train_records:
        groups.setdefault(record["trajectory_id"], []).append(record)
    for trajectory in groups.values():
        ordered = sorted(trajectory, key=lambda item: (item["trajectory_rank"], item["source_ordinal"]))
        for left, right in zip(ordered, ordered[1:]):
            if left["trajectory_rank"] + 1 == right["trajectory_rank"]:
                transition_pairs.add((left["poi_index"], right["poi_index"]))
    transition_pairs = sorted(transition_pairs)
    source_coordinates = [(source, edge) for edge, (source, _) in enumerate(transition_pairs)]
    target_coordinates = [(target, edge) for edge, (_, target) in enumerate(transition_pairs)]
    source_raw = _binary_graph((poi_count, len(transition_pairs)), source_coordinates)
    target_raw = _binary_graph((poi_count, len(transition_pairs)), target_coordinates)
    graphs["transition_source_raw"] = source_raw
    graphs["transition_target_raw"] = target_raw
    graphs["transition_source_read"] = row_normalize(transpose_sparse(source_raw))
    graphs["transition_target_write"] = row_normalize(target_raw)
    return graphs, transition_pairs


def build_group_support(scenario_rows):
    support = {}
    for split in LEGAL_SPLITS:
        rows = [row for row in scenario_rows if row["SplitTag"] == split]
        marginal = {}
        for task in AXIS_TASKS:
            members = [row for row in rows if task in row["marginal_tasks"]]
            marginal[task] = {
                "targets": len(members),
                "distinct_users": len(set(row["user_graph_index"] for row in members)),
            }
        joint = {}
        for user_group in (0, 1):
            for time_group in (0, 1):
                for poi_group in (0, 1):
                    key = "{}|{}|{}".format(user_group, time_group, poi_group)
                    members = [row for row in rows if row["joint_triple"] == key]
                    joint[key] = {
                        "targets": len(members),
                        "distinct_users": len(set(row["user_graph_index"] for row in members)),
                    }
        support[split] = {"marginal": marginal, "joint_cells": joint}
    return support


def build_material(rows, encoding):
    records = canonicalize_records(rows, encoding)
    train_records = [record for record in records if record["original_split"] == "train"]
    user_count = len(encoding["UserId"]["classes"])
    poi_count = len(encoding["PoiId"]["classes"])
    user_labels, hotel_shares = fit_user_labels(train_records, user_count)
    poi_coordinates, center, poi_labels = fit_poi_coordinates(train_records, poi_count)
    scenarios = build_scenario_rows(records, user_labels, poi_labels)
    graphs, transition_pairs = build_graphs(
        train_records,
        user_count,
        poi_count,
        user_labels,
        poi_coordinates,
        poi_labels,
    )
    graph_payloads = {name: serialize_sparse(matrix) for name, matrix in sorted(graphs.items())}
    graph_manifest = {
        "schema": "msahg.on-sthgcn.causal-graph-manifest.v1",
        "variant": "MARGINAL_AXIS_V1",
        "user_count": user_count,
        "poi_count": poi_count,
        "time_slot_count": 48,
        "user_encoded_offset": int(encoding["UserId"]["offset"]),
        "poi_encoded_offset": int(encoding["PoiId"]["offset"]),
        "transition_pairs": [list(pair) for pair in transition_pairs],
        "graphs": {
            name: {
                "file": "graphs/{}.npz".format(name),
                "shape": list(graphs[name]["shape"]),
                "index_dtype": "int64",
                "value_dtype": graphs[name]["value_dtype"],
                "nnz": len(graphs[name]["coordinates"]),
                "sha256": sha256_bytes(graph_payloads[name]),
            }
            for name in sorted(graphs)
        },
        "task_routing": TASK_ROUTING,
        "joint_composite_forward": False,
    }
    center_receipt = {
        "schema": "msahg.on-sthgcn.activity-center.v1",
        "method": "coordinate-wise median over unique train-known POI median coordinates",
        "latitude_binary64_decimal": repr(center[0]),
        "longitude_binary64_decimal": repr(center[1]),
        "earth_radius_km": EARTH_RADIUS_KM,
        "scenario_radius_km": REGION_RADIUS_KM,
        "geography_radius_km": GEOGRAPHY_RADIUS_KM,
        "poi_coordinates": {
            str(poi): {
                "latitude_binary64_decimal": repr(poi_coordinates[poi][0]),
                "longitude_binary64_decimal": repr(poi_coordinates[poi][1]),
                "group": poi_labels[poi],
            }
            for poi in range(poi_count)
        },
    }
    support = build_group_support(scenarios)
    artifacts = {
        "scenario_labels.jsonl": canonical_jsonl_bytes(scenarios),
        "activity_center.json": canonical_json_bytes(center_receipt),
        "group_support.json": canonical_json_bytes(
            {
                "schema": "msahg.on-sthgcn.group-support.v1",
                "marginal_tasks": list(AXIS_TASKS),
                "joint_cells_are_metadata_only": True,
                "support": support,
            }
        ),
        "graph_manifest.json": canonical_json_bytes(graph_manifest),
    }
    for name, payload in sorted(graph_payloads.items()):
        artifacts["graphs/{}.npz".format(name)] = payload
    train_derived_names = ["activity_center.json", "graph_manifest.json"] + sorted(
        name for name in artifacts if name.startswith("graphs/")
    )
    fingerprint = hashlib.sha256()
    for name in train_derived_names:
        fingerprint.update(name.encode("utf-8") + b"\0" + artifacts[name])
    return {
        "records": records,
        "train_records": train_records,
        "scenario_rows": scenarios,
        "user_labels": user_labels,
        "hotel_shares": hotel_shares,
        "poi_coordinates": poi_coordinates,
        "poi_labels": poi_labels,
        "activity_center": center,
        "graphs": graphs,
        "transition_pairs": transition_pairs,
        "group_support": support,
        "graph_manifest": graph_manifest,
        "artifacts": artifacts,
        "train_derived_fingerprint": fingerprint.hexdigest(),
    }


def load_real_rows(sample_csv, provenance_csv):
    with open(str(sample_csv), "r", encoding="utf-8", newline="") as handle:
        sample = list(csv.DictReader(handle))
    with open(str(provenance_csv), "r", encoding="utf-8", newline="") as handle:
        provenance = list(csv.DictReader(handle))
    if len(sample) != len(provenance):
        raise CausalMaterializerError("sample/provenance row count mismatch")
    rows = []
    for left, right in zip(sample, provenance):
        for field in ("check_ins_id", "source_ordinal", "raw_trajectory_id", "SplitTag"):
            if str(left[field]) != str(right[field]):
                raise CausalMaterializerError("sample/provenance identity mismatch: " + field)
        merged = dict(left)
        merged["OriginalSplitTag"] = right["OriginalSplitTag"]
        rows.append(merged)
    return rows


def verify_runtime_authority(path, expected_sha256, implementation_commit):
    authority_path = Path(path).resolve()
    if sha256_file(authority_path) != expected_sha256:
        raise CausalMaterializerError("real runtime authority identity mismatch")
    authority = json.loads(authority_path.read_text(encoding="utf-8"))
    if (
        authority.get("schema")
        != "msahg.on-sthgcn.causal-materializer-real-runtime.v1"
        or authority.get("implementation_commit") != implementation_commit
        or authority.get("registry_sha256") != REGISTRY_SHA256
        or authority.get("real_materialization_authorized") is not True
    ):
        raise CausalMaterializerError("real materialization is not authorized")
    return authority


def write_material(output_dir, material, dataset, input_hashes, implementation_commit):
    output = Path(output_dir).resolve()
    if output.exists():
        raise CausalMaterializerError("output directory already exists")
    output.mkdir(parents=True, exist_ok=False)
    for relative, payload in sorted(material["artifacts"].items()):
        path = output / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(str(path), "wb") as handle:
            handle.write(payload)
    receipt = {
        "schema": "msahg.on-sthgcn.causal-materialization-receipt.v1",
        "dataset": dataset,
        "decision": "MATERIALIZED_PENDING_INDEPENDENT_AUDIT",
        "implementation_commit": implementation_commit,
        "registry_sha256": REGISTRY_SHA256,
        "input_hashes": input_hashes,
        "rows": len(material["records"]),
        "eligible_targets": len(material["scenario_rows"]),
        "train_derived_fingerprint": material["train_derived_fingerprint"],
        "scenario_labels_materialized": True,
        "activity_center_materialized": True,
        "graph_materialized": True,
        "model_executed": False,
        "training_performed": False,
        "inference_performed": False,
        "loss_computed": False,
        "checkpoint_accessed": False,
        "recommendation_metrics_computed": False,
        "target_evaluation_performed": False,
    }
    receipt_bytes = canonical_json_bytes(receipt)
    with open(str(output / "materialization_receipt.json"), "wb") as handle:
        handle.write(receipt_bytes)
    names = sorted(
        str(path.relative_to(output))
        for path in output.rglob("*")
        if path.is_file()
    )
    with open(str(output / "SHA256SUMS"), "w", encoding="utf-8", newline="\n") as handle:
        for name in names:
            handle.write("{}  {}\n".format(sha256_file(output / name), name))
    return receipt


def synthetic_fixture():
    coordinates = {
        0: (0.0, -0.01),
        1: (0.0, 0.01),
        2: (0.0, -0.20),
        3: (0.0, 0.20),
    }
    rows = []
    ordinal = 0
    start = datetime(2024, 1, 1, 0, 0, 0)
    for user in range(4):
        for index in range(20):
            poi = (index + user) % 4
            timestamp = start + timedelta(hours=12 * index)
            hotel_limit = 1 if user < 2 else 2
            rows.append(
                {
                    "check_ins_id": ordinal,
                    "source_ordinal": ordinal,
                    "pseudo_session_trajectory_id": "train-{}".format(user),
                    "pseudo_session_trajectory_rank": index + 1,
                    "raw_trajectory_id": "train-{}".format(user),
                    "UserId": user,
                    "PoiId": poi,
                    "PoiCategoryName": "Hotel" if index < hotel_limit else "Other",
                    "Latitude": coordinates[poi][0],
                    "Longitude": coordinates[poi][1],
                    "UTCTimeOffset": timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                    "SplitTag": "ignore" if index == 0 else "train",
                    "OriginalSplitTag": "train",
                }
            )
            ordinal += 1
    combinations = [
        (0, 0, 0),
        (0, 0, 1),
        (0, 1, 0),
        (0, 1, 1),
        (1, 0, 0),
        (1, 0, 1),
        (1, 1, 0),
        (1, 1, 1),
    ]
    for index, (user_group, time_group, poi_group) in enumerate(combinations):
        user = user_group * 2
        poi = 0 if poi_group == 0 else 2
        prefix_time = datetime(2024, 1, 3, 9, 0, 0) if time_group == 0 else datetime(2024, 1, 6, 9, 0, 0)
        split = "validation" if index < 4 else "test"
        trajectory = "eval-{}".format(index)
        for rank in (1, 2):
            event_poi = poi if rank == 1 else (poi + 1) % 4
            rows.append(
                {
                    "check_ins_id": ordinal,
                    "source_ordinal": ordinal,
                    "pseudo_session_trajectory_id": trajectory,
                    "pseudo_session_trajectory_rank": rank,
                    "raw_trajectory_id": trajectory,
                    "UserId": user,
                    "PoiId": event_poi,
                    "PoiCategoryName": "Other",
                    "Latitude": coordinates[event_poi][0],
                    "Longitude": coordinates[event_poi][1],
                    "UTCTimeOffset": (prefix_time + timedelta(hours=rank - 1)).strftime("%Y-%m-%d %H:%M:%S"),
                    "SplitTag": "ignore" if rank == 1 else split,
                    "OriginalSplitTag": split,
                }
            )
            ordinal += 1
    encoding = {
        "UserId": {"classes": ["u0", "u1", "u2", "u3"], "offset": 0, "padding_id": 4},
        "PoiId": {"classes": ["p0", "p1", "p2", "p3"], "offset": 0, "padding_id": 4},
    }
    return rows, encoding


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", required=True)
    parser.add_argument("--runtime-authority", required=True)
    parser.add_argument("--runtime-authority-sha256", required=True)
    parser.add_argument("--dataset", choices=("nyc", "tky"), required=True)
    parser.add_argument("--sample-csv", required=True)
    parser.add_argument("--label-encoding", required=True)
    parser.add_argument("--provenance-sidecar", required=True)
    parser.add_argument("--output-dir", required=True)
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    registry = verify_registry(args.registry)
    runtime = verify_reproduction_authority()
    verify_frozen_repository_material(registry)
    verify_runtime_authority(
        args.runtime_authority,
        args.runtime_authority_sha256,
        runtime["implementation_commit"],
    )
    expected = registry["frozen_real_inputs"][args.dataset]
    input_paths = {
        "sample.csv": Path(args.sample_csv).resolve(),
        "label_encoding.json": Path(args.label_encoding).resolve(),
        "record_split_provenance.csv": Path(args.provenance_sidecar).resolve(),
    }
    input_hashes = {name: sha256_file(path) for name, path in input_paths.items()}
    for name, actual in input_hashes.items():
        if actual != expected[name]:
            raise CausalMaterializerError("real input identity mismatch: " + name)
    rows = load_real_rows(input_paths["sample.csv"], input_paths["record_split_provenance.csv"])
    if len(rows) != int(expected["rows"]):
        raise CausalMaterializerError("real input row count mismatch")
    encoding = json.loads(input_paths["label_encoding.json"].read_text(encoding="utf-8"))
    first = build_material(rows, encoding)
    second = build_material(rows, encoding)
    if first["artifacts"] != second["artifacts"]:
        raise CausalMaterializerError("two-run materialization is not byte deterministic")
    receipt = write_material(
        args.output_dir,
        first,
        args.dataset,
        input_hashes,
        runtime["implementation_commit"],
    )
    print("MATERIALIZATION={}".format(receipt["decision"]))
    print("OUTPUT={}".format(Path(args.output_dir).resolve()))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as error:
        print("PROTOCOL_FAILURE={}".format(error), file=sys.stderr)
        sys.exit(2)
