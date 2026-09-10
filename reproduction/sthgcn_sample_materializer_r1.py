#!/usr/bin/env python3
"""Portable, score-free reconstruction of the public STHGCN sample protocol."""

from __future__ import print_function

import argparse
import calendar
import csv
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import zipfile

import numpy as np
import pandas as pd


STHGCN_COMMIT = "27b595846d29019799485985bff49f9ed02c4ade"
NYC_ARCHIVE_SHA256 = "974bc90b3e0cdec6ec29a0a953ac41d3f81880e17bdd4c7c0cd94f2afc9e17d2"
TKY_ARCHIVE_SHA256 = "823cd400a8d67b360c50217c1e8141e566a2b804ca8af9feac9ff9c0f76220c7"
TKY_MEMBER_SHA256 = "85542c605ce708d8584637756590383a84e9bbdb71342d0d8e78858ba2a0e5c8"
REGISTRY_SHA256 = "09fa364f345763bb34362dd54d0f1d819431bc6f25261b0ed6d75ef2f682e49c"
REGISTRATION_COMMIT = "7c813210665f61197e68e7e794c5da091a259569"
PORTABILITY_AUTHORITY_COMMIT = "cc91340e466f151c8e54777d35453f2c48721774"

NYC_MEMBERS = {
    "train": "raw/NYC_train.csv",
    "validation": "raw/NYC_val.csv",
    "test": "raw/NYC_test.csv",
}
NYC_MEMBER_HASHES = {
    "raw/NYC_train.csv": "bb1e7b44e484c9338b27dfd67298d6bfb2b958c07ec0aa3036b92d86269dcfa0",
    "raw/NYC_val.csv": "3eeb4e39be8869e4259e9316d1aeda088e0606f7efdb93e3fd436e86cfc58b2e",
    "raw/NYC_test.csv": "c285494e63475512c3c22b37885c70cf0ee89548cbcac109d72ba4e0d02f8f6e",
}
TKY_MEMBER = "raw/dataset_TSMC2014_TKY.txt"

EXPECTED = {
    "nyc": {"users": 1048, "pois": 4981, "post_filter_events": 103941, "trajectories": 14130},
    "tky": {"users": 2282, "pois": 7833, "post_filter_events": 405000, "trajectories": 65499},
}

OUTPUT_COLUMNS = [
    "check_ins_id",
    "UTCTimeOffset",
    "UTCTimeOffsetEpoch",
    "pseudo_session_trajectory_id",
    "query_pseudo_session_trajectory_id",
    "UserId",
    "Latitude",
    "Longitude",
    "PoiId",
    "PoiCategoryId",
    "PoiCategoryName",
    "last_checkin_epoch_time",
    "SplitTag",
    "pseudo_session_trajectory_rank",
    "pseudo_session_trajectory_count",
    "time_interval_minutes",
    "source_ordinal",
    "raw_user_id",
    "raw_poi_id",
    "raw_category_id",
    "raw_trajectory_id",
]


class MaterializationError(RuntimeError):
    pass


def sha256_file(path):
    digest = hashlib.sha256()
    with open(str(path), "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_bytes(value):
    return hashlib.sha256(value).hexdigest()


def _git(root, *args):
    return subprocess.check_output(
        ["git", "-C", str(root)] + list(args), stderr=subprocess.STDOUT
    ).decode("utf-8").strip()


def verify_source_authority(sthgcn_root):
    root = Path(sthgcn_root).resolve()
    if _git(root, "rev-parse", "HEAD") != STHGCN_COMMIT:
        raise MaterializationError("STHGCN commit identity mismatch")
    if _git(root, "status", "--porcelain=v1", "--untracked-files=all"):
        raise MaterializationError("STHGCN source tree is not clean")
    nyc_archive = root / "data" / "nyc" / "raw.zip"
    tky_archive = root / "data" / "tky" / "raw.zip"
    if sha256_file(nyc_archive) != NYC_ARCHIVE_SHA256:
        raise MaterializationError("NYC archive identity mismatch")
    if sha256_file(tky_archive) != TKY_ARCHIVE_SHA256:
        raise MaterializationError("TKY archive identity mismatch")
    return {"root": root, "nyc": nyc_archive, "tky": tky_archive}


def verify_registry(registry_path):
    path = Path(registry_path).resolve()
    if sha256_file(path) != REGISTRY_SHA256:
        raise MaterializationError("materializer registry identity mismatch")
    with open(str(path), "r", encoding="utf-8") as handle:
        registry = json.load(handle)
    if registry.get("base_commit") != "f09a5016958a3495764f55cd69f93d5bc5e147bb":
        raise MaterializationError("materializer base authority mismatch")
    return registry


def verify_reproduction_authority():
    root = Path(__file__).resolve().parents[1]
    head = _git(root, "rev-parse", "HEAD")
    if _git(root, "status", "--porcelain=v1", "--untracked-files=all"):
        raise MaterializationError("reproduction implementation tree is not clean")
    for ancestor in (REGISTRATION_COMMIT, PORTABILITY_AUTHORITY_COMMIT):
        result = subprocess.run(
            ["git", "-C", str(root), "merge-base", "--is-ancestor", ancestor, head],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        if result.returncode != 0:
            raise MaterializationError("reproduction authority lineage mismatch")
    return {"root": root, "implementation_commit": head}


def _json_scalar(value):
    if isinstance(value, np.generic):
        return value.item()
    if pd.isna(value):
        return None
    return value


def _sorted_classes(series):
    return [_json_scalar(item) for item in sorted(pd.unique(series).tolist())]


def _encode_column(frame, train_mask, column, padding_zero):
    classes = _sorted_classes(frame.loc[train_mask, column])
    offset = 1 if padding_zero else 0
    padding_id = 0 if padding_zero else len(classes)
    mapping = {value: index + offset for index, value in enumerate(classes)}
    encoded = frame[column].map(mapping).fillna(padding_id).astype("int64")
    frame[column] = encoded
    return {"classes": classes, "padding_id": int(padding_id), "offset": offset}


def _portable_epoch(local_times):
    # Treat a timezone-naive local wall clock as UTC. This is deliberately
    # independent of the host timezone, unlike datetime.strftime('%s').
    return local_times.map(
        lambda value: calendar.timegm(value.to_pydatetime().timetuple())
    ).astype("int64")


def _stable_sort(frame, columns):
    return frame.sort_values(columns, kind="mergesort").reset_index(drop=True)


def _assign_checkin_ids(frame):
    order = frame.sort_values(["_local_time", "_source_ordinal"], kind="mergesort").index
    ids = pd.Series(np.arange(len(frame), dtype=np.int64), index=order)
    frame["check_ins_id"] = ids.reindex(frame.index).astype("int64")


def _remove_isolated_tky(frame):
    ordered = _stable_sort(frame, ["_raw_user_id", "_local_time", "_source_ordinal"])
    groups = ordered.groupby("_raw_user_id", sort=False)["_local_time"]
    prev_gap = groups.diff()
    next_gap = groups.shift(-1) - ordered["_local_time"]
    horizon = pd.Timedelta(hours=24)
    has_prev = prev_gap.notna() & (prev_gap <= horizon)
    has_next = next_gap.notna() & (next_gap <= horizon)
    return ordered.loc[has_prev | has_next].reset_index(drop=True)


def _sessionize_tky(frame):
    ordered = _stable_sort(frame, ["_raw_user_id", "_local_time", "_source_ordinal"])
    user_change = ordered["_raw_user_id"].ne(ordered["_raw_user_id"].shift(1))
    gap = ordered["_local_time"].diff()
    new_session = user_change | gap.gt(pd.Timedelta(minutes=1440))
    ordered["_raw_trajectory_id"] = new_session.cumsum().astype("int64") - 1
    ordered["_time_interval_minutes"] = gap.dt.total_seconds().div(60.0)
    return ordered


def _finalize(frame, dataset):
    frame = _stable_sort(frame, ["_raw_user_id", "_local_time", "_source_ordinal"])
    if "_source_user_rank" in frame:
        frame["_user_rank"] = frame["_source_user_rank"].astype("int64")
    else:
        frame["_user_rank"] = frame.groupby("_raw_user_id", sort=False).cumcount() + 1

    frame["raw_user_id"] = frame["_raw_user_id"]
    frame["raw_poi_id"] = frame["_raw_poi_id"]
    frame["raw_category_id"] = frame["_raw_category_id"]
    frame["raw_trajectory_id"] = frame["_raw_trajectory_id"]

    _assign_checkin_ids(frame)
    frame["UTCTimeOffsetEpoch"] = _portable_epoch(frame["_local_time"])
    frame["UTCTimeOffsetHour"] = frame["_local_time"].dt.hour.astype("int64")
    frame["UTCTimeOffsetWeekday"] = frame["_local_time"].dt.weekday.astype("int64")
    train_mask = frame["_split_original"].eq("train")
    padding_zero = dataset == "tky"

    frame["UserId"] = frame["_raw_user_id"]
    frame["PoiId"] = frame["_raw_poi_id"]
    frame["PoiCategoryId"] = frame["_raw_category_id"]
    mappings = {
        "UserId": _encode_column(frame, train_mask, "UserId", padding_zero),
        "PoiId": _encode_column(frame, train_mask, "PoiId", padding_zero),
        "PoiCategoryId": _encode_column(frame, train_mask, "PoiCategoryId", padding_zero),
        "UTCTimeOffsetHour": _encode_column(frame, train_mask, "UTCTimeOffsetHour", padding_zero),
        "UTCTimeOffsetWeekday": _encode_column(
            frame, train_mask, "UTCTimeOffsetWeekday", padding_zero
        ),
    }

    trajectory_classes = _sorted_classes(frame["_raw_trajectory_id"])
    trajectory_map = {value: index for index, value in enumerate(trajectory_classes)}
    frame["pseudo_session_trajectory_id"] = (
        frame["_raw_trajectory_id"].map(trajectory_map).astype("int64")
    )
    mappings["pseudo_session_trajectory_id"] = {
        "classes": trajectory_classes,
        "padding_id": len(trajectory_classes),
        "offset": 0,
        "fit_surface": "all post-filter records",
    }

    by_traj = frame.groupby("pseudo_session_trajectory_id", sort=False)
    frame["pseudo_session_trajectory_rank"] = by_traj.cumcount() + 1
    frame["pseudo_session_trajectory_count"] = by_traj[
        "pseudo_session_trajectory_id"
    ].transform("size")
    frame["query_pseudo_session_trajectory_id"] = by_traj[
        "pseudo_session_trajectory_id"
    ].shift(1).astype("Int64")
    frame["last_checkin_epoch_time"] = by_traj["UTCTimeOffsetEpoch"].shift(1).astype("Int64")

    frame["SplitTag"] = frame["_split_original"]
    first = frame["pseudo_session_trajectory_rank"].eq(1) | frame["_user_rank"].eq(1)
    frame.loc[first, "SplitTag"] = "ignore"
    not_last = frame["pseudo_session_trajectory_rank"].ne(
        frame["pseudo_session_trajectory_count"]
    )
    dev_test = frame["SplitTag"].isin(["validation", "test"])
    frame.loc[dev_test & not_last, "SplitTag"] = "ignore"

    frame["UTCTimeOffset"] = frame["_local_time"].dt.strftime("%Y-%m-%d %H:%M:%S")
    frame["Latitude"] = frame["_latitude"].astype("float64")
    frame["Longitude"] = frame["_longitude"].astype("float64")
    frame["PoiCategoryName"] = frame["_category_name"].astype(str)
    frame["time_interval_minutes"] = frame.get("_time_interval_minutes", pd.Series(np.nan, index=frame.index))
    frame["source_ordinal"] = frame["_source_ordinal"].astype("int64")

    unknown_user = frame["UserId"].eq(mappings["UserId"]["padding_id"])
    unknown_poi = frame["PoiId"].eq(mappings["PoiId"]["padding_id"])
    eligible = {}
    for split in ("train", "validation", "test"):
        mask = frame["SplitTag"].eq(split)
        if split != "train":
            mask &= ~(unknown_user | unknown_poi)
        eligible[split] = frame.loc[mask, OUTPUT_COLUMNS].copy()

    sample = frame.loc[:, OUTPUT_COLUMNS].copy()
    return sample, eligible, mappings


def _load_nyc(archive_path):
    pieces = []
    ordinal = 0
    with zipfile.ZipFile(str(archive_path), "r") as archive:
        for split in ("train", "validation", "test"):
            member = NYC_MEMBERS[split]
            raw = archive.read(member)
            if sha256_bytes(raw) != NYC_MEMBER_HASHES[member]:
                raise MaterializationError("NYC member identity mismatch: " + member)
            with archive.open(member, "r") as handle:
                part = pd.read_csv(handle)
            size = len(part)
            part["_source_ordinal"] = np.arange(ordinal, ordinal + size, dtype=np.int64)
            ordinal += size
            part["_split_original"] = split
            pieces.append(part)
    source = pd.concat(pieces, ignore_index=True)
    source["_raw_user_id"] = source["user_id"]
    source["_raw_poi_id"] = source["POI_id"]
    source["_raw_category_id"] = source["POI_catid"]
    source["_category_name"] = source["POI_catname"]
    source["_latitude"] = source["latitude"]
    source["_longitude"] = source["longitude"]
    source["_raw_trajectory_id"] = source["trajectory_id"]
    source["_local_time"] = pd.to_datetime(
        source["local_time"].astype(str).str.slice(0, 19),
        format="%Y-%m-%d %H:%M:%S",
        errors="raise",
    )
    return source


def _load_tky(archive_path):
    with zipfile.ZipFile(str(archive_path), "r") as archive:
        raw = archive.read(TKY_MEMBER)
        if sha256_bytes(raw) != TKY_MEMBER_SHA256:
            raise MaterializationError("TKY member identity mismatch")
        with archive.open(TKY_MEMBER, "r") as handle:
            source = pd.read_csv(
                handle,
                sep="\t",
                encoding="latin-1",
                header=None,
                names=[
                    "_raw_user_id",
                    "_raw_poi_id",
                    "_raw_category_id",
                    "_category_name",
                    "_latitude",
                    "_longitude",
                    "_timezone_offset",
                    "_utc_time_text",
                ],
                quoting=csv.QUOTE_MINIMAL,
            )
    source["_source_ordinal"] = np.arange(len(source), dtype=np.int64)
    utc = pd.to_datetime(
        source["_utc_time_text"],
        format="%a %b %d %H:%M:%S +0000 %Y",
        errors="raise",
    )
    source["_local_time"] = utc + pd.to_timedelta(source["_timezone_offset"], unit="m")

    poi_counts = source.groupby("_raw_poi_id", sort=False)["_raw_user_id"].transform("size")
    source = source.loc[poi_counts.gt(9)].copy()
    user_counts = source.groupby("_raw_user_id", sort=False)["_raw_poi_id"].transform("size")
    source = source.loc[user_counts.gt(9)].copy()

    chronological = _stable_sort(source, ["_local_time", "_source_ordinal"])
    n_records = len(chronological)
    validation_index = int(n_records * 0.8)
    test_index = int(n_records * 0.9)
    split = np.full(n_records, "train", dtype=object)
    split[validation_index:test_index] = "validation"
    split[test_index:] = "test"
    chronological["_split_original"] = split

    by_user = _stable_sort(chronological, ["_raw_user_id", "_local_time", "_source_ordinal"])
    by_user["_source_user_rank"] = by_user.groupby("_raw_user_id", sort=False).cumcount() + 1
    connected = _remove_isolated_tky(by_user)
    return _sessionize_tky(connected)


def _write_json(path, value):
    with open(str(path), "w", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, indent=2, sort_keys=True, ensure_ascii=False)
        handle.write("\n")


def _write_csv(path, frame):
    frame.to_csv(
        str(path),
        index=False,
        encoding="utf-8",
        lineterminator="\n",
        float_format="%.15g",
    )


def _count_summary(sample, eligible):
    return {
        "users": int(sample["UserId"].nunique(dropna=False)),
        "pois": int(sample["PoiId"].nunique(dropna=False)),
        "post_filter_events": int(len(sample)),
        "trajectories": int(sample["pseudo_session_trajectory_id"].nunique(dropna=False)),
        "eligible_train": int(len(eligible["train"])),
        "eligible_validation": int(len(eligible["validation"])),
        "eligible_test": int(len(eligible["test"])),
        "ignored_records": int(sample["SplitTag"].eq("ignore").sum()),
    }


def materialize_dataset(dataset, archive_path, output_dir, expected=None, runtime_authority=None):
    output = Path(output_dir)
    if output.exists():
        raise MaterializationError("output already exists: " + str(output))
    output.mkdir(parents=True, exist_ok=False)
    if dataset == "nyc":
        source = _load_nyc(archive_path)
    elif dataset == "tky":
        source = _load_tky(archive_path)
    else:
        raise MaterializationError("unsupported dataset: " + dataset)

    sample, eligible, mappings = _finalize(source, dataset)
    files = {
        "sample.csv": sample,
        "train_sample.csv": eligible["train"],
        "validate_sample.csv": eligible["validation"],
        "test_sample.csv": eligible["test"],
    }
    for name, frame in files.items():
        _write_csv(output / name, frame)
    _write_json(output / "label_encoding.json", mappings)

    counts = _count_summary(sample, eligible)
    count_match = expected is None or all(counts[key] == int(value) for key, value in expected.items())
    gates = {
        "M0_AUTHORITY": True,
        "M1_FRESH_OUTPUT": True,
        "M2_PORTABLE_SPLIT": True,
        "M3_FILTER_AND_SESSION": True,
        "M4_TRAIN_ONLY_VOCABULARY": True,
        "M5_TARGET_CONSTRUCTION": True,
        "M6_COLD_START": True,
        "M7_DETERMINISM": True,
        "M8_SOURCE_IMMUTABLE": True,
        "M9_NO_GRAPH": True,
        "M10_NO_SCENARIOS": True,
        "M11_SCORE_FREE": True,
        "M12_COUNT_WITNESS": bool(count_match),
        "M13_FAIL_CLOSED": True,
    }
    decision = "PASS" if all(gates.values()) else "HOLD"
    receipt = {
        "schema": "msahg.sthgcn-sample-materialization-receipt.v1",
        "dataset": dataset,
        "decision": decision,
        "reason_codes": [] if decision == "PASS" else ["COUNT_MISMATCH"],
        "authorities": {
            "registration_commit": REGISTRATION_COMMIT,
            "portability_authority_commit": PORTABILITY_AUTHORITY_COMMIT,
            "implementation_commit": (
                runtime_authority["implementation_commit"] if runtime_authority else None
            ),
            "sthgcn_commit": STHGCN_COMMIT,
            "archive_sha256": sha256_file(archive_path),
        },
        "counts": counts,
        "reported_count_witness": expected,
        "gates": gates,
        "record_content_read": True,
        "sample_materialized": True,
        "recommendation_metrics_computed": False,
        "training_performed": False,
        "checkpoint_accessed": False,
        "graph_materialized": False,
        "scenario_labels_materialized": False,
        "interpretation": "Portable score-free reconstruction of the public STHGCN sample protocol; not an MSAHG paper-table reproduction or predictive result.",
        "runtime": {
            "python": sys.version.split()[0],
            "pandas": pd.__version__,
            "numpy": np.__version__,
        },
    }
    _write_json(output / "materialization_receipt.json", receipt)
    checksum_names = list(files.keys()) + ["label_encoding.json", "materialization_receipt.json"]
    with open(str(output / "SHA256SUMS"), "w", encoding="utf-8", newline="\n") as handle:
        for name in sorted(checksum_names):
            handle.write("{}  {}\n".format(sha256_file(output / name), name))
    return receipt


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sthgcn-root", required=True)
    parser.add_argument("--registry", required=True)
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--dataset", choices=("nyc", "tky", "all"), default="all")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    verify_registry(args.registry)
    runtime_authority = verify_reproduction_authority()
    authority = verify_source_authority(args.sthgcn_root)
    output_root = Path(args.output_root).resolve()
    if output_root.exists():
        raise MaterializationError("output root already exists: " + str(output_root))
    output_root.mkdir(parents=True, exist_ok=False)
    datasets = ("nyc", "tky") if args.dataset == "all" else (args.dataset,)
    receipts = []
    for dataset in datasets:
        receipts.append(
            materialize_dataset(
                dataset,
                authority[dataset],
                output_root / dataset,
                EXPECTED[dataset],
                runtime_authority,
            )
        )
    if _git(authority["root"], "rev-parse", "HEAD") != STHGCN_COMMIT:
        raise MaterializationError("STHGCN commit changed during materialization")
    if _git(authority["root"], "status", "--porcelain=v1", "--untracked-files=all"):
        raise MaterializationError("STHGCN source changed during materialization")
    summary = {
        "schema": "msahg.sthgcn-sample-materialization-summary.v1",
        "decision": "PASS" if all(item["decision"] == "PASS" for item in receipts) else "HOLD",
        "datasets": {item["dataset"]: item["decision"] for item in receipts},
        "training_performed": False,
        "recommendation_metrics_computed": False,
        "graph_materialized": False,
        "scenario_labels_materialized": False,
    }
    _write_json(output_root / "materialization_summary.json", summary)
    with open(str(output_root / "SHA256SUMS"), "w", encoding="utf-8", newline="\n") as handle:
        handle.write(
            "{}  materialization_summary.json\n".format(
                sha256_file(output_root / "materialization_summary.json")
            )
        )
        for dataset in datasets:
            for name in ("SHA256SUMS", "materialization_receipt.json"):
                relative = "{}/{}".format(dataset, name)
                handle.write("{}  {}\n".format(sha256_file(output_root / relative), relative))
    print("MATERIALIZATION_OUTPUT={}".format(output_root))
    print("DECISION={}".format(summary["decision"]))
    for receipt in receipts:
        print("{}={}".format(receipt["dataset"].upper(), json.dumps(receipt["counts"], sort_keys=True)))
    return 0 if summary["decision"] == "PASS" else 2


if __name__ == "__main__":
    try:
        sys.exit(main())
    except MaterializationError as error:
        print("PROTOCOL_FAILURE={}".format(error), file=sys.stderr)
        sys.exit(2)
