from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional
import numpy as np


@dataclass(frozen=True)
class LayerParam:
    """Single diffusion layer specification.

    Attributes:
        name: Layer identifier
        thickness: Physical thickness [m]
        diffusivity: Fickian diffusion coefficient [m^2/s]
        reaction_rate: First-order reaction constant [1/s], use 0 for pure diffusion
        nodes: Number of grid nodes for this layer (must be >= 2)
        D0: Pre-exponential factor for Arrhenius equation [m^2/s] (optional)
        Ea: Activation energy [eV] (optional)

    Note:
        Parameter validation is performed in validate_params() in utils.py
        For temperature-dependent simulations, D0 and Ea must be provided.
    """

    name: str
    thickness: float  # meters
    diffusivity: float  # m^2/s
    reaction_rate: float  # 1/s (set 0 for pure diffusion)
    nodes: int  # grid nodes for this layer (>=2)
    D0: Optional[float] = None  # m^2/s (for Arrhenius)
    Ea: Optional[float] = None  # eV (for Arrhenius)


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
        temperatures: Optional list of temperatures [K] for temperature sweep
    """

    layers: List[LayerParam]
    Cs: float  # mol/m^3
    dt: float  # seconds
    t_max: float  # seconds
    bc_right: str  # 'Neumann' or 'Dirichlet'
    probe_position: Optional[float] = None
    temperatures: Optional[List[float]] = None  # Kelvin (for temperature sweep)


@dataclass(frozen=True)
class CapacitorParams:
    """Parallel plate capacitor model parameters for doping analysis.

    Attributes:
        epsilon_r: Relative permittivity (dimensionless)
        A: Electrode area [m^2]
        d: Distance between plates [m]
        V0: Reference voltage [V]

    Note:
        Capacitance C = (epsilon_0 * epsilon_r * A) / d
        where epsilon_0 = 8.854187817e-12 F/m
        Charge change: dq = C * (V - V0)
    """

    epsilon_r: float
    A: float  # m^2
    d: float  # m
    V0: float  # V


@dataclass
class ExperimentalData:
    """Experimental data for doping analysis.

    Attributes:
        name: Dataset identifier
        capacitor: Capacitor model parameters
        fixed_var: Fixed variable name ('temperature', 'time', or 'position')
        fixed_value: Value of the fixed variable
        row_var: Row variable name ('temperature', 'time', or 'position')
        row_values: Array of row variable values
        col_var: Column variable name ('temperature', 'time', or 'position')
        col_values: Array of column variable values
        voltage_grid: 2D array of voltage measurements [row, col] in V
        dq_grid: 2D array of calculated charge changes [row, col] in C (auto-calculated)

    Note:
        The three variables (fixed_var, row_var, col_var) must be distinct and
        cover all three dimensions: temperature, time, position.
        Row and column variables form the 2D grid for voltage measurements.
    """

    name: str
    capacitor: CapacitorParams
    fixed_var: str  # "temperature", "time", "position"
    fixed_value: float
    row_var: str  # "temperature", "time", "position"
    row_values: np.ndarray  # 1D array
    col_var: str  # "temperature", "time", "position"
    col_values: np.ndarray  # 1D array
    voltage_grid: np.ndarray  # 2D array [row, col] in V
    dq_grid: np.ndarray  # 2D array [row, col] in C (calculated)
