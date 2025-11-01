# Diffusion–Reaction GUI Simulator

Multilayer 1D diffusion–reaction simulator with a Tkinter GUI and Crank–Nicolson time integration. Each layer may have unique thickness, diffusivity, and reaction rate; the final layer acts as the absorbing/ reactive target and reports flux and cumulative uptake over time.

## Requirements

- Python 3.10+
- Packages: `numpy`, `matplotlib` (Tkinter ships with CPython)

### Quick Install

```bash
# Using requirements.txt (recommended)
pip install -r requirements.txt

# Or install manually
pip install numpy matplotlib
```

### Development Setup (Virtual Environment Recommended)

1. **Create virtual environment**:
   ```bash
   python -m venv venv
   ```

2. **Activate environment**:
   ```bash
   # Windows PowerShell
   .\venv\Scripts\Activate.ps1

   # Windows CMD
   venv\Scripts\activate.bat

   # Linux/macOS
   source venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   # For users (minimal)
   pip install -r requirements.txt

   # For developers (includes testing/build tools)
   pip install -r requirements-dev.txt
   ```

4. **Verify installation**:
   ```bash
   python -c "import numpy; import matplotlib; print('All packages installed')"
   ```

## Running the simulator

- GUI: `python -m diffreact_gui`
- CLI mode: `python -m diffreact_gui.main --cli [--debug]`
- PyInstaller entry point: `python run_diffreact_gui.py`

Outputs land in `results/` by default (`results.npz`, `flux_vs_time.csv`, `concentration_profiles.csv`, `profile_t_<t>.csv`, `metadata.json`).

## GUI features

### Core Features
- **Multi-layer stack**: Layer table for per-layer parameters (top → bottom); the last row is the target layer
- **Progress tracking**: Run/Abort buttons at top with progress bar; abort simulation anytime
- **Built-in manual**: "View Manual" window summarizes governing equations, usage, and input constraints
- **Time navigation**: Slider, spin box, and step buttons beneath profile plot
- **Input validation**: Checks physical constraints before every run with actionable error dialogs

### Material Properties
- **Dual input modes**: Toggle between direct diffusivity (D) or Arrhenius parameters (D₀, Ea)
- **Material library**: Save and load material properties to/from persistent library
- **Temperature sweep**: Enter comma-separated temperature list (e.g., "300, 350, 400, 450") for multi-temperature simulations

### Analysis Tools
- **Flux probe**: Inspect flux/cumulative uptake at arbitrary position or layer center
- **Flux view selector**: Focus on surface, interface, exit, or probe flux/uptake curves individually
- **Mass/uptake metrics**: Reported for the final (target) layer

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

### Building a standalone executable

**Prerequisites**: Virtual environment with PyInstaller installed (included in `requirements-dev.txt`).

1. **Activate virtual environment** (if not already active):
   ```bash
   venv\Scripts\activate  # Windows
   source venv/bin/activate  # Linux/macOS
   ```

2. **Clean previous builds** (optional):
   ```bash
   python -c "import shutil; shutil.rmtree('build', ignore_errors=True); shutil.rmtree('dist', ignore_errors=True)"
   ```

3. **Build executable**:
   ```bash
   python -m PyInstaller --onefile --noconsole --name DiffReactGUI run_diffreact_gui.py
   ```

4. **Output**: `dist/DiffReactGUI.exe` (~40 MB)

**Important**: Always use `python -m PyInstaller` (not `pyinstaller` directly) to avoid path issues.

### Common Issues

| Issue | Solution |
|-------|----------|
| "No Python at ..." error | Ensure virtual environment is active; use `python -m PyInstaller` |
| "Unable to create process" | Reinstall PyInstaller: `pip uninstall -y pyinstaller && pip install pyinstaller` |
| Module not found | Clean build dirs and rebuild |
| PowerShell execution policy | Run `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser` |
