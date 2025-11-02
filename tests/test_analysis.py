"""
Unit tests for analysis module (doping analysis functionality).
"""

import numpy as np
import pytest

from diffreact_gui.analysis import (
    EPSILON_0,
    calculate_capacitance,
    calculate_dq,
    calculate_dq_grid,
    interpolate_simulation_data,
    prepare_plot_data,
)
from diffreact_gui.models import CapacitorParams, ExperimentalData


class TestCapacitorCalculations:
    """Test capacitor model calculations."""

    def test_calculate_capacitance(self):
        """Test capacitance calculation."""
        params = CapacitorParams(
            epsilon_r=3.9,  # SiO2
            A=1e-4,  # 1 cm^2
            d=1e-9,  # 1 nm
            V0=0.0
        )

        C = calculate_capacitance(params)

        # Expected: C = (8.854e-12 * 3.9 * 1e-4) / 1e-9 = 3.45e-5 F
        expected = (EPSILON_0 * 3.9 * 1e-4) / 1e-9
        assert np.isclose(C, expected)
        assert C > 0

    def test_calculate_dq(self):
        """Test charge change calculation."""
        params = CapacitorParams(
            epsilon_r=3.9,
            A=1e-4,
            d=1e-9,
            V0=1.0
        )

        # Test with voltage above V0
        dq = calculate_dq(2.0, params)
        C = calculate_capacitance(params)
        expected = C * (2.0 - 1.0)
        assert np.isclose(dq, expected)

        # Test with voltage below V0
        dq_neg = calculate_dq(0.5, params)
        expected_neg = C * (0.5 - 1.0)
        assert np.isclose(dq_neg, expected_neg)
        assert dq_neg < 0

        # Test with pre-calculated capacitance
        dq_with_C = calculate_dq(2.0, params, capacitance=C)
        assert np.isclose(dq, dq_with_C)

    def test_calculate_dq_grid(self):
        """Test charge change calculation for grid."""
        params = CapacitorParams(
            epsilon_r=3.9,
            A=1e-4,
            d=1e-9,
            V0=1.0
        )

        voltage_grid = np.array([
            [1.0, 1.5, 2.0],
            [1.2, 1.7, 2.2],
        ])

        dq_grid = calculate_dq_grid(voltage_grid, params)

        # Check shape
        assert dq_grid.shape == voltage_grid.shape

        # Check values
        C = calculate_capacitance(params)
        expected = C * (voltage_grid - 1.0)
        assert np.allclose(dq_grid, expected)

    def test_zero_voltage_difference(self):
        """Test dq calculation when V = V0."""
        params = CapacitorParams(
            epsilon_r=3.9,
            A=1e-4,
            d=1e-9,
            V0=2.5
        )

        dq = calculate_dq(2.5, params)
        assert dq == 0.0


class TestInterpolation:
    """Test simulation data interpolation."""

    def create_mock_temp_sweep_results(self):
        """Create mock temperature sweep results for testing."""
        temps = np.array([300.0, 350.0, 400.0])
        times = np.linspace(0, 1000, 11)  # 0, 100, 200, ..., 1000
        positions = np.linspace(0, 1e-6, 6)  # 0, 2e-7, 4e-7, ..., 1e-6

        # Create synthetic 3D concentration data
        # C increases with temperature, time, and decreases with position
        T_grid, t_grid, x_grid = np.meshgrid(temps, times, positions, indexing='ij')
        C_Txt = (T_grid / 300) * (t_grid / 1000) * (1 - x_grid / 1e-6) * 1e3

        # Flux data (2D, doesn't depend on position)
        T_grid_2d, t_grid_2d = np.meshgrid(temps, times, indexing='ij')
        J_surface_Tt = (T_grid_2d / 300) * (t_grid_2d / 1000) * 1e-6

        # Build results_by_temp
        results_by_temp = {}
        for i, T in enumerate(temps):
            results_by_temp[T] = {
                "cum_source": (T / 300) * (times / 1000) * 1e-3,
                "cum_end": (T / 300) * (times / 1000) * 0.5e-3,
                "cum_target": (T / 300) * (times / 1000) * 0.8e-3,
                "mass_target": (T / 300) * (times / 1000) * 2e-3,
            }

        return {
            "temperatures": temps,
            "t": times,
            "x": positions,
            "C_Txt": C_Txt,
            "J_surface_Tt": J_surface_Tt,
            "J_end_Tt": J_surface_Tt * 0.5,
            "J_target_Tt": J_surface_Tt * 0.8,
            "results_by_temp": results_by_temp,
        }

    def test_interpolate_concentration(self):
        """Test interpolation of concentration data."""
        results = self.create_mock_temp_sweep_results()

        # Test at grid points (should match exactly)
        target_temps = np.array([300.0, 350.0])
        target_times = np.array([500.0, 500.0])
        target_positions = np.array([5e-7, 5e-7])

        C_interp = interpolate_simulation_data(
            results,
            target_temps,
            target_times,
            target_positions,
            "C",
            is_temperature_sweep=True
        )

        # Manually calculate expected values
        # C = (T/300) * (t/1000) * (1 - x/1e-6) * 1e3
        expected = []
        for T, t, x in zip(target_temps, target_times, target_positions):
            C_expected = (T / 300) * (t / 1000) * (1 - x / 1e-6) * 1e3
            expected.append(C_expected)
        expected = np.array(expected)

        assert np.allclose(C_interp, expected, rtol=0.01)

    def test_interpolate_flux(self):
        """Test interpolation of flux data."""
        results = self.create_mock_temp_sweep_results()

        target_temps = np.array([325.0, 375.0])  # Mid-points
        target_times = np.array([250.0, 750.0])
        target_positions = np.array([0.0, 0.0])  # Position doesn't matter for flux

        J_interp = interpolate_simulation_data(
            results,
            target_temps,
            target_times,
            target_positions,
            "J_source",
            is_temperature_sweep=True
        )

        # Check reasonable values
        assert len(J_interp) == 2
        assert np.all(J_interp > 0)

    def test_interpolate_cumulative(self):
        """Test interpolation of cumulative data."""
        results = self.create_mock_temp_sweep_results()

        target_temps = np.array([300.0])
        target_times = np.array([500.0])
        target_positions = np.array([0.0])

        cum_interp = interpolate_simulation_data(
            results,
            target_temps,
            target_times,
            target_positions,
            "cum_source",
            is_temperature_sweep=True
        )

        # cum = (T/300) * (t/1000) * 1e-3
        expected = (300.0 / 300) * (500.0 / 1000) * 1e-3
        assert np.isclose(cum_interp[0], expected, rtol=0.01)

    def test_empty_input(self):
        """Test interpolation with empty arrays."""
        results = self.create_mock_temp_sweep_results()

        target_temps = np.array([])
        target_times = np.array([])
        target_positions = np.array([])

        result = interpolate_simulation_data(
            results,
            target_temps,
            target_times,
            target_positions,
            "C",
            is_temperature_sweep=True
        )

        assert len(result) == 0

    def test_mismatched_array_lengths(self):
        """Test error handling for mismatched array lengths."""
        results = self.create_mock_temp_sweep_results()

        target_temps = np.array([300.0, 350.0])
        target_times = np.array([500.0])  # Different length
        target_positions = np.array([5e-7, 5e-7])

        with pytest.raises(ValueError, match="same length"):
            interpolate_simulation_data(
                results,
                target_temps,
                target_times,
                target_positions,
                "C",
                is_temperature_sweep=True
            )

    def test_unknown_variable(self):
        """Test error handling for unknown variable."""
        results = self.create_mock_temp_sweep_results()

        target_temps = np.array([300.0])
        target_times = np.array([500.0])
        target_positions = np.array([5e-7])

        with pytest.raises(ValueError, match="Unknown variable"):
            interpolate_simulation_data(
                results,
                target_temps,
                target_times,
                target_positions,
                "invalid_var",
                is_temperature_sweep=True
            )


class TestPreparePlotData:
    """Test plot data preparation."""

    def create_mock_experimental_data(self):
        """Create mock experimental data."""
        params = CapacitorParams(
            epsilon_r=3.9,
            A=1e-4,
            d=1e-9,
            V0=1.0
        )

        row_values = np.array([100.0, 200.0, 300.0])  # Time
        col_values = np.array([300.0, 350.0, 400.0])  # Temperature

        # Create voltage grid
        voltage_grid = np.array([
            [1.2, 1.5, 1.8],  # 100s at different temps
            [2.1, 2.6, 3.0],  # 200s at different temps
            [2.8, 3.4, 3.9],  # 300s at different temps
        ])

        # Calculate dq grid
        C = calculate_capacitance(params)
        dq_grid = C * (voltage_grid - 1.0)

        return ExperimentalData(
            name="Test Data",
            capacitor=params,
            fixed_var="position",
            fixed_value=1e-6,
            row_var="time",
            row_values=row_values,
            col_var="temperature",
            col_values=col_values,
            voltage_grid=voltage_grid,
            dq_grid=dq_grid,
        )

    def create_mock_temp_sweep_results(self):
        """Create mock temperature sweep results."""
        temps = np.array([300.0, 350.0, 400.0])
        times = np.array([100.0, 200.0, 300.0])
        positions = np.array([0.0, 5e-7, 1e-6])

        # Simple synthetic data
        T_grid, t_grid, x_grid = np.meshgrid(temps, times, positions, indexing='ij')
        C_Txt = (T_grid / 300) * (t_grid / 100) * (1 + x_grid / 1e-6) * 1e3

        return {
            "temperatures": temps,
            "t": times,
            "x": positions,
            "C_Txt": C_Txt,
        }

    def test_prepare_plot_data_col_x_axis(self):
        """Test prepare_plot_data with column variable as X-axis."""
        exp_data = self.create_mock_experimental_data()
        sim_results = self.create_mock_temp_sweep_results()

        # X-axis = temperature (col_var)
        # Filter: time = 100s (row_var)
        x_values, sim_y, exp_y = prepare_plot_data(
            sim_results,
            exp_data,
            x_axis_var="temperature",
            sim_y_var="C",
            sim_filters={"time": 100.0},
            exp_filter={"time": 100.0},
            is_temperature_sweep=True
        )

        # Check shapes
        assert len(x_values) == 3
        assert len(sim_y) == 3
        assert len(exp_y) == 3

        # X values should be column values
        assert np.array_equal(x_values, exp_data.col_values)

        # Exp Y should be first row of dq_grid
        assert np.array_equal(exp_y, exp_data.dq_grid[0, :])

    def test_prepare_plot_data_row_x_axis(self):
        """Test prepare_plot_data with row variable as X-axis."""
        exp_data = self.create_mock_experimental_data()
        sim_results = self.create_mock_temp_sweep_results()

        # X-axis = time (row_var)
        # Filter: temperature = 300K (col_var)
        x_values, sim_y, exp_y = prepare_plot_data(
            sim_results,
            exp_data,
            x_axis_var="time",
            sim_y_var="C",
            sim_filters={"temperature": 300.0},
            exp_filter={"temperature": 300.0},
            is_temperature_sweep=True
        )

        # Check shapes
        assert len(x_values) == 3
        assert len(sim_y) == 3
        assert len(exp_y) == 3

        # X values should be row values
        assert np.array_equal(x_values, exp_data.row_values)

        # Exp Y should be first column of dq_grid
        assert np.array_equal(exp_y, exp_data.dq_grid[:, 0])

    def test_invalid_x_axis_var(self):
        """Test error when X-axis variable doesn't match row or col."""
        exp_data = self.create_mock_experimental_data()
        sim_results = self.create_mock_temp_sweep_results()

        # X-axis = position (which is fixed_var, not row or col)
        with pytest.raises(ValueError, match="must match row_var"):
            prepare_plot_data(
                sim_results,
                exp_data,
                x_axis_var="position",
                sim_y_var="C",
                sim_filters={"temperature": 300.0},
                exp_filter={"temperature": 300.0},
                is_temperature_sweep=True
            )

    def test_missing_exp_filter(self):
        """Test error when experimental filter is missing."""
        exp_data = self.create_mock_experimental_data()
        sim_results = self.create_mock_temp_sweep_results()

        # Missing time filter
        with pytest.raises(ValueError, match="Filter must specify"):
            prepare_plot_data(
                sim_results,
                exp_data,
                x_axis_var="temperature",
                sim_y_var="C",
                sim_filters={"time": 100.0},
                exp_filter={},  # Missing time
                is_temperature_sweep=True
            )

    def test_missing_sim_filter(self):
        """Test error when simulation filter is missing."""
        exp_data = self.create_mock_experimental_data()
        sim_results = self.create_mock_temp_sweep_results()

        # Missing time filter in sim_filters
        with pytest.raises(ValueError, match="Simulation filter must specify"):
            prepare_plot_data(
                sim_results,
                exp_data,
                x_axis_var="temperature",
                sim_y_var="C",
                sim_filters={},  # Missing time
                exp_filter={"time": 100.0},
                is_temperature_sweep=True
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
