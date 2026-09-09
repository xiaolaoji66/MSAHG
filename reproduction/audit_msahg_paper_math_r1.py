"""Synthetic target-free qualification for MSAHG paper-math R1."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import subprocess
from pathlib import Path
from typing import Dict, Mapping, Tuple

import torch

from msahg_paper_math_r1 import (
    GRAPH_KEYS,
    TASKS,
    AdaptiveSplitMSAHG,
    MSAHGPaperMathCore,
    recommendation_objective,
)


EXPECTED_REGISTRY_SHA256 = "e17a0c19dc3f10d6722c6157128438dc34d9cfd49e5ecdf53b3cb7d6b830678a"
EXPECTED_SCOPE_COMMIT = "8308cf4b9a12b604d397e4932ae8932190436982"
EXPECTED_UPSTREAM_COMMIT = "3d74d70c852c56adcc09d907488410be5eda2744"
REGISTERED_GATES = (
    "A0_AUTHORITY_IDENTITY",
    "A1_NO_GUGEN_DEPENDENCY",
    "A2_FORWARD_SHAPES",
    "A3_GRAPH_VIEW_COHERENCE",
    "A4_TASK_INDEX_BIJECTION",
    "A5_SHARED_ANCHOR",
    "A6_SPLIT_PREDICATE",
    "A7_UNSPLIT_IDENTITY",
    "A8_SPLIT_ISOLATION",
    "A9_OPTIMIZER_COMPLETENESS",
    "A10_GRADIENT_REACHABILITY",
    "A11_CHECKPOINT_ROUNDTRIP",
    "A12_DETERMINISM",
    "A13_CPU_SMOKE",
    "A14_CUDA_SMOKE_IF_AVAILABLE",
    "A15_TARGET_BLIND",
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _tensor_sha(tensor: torch.Tensor) -> str:
    value = tensor.detach().cpu().contiguous()
    return hashlib.sha256(value.numpy().tobytes()).hexdigest()


def _git(repo: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(repo)] + list(args), text=True
    ).strip()


def _normalized(rows: int, cols: int, device: torch.device) -> torch.Tensor:
    values = torch.arange(1, rows * cols + 1, dtype=torch.float32, device=device)
    values = values.reshape(rows, cols)
    return values / values.sum(dim=1, keepdim=True)


def _fixture(device: torch.device) -> Tuple[torch.Tensor, Dict[str, torch.Tensor]]:
    users, pois, times, transitions = 4, 7, 3, 5
    graphs = {
        "collaborative_h_up": _normalized(users, pois, device),
        "collaborative_h_pu": _normalized(pois, users, device),
        "temporal_poi_h_tp": _normalized(times, pois, device),
        "temporal_poi_h_pt": _normalized(pois, times, device),
        "temporal_user_h_tu": _normalized(times, users, device),
        "temporal_user_h_ut": _normalized(users, times, device),
        "geography": _normalized(pois, pois, device),
        "transition_h_tar": _normalized(transitions, pois, device),
        "transition_h_src": _normalized(pois, transitions, device),
    }
    assert tuple(sorted(graphs)) == tuple(sorted(GRAPH_KEYS))
    return torch.tensor([0, 2, 3], device=device), graphs


def _new_wrapper(device: torch.device) -> AdaptiveSplitMSAHG:
    torch.manual_seed(260909)
    if device.type == "cuda":
        torch.cuda.manual_seed_all(260909)
    core = MSAHGPaperMathCore(
        num_users=4,
        num_pois=7,
        embedding_dim=8,
        graph_layers=2,
        dropout=0.0,
        temperature=0.1,
    ).to(device)
    return AdaptiveSplitMSAHG(core, conflict_threshold=-0.5).to(device)


def _device_audit(device: torch.device) -> Mapping[str, object]:
    wrapper = _new_wrapper(device)
    user_ids, graphs = _fixture(device)
    wrapper.eval()

    core_logits, core_aux = wrapper.core(user_ids, graphs, return_aux=True)
    anchor_logits, anchor_aux = wrapper(TASKS[0], user_ids, graphs, return_aux=True)
    unsplit_exact = torch.equal(core_logits, anchor_logits)

    perturbed = dict(graphs)
    perturbed["geography"] = torch.eye(7, device=device)
    _, changed_aux = wrapper(TASKS[0], user_ids, perturbed, return_aux=True)
    geography_changed = not torch.equal(
        anchor_aux["poi_views"]["geography"],
        changed_aux["poi_views"]["geography"],
    )
    unrelated_collaborative_exact = torch.equal(
        anchor_aux["poi_views"]["collaborative"],
        changed_aux["poi_views"]["collaborative"],
    )

    parameter_name = "user_view_gates.collaborative.weight"
    partitions = (TASKS[:3], TASKS[3:])
    wrapper.split_parameter(parameter_name, partitions)
    topology = wrapper.split_topology()

    group0_key = wrapper._task_keys[parameter_name][TASKS[0]]
    group1_key = wrapper._task_keys[parameter_name][TASKS[-1]]
    before_group0 = wrapper(TASKS[0], user_ids, graphs)
    before_group1 = wrapper(TASKS[-1], user_ids, graphs)
    with torch.no_grad():
        wrapper.split_parameters[group0_key].add_(0.25)
    after_group0 = wrapper(TASKS[0], user_ids, graphs)
    after_group1 = wrapper(TASKS[-1], user_ids, graphs)
    split_isolation = (
        not torch.equal(before_group0, after_group0)
        and torch.equal(before_group1, after_group1)
    )

    trainable = wrapper.optimizer_parameters()
    optimizer_ids = wrapper.optimizer_parameter_ids()
    optimizer_complete = (
        len(optimizer_ids) == len(set(optimizer_ids))
        and set(optimizer_ids)
        == {id(parameter) for parameter in wrapper.parameters() if parameter.requires_grad}
        and id(wrapper.split_parameters[group0_key]) in optimizer_ids
        and id(wrapper.split_parameters[group1_key]) in optimizer_ids
        and not wrapper._core_parameter(parameter_name).requires_grad
    )

    wrapper.train()
    targets = torch.tensor([1, 3, 5], device=device)
    objectives = []
    for task in (TASKS[0], TASKS[-1]):
        logits, auxiliary = wrapper(task, user_ids, graphs, return_aux=True)
        objectives.append(
            recommendation_objective(wrapper.core, logits, auxiliary, targets)
        )
    total = torch.stack(objectives).sum()
    total.backward()
    split_gradients_reachable = all(
        wrapper.split_parameters[key].grad is not None
        and torch.isfinite(wrapper.split_parameters[key].grad).all()
        and bool(wrapper.split_parameters[key].grad.abs().sum() > 0)
        for key in (group0_key, group1_key)
    )
    all_trainable_gradients_finite = all(
        parameter.grad is None or torch.isfinite(parameter.grad).all()
        for parameter in trainable
    )

    checkpoint = {
        "topology": topology,
        "state_dict": {
            key: value.detach().clone() for key, value in wrapper.state_dict().items()
        },
    }
    restored = _new_wrapper(device)
    restored.restore_topology(checkpoint["topology"])
    restored.load_state_dict(checkpoint["state_dict"], strict=True)
    restored.eval()
    wrapper.eval()
    restored_logits = restored(TASKS[0], user_ids, graphs)
    reference_logits = wrapper(TASKS[0], user_ids, graphs)
    checkpoint_exact = torch.equal(restored_logits, reference_logits)

    synthetic_similarities = torch.eye(3, device=device)
    synthetic_similarities[0, 1] = synthetic_similarities[1, 0] = -0.5
    synthetic_similarities[0, 2] = synthetic_similarities[2, 0] = -0.50001
    threshold_exact = wrapper.conflicting_pairs(synthetic_similarities) == ((0, 2),)

    repeat = _new_wrapper(device)
    repeat.eval()
    repeat_logits = repeat(TASKS[0], user_ids, graphs)
    deterministic = _tensor_sha(core_logits) == _tensor_sha(repeat_logits)

    return {
        "device": str(device),
        "finite": bool(torch.isfinite(reference_logits).all()),
        "full_catalog_shape": list(reference_logits.shape),
        "unsplit_exact": bool(unsplit_exact),
        "geography_view_changed": bool(geography_changed),
        "unrelated_collaborative_view_exact": bool(unrelated_collaborative_exact),
        "split_isolation": bool(split_isolation),
        "optimizer_complete": bool(optimizer_complete),
        "split_gradients_reachable": bool(split_gradients_reachable),
        "all_trainable_gradients_finite": bool(all_trainable_gradients_finite),
        "checkpoint_exact": bool(checkpoint_exact),
        "threshold_exact": bool(threshold_exact),
        "deterministic": bool(deterministic),
        "output_sha256": _tensor_sha(reference_logits),
        "trainable_parameter_count": int(sum(p.numel() for p in trainable)),
        "split_topology": {
            key: [list(group) for group in groups] for key, groups in topology.items()
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    repo = Path(args.repo).resolve()
    output = Path(args.output).resolve()
    registry = repo / "reproduction" / "PAPER_FAITHFUL_R1_REGISTRY.json"
    module = repo / "reproduction" / "msahg_paper_math_r1.py"
    audit = repo / "reproduction" / "audit_msahg_paper_math_r1.py"

    if output.exists():
        raise RuntimeError("output path already exists")
    output.mkdir(parents=False)

    head = _git(repo, "rev-parse", "HEAD")
    parent = _git(repo, "rev-parse", "HEAD^")
    clean = _git(repo, "status", "--porcelain=v1", "--untracked-files=all") == ""
    changed = _git(repo, "diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD").splitlines()

    cpu = _device_audit(torch.device("cpu"))
    cuda_available = torch.cuda.is_available()
    cuda = _device_audit(torch.device("cuda:0")) if cuda_available else None

    # Scan the production module only.  The auditor necessarily contains the
    # forbidden strings as predicates, so including itself would self-trigger.
    source_text = module.read_text(encoding="utf-8")
    forbidden_fragments = (
        "gugen-baseline",
        "gugen_innovation_runs",
        "datasets/NYC",
        "datasets/TKY",
        "test.pkl",
        "group_result.txt",
    )
    target_blind = not any(fragment in source_text for fragment in forbidden_fragments)

    exact_files = sorted(changed) == sorted(
        [
            "reproduction/audit_msahg_paper_math_r1.py",
            "reproduction/msahg_paper_math_r1.py",
            "scripts/run_msahg_paper_math_r1_target_free.sh",
            "tests/test_msahg_paper_math_r1.py",
        ]
    )
    authority_identity = (
        parent == EXPECTED_SCOPE_COMMIT
        and _sha256(registry) == EXPECTED_REGISTRY_SHA256
        and clean
        and exact_files
    )

    device_records = [cpu] + ([cuda] if cuda is not None else [])
    gates = {
        "A0_AUTHORITY_IDENTITY": authority_identity,
        "A1_NO_GUGEN_DEPENDENCY": target_blind,
        "A2_FORWARD_SHAPES": all(r["full_catalog_shape"] == [3, 7] for r in device_records),
        "A3_GRAPH_VIEW_COHERENCE": all(
            r["geography_view_changed"] and r["unrelated_collaborative_view_exact"]
            for r in device_records
        ),
        "A4_TASK_INDEX_BIJECTION": tuple(TASKS)
        == ("User/0", "User/1", "Time/0", "Time/1", "POI/0", "POI/1"),
        "A5_SHARED_ANCHOR": all(r["unsplit_exact"] for r in device_records),
        "A6_SPLIT_PREDICATE": all(r["threshold_exact"] for r in device_records),
        "A7_UNSPLIT_IDENTITY": all(r["unsplit_exact"] for r in device_records),
        "A8_SPLIT_ISOLATION": all(r["split_isolation"] for r in device_records),
        "A9_OPTIMIZER_COMPLETENESS": all(r["optimizer_complete"] for r in device_records),
        "A10_GRADIENT_REACHABILITY": all(
            r["split_gradients_reachable"] and r["all_trainable_gradients_finite"]
            for r in device_records
        ),
        "A11_CHECKPOINT_ROUNDTRIP": all(r["checkpoint_exact"] for r in device_records),
        "A12_DETERMINISM": all(r["deterministic"] for r in device_records),
        "A13_CPU_SMOKE": cpu["finite"],
        "A14_CUDA_SMOKE_IF_AVAILABLE": (cuda is None or cuda["finite"]),
        "A15_TARGET_BLIND": target_blind,
    }
    if tuple(gates) != REGISTERED_GATES:
        raise RuntimeError("gate order or identity drift")

    decision = "PASS" if all(gates.values()) else "FAIL"
    receipt = {
        "schema": "msahg.paper-math-r1.target-free-receipt.v1",
        "decision": decision,
        "git_commit": head,
        "git_parent": parent,
        "expected_upstream_commit": EXPECTED_UPSTREAM_COMMIT,
        "registry_sha256": _sha256(registry),
        "source_sha256": {
            "module": _sha256(module),
            "audit": _sha256(audit),
        },
        "gates": gates,
        "failed_gates": [name for name, value in gates.items() if not value],
        "cpu": cpu,
        "cuda": cuda,
        "runtime": {
            "python": platform.python_version(),
            "torch": torch.__version__,
            "cuda_available": cuda_available,
            "cuda_version": torch.version.cuda,
            "device_name": torch.cuda.get_device_name(0) if cuda_available else None,
        },
        "target_accessed": False,
        "metrics_computed": False,
        "training_performed": False,
        "paper_table_reproduction_established": False,
        "interpretation": (
            "PASS establishes synthetic computation-graph and APS parameter-bank "
            "coherence only. It does not establish dataset identity or paper metrics."
        ),
    }
    receipt_path = output / "target_free_receipt.json"
    receipt_path.write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    raw_sha = _sha256(receipt_path)
    (output / "SHA256SUMS").write_text(
        "{}  target_free_receipt.json\n".format(raw_sha), encoding="utf-8"
    )
    print("TARGET_FREE_RECEIPT={}".format(receipt_path))
    print("DECISION={}".format(decision))
    return 0 if decision == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
