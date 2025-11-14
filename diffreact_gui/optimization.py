"""Parameter optimization module for fitting simulation to experimental data.

This module provides grid search and optimization algorithms to find
optimal diffusivity (D0, Ea) and reaction rate (k) parameters that best
match experimental data.
"""
from __future__ import annotations

import copy
import itertools
import time
import threading
from dataclasses import dataclass
from typing import Dict, List, Tuple, Any, Optional, Callable

import numpy as np

from .models import LayerParam, SimParams, ExperimentalData
from .solver import run_temperature_sweep
from .analysis import calculate_global_fit_metrics


@dataclass
class ParamSpec:
    """Specification for a parameter to optimize.

    Attributes:
        name: Parameter name ("D0", "Ea", or "k")
        min_val: Minimum value
        max_val: Maximum value
        n_points: Number of grid points
        scale: "linear" or "log" spacing
        layer_idx: Which layer this parameter belongs to
    """
    name: str
    min_val: float
    max_val: float
    n_points: int
    scale: str = "linear"  # "linear" or "log"
    layer_idx: int = 0


@dataclass
class OptimizationResult:
    """Container for optimization results.

    Attributes:
        best_params: Dictionary of best parameter values {(layer_idx, param_name): value}
        best_score: Best fitness score achieved
        best_layers: Layer parameters with optimal values applied
        all_params: Array of all parameter combinations tested (n_combinations, n_params)
        all_scores: Array of fitness scores for each combination (n_combinations,)
        param_names: List of parameter names in order
        metric_name: Name of metric used ("r_squared", "rmse", etc.)
        elapsed_time: Total optimization time in seconds
        n_simulations: Number of simulations run
        success: Whether optimization completed successfully
        message: Status or error message
    """
    best_params: Dict[Tuple[int, str], float]
    best_score: float
    best_layers: List[LayerParam]
    all_params: np.ndarray
    all_scores: np.ndarray
    param_names: List[Tuple[int, str]]
    metric_name: str
    elapsed_time: float
    n_simulations: int
    success: bool
    message: str


def generate_grid(param_specs: List[ParamSpec]) -> Tuple[np.ndarray, List[Tuple[int, str]]]:
    """
    Generate parameter grid for grid search.

    Args:
        param_specs: List of parameter specifications

    Returns:
        Tuple of:
            - grid: Array of parameter combinations (n_combinations, n_params)
            - param_names: List of (layer_idx, param_name) tuples
    """
    param_ranges = []
    param_names = []

    for spec in param_specs:
        if spec.scale == "log":
            values = np.logspace(np.log10(spec.min_val), np.log10(spec.max_val), spec.n_points)
        else:
            values = np.linspace(spec.min_val, spec.max_val, spec.n_points)

        param_ranges.append(values)
        param_names.append((spec.layer_idx, spec.name))

    # Create meshgrid and reshape to (n_combinations, n_params)
    meshes = np.meshgrid(*param_ranges, indexing='ij')
    grid = np.column_stack([mesh.ravel() for mesh in meshes])

    return grid, param_names


def apply_params_to_layers(
    base_layers: List[LayerParam],
    param_values: np.ndarray,
    param_names: List[Tuple[int, str]]
) -> List[LayerParam]:
    """
    Apply parameter values to layer specifications.

    Args:
        base_layers: Original layer parameters
        param_values: Array of parameter values (n_params,)
        param_names: List of (layer_idx, param_name) tuples

    Returns:
        New list of LayerParam with updated values
    """
    # Deep copy to avoid modifying original
    layers = copy.deepcopy(base_layers)

    for param_val, (layer_idx, param_name) in zip(param_values, param_names):
        layer = layers[layer_idx]

        # Create new LayerParam with updated value
        kwargs = {
            'name': layer.name,
            'thickness': layer.thickness,
            'diffusivity': layer.diffusivity,
            'reaction_rate': layer.reaction_rate,
            'nodes': layer.nodes,
            'D0': layer.D0,
            'Ea': layer.Ea,
        }

        if param_name == "D0":
            kwargs['D0'] = param_val
        elif param_name == "Ea":
            kwargs['Ea'] = param_val
        elif param_name == "k":
            kwargs['reaction_rate'] = param_val
        else:
            raise ValueError(f"Unknown parameter: {param_name}")

        layers[layer_idx] = LayerParam(**kwargs)

    return layers


def run_grid_search_optimization(
    exp_data: ExperimentalData,
    base_layers: List[LayerParam],
    base_sim_params: SimParams,
    temperatures: List[float],
    param_specs: List[ParamSpec],
    sim_y_var: str = "C",
    metric: str = "r_squared",
    progress_callback: Optional[Callable[[int, int, float], None]] = None,
    abort_flag: Optional[threading.Event] = None
) -> OptimizationResult:
    """
    Run grid search optimization to find best parameters.

    Args:
        exp_data: Experimental data to fit
        base_layers: Base layer parameters (will be modified during optimization)
        base_sim_params: Simulation parameters
        temperatures: List of temperatures for sweep
        param_specs: List of parameter specifications to optimize
        sim_y_var: Simulation variable to compare ("C", "J_target", etc.)
        metric: Fitness metric ("r_squared" to maximize, "rmse"/"nrmse" to minimize)
        progress_callback: Optional callback(current, total, best_score) for progress updates
        abort_flag: Optional threading.Event to abort optimization

    Returns:
        OptimizationResult with best parameters and full results

    Example:
        >>> param_specs = [
        ...     ParamSpec("D0", 1e-8, 1e-6, 10, "log", layer_idx=0),
        ...     ParamSpec("Ea", 0.5, 2.0, 10, "linear", layer_idx=0),
        ...     ParamSpec("k", 0.0, 100.0, 5, "linear", layer_idx=1),
        ... ]
        >>> result = run_grid_search_optimization(
        ...     exp_data, layers, sim_params, [600, 700, 800], param_specs
        ... )
        >>> print(f"Best D0: {result.best_params[(0, 'D0')]:.2e}")
    """
    start_time = time.time()

    # Generate parameter grid
    param_grid, param_names = generate_grid(param_specs)
    n_combinations = len(param_grid)

    print(f"[INFO] Grid search: {n_combinations} combinations to test")
    print(f"[INFO] Parameters: {param_names}")

    # Storage for results
    all_scores = np.zeros(n_combinations)
    best_score = -np.inf if metric == "r_squared" else np.inf
    best_idx = 0

    # Run simulations for each parameter combination
    for i, param_values in enumerate(param_grid):
        # Check abort flag
        if abort_flag and abort_flag.is_set():
            elapsed = time.time() - start_time
            return OptimizationResult(
                best_params={},
                best_score=0.0,
                best_layers=base_layers,
                all_params=param_grid[:i],
                all_scores=all_scores[:i],
                param_names=param_names,
                metric_name=metric,
                elapsed_time=elapsed,
                n_simulations=i,
                success=False,
                message="Optimization aborted by user"
            )

        # Apply parameters to layers
        layers = apply_params_to_layers(base_layers, param_values, param_names)

        try:
            # Run temperature sweep simulation
            sim_results = run_temperature_sweep(
                layers=layers,
                sim_params=base_sim_params,
                temperatures=temperatures,
                abort_flag=abort_flag
            )

            # Calculate fitness metric
            metrics = calculate_global_fit_metrics(
                sim_results=sim_results,
                exp_data=exp_data,
                sim_y_var=sim_y_var,
                is_temperature_sweep=True
            )

            # Check for errors in metrics
            if "error" in metrics:
                print(f"[WARNING] Combination {i} has data issue: {metrics['error']}")

            if metric == "r_squared":
                score = metrics["r_squared"]
                all_scores[i] = score
                # Log if score is 0
                if score == 0.0 and i == 0:
                    print(f"[WARNING] First combination has R²=0. Check:")
                    print(f"  - sim_y_var='{sim_y_var}' matches experimental data units")
                    print(f"  - Simulation values: mean={metrics['mean_sim']:.3e}")
                    print(f"  - Experimental values: mean={metrics['mean_exp']:.3e}")
                if score > best_score:
                    best_score = score
                    best_idx = i
            elif metric == "rmse":
                # RMSE: lower is better, so negate for comparison
                score = -metrics["nrmse"]  # Use NRMSE instead of raw RMSE
                all_scores[i] = -score  # Store positive NRMSE
                if score > best_score:
                    best_score = score
                    best_idx = i
            elif metric == "nrmse":
                score = -metrics["nrmse"]  # Negate because lower is better
                all_scores[i] = -score  # Store positive NRMSE
                if score > best_score:
                    best_score = score
                    best_idx = i
            else:
                raise ValueError(f"Unknown metric: {metric}")

            # Progress callback
            if progress_callback:
                actual_best_score = best_score if metric == "r_squared" else -best_score
                progress_callback(i + 1, n_combinations, actual_best_score)

            # Log progress every 10%
            if (i + 1) % max(1, n_combinations // 10) == 0:
                pct = 100 * (i + 1) / n_combinations
                actual_best_score = best_score if metric == "r_squared" else -best_score
                print(f"[INFO] Progress: {pct:.0f}% ({i+1}/{n_combinations}), Best {metric}: {actual_best_score:.4f}")

        except Exception as e:
            print(f"[WARNING] Simulation failed for combination {i}: {e}")
            all_scores[i] = -np.inf if metric == "r_squared" else np.inf
            continue

    # Extract best parameters
    best_param_values = param_grid[best_idx]
    best_params_dict = {name: val for name, val in zip(param_names, best_param_values)}
    best_layers = apply_params_to_layers(base_layers, best_param_values, param_names)

    elapsed_time = time.time() - start_time
    actual_best_score = best_score if metric == "r_squared" else -best_score

    print(f"[INFO] Optimization complete in {elapsed_time:.1f}s")
    print(f"[INFO] Best {metric}: {actual_best_score:.4f}")
    print(f"[INFO] Best parameters:")
    for (layer_idx, param_name), val in best_params_dict.items():
        print(f"  Layer {layer_idx} {param_name}: {val:.4e}")

    return OptimizationResult(
        best_params=best_params_dict,
        best_score=actual_best_score,
        best_layers=best_layers,
        all_params=param_grid,
        all_scores=all_scores,
        param_names=param_names,
        metric_name=metric,
        elapsed_time=elapsed_time,
        n_simulations=n_combinations,
        success=True,
        message=f"Grid search completed successfully. Tested {n_combinations} combinations."
    )


def estimate_optimization_time(
    param_specs: List[ParamSpec],
    single_sim_time: float = 2.0
) -> float:
    """
    Estimate total optimization time.

    Args:
        param_specs: List of parameter specifications
        single_sim_time: Estimated time for one simulation (seconds)

    Returns:
        Estimated total time in seconds
    """
    n_combinations = np.prod([spec.n_points for spec in param_specs])
    return n_combinations * single_sim_time
