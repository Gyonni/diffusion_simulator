from __future__ import annotations

import numpy as np

from diffreact_gui.models import LayerParam, SimParams
from diffreact_gui.solver import run_simulation, mass_balance_diagnostics
from diffreact_gui.physics import steady_flux


def test_pure_diffusion_neumann_right():
    # k=0, left Dirichlet, right Neumann; right flux should approach ~0
    params = SimParams(
        layers=[LayerParam(name="Layer", thickness=1e-6, diffusivity=1e-14, reaction_rate=0.0, nodes=201)],
        Cs=1.0,
        dt=1e-3,
        t_max=1e-2,
        bc_right="Neumann",
    )
    res = run_simulation(params)
    assert res["C_xt"].shape == (len(res["t"]), len(res["x"]))
    # Right flux small compared to left initial flux
    assert abs(res["J_end"][-1]) < 1e-6, f"J_end={res['J_end'][-1]:.3e}"


def test_steady_flux_neumann_analytical_match():
    # Moderate reaction rate so ell is well-resolved on the grid
    params = SimParams(
        layers=[
            LayerParam(
                name="Film",
                thickness=5e-7,
                diffusivity=1e-14,
                reaction_rate=10.0,
                nodes=401,
            )
        ],
        Cs=1.0,
        dt=1e-4,
        t_max=0.5,
        bc_right="Neumann",
    )
    res = run_simulation(params)
    diag = res["diagnostics"]
    assert diag.get("ell_over_dx_min", 0.0) > 10.0
    assert diag["dt_used"] <= params.dt + 1e-12
    layer = params.layers[0]
    J_anal = steady_flux(layer.diffusivity, layer.reaction_rate, layer.thickness, params.Cs, "Neumann")
    # Take last 10% average as approximation of steady
    n = len(res["t"])
    J_mean = np.mean(res["J_source"][int(0.9 * n) :])
    rel = abs(J_mean - J_anal) / max(abs(J_anal), 1e-12)
    assert rel <= 0.05, f"J_mean={J_mean:.6e}, J_anal={J_anal:.6e}, rel={rel:.3%}"


def test_mass_balance_residual():
    params = SimParams(
        layers=[
            LayerParam(
                name="Barrier",
                thickness=2.5e-7,
                diffusivity=1e-14,
                reaction_rate=0.0,
                nodes=201,
            ),
            LayerParam(
                name="Target",
                thickness=2.5e-7,
                diffusivity=1e-14,
                reaction_rate=10.0,
                nodes=201,
            ),
        ],
        Cs=1.0,
        dt=1e-4,
        t_max=0.1,
        bc_right="Neumann",
    )
    res = run_simulation(params)
    diag = res["diagnostics"]
    assert diag.get("ell_over_dx_min", 0.0) > 10.0
    assert diag["dt_used"] <= params.dt + 1e-12
    R, rel, comps = mass_balance_diagnostics(
        res["k_profile"],
        res["t"],
        res["x"],
        res["C_xt"],
        res["J_source"],
        res["J_end"],
        return_components=True,
    )
    assert rel <= 0.05, (
        "Mass balance mismatch: "
        f"residual={R:.6e}, rel={rel:.3%}, components={comps}"
    )
