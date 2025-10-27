"""Minimal test runner for environments without pytest.

Usage:
  python run_tests.py

Runs a subset of tests defined in tests/test_solver.py and exits with non-zero
status if any test fails.
"""
from __future__ import annotations

import sys
import traceback


def main() -> int:
    results = []
    try:
        import tests.test_solver as ts
    except Exception as e:
        traceback.print_exc()
        return 1

    def run_one(name, fn):
        try:
            fn()
            results.append((name, True, ""))
        except AssertionError as e:
            results.append((name, False, f"AssertionError: {e}"))
        except Exception:
            results.append((name, False, "".join(traceback.format_exc())))

    run_one("test_pure_diffusion_neumann_right", ts.test_pure_diffusion_neumann_right)
    run_one("test_steady_flux_neumann_analytical_match", ts.test_steady_flux_neumann_analytical_match)
    run_one("test_mass_balance_residual", ts.test_mass_balance_residual)

    ok = all(ok for _, ok, _ in results)
    for name, passed, info in results:
        status = "PASS" if passed else "FAIL"
        print(f"{status} - {name}")
        if not passed:
            print(info)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

