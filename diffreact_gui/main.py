from __future__ import annotations

import argparse
import logging

from .config import Defaults, RESULTS_DIR
from .gui_elements import App
from .models import SimParams
from .solver import mass_balance_diagnostics, run_simulation
from .utils import (
    ensure_results_dir,
    save_csv_flux,
    save_metadata,
    save_profiles_matrix,
    save_results_npz,
    setup_logging,
)


def run_cli(debug: bool = False) -> None:
    setup_logging()
    log = logging.getLogger("cli")
    defaults = Defaults()
    params = SimParams(
        layers=list(defaults.layers),
        Cs=defaults.Cs,
        dt=defaults.dt,
        t_max=defaults.t_max,
        bc_right=defaults.bc_right,
    )
    log.info(
        "Running CLI simulation with %d layers: %s",
        len(params.layers),
        [layer.name for layer in params.layers],
    )
    res = run_simulation(params)


    # Diagnostics
    residual, rel = mass_balance_diagnostics(
        res["k_profile"],
        res["t"],
        res["x"],
        res["C_xt"],
        res["J_source"],
        res["J_end"],
    )
    if rel > 0.01:
        log.warning("Mass-balance residual too high: %.3f%% (residual=%e)", rel * 100, residual)
    else:
        log.info("Mass-balance residual OK: %.3f%%", rel * 100)

    # Save
    base = ensure_results_dir(RESULTS_DIR)
    npz = save_results_npz(
        base,
        t=res["t"],
        x=res["x"],
        C_xt=res["C_xt"],
        J_source=res["J_source"],
        J_target=res["J_target"],
        J_end=res["J_end"],
        cum_source=res["cum_source"],
        cum_target=res["cum_target"],
        cum_end=res["cum_end"],
        mass_target=res["mass_target"],
        layer_boundaries=res["layer_boundaries"],
        D_nodes=res.get("D_nodes"),
        D_edges=res.get("D_edges"),
        J_probe=res.get("J_probe"),
        cum_probe=res.get("cum_probe"),
        probe_position=params.probe_position,
    )
    csv = save_csv_flux(
        base,
        res["t"],
        res["J_source"],
        res["J_target"],
        res["J_end"],
        res["cum_source"],
        res["cum_target"],
        res["cum_end"],
        res["mass_target"],
        J_probe=res.get("J_probe"),
        cum_probe=res.get("cum_probe"),
    )
    save_profiles_matrix(base, res["x"], res["t"], res["C_xt"])
    save_metadata(base, params, extras={"layer_boundaries": res["layer_boundaries"].tolist()})
    log.info("Saved: %s, %s", npz, csv)
    if debug:
        log.info("Debug mode: arrays saved to NPZ with shapes: t=%s, x=%s, C_xt=%s", res["t"].shape, res["x"].shape, res["C_xt"].shape)


def main() -> None:
    parser = argparse.ArgumentParser(description="1D Diffusion–Reaction Simulator")
    parser.add_argument("--cli", action="store_true", help="Run a CLI simulation and exit")
    parser.add_argument("--debug", action="store_true", help="Extra debug outputs in CLI mode")
    args = parser.parse_args()

    if args.cli:
        run_cli(debug=args.debug)
    else:
        # GUI mode
        setup_logging()
        app = App()
        app.mainloop()


if __name__ == "__main__":
    main()
