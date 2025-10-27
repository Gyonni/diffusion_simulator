# Diffusion–Reaction GUI Simulator

A GUI-based multilayer diffusion–reaction simulator using a Crank–Nicolson scheme. Each layer may have distinct thickness, diffusivity, and reaction rate; the final layer is treated as the absorbing target and reports flux and cumulative uptake.

- GUI entry: `python -m diffreact_gui`
- CLI run: `python -m diffreact_gui.main --cli [--debug]`
- Standalone launcher for PyInstaller: `python run_diffreact_gui.py`

Outputs (default): `results/results.npz`, `results/flux_vs_time.csv`, `results/profile_t_<t>.csv`, `results/metadata.json`.

PyInstaller (one-file):

```
pyinstaller --onefile --noconsole --name DiffReactGUI run_diffreact_gui.py
```

Python 3.10+ recommended. Dependencies: numpy, matplotlib, tkinter (builtin).

Right-hand boundary modes:
- **Neumann**: `∂C/∂x = 0` at the stack exit (impermeable)
- **Dirichlet**: `C = 0` at the stack exit (perfect sink)

The solver checks mass balance (`|R|/|ΔM|`) and raises a warning if the residual exceeds 1 %. Use the GUI layer table to tune spatial resolution (target `ell_over_dx_min > 10`) for accurate uptake predictions.
