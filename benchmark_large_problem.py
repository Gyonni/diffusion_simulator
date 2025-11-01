"""Benchmark with larger problem size where parallel execution shines."""

import time
import numpy as np
from multiprocessing import cpu_count

from diffreact_gui.models import LayerParam, SimParams
from diffreact_gui.solver import run_temperature_sweep


def benchmark_large_temperature_sweep():
    """Test with 10 temperatures and longer simulation time."""
    D0 = 1e-10
    Ea = 0.5
    temps = list(range(300, 550, 25))  # 10 temperatures

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
        t_max=0.5,  # Longer simulation
        bc_right="Neumann",
        temperatures=temps,
    )

    print(f"Number of temperatures: {len(temps)}")
    print(f"Temperatures: {temps}")
    print(f"Available CPU cores: {cpu_count()}")
    print(f"Simulation time: {params.t_max}s")
    print()

    # Sequential
    print("Running SEQUENTIAL...")
    start = time.perf_counter()
    result_seq = run_temperature_sweep(params, use_parallel=False)
    seq_time = time.perf_counter() - start
    print(f"Sequential: {seq_time:.4f}s")
    print()

    # Parallel
    print("Running PARALLEL...")
    start = time.perf_counter()
    result_par = run_temperature_sweep(params, use_parallel=True)
    par_time = time.perf_counter() - start
    print(f"Parallel: {par_time:.4f}s")
    print()

    # Speedup
    speedup = seq_time / par_time
    print("=" * 60)
    print(f"SPEEDUP: {speedup:.2f}x")
    print(f"Time saved: {seq_time - par_time:.4f}s ({(1 - par_time/seq_time)*100:.1f}% faster)")
    print("=" * 60)
    print()

    # Verify results are identical
    temp_to_check = temps[0]
    seq_flux = result_seq["results_by_temp"][temp_to_check]["J_source"]
    par_flux = result_par["results_by_temp"][temp_to_check]["J_source"]
    max_diff = np.max(np.abs(seq_flux - par_flux))
    print(f"Result verification: max difference = {max_diff:.3e}")
    if max_diff < 1e-10:
        print("✓ Results are identical!")
    else:
        print("✗ Results differ (may be due to interpolation differences)")


if __name__ == "__main__":
    print("=" * 60)
    print("Large Problem Benchmark: Where Parallel Shines")
    print("=" * 60)
    print()

    benchmark_large_temperature_sweep()
