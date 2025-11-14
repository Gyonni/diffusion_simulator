"""UI components for parameter optimization tab."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import math
from typing import Optional, Dict, Any, List, Tuple

import numpy as np
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk

from .optimization import (
    ParamSpec,
    OptimizationResult,
    run_grid_search_optimization,
    estimate_optimization_time
)
from .models import ExperimentalData


class OptimizationTab(ttk.Frame):
    """Tab for parameter optimization using grid search."""

    def __init__(self, parent, app_ref=None, **kwargs):
        """
        Initialize Optimization tab.

        Args:
            parent: Parent widget
            app_ref: Reference to main App instance
        """
        super().__init__(parent, **kwargs)
        self.app_ref = app_ref

        # Optimization state
        self.optimization_result: Optional[OptimizationResult] = None
        self.is_running = False
        self.abort_flag = threading.Event()

        # Parameter specifications (will be populated from UI)
        self.param_specs: List[ParamSpec] = []

        # Build UI
        self._build_ui()

    def _build_ui(self):
        """Build the optimization tab UI (controls only - graph in main area)."""
        # Create scrollable container for controls
        main_container = ttk.Frame(self)
        main_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Add scrollbar
        canvas = tk.Canvas(main_container)
        scrollbar = ttk.Scrollbar(main_container, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Build controls in scrollable frame
        self._build_controls(scrollable_frame)

    def _build_controls(self, parent):
        """Build control widgets in left panel."""
        bold_font = ("TkDefaultFont", 10, "bold")
        label_font = ("TkDefaultFont", 9)

        # === Parameter Selection ===
        param_frame = ttk.LabelFrame(parent, text="📊 Parameters to Optimize (Grid Search)", padding=10)
        param_frame.pack(fill=tk.X, padx=10, pady=5)

        # Layer selection
        row = 0
        ttk.Label(param_frame, text="Target Layer:", font=bold_font).grid(row=row, column=0, sticky="w", padx=5, pady=3)
        self.var_target_layer = tk.StringVar(value="0")
        self.combo_target_layer = ttk.Combobox(param_frame, textvariable=self.var_target_layer,
                                                state="readonly", width=25)
        self.combo_target_layer.grid(row=row, column=1, columnspan=2, padx=5, pady=3, sticky="ew")

        # D0 parameter
        row += 1
        self.var_optimize_D0 = tk.BooleanVar(value=True)
        ttk.Checkbutton(param_frame, text="D₀ [m²/s]", variable=self.var_optimize_D0,
                        command=self._update_time_estimate).grid(row=row, column=0, sticky="w", padx=5, pady=3)

        row += 1
        ttk.Label(param_frame, text="  Min:", font=label_font).grid(row=row, column=0, sticky="w", padx=20, pady=2)
        self.var_D0_min = tk.StringVar(value="1e-9")
        ttk.Entry(param_frame, textvariable=self.var_D0_min, width=12).grid(row=row, column=1, padx=5, pady=2, sticky="w")

        ttk.Label(param_frame, text="Max:", font=label_font).grid(row=row, column=1, sticky="e", padx=5, pady=2)
        self.var_D0_max = tk.StringVar(value="1e-5")
        ttk.Entry(param_frame, textvariable=self.var_D0_max, width=12).grid(row=row, column=2, padx=5, pady=2, sticky="w")

        row += 1
        ttk.Label(param_frame, text="  Points:", font=label_font).grid(row=row, column=0, sticky="w", padx=20, pady=2)
        self.var_D0_points = tk.StringVar(value="10")
        ttk.Entry(param_frame, textvariable=self.var_D0_points, width=12).grid(row=row, column=1, padx=5, pady=2, sticky="w")

        ttk.Label(param_frame, text="Scale:", font=label_font).grid(row=row, column=1, sticky="e", padx=5, pady=2)
        self.var_D0_scale = tk.StringVar(value="log")
        ttk.Combobox(param_frame, textvariable=self.var_D0_scale, values=["linear", "log"],
                     state="readonly", width=10).grid(row=row, column=2, padx=5, pady=2, sticky="w")

        # Ea parameter
        row += 1
        ttk.Separator(param_frame, orient="horizontal").grid(row=row, column=0, columnspan=3, sticky="ew", pady=5)

        row += 1
        self.var_optimize_Ea = tk.BooleanVar(value=True)
        ttk.Checkbutton(param_frame, text="Eₐ [eV]", variable=self.var_optimize_Ea,
                        command=self._update_time_estimate).grid(row=row, column=0, sticky="w", padx=5, pady=3)

        row += 1
        ttk.Label(param_frame, text="  Min:", font=label_font).grid(row=row, column=0, sticky="w", padx=20, pady=2)
        self.var_Ea_min = tk.StringVar(value="0.1")
        ttk.Entry(param_frame, textvariable=self.var_Ea_min, width=12).grid(row=row, column=1, padx=5, pady=2, sticky="w")

        ttk.Label(param_frame, text="Max:", font=label_font).grid(row=row, column=1, sticky="e", padx=5, pady=2)
        self.var_Ea_max = tk.StringVar(value="3.0")
        ttk.Entry(param_frame, textvariable=self.var_Ea_max, width=12).grid(row=row, column=2, padx=5, pady=2, sticky="w")

        row += 1
        ttk.Label(param_frame, text="  Points:", font=label_font).grid(row=row, column=0, sticky="w", padx=20, pady=2)
        self.var_Ea_points = tk.StringVar(value="10")
        ttk.Entry(param_frame, textvariable=self.var_Ea_points, width=12).grid(row=row, column=1, padx=5, pady=2, sticky="w")

        ttk.Label(param_frame, text="Scale:", font=label_font).grid(row=row, column=1, sticky="e", padx=5, pady=2)
        self.var_Ea_scale = tk.StringVar(value="linear")
        ttk.Combobox(param_frame, textvariable=self.var_Ea_scale, values=["linear", "log"],
                     state="readonly", width=10).grid(row=row, column=2, padx=5, pady=2, sticky="w")

        # k parameter
        row += 1
        ttk.Separator(param_frame, orient="horizontal").grid(row=row, column=0, columnspan=3, sticky="ew", pady=5)

        row += 1
        self.var_optimize_k = tk.BooleanVar(value=False)
        ttk.Checkbutton(param_frame, text="k [1/s]", variable=self.var_optimize_k,
                        command=self._update_time_estimate).grid(row=row, column=0, sticky="w", padx=5, pady=3)

        row += 1
        ttk.Label(param_frame, text="  Min:", font=label_font).grid(row=row, column=0, sticky="w", padx=20, pady=2)
        self.var_k_min = tk.StringVar(value="0.0")
        ttk.Entry(param_frame, textvariable=self.var_k_min, width=12).grid(row=row, column=1, padx=5, pady=2, sticky="w")

        ttk.Label(param_frame, text="Max:", font=label_font).grid(row=row, column=1, sticky="e", padx=5, pady=2)
        self.var_k_max = tk.StringVar(value="100.0")
        ttk.Entry(param_frame, textvariable=self.var_k_max, width=12).grid(row=row, column=2, padx=5, pady=2, sticky="w")

        row += 1
        ttk.Label(param_frame, text="  Points:", font=label_font).grid(row=row, column=0, sticky="w", padx=20, pady=2)
        self.var_k_points = tk.StringVar(value="5")
        ttk.Entry(param_frame, textvariable=self.var_k_points, width=12).grid(row=row, column=1, padx=5, pady=2, sticky="w")

        ttk.Label(param_frame, text="Scale:", font=label_font).grid(row=row, column=1, sticky="e", padx=5, pady=2)
        self.var_k_scale = tk.StringVar(value="linear")
        ttk.Combobox(param_frame, textvariable=self.var_k_scale, values=["linear", "log"],
                     state="readonly", width=10).grid(row=row, column=2, padx=5, pady=2, sticky="w")

        # Bind value changes to update time estimate
        for var in [self.var_D0_points, self.var_Ea_points, self.var_k_points]:
            var.trace_add("write", lambda *args: self._update_time_estimate())

        # === Optimization Settings ===
        settings_frame = ttk.LabelFrame(parent, text="⚙️ Optimization Settings", padding=10)
        settings_frame.pack(fill=tk.X, padx=10, pady=5)

        row = 0
        ttk.Label(settings_frame, text="Metric:", font=bold_font).grid(row=row, column=0, sticky="w", padx=5, pady=3)
        self.var_metric = tk.StringVar(value="r_squared")
        ttk.Combobox(settings_frame, textvariable=self.var_metric,
                     values=["r_squared", "nrmse"], state="readonly", width=22).grid(row=row, column=1, padx=5, pady=3)

        row += 1
        ttk.Label(settings_frame, text="Sim Y Variable:", font=bold_font).grid(row=row, column=0, sticky="w", padx=5, pady=3)
        self.var_sim_y = tk.StringVar(value="C")
        ttk.Combobox(settings_frame, textvariable=self.var_sim_y,
                     values=["C", "J_source", "J_end", "J_target"], state="readonly", width=22).grid(row=row, column=1, padx=5, pady=3)

        # === Run Control ===
        run_frame = ttk.LabelFrame(parent, text="▶️ Run Optimization", padding=10)
        run_frame.pack(fill=tk.X, padx=10, pady=5)

        # Time estimate
        self.lbl_time_estimate = ttk.Label(run_frame, text="Estimated time: --", font=("TkDefaultFont", 9))
        self.lbl_time_estimate.pack(anchor="w", pady=(0, 5))

        # Progress bar
        self.progress_var = tk.DoubleVar(value=0)
        self.progress_bar = ttk.Progressbar(run_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill=tk.X, pady=5)

        self.lbl_progress = ttk.Label(run_frame, text="Ready", font=("TkDefaultFont", 9))
        self.lbl_progress.pack(anchor="w", pady=(0, 5))

        # Buttons
        btn_frame = ttk.Frame(run_frame)
        btn_frame.pack(fill=tk.X, pady=5)

        self.btn_run = ttk.Button(btn_frame, text="▶ Run Optimization", command=self._run_optimization, width=20)
        self.btn_run.pack(side=tk.LEFT, padx=5)

        self.btn_stop = ttk.Button(btn_frame, text="⏹ Stop", command=self._stop_optimization, width=15, state="disabled")
        self.btn_stop.pack(side=tk.LEFT, padx=5)

        # === Results ===
        results_frame = ttk.LabelFrame(parent, text="📈 Optimization Results", padding=10)
        results_frame.pack(fill=tk.X, padx=10, pady=5)

        self.lbl_best_score = ttk.Label(results_frame, text="Best Score: --", font=bold_font)
        self.lbl_best_score.pack(anchor="w", pady=2)

        self.lbl_best_params = tk.Text(results_frame, height=6, width=40, font=("Courier", 9))
        self.lbl_best_params.pack(fill=tk.X, pady=5)
        self.lbl_best_params.insert("1.0", "Run optimization to see results...")
        self.lbl_best_params.config(state="disabled")

        # Action buttons
        action_frame = ttk.Frame(results_frame)
        action_frame.pack(fill=tk.X, pady=5)

        ttk.Button(action_frame, text="✓ Apply to Setup", command=self._apply_to_setup, width=18).pack(side=tk.LEFT, padx=3)
        ttk.Button(action_frame, text="📊 Show Heatmap", command=self._show_heatmap, width=18).pack(side=tk.LEFT, padx=3)
        ttk.Button(action_frame, text="💾 Save Results", command=self._save_results, width=18).pack(side=tk.LEFT, padx=3)

        # Update initial time estimate
        self._update_time_estimate()

    def _update_time_estimate(self):
        """Update estimated optimization time."""
        try:
            specs = []
            if self.var_optimize_D0.get():
                specs.append(ParamSpec("D0", 1e-9, 1e-5, int(self.var_D0_points.get()), "log", 0))
            if self.var_optimize_Ea.get():
                specs.append(ParamSpec("Ea", 0.1, 3.0, int(self.var_Ea_points.get()), "linear", 0))
            if self.var_optimize_k.get():
                specs.append(ParamSpec("k", 0.0, 100.0, int(self.var_k_points.get()), "linear", 0))

            if not specs:
                self.lbl_time_estimate.config(text="Select at least one parameter to optimize")
                return

            n_combinations = np.prod([spec.n_points for spec in specs])
            estimated_time = estimate_optimization_time(specs, single_sim_time=2.0)

            if estimated_time < 60:
                time_str = f"{estimated_time:.0f} seconds"
            else:
                time_str = f"{estimated_time/60:.1f} minutes"

            self.lbl_time_estimate.config(text=f"Estimated time: {time_str} ({n_combinations} simulations)")

        except ValueError:
            self.lbl_time_estimate.config(text="Invalid parameter values")

    def _run_optimization(self):
        """Start optimization in background thread."""
        print("[DEBUG] Run Optimization button clicked")

        # Validation checks
        try:
            if not self.app_ref:
                messagebox.showerror("Error", "Application reference not found.")
                print("[ERROR] app_ref is None")
                return

            if not hasattr(self.app_ref, 'results'):
                messagebox.showerror("No Simulation", "Please run a simulation first (Setup tab).\n\nSimulation results not found.")
                print("[ERROR] app_ref has no 'results' attribute")
                return

            if not self.app_ref.results:
                messagebox.showerror("No Simulation", "Please run a simulation first (Setup tab).\n\nSimulation results are empty.")
                print("[ERROR] app_ref.results is empty")
                return

            print("[DEBUG] Simulation results found")

            # Get experimental data from Analysis tab
            if not hasattr(self.app_ref, 'analysis_tab_widget'):
                messagebox.showerror("No Analysis Tab", "Analysis tab not found.\n\nPlease ensure the Analysis tab is properly initialized.")
                print("[ERROR] app_ref has no 'analysis_tab_widget' attribute")
                return

            exp_data = self.app_ref.analysis_tab_widget.get_experimental_data()
            if exp_data is None:
                messagebox.showerror("No Experimental Data",
                    "Please load experimental data in the Analysis tab first.\n\n"
                    "Steps:\n"
                    "1. Go to Analysis tab\n"
                    "2. Click 'Load Experimental Data'\n"
                    "3. Select a valid data file")
                print("[ERROR] Experimental data is None")
                return

            print(f"[DEBUG] Experimental data loaded: {len(exp_data.temps)} temps, {len(exp_data.times)} times, {len(exp_data.positions)} positions")

        except Exception as e:
            messagebox.showerror("Validation Error", f"Error during validation:\n{str(e)}")
            print(f"[ERROR] Exception during validation: {e}")
            import traceback
            traceback.print_exc()
            return

        # Build parameter specifications
        try:
            param_specs = []
            layer_idx = int(self.var_target_layer.get())
            print(f"[DEBUG] Target layer index: {layer_idx}")

            if self.var_optimize_D0.get():
                D0_min = float(self.var_D0_min.get())
                D0_max = float(self.var_D0_max.get())
                D0_points = int(self.var_D0_points.get())
                D0_scale = self.var_D0_scale.get()
                print(f"[DEBUG] D0: min={D0_min}, max={D0_max}, points={D0_points}, scale={D0_scale}")
                param_specs.append(ParamSpec("D0", D0_min, D0_max, D0_points, D0_scale, layer_idx))

            if self.var_optimize_Ea.get():
                Ea_min = float(self.var_Ea_min.get())
                Ea_max = float(self.var_Ea_max.get())
                Ea_points = int(self.var_Ea_points.get())
                Ea_scale = self.var_Ea_scale.get()
                print(f"[DEBUG] Ea: min={Ea_min}, max={Ea_max}, points={Ea_points}, scale={Ea_scale}")
                param_specs.append(ParamSpec("Ea", Ea_min, Ea_max, Ea_points, Ea_scale, layer_idx))

            if self.var_optimize_k.get():
                k_min = float(self.var_k_min.get())
                k_max = float(self.var_k_max.get())
                k_points = int(self.var_k_points.get())
                k_scale = self.var_k_scale.get()
                print(f"[DEBUG] k: min={k_min}, max={k_max}, points={k_points}, scale={k_scale}")
                param_specs.append(ParamSpec("k", k_min, k_max, k_points, k_scale, layer_idx))

            if not param_specs:
                messagebox.showerror("No Parameters",
                    "Please select at least one parameter to optimize.\n\n"
                    "Check the boxes for D0, Ea, or k in the Parameters section.")
                print("[ERROR] No parameters selected")
                return

            print(f"[DEBUG] Total {len(param_specs)} parameters selected")

        except ValueError as e:
            messagebox.showerror("Invalid Input",
                f"Invalid parameter values:\n{str(e)}\n\n"
                "Please check that all min/max values are valid numbers.")
            print(f"[ERROR] ValueError building param_specs: {e}")
            import traceback
            traceback.print_exc()
            return
        except Exception as e:
            messagebox.showerror("Parameter Error", f"Error building parameters:\n{str(e)}")
            print(f"[ERROR] Exception building param_specs: {e}")
            import traceback
            traceback.print_exc()
            return

        # Get simulation parameters
        try:
            base_layers = self.app_ref.layer_table.get_layers()
            print(f"[DEBUG] Got {len(base_layers)} layers from layer table")

            base_sim_params = self.app_ref._get_sim_params()
            print(f"[DEBUG] Got simulation parameters: Cs={base_sim_params.Cs}, dt={base_sim_params.dt}, t_max={base_sim_params.t_max}")

            # Check if temperature sweep
            is_temp_sweep = hasattr(self.app_ref, 'is_temperature_sweep') and self.app_ref.is_temperature_sweep
            if is_temp_sweep:
                temperatures = self.app_ref.temperature_manager.get_temperatures()
                print(f"[DEBUG] Temperature sweep mode: {len(temperatures)} temperatures")
            else:
                temperatures = [300.0]
                print("[DEBUG] Single temperature mode: 300.0 K")

            sim_y_var = self.var_sim_y.get()
            metric = self.var_metric.get()
            print(f"[DEBUG] sim_y_var={sim_y_var}, metric={metric}")

        except Exception as e:
            messagebox.showerror("Configuration Error",
                f"Error getting simulation parameters:\n{str(e)}\n\n"
                "Please ensure the Setup tab is properly configured.")
            print(f"[ERROR] Exception getting sim parameters: {e}")
            import traceback
            traceback.print_exc()
            return

        # Update UI state
        self.is_running = True
        self.abort_flag.clear()
        self.btn_run.config(state="disabled")
        self.btn_stop.config(state="normal")
        self.progress_var.set(0)
        self.lbl_progress.config(text="Starting optimization...")
        print("[DEBUG] UI state updated, starting optimization thread")

        # Run optimization in thread
        def optimization_thread():
            try:
                print("[DEBUG] Optimization thread started")
                result = run_grid_search_optimization(
                    exp_data=exp_data,
                    base_layers=base_layers,
                    base_sim_params=base_sim_params,
                    temperatures=temperatures,
                    param_specs=param_specs,
                    sim_y_var=sim_y_var,
                    metric=metric,
                    progress_callback=self._update_progress,
                    abort_flag=self.abort_flag
                )
                print("[DEBUG] Optimization completed successfully")

                # Update UI on main thread
                self.after(0, lambda: self._optimization_complete(result))

            except Exception as e:
                print(f"[ERROR] Optimization thread exception: {e}")
                import traceback
                traceback.print_exc()
                self.after(0, lambda: self._optimization_error(str(e)))

        thread = threading.Thread(target=optimization_thread, daemon=True)
        thread.start()
        print("[DEBUG] Optimization thread launched")

    def _stop_optimization(self):
        """Stop ongoing optimization."""
        self.abort_flag.set()
        self.lbl_progress.config(text="Stopping...")
        self.btn_stop.config(state="disabled")

    def _update_progress(self, current: int, total: int, best_score: float):
        """Update progress bar and label."""
        pct = 100 * current / total
        self.progress_var.set(pct)
        self.lbl_progress.config(text=f"Progress: {current}/{total} ({pct:.0f}%) | Best: {best_score:.4f}")

    def _optimization_complete(self, result: OptimizationResult):
        """Handle optimization completion."""
        print("[DEBUG] Optimization complete handler called")
        self.is_running = False
        self.btn_run.config(state="normal")
        self.btn_stop.config(state="disabled")
        self.optimization_result = result

        if result.success:
            self.lbl_progress.config(text=f"✓ Complete in {result.elapsed_time:.1f}s")
            self.lbl_best_score.config(text=f"Best {result.metric_name}: {result.best_score:.4f}")

            # Display best parameters
            self.lbl_best_params.config(state="normal")
            self.lbl_best_params.delete("1.0", tk.END)
            for (layer_idx, param_name), value in result.best_params.items():
                self.lbl_best_params.insert(tk.END, f"Layer {layer_idx} {param_name}: {value:.4e}\n")
            self.lbl_best_params.config(state="disabled")

            # Draw visualization in main graph area
            print("[DEBUG] Drawing optimization results in main graph area")
            self._draw_optimization_results(result)

            # Check if results are suspicious
            completion_msg = f"Found optimal parameters!\n\n"
            completion_msg += f"Best {result.metric_name}: {result.best_score:.4f}\n"
            completion_msg += f"Time: {result.elapsed_time:.1f}s\n"
            completion_msg += f"Simulations: {result.n_simulations}"

            # Warn if R² is 0 or very low
            if result.metric_name == "r_squared" and result.best_score < 0.01:
                completion_msg += "\n\n⚠️ WARNING: Very low R² detected!"
                completion_msg += "\nPossible causes:"
                completion_msg += "\n• Wrong 'Sim Y Variable' selected"
                completion_msg += "\n• Unit mismatch (sim vs exp data)"
                completion_msg += "\n• Poor parameter ranges"
                completion_msg += "\n\nCheck console for detailed diagnostics."

            messagebox.showinfo("Optimization Complete", completion_msg)
        else:
            self.lbl_progress.config(text=f"✗ {result.message}")
            messagebox.showwarning("Optimization Stopped", result.message)

    def _optimization_error(self, error_msg: str):
        """Handle optimization error."""
        print(f"[ERROR] Optimization error handler called: {error_msg}")
        self.is_running = False
        self.btn_run.config(state="normal")
        self.btn_stop.config(state="disabled")
        self.lbl_progress.config(text="✗ Error occurred")

        # Show detailed error message
        error_display = f"Optimization failed:\n\n{error_msg}\n\n"
        error_display += "Common causes:\n"
        error_display += "• Invalid parameter ranges (min >= max)\n"
        error_display += "• Experimental data mismatch with simulation\n"
        error_display += "• Too many grid points (memory overflow)\n"
        error_display += "• Check console for detailed traceback"

        messagebox.showerror("Optimization Error", error_display)

    def _draw_optimization_results(self, result: OptimizationResult):
        """Draw optimization results in main graph area."""
        try:
            if not self.app_ref or not hasattr(self.app_ref, 'optimization_fig'):
                print("[ERROR] Main graph area not accessible")
                return

            fig = self.app_ref.optimization_fig
            fig.clear()

            # Determine number of parameters optimized
            n_params = len(result.param_names)
            print(f"[DEBUG] Drawing results for {n_params} parameters")

            if n_params == 1:
                # 1D plot: parameter vs score
                ax = fig.add_subplot(111)
                param_name = result.param_names[0]
                ax.plot(result.all_params[:, 0], result.all_scores, 'b.-', markersize=8)
                ax.axvline(result.best_params[param_name], color='r', linestyle='--', linewidth=2, label='Best')
                ax.set_xlabel(f"{param_name[1]} (Layer {param_name[0]})")
                ax.set_ylabel(f"{result.metric_name}")
                ax.set_title(f"Optimization Results: {result.metric_name} = {result.best_score:.4f}")
                ax.legend()
                ax.grid(True, alpha=0.3)

            elif n_params == 2:
                # 2D heatmap: parameter1 vs parameter2 vs score
                import numpy as np
                param1_name = result.param_names[0]
                param2_name = result.param_names[1]

                # Reshape scores to 2D grid
                unique_p1 = np.unique(result.all_params[:, 0])
                unique_p2 = np.unique(result.all_params[:, 1])
                scores_2d = result.all_scores.reshape(len(unique_p1), len(unique_p2))

                ax = fig.add_subplot(111)
                im = ax.imshow(scores_2d, aspect='auto', origin='lower', cmap='viridis',
                              extent=[unique_p2.min(), unique_p2.max(), unique_p1.min(), unique_p1.max()])
                ax.plot(result.best_params[param2_name], result.best_params[param1_name],
                       'r*', markersize=20, label='Best')
                ax.set_xlabel(f"{param2_name[1]} (Layer {param2_name[0]})")
                ax.set_ylabel(f"{param1_name[1]} (Layer {param1_name[0]})")
                ax.set_title(f"Optimization Heatmap: {result.metric_name} = {result.best_score:.4f}")
                fig.colorbar(im, ax=ax, label=result.metric_name)
                ax.legend()

            else:
                # 3+ parameters: show convergence plot
                ax = fig.add_subplot(111)
                cumulative_best = np.maximum.accumulate(result.all_scores) if result.metric_name == "r_squared" else np.minimum.accumulate(result.all_scores)
                ax.plot(cumulative_best, 'b-', linewidth=2)
                ax.axhline(result.best_score, color='r', linestyle='--', linewidth=2, label='Best')
                ax.set_xlabel("Simulation Number")
                ax.set_ylabel(f"Best {result.metric_name}")
                ax.set_title(f"Optimization Convergence: {n_params} Parameters")
                ax.legend()
                ax.grid(True, alpha=0.3)

            fig.tight_layout()
            self.app_ref.optimization_canvas.draw()
            print("[DEBUG] Optimization results drawn successfully")

        except Exception as e:
            print(f"[ERROR] Failed to draw optimization results: {e}")
            import traceback
            traceback.print_exc()
            messagebox.showerror("Visualization Error",
                                f"Failed to draw results:\n{str(e)}\n\n"
                                "Results are still available in the left panel.")

    def _apply_to_setup(self):
        """Apply optimized parameters to Setup tab."""
        if self.optimization_result is None or not self.optimization_result.success:
            messagebox.showwarning("No Results", "No optimization results to apply.")
            return

        # Apply best parameters to layer table in Setup tab
        try:
            layer_table = self.app_ref.layer_table
            layers = layer_table.get_layers()

            for (layer_idx, param_name), value in self.optimization_result.best_params.items():
                # Update layer table
                if param_name == "D0":
                    layer_table.table.set(layer_table.table.get_children()[layer_idx], "D0", f"{value:.4e}")
                elif param_name == "Ea":
                    layer_table.table.set(layer_table.table.get_children()[layer_idx], "Ea", f"{value:.4f}")
                elif param_name == "k":
                    layer_table.table.set(layer_table.table.get_children()[layer_idx], "k", f"{value:.4e}")

            messagebox.showinfo("Applied", "Optimized parameters have been applied to Setup tab.\n\n"
                                          "You can now run a new simulation with these parameters.")

        except Exception as e:
            messagebox.showerror("Apply Error", f"Failed to apply parameters:\n{str(e)}")

    def _show_heatmap(self):
        """Redraw optimization results in main graph area."""
        if self.optimization_result is None or not self.optimization_result.success:
            messagebox.showwarning("No Results", "No optimization results to visualize.")
            return

        # Redraw the visualization
        self._draw_optimization_results(self.optimization_result)
        messagebox.showinfo("Visualization Updated", "Optimization results are displayed in the main graph area.")

    def _save_results(self):
        """Save optimization results to file."""
        if self.optimization_result is None or not self.optimization_result.success:
            messagebox.showwarning("No Results", "No optimization results to save.")
            return

        # Implementation in next step
        messagebox.showinfo("Coming Soon", "Save functionality will be implemented next!")

    def initialize(self, layer_names: List[str]):
        """
        Initialize UI with layer names.

        Args:
            layer_names: List of layer names from Setup tab
        """
        # Update layer combobox
        self.combo_target_layer['values'] = [f"{i}: {name}" for i, name in enumerate(layer_names)]
        if layer_names:
            self.combo_target_layer.set(f"0: {layer_names[0]}")
