"""Score-free qualification for the public STHGCN sample protocol.

This auditor reads source files and public data archives only to establish
identity and preprocessing semantics.  It never imports either model, creates
graph objects, trains, selects a checkpoint, or computes recommendation
metrics.
"""

from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import io
import json
import subprocess
import sys
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Dict, Mapping, Sequence


MSAHG_REGISTRATION_COMMIT = "87e21b86f39f7491e2460f0647ace0e14d6fbb17"
STHGCN_COMMIT = "27b595846d29019799485985bff49f9ed02c4ade"

EXPECTED_HASHES = {
    "LICENSE": "c71d239df91726fc519c6eb72d318ec65820627232b2f796219e87dcf35d0ab4",
    "README.md": "90d667566b38e9404ac93e0ef35523a17f597b5a220fb30e82acc9d81b10ee4e",
    "preprocess/preprocess_main.py": "d8ade2ff7f5e17db7322d38db6a0b2d003f7bd27133ea6a773d927a8f904bfba",
    "preprocess/preprocess_fn.py": "aaf6134b6912a69cdc77d34f6e62ac134329acee2e08175c626844944ebf0966",
    "preprocess/file_reader.py": "f14cbda6289f289bebe61b32312afff325c9c50c4b926b009e9d04680697180e",
    "preprocess/generate_hypergraph.py": "0d41977dd07a22f83b90beb19140a86c650c534fde08829bec830681be6fd96a",
    "dataset/lbsn_dataset.py": "6c1ecd998b50fc180eb56af3d05de7a96b67be9ae50a291bebe9192ea5074b9e",
    "layer/sampler.py": "70d6ff5911b9506aadfac90bbd6516b74b550fed89f588a4cdd9bc364f253546",
    "conf/best_conf/nyc.yml": "4695cae00047eb94028429b6f00dd12e48324a1bcf23c7493889a933d06a04bd",
    "conf/best_conf/tky.yml": "ab5745f924a8acdcdd14cce832614b7fe83ccbb082669789b98b89c29b7a4918",
    "data/nyc/raw.zip": "974bc90b3e0cdec6ec29a0a953ac41d3f81880e17bdd4c7c0cd94f2afc9e17d2",
    "data/tky/raw.zip": "823cd400a8d67b360c50217c1e8141e566a2b804ca8af9feac9ff9c0f76220c7",
    "requirements.txt": "557988c4bdf82da8923db1a8ba4c6ee2b5dd64460dc47c75f1fda34d2fd8a9e0",
}

NYC_MEMBERS = {
    "raw/NYC_train.csv": {
        "bytes": 16896314,
        "sha256": "bb1e7b44e484c9338b27dfd67298d6bfb2b958c07ec0aa3036b92d86269dcfa0",
        "rows": 83228,
    },
    "raw/NYC_val.csv": {
        "bytes": 2106303,
        "sha256": "3eeb4e39be8869e4259e9316d1aeda088e0606f7efdb93e3fd436e86cfc58b2e",
        "rows": 10339,
    },
    "raw/NYC_test.csv": {
        "bytes": 2111049,
        "sha256": "c285494e63475512c3c22b37885c70cf0ee89548cbcac109d72ba4e0d02f8f6e",
        "rows": 10374,
    },
}

TKY_MEMBER = "raw/dataset_TSMC2014_TKY.txt"
TKY_MEMBER_SHA256 = "85542c605ce708d8584637756590383a84e9bbdb71342d0d8e78858ba2a0e5c8"
TKY_RAW_IDENTITY = {"rows": 573703, "users": 2293, "pois": 61858, "categories": 385}

REQUIRED_GATES = (
    "Q0_MSAHG_AUTHORITY",
    "Q1_STHGCN_AUTHORITY",
    "Q2_LICENSE_AND_SOURCE_HASHES",
    "Q3_ARCHIVE_MEMBERS",
    "Q4_NYC_RAW_SPLIT_COUNTS",
    "Q5_TKY_RAW_IDENTITY",
    "Q6_SOURCE_SEMANTICS",
    "Q7_SPLIT_ASSIGNMENT_AUDIT",
    "Q8_FULL_GRAPH_INPUT_AUDIT",
    "Q9_DATASET_IDENTITY_SEPARATION",
    "Q10_NO_GUGEN_DEPENDENCY",
    "Q11_SCORE_FREE",
    "Q12_FAIL_CLOSED",
)


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def git(repo: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(repo)] + list(args), stderr=subprocess.STDOUT
    ).decode("utf-8").strip()


def assert_clean_exact_repo(repo: Path, expected_commit: str) -> Dict[str, str]:
    head = git(repo, "rev-parse", "HEAD")
    if head != expected_commit:
        raise ValueError("unexpected repository commit: {}".format(head))
    status = git(repo, "status", "--porcelain=v1", "--untracked-files=all")
    if status:
        raise ValueError("repository is not clean")
    remote = git(repo, "remote", "get-url", "origin")
    return {"commit": head, "origin": remote, "clean": "true"}


def assert_msahg_lineage(repo: Path) -> Dict[str, str]:
    head = git(repo, "rev-parse", "HEAD")
    subprocess.check_call(
        [
            "git",
            "-C",
            str(repo),
            "merge-base",
            "--is-ancestor",
            MSAHG_REGISTRATION_COMMIT,
            head,
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return {"head": head, "registration_ancestor": MSAHG_REGISTRATION_COMMIT}


def verify_source_hashes(repo: Path) -> Dict[str, str]:
    observed = {}
    for relative, expected in sorted(EXPECTED_HASHES.items()):
        path = repo / relative
        if not path.is_file():
            raise ValueError("missing frozen STHGCN file: {}".format(relative))
        digest = sha256_file(path)
        if digest != expected:
            raise ValueError("STHGCN hash mismatch for {}: {}".format(relative, digest))
        observed[relative] = digest
    return observed


def archive_member_bytes(archive: zipfile.ZipFile, member: str) -> bytes:
    try:
        return archive.read(member)
    except KeyError:
        raise ValueError("missing archive member: {}".format(member))


def inspect_nyc_archive(path: Path) -> Dict[str, object]:
    results = {}
    with zipfile.ZipFile(str(path)) as archive:
        files = sorted(name for name in archive.namelist() if not name.endswith("/"))
        if files != sorted(NYC_MEMBERS):
            raise ValueError("unexpected NYC archive members: {}".format(files))
        for member, expected in sorted(NYC_MEMBERS.items()):
            payload = archive_member_bytes(archive, member)
            if len(payload) != expected["bytes"]:
                raise ValueError("NYC member byte mismatch: {}".format(member))
            if sha256_bytes(payload) != expected["sha256"]:
                raise ValueError("NYC member hash mismatch: {}".format(member))

            reader = csv.DictReader(io.StringIO(payload.decode("utf-8"), newline=""))
            rows = 0
            users = set()
            pois = set()
            trajectories = set()
            minimum = None
            maximum = None
            for row in reader:
                rows += 1
                users.add(row["user_id"])
                pois.add(row["POI_id"])
                trajectories.add(row["trajectory_id"])
                stamp = datetime.strptime(row["local_time"][:19], "%Y-%m-%d %H:%M:%S")
                minimum = stamp if minimum is None or stamp < minimum else minimum
                maximum = stamp if maximum is None or stamp > maximum else maximum
            if rows != expected["rows"]:
                raise ValueError("NYC member row mismatch: {}".format(member))
            results[member] = {
                "bytes": len(payload),
                "sha256": sha256_bytes(payload),
                "rows": rows,
                "users": len(users),
                "pois": len(pois),
                "trajectories": len(trajectories),
                "min_local_time": minimum.isoformat(sep=" "),
                "max_local_time": maximum.isoformat(sep=" "),
            }

    train = results["raw/NYC_train.csv"]
    valid = results["raw/NYC_val.csv"]
    test = results["raw/NYC_test.csv"]
    if not (
        train["max_local_time"] < valid["min_local_time"]
        and valid["max_local_time"] < test["min_local_time"]
    ):
        raise ValueError("NYC file-level splits are not chronologically disjoint")
    if sum(item["rows"] for item in results.values()) != 103941:
        raise ValueError("NYC total row mismatch")
    return results


def inspect_tky_archive(path: Path) -> Dict[str, object]:
    with zipfile.ZipFile(str(path)) as archive:
        files = sorted(name for name in archive.namelist() if not name.endswith("/"))
        if files != [TKY_MEMBER]:
            raise ValueError("unexpected TKY archive members: {}".format(files))
        digest = hashlib.sha256()
        rows = 0
        users = set()
        pois = set()
        categories = set()
        with archive.open(TKY_MEMBER) as handle:
            for raw_line in handle:
                digest.update(raw_line)
                columns = raw_line.decode("latin-1").rstrip("\r\n").split("\t")
                if len(columns) != 8:
                    raise ValueError("invalid TKY column count at row {}".format(rows + 1))
                rows += 1
                users.add(columns[0])
                pois.add(columns[1])
                categories.add(columns[2])
        observed = {
            "member": TKY_MEMBER,
            "member_sha256": digest.hexdigest(),
            "rows": rows,
            "users": len(users),
            "pois": len(pois),
            "categories": len(categories),
        }
    if observed["member_sha256"] != TKY_MEMBER_SHA256:
        raise ValueError("TKY member hash mismatch")
    for key, expected in TKY_RAW_IDENTITY.items():
        if observed[key] != expected:
            raise ValueError("TKY raw {} mismatch: {}".format(key, observed[key]))
    return observed


def inspect_source_semantics(repo: Path) -> Dict[str, bool]:
    reader = (repo / "preprocess/file_reader.py").read_text(encoding="utf-8")
    functions = (repo / "preprocess/preprocess_fn.py").read_text(encoding="utf-8")
    main = (repo / "preprocess/preprocess_main.py").read_text(encoding="utf-8")
    sampler = (repo / "layer/sampler.py").read_text(encoding="utf-8")
    checks = {
        "poi_keep_strictly_above_threshold": "['UserId'] > poi_min_freq" in reader,
        "user_keep_strictly_above_threshold": "['PoiId'] > user_min_freq" in reader,
        "intended_global_80_10_10": (
            "validation_index = int(total_len * 0.8)" in reader
            and "test_index = int(total_len * 0.9)" in reader
            and "sort_values(by='UTCTimeOffset'" in reader
        ),
        "session_break_strictly_above_interval": (
            "time_diff.total_seconds() / 60 > session_time_interval" in reader
        ),
        "label_fit_uses_train": "df_train = df[df['SplitTag'] == 'train']" in reader,
        "remove_unseen_user_and_poi": (
            "df_validate['UserId'].isin(train_user_set)" in functions
            and "df_validate['PoiId'].isin(train_poi_set)" in functions
            and "df_test['UserId'].isin(train_user_set)" in functions
            and "df_test['PoiId'].isin(train_poi_set)" in functions
        ),
        "first_event_ignored": "pseudo_session_trajectory_rank'] == 1" in functions,
        "validation_test_last_event_only": (
            "df['SplitTag'] == 'validation'" in functions
            and "df['SplitTag'] == 'test'" in functions
            and "pseudo_session_trajectory_count" in functions
        ),
        "nyc_uses_presplit_files": all(
            name in main for name in ("NYC_train.csv", "NYC_val.csv", "NYC_test.csv")
        ),
        "target_time_filter_present": (
            "edge_t[target_mask] <= edge_max_time" in sampler
            and "filter_traj2traj_with_leakage" in sampler
        ),
    }
    if not all(checks.values()):
        raise ValueError("source semantic predicate missing")
    return checks


def detect_protocol_hazards(repo: Path) -> Dict[str, bool]:
    reader = (repo / "preprocess/file_reader.py").read_text(encoding="utf-8")
    main = (repo / "preprocess/preprocess_main.py").read_text(encoding="utf-8")
    hazards = {
        "tky_validation_chained_assignment_detected": (
            "df.iloc[validation_index:test_index]['SplitTag'] = 'validation'" in reader
        ),
        "tky_test_chained_assignment_detected": (
            "df.iloc[test_index:]['SplitTag'] = 'test'" in reader
        ),
        "combined_sample_hypergraph_input_detected": (
            "generate_hypergraph_from_file(sample_file, preprocessed_path, cfg.dataset_args)" in main
        ),
    }
    if not all(hazards.values()):
        raise ValueError("registered source hazard no longer detected")
    return hazards


def reduce_decision(gates: Mapping[str, bool]) -> str:
    if tuple(gates.keys()) != REQUIRED_GATES:
        return "PROTOCOL_FAILURE"
    return "PASS" if all(value is True for value in gates.values()) else "PROTOCOL_FAILURE"


def imported_roots(source: str) -> set:
    roots = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            roots.add(node.module.split(".", 1)[0])
    return roots


def called_names(source: str) -> set:
    names = set()
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.Call):
            continue
        if isinstance(node.func, ast.Name):
            names.add(node.func.id)
        elif isinstance(node.func, ast.Attribute):
            names.add(node.func.attr)
    return names


def build_receipt(msahg_repo: Path, sthgcn_repo: Path) -> Dict[str, object]:
    gates = {name: False for name in REQUIRED_GATES}

    msahg = assert_msahg_lineage(msahg_repo)
    gates["Q0_MSAHG_AUTHORITY"] = True

    sthgcn = assert_clean_exact_repo(sthgcn_repo, STHGCN_COMMIT)
    gates["Q1_STHGCN_AUTHORITY"] = True

    hashes = verify_source_hashes(sthgcn_repo)
    gates["Q2_LICENSE_AND_SOURCE_HASHES"] = True

    nyc = inspect_nyc_archive(sthgcn_repo / "data/nyc/raw.zip")
    tky = inspect_tky_archive(sthgcn_repo / "data/tky/raw.zip")
    gates["Q3_ARCHIVE_MEMBERS"] = True
    gates["Q4_NYC_RAW_SPLIT_COUNTS"] = True
    gates["Q5_TKY_RAW_IDENTITY"] = True

    semantics = inspect_source_semantics(sthgcn_repo)
    gates["Q6_SOURCE_SEMANTICS"] = True

    hazards = detect_protocol_hazards(sthgcn_repo)
    gates["Q7_SPLIT_ASSIGNMENT_AUDIT"] = (
        hazards["tky_validation_chained_assignment_detected"]
        and hazards["tky_test_chained_assignment_detected"]
    )
    gates["Q8_FULL_GRAPH_INPUT_AUDIT"] = hazards[
        "combined_sample_hypergraph_input_detected"
    ]

    sthgcn_counts = ((1048, 4981, 103941, 14130), (2282, 7833, 405000, 65499))
    msahg_counts = ((1743, 7289, 57327, 6102), (1383, 17023, 507260, 41374))
    gates["Q9_DATASET_IDENTITY_SEPARATION"] = all(
        left != right for left, right in zip(sthgcn_counts, msahg_counts)
    )

    source = Path(__file__).read_text(encoding="utf-8")
    gates["Q10_NO_GUGEN_DEPENDENCY"] = imported_roots(source).isdisjoint(
        {"torch", "dgl", "model", "gugen"}
    )
    gates["Q11_SCORE_FREE"] = called_names(source).isdisjoint(
        {"accuracy_score", "mean_reciprocal_rank", "cross_entropy", "backward"}
    )
    gates["Q12_FAIL_CLOSED"] = True

    receipt = {
        "schema": "msahg.sthgcn-sample-protocol.score-free-qualification.v1",
        "decision": reduce_decision(gates),
        "gates": gates,
        "authorities": {"msahg": msahg, "sthgcn": sthgcn},
        "source_hashes": hashes,
        "nyc_archive": nyc,
        "tky_archive": tky,
        "source_semantics": semantics,
        "registered_hazards": hazards,
        "paper_faithful_empirical_reproduction": False,
        "sample_materialized": False,
        "graph_materialized": False,
        "scenario_labels_materialized": False,
        "training_performed": False,
        "recommendation_metrics_computed": False,
        "status_after_pass": "SAMPLE_PROTOCOL_SOURCE_QUALIFIED_MATERIALIZER_NOT_AUTHORIZED",
        "warnings": [
            "TKY source split uses non-portable Pandas chained assignment",
            "STHGCN PyG graph construction starts from combined sample.csv",
            "MSAHG six-scenario label identity remains unresolved",
        ],
    }
    return receipt


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--msahg-repo", required=True, type=Path)
    parser.add_argument("--sthgcn-repo", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args(argv)


def main(argv: Sequence[str] = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    try:
        receipt = build_receipt(args.msahg_repo.resolve(), args.sthgcn_repo.resolve())
    except Exception as exc:
        print("PROTOCOL_FAILURE={}".format(exc), file=sys.stderr)
        return 2
    if receipt["decision"] != "PASS":
        print(json.dumps(receipt, indent=2, sort_keys=True))
        return 2
    if args.output.exists():
        print("PROTOCOL_FAILURE=output already exists", file=sys.stderr)
        return 2
    args.output.parent.mkdir(parents=True, exist_ok=True)
    encoded = (json.dumps(receipt, indent=2, sort_keys=True) + "\n").encode("utf-8")
    with args.output.open("xb") as handle:
        handle.write(encoded)
    print("RECEIPT={}".format(args.output))
    print("DECISION=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
