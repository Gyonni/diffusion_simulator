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

    # Validate: check for single data point on any axis (interpolation requires at least 2 points)
    # For single-temperature simulations, RegularGridInterpolator needs at least 2 points on each axis
    # We'll handle this by duplicating the temperature dimension with a tiny offset
    if len(temps) < 2:
        unique_target_temps = np.unique(target_temps)
        if len(unique_target_temps) > 1:
            raise ValueError(
                f"Cannot interpolate to {len(unique_target_temps)} different temperatures "
                f"when simulation has only {len(temps)} temperature point(s). "
                "Please run a temperature sweep simulation with multiple temperatures."
            )

        print(f"[INFO] Single-temperature simulation detected (T={temps[0]:.2f} K). Creating duplicate grid for interpolation.")
        # Duplicate the temperature grid with a tiny offset
        temps_original = temps.copy()
        temps = np.array([temps[0], temps[0] + 1e-6])  # Add tiny offset (0.000001 K)
        # Duplicate data along temperature axis
        data_3d = np.repeat(data_3d, 2, axis=0)  # [1, time, x] -> [2, time, x]

    if len(times) < 2:
        raise ValueError(
            f"Cannot interpolate with only {len(times)} time point(s). "
            "Need at least 2 points for interpolation. "
            "This should not happen - check simulation time step configuration."
        )
    if len(positions) < 2:
        raise ValueError(
            f"Cannot interpolate with only {len(positions)} position point(s). "
            "Need at least 2 points for interpolation. "
            "Please increase the number of nodes in your layers."
        )

    # Check if target points are outside simulation bounds (extrapolation warning)
    temp_min, temp_max = temps.min(), temps.max()
    time_min, time_max = times.min(), times.max()
    pos_min, pos_max = positions.min(), positions.max()

    out_of_bounds = []
    if np.any(target_temps < temp_min) or np.any(target_temps > temp_max):
        out_of_bounds.append(f"Temperature: target [{target_temps.min():.1f}, {target_temps.max():.1f}] K, sim [{temp_min:.1f}, {temp_max:.1f}] K")
    if np.any(target_times < time_min) or np.any(target_times > time_max):
        out_of_bounds.append(f"Time: target [{target_times.min():.3e}, {target_times.max():.3e}] s, sim [{time_min:.3e}, {time_max:.3e}] s")
    if np.any(target_positions < pos_min) or np.any(target_positions > pos_max):
        out_of_bounds.append(f"Position: target [{target_positions.min():.3e}, {target_positions.max():.3e}] m, sim [{pos_min:.3e}, {pos_max:.3e}] m")

    if out_of_bounds:
        import warnings
        warnings.warn(
            "WARNING: Target points are outside simulation range. Extrapolation may produce unreliable results.\n" +
            "\n".join(out_of_bounds) +
            "\nConsider adjusting your experimental data or simulation range.",
            UserWarning
        )
        print("[WARNING] Extrapolation detected:")
        for msg in out_of_bounds:
            print(f"  - {msg}")

    # Clamp out-of-bounds coordinates to simulation range (nearest-neighbor extrapolation)
    # This is more reliable than relying on RegularGridInterpolator's fill_value
    target_temps_clamped = np.clip(target_temps, temps.min(), temps.max())
    target_times_clamped = np.clip(target_times, times.min(), times.max())
    target_positions_clamped = np.clip(target_positions, positions.min(), positions.max())

    # Create interpolator with bounds checking disabled (we handle clamping ourselves)
    interp = RegularGridInterpolator(
        (temps, times, positions),
        data_3d,
        method='linear',
        bounds_error=False,
        fill_value=None  # Not used since we clamp coordinates
    )

    # Prepare points for interpolation (using clamped coordinates)
    points = np.column_stack([target_temps_clamped, target_times_clamped, target_positions_clamped])

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
    exp_filters: Dict[str, float],
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
        exp_filters: Filter values for non-X variables in experimental data (now 2 filters, same as sim_filters)
                    e.g., {"time": 100.0, "position": 1e-6}
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
            - exp_filters = {"time": 100.0, "position": 1e-6}

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
        if other_var not in exp_filters:
            raise ValueError(f"Filter must specify {other_var}")
        other_idx = np.argmin(np.abs(other_values - exp_filters[other_var]))
        exp_y_values = exp_data.dq_grid[:, other_idx]
    elif x_axis_var == exp_data.col_var:
        x_values = exp_data.col_values.copy()
        other_var = exp_data.row_var
        other_values = exp_data.row_values
        # X is col, so we select row based on filter
        if other_var not in exp_filters:
            raise ValueError(f"Filter must specify {other_var}")
        other_idx = np.argmin(np.abs(other_values - exp_filters[other_var]))
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


def calculate_global_fit_metrics(
    sim_results: Dict,
    exp_data: ExperimentalData,
    sim_y_var: str = "C",
    is_temperature_sweep: bool = False
) -> Dict[str, float]:
    """
    Calculate global goodness-of-fit metrics between all experimental data points
    and corresponding simulation values.

    This function evaluates the overall agreement between simulation and experiment
    across the entire 3D parameter space (temperature × time × position).

    Args:
        sim_results: Simulation results dictionary with keys "t", "x", "C", etc.
        exp_data: Experimental data with 2D grid (row_var × col_var) + fixed_var
        sim_y_var: Simulation variable to compare (default: "C" for concentration)
        is_temperature_sweep: Whether simulation used temperature sweep

    Returns:
        Dictionary with metrics:
            - "r_squared": Coefficient of determination from linear regression [0-1, higher is better]
            - "nrmse": Normalized RMSE relative to best-fit line [0-1, lower is better]
            - "n_points": Number of data points used in comparison
            - "slope": Slope of best-fit line (y = slope*x + intercept)
            - "intercept": Intercept of best-fit line
            - "p_value": P-value of linear regression (statistical significance)
            - "mean_exp": Mean of experimental values
            - "mean_sim": Mean of interpolated simulation values

    Raises:
        ValueError: If experimental data structure is invalid
        ValueError: If simulation data is missing required keys

    Notes:
        - Uses linear regression (y = a*x + b) instead of y=x comparison
        - This is appropriate when comparing different units (e.g., dq vs C or flux)
        - R² indicates how well the data fits a linear relationship
        - Residuals are calculated from the best-fit line, not y=x
        - All experimental grid points are compared with interpolated simulation values
    """
    print("[DEBUG calculate_global_fit_metrics] Starting global fit calculation")

    # Validate inputs
    if exp_data.dq_grid is None or exp_data.dq_grid.size == 0:
        raise ValueError("Experimental data grid is empty")

    # Get all experimental data points (flatten 2D grid)
    exp_values_2d = exp_data.dq_grid  # shape: (n_rows, n_cols)
    exp_values_flat = exp_values_2d.flatten()  # 1D array
    n_points = exp_values_flat.size

    print(f"[DEBUG] Experimental data shape: {exp_values_2d.shape}, total points: {n_points}")
    print(f"[DEBUG] Exp data range: [{np.min(exp_values_flat):.3e}, {np.max(exp_values_flat):.3e}]")

    # Build 3D coordinates for all experimental points
    # Experimental data structure:
    #   - row_var: exp_data.row_var (e.g., "time")
    #   - col_var: exp_data.col_var (e.g., "temperature")
    #   - fixed_var: exp_data.fixed_var (e.g., "position")
    row_vals = exp_data.row_values  # e.g., [100, 200, 300] for time
    col_vals = exp_data.col_values  # e.g., [300, 350, 400] for temperature
    fixed_val = exp_data.fixed_value  # e.g., 1e-6 for position

    # Create meshgrid for all combinations
    row_grid, col_grid = np.meshgrid(row_vals, col_vals, indexing='ij')
    row_coords = row_grid.flatten()  # All row variable values
    col_coords = col_grid.flatten()  # All col variable values

    # Map to 3D coordinates (temperature, time, position)
    var_map = {
        exp_data.row_var: row_coords,
        exp_data.col_var: col_coords,
        exp_data.fixed_var: np.full(n_points, fixed_val)
    }

    target_temps = var_map["temperature"]
    target_times = var_map["time"]
    target_positions = var_map["position"]

    print(f"[DEBUG] Interpolation targets:")
    print(f"  Temperature: [{np.min(target_temps):.1f}, {np.max(target_temps):.1f}] K")
    print(f"  Time: [{np.min(target_times):.3e}, {np.max(target_times):.3e}] s")
    print(f"  Position: [{np.min(target_positions):.3e}, {np.max(target_positions):.3e}] m")

    # Interpolate simulation data at all experimental coordinates
    sim_values_flat = interpolate_simulation_data(
        sim_results=sim_results,
        target_temps=target_temps,
        target_times=target_times,
        target_positions=target_positions,
        variable=sim_y_var,
        is_temperature_sweep=is_temperature_sweep
    )

    print(f"[DEBUG] Simulation values range: [{np.min(sim_values_flat):.3e}, {np.max(sim_values_flat):.3e}]")

    # Perform linear regression: y = a*x + b where x=sim, y=exp
    # This is appropriate when comparing different units (e.g., dq vs C)
    # Returns: slope (a), intercept (b), r_value, p_value, std_err
    from scipy import stats

    slope, intercept, r_value, p_value, std_err = stats.linregress(sim_values_flat, exp_values_flat)
    r_squared = r_value ** 2  # R² from linear regression

    print(f"[DEBUG] Linear regression: y = {slope:.3e}*x + {intercept:.3e}")
    print(f"[DEBUG] R² = {r_squared:.4f}, p-value = {p_value:.3e}")

    # Calculate residuals from best-fit line (not from y=x line)
    exp_predicted_from_regression = slope * sim_values_flat + intercept
    residuals = exp_values_flat - exp_predicted_from_regression

    # Calculate NRMSE relative to best-fit line
    rmse = np.sqrt(np.mean(residuals ** 2))
    exp_range = np.max(exp_values_flat) - np.min(exp_values_flat)

    if exp_range == 0:
        nrmse = 0.0 if rmse == 0 else np.inf
    else:
        nrmse = rmse / exp_range

    print(f"[DEBUG] Fit metrics: R²={r_squared:.4f}, NRMSE={nrmse:.4f}")

    return {
        "r_squared": float(r_squared),
        "nrmse": float(nrmse),
        "n_points": int(n_points),
        "slope": float(slope),
        "intercept": float(intercept),
        "p_value": float(p_value),
        "mean_exp": float(np.mean(exp_values_flat)),
        "mean_sim": float(np.mean(sim_values_flat)),
    }


def prepare_global_scatter_data(
    sim_results: Dict,
    exp_data: ExperimentalData,
    sim_y_var: str = "C",
    is_temperature_sweep: bool = False
) -> Tuple[np.ndarray, np.ndarray, float, float]:
    """
    Prepare data for global scatter plot (simulation vs experiment).

    Returns all experimental points and their corresponding simulation values
    for creating a scatter plot where X=simulation, Y=experiment, along with
    the best-fit linear regression line parameters.

    Args:
        sim_results: Simulation results dictionary
        exp_data: Experimental data
        sim_y_var: Simulation variable to compare
        is_temperature_sweep: Whether simulation used temperature sweep

    Returns:
        Tuple of (sim_values, exp_values, slope, intercept):
            - sim_values: 1D array of simulation values
            - exp_values: 1D array of experimental values
            - slope: Slope of best-fit line (y = slope*x + intercept)
            - intercept: Intercept of best-fit line

    Notes:
        - Uses linear regression to find best-fit line
        - Appropriate for comparing different units (e.g., dq vs C)
    """
    # Get all experimental data points
    exp_values_flat = exp_data.dq_grid.flatten()
    n_points = exp_values_flat.size

    # Build 3D coordinates
    row_vals = exp_data.row_values
    col_vals = exp_data.col_values
    fixed_val = exp_data.fixed_value

    row_grid, col_grid = np.meshgrid(row_vals, col_vals, indexing='ij')
    row_coords = row_grid.flatten()
    col_coords = col_grid.flatten()

    var_map = {
        exp_data.row_var: row_coords,
        exp_data.col_var: col_coords,
        exp_data.fixed_var: np.full(n_points, fixed_val)
    }

    target_temps = var_map["temperature"]
    target_times = var_map["time"]
    target_positions = var_map["position"]

    # Interpolate simulation data
    sim_values_flat = interpolate_simulation_data(
        sim_results=sim_results,
        target_temps=target_temps,
        target_times=target_times,
        target_positions=target_positions,
        variable=sim_y_var,
        is_temperature_sweep=is_temperature_sweep
    )

    # Calculate best-fit line using linear regression
    from scipy import stats
    slope, intercept, _, _, _ = stats.linregress(sim_values_flat, exp_values_flat)

    return sim_values_flat, exp_values_flat, slope, intercept


def prepare_residual_heatmap_data(
    sim_results: Dict,
    exp_data: ExperimentalData,
    sim_y_var: str = "C",
    is_temperature_sweep: bool = False,
    residual_type: str = "percent"
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Prepare residual heatmap data matching experimental data grid structure.

    Residuals are calculated relative to the best-fit linear regression line,
    not relative to y=x or raw differences. This is appropriate when comparing
    different units (e.g., dq vs C).

    Args:
        sim_results: Simulation results dictionary
        exp_data: Experimental data
        sim_y_var: Simulation variable to compare
        is_temperature_sweep: Whether simulation used temperature sweep
        residual_type: Type of residual to calculate
            - "absolute": exp - (slope*sim + intercept)
            - "percent": 100 * (exp - predicted) / predicted
            - "normalized": (exp - predicted) / range(exp)

    Returns:
        Tuple of (row_values, col_values, residual_grid):
            - row_values: 1D array of row variable values
            - col_values: 1D array of column variable values
            - residual_grid: 2D array of residuals, shape (n_rows, n_cols)

    Notes:
        - First calculates best-fit line: y = slope*x + intercept
        - Residuals show deviation from linear relationship
        - The returned grid can be directly plotted as a heatmap
    """
    # Get experimental grid
    exp_grid = exp_data.dq_grid  # shape: (n_rows, n_cols)
    n_rows, n_cols = exp_grid.shape

    row_vals = exp_data.row_values
    col_vals = exp_data.col_values
    fixed_val = exp_data.fixed_value

    # Build coordinates for all grid points
    row_grid, col_grid = np.meshgrid(row_vals, col_vals, indexing='ij')
    row_coords = row_grid.flatten()
    col_coords = col_grid.flatten()

    var_map = {
        exp_data.row_var: row_coords,
        exp_data.col_var: col_coords,
        exp_data.fixed_var: np.full(n_rows * n_cols, fixed_val)
    }

    # Interpolate simulation
    sim_values = interpolate_simulation_data(
        sim_results=sim_results,
        target_temps=var_map["temperature"],
        target_times=var_map["time"],
        target_positions=var_map["position"],
        variable=sim_y_var,
        is_temperature_sweep=is_temperature_sweep
    )

    # Reshape to 2D grid
    sim_grid = sim_values.reshape(n_rows, n_cols)
    exp_grid_flat = exp_grid.flatten().reshape(n_rows, n_cols)

    # Calculate best-fit line using linear regression on all points
    from scipy import stats
    sim_values_1d = sim_grid.flatten()
    exp_values_1d = exp_grid_flat.flatten()
    slope, intercept, _, _, _ = stats.linregress(sim_values_1d, exp_values_1d)

    # Calculate residuals from best-fit line (not from y=x or raw difference)
    # exp_predicted = slope * sim + intercept
    # residual = exp_actual - exp_predicted
    exp_predicted_grid = slope * sim_grid + intercept
    residual_from_regression = exp_grid_flat - exp_predicted_grid

    # Calculate residuals based on type
    if residual_type == "absolute":
        residual_grid = residual_from_regression
    elif residual_type == "percent":
        # % error relative to best-fit line prediction
        with np.errstate(divide='ignore', invalid='ignore'):
            residual_grid = 100.0 * residual_from_regression / exp_predicted_grid
            residual_grid = np.where(np.isfinite(residual_grid), residual_grid, 0.0)
    elif residual_type == "normalized":
        exp_range = np.max(exp_grid_flat) - np.min(exp_grid_flat)
        if exp_range == 0:
            residual_grid = np.zeros_like(sim_grid)
        else:
            residual_grid = residual_from_regression / exp_range
    else:
        raise ValueError(f"Unknown residual_type: {residual_type}")

    return row_vals, col_vals, residual_grid


def prepare_trellis_scatter_data(
    sim_results: Dict,
    exp_data: ExperimentalData,
    sim_y_var: str = "C",
    is_temperature_sweep: bool = False
) -> Dict:
    """
    Prepare data for trellis (faceted) scatter plots.

    Each facet shows one slice of the data (e.g., one temperature or one time point),
    allowing proper evaluation of fit quality for each condition separately.

    Args:
        sim_results: Simulation results dictionary
        exp_data: Experimental data with 2D grid (row_var × col_var) + fixed_var
        sim_y_var: Simulation variable to compare
        is_temperature_sweep: Whether simulation used temperature sweep

    Returns:
        Dictionary with:
            - "facet_var": Name of variable to facet by (row or col)
            - "facet_values": Values for each facet
            - "x_var": Name of X-axis variable
            - "facet_data": List of dicts, each containing:
                - "facet_label": Label for this facet
                - "x_values": X-axis values for this facet
                - "sim_values": Simulation Y values
                - "exp_values": Experimental Y values
                - "slope": Best-fit line slope
                - "intercept": Best-fit line intercept
                - "r_squared": R² for this facet
            - "overall_r_squared": R² across all data

    Notes:
        - Faceting separates different conditions (e.g., different temperatures)
        - This is scientifically more rigorous than combining all conditions
    """
    from scipy import stats

    # Get experimental grid
    exp_grid = exp_data.dq_grid  # shape: (n_rows, n_cols)
    n_rows, n_cols = exp_grid.shape

    row_vals = exp_data.row_values
    col_vals = exp_data.col_values
    fixed_val = exp_data.fixed_value

    # Decide which variable to facet by (use the one with more values for better visualization)
    if n_rows >= n_cols:
        facet_var = exp_data.row_var
        facet_values = row_vals
        x_var = exp_data.col_var
        x_values_all = col_vals
        facet_is_row = True
    else:
        facet_var = exp_data.col_var
        facet_values = col_vals
        x_var = exp_data.row_var
        x_values_all = row_vals
        facet_is_row = False

    facet_data = []
    all_sim_values = []
    all_exp_values = []

    # For each facet (e.g., each temperature), create a separate scatter plot
    for i, facet_val in enumerate(facet_values):
        # Extract data for this facet
        if facet_is_row:
            exp_values_this_facet = exp_grid[i, :]  # This row
        else:
            exp_values_this_facet = exp_grid[:, i]  # This column

        # Build coordinates for interpolation
        n_points = len(x_values_all)
        var_map = {
            exp_data.fixed_var: np.full(n_points, fixed_val)
        }

        if facet_is_row:
            var_map[exp_data.row_var] = np.full(n_points, facet_val)
            var_map[exp_data.col_var] = x_values_all
        else:
            var_map[exp_data.col_var] = np.full(n_points, facet_val)
            var_map[exp_data.row_var] = x_values_all

        # Interpolate simulation
        sim_values_this_facet = interpolate_simulation_data(
            sim_results=sim_results,
            target_temps=var_map["temperature"],
            target_times=var_map["time"],
            target_positions=var_map["position"],
            variable=sim_y_var,
            is_temperature_sweep=is_temperature_sweep
        )

        # Calculate best-fit line for this facet
        # Handle case where all sim values are identical (no variation)
        if np.allclose(sim_values_this_facet, sim_values_this_facet[0]):
            # All sim values are the same (e.g., all zeros from extrapolation)
            # Cannot perform linear regression
            slope = np.nan
            intercept = np.nan
            r_squared = 0.0
            print(f"[WARNING] All simulation values identical for facet {facet_var}={facet_val:.2e}. R² set to 0.0")
        else:
            slope, intercept, r_value, _, _ = stats.linregress(sim_values_this_facet, exp_values_this_facet)
            r_squared = r_value ** 2

        # Store for this facet
        facet_data.append({
            "facet_label": f"{facet_var}={facet_val:.2e}",
            "x_values": x_values_all.copy(),
            "sim_values": sim_values_this_facet.copy(),
            "exp_values": exp_values_this_facet.copy(),
            "slope": slope,
            "intercept": intercept,
            "r_squared": r_squared
        })

        # Accumulate for overall R²
        all_sim_values.extend(sim_values_this_facet)
        all_exp_values.extend(exp_values_this_facet)

    # Calculate overall R² across all facets
    all_sim_values = np.array(all_sim_values)
    all_exp_values = np.array(all_exp_values)

    if np.allclose(all_sim_values, all_sim_values[0]):
        # All sim values are identical across all facets
        overall_slope = np.nan
        overall_intercept = np.nan
        overall_r_squared = 0.0
        print("[WARNING] All simulation values identical across all facets. Overall R² set to 0.0")
    else:
        overall_slope, overall_intercept, overall_r_value, _, _ = stats.linregress(all_sim_values, all_exp_values)
        overall_r_squared = overall_r_value ** 2

    return {
        "facet_var": facet_var,
        "facet_values": facet_values,
        "x_var": x_var,
        "facet_data": facet_data,
        "overall_r_squared": overall_r_squared,
        "overall_slope": overall_slope,
        "overall_intercept": overall_intercept
    }
