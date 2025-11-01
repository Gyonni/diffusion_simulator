"""Benchmark script to measure Phase 1 performance improvements."""

import time
import numpy as np

from diffreact_gui.models import LayerParam, SimParams
from diffreact_gui.solver import run_simulation, run_temperature_sweep


def benchmark_single_simulation(n_runs=5):
    """Benchmark a single simulation."""
    params = SimParams(
        layers=[
            LayerParam(name="Layer1", thickness=1e-6, diffusivity=1e-14, reaction_rate=0.0, nodes=200)
        ],
        Cs=1.0,
        dt=1e-3,
        t_max=0.5,
        bc_right="Neumann",
    )

    times = []
    for _ in range(n_runs):
        start = time.perf_counter()
        run_simulation(params)
        elapsed = time.perf_counter() - start
        times.append(elapsed)

    mean_time = np.mean(times)
    std_time = np.std(times)
    print(f"Single simulation: {mean_time:.4f} ± {std_time:.4f} seconds")
    return mean_time


def benchmark_temperature_sweep(n_runs=3):
    """Benchmark temperature sweep (sequential, not yet parallelized)."""
    D0 = 1e-10
    Ea = 0.5
    temps = [300.0, 350.0, 400.0, 450.0, 500.0]

    params = SimParams(
        layers=[
            LayerParam(
                name="Layer1",
                thickness=1e-6,
                diffusivity=None,
                D0=D0,
                Ea=Ea,
                reaction_rate=0.0,
                nodes=200,
            )
        ],
        Cs=1.0,
        dt=1e-3,
        t_max=0.1,
        bc_right="Neumann",
        temperatures=temps,
    )

    times = []
    for _ in range(n_runs):
        start = time.perf_counter()
        run_temperature_sweep(params)
        elapsed = time.perf_counter() - start
        times.append(elapsed)

    mean_time = np.mean(times)
    std_time = np.std(times)
    print(f"Temperature sweep (5 temps): {mean_time:.4f} ± {std_time:.4f} seconds")
    return mean_time


if __name__ == "__main__":
    print("=" * 60)
    print("Phase 1 Performance Benchmark")
    print("=" * 60)
    print()

    print("Test 1: Single Simulation")
    print("-" * 60)
    single_time = benchmark_single_simulation(n_runs=5)
    print()

    print("Test 2: Temperature Sweep (Sequential)")
    print("-" * 60)
    sweep_time = benchmark_temperature_sweep(n_runs=3)
    print()

    print("=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"Single simulation: {single_time:.4f} seconds")
    print(f"Temperature sweep: {sweep_time:.4f} seconds")
    print(f"Average per temperature: {sweep_time / 5:.4f} seconds")
    print()
    print("Note: Phase 1 optimizations (vectorization) complete.")
    print("      Phase 2 (parallelization) will further speed up temperature sweep.")
