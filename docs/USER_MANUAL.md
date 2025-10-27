# Diffusion–Reaction GUI Simulator – User Manual

## 1. Overview

The Diffusion–Reaction GUI Simulator models one-dimensional transport through an arbitrary stack of layers. Each layer can have unique thickness, diffusivity, and reaction rate. The simulator solves

\[
\frac{\partial C}{\partial t} = \frac{\partial}{\partial x}\Bigl(D(x)\,\frac{\partial C}{\partial x}\Bigr) - k(x) C
\]

with a Crank–Nicolson scheme and visualises the results through an interactive Tkinter interface. The final (bottom) layer represents the absorbing material of interest; the tool reports flux into that layer and its accumulated uptake, making it useful for semiconductor diffusion barriers, coatings, and multilayer absorbers.

---

## 2. Quick Start

### 2.1 Environment
- Python 3.10+
- Required packages: `numpy`, `matplotlib`, `tkinter` (built in)

Install dependencies (preferably inside a virtual environment):

```bash
python -m pip install numpy matplotlib
```

### 2.2 Launching the GUI

```bash
python -m diffreact_gui
```

The window opens with default layers and parameters. Modify entries on the left and click **Run Simulation**.

### 2.3 Command-Line Mode

```bash
python -m diffreact_gui.main --cli [--debug]
```

CLI mode runs the default stack, writes outputs to `results/`, and logs mass-balance diagnostics. `--debug` prints array shapes after completion.

---

## 3. Interface Walkthrough

### 3.1 Layout
- **Left panel**: global parameters (`C_s`, `Δt`, `t_max`), right-boundary selector, and a layer table with Add/Update/Remove and reordering controls. The bottom row is interpreted as the absorbing target layer.
- **Right panel**: stacked Matplotlib plots (flux/uptake above, concentration profile below), a navigation toolbar for zoom/pan/reset, and a time slider labelled `Time [s]: …`.

### 3.2 Workflow
1. Configure global settings and build the layer stack. Set `k=0` for purely diffusive barriers; specify non-zero `k` only for layers with reactions/absorption.
2. Choose the terminal boundary (`Dirichlet` sink or `Neumann` impermeable) and click **Run Simulation**. The button remains disabled while the solver runs in a background thread.
3. After completion:
   - The flux chart displays `J_source(t)` (entry surface), `J_target(t)` (into the target layer), `J_end(t)` (stack exit), cumulative uptake `∫J_target dt`, and the integrated mass inside the target layer.
   - The concentration profile spans the entire stack with dashed vertical lines marking interfaces.
4. Use the Matplotlib toolbar to zoom or pan. Adjust the bottom controls (slider, ◀/▶ step buttons, or the numeric spin box) to inspect different snapshots; the label updates to the exact simulation time.
5. Export results via **Export Flux CSV** (writes `results.npz` and `flux_vs_time.csv`) or export the current profile via **Export Current Profile CSV**.

### 3.3 Status Messages
- Mass-balance warnings (relative residual > 1 %) appear in a modal dialog.
- Numerical failures after repeated `Δt` reductions surface as error dialogs.

---

## 4. Simulation Parameters

| Global control | Units | Default | Description |
|----------------|-------|---------|-------------|
| `C_s` | mol·m⁻³ | 1.0 | Dirichlet concentration at `x = 0`. |
| `Δt` | s | 1×10⁻³ | Time step; automatically halved on solver failure down to `max(10⁻⁹, 10⁻⁶·t_max)`. |
| `t_max` | s | 0.5 | Total simulated time. |
| Right BC | – | Dirichlet | Terminal boundary (`Dirichlet` or `Neumann`). |

### 4.1 Layer Table Columns

| Column | Units | Description |
|--------|-------|-------------|
| Name | – | Label stored in metadata/exports. Final row is the target material. |
| Thickness | m | Physical thickness of the layer segment. |
| Diffusivity | m²·s⁻¹ | Fickian diffusion coefficient. |
| Reaction `k` | s⁻¹ | First-order sink rate; use `0` for purely diffusive layers. |
| Nodes | – | Grid nodes assigned to the layer (≥ 2). Interfaces reuse the final node of the preceding layer. |

### 4.2 Right-Boundary Models
1. **Neumann (impermeable)** — `∂C/∂x = 0` at `x = L_total`; represents a sealed backside.
2. **Dirichlet (perfect sink)** — `C(L_total,t) = 0`; models an ideal sink beyond the target layer.

### 4.3 Derived Diagnostics
- **Target penetration depth**: `ℓ = √(D_target/k_target)` (∞ if `k_target = 0`).
- **Resolution indicator**: `ell_over_dx_min` reports how well the target layer resolves `ℓ`; values > 10 are recommended.
- **Total thickness**: recorded in `diagnostics['total_thickness']` for verification against design values.

---

## 5. Numerical Model Notes

### 5.1 Discretisation
- Layer meshes are concatenated into a global non-uniform grid; adjacent layers share interface nodes to maintain continuity.
- Piecewise-constant `D(x)` and `k(x)` are handled via harmonic averaging across interfaces.
- The Crank–Nicolson scheme discretises `∂C/∂t = ∂/∂x(D ∂C/∂x) - kC`, producing a tridiagonal system tailored to the variable spacing.
- For passive layers (`k = 0`) you can keep node counts low (two to four nodes) because their profiles remain nearly linear; reserve finer meshes for the reactive target layer.

### 5.2 Stability Guidance
- Crank–Nicolson is unconditionally stable, but accuracy demands adequate spatial resolution. Increase per-layer node counts until `ell_over_dx_min` comfortably exceeds 10.
- The solver automatically caps `Δt` using the smallest `(Δx)^2/D` across the stack to suppress boundary oscillations, and will halve it further (up to six times) if the linear solve fails. The results include `dt_used` and `dt_requested` in the diagnostics block.

### 5.3 Flux & Uptake Metrics
- `J_source` — flux at the entry surface (`x = 0`).
- `J_target` — flux entering the target layer (interface between the last two layers, or equal to `J_end` in single-layer cases).
- `J_end` — flux at the stack exit (`x = L_total`).
- `cum_source`, `cum_target` — cumulative integrals of `J_source` and `J_target`.
- `mass_target(t) = ∫_{target} C(x,t) dx` — stored mass per unit area inside the target layer.

### 5.4 Mass-Balance Diagnostic

\[
R = \int J_{\text{source}}\,dt - \int J_{\text{end}}\,dt - \iint k(x)C\,dx\,dt - \Bigl[\int C(x,t_{\max})\,dx - \int C(x,0)\,dx\Bigr]
\]

Values of `|R|/max(|ΔM|, 10⁻¹²)` above 1 % trigger a GUI warning, indicating under-resolved meshes or aggressive time steps.

---

## 6. Outputs

All runs write into `results/` (created on demand):

| File | Description |
|------|-------------|
| `results.npz` | Arrays `t`, `x`, `C_xt`, `J_source`, `J_target`, `J_end`, `cum_source`, `cum_target`, `mass_target`, `layer_boundaries`. |
| `flux_vs_time.csv` | CSV columns: `t`, `J_source`, `J_target`, `J_end`, `cum_source`, `cum_target`, `cum_end`, `mass_target` (units listed in the header). |
| `profile_t_<t>.csv` | Exported concentration profile for the selected slider time. |
| `metadata.json` | Global parameters, full layer table, boundary condition, and layer boundaries. |

Outputs are overwritten for each run; copy the directory to archive previous results.

---

## 7. Recommended Workflow

1. **Single-layer benchmark** — run a lone reactive layer and compare `J_source` against the analytical steady-state flux (`physics.steady_flux`).
2. **Add barriers** — insert zero-reaction (`k=0`) layers ahead of the target material to assess diffusion delays. Increase node counts until `ell_over_dx_min` stabilises.
3. **Boundary sensitivity** — toggle between Neumann and Dirichlet endings to evaluate retention versus sink behaviour.
4. **Reporting** — export the flux CSV for temporal metrics and the profile CSV for spatial snapshots at key times.

---

## 8. Troubleshooting

| Symptom | Likely cause | Suggested action |
|---------|--------------|------------------|
| Mass-balance warning (> 1 %) | Target layer under-resolved or `Δt` too large | Increase node counts where gradients are steep, reduce `Δt`, or re-check material properties. |
| Solver error “Zero pivot” | Excessive `Δt` or extreme parameters | Allow the automatic halving to proceed, or manually supply a smaller `Δt`. |
| Noisy flux traces | Inadequate spatial resolution | Increase nodes in layers with strong gradients. |
| GUI feels sluggish | Very fine meshes with tiny `Δt` | Wait for completion or run from the CLI for batch studies. |

---

## 9. PyInstaller Packaging (Windows)

### 9.1 Preparation
- Ensure Python 3.10+ is installed alongside required packages.
- Working inside a virtual environment is recommended.

### 9.2 Build

```bash
python -m pip install pyinstaller
pyinstaller --onefile --noconsole --name DiffReactGUI run_diffreact_gui.py
```

- Output: `dist/DiffReactGUI.exe`
- The executable launches the GUI directly. For CLI mode, continue using Python with `--cli`.

### 9.3 Suggested Distribution Layout

```
DistReactGUI/
├── DiffReactGUI.exe
├── README.txt
├── LICENSE (MIT)
├── examples/
│   ├── default_config.json
│   └── test_case_steady_state.csv
└── logs/
```

Include basic usage instructions and any additional runtime requirements in `README.txt`.

---

## 10. Extensibility Notes

The project is structured for modular growth:

- `solver.py` — multilayer Crank–Nicolson solver and diagnostics.
- `physics.py` — analytical references (steady-state flux, characteristic length).
- `plots.py` & `gui_elements.py` — visualisation and Tkinter GUI components.
- `utils.py` — validation, logging, and export helpers.

Future enhancements outlined in the specifications include Robin boundaries, temperature-dependent diffusivity, multi-dimensional extensions, and parameter sweeps.

---

### Need Help?

If results look suspicious, inspect `results/metadata.json` and the log output for diagnostics (e.g., `ell_over_dx_min`, chosen `Δt`). Adjust layer resolution or time-step settings accordingly.
