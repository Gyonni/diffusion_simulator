from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class LayerParam:
    """Single diffusion layer specification."""

    name: str
    thickness: float  # meters
    diffusivity: float  # m^2/s
    reaction_rate: float  # 1/s (set 0 for pure diffusion)
    nodes: int  # grid nodes for this layer (>=2)


@dataclass
class SimParams:
    """Simulation parameters for the multilayer diffusion model."""

    layers: List[LayerParam]
    Cs: float  # mol/m^3
    dt: float  # seconds
    t_max: float  # seconds
    bc_right: str  # 'Neumann' or 'Dirichlet'

