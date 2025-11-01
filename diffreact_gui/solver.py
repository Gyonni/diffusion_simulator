from __future__ import annotations

"""Crank–Nicolson solver for multilayer 1D diffusion–reaction."""

import logging
from typing import Callable, Dict, List, Optional, Tuple

import numpy as np

from .models import LayerParam, SimParams
from .physics import char_length_ell
from .utils import cumulative_trapz

logger = logging.getLogger(__name__)

# Numerical stability constants
ZERO_PIVOT_TOLERANCE = 1e-14
STABILITY_FACTOR = 0.45
MIN_DT_FACTOR = 1e-9
DT_REDUCTION_FACTOR = 1e-6
DT_HALVING_FACTOR = 0.5
MASS_BALANCE_TOLERANCE = 0.01
EPSILON_SMALL = 1e-12
EPSILON_DIFFUSIVITY = 1e-30


class TridiagonalSolveError(np.linalg.LinAlgError):
    """Raised when the tridiagonal solver encounters a singular pivot."""


def _thomas_solve(a: np.ndarray, b: np.ndarray, c: np.ndarray, d: np.ndarray) -> np.ndarray:
    """Solve a tridiagonal linear system using the Thomas algorithm.

    Args:
        a: Lower diagonal coefficients
        b: Main diagonal coefficients
        c: Upper diagonal coefficients
        d: Right-hand side vector

    Returns:
        Solution vector x

    Raises:
        TridiagonalSolveError: If a zero pivot is encountered
    """
    n = len(b)
    cp = np.empty_like(c)
    dp = np.empty_like(d)

    if abs(b[0]) < ZERO_PIVOT_TOLERANCE:
        raise TridiagonalSolveError("Zero pivot at first row")
    cp[0] = c[0] / b[0]
    dp[0] = d[0] / b[0]

    for i in range(1, n):
        denom = b[i] - a[i] * cp[i - 1]
        if abs(denom) < ZERO_PIVOT_TOLERANCE:
            raise TridiagonalSolveError(f"Zero pivot at row {i}")
        cp[i] = c[i] / denom if i < n - 1 else 0.0
        dp[i] = (d[i] - a[i] * dp[i - 1]) / denom

    x = np.empty_like(d)
    x[-1] = dp[-1]
    for i in range(n - 2, -1, -1):
        x[i] = dp[i] - cp[i] * x[i + 1]
    return x


def _harmonic_mean(a: float, b: float) -> float:
    """Compute harmonic mean of two values.

    Args:
        a: First value
        b: Second value

    Returns:
        Harmonic mean: 2ab/(a+b), or a if a==b, or 0 if both are zero
    """
    if a == b:
        return a
    denom = a + b
    if denom == 0.0:
        return 0.0
    return 2.0 * a * b / denom


def _build_grid(layers: List[LayerParam]) -> Tuple[np.ndarray, np.ndarray, np.ndarray, List[Dict[str, int]], np.ndarray]:
    """Create node coordinates and property arrays for the layer stack."""

    x_values: List[float] = []
    D_nodes: List[float] = []
    k_nodes: List[float] = []
    layer_meta: List[Dict[str, int]] = []

    position = 0.0
    cumulative = 0.0
    boundaries = [0.0]
    for idx, layer in enumerate(layers):
        local = np.linspace(0.0, layer.thickness, layer.nodes, endpoint=True)
        if idx == 0:
            nodes = position + local
        else:
            nodes = position + local[1:]

        start_idx = len(x_values)
        x_values.extend(nodes.tolist())
        D_nodes.extend([layer.diffusivity] * len(nodes))
        k_nodes.extend([layer.reaction_rate] * len(nodes))
        end_idx = len(x_values) - 1

        layer_meta.append(
            {
                "name": layer.name,
                "start_idx": start_idx,
                "end_idx": end_idx,
                "start_with_interface": start_idx if idx == 0 else max(start_idx - 1, 0),
            }
        )

        position += layer.thickness
        cumulative += layer.thickness
        boundaries.append(cumulative)

    x = np.array(x_values, dtype=float)
    D_arr = np.array(D_nodes, dtype=float)
    k_arr = np.array(k_nodes, dtype=float)
    boundaries_arr = np.array(boundaries, dtype=float)
    return x, D_arr, k_arr, layer_meta, boundaries_arr


def _compute_edge_diffusivity(D_nodes: np.ndarray) -> np.ndarray:
    """Compute edge-centered diffusivities using harmonic mean.

    Args:
        D_nodes: Diffusivity values at grid nodes

    Returns:
        Edge-centered diffusivity array (length N-1)
    """
    return np.array(
        [_harmonic_mean(D_nodes[i], D_nodes[i + 1]) for i in range(len(D_nodes) - 1)],
        dtype=float
    )


def _assemble_system(
    x: np.ndarray,
    D_nodes: np.ndarray,
    k_nodes: np.ndarray,
    dt: float,
    bc_right: str,
) -> Tuple[
    np.ndarray,
    np.ndarray,
    np.ndarray,
    np.ndarray,
    np.ndarray,
    np.ndarray,
    np.ndarray,
]:
    """Build LHS/RHS coefficients for Crank–Nicolson on a non-uniform grid."""

    N = len(x)
    if N < 2:
        raise ValueError("Grid must contain at least two nodes")

    dx = np.diff(x)
    D_edges = _compute_edge_diffusivity(D_nodes)

    aL = np.zeros(N)
    bL = np.zeros(N)
    cL = np.zeros(N)
    aR = np.zeros(N)
    bR = np.zeros(N)
    cR = np.zeros(N)
    # Left Dirichlet boundary
    aL[0] = 0.0
    bL[0] = 1.0
    cL[0] = 0.0
    aR[0] = 0.0
    bR[0] = 0.0
    cR[0] = 0.0

    for i in range(1, N - 1):
        dx_w = dx[i - 1]
        dx_e = dx[i]
        denom = dx_w + dx_e
        D_w = D_edges[i - 1]
        D_e = D_edges[i]
        alpha = 2.0 * D_w / (dx_w * denom)
        gamma = 2.0 * D_e / (dx_e * denom)
        k_i = k_nodes[i]

        aL[i] = -0.5 * dt * alpha
        cL[i] = -0.5 * dt * gamma
        bL[i] = 1.0 + 0.5 * dt * (alpha + gamma + k_i)

        aR[i] = 0.5 * dt * alpha
        cR[i] = 0.5 * dt * gamma
        bR[i] = 1.0 - 0.5 * dt * (alpha + gamma + k_i)

    if bc_right == "Dirichlet":
        aL[-1] = 0.0
        bL[-1] = 1.0
        cL[-1] = 0.0
        aR[-1] = 0.0
        bR[-1] = 0.0
        cR[-1] = 0.0
    elif bc_right == "Neumann":
        aL[-1] = -1.0
        bL[-1] = 1.0
        cL[-1] = 0.0
        aR[-1] = 0.0
        bR[-1] = 0.0
        cR[-1] = 0.0
    else:
        raise ValueError(f"Unsupported right boundary: {bc_right}")

    return aL, bL, cL, aR, bR, cR, D_edges


def _compute_flux(
    x: np.ndarray,
    D_edges: np.ndarray,
    C: np.ndarray,
    *,
    interface_idx: int | None,
) -> Tuple[float, float, float]:
    """Compute flux at source, end, and target interface."""

    dx_source = x[1] - x[0]
    J_source = -D_edges[0] * (C[1] - C[0]) / dx_source

    dx_end = x[-1] - x[-2]
    J_end = -D_edges[-1] * (C[-1] - C[-2]) / dx_end

    if interface_idx is not None:
        dx_target = x[interface_idx + 1] - x[interface_idx]
        D_target = D_edges[interface_idx]
        J_target = -D_target * (C[interface_idx + 1] - C[interface_idx]) / dx_target
    else:
        J_target = J_end

    return J_source, J_end, J_target


def run_simulation(
    params: SimParams,
    max_retries: int = 6,
    progress_callback: Optional[Callable[[float], None]] = None,
) -> Dict[str, np.ndarray | Dict[str, float] | List[str]]:
    """Run the multilayer diffusion–reaction simulation."""

    layers = params.layers
    Cs = params.Cs
    dt = params.dt
    requested_dt = dt
    t_max = params.t_max
    bc_right = params.bc_right

    x, D_nodes, k_nodes, layer_meta, boundaries = _build_grid(layers)
    N = len(x)

    # Indexing helpers for the target (final) layer
    target_meta = layer_meta[-1]
    target_start = target_meta["start_idx"]
    target_start_inclusive = target_meta["start_with_interface"]
    target_end = target_meta["end_idx"]
    interface_idx = target_start - 1 if target_start > 0 else None

    attempts = 0
    dx_all = np.diff(x)
    if dx_all.size > 0:
        D_edges_nominal = _compute_edge_diffusivity(D_nodes)
        with np.errstate(divide="ignore", invalid="ignore"):
            ratio = (dx_all ** 2) / np.maximum(D_edges_nominal, EPSILON_DIFFUSIVITY)
        finite_ratio = ratio[np.isfinite(ratio) & (ratio > 0)]
        if finite_ratio.size > 0:
            recommended_dt = STABILITY_FACTOR * float(np.min(finite_ratio))
            if dt > recommended_dt:
                logger.warning(
                    "Time step %.3e exceeds stability recommendation %.3e based on spatial resolution; clamping.",
                    dt,
                    recommended_dt,
                )
                dt = recommended_dt
    current_dt = dt

    dirichlet_right_value = 0.0 if bc_right == "Dirichlet" else None

    while True:
        attempts += 1
        try:
            n_steps = int(np.floor(t_max / current_dt)) + 1
            t = np.linspace(0.0, current_dt * (n_steps - 1), n_steps)

            aL, bL, cL, aR, bR, cR, D_edges = _assemble_system(
                x, D_nodes, k_nodes, current_dt, bc_right
            )

            C = np.zeros(N)
            C[0] = Cs
            if bc_right == "Dirichlet":
                C[-1] = dirichlet_right_value if dirichlet_right_value is not None else 0.0
            elif bc_right == "Neumann" and N > 1:
                C[-1] = C[-2]

            C_xt = np.zeros((n_steps, N))
            J_source = np.zeros(n_steps)
            J_end = np.zeros(n_steps)
            J_target = np.zeros(n_steps)
            mass_target = np.zeros(n_steps)

            C_xt[0] = C.copy()
            J_source[0], J_end[0], J_target[0] = _compute_flux(x, D_edges, C, interface_idx=interface_idx)

            x_target = x[target_start_inclusive : target_end + 1]
            mass_target[0] = np.trapz(C[target_start_inclusive : target_end + 1], x_target)

            rhs = np.zeros(N)

            if progress_callback is not None:
                progress_callback(0.0)

            for idx_t in range(1, n_steps):
                rhs[0] = Cs
                if bc_right == "Dirichlet":
                    rhs[-1] = dirichlet_right_value if dirichlet_right_value is not None else 0.0
                else:
                    rhs[-1] = 0.0

                rhs[1:-1] = (
                    aR[1:-1] * C[:-2]
                    + bR[1:-1] * C[1:-1]
                    + cR[1:-1] * C[2:]
                )

                C = _thomas_solve(aL, bL, cL, rhs)

                C[0] = Cs
                if bc_right == "Dirichlet":
                    C[-1] = dirichlet_right_value if dirichlet_right_value is not None else 0.0
                elif bc_right == "Neumann":
                    C[-1] = C[-2]

                C_xt[idx_t] = C
                J_source[idx_t], J_end[idx_t], J_target[idx_t] = _compute_flux(
                    x, D_edges, C, interface_idx=interface_idx
                )
                mass_target[idx_t] = np.trapz(
                    C[target_start_inclusive : target_end + 1], x[target_start_inclusive : target_end + 1]
                )

                if progress_callback is not None and n_steps > 1:
                    progress_callback(idx_t / (n_steps - 1))

            cum_source = cumulative_trapz(J_source, t)
            cum_end = cumulative_trapz(J_end, t)
            cum_target = cumulative_trapz(J_target, t)

            diagnostics: Dict[str, float] = {
                "min_dx": float(np.min(np.diff(x))),
                "total_thickness": float(boundaries[-1]),
                "dt_used": float(current_dt),
                "dt_requested": float(requested_dt),
            }

            target_layer = layers[-1]
            ell = char_length_ell(target_layer.diffusivity, target_layer.reaction_rate)
            if not np.isinf(ell):
                dx_target = np.diff(x[target_start_inclusive : target_end + 1])
                if dx_target.size > 0:
                    diagnostics["ell_over_dx_min"] = float(ell / np.min(dx_target))
                diagnostics["ell"] = float(ell)

            if progress_callback is not None:
                progress_callback(1.0)

            return {
                "t": t,
                "x": x,
                "C_xt": C_xt,
                "J_source": J_source,
                "J_end": J_end,
                "J_target": J_target,
                "cum_source": cum_source,
                "cum_end": cum_end,
                "cum_target": cum_target,
                "mass_target": mass_target,
                "layer_boundaries": boundaries,
                "layer_names": [layer.name for layer in layers],
                "diagnostics": diagnostics,
                "k_profile": k_nodes,
                "D_nodes": D_nodes,
                "D_edges": D_edges,
                "target_indices": {
                    "start_inclusive": target_start_inclusive,
                    "end": target_end,
                },
            }

        except (TridiagonalSolveError, np.linalg.LinAlgError) as exc:
            dt_min = max(MIN_DT_FACTOR, DT_REDUCTION_FACTOR * t_max)
            if current_dt <= dt_min or attempts > max_retries:
                logger.error("Solver failed after %d attempts: %s", attempts, exc)
                raise
            logger.warning(
                "Solver failed (attempt %d): %s. Halving dt to improve stability.",
                attempts,
                exc,
            )
            current_dt *= DT_HALVING_FACTOR


def mass_balance_diagnostics(
    k_profile: np.ndarray,
    t: np.ndarray,
    x: np.ndarray,
    C_xt: np.ndarray,
    J_source: np.ndarray,
    J_end: np.ndarray,
    *,
    return_components: bool = False,
) -> Tuple[float, float] | Tuple[float, float, Dict[str, float]]:
    """Compute mass-balance residual and relative error for the stack."""

    int_J_source = cumulative_trapz(J_source, t)[-1]
    int_J_end = cumulative_trapz(J_end, t)[-1]

    spatial_integrals = np.trapz(C_xt * k_profile[None, :], x, axis=1)
    int_kC = np.trapz(spatial_integrals, t)

    total_change = np.trapz(C_xt[-1], x) - np.trapz(C_xt[0], x)

    residual = int_J_source - int_J_end - int_kC - total_change
    scale = max(
        abs(total_change),
        abs(int_J_source),
        abs(int_J_end),
        abs(int_kC),
        EPSILON_SMALL,
    )
    rel_error = abs(residual) / scale

    components = {
        "int_J_source": float(int_J_source),
        "int_J_end": float(int_J_end),
        "int_kC": float(int_kC),
        "total_change": float(total_change),
    }

    if return_components:
        return residual, rel_error, components
    return residual, rel_error
