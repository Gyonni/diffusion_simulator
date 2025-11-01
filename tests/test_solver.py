from __future__ import annotations

import numpy as np

from diffreact_gui.models import LayerParam, SimParams
from diffreact_gui.solver import run_simulation, run_temperature_sweep, mass_balance_diagnostics
from diffreact_gui.physics import steady_flux, calculate_diffusivity_arrhenius


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


def test_run_simulation_return_keys():
    """Test that run_simulation returns correct dictionary keys (t, not time; J_end, not J_exit)."""
    params = SimParams(
        layers=[LayerParam(name="Layer", thickness=1e-6, diffusivity=1e-14, reaction_rate=0.0, nodes=50)],
        Cs=1.0,
        dt=1e-3,
        t_max=1e-2,
        bc_right="Neumann",
    )
    res = run_simulation(params)

    # Test for correct key names (bug fix verification)
    assert "t" in res, "Expected 't' key in result dictionary"
    assert "time" not in res, "'time' key should not exist (use 't' instead)"
    assert "J_end" in res, "Expected 'J_end' key in result dictionary"
    assert "J_exit" not in res, "'J_exit' key should not exist (use 'J_end' instead)"

    # Test shapes
    assert isinstance(res["t"], np.ndarray)
    assert isinstance(res["J_end"], np.ndarray)
    assert len(res["t"]) == len(res["J_end"])


def test_temperature_sweep_basic():
    """Test temperature sweep functionality with Arrhenius parameters."""
    D0 = 1e-10  # m^2/s
    Ea = 0.5    # eV
    temps = [300.0, 350.0, 400.0]

    params = SimParams(
        layers=[
            LayerParam(
                name="Layer1",
                thickness=1e-6,
                diffusivity=None,  # Will be calculated from D0, Ea
                D0=D0,
                Ea=Ea,
                reaction_rate=0.0,
                nodes=50,
            )
        ],
        Cs=1.0,
        dt=1e-3,
        t_max=1e-2,
        bc_right="Neumann",
        temperatures=temps,
    )

    res = run_temperature_sweep(params)

    # Check return structure
    assert "temperatures" in res
    assert "t" in res
    assert "x" in res
    assert "C_Txt" in res
    assert "J_surface_Tt" in res
    assert "J_end_Tt" in res

    # Check shapes
    assert len(res["temperatures"]) == len(temps)
    assert res["C_Txt"].shape[0] == len(temps)  # First dimension is temperature
    assert res["J_surface_Tt"].shape[0] == len(temps)
    assert res["J_end_Tt"].shape[0] == len(temps)

    # Verify diffusivity increases with temperature
    D_300 = calculate_diffusivity_arrhenius(D0, Ea, 300.0)
    D_400 = calculate_diffusivity_arrhenius(D0, Ea, 400.0)
    assert D_400 > D_300, "Diffusivity should increase with temperature"


def test_temperature_sweep_uses_correct_keys():
    """Test that temperature sweep correctly uses 't' and 'J_end' keys from run_simulation."""
    D0 = 1e-10
    Ea = 0.5
    temps = [300.0, 350.0]

    params = SimParams(
        layers=[
            LayerParam(
                name="TestLayer",
                thickness=1e-6,
                diffusivity=None,
                D0=D0,
                Ea=Ea,
                reaction_rate=0.0,
                nodes=30,
            )
        ],
        Cs=1.0,
        dt=1e-3,
        t_max=5e-3,
        bc_right="Neumann",
        temperatures=temps,
    )

    # This should not raise KeyError for 'time' or 'J_exit' (bug fix verification)
    try:
        res = run_temperature_sweep(params)
        # If we get here, the bug is fixed
        assert True
    except KeyError as e:
        assert False, f"KeyError raised: {e}. Check if run_temperature_sweep uses correct keys ('t', 'J_end')."

    # Verify result structure
    assert res["t"] is not None
    assert res["J_end_Tt"] is not None
    assert res["J_end_Tt"].shape == (len(temps), len(res["t"]))


def test_arrhenius_calculation():
    """Test Arrhenius diffusivity calculation."""
    D0 = 1e-10  # m^2/s
    Ea = 0.5    # eV
    T1 = 300.0  # K
    T2 = 400.0  # K

    D1 = calculate_diffusivity_arrhenius(D0, Ea, T1)
    D2 = calculate_diffusivity_arrhenius(D0, Ea, T2)

    # Basic sanity checks
    assert D1 > 0, "Diffusivity must be positive"
    assert D2 > 0, "Diffusivity must be positive"
    assert D2 > D1, "Diffusivity should increase with temperature"

    # D = D0 * exp(-Ea / (kb*T))
    # With Ea = 0.5 eV and T = 300 K, the exponential factor is very small
    # exp(-0.5 / (8.617e-5 * 300)) = exp(-19.3) ≈ 4e-9
    # So D1 ≈ 1e-10 * 4e-9 = 4e-19, which is valid
    assert D1 < D0, "D should be less than D0 at finite temperature with positive Ea"
    assert D2 < D0, "D should be less than D0 at finite temperature with positive Ea"

    # Verify Arrhenius relationship: D2/D1 = exp(Ea/kb * (1/T1 - 1/T2))
    ratio = D2 / D1
    assert ratio > 1, "Ratio should be greater than 1 since T2 > T1"
