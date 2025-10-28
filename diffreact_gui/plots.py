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

    ax_prof.set_title("Concentration Profile")
    ax_prof.set_xlabel("x [m]")
    ax_prof.set_ylabel("C [mol/m^3]")
    line_prof, = ax_prof.plot([], [], color="tab:blue")

    artists = {
        "figure": fig,
        "ax_flux": ax_flux,
        "ax_flux_secondary": ax_flux_secondary,
        "ax_flux_legend": None,
        "ax_prof": ax_prof,
        "line_J_surface": line_J_surface,
        "line_J_target": line_J_target,
        "line_J_exit": line_J_exit,
        "line_J_probe": line_J_probe,
        "line_cum_surface": line_cum_surface,
        "line_cum_target": line_cum_target,
        "line_cum_exit": line_cum_exit,
        "line_mass_target": line_mass_target,
        "line_cum_probe": line_cum_probe,
        "line_prof": line_prof,
        "boundary_lines": [],
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
    artists: Dict[str, any],
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
