from __future__ import annotations

"""Analytical helpers and derived quantities.

All functions use SI units.
"""
import math
from typing import Literal


def char_length_ell(D: float, k: float) -> float:
    """Return characteristic length ell = sqrt(D/k). For k=0, return math.inf."""
    if k <= 0:
        return math.inf
    return math.sqrt(D / k)


def damkohler_number(L: float, D: float, k: float) -> float:
    """Return Da = L / ell."""
    ell = char_length_ell(D, k)
    if math.isinf(ell):
        return 0.0
    return L / ell


def steady_flux(D: float, k: float, L: float, Cs: float, bc_right: Literal["Neumann", "Dirichlet"]) -> float:
    """Analytical steady-state flux at x=0 for select BCs.

    For Dirichlet at x=0 (C=Cs) and:
    - Neumann at x=L: J = (D/ell) * Cs * tanh(L/ell)
    - Dirichlet at x=L (perfect sink): J = (D/ell) * Cs * coth(L/ell)

    For k=0, use limits:
    - Neumann: J = D * Cs * (0) / L -> approaches 0 as steady state is uniform Cs
    - Dirichlet: J = D * Cs / L
    """
    ell = char_length_ell(D, k)
    if math.isinf(ell):
        if bc_right == "Neumann":
            return 0.0
        # Dirichlet perfect sink with k=0
        return D * Cs / L

    Da = L / ell
    if bc_right == "Neumann":
        return (D / ell) * Cs * math.tanh(Da)
    elif bc_right == "Dirichlet":
        # Avoid division by zero for very small Da; coth(x) ~ 1/x + x/3
        if Da < 1e-12:
            return (D / ell) * Cs * (1.0 / Da)
        return (D / ell) * Cs / math.tanh(Da)
    else:
        raise ValueError("Unsupported bc_right for steady_flux")

