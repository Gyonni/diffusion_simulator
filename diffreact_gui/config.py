"""Configuration defaults for the Diffusion–Reaction GUI Simulator.

All physical units use SI:
- thickness: m
- diffusivity: m^2/s
- reaction_rate: 1/s
- Cs: mol/m^3
- dt: s
- t_max: s
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

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
            diffusivity=5.0e-15,
            reaction_rate=0.0,
            nodes=81,
        ),
        LayerParam(
            name="Target",
            thickness=3.0e-7,
            diffusivity=1.0e-14,
            reaction_rate=1.0e3,
            nodes=121,
        ),
    )


# Directory for simulation outputs
RESULTS_DIR = "results"

# Logging configuration
LOG_LEVEL = "INFO"
