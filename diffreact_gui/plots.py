from __future__ import annotations

"""Matplotlib plotting helpers for the GUI."""

from typing import Any, Dict, List, Tuple

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D


def create_figures() -> Tuple[plt.Figure, Dict[str, Any]]:
    # 4 subplots: Flux vs Time, C vs Time, C vs x, C vs T
    fig, ((ax_flux, ax_c_time), (ax_prof, ax_temp)) = plt.subplots(2, 2, figsize=(12, 8), sharex=False)
    # Adjust spacing
    fig.subplots_adjust(hspace=0.3, wspace=0.3, top=0.96, bottom=0.06, left=0.08, right=0.92)

    # First plot: Flux & Uptake vs Time
    ax_flux.set_title("Flux & Uptake vs Time")
    ax_flux.set_xlabel("t [s]")
    ax_flux.set_ylabel("Flux [mol/(m^2·s)]")
    ax_flux_secondary = ax_flux.twinx()
    ax_flux_secondary.set_ylabel("Integrated uptake [mol/m^2]")

    line_J_surface, = ax_flux.plot([], [], color="tab:blue")
    line_J_surface.set_label("Flux at surface (x=0)")
    line_J_target, = ax_flux.plot([], [], color="tab:orange")
    line_J_target.set_label("Flux at reporting interface")
    line_J_exit, = ax_flux.plot([], [], color="tab:green", linestyle="--")
    line_J_exit.set_label("Flux at exit (x=L)")
    line_J_probe, = ax_flux.plot([], [], color="tab:red", linestyle=":")
    line_J_probe.set_label("Flux at probe")

    line_cum_surface, = ax_flux_secondary.plot([], [], color="tab:blue", linestyle="-")
    line_cum_surface.set_label("Cumulative uptake at surface")
    line_cum_target, = ax_flux_secondary.plot([], [], color="tab:orange", linestyle="-.")
    line_cum_target.set_label("Cumulative uptake at reporting interface")
    line_cum_exit, = ax_flux_secondary.plot([], [], color="tab:green", linestyle="--")
    line_cum_exit.set_label("Cumulative uptake at exit")
    line_mass_target, = ax_flux_secondary.plot([], [], color="tab:purple", linestyle=":")
    line_mass_target.set_label("Mass in reporting layer")
    line_cum_probe, = ax_flux_secondary.plot([], [], color="tab:brown", linestyle="--")
    line_cum_probe.set_label("Cumulative uptake at probe")

    # Second plot: Concentration vs Time (at selected position)
    ax_c_time.set_title("Concentration vs Time (at selected position)")
    ax_c_time.set_xlabel("t [s]")
    ax_c_time.set_ylabel("C [mol/m^3]")
    line_c_time, = ax_c_time.plot([], [], color="tab:purple", marker='o', markersize=3)

    # Third plot: Concentration Profile (C vs x)
    ax_prof.set_title("Concentration Profile")
    ax_prof.set_xlabel("x [m]")
    ax_prof.set_ylabel("C [mol/m^3]")
    line_prof, = ax_prof.plot([], [], color="tab:blue")

    # Fourth plot: Concentration vs Temperature
    ax_temp.set_title("Concentration vs Temperature (at selected position)")
    ax_temp.set_xlabel("T [K]")
    ax_temp.set_ylabel("C [mol/m^3]")
    line_temp, = ax_temp.plot([], [], marker='o', linestyle='-', color="tab:red")
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
