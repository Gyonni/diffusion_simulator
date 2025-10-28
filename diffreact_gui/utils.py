from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict
from typing import Any, Dict

import numpy as np

from .config import RESULTS_DIR, LOG_LEVEL
from .models import SimParams


def setup_logging(level: str = LOG_LEVEL) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


def validate_params(p: SimParams) -> None:
    if not p.layers:
        raise ValueError("At least one layer must be specified")
    total_length = 0.0
    for idx, layer in enumerate(p.layers):
        if layer.thickness <= 0:
            raise ValueError(f"Layer {idx + 1} thickness must be positive")
        if layer.diffusivity <= 0:
            raise ValueError(f"Layer {idx + 1} diffusivity must be positive")
        if layer.reaction_rate < 0:
            raise ValueError(f"Layer {idx + 1} reaction rate must be non-negative")
        if layer.nodes < 2:
            raise ValueError(f"Layer {idx + 1} nodes must be >= 2")
        total_length += layer.thickness
    if total_length <= 0:
        raise ValueError("Total stack thickness must be positive")
    if p.dt <= 0:
        raise ValueError("dt must be positive")
    if p.t_max <= 0:
        raise ValueError("t_max must be positive")
    if p.Cs < 0:
        raise ValueError("Cs must be non-negative")
    if p.bc_right not in {"Neumann", "Dirichlet"}:
        raise ValueError("bc_right must be one of: Neumann, Dirichlet")


def ensure_results_dir(path: str = RESULTS_DIR) -> str:
    os.makedirs(path, exist_ok=True)
    return path


def cumulative_trapz(y: np.ndarray, x: np.ndarray) -> np.ndarray:
    """Return cumulative trapezoidal integral of y(x).

    Parameters
    - y: shape (N,) array
    - x: shape (N,) array, strictly increasing
    """
    if y.shape != x.shape:
        raise ValueError("y and x must have the same shape")
    out = np.zeros_like(y)
    for i in range(1, len(y)):
        out[i] = out[i - 1] + 0.5 * (y[i] + y[i - 1]) * (x[i] - x[i - 1])
    return out


def save_results_npz(
    base_path: str,
    *,
    t: np.ndarray,
    x: np.ndarray,
    C_xt: np.ndarray,
    J_source: np.ndarray,
    J_target: np.ndarray,
    J_end: np.ndarray,
    cum_source: np.ndarray,
    cum_target: np.ndarray,
    cum_end: np.ndarray,
    mass_target: np.ndarray,
    layer_boundaries: np.ndarray,
    D_nodes: np.ndarray | None = None,
    D_edges: np.ndarray | None = None,
    J_probe: np.ndarray | None = None,
    cum_probe: np.ndarray | None = None,
    probe_position: float | None = None,
) -> str:
    npz_path = os.path.join(base_path, "results.npz")
    payload: Dict[str, Any] = {
        "t": t,
        "x": x,
        "C_xt": C_xt,
        "J_source": J_source,
        "J_target": J_target,
        "J_end": J_end,
        "cum_source": cum_source,
        "cum_target": cum_target,
        "cum_end": cum_end,
        "mass_target": mass_target,
        "layer_boundaries": layer_boundaries,
    }
    if D_nodes is not None:
        payload["D_nodes"] = D_nodes
    if D_edges is not None:
        payload["D_edges"] = D_edges
    if J_probe is not None:
        payload["J_probe"] = J_probe
    if cum_probe is not None:
        payload["cum_probe"] = cum_probe
    if probe_position is not None:
        payload["probe_position"] = probe_position
    np.savez(npz_path, **payload)
    return npz_path


def save_csv_flux(
    base_path: str,
    t: np.ndarray,
    J_source: np.ndarray,
    J_target: np.ndarray,
    J_end: np.ndarray,
    cum_source: np.ndarray,
    cum_target: np.ndarray,
    cum_end: np.ndarray,
    mass_target: np.ndarray,
    *,
    J_probe: np.ndarray | None = None,
    cum_probe: np.ndarray | None = None,
) -> str:
    csv_path = os.path.join(base_path, "flux_vs_time.csv")
    columns = [
        t,
        J_source,
        J_target,
        J_end,
        cum_source,
        cum_target,
        cum_end,
        mass_target,
    ]
    header = [
        "t[s]",
        "Flux_surface[mol/(m^2*s)]",
        "Flux_target_interface[mol/(m^2*s)]",
        "Flux_exit[mol/(m^2*s)]",
        "Cum_flux_surface[mol/m^2]",
        "Cum_flux_target_interface[mol/m^2]",
        "Cum_flux_exit[mol/m^2]",
        "Mass_target[mol/m^2]",
    ]
    if J_probe is not None and J_probe.size:
        columns.append(J_probe)
        header.append("Flux_probe[mol/(m^2*s)]")
    if cum_probe is not None and cum_probe.size:
        columns.append(cum_probe)
        header.append("Cum_flux_probe[mol/m^2]")
    data = np.column_stack(columns)
    header_line = ",".join(header)
    np.savetxt(csv_path, data, delimiter=",", header=header_line, comments="")
    return csv_path


def save_csv_profile(base_path: str, x: np.ndarray, C: np.ndarray, t_value: float) -> str:
    csv_path = os.path.join(base_path, f"profile_t_{t_value:.6g}s.csv")
    header = "x[m],C[mol/m^3]"
    data = np.column_stack([x, C])
    np.savetxt(csv_path, data, delimiter=",", header=header, comments="")
    return csv_path


def save_profiles_matrix(base_path: str, x: np.ndarray, t: np.ndarray, C_xt: np.ndarray) -> str:
    csv_path = os.path.join(base_path, "concentration_profiles.csv")
    header = ["x[m]"] + [f"C(t={ti:.6g}s)[mol/m^3]" for ti in t]
    data = np.column_stack([x, C_xt.T])
    np.savetxt(csv_path, data, delimiter=",", header=",".join(header), comments="")
    return csv_path


def save_metadata(base_path: str, params: SimParams, extras: Dict[str, Any] | None = None) -> str:
    meta_path = os.path.join(base_path, "metadata.json")
    payload: Dict[str, Any] = asdict(params)
    if extras:
        payload.update(extras)
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    return meta_path
