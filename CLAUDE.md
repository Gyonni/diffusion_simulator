# CLAUDE.md - Development Reference Guide

**Last Updated**: 2025-11-02
**Purpose**: Essential reference for all development work on DiffReact GUI Simulator

---

## 1. PROJECT OVERVIEW

**What This Is**: A multilayer 1D diffusion-reaction simulator with interactive Tkinter GUI for modeling transient transport through layered materials.

**Core Equation**:
```
∂C/∂t = ∂/∂x(D(x)·∂C/∂x) - k(x)·C
```

**Primary Use Cases**:
- Semiconductor diffusion barriers
- Multilayer coating analysis
- Material absorption studies
- Temperature-dependent simulations (Arrhenius: D = D₀·exp(-Eₐ/(kb·T)))

**Key Features**: Multilayer stacks, temperature sweeps, real-time visualization, material library, comprehensive export (NPZ/CSV/Excel)

---

## 2. CORE ARCHITECTURE (6 Modules)

| Module | Responsibility | Key Functions/Classes |
|--------|----------------|----------------------|
| **solver.py** | Numerical engine (Crank-Nicolson) | `run_simulation()`, `run_temperature_sweep()`, Thomas algorithm |
| **physics.py** | Physical models & analytical solutions | `arrhenius_D()`, `characteristic_length()`, `steady_state_flux()` |
| **gui_elements.py** | Tkinter UI components | `App`, `LayerTable`, `MaterialLibraryDialog` |
| **plots.py** | Matplotlib visualization | `update_flux_axes()`, `update_profile_axes()`, `update_temp_axes()` |
| **models.py** | Data structures | `LayerParam`, `SimParams` |
| **utils.py** | Validation, I/O, utilities | `validate_params()`, `save_*()`, `load_material_library()` |

**Data Flow**:
```
User Input → gui_elements.App
          → utils.validate_params()
          → solver.run_simulation() / run_temperature_sweep()
          → plots.update_*_axes()
          → utils.save_*()
```

**Dependencies**:
- Core: `numpy`, `matplotlib`, `tkinter` (built-in)
- Export: `openpyxl` (Excel temperature sweep)
- Dev: `pytest`, `black`, `flake8`, `mypy`, `pyinstaller`

---

## 3. CRITICAL TECHNICAL CONSTRAINTS

### Numerical Model
- **Scheme**: Crank-Nicolson (unconditionally stable, requires spatial resolution)
- **Stability**: Auto dt capping based on `min((Δx)²/D)`, up to 6 halvings on failure
- **Grid**: Non-uniform concatenated layers, shared interface nodes
- **Interface Handling**: Harmonic averaging for D(x)
- **Mass Balance Tolerance**: `|R|/max(|ΔM|, 10⁻¹²) < 1%`

### Resolution Guidelines
- Passive layers (k=0): 2-4 nodes sufficient
- Reactive target layer: `ell_over_dx_min > 10` recommended
- Characteristic length: `ℓ = √(D_target/k_target)`

### Temperature Sweep Requirements (CRITICAL)
1. All layers **MUST** have D₀ and Eₐ values
2. Temperature list must be non-empty and positive
3. Common dt calculated across ALL temperatures (Phase 9 fix)
4. Stability: `dt = min(STABILITY_FACTOR * dx² / D)` across all temps

### Return Dictionary Keys (AVOID KeyError!)
```python
# CORRECT keys from solver functions:
result = {
    "t": time_array,        # NOT "time"!
    "J_end": exit_flux,     # NOT "J_exit"!
    "C": concentration,
    "x": grid_positions,
    # ... (document all keys in docstrings)
}
```

### Boundary Conditions
- **Left (x=0)**: Dirichlet `C_s` (fixed concentration)
- **Right (x=L)**: Dirichlet `C=0` (perfect sink) OR Neumann `∂C/∂x=0` (impermeable)

### Performance Notes (Phase 11)
- Vectorization: 5-15% overall speedup
- Parallel temperature sweep: Sequential faster for typical problems (overhead 1-3s)
- Auto-detection: Parallel when `n_temps ≥ 10` OR `estimated_time > 2.0s`
- Windows process spawn overhead significant

---

## 4. DEVELOPMENT RULES (MANDATORY)

### 🚨 NON-NEGOTIABLE PRINCIPLES

#### A. User Confirmation Required BEFORE:
- [ ] Architectural changes
- [ ] Adding/removing dependencies
- [ ] UI/UX modifications
- [ ] Changing file formats or APIs
- [ ] When multiple valid approaches exist → Present options

#### B. Testing Requirements (MUST PASS BEFORE DELIVERY):
```bash
# 1. Manual testing
python -m diffreact_gui  # Verify feature works

# 2. Edge case testing
# - Empty inputs
# - Boundary values (zero, negative, very large)
# - Invalid data types
# - Check console for errors

# 3. Automated tests
python run_tests.py  # ALL tests must pass
```

#### C. Documentation Updates (AFTER EVERY CHANGE):
- [ ] **IMPLEMENTATION_STATUS.md**: Add feature with phase/date/notes
- [ ] **PROJECT_STRUCTURE.md**: Update if files/modules/dependencies changed
- [ ] **docs/USER_MANUAL.md**: Update if user-facing features changed
- [ ] **Code docstrings**: Update function signatures and behavior

#### D. Code Quality Standards:
1. **Modularity**: Single responsibility, <50 lines per function
2. **Efficiency**: NumPy vectorization, profile critical paths
3. **Readability**: Descriptive names, type hints, docstrings
4. **Maintainability**: Named constants, minimize global state

---

## 5. CODING STANDARDS

### Naming Conventions
```python
# Modules
solver.py, gui_elements.py  # snake_case

# Classes
class LayerParam:           # PascalCase
class MaterialLibraryDialog:

# Functions
def run_simulation():       # snake_case
def _build_matrix():        # _private with underscore

# Constants
STABILITY_FACTOR = 0.45     # UPPER_SNAKE_CASE
KB_EV = 8.617333262e-5

# Variables
layer_params = []           # snake_case
```

### Type Hints (REQUIRED)
```python
def run_simulation(
    layers: List[LayerParam],
    sim_params: SimParams,
    abort_flag: Optional[threading.Event] = None
) -> Dict[str, np.ndarray]:
    """
    Run diffusion-reaction simulation.

    Args:
        layers: List of layer parameters
        sim_params: Global simulation parameters
        abort_flag: Optional event for early termination

    Returns:
        Dictionary with keys: 't', 'C', 'x', 'J_end', 'M_absorbed'
    """
    pass
```

### Docstring Style (Google or NumPy)
- All public functions/classes must have docstrings
- Include: Brief description, Args, Returns, Raises (if applicable)
- Document return dictionary structure explicitly

### PEP 8 Compliance
- 4 spaces indentation (no tabs)
- 79-character line limit (99 acceptable for readability)
- 2 blank lines between top-level definitions
- Run: `black .` and `flake8` before committing

---

## 6. COMMON PITFALLS (Learn from History)

### Bug Categories Fixed in Development

#### 1. KeyError Issues (Phases 1-2)
```python
# WRONG
time_data = result["time"]      # KeyError!
flux_data = result["J_exit"]    # KeyError!

# CORRECT
time_data = result["t"]
flux_data = result["J_end"]
```
**Lesson**: Always check return dict keys match usage. Document in docstrings.

#### 2. Memory Errors (Phases 6-7)
```python
# WRONG: Missing temperature validation
if mode == "arrhenius" and not temperatures:
    # Crashes with MemoryError!

# CORRECT: Validate early
if mode == "arrhenius":
    if not temperatures or any(T <= 0 for T in temperatures):
        raise ValueError("Arrhenius mode requires positive temperatures")
```
**Lesson**: Validate inputs at entry points before heavy computation.

#### 3. Array Shape Mismatches (Phase 9)
```python
# WRONG: Different dt per temperature
for T in temps:
    dt = calculate_dt_for_this_temp(T)  # Inconsistent!

# CORRECT: Common dt across all temps
dt = min(calculate_dt(T) for T in temps)
for T in temps:
    run_with_fixed_dt(dt)  # Consistent array shapes
```
**Lesson**: Temperature sweeps need consistent time grids.

#### 4. Column Mapping (Phase 8)
```python
# WRONG: Hardcoded column indices
value = row[3]  # Breaks when columns reordered!

# CORRECT: Use column name mapping
col_idx = self.column_map["D0"]
value = row[col_idx]
```
**Lesson**: Use named indices, not magic numbers.

---

## 7. PRE-DELIVERY CHECKLIST

### Before Submitting ANY Code:

#### Code Review
- [ ] Follows all development principles (Section 4)
- [ ] Manually tested and works (run the app!)
- [ ] All automated tests pass (`python run_tests.py`)
- [ ] New tests added for new features/bug fixes
- [ ] No debug `print()` statements left behind
- [ ] Error handling is robust (try/except with specific exceptions)
- [ ] Performance is acceptable (profile if critical path)

#### Documentation
- [ ] IMPLEMENTATION_STATUS.md updated with feature details
- [ ] PROJECT_STRUCTURE.md updated if architecture changed
- [ ] USER_MANUAL.md updated if user-facing changes
- [ ] All function docstrings accurate and complete
- [ ] Type hints on all function signatures

#### User Communication
- [ ] User confirmation obtained for significant changes
- [ ] Ambiguities clarified before implementation
- [ ] Options presented when multiple approaches valid

---

## 8. DECISION FRAMEWORK

### When to Ask User (Always Confirm First)
1. Multiple valid implementation approaches exist
2. UI/UX changes that affect user workflow
3. Performance vs. readability tradeoffs
4. Adding external dependencies
5. Changing file formats or breaking changes
6. Requirements are ambiguous or underspecified

### Debugging Workflow
```
1. Reproduce error reliably
   └─> Get exact steps to trigger bug

2. Read FULL traceback
   └─> Exact line, file, context

3. Understand ROOT CAUSE (not symptoms)
   └─> Why did it fail? What assumption broke?

4. Verify return values
   └─> Print/log dict keys, array shapes, types

5. Implement minimal fix
   └─> Change only what's necessary

6. Test the fix
   └─> Original case + edge cases

7. Add regression test
   └─> Prevent future breakage
```

### Performance Optimization Workflow
```
1. Profile first (don't guess)
   └─> Use cProfile, line_profiler, memory_profiler

2. Identify bottlenecks
   └─> Where is 80% of time spent?

3. Optimize hot paths only
   └─> Frequent code, inner loops

4. Measure impact
   └─> Benchmark before/after

5. Maintain readability
   └─> Clarity > minor gains

6. Document tradeoffs
   └─> Why this approach? What's the cost?
```

---

## 9. QUICK REFERENCE TABLES

### File Locations
```
diffreact_gui/
├── solver.py           # Numerical engine
├── physics.py          # Analytical models
├── gui_elements.py     # UI components
├── plots.py            # Visualization
├── models.py           # Data structures
├── utils.py            # Validation, I/O
└── config.py           # Constants, defaults

tests/
└── test_solver.py      # Unit/integration tests

docs/
├── USER_MANUAL.md      # English manual
└── USER_MANUAL_KO.md   # Korean manual

Root docs:
├── README.md                    # Overview, install, usage
├── DEVELOPMENT_GUIDELINES.md    # MANDATORY reference
├── IMPLEMENTATION_STATUS.md     # Feature history
├── PROJECT_STRUCTURE.md         # Architecture
└── CLAUDE.md                    # This file
```

### Physical Constants
```python
KB_EV = 8.617333262e-5  # eV/K (Boltzmann constant)
STABILITY_FACTOR = 0.45  # Crank-Nicolson dt scaling
```

### GUI Layout (Phase 10)
```
┌─────────────────────────────────────────────────┐
│ ▶ Run  ■ Stop  💾 Save  [Progress Bar]         │
├──────────────┬──────────────────────────────────┤
│ Setup Tab    │                                  │
│ ├─ Layers    │      3 Matplotlib Plots          │
│ ├─ Params    │      (9x7 size)                  │
│ └─ Material  │      ├─ Flux/Uptake vs Time      │
│              │      ├─ Concentration Profile     │
│ Results Tab  │      └─ Temp vs Concentration    │
│ ├─ Flux Probe│                                  │
│ ├─ Temp Sel. │      Time Slider / Controls      │
│ └─ Temp Plot │                                  │
└──────────────┴──────────────────────────────────┘
     550px               Resizable PanedWindow
```

### Output Files
- Single sim: `results.npz`, `flux_vs_time.csv`, `concentration_profiles.csv`, `metadata.json`
- Temp sweep: `results_temperature_sweep.npz`, `results_temperature_sweep.xlsx`
- Material lib: `materials_library.json`

---

## 10. GIT WORKFLOW

### Commit Message Format
```
<type>: <subject>

Types: feat, fix, refactor, docs, test, style, perf
```

Examples:
```
feat: add temperature sweep parallel mode
fix: correct KeyError in solver return dict
docs: update IMPLEMENTATION_STATUS with Phase 11
refactor: extract validation logic to utils
test: add edge case tests for negative diffusivity
perf: vectorize Arrhenius calculation
```

### Branch Strategy
- `main` - Stable production code
- `dev` - Development integration
- `feature/*` - New features
- `bugfix/*` - Bug fixes

### Rules
- Commit only working code
- Run tests before pushing
- Keep commits atomic (one logical change)

---

## 11. WORLD-CLASS DEVELOPER PRINCIPLES

### Core Philosophy
1. **Clarity over Cleverness** - Readable code > "clever" tricks
2. **Fail Fast** - Validate early, provide clear error messages
3. **DRY but Pragmatic** - Don't repeat yourself, but avoid premature abstraction
4. **Test the Unhappy Path** - Edge cases, invalid inputs, error conditions
5. **Document Decisions** - Why, not just what (especially non-obvious choices)
6. **Optimize for Change** - Code will be modified; make it easy

### Process Discipline
- **Plan before coding** - Understand requirements fully
- **Test continuously** - Don't wait until "done"
- **Refactor ruthlessly** - Improve structure as you learn
- **Review your own code** - Read before submitting
- **Learn from history** - Study past bugs (Section 6)

### Communication
- **Ask when uncertain** - Better than wrong assumptions
- **Explain tradeoffs** - Pros/cons of each approach
- **Be specific** - "The validation in utils.py line 142" not "the validation"
- **Document intent** - Comments explain WHY, not WHAT

---

## 12. IMPLEMENTATION STATUS SNAPSHOT

**Total Features**: 43 across 11 phases (as of 2025-11-02)
**Current State**: All features complete, no known issues

**Recent Major Changes**:
- Phase 11: Performance optimization (vectorization, parallel sweep auto-detection)
- Phase 10: Tab structure, Excel export, unified save button
- Phase 9: Temperature sweep array shape consistency fix
- Phases 6-7: Memory error fixes, temperature validation

**See IMPLEMENTATION_STATUS.md for complete history**

---

## 13. ADDITIONAL RESOURCES

### For Detailed Information, See:
- **DEVELOPMENT_GUIDELINES.md** - Complete development rules and processes
- **PROJECT_STRUCTURE.md** - Detailed architecture and diagrams
- **IMPLEMENTATION_STATUS.md** - Full feature development history
- **docs/USER_MANUAL.md** - User-facing functionality documentation
- **README.md** - Installation, quick start, basic usage

### External References:
- Crank-Nicolson method: Numerical analysis textbooks
- Arrhenius equation: Physical chemistry references
- Thomas algorithm: Tridiagonal matrix solver documentation

---

## FINAL REMINDER

**BEFORE ANY DEVELOPMENT WORK**:
1. Read the user request carefully
2. Check if confirmation needed (Section 8)
3. Understand which modules affected (Section 2)
4. Review relevant constraints (Section 3)
5. Plan the change (modularity, testing)
6. Implement following standards (Sections 4-5)
7. Test thoroughly (Section 7)
8. Update documentation (Section 4C)
9. Review against checklist (Section 7)
10. Deliver with confidence

**YOU ARE A WORLD-CLASS DEVELOPER**. Follow these guidelines, maintain high standards, and always prioritize code quality, user experience, and maintainability.

---

*End of CLAUDE.md*
