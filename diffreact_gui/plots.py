from __future__ import annotations

"""Matplotlib plotting helpers for the GUI."""

from typing import Any, Dict, List, Tuple

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D


def create_figures() -> Tuple[plt.Figure, Dict[str, Any]]:
    # 4 subplots: Flux vs Time, C vs Time, C vs x, C vs T
    fig, ((ax_flux, ax_c_time), (ax_prof, ax_temp)) = plt.subplots(2, 2, figsize=(14, 10), sharex=False)
    # Adjust spacing
    fig.subplots_adjust(hspace=0.35, wspace=0.35, top=0.95, bottom=0.07, left=0.09, right=0.91)

    # First plot: Flux & Uptake vs Time
    ax_flux.set_title("Flux & Uptake vs Time", fontsize=13, fontweight='bold')
    ax_flux.set_xlabel("t [s]", fontsize=11)
    ax_flux.set_ylabel("Flux [mol/(m^2·s)]", fontsize=11)
    ax_flux.tick_params(axis='both', labelsize=10)
    ax_flux_secondary = ax_flux.twinx()
    ax_flux_secondary.set_ylabel("Integrated uptake [mol/m^2]", fontsize=11)
    ax_flux_secondary.tick_params(axis='y', labelsize=10)

    line_J_surface, = ax_flux.plot([], [], color="tab:blue", linewidth=2)
    line_J_surface.set_label("Flux at surface (x=0)")
    line_J_target, = ax_flux.plot([], [], color="tab:orange", linewidth=2)
    line_J_target.set_label("Flux at reporting interface")
    line_J_exit, = ax_flux.plot([], [], color="tab:green", linestyle="--", linewidth=2)
    line_J_exit.set_label("Flux at exit (x=L)")
    line_J_probe, = ax_flux.plot([], [], color="tab:red", linestyle=":", linewidth=2)
    line_J_probe.set_label("Flux at probe")

    line_cum_surface, = ax_flux_secondary.plot([], [], color="tab:blue", linestyle="-", linewidth=2)
    line_cum_surface.set_label("Cumulative uptake at surface")
    line_cum_target, = ax_flux_secondary.plot([], [], color="tab:orange", linestyle="-.", linewidth=2)
    line_cum_target.set_label("Cumulative uptake at reporting interface")
    line_cum_exit, = ax_flux_secondary.plot([], [], color="tab:green", linestyle="--", linewidth=2)
    line_cum_exit.set_label("Cumulative uptake at exit")
    line_mass_target, = ax_flux_secondary.plot([], [], color="tab:purple", linestyle=":", linewidth=2)
    line_mass_target.set_label("Mass in reporting layer")
    line_cum_probe, = ax_flux_secondary.plot([], [], color="tab:brown", linestyle="--", linewidth=2)
    line_cum_probe.set_label("Cumulative uptake at probe")

    # Second plot: Concentration vs Time (at selected position)
    ax_c_time.set_title("Concentration vs Time (at selected position)", fontsize=13, fontweight='bold')
    ax_c_time.set_xlabel("t [s]", fontsize=11)
    ax_c_time.set_ylabel("C [mol/m^3]", fontsize=11)
    ax_c_time.tick_params(axis='both', labelsize=10)
    line_c_time, = ax_c_time.plot([], [], color="tab:purple", marker='o', markersize=4, linewidth=2)

    # Third plot: Concentration Profile (C vs x)
    ax_prof.set_title("Concentration Profile", fontsize=13, fontweight='bold')
    ax_prof.set_xlabel("x [m]", fontsize=11)
    ax_prof.set_ylabel("C [mol/m^3]", fontsize=11)
    ax_prof.tick_params(axis='both', labelsize=10)
    line_prof, = ax_prof.plot([], [], color="tab:blue", linewidth=2)

    # Fourth plot: Concentration vs Temperature
    ax_temp.set_title("Concentration vs Temperature (at selected position)", fontsize=13, fontweight='bold')
    ax_temp.set_xlabel("T [K]", fontsize=11)
    ax_temp.set_ylabel("C [mol/m^3]", fontsize=11)
    ax_temp.tick_params(axis='both', labelsize=10)
    line_temp, = ax_temp.plot([], [], marker='o', linestyle='-', color="tab:red", markersize=6, linewidth=2)
    line_temp.set_label("C(T) at position")

    artists = {
        "figure": fig,
        "ax_flux": ax_flux,
        "ax_flux_secondary": ax_flux_secondary,
        "ax_flux_legend": None,
        "ax_c_time": ax_c_time,
        "ax_prof": ax_prof,
        "ax_temp": ax_temp,
        "line_J_surface": line_J_surface,
        "line_J_target": line_J_target,
        "line_J_exit": line_J_exit,
        "line_J_probe": line_J_probe,
        "line_cum_surface": line_cum_surface,
        "line_cum_target": line_cum_target,
        "line_cum_exit": line_cum_exit,
        "line_mass_target": line_mass_target,
        "line_cum_probe": line_cum_probe,
        "line_c_time": line_c_time,
        "line_prof": line_prof,
        "line_temp": line_temp,
        "boundary_lines": [],
        "c_time_lines": [],
        "flux_line_keys": [
            "line_J_surface",
            "line_J_target",
            "line_J_exit",
            "line_J_probe",
        ],
        "flux_cum_keys": [
            "line_cum_surface",
            "line_cum_target",
            "line_cum_exit",
            "line_cum_probe",
            "line_mass_target",
        ],
    }
    return fig, artists


def update_flux_axes(
    artists: Dict[str, Any],
    t: np.ndarray,
    J_surface: np.ndarray,
    J_target: np.ndarray,
    J_exit: np.ndarray,
    cum_surface: np.ndarray,
    cum_target: np.ndarray,
    cum_exit: np.ndarray,
    mass_target: np.ndarray,
    *,
    J_probe: np.ndarray | None = None,
    cum_probe: np.ndarray | None = None,
    temperature: float | None = None,
) -> None:
    artists["line_J_surface"].set_data(t, J_surface)
    artists["line_J_target"].set_data(t, J_target)
    artists["line_J_exit"].set_data(t, J_exit)
    artists["line_cum_target"].set_data(t, cum_target)
    artists["line_cum_surface"].set_data(t, cum_surface)
    artists["line_cum_exit"].set_data(t, cum_exit)
    artists["line_mass_target"].set_data(t, mass_target)

    if J_probe is not None and J_probe.size:
        artists["line_J_probe"].set_data(t, J_probe)
    else:
        artists["line_J_probe"].set_data([], [])

    if cum_probe is not None and cum_probe.size:
        artists["line_cum_probe"].set_data(t, cum_probe)
    else:
        artists["line_cum_probe"].set_data([], [])

    ax_flux = artists["ax_flux"]
    # Update title with temperature if specified
    if temperature is not None:
        ax_flux.set_title(f"Flux & Uptake vs Time (T = {temperature:.1f} K)")
    else:
        ax_flux.set_title("Flux & Uptake vs Time")

    ax_flux.relim()
    if t.size:
        ax_flux.set_xlim(t[0], t[-1])
    ax_flux.autoscale_view()

    ax_flux_secondary = artists["ax_flux_secondary"]
    ax_flux_secondary.relim()
    if t.size:
        ax_flux_secondary.set_xlim(t[0], t[-1])
    ax_flux_secondary.autoscale_view()


def update_profile_axes(
    artists: Dict[str, Any],
    x: np.ndarray,
    C: np.ndarray,
    boundaries: np.ndarray,
    temperature: float | None = None,
) -> None:
    artists["line_prof"].set_data(x, C)
    ax = artists["ax_prof"]

    # Update title with temperature if specified
    if temperature is not None:
        ax.set_title(f"Concentration Profile (T = {temperature:.1f} K)")
    else:
        ax.set_title("Concentration Profile")

    for line in artists.get("boundary_lines", []):
        line.remove()
    artists["boundary_lines"] = []

    # Skip first and last boundary (0 and total thickness)
    for boundary in boundaries[1:-1]:
        vline = ax.axvline(boundary, color="gray", linestyle="--", alpha=0.3)
        artists["boundary_lines"].append(vline)

    ax.relim()
    ax.autoscale_view()


def update_temperature_axes(
    artists: Dict[str, Any],
    temperatures: np.ndarray,
    concentrations_list: list,
    position: float,
) -> None:
    """Update temperature vs concentration plot with multiple time series.

    Args:
        artists: Dictionary of matplotlib artist objects
        temperatures: Array of temperatures [K]
        concentrations_list: List of (time_value, concentration_array) tuples
                            or single concentration array (backward compatibility)
        position: The x-position [m] where concentrations were sampled
    """
    ax = artists["ax_temp"]

    # Clear existing lines (except the original line_temp for backward compatibility)
    if "temp_plot_lines" in artists:
        for line in artists["temp_plot_lines"]:
            line.remove()
        artists["temp_plot_lines"] = []
    else:
        artists["temp_plot_lines"] = []

    # Handle backward compatibility: if concentrations_list is a numpy array
    if isinstance(concentrations_list, np.ndarray):
        concentrations_list = [(None, concentrations_list)]

    # Plot each time series
    lines = []
    labels = []
    for time_value, concentrations in concentrations_list:
        if time_value is None:
            label = "Current time"
        else:
            label = f"t = {time_value:.3e} s"

        line, = ax.plot(temperatures, concentrations, marker='o', linestyle='-', label=label)
        lines.append(line)
        labels.append(label)

    artists["temp_plot_lines"] = lines

    # Update title
    ax.set_title(f"Concentration vs Temperature (at x={position:.3e} m)")

    # Add legend if multiple time series
    if len(concentrations_list) > 1:
        ax.legend(loc='best', fontsize=8)
    else:
        # Remove legend if only one series
        if ax.get_legend() is not None:
            ax.get_legend().remove()

    ax.relim()
    ax.autoscale_view()



def update_c_time_axes(
    artists: Dict[str, Any],
    t: np.ndarray,
    concentrations_list: list,
    position: float,
) -> None:
    """Update concentration vs time plot with multiple temperature series.

    Args:
        artists: Dictionary of matplotlib artist objects
        t: Time array [s]
        concentrations_list: List of (temperature, concentration_array) tuples
                            or single concentration array (backward compatibility)
        position: The x-position [m] where concentrations were sampled
    """
    ax = artists["ax_c_time"]

    # Clear existing lines
    if "c_time_lines" in artists:
        for line in artists["c_time_lines"]:
            line.remove()
        artists["c_time_lines"] = []
    else:
        artists["c_time_lines"] = []

    # Handle backward compatibility: if concentrations_list is a numpy array
    if isinstance(concentrations_list, np.ndarray):
        concentrations_list = [(None, concentrations_list)]

    # Plot each temperature series
    lines = []
    for temp_value, concentrations in concentrations_list:
        if temp_value is None:
            label = f"x = {position:.3e} m"
        else:
            label = f"T = {temp_value:.1f} K"

        line, = ax.plot(t, concentrations, marker='o', markersize=3, linestyle='-', label=label)
        lines.append(line)

    artists["c_time_lines"] = lines

    # Update title
    ax.set_title(f"Concentration vs Time (at x={position:.3e} m)")

    # Add legend if multiple temperature series
    if len(concentrations_list) > 1:
        ax.legend(loc='best', fontsize=8)
    else:
        # Remove legend if only one series
        if ax.get_legend() is not None:
            ax.get_legend().remove()

    ax.relim()
    ax.autoscale_view()


def create_analysis_figure():
    """Create figure for doping analysis (dual Y-axis plot)."""
    from matplotlib.figure import Figure
    # Larger figure size for better visibility in full-screen mode
    fig = Figure(figsize=(14, 10), dpi=100)
    ax_sim = fig.add_subplot(111)
    ax_exp = ax_sim.twinx()
    ax_sim.set_xlabel("X-axis Variable", fontsize=14)
    ax_sim.set_ylabel("Simulation Data", color='blue', fontsize=14)
    ax_sim.tick_params(axis='y', labelcolor='blue', labelsize=11)
    ax_sim.tick_params(axis='x', labelsize=11)
    ax_exp.set_ylabel("dq [C]", color='red', fontsize=14)
    ax_exp.tick_params(axis='y', labelcolor='red', labelsize=11)
    ax_sim.grid(True, alpha=0.3)
    artists = {"ax_sim": ax_sim, "ax_exp": ax_exp, "line_sim": None, "line_exp": None}
    fig.tight_layout()
    return fig, ax_sim, ax_exp, artists


def update_analysis_plot(artists, x_values, sim_y_values, exp_y_values, x_label, sim_y_label, x_var_name="Variable", filter_info="", use_log_scale=False):
    """Update dual Y-axis analysis plot.

    CRITICAL: ax_sim (left/blue) and ax_exp (right/red) are twin axes.
    When clearing, we must preserve the twin relationship.

    Args:
        artists: Dictionary containing ax_sim, ax_exp, line_sim, line_exp
        x_values: X-axis data array
        sim_y_values: Simulation Y-axis data array (left axis)
        exp_y_values: Experimental Y-axis data array (right axis)
        x_label: X-axis label
        sim_y_label: Simulation Y-axis label (left axis)
        x_var_name: Variable name for plot title
        filter_info: Filter information string for subtitle
        use_log_scale: If True, use logarithmic scale for left Y-axis (simulation)
    """
    ax_sim = artists["ax_sim"]
    ax_exp = artists["ax_exp"]

    # DEBUG: Print data ranges
    print(f"[DEBUG update_analysis_plot] x_values: {x_values}")
    print(f"[DEBUG update_analysis_plot] sim_y_values: {sim_y_values}")
    print(f"[DEBUG update_analysis_plot] exp_y_values: {exp_y_values}")

    # Remove old lines without clearing axes (preserves twin relationship)
    if artists["line_sim"] is not None:
        try:
            artists["line_sim"].remove()
        except:
            pass
    if artists["line_exp"] is not None:
        try:
            artists["line_exp"].remove()
        except:
            pass

    # Clear artists but don't use clear() to preserve twin relationship
    for line in ax_sim.lines[:]:
        line.remove()
    for line in ax_exp.lines[:]:
        line.remove()

    # Remove old legend if exists
    if ax_sim.get_legend() is not None:
        ax_sim.get_legend().remove()

    # Plot simulation data on left axis (blue)
    line_sim = ax_sim.plot(x_values, sim_y_values, 'b-o', label='Simulation',
                           linewidth=3, markersize=10, zorder=5)[0]

    # Plot experimental data on right axis (red)
    line_exp = ax_exp.plot(x_values, exp_y_values, 'r-s', label='Experimental dq',
                           linewidth=3, markersize=10, zorder=5)[0]

    print(f"[DEBUG update_analysis_plot] After plotting - line_sim in ax_sim.lines: {line_sim in ax_sim.lines}")
    print(f"[DEBUG update_analysis_plot] After plotting - line_exp in ax_exp.lines: {line_exp in ax_exp.lines}")

    # Configure left axis (simulation - blue)
    ax_sim.set_xlabel(x_label, fontsize=14)
    ax_sim.set_ylabel(sim_y_label, color='blue', fontsize=14)
    ax_sim.tick_params(axis='y', labelcolor='blue', labelsize=11)
    ax_sim.tick_params(axis='x', labelsize=11)

    # Configure right axis (experimental - red)
    ax_exp.set_ylabel("dq [C]", color='red', fontsize=14)
    ax_exp.tick_params(axis='y', labelcolor='red', labelsize=11)

    # Set title
    title = f"Analysis: {x_var_name} Dependence"
    if filter_info:
        title += f"\n{filter_info}"
    ax_sim.set_title(title, fontsize=15, fontweight='bold')

    # Ensure grid is behind everything
    ax_sim.grid(True, alpha=0.3, zorder=0)

    # Create combined legend
    lines = [line_sim, line_exp]
    labels = [l.get_label() for l in lines]
    ax_sim.legend(lines, labels, loc='upper left', fontsize=11)

    # Store line references
    artists["line_sim"] = line_sim
    artists["line_exp"] = line_exp

    # Apply logarithmic scale if requested
    import numpy as np
    sim_y_min, sim_y_max = np.min(sim_y_values), np.max(sim_y_values)
    print(f"[DEBUG update_analysis_plot] sim_y_min={sim_y_min:.3e}, sim_y_max={sim_y_max:.3e}")
    print(f"[DEBUG update_analysis_plot] use_log_scale={use_log_scale}")

    if use_log_scale:
        # Check if data is suitable for log scale (all positive values)
        if np.any(sim_y_values <= 0):
            print(f"[WARNING update_analysis_plot] Log scale requested but data contains non-positive values. Using linear scale.")
            ax_sim.set_yscale('linear')
        else:
            print(f"[DEBUG update_analysis_plot] Applying logarithmic scale to left Y-axis")
            ax_sim.set_yscale('log')
            # Force relim and autoscale for log scale
            ax_sim.relim()
            ax_sim.autoscale_view(scalex=True, scaley=True)
    else:
        # Ensure linear scale is set (important when switching back from log)
        ax_sim.set_yscale('linear')

        # Force autoscale for both axes independently with margins
        ax_sim.relim()
        ax_sim.autoscale_view(scalex=True, scaley=True)
        ax_sim.margins(x=0.05, y=0.1)  # Add 5% x-margin, 10% y-margin

        # CRITICAL FIX: Force scientific notation for very small values
        if sim_y_max != 0 and abs(sim_y_max) < 1e-10:
            # For very small values, force scientific notation
            print(f"[DEBUG update_analysis_plot] Applying scientific notation for small values")
            ax_sim.ticklabel_format(axis='y', style='scientific', scilimits=(0, 0))
            # Set explicit limits with margin
            y_range = sim_y_max - sim_y_min
            margin = max(abs(y_range) * 0.1, abs(sim_y_max) * 0.1)
            ax_sim.set_ylim(sim_y_min - margin, sim_y_max + margin)
            print(f"[DEBUG update_analysis_plot] Set explicit y-limits: {ax_sim.get_ylim()}")

    print(f"[DEBUG update_analysis_plot] ax_sim y-limits: {ax_sim.get_ylim()}")

    ax_exp.relim()
    ax_exp.autoscale_view(scalex=True, scaley=True)
    ax_exp.margins(y=0.1)  # Add 10% y-margin
    print(f"[DEBUG update_analysis_plot] ax_exp y-limits: {ax_exp.get_ylim()}")

    print(f"[DEBUG update_analysis_plot] line_sim visible: {line_sim.get_visible()}, zorder: {line_sim.get_zorder()}, color: {line_sim.get_color()}")
    print(f"[DEBUG update_analysis_plot] line_exp visible: {line_exp.get_visible()}, zorder: {line_exp.get_zorder()}, color: {line_exp.get_color()}")
    print(f"[DEBUG update_analysis_plot] ax_sim has {len(ax_sim.lines)} lines")
    print(f"[DEBUG update_analysis_plot] ax_exp has {len(ax_exp.lines)} lines")
