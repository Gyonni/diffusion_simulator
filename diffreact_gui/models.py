from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional


@dataclass(frozen=True)
class LayerParam:
    """Single diffusion layer specification.

    Attributes:
        name: Layer identifier
        thickness: Physical thickness [m]
        diffusivity: Fickian diffusion coefficient [m^2/s]
        reaction_rate: First-order reaction constant [1/s], use 0 for pure diffusion
        nodes: Number of grid nodes for this layer (must be >= 2)

    Note:
        Parameter validation is performed in validate_params() in utils.py
    """

    name: str
    thickness: float  # meters
    diffusivity: float  # m^2/s
    reaction_rate: float  # 1/s (set 0 for pure diffusion)
    nodes: int  # grid nodes for this layer (>=2)


@dataclass
class SimParams:
    """Simulation parameters for the multilayer diffusion model.

    Attributes:
        layers: List of layer specifications (top to bottom)
        Cs: Surface concentration at x=0 [mol/m^3]
        dt: Time step [s]
        t_max: Total simulation time [s]
        bc_right: Right boundary condition ('Neumann' or 'Dirichlet')
        probe_position: Optional position for flux probe [m]
    """

    layers: List[LayerParam]
    Cs: float  # mol/m^3
    dt: float  # seconds
    t_max: float  # seconds
    bc_right: str  # 'Neumann' or 'Dirichlet'
    probe_position: Optional[float] = None
