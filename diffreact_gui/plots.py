from __future__ import annotations

"""Matplotlib plotting helpers for the GUI."""

from typing import Dict, Tuple

import matplotlib.pyplot as plt
import numpy as np


def create_figures() -> Tuple[plt.Figure, Dict[str, any]]:
    fig, (ax_flux, ax_prof) = plt.subplots(2, 1, figsize=(9, 7), sharex=False)
    fig.subplots_adjust(hspace=0.35)

    ax_flux.set_title("Flux & Uptake vs Time")
    ax_flux.set_xlabel("t [s]")
    ax_flux.set_ylabel("J [mol/(m^2·s)]")
    ax_flux_secondary = ax_flux.twinx()
    ax_flux_secondary.set_ylabel("Integrated uptake [mol/m^2]")

    line_J_source, = ax_flux.plot([], [], label="J_source", color="tab:blue")
    line_J_target, = ax_flux.plot([], [], label="J_target", color="tab:orange")
    line_J_end, = ax_flux.plot([], [], label="J_end", color="tab:green", linestyle="--")

    line_cum_target, = ax_flux_secondary.plot(
        [], [], label="cum_target", color="tab:red", linestyle="-.")
    line_mass_target, = ax_flux_secondary.plot(
        [], [], label="mass_target", color="tab:purple", linestyle=":")

    lines = [line_J_source, line_J_target, line_J_end, line_cum_target, line_mass_target]
    labels = [line.get_label() for line in lines]
    ax_flux.legend(lines, labels, loc="best")

    ax_prof.set_title("Concentration Profile")
    ax_prof.set_xlabel("x [m]")
    ax_prof.set_ylabel("C [mol/m^3]")
    line_prof, = ax_prof.plot([], [], color="tab:blue")

    artists = {
        "figure": fig,
        "ax_flux": ax_flux,
        "ax_flux_secondary": ax_flux_secondary,
        "ax_prof": ax_prof,
        "line_J_source": line_J_source,
        "line_J_target": line_J_target,
        "line_J_end": line_J_end,
        "line_cum_target": line_cum_target,
        "line_mass_target": line_mass_target,
        "line_prof": line_prof,
        "boundary_lines": [],
    }
    return fig, artists


def update_flux_axes(
    artists: Dict[str, any],
    t: np.ndarray,
    J_source: np.ndarray,
    J_target: np.ndarray,
    J_end: np.ndarray,
    cum_target: np.ndarray,
    mass_target: np.ndarray,
) -> None:
    artists["line_J_source"].set_data(t, J_source)
    artists["line_J_target"].set_data(t, J_target)
    artists["line_J_end"].set_data(t, J_end)
    artists["line_cum_target"].set_data(t, cum_target)
    artists["line_mass_target"].set_data(t, mass_target)

    ax_flux = artists["ax_flux"]
    ax_flux.relim()
    ax_flux.autoscale_view()

    ax_flux_secondary = artists["ax_flux_secondary"]
    ax_flux_secondary.relim()
    ax_flux_secondary.autoscale_view()


def update_profile_axes(
    artists: Dict[str, any],
    x: np.ndarray,
    C: np.ndarray,
    boundaries: np.ndarray,
) -> None:
    artists["line_prof"].set_data(x, C)
    ax = artists["ax_prof"]

    for line in artists.get("boundary_lines", []):
        line.remove()
    artists["boundary_lines"] = []

    # Skip first and last boundary (0 and total thickness)
    for boundary in boundaries[1:-1]:
        vline = ax.axvline(boundary, color="gray", linestyle="--", alpha=0.3)
        artists["boundary_lines"].append(vline)

    ax.relim()
    ax.autoscale_view()
