"""Configuration defaults and presets for the Diffusion–Reaction GUI Simulator.

All physical units use SI:
- thickness: m
- diffusivity: m^2/s
- reaction_rate: 1/s
- Cs: mol/m^3
- dt: s
- t_max: s
- temperature: K
- capacitance: F
- area: m^2
- distance: m
- voltage: V
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple, Dict, Any

from .models import LayerParam


@dataclass(frozen=True)
class Defaults:
    """Default simulation parameters for the GUI.

    Attributes:
        Cs: Surface concentration [mol/m^3]
        dt: Time step [s]
        t_max: Total simulation time [s]
        bc_right: Right boundary condition ('Neumann' or 'Dirichlet')
        layers: Tuple of layer specifications (top to bottom)
    """
    Cs: float = 1.0
    dt: float = 1e-3
    t_max: float = 0.5
    bc_right: str = "Dirichlet"  # Options: Neumann, Dirichlet
    layers: Tuple[LayerParam, ...] = (
        LayerParam(
            name="Barrier",
            thickness=2.0e-7,
            diffusivity=5.0e-15,  # Will be ignored when D0/Ea are set
            reaction_rate=0.0,
            nodes=11,
            D0=1.0e-6,
            Ea=1.0,
        ),
        LayerParam(
            name="Target",
            thickness=3.0e-7,
            diffusivity=1.0e-14,  # Will be ignored when D0/Ea are set
            reaction_rate=0.0,
            nodes=21,
            D0=1.0e-7,
            Ea=1.0,
        ),
    )


# ============================================================================
# PRESET CONFIGURATIONS
# ============================================================================

# Setup Tab Presets
# ------------------
SETUP_PRESETS: Dict[str, Dict[str, Any]] = {
    "Default (Barrier + Target)": {
        "Cs": 1.0,
        "dt": 1e-3,
        "t_max": 0.5,
        "bc_right": "Dirichlet",
        "layers": (
            LayerParam(
                name="Barrier",
                thickness=2.0e-7,
                diffusivity=5.0e-15,
                reaction_rate=0.0,
                nodes=11,
                D0=1.0e-6,
                Ea=1.0,
            ),
            LayerParam(
                name="Target",
                thickness=3.0e-7,
                diffusivity=1.0e-14,
                reaction_rate=0.0,
                nodes=21,
                D0=1.0e-7,
                Ea=1.0,
            ),
        ),
    },
    "Fast Diffusion (High D)": {
        "Cs": 1.0,
        "dt": 1e-4,
        "t_max": 0.1,
        "bc_right": "Dirichlet",
        "layers": (
            LayerParam(
                name="Fast Layer",
                thickness=5.0e-7,
                diffusivity=1.0e-12,
                reaction_rate=0.0,
                nodes=21,
                D0=1.0e-5,
                Ea=0.5,
            ),
        ),
    },
    "Slow Diffusion (Low D)": {
        "Cs": 1.0,
        "dt": 1e-2,
        "t_max": 10.0,
        "bc_right": "Dirichlet",
        "layers": (
            LayerParam(
                name="Slow Layer",
                thickness=5.0e-7,
                diffusivity=1.0e-16,
                reaction_rate=0.0,
                nodes=21,
                D0=1.0e-9,
                Ea=2.0,
            ),
        ),
    },
    "Three-Layer Stack": {
        "Cs": 1.0,
        "dt": 1e-3,
        "t_max": 1.0,
        "bc_right": "Dirichlet",
        "layers": (
            LayerParam(name="Layer1", thickness=1.0e-7, diffusivity=1.0e-14, reaction_rate=0.0, nodes=5, D0=1.0e-6, Ea=0.8),
            LayerParam(name="Layer2", thickness=2.0e-7, diffusivity=5.0e-15, reaction_rate=0.0, nodes=11, D0=5.0e-7, Ea=1.0),
            LayerParam(name="Layer3", thickness=2.0e-7, diffusivity=1.0e-15, reaction_rate=0.0, nodes=11, D0=1.0e-7, Ea=1.2),
        ),
    },
    "Reactive Target": {
        "Cs": 1.0,
        "dt": 1e-3,
        "t_max": 0.5,
        "bc_right": "Dirichlet",
        "layers": (
            LayerParam(
                name="Passive",
                thickness=2.0e-7,
                diffusivity=5.0e-15,
                reaction_rate=0.0,
                nodes=5,
                D0=1.0e-6,
                Ea=1.0,
            ),
            LayerParam(
                name="Reactive",
                thickness=3.0e-7,
                diffusivity=1.0e-14,
                reaction_rate=10.0,  # High reaction rate
                nodes=21,
                D0=1.0e-7,
                Ea=1.0,
            ),
        ),
    },
}

# Results Tab Presets
# -------------------
RESULTS_PRESETS: Dict[str, Dict[str, Any]] = {
    "Standard View": {
        "flux_position": "target",  # "source", "interface", "target", "probe"
        "probe_position": 2.5e-7,
        "selected_time_index": 0,
    },
    "Interface Monitoring": {
        "flux_position": "interface",
        "probe_position": 2.0e-7,  # At interface
        "selected_time_index": 0,
    },
    "End-of-Simulation": {
        "flux_position": "target",
        "probe_position": 5.0e-7,
        "selected_time_index": -1,  # Last time point
    },
}

# Analysis Tab Presets
# --------------------
ANALYSIS_PRESETS: Dict[str, Dict[str, Any]] = {
    "Temperature Sweep Analysis": {
        "x_axis": "temperature",
        "sim_y": "C",
        "sim_filter_1": 0.5,  # time [s]
        "sim_filter_2": 5.0e-7,  # position [m]
        "exp_filter_1": 0.5,  # time [s]
        "exp_filter_2": 5.0e-7,  # position [m]
        "fixed_var": "position",
        "fixed_value": 1.0e-6,
        "row_var": "time",
        "col_var": "temperature",
        "epsilon_r": 3.9,
        "A": 1.0e-4,
        "d": 1.0e-9,
        "V0": 0.0,
    },
    "Time Evolution": {
        "x_axis": "time",
        "sim_y": "C",
        "sim_filter_1": 600.0,  # temperature [K]
        "sim_filter_2": 5.0e-7,  # position [m]
        "exp_filter_1": 600.0,  # temperature [K]
        "exp_filter_2": 5.0e-7,  # position [m]
        "fixed_var": "position",
        "fixed_value": 1.0e-6,
        "row_var": "time",
        "col_var": "temperature",
        "epsilon_r": 3.9,
        "A": 1.0e-4,
        "d": 1.0e-9,
        "V0": 0.0,
    },
    "Position Profile": {
        "x_axis": "position",
        "sim_y": "C",
        "sim_filter_1": 600.0,  # temperature [K]
        "sim_filter_2": 0.5,  # time [s]
        "exp_filter_1": 600.0,  # temperature [K]
        "exp_filter_2": 0.5,  # time [s]
        "fixed_var": "temperature",
        "fixed_value": 600.0,
        "row_var": "time",
        "col_var": "position",
        "epsilon_r": 3.9,
        "A": 1.0e-4,
        "d": 1.0e-9,
        "V0": 0.0,
    },
    "Flux Analysis": {
        "x_axis": "temperature",
        "sim_y": "J_target",
        "sim_filter_1": 0.5,  # time [s]
        "sim_filter_2": 5.0e-7,  # position [m]
        "exp_filter_1": 0.5,  # time [s]
        "exp_filter_2": 5.0e-7,  # position [m]
        "fixed_var": "position",
        "fixed_value": 1.0e-6,
        "row_var": "time",
        "col_var": "temperature",
        "epsilon_r": 3.9,
        "A": 1.0e-4,
        "d": 1.0e-9,
        "V0": 0.0,
    },
}


# Directory for simulation outputs
RESULTS_DIR = "results"

# Logging configuration
LOG_LEVEL = "INFO"
