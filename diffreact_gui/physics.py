from __future__ import annotations

"""Analytical helpers and derived quantities.

All functions use SI units.
"""
import math
from typing import Literal

# Physical constants
EPSILON_K = 1e-30  # Small value to prevent division by zero
KB_EV = 8.617333262e-5  # Boltzmann constant [eV/K]


def calculate_diffusivity_arrhenius(D0: float, Ea: float, T: float) -> float:
    """Calculate diffusivity using Arrhenius equation.

    Args:
        D0: Pre-exponential factor [m^2/s]
        Ea: Activation energy [eV]
        T: Temperature [K]

    Returns:
        Diffusivity D = D0 * exp(-Ea/(kb*T)) [m^2/s]

    Notes:
        Uses Boltzmann constant kb = 8.617333262e-5 eV/K
    """
    return D0 * math.exp(-Ea / (KB_EV * T))


def char_length_ell(D: float, k: float) -> float:
    """Return characteristic penetration length ell = sqrt(D/k).

    Args:
        D: Diffusion coefficient [m^2/s]
        k: Reaction rate constant [1/s]

    Returns:
        Characteristic length [m], or math.inf if k <= 0
    """
    if k <= 0:
        return math.inf
    return math.sqrt(D / k)


def damkohler_number(L: float, D: float, k: float) -> float:
    """Return Damköhler number Da = L / ell.

    Args:
        L: Film thickness [m]
        D: Diffusion coefficient [m^2/s]
        k: Reaction rate constant [1/s]

    Returns:
        Dimensionless Damköhler number
    """
    ell = char_length_ell(D, k)
    if math.isinf(ell):
        return 0.0
    return L / ell


def steady_flux(
    D: float,
    k: float,
    L: float,
    Cs: float,
    bc_right: Literal["Neumann", "Dirichlet"]
) -> float:
    """Analytical steady-state flux at x=0 for specified boundary conditions.

    Args:
        D: Diffusion coefficient [m^2/s]
        k: Reaction rate constant [1/s]
        L: Film thickness [m]
        Cs: Surface concentration [mol/m^3]
        bc_right: Right boundary condition type

    Returns:
        Steady-state flux at x=0 [mol/(m^2·s)]

    Notes:
        For Dirichlet at x=0 (C=Cs) and:
        - Neumann at x=L: J = (D/ell) * Cs * tanh(L/ell)
        - Dirichlet at x=L (perfect sink): J = (D/ell) * Cs * coth(L/ell)

        For k=0 (pure diffusion):
        - Neumann: J -> 0 (steady state is uniform Cs)
        - Dirichlet: J = D * Cs / L

    Raises:
        ValueError: If bc_right is not 'Neumann' or 'Dirichlet'
    """
    ell = char_length_ell(D, k)

    # Pure diffusion case (k=0)
    if math.isinf(ell):
        if bc_right == "Neumann":
            return 0.0
        elif bc_right == "Dirichlet":
            return D * Cs / L
        else:
            raise ValueError(f"Unsupported bc_right: {bc_right}")

    Da = L / ell

    if bc_right == "Neumann":
        return (D / ell) * Cs * math.tanh(Da)
    elif bc_right == "Dirichlet":
        # Avoid division by zero for very small Da; coth(x) ~ 1/x + x/3
        if Da < 1e-12:
            return (D / ell) * Cs * (1.0 / Da)
        return (D / ell) * Cs / math.tanh(Da)
    else:
        raise ValueError(f"Unsupported bc_right: {bc_right}")

