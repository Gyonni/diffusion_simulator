# Development Guidelines – Diffusion–Reaction GUI Simulator

**Mandatory Reference Document for All Code Modifications**

This document establishes the fundamental development principles, workflows, and standards that **must** be followed for all code changes, improvements, and testing in this project.

---

## Core Development Principles

### 1. User Confirmation Required
- **Always ask the user for confirmation** before making decisions that affect:
  - Architecture or design patterns
  - Major algorithm changes
  - UI/UX modifications beyond explicit requests
  - Dependency additions or version changes
  - File structure reorganization
- When implementing requested features, clarify ambiguous requirements before proceeding
- If multiple valid approaches exist, present options and ask for user preference

### 2. Code Quality Standards

#### Modularity
- Each function/method should have a single, well-defined responsibility
- Keep functions under 50 lines when possible; refactor complex logic into helper functions
- Use clear module boundaries: `gui_elements.py`, `solver.py`, `physics.py`, `plots.py`, `models.py`, `utils.py`
- Avoid tight coupling; use dependency injection and clear interfaces

#### Efficiency
- Profile performance-critical code (e.g., Crank-Nicolson solver loops)
- Use NumPy vectorization instead of Python loops for numerical operations
- Cache expensive computations when appropriate
- Document time complexity for algorithms

#### Readability
- Use descriptive variable names: `layer_thickness` not `lt`, `diffusivity` not `d`
- Add docstrings to all public functions/classes (Google style preferred)
- Include inline comments for non-obvious logic
- Use type hints for function signatures
- Follow PEP 8 style guide (4 spaces, 79-character lines for code, 72 for docstrings)

#### Maintainability
- Avoid magic numbers; use named constants: `DEFAULT_CANVAS_WIDTH = 450`
- Keep related code together; separate concerns into different modules
- Use meaningful class and function names that describe behavior
- Minimize global state; prefer passing parameters explicitly

### 3. Documentation Requirements

**MANDATORY: Update all relevant documentation after every code change**

#### Implementation Status
- Update [`IMPLEMENTATION_STATUS.md`](IMPLEMENTATION_STATUS.md) after completing any feature
- Document new features, bug fixes, and improvements
- Include version/date information
- Mark tasks as completed with implementation notes

#### Project Structure
- Update [`PROJECT_STRUCTURE.md`](PROJECT_STRUCTURE.md) when adding new files, modules, or reorganizing code
- Document new directories or significant file changes
- Update module dependency diagrams
- Keep file descriptions current with actual implementation

#### User-Facing Documentation
- Update [`docs/USER_MANUAL.md`](docs/USER_MANUAL.md) and [`docs/USER_MANUAL_KO.md`](docs/USER_MANUAL_KO.md) for user-visible features
- Document new GUI elements, input parameters, or analysis tools
- Add usage examples where appropriate
- Update troubleshooting section for common issues

#### Code Documentation
- Update docstrings when function signatures or behavior changes
- Keep README.md current with installation and usage instructions
- Document any breaking changes or migration steps

### 4. Testing Requirements

**MANDATORY: Test all code changes before delivery**

#### Before Providing Code to User
1. **Run the application** and verify the feature works as expected
2. **Test edge cases** (empty inputs, boundary values, invalid data)
3. **Check for errors** in console output
4. **Verify UI behavior** (for GUI changes)
5. **Run the full test suite**: `python run_tests.py`

#### Updating Test Suite
- **Add new tests** for every new feature or bug fix
- Update existing tests if behavior changes
- Ensure test coverage for:
  - Core physics/solver functions
  - Input validation
  - Error handling
  - Edge cases
- Tests should be in `tests/` directory
- Use descriptive test names: `test_temperature_sweep_with_arrhenius_params()`

#### Test Execution
```bash
# Always run before committing changes
python run_tests.py

# Or with pytest (if available)
pytest -q
```

- All tests must pass before code is provided to user
- If tests fail, fix the issue or update tests appropriately
- Document test failures and resolutions in commit messages

---

## World-Class Development Workflows

### Version Control (Git)
 
 o layer table", "fix: Resolve KeyError in temperature sweep")
- Types: `feat`, `fix`, `refactor`, `docs`, `test`, `style`, `perf`
- Commit working code only; never commit broken code

#### Branches
- Use feature branches for significant changes
- Main branch should always be stable
- Branch naming: `feature/<name>`, `fix/<issue>`, `refactor/<component>`

### Code Review Checklist

Before finalizing any code change, verify:

- [ ] Code follows all principles in this document
- [ ] Functionality tested manually and works as expected
- [ ] All tests pass (`python run_tests.py`)
- [ ] New tests added for new features/fixes
- [ ] Documentation updated (IMPLEMENTATION_STATUS.md, docs/manual.md)
- [ ] Code is readable and well-commented
- [ ] No unnecessary debug print statements
- [ ] Error handling is robust and user-friendly
- [ ] Performance is acceptable (no obvious bottlenecks)
- [ ] User confirmation obtained for any decisions

### Debugging Process

1. **Reproduce the error** reliably
2. **Read the full traceback** – identify exact line and context
3. **Understand root cause** – don't just fix symptoms
4. **Check return values** – verify function outputs match expectations (e.g., "t" vs "time", "J_end" vs "J_exit")
5. **Test the fix** – ensure error doesn't reoccur
6. **Add regression test** – prevent future breakage

### Performance Optimization

1. **Profile first** – identify actual bottlenecks, don't guess
2. **Measure impact** – benchmark before and after changes
3. **Optimize hot paths** – focus on code that runs frequently
4. **Maintain readability** – don't sacrifice clarity for minor gains
5. **Document tradeoffs** – explain optimization decisions

---

## Project-Specific Guidelines

### Diffusion-Reaction Simulator

#### Numerical Accuracy
- Crank-Nicolson scheme requires careful handling of time steps
- Automatically cap `Δt` based on smallest `(Δx)²/D` to prevent oscillations
- Enforce mass balance: warn if `|R| / max(|ΔM|, 10⁻¹²)` > 1%
- Test against analytical solutions when possible

#### GUI Design Principles
- Keep parameter panel resizable for user flexibility
- Fix critical controls (Run/Stop buttons) at top
- Provide progress feedback for long-running simulations
- Make error messages detailed, copyable, and actionable
- Use meaningful symbols (▶ Run, ■ Stop) for clarity

#### Input Validation
- Check all physical constraints before simulation
- Provide clear error messages with specific issues
- Validate layer parameters (positive thickness, non-negative D and k)
- Verify temperature values are physically meaningful (> 0 K)
- Ensure node counts are reasonable (2+ nodes per layer)

#### Return Value Conventions
Always use consistent key names in result dictionaries:
- Time array: `"t"` (NOT "time")
- Exit flux: `"J_end"` (NOT "J_exit")
- Document return dictionary structure in function docstrings

#### Material Properties
- Support both direct diffusivity input and Arrhenius parameters (D₀, Eₐ)
- Display activation energy (Eₐ) in layer table for verification
- Ensure temperature-dependent calculations use correct units (eV for Eₐ)

#### Testing Strategy
- Unit tests for individual physics functions
- Integration tests for full simulation pipeline
- Validation against known analytical solutions
- Edge case testing (single layer, zero diffusivity, etc.)
- GUI smoke tests (launch, input, run, close)

---

## Continuous Improvement

### Regular Reviews
- Periodically review this document and update as project evolves
- Incorporate lessons learned from bugs and issues
- Refine guidelines based on team feedback

### Knowledge Sharing
- Document complex algorithms and design decisions
- Maintain clear inline comments for tricky code sections
- Update manual with usage tips and best practices

### Technical Debt
- Track known issues and TODOs in IMPLEMENTATION_STATUS.md
- Prioritize refactoring high-value components
- Balance new features with code quality improvements

---

## Quick Reference Checklist

**Before Every Code Change:**
- [ ] Understand user requirement clearly
- [ ] Ask for confirmation if any ambiguity exists
- [ ] Plan approach (consider alternatives if applicable)

**During Implementation:**
- [ ] Write modular, efficient, readable code
- [ ] Add type hints and docstrings
- [ ] Follow naming conventions and style guide
- [ ] Handle errors gracefully with informative messages

**After Implementation:**
- [ ] Test manually – verify feature works
- [ ] Run test suite – `python run_tests.py`
- [ ] Add/update tests for new functionality
- [ ] Update IMPLEMENTATION_STATUS.md
- [ ] Update docs/manual.md (if user-facing change)
- [ ] Review code against this checklist

**Before Delivery:**
- [ ] All tests pass
- [ ] Documentation complete
- [ ] No known errors or warnings
- [ ] Code reviewed against quality standards

---

*This document is a living guideline. When in doubt, prioritize user needs, code quality, and thorough testing.*
