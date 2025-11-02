"""
Doping analysis module for correlating experimental data with simulation results.

This module provides functions for:
- Capacitor model calculations (dq from voltage measurements)
- 3D interpolation of simulation data
- Data preparation for visualization
"""

from typing import Dict, List, Tuple, Optional
import numpy as np
from scipy.interpolate import RegularGridInterpolator

from .models import CapacitorParams, ExperimentalData


# Physical constant
EPSILON_0 = 8.854187817e-12  # F/m (Vacuum permittivity)


def calculate_capacitance(params: CapacitorParams) -> float:
    """
    Calculate capacitance from parallel plate capacitor model.

    Args:
        params: Capacitor parameters

    Returns:
        Capacitance in Farads [F]

    Formula:
        C = (epsilon_0 * epsilon_r * A) / d
    """
    return (EPSILON_0 * params.epsilon_r * params.A) / params.d


def calculate_dq(
    voltage: float,
    params: CapacitorParams,
    capacitance: Optional[float] = None
) -> float:
    """
    Calculate charge change from voltage measurement.

    Args:
        voltage: Measured voltage [V]
        params: Capacitor parameters
        capacitance: Pre-calculated capacitance [F] (optional, will calculate if not provided)

    Returns:
        Charge change dq in Coulombs [C]

    Formula:
        dq = C * (V - V0)
    """
    if capacitance is None:
        capacitance = calculate_capacitance(params)

    return capacitance * (voltage - params.V0)


def calculate_dq_grid(
    voltage_grid: np.ndarray,
    params: CapacitorParams
) -> np.ndarray:
    """
    Calculate charge changes for entire voltage grid.

    Args:
        voltage_grid: 2D array of voltage measurements [row, col] in V
        params: Capacitor parameters

    Returns:
        2D array of charge changes [row, col] in C
    """
    capacitance = calculate_capacitance(params)
    return capacitance * (voltage_grid - params.V0)


def interpolate_simulation_data(
    sim_results: Dict,
    target_temps: np.ndarray,
    target_times: np.ndarray,
    target_positions: np.ndarray,
    variable: str,
    is_temperature_sweep: bool = True
) -> np.ndarray:
    """
    Interpolate simulation data to target 3D points using linear interpolation.

    Args:
        sim_results: Simulation results dictionary (from run_simulation or run_temperature_sweep)
        target_temps: Target temperature values [K] (1D array)
        target_times: Target time values [s] (1D array)
        target_positions: Target position values [m] (1D array)
        variable: Variable to interpolate. Options:
            - "C": Concentration
            - "J_source": Flux at x=0
            - "J_end": Flux at x=L
            - "J_target": Flux at interface
            - "J_probe": Flux at probe position (if available)
            - "cum_source": Cumulative uptake at x=0
            - "cum_end": Cumulative uptake at x=L
            - "cum_target": Cumulative at interface
            - "mass_target": Mass in target layer
        is_temperature_sweep: True if sim_results is from run_temperature_sweep()

    Returns:
        1D array of interpolated values at each (temp, time, pos) triplet

    Raises:
        ValueError: If variable is not found in sim_results
        ValueError: If arrays have incompatible shapes

    Note:
        - All three target arrays must have the same length
        - Uses linear interpolation with extrapolation for points outside the grid
        - For single temperature simulations, provide the same temperature for all points
    """
    # Validate input arrays
    n_points = len(target_temps)
    if len(target_times) != n_points or len(target_positions) != n_points:
        raise ValueError(
            f"All target arrays must have same length. Got temps={len(target_temps)}, "
            f"times={len(target_times)}, positions={len(target_positions)}"
        )

    if n_points == 0:
        return np.array([])

    # Get simulation grid
    if is_temperature_sweep:
        temps = sim_results["temperatures"]
        times = sim_results["t"]
        positions = sim_results["x"]

        # Get 3D data based on variable
        if variable == "C":
            data_3d = sim_results["C_Txt"]  # [temp, time, x]
        elif variable == "J_source":
            # Flux data is [temp, time], need to broadcast for position
            flux_Tt = sim_results["J_surface_Tt"]
            # For flux, position doesn't matter (it's at boundary)
            # Create dummy 3D array by broadcasting
            data_3d = np.broadcast_to(
                flux_Tt[:, :, np.newaxis],
                (len(temps), len(times), len(positions))
            )
        elif variable == "J_end":
            flux_Tt = sim_results["J_end_Tt"]
            data_3d = np.broadcast_to(
                flux_Tt[:, :, np.newaxis],
                (len(temps), len(times), len(positions))
            )
        elif variable == "J_target":
            flux_Tt = sim_results["J_target_Tt"]
            data_3d = np.broadcast_to(
                flux_Tt[:, :, np.newaxis],
                (len(temps), len(times), len(positions))
            )
        elif variable == "J_probe":
            if "J_probe_Tt" not in sim_results:
                raise ValueError("J_probe not available in simulation results")
            flux_Tt = sim_results["J_probe_Tt"]
            data_3d = np.broadcast_to(
                flux_Tt[:, :, np.newaxis],
                (len(temps), len(times), len(positions))
            )
        elif variable == "cum_source":
            # Cumulative data: need to extract from results_by_temp
            # This is more complex, need to build 3D array
            cum_Tt = np.zeros((len(temps), len(times)))
            for i, T in enumerate(temps):
                cum_Tt[i, :] = sim_results["results_by_temp"][T]["cum_source"]
            data_3d = np.broadcast_to(
                cum_Tt[:, :, np.newaxis],
                (len(temps), len(times), len(positions))
            )
        elif variable == "cum_end":
            cum_Tt = np.zeros((len(temps), len(times)))
            for i, T in enumerate(temps):
                cum_Tt[i, :] = sim_results["results_by_temp"][T]["cum_end"]
            data_3d = np.broadcast_to(
                cum_Tt[:, :, np.newaxis],
                (len(temps), len(times), len(positions))
            )
        elif variable == "cum_target":
            cum_Tt = np.zeros((len(temps), len(times)))
            for i, T in enumerate(temps):
                cum_Tt[i, :] = sim_results["results_by_temp"][T]["cum_target"]
            data_3d = np.broadcast_to(
                cum_Tt[:, :, np.newaxis],
                (len(temps), len(times), len(positions))
            )
        elif variable == "mass_target":
            mass_Tt = np.zeros((len(temps), len(times)))
            for i, T in enumerate(temps):
                mass_Tt[i, :] = sim_results["results_by_temp"][T]["mass_target"]
            data_3d = np.broadcast_to(
                mass_Tt[:, :, np.newaxis],
                (len(temps), len(times), len(positions))
            )
        else:
            raise ValueError(f"Unknown variable: {variable}")

    else:
        # Single temperature simulation
        # Create pseudo temperature dimension
        # Use the unique temperature value from target_temps (all should be same for single temp)
        unique_temps = np.unique(target_temps)
        if len(unique_temps) == 1:
            temps = unique_temps  # Single value array
        else:
            # If multiple temperatures requested but only single temp simulation available,
            # use the first one as reference (interpolation will duplicate values)
            temps = np.array([target_temps[0]])
        times = sim_results["t"]
        positions = sim_results["x"]

        if variable == "C":
            # C_xt is [time, x], add temperature dimension
            data_3d = sim_results["C_xt"][np.newaxis, :, :]  # [1, time, x]
        elif variable == "J_source":
            flux_t = sim_results["J_source"]
            data_3d = np.broadcast_to(
                flux_t[np.newaxis, :, np.newaxis],
                (1, len(times), len(positions))
            )
        elif variable == "J_end":
            flux_t = sim_results["J_end"]
            data_3d = np.broadcast_to(
                flux_t[np.newaxis, :, np.newaxis],
                (1, len(times), len(positions))
            )
        elif variable == "J_target":
            flux_t = sim_results["J_target"]
            data_3d = np.broadcast_to(
                flux_t[np.newaxis, :, np.newaxis],
                (1, len(times), len(positions))
            )
        elif variable.startswith("cum_") or variable == "mass_target":
            scalar_t = sim_results[variable]
            data_3d = np.broadcast_to(
                scalar_t[np.newaxis, :, np.newaxis],
                (1, len(times), len(positions))
            )
        else:
            raise ValueError(f"Unknown variable: {variable}")

    # Debug logging
    print(f"[DEBUG interpolate_simulation_data] variable={variable}, is_temp_sweep={is_temperature_sweep}")
    print(f"[DEBUG interpolate_simulation_data] Simulation grid: temps={temps}, len={len(temps)}")
    print(f"[DEBUG interpolate_simulation_data] Simulation grid: times min={times.min():.3e}, max={times.max():.3e}, len={len(times)}")
    print(f"[DEBUG interpolate_simulation_data] Simulation grid: positions min={positions.min():.3e}, max={positions.max():.3e}, len={len(positions)}")
    print(f"[DEBUG interpolate_simulation_data] Target temps: min={target_temps.min():.3e}, max={target_temps.max():.3e}")
    print(f"[DEBUG interpolate_simulation_data] Target times: min={target_times.min():.3e}, max={target_times.max():.3e}")
    print(f"[DEBUG interpolate_simulation_data] Target positions: min={target_positions.min():.3e}, max={target_positions.max():.3e}")
    print(f"[DEBUG interpolate_simulation_data] data_3d shape: {data_3d.shape}, min={np.min(data_3d):.3e}, max={np.max(data_3d):.3e}")

    # Create interpolator
    interp = RegularGridInterpolator(
        (temps, times, positions),
        data_3d,
        method='linear',
        bounds_error=False,
        fill_value=None  # Extrapolate outside bounds
    )

    # Prepare points for interpolation
    points = np.column_stack([target_temps, target_times, target_positions])

    # Interpolate
    interpolated_values = interp(points)
    print(f"[DEBUG interpolate_simulation_data] Interpolated values: min={np.min(interpolated_values):.3e}, max={np.max(interpolated_values):.3e}, has_nan={np.any(np.isnan(interpolated_values))}")

    return interpolated_values


def prepare_plot_data(
    sim_results: Dict,
    exp_data: ExperimentalData,
    x_axis_var: str,
    sim_y_var: str,
    sim_filters: Dict[str, float],
    exp_filter: Dict[str, float],
    is_temperature_sweep: bool = True
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Prepare data for dual Y-axis plot comparing simulation and experimental results.

    Args:
        sim_results: Simulation results dictionary
        exp_data: Experimental data object
        x_axis_var: Variable for X-axis ("temperature", "time", or "position")
        sim_y_var: Simulation variable for left Y-axis (e.g., "C", "J_source", etc.)
        sim_filters: Filter values for non-X variables in simulation
                    e.g., {"time": 100.0, "position": 1e-6}
        exp_filter: Filter value for the non-X, non-fixed variable in experimental data
                   e.g., {"time": 100.0}
        is_temperature_sweep: True if sim_results is from temperature sweep

    Returns:
        Tuple of (x_values, sim_y_values, exp_y_values):
            - x_values: X-axis values
            - sim_y_values: Interpolated simulation data
            - exp_y_values: Experimental dq values

    Raises:
        ValueError: If x_axis_var doesn't match exp_data's row or col variable
        ValueError: If filter variables are inconsistent

    Example:
        If exp_data has:
            - fixed_var = "position", fixed_value = 1e-6
            - row_var = "time", row_values = [100, 200, 300]
            - col_var = "temperature", col_values = [300, 350, 400]

        And we want:
            - x_axis_var = "temperature"
            - exp_filter = {"time": 100.0}

        Then:
            - x_values = [300, 350, 400] (from col_values)
            - exp_y_values = dq_grid[0, :] (first row, all columns)
            - sim_y_values = interpolated at (temps=[300,350,400], time=100, pos=1e-6)
    """
    # Determine X-axis values from experimental data
    if x_axis_var == exp_data.row_var:
        x_values = exp_data.row_values.copy()
        other_var = exp_data.col_var
        other_values = exp_data.col_values
        # X is row, so we select column based on filter
        if other_var not in exp_filter:
            raise ValueError(f"Filter must specify {other_var}")
        other_idx = np.argmin(np.abs(other_values - exp_filter[other_var]))
        exp_y_values = exp_data.dq_grid[:, other_idx]
    elif x_axis_var == exp_data.col_var:
        x_values = exp_data.col_values.copy()
        other_var = exp_data.row_var
        other_values = exp_data.row_values
        # X is col, so we select row based on filter
        if other_var not in exp_filter:
            raise ValueError(f"Filter must specify {other_var}")
        other_idx = np.argmin(np.abs(other_values - exp_filter[other_var]))
        exp_y_values = exp_data.dq_grid[other_idx, :]
    else:
        raise ValueError(
            f"X-axis variable '{x_axis_var}' must match row_var '{exp_data.row_var}' "
            f"or col_var '{exp_data.col_var}'"
        )

    n_points = len(x_values)

    # Build 3D coordinates for simulation interpolation
    # Map variable names to values
    coord_map = {
        "temperature": np.zeros(n_points),
        "time": np.zeros(n_points),
        "position": np.zeros(n_points),
    }

    # Set X-axis variable
    coord_map[x_axis_var] = x_values

    # Set fixed variable from experimental data
    coord_map[exp_data.fixed_var] = np.full(n_points, exp_data.fixed_value)

    # Set filtered variable
    # Find the third variable (not X-axis, not fixed)
    all_vars = {"temperature", "time", "position"}
    third_var = list(all_vars - {x_axis_var, exp_data.fixed_var})[0]

    if third_var not in sim_filters:
        raise ValueError(f"Simulation filter must specify {third_var}")

    coord_map[third_var] = np.full(n_points, sim_filters[third_var])

    # Interpolate simulation data
    sim_y_values = interpolate_simulation_data(
        sim_results,
        coord_map["temperature"],
        coord_map["time"],
        coord_map["position"],
        sim_y_var,
        is_temperature_sweep
    )

    return x_values, sim_y_values, exp_y_values
