# Diffusion–Reaction GUI Simulator

Multilayer 1D diffusion–reaction simulator with a Tkinter GUI and Crank–Nicolson time integration. Each layer may have unique thickness, diffusivity, and reaction rate; the final layer acts as the absorbing/ reactive target and reports flux and cumulative uptake over time.

## Requirements

- Python 3.10+
- Packages: `numpy`, `matplotlib` (Tkinter ships with CPython)

Install dependencies:

```bash
python -m pip install numpy matplotlib
```

## Running the simulator

- GUI: `python -m diffreact_gui`
- CLI mode: `python -m diffreact_gui.main --cli [--debug]`
- PyInstaller entry point: `python run_diffreact_gui.py`

Outputs land in `results/` by default (`results.npz`, `flux_vs_time.csv`, `concentration_profiles.csv`, `profile_t_<t>.csv`, `metadata.json`).

## GUI features

- Layer table for per-layer parameters (top → bottom); the last row is the target layer.
- Progress bar updates while the solver runs; completion dialog confirms success.
- Built-in “View Manual” window summarises the governing equations, usage, and input constraints.
- Time navigation beneath the profile plot (slider, spin box, step buttons) keeps the displayed snapshot and label in sync.
- Validation before every run checks physical constraints (positive thickness/diffusivity, `Δt < t_max`, etc.) and shows actionable error dialogs if violated.
- Optional Arrhenius helper (enter T, D₀, Ea) to populate layer diffusivities.
- Flux probe entry lets you inspect flux/cumulative uptake at an arbitrary position in the stack.
- Mass/uptake metrics are reported for the final layer; choose its properties accordingly.
- Flux view selector lets you focus on surface, interface, exit, or probe flux/uptake curves individually.

## Numerical notes

- Crank–Nicolson scheme on a shared non-uniform grid; continuity of concentration and flux enforced at every interface.
- Time step automatically capped based on the smallest `(Δx)²/D` to suppress boundary oscillations. Diagnostics record both the requested and effective `Δt`.
- Mass balance warning triggers when `|R| / max(|ΔM|, 10⁻¹²)` exceeds 1 %.
- For passive layers (`k = 0`), coarse node counts (2–4) are generally sufficient; reserve finer meshes for the reactive target layer to save memory.

Right-hand boundary options:

- **Neumann**: `∂C/∂x = 0` (impermeable backside)
- **Dirichlet**: `C = 0` (perfect sink)

## Testing

```bash
python run_tests.py
```

or (if `pytest` is available):

```bash
pytest -q
```

## Packaging

Create a single-file executable (Windows example):

```bash
pyinstaller --onefile --noconsole --name DiffReactGUI run_diffreact_gui.py
```
