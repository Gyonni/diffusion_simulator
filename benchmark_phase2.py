"""Benchmark script to measure Phase 2 (parallel) performance improvements."""

import time
import numpy as np
from multiprocessing import cpu_count

from diffreact_gui.models import LayerParam, SimParams
from diffreact_gui.solver import run_temperature_sweep


def benchmark_parallel_vs_sequential(n_runs=3):
    """Compare parallel vs sequential temperature sweep."""
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

    print(f"Number of temperatures: {len(temps)}")
    print(f"Available CPU cores: {cpu_count()}")
    print()

    # Sequential benchmark
    print("Running SEQUENTIAL benchmarks...")
    sequential_times = []
    for run in range(n_runs):
        start = time.perf_counter()
        result = run_temperature_sweep(params, use_parallel=False)
        elapsed = time.perf_counter() - start
        sequential_times.append(elapsed)
        print(f"  Run {run+1}/{n_runs}: {elapsed:.4f}s")

    seq_mean = np.mean(sequential_times)
    seq_std = np.std(sequential_times)
    print(f"Sequential: {seq_mean:.4f} ± {seq_std:.4f} seconds")
    print()

    # Parallel benchmark
    print("Running PARALLEL benchmarks...")
    parallel_times = []
    for run in range(n_runs):
        start = time.perf_counter()
        result = run_temperature_sweep(params, use_parallel=True)
        elapsed = time.perf_counter() - start
        parallel_times.append(elapsed)
        print(f"  Run {run+1}/{n_runs}: {elapsed:.4f}s")

    par_mean = np.mean(parallel_times)
    par_std = np.std(parallel_times)
    print(f"Parallel: {par_mean:.4f} ± {par_std:.4f} seconds")
    print()

    # Calculate speedup
    speedup = seq_mean / par_mean
    print("=" * 60)
    print(f"SPEEDUP: {speedup:.2f}x")
    print(f"Time saved: {seq_mean - par_mean:.4f}s ({(1 - par_mean/seq_mean)*100:.1f}% faster)")
    print("=" * 60)

    return seq_mean, par_mean, speedup


if __name__ == "__main__":
    print("=" * 60)
    print("Phase 2 Performance Benchmark: Parallel vs Sequential")
    print("=" * 60)
    print()

    seq_time, par_time, speedup = benchmark_parallel_vs_sequential(n_runs=3)

    print()
    print("Summary:")
    print("-" * 60)
    print(f"Sequential execution: {seq_time:.4f}s")
    print(f"Parallel execution:   {par_time:.4f}s")
    print(f"Speedup:              {speedup:.2f}x")
    print()
    print("Note: Phase 1 + 2 optimizations complete!")
    print("      Vectorization + Parallelization = massive speedup")
