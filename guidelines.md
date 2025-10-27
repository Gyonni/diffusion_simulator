# AI Coding Context Specification for Diffusion–Reaction GUI Simulator

## 1. Project Overview
This project defines a **GUI-based 1D Diffusion–Reaction Simulator** designed for scientific and engineering use, especially in semiconductor or materials diffusion analysis. The simulation numerically solves the **time-dependent diffusion–reaction equation** using a **Crank–Nicolson implicit scheme** and visualizes results through an interactive Tkinter interface.

The resulting software must be:
- **Executable without IDE** (convertible to `.exe` via PyInstaller)
- **Modular and maintainable** (each subsystem separated)
- **Numerically stable and efficient** (Crank–Nicolson with well-defined boundary handling)
- **Graphically interactive** (time & spatial plots, adjustable parameters)

---

## 2. Purpose
To allow non-programmers (e.g., material scientists, engineers) to:
- Input physical parameters (D, k, L, Cs, dt, t_max, etc.)
- Select boundary conditions (Neumann or Dirichlet)
- Observe concentration evolution both in space and time
- Inspect fluxes and cumulative absorbed gas quantities graphically

This tool supports **visual, quantitative, and pedagogical exploration** of diffusion–reaction phenomena in solid-state or thin-film systems.

---

## 3. Functional Requirements

### 3.1. Core Equation
\[
\frac{\partial C}{\partial t} = D\frac{\partial^2 C}{\partial x^2} - kC
\]
where
- \( D \): diffusion coefficient (m²/s)
- \( k \): first-order reaction rate constant (1/s)
- \( L \): total film thickness (m)
- \( C_s \): constant surface concentration (mol/m³)

### 3.2. Boundary Conditions
- **Left (x = 0)**: Dirichlet \(C = C_s\)
- **Right (x = L)**: selectable
  - **Neumann (impermeable)**: \(\partial C / \partial x = 0\)
  - **Dirichlet (perfect sink)**: \(C = 0\)

### 3.3. Output Quantities
- Time evolution of left/right fluxes
  - \( J = -D(\partial C / \partial x) \)
- Spatial concentration profiles at selectable times
- Cumulative absorption (time integral of flux)

---

## 4. Program Architecture

### 4.1. File Layout
```
diffreact_gui/
├── main.py               # Entry point with Tkinter GUI
├── solver.py             # Numerical core (Crank–Nicolson implementation)
├── physics.py            # Flux, reaction, and analytical model helpers
├── plots.py              # Matplotlib figure and update logic
├── gui_elements.py       # Widget and layout logic
├── config.py             # Default parameters and constants
└── utils.py              # Validation, unit conversion, and debugging tools
```

### 4.2. Module Descriptions

| Module | Responsibility |
|---------|----------------|
| `solver.py` | Builds CN matrices, applies boundary conditions, and performs time integration. |
| `physics.py` | Provides analytical expressions for verification (steady-state, flux laws). |
| `plots.py` | Manages figure generation, line updates, and rescaling. |
| `gui_elements.py` | Handles Tkinter layout, input fields, buttons, and callbacks. |
| `config.py` | Defines default simulation parameters, e.g., `D_default = 1e-14`. |
| `utils.py` | Provides error handling, logging, and result export (CSV/PNG). |

---

## 5. Numerical Implementation Guidelines

### 5.1. Discretization
- **Scheme:** Crank–Nicolson (semi-implicit second order)
- **Grid:** 1D uniform, `nx` nodes between `[0, L]`
- **Matrix Form:**
  \[
  (I + rA + sI)C^{n+1} = (I - rA - sI)C^n + B_{BC}
  \]
  where `r = DΔt/(2Δx²)` and `s = kΔt/2`.

### 5.2. Stability
Crank–Nicolson is unconditionally stable for linear diffusion–reaction, but large Δt reduces accuracy. Recommend:
- `Δx ≤ L/200`
- `Δt ≤ 0.01 * L²/D`

### 5.3. Boundary Handling
- **Dirichlet:** Replace end-node concentration directly.
- **Neumann:** Mirror ghost-point (C_N = C_{N-2}) or modify last equation coefficients.

### 5.4. Validation
Compare steady-state flux with analytical solutions:
\[
J = \frac{D}{\ell}C_s \tanh\frac{L}{\ell}, \quad \ell = \sqrt{\frac{D}{k}}
\]

---

## 6. GUI Design Specifications

### 6.1. Input Section
| Field | Type | Default | Description |
|--------|------|----------|--------------|
| Diffusion coefficient (D) | Float | 1e-14 | m²/s |
| Reaction rate (k) | Float | 1e3 | 1/s |
| Length (L) | Float | 5e-7 | m |
| Surface concentration (Cs) | Float | 1.0 | mol/m³ |
| Time step (dt) | Float | 1e-3 | s |
| Total time (t_max) | Float | 0.5 | s |
| Spatial nodes (nx) | Int | 201 | – |
| Right BC | Dropdown | Neumann / Dirichlet | – |

### 6.2. Output Section
- Graph 1: Flux vs Time (J₀, J_L, cumulative curves)
- Graph 2: Concentration Profile (C(x,t))
- Interactive time selector (spinbox or slider)

---

## 7. Debugging and Testing Strategy

### 7.1. Unit Testing
Each module should include a `if __name__ == '__main__':` block or `pytest` tests verifying:
- **solver.py:** matrix symmetry, conservation for k=0, BC handling
- **physics.py:** steady-state analytical vs numerical flux (within tolerance)
- **plots.py:** matplotlib axes labeling and figure instance creation
- **utils.py:** input validation exceptions

### 7.2. Debug Logging
- Use Python’s `logging` module, not print statements.
- Levels: DEBUG (matrix dimensions, flux values), INFO (simulation start/end), ERROR (singular matrix).

### 7.3. Visualization Diagnostics
Provide an optional **debug plot mode** overlaying analytical vs numerical profiles for steady-state verification.

---

## 8. Packaging Instructions

### 8.1. PyInstaller Build
```bash
pip install pyinstaller
pyinstaller --onefile --noconsole --name DiffReactGUI main.py
```
Executable: `dist/DiffReactGUI.exe`

### 8.2. Requirements
```
numpy
matplotlib
tkinter (builtin)
```

### 8.3. File Structure for Distribution
```
DistReactGUI/
├── DiffReactGUI.exe
├── README.txt
├── LICENSE
├── examples/
│   ├── default_config.json
│   └── test_case_steady_state.csv
└── logs/
```

---

## 9. Extension Plan (Future Work)
- **Multi-layer diffusion** (spatially variable D, k)
- **Arrhenius temperature dependence**
- **Surface reaction (Robin BC)**
- **2D version using finite difference grid**
- **Automated parameter sweep / batch simulation mode**

---

## 10. AI-Coding Guidelines for GPT Codex or similar LLMs

### 10.1. General Goals
- Maintain **scientific fidelity** and **numerical correctness**.
- Ensure **human readability** and **debug traceability**.
- Generate **self-contained, executable** code.

### 10.2. Coding Standards
1. Use explicit imports (no wildcard `from ... import *`).
2. Use type hints (PEP 484) for all functions.
3. Encapsulate all numerical constants in `config.py`.
4. Separate GUI logic from numerical solvers.
5. Never hardcode file paths—use relative or user-selected directories.
6. Include minimal docstrings for every function with math and units.
7. Always provide a `main()` entry for manual CLI testing.

### 10.3. Debugging Support
- Add `--debug` flag in CLI version to dump intermediate `C(x,t)` arrays.
- Use `numpy.savez()` to export all results for inspection.
- Provide consistency check: ensure `∫J dt ≈ ∫kC dx dt` within 1% tolerance.

### 10.4. Performance Recommendations
- Precompute constant matrices (`A`, `B`) once.
- Prefer vectorized NumPy operations.
- Avoid reallocation in time loop (preallocate arrays).

### 10.5. Error Handling
- Validate physical realism: reject negative `D`, `k`, `L`, `dt`, or zero `nx`.
- Catch `LinAlgError` for singular matrices and reduce `dt` automatically.

### 10.6. GUI Responsiveness
- Run simulation in a background thread if step time >1s.
- Disable Run button during computation.
- Use `FigureCanvasTkAgg.draw_idle()` for efficient redraws.

---

## 11. Example Test Case (for Debugging)
| Parameter | Value |
|------------|-------|
| D | 1e-14 m²/s |
| k | 1e3 1/s |
| L | 5e-7 m |
| Cs | 1.0 mol/m³ |
| dt | 1e-3 s |
| t_max | 0.5 s |
| nx | 201 |
| BC | Neumann |

Expected behavior:
- \(C(x,t)\) increases near the surface and decays exponentially with x.
- Flux \(J_0(t)\) initially high, then stabilizes at \(C_s\sqrt{Dk}\).

---

## 12. Version Control and Collaboration
- Use Git for source management (`main`, `dev`, `feature/*`).
- Apply semantic commits (feat, fix, refactor, doc).
- Autoformat with `black` and lint with `flake8`.
- Include `.gitignore` for build and cache directories.

---

**End of Specification Document**

