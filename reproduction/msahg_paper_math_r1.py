"""Target-free reconstruction of the paper-determined MSAHG computation graph.

This module intentionally contains no dataset loader, metric implementation,
checkpoint selection, or training entry point.  It separates the graph model
from Adaptive Parameter Splitting (APS), and uses functional parameter
substitution instead of mutating registered module parameters during forward.
"""

from __future__ import annotations

import hashlib
from itertools import combinations
from typing import Dict, Iterable, List, Mapping, Sequence, Tuple

import torch
import torch.nn as nn
import torch.nn.functional as F

try:
    from torch.func import functional_call
except ImportError:  # pragma: no cover - compatibility for older torch only
    from torch.nn.utils.stateless import functional_call


TASKS: Tuple[str, ...] = (
    "User/0",
    "User/1",
    "Time/0",
    "Time/1",
    "POI/0",
    "POI/1",
)

GRAPH_KEYS: Tuple[str, ...] = (
    "collaborative_h_up",
    "collaborative_h_pu",
    "temporal_poi_h_tp",
    "temporal_poi_h_pt",
    "temporal_user_h_tu",
    "temporal_user_h_ut",
    "geography",
    "transition_h_tar",
    "transition_h_src",
)


def _matmul(matrix: torch.Tensor, values: torch.Tensor) -> torch.Tensor:
    if matrix.layout != torch.strided:
        return torch.sparse.mm(matrix, values)
    return matrix.matmul(values)


def _residual_graph_stack(
    values: torch.Tensor,
    left: torch.Tensor,
    right: torch.Tensor,
    layers: int,
    dropout: float,
    training: bool,
) -> torch.Tensor:
    states = [values]
    current = values
    for _ in range(layers):
        propagated = _matmul(right, _matmul(left, current))
        current = propagated + current
        current = F.dropout(current, p=dropout, training=training)
        states.append(current)
    return torch.stack(states, dim=0).mean(dim=0)


def _residual_adjacency_stack(
    values: torch.Tensor,
    adjacency: torch.Tensor,
    layers: int,
    dropout: float,
    training: bool,
) -> torch.Tensor:
    states = [values]
    current = values
    for _ in range(layers):
        current = _matmul(adjacency, current) + current
        current = F.dropout(current, p=dropout, training=training)
        states.append(current)
    return torch.stack(states, dim=0).mean(dim=0)


class MSAHGPaperMathCore(nn.Module):
    """Paper-determined graph scorer, independent from released data objects."""

    def __init__(
        self,
        num_users: int,
        num_pois: int,
        embedding_dim: int = 128,
        graph_layers: int = 3,
        dropout: float = 0.5,
        temperature: float = 0.1,
    ) -> None:
        super().__init__()
        if num_users <= 0 or num_pois <= 0:
            raise ValueError("num_users and num_pois must be positive")
        if embedding_dim <= 0 or graph_layers < 0:
            raise ValueError("invalid model geometry")
        if temperature <= 0:
            raise ValueError("temperature must be positive")

        self.num_users = int(num_users)
        self.num_pois = int(num_pois)
        self.embedding_dim = int(embedding_dim)
        self.graph_layers = int(graph_layers)
        self.dropout = float(dropout)
        self.temperature = float(temperature)

        self.user_embedding = nn.Embedding(num_users, embedding_dim)
        self.poi_embedding = nn.Embedding(num_pois, embedding_dim)

        self.poi_view_gates = nn.ModuleDict(
            {
                view: nn.Linear(embedding_dim, embedding_dim)
                for view in ("collaborative", "temporal", "geography", "transition")
            }
        )
        self.temporal_user_input_gate = nn.Linear(embedding_dim, embedding_dim)
        self.user_view_gates = nn.ModuleDict(
            {
                view: nn.Linear(embedding_dim, 1)
                for view in ("collaborative", "temporal", "geography", "transition")
            }
        )

    def _validate_graphs(self, graphs: Mapping[str, torch.Tensor]) -> None:
        if tuple(sorted(graphs)) != tuple(sorted(GRAPH_KEYS)):
            raise ValueError("graph mapping must contain exactly the registered keys")

        u, p = self.num_users, self.num_pois
        expected = {
            "collaborative_h_up": (u, p),
            "collaborative_h_pu": (p, u),
            "temporal_poi_h_pt": (p, None),
            "temporal_user_h_ut": (u, None),
            "geography": (p, p),
            "transition_h_src": (p, None),
        }
        for key, (rows, cols) in expected.items():
            shape = tuple(graphs[key].shape)
            if shape[0] != rows or (cols is not None and shape[1] != cols):
                raise ValueError("invalid shape for {}: {}".format(key, shape))

        paired = (
            ("temporal_poi_h_tp", "temporal_poi_h_pt"),
            ("temporal_user_h_tu", "temporal_user_h_ut"),
            ("transition_h_tar", "transition_h_src"),
        )
        for left, right in paired:
            if graphs[left].shape[0] != graphs[right].shape[1]:
                raise ValueError("incompatible graph pair: {} / {}".format(left, right))
            if graphs[left].shape[1] != graphs[right].shape[0]:
                raise ValueError("incompatible graph pair: {} / {}".format(left, right))

        if graphs["temporal_poi_h_tp"].shape[1] != p:
            raise ValueError("temporal POI incidence must end in POI coordinates")
        if graphs["temporal_user_h_tu"].shape[1] != u:
            raise ValueError("temporal user incidence must end in user coordinates")
        if graphs["transition_h_tar"].shape[1] != p:
            raise ValueError("transition target incidence must end in POI coordinates")

    @staticmethod
    def _gated(values: torch.Tensor, gate: nn.Linear) -> torch.Tensor:
        return values * torch.sigmoid(gate(values))

    def forward(
        self,
        user_ids: torch.Tensor,
        graphs: Mapping[str, torch.Tensor],
        return_aux: bool = False,
    ):
        self._validate_graphs(graphs)
        if user_ids.ndim != 1:
            raise ValueError("user_ids must be one-dimensional")
        if user_ids.numel() and (user_ids.min() < 0 or user_ids.max() >= self.num_users):
            raise ValueError("user_ids out of range")

        poi_base = self.poi_embedding.weight
        user_base = self.user_embedding.weight

        poi_inputs = {
            name: self._gated(poi_base, self.poi_view_gates[name])
            for name in ("collaborative", "temporal", "geography", "transition")
        }
        temporal_user_input = self._gated(user_base, self.temporal_user_input_gate)

        collaborative_poi = _residual_graph_stack(
            poi_inputs["collaborative"],
            graphs["collaborative_h_up"],
            graphs["collaborative_h_pu"],
            self.graph_layers,
            self.dropout,
            self.training,
        )
        temporal_poi = _residual_graph_stack(
            poi_inputs["temporal"],
            graphs["temporal_poi_h_tp"],
            graphs["temporal_poi_h_pt"],
            self.graph_layers,
            self.dropout,
            self.training,
        )
        temporal_user = _residual_graph_stack(
            temporal_user_input,
            graphs["temporal_user_h_tu"],
            graphs["temporal_user_h_ut"],
            self.graph_layers,
            self.dropout,
            self.training,
        )
        geography_poi = _residual_adjacency_stack(
            poi_inputs["geography"],
            graphs["geography"],
            self.graph_layers,
            0.0,
            self.training,
        )
        transition_poi = _residual_graph_stack(
            poi_inputs["transition"],
            graphs["transition_h_tar"],
            graphs["transition_h_src"],
            self.graph_layers,
            self.dropout,
            self.training,
        )

        collaborative_user_all = _matmul(
            graphs["collaborative_h_up"], collaborative_poi
        )
        geography_user_all = _matmul(graphs["collaborative_h_up"], geography_poi)
        transition_user_all = _matmul(
            graphs["collaborative_h_up"], transition_poi
        )

        poi_views = {
            "collaborative": F.normalize(collaborative_poi, p=2, dim=1),
            "temporal": F.normalize(temporal_poi, p=2, dim=1),
            "geography": F.normalize(geography_poi, p=2, dim=1),
            "transition": F.normalize(transition_poi, p=2, dim=1),
        }
        user_views = {
            "collaborative": F.normalize(collaborative_user_all[user_ids], p=2, dim=1),
            "temporal": F.normalize(temporal_user[user_ids], p=2, dim=1),
            "geography": F.normalize(geography_user_all[user_ids], p=2, dim=1),
            "transition": F.normalize(transition_user_all[user_ids], p=2, dim=1),
        }

        fused_user = sum(
            torch.sigmoid(self.user_view_gates[name](values)) * values
            for name, values in user_views.items()
        )
        fused_poi = sum(poi_views.values())
        logits = fused_user.matmul(fused_poi.transpose(0, 1))

        auxiliary = {
            "poi_views": poi_views,
            "user_views": user_views,
            "fused_user": fused_user,
            "fused_poi": fused_poi,
        }
        if return_aux:
            return logits, auxiliary
        return logits

    def cross_view_contrastive_loss(
        self, auxiliary: Mapping[str, Mapping[str, torch.Tensor]]
    ) -> torch.Tensor:
        losses: List[torch.Tensor] = []
        for view_scope in ("poi_views", "user_views"):
            views = auxiliary[view_scope]
            for left, right in combinations(sorted(views), 2):
                scores = views[left].matmul(views[right].transpose(0, 1))
                scores = scores / self.temperature
                targets = torch.arange(scores.shape[0], device=scores.device)
                losses.append(F.cross_entropy(scores, targets))
        return torch.stack(losses).sum()


class AdaptiveSplitMSAHG(nn.Module):
    """APS wrapper with explicit, optimizer-visible parameter banks."""

    def __init__(
        self,
        core: MSAHGPaperMathCore,
        tasks: Sequence[str] = TASKS,
        conflict_threshold: float = -0.5,
    ) -> None:
        super().__init__()
        if len(tasks) != len(set(tasks)) or not tasks:
            raise ValueError("tasks must be non-empty and unique")
        self.core = core
        self.tasks = tuple(tasks)
        self.conflict_threshold = float(conflict_threshold)
        self.split_parameters = nn.ParameterDict()
        self._topology: Dict[str, Tuple[Tuple[str, ...], ...]] = {}
        self._task_keys: Dict[str, Dict[str, str]] = {}

    @staticmethod
    def _bank_key(parameter_name: str, group_index: int) -> str:
        digest = hashlib.sha256(parameter_name.encode("utf-8")).hexdigest()[:16]
        return "p_{}_g{}".format(digest, group_index)

    def _core_parameter(self, name: str) -> nn.Parameter:
        parameters = dict(self.core.named_parameters())
        if name not in parameters:
            raise KeyError("unknown core parameter: {}".format(name))
        return parameters[name]

    def split_parameter(
        self, parameter_name: str, task_groups: Sequence[Sequence[str]]
    ) -> None:
        if parameter_name in self._topology:
            raise ValueError("parameter already split: {}".format(parameter_name))
        normalized = tuple(tuple(group) for group in task_groups)
        if len(normalized) < 2 or any(not group for group in normalized):
            raise ValueError("a split requires at least two non-empty groups")
        flattened = tuple(task for group in normalized for task in group)
        if len(flattened) != len(set(flattened)) or set(flattened) != set(self.tasks):
            raise ValueError("task groups must partition the registered tasks")

        original = self._core_parameter(parameter_name)
        self._topology[parameter_name] = normalized
        self._task_keys[parameter_name] = {}
        for group_index, group in enumerate(normalized):
            key = self._bank_key(parameter_name, group_index)
            self.split_parameters[key] = nn.Parameter(original.detach().clone())
            for task in group:
                self._task_keys[parameter_name][task] = key
        original.requires_grad_(False)

    def split_topology(self) -> Dict[str, Tuple[Tuple[str, ...], ...]]:
        return {name: tuple(groups) for name, groups in self._topology.items()}

    def restore_topology(
        self, topology: Mapping[str, Sequence[Sequence[str]]]
    ) -> None:
        if self._topology:
            raise ValueError("topology can only be restored into an unsplit wrapper")
        for name in sorted(topology):
            self.split_parameter(name, topology[name])

    def overrides_for(self, task: str) -> Dict[str, torch.Tensor]:
        if task not in self.tasks:
            raise KeyError("unknown task: {}".format(task))
        return {
            name: self.split_parameters[task_keys[task]]
            for name, task_keys in self._task_keys.items()
        }

    def forward(
        self,
        task: str,
        user_ids: torch.Tensor,
        graphs: Mapping[str, torch.Tensor],
        return_aux: bool = False,
    ):
        overrides = self.overrides_for(task)
        if not overrides:
            return self.core(user_ids, graphs, return_aux=return_aux)
        return functional_call(
            self.core,
            overrides,
            (user_ids, graphs),
            {"return_aux": return_aux},
            strict=False,
        )

    def optimizer_parameters(self) -> List[nn.Parameter]:
        parameters: List[nn.Parameter] = []
        seen = set()
        for parameter in self.parameters():
            if parameter.requires_grad and id(parameter) not in seen:
                parameters.append(parameter)
                seen.add(id(parameter))
        return parameters

    def optimizer_parameter_ids(self) -> Tuple[int, ...]:
        return tuple(id(parameter) for parameter in self.optimizer_parameters())

    @staticmethod
    def gradient_cosines(
        task_losses: Sequence[torch.Tensor], parameter: nn.Parameter
    ) -> torch.Tensor:
        gradients: List[torch.Tensor] = []
        for loss in task_losses:
            gradient = torch.autograd.grad(
                loss, parameter, retain_graph=True, allow_unused=True
            )[0]
            if gradient is None:
                gradients.append(torch.zeros_like(parameter).reshape(-1))
            else:
                flattened = gradient.reshape(-1)
                gradients.append(flattened / flattened.norm().clamp_min(1e-12))
        return torch.stack(gradients).matmul(torch.stack(gradients).transpose(0, 1))

    def conflicting_pairs(self, similarities: torch.Tensor) -> Tuple[Tuple[int, int], ...]:
        if similarities.ndim != 2 or similarities.shape[0] != similarities.shape[1]:
            raise ValueError("similarities must be square")
        pairs = []
        for left in range(similarities.shape[0]):
            for right in range(left + 1, similarities.shape[1]):
                if float(similarities[left, right]) < self.conflict_threshold:
                    pairs.append((left, right))
        return tuple(pairs)


def recommendation_objective(
    core: MSAHGPaperMathCore,
    logits: torch.Tensor,
    auxiliary: Mapping[str, Mapping[str, torch.Tensor]],
    targets: torch.Tensor,
    lambda_cl: float = 0.1,
) -> torch.Tensor:
    if not 0.0 <= lambda_cl <= 1.0:
        raise ValueError("lambda_cl must be in [0, 1]")
    recommendation = F.cross_entropy(logits, targets)
    contrastive = core.cross_view_contrastive_loss(auxiliary)
    return (1.0 - lambda_cl) * recommendation + lambda_cl * contrastive
