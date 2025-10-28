from __future__ import annotations

import math
import textwrap
import threading
import tkinter as tk
from tkinter import messagebox, ttk
from typing import List, Optional

from tkinter import scrolledtext

import numpy as np

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure

_HTML_AVAILABLE = False
try:  # pragma: no cover - optional dependency
    from tkhtmlview import HTMLLabel
    _HTML_AVAILABLE = True
except ImportError:
    HTMLLabel = None

MANUAL_HTML = """
<h1 style='text-align:center;margin-bottom:0;'>Diffusion–Reaction Simulator</h1>
<p style='text-align:center;font-style:italic;margin-top:4px;'>Multilayer 1D transport solver</p>

<h2>Governing Equation</h2>
<p style='font-size:1.1em;text-align:center;'>
∂C/∂t = ∂/∂x&nbsp;( D(x) ∂C/∂x ) − k(x) C
</p>
<p>Each layer supplies its own diffusivity <em>D</em> and reaction rate <em>k</em>. The solver enforces continuity of concentration and flux at every interface using a Crank–Nicolson scheme on a shared mesh.</p>

<h2>Boundary Conditions</h2>
<ul>
  <li><strong>Left</strong>: Dirichlet &nbsp;C(0,t) = C<sub>s</sub></li>
  <li><strong>Right</strong>: selectable Dirichlet sink or Neumann (impermeable)</li>
</ul>

<h2>Usage Highlights</h2>
<ol>
  <li>Build the layer stack (top to bottom) with thickness, diffusivity, reaction rate, and node count.</li>
  <li>Adjust global parameters (C<sub>s</sub>, Δt, t<sub>max</sub>) and choose the terminating boundary.</li>
  <li>Press <strong>Run Simulation</strong>; progress updates appear below the controls.</li>
  <li>Inspect flux, cumulative uptake, and the spatial profile using the toolbar, slider, or stepper buttons.</li>
  <li>Use the <strong>Flux view</strong> dropdown to focus on surface, target interface, exit, or probe curves.</li>
  <li>Export flux histories (CSV/NPZ) or the current profile (CSV) via the buttons on the left.</li>
</ol>

<h2>Input Constraints</h2>
<ul>
  <li>At least one layer; the final row is treated as the reporting layer for mass/uptake metrics.</li>
  <li>Layer thickness &gt; 0, diffusivity &gt; 0, reaction rate ≥ 0, nodes ≥ 2.</li>
  <li>Surface concentration C<sub>s</sub> ≥ 0.</li>
  <li>Δt &gt; 0 and less than t<sub>max</sub>. Very large Δt will be reduced automatically.</li>
</ul>

<h2>Key Quantities</h2>
<ul>
  <li><strong>Flux @ surface</strong> = −D&nbsp;∂C/∂x at x = 0</li>
  <li><strong>Flux into reporting interface</strong>: flux across the boundary between the penultimate and final layers</li>
  <li><strong>Flux @ exit</strong>: flux at x = L</li>
  <li><strong>Flux @ probe</strong>: flux across the element containing the user-specified position (optional)</li>
  <li><strong>Mass in reporting layer</strong> = ∫<sub>reporting</sub> C(x,t) dx</li>
  <li><strong>ℓ</strong> = √(D/k) reported for the final layer; keep ℓ/Δx ≥ 10 for accuracy.</li>
</ul>

<h2>Tips</h2>
<ul>
  <li>Δt is automatically capped using the smallest (Δx)²/D to reduce boundary oscillations.</li>
  <li>Use coarse node counts for passive layers (k = 0) and concentrate resolution in the reactive/reporting layer.</li>
  <li>Set a flux probe (position or layer) to inspect local flux and uptake alongside the curve.</li>
  <li>Use the CLI (<code>python -m diffreact_gui.main --cli --debug</code>) for quick batch runs.</li>
</ul>
"""

CONSTRAINTS_TEXT = (
    "Input requirements:\n"
    "  • At least one layer (final row is the reporting layer).\n"
    "  • Thickness > 0, diffusivity > 0, reaction rate ≥ 0, nodes ≥ 2.\n"
    "  • Surface concentration Cs ≥ 0.\n"
    "  • Δt > 0 and Δt < t_max.\n"
)

ARRHENIUS_R = 8.31446261815324  # J/(mol·K)

from .config import Defaults, RESULTS_DIR
from .models import LayerParam, SimParams
from .plots import create_figures, update_flux_axes, update_profile_axes
from .solver import mass_balance_diagnostics, run_simulation
from .utils import (
    cumulative_trapz,
    ensure_results_dir,
    save_csv_flux,
    save_csv_profile,
    save_profiles_matrix,
    save_metadata,
    save_results_npz,
    validate_params,
)


class LayerTable(ttk.Frame):
    """A small widget to manage multilayer parameter entries."""

    columns = ("name", "thickness", "diffusivity", "reaction", "nodes")

    def __init__(
        self,
        master: tk.Widget,
        layers: List[LayerParam],
        *,
        on_layers_changed: Optional[callable] = None,
    ) -> None:
        super().__init__(master)
        self._on_layers_changed = on_layers_changed

        self.tree = ttk.Treeview(self, columns=self.columns, show="headings", height=6)
        for col, heading in zip(
            self.columns,
            ["Name", "Thickness [m]", "D [m^2/s]", "k [1/s]", "Nodes"],
        ):
            self.tree.heading(col, text=heading)
            self.tree.column(col, width=110, anchor=tk.CENTER)
        self.tree.pack(fill=tk.BOTH, expand=True)

        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        self.entry_vars = {
            "name": tk.StringVar(value="Layer"),
            "thickness": tk.StringVar(value="1e-7"),
            "diffusivity": tk.StringVar(value="1e-14"),
            "reaction": tk.StringVar(value="0.0"),
            "nodes": tk.StringVar(value="101"),
        }

        form = ttk.Frame(self)
        form.pack(fill=tk.X, pady=4)

        for idx, (label, key) in enumerate(
            [
                ("Name", "name"),
                ("Thickness [m]", "thickness"),
                ("D [m^2/s]", "diffusivity"),
                ("k [1/s]", "reaction"),
                ("Nodes", "nodes"),
            ]
        ):
            frm = ttk.Frame(form)
            frm.grid(row=idx // 2, column=idx % 2, sticky="ew", padx=2, pady=2)
            ttk.Label(frm, text=label).pack(anchor=tk.W)
            ttk.Entry(frm, textvariable=self.entry_vars[key], width=18).pack(fill=tk.X)

        form.grid_columnconfigure(0, weight=1)
        form.grid_columnconfigure(1, weight=1)

        arr_frame = ttk.Labelframe(self, text="Arrhenius (optional)")
        arr_frame.pack(fill=tk.X, pady=4)

        self.arrhenius_vars = {
            "T": tk.StringVar(value=""),
            "D0": tk.StringVar(value=""),
            "Ea": tk.StringVar(value=""),
        }

        ttk.Label(arr_frame, text="Temperature [K]").grid(row=0, column=0, sticky="w", padx=2, pady=2)
        ttk.Entry(arr_frame, textvariable=self.arrhenius_vars["T"], width=12).grid(row=0, column=1, padx=2, pady=2)

        ttk.Label(arr_frame, text="D0 [m^2/s]").grid(row=1, column=0, sticky="w", padx=2, pady=2)
        ttk.Entry(arr_frame, textvariable=self.arrhenius_vars["D0"], width=12).grid(row=1, column=1, padx=2, pady=2)

        ttk.Label(arr_frame, text="Ea [J/mol]").grid(row=2, column=0, sticky="w", padx=2, pady=2)
        ttk.Entry(arr_frame, textvariable=self.arrhenius_vars["Ea"], width=12).grid(row=2, column=1, padx=2, pady=2)

        ttk.Button(
            arr_frame,
            text="Compute D",
            command=self._apply_arrhenius,
        ).grid(row=0, column=2, rowspan=3, padx=6, pady=2, sticky="ns")

        btn_bar = ttk.Frame(self)
        btn_bar.pack(fill=tk.X, pady=4)
        ttk.Button(btn_bar, text="Add", command=self._add).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_bar, text="Update", command=self._update).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_bar, text="Remove", command=self._remove).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_bar, text="↑", width=3, command=lambda: self._move(-1)).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_bar, text="↓", width=3, command=lambda: self._move(1)).pack(side=tk.LEFT, padx=2)

        for layer in layers:
            self._insert_layer(layer)
        if layers:
            first_id = self.tree.get_children()[0]
            self.tree.selection_set(first_id)
            self.tree.focus(first_id)
            self._on_select()
        self._notify_layers_changed()

    def _insert_layer(self, layer: LayerParam) -> None:
        self.tree.insert(
            "",
            "end",
            values=(
                layer.name,
                f"{layer.thickness:.6g}",
                f"{layer.diffusivity:.6g}",
                f"{layer.reaction_rate:.6g}",
                str(layer.nodes),
            ),
        )

    def _on_select(self, _event: Optional[tk.Event] = None) -> None:
        item = self._selected_item()
        if not item:
            return
        values = self.tree.item(item, "values")
        keys = ("name", "thickness", "diffusivity", "reaction", "nodes")
        for key, value in zip(keys, values):
            self.entry_vars[key].set(value)

    def _selected_item(self) -> Optional[str]:
        sel = self.tree.selection()
        return sel[0] if sel else None

    def _add(self) -> None:
        try:
            layer = self._layer_from_entries()
        except ValueError as exc:
            messagebox.showerror("Invalid layer", str(exc), parent=self)
            return
        self._insert_layer(layer)
        self._notify_layers_changed()

    def _update(self) -> None:
        item = self._selected_item()
        if not item:
            return
        try:
            layer = self._layer_from_entries()
        except ValueError as exc:
            messagebox.showerror("Invalid layer", str(exc), parent=self)
            return
        self.tree.item(
            item,
            values=(
                layer.name,
                f"{layer.thickness:.6g}",
                f"{layer.diffusivity:.6g}",
                f"{layer.reaction_rate:.6g}",
                str(layer.nodes),
            ),
        )
        self._notify_layers_changed()

    def _remove(self) -> None:
        item = self._selected_item()
        if not item:
            return
        self.tree.delete(item)
        self._notify_layers_changed()

    def _move(self, direction: int) -> None:
        item = self._selected_item()
        if not item:
            return
        parent = self.tree.parent(item)
        index = self.tree.index(item)
        new_index = index + direction
        if new_index < 0 or new_index >= len(self.tree.get_children(parent)):
            return
        self.tree.move(item, parent, new_index)
        self._notify_layers_changed()

    def _apply_arrhenius(self) -> None:
        item = self._selected_item()
        if not item:
            messagebox.showinfo("Arrhenius", "Select a layer to apply Arrhenius parameters.", parent=self)
            return
        try:
            T = float(self.arrhenius_vars["T"].get())
            D0 = float(self.arrhenius_vars["D0"].get())
            Ea = float(self.arrhenius_vars["Ea"].get())
        except ValueError:
            messagebox.showerror("Arrhenius", "Provide numeric Temperature, D0, and Ea values.", parent=self)
            return
        if T <= 0 or D0 <= 0:
            messagebox.showerror("Arrhenius", "Temperature and D0 must be positive.", parent=self)
            return
        D = D0 * math.exp(-Ea / (ARRHENIUS_R * T))
        self.entry_vars["diffusivity"].set(f"{D:.6g}")
        self._update()
        self._notify_layers_changed()

    def _layer_from_entries(self) -> LayerParam:
        try:
            name = self.entry_vars["name"].get().strip() or "Layer"
            thickness = float(self.entry_vars["thickness"].get())
            diffusivity = float(self.entry_vars["diffusivity"].get())
            reaction = float(self.entry_vars["reaction"].get())
            nodes = int(self.entry_vars["nodes"].get())
        except ValueError as exc:
            raise ValueError("Layer fields must be numeric") from exc
        if nodes < 2:
            raise ValueError("Nodes must be ≥ 2")
        if thickness <= 0 or diffusivity <= 0:
            raise ValueError("Thickness and diffusivity must be positive")
        if reaction < 0:
            raise ValueError("Reaction rate must be ≥ 0")
        return LayerParam(name=name, thickness=thickness, diffusivity=diffusivity, reaction_rate=reaction, nodes=nodes)

    def get_layers(self) -> List[LayerParam]:
        layers: List[LayerParam] = []
        for item in self.tree.get_children():
            name, thickness, diffusivity, reaction, nodes = self.tree.item(item, "values")
            layers.append(
                LayerParam(
                    name=name,
                    thickness=float(thickness),
                    diffusivity=float(diffusivity),
                    reaction_rate=float(reaction),
                    nodes=int(nodes),
                )
            )
        return layers

    def get_layer_names(self) -> List[str]:
        return [self.tree.item(item, "values")[0] for item in self.tree.get_children()]

    def _notify_layers_changed(self) -> None:
        if self._on_layers_changed is not None:
            self._on_layers_changed()


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Multilayer Diffusion–Reaction Simulator")
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self.results: Optional[dict] = None
        self.last_params: Optional[SimParams] = None
        self._current_time_index = 0
        self._max_time_index = 0
        self._suppress_time_callback = False
        self._progress_value = tk.DoubleVar(value=0.0)
        self._manual_window: Optional[tk.Toplevel] = None
        self.selected_flux = tk.StringVar(value="Target interface")

        self.frm_left = ttk.Frame(self, padding=6)
        self.frm_right = ttk.Frame(self, padding=6)
        self.frm_left.grid(row=0, column=0, sticky="nsew")
        self.frm_right.grid(row=0, column=1, sticky="nsew")
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._build_inputs(self.frm_left)

        fig, artists = create_figures()
        self.artists = artists
        self.canvas = FigureCanvasTkAgg(fig, master=self.frm_right)
        self.canvas.draw_idle()
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        self.toolbar = NavigationToolbar2Tk(self.canvas, self.frm_right)
        self.toolbar.update()
        self._flux_visibility_map = {
            "Surface (x=0)": ("line_J_surface", "line_cum_surface"),
            "Target interface": ("line_J_target", "line_cum_target"),
            "Exit (x=L)": ("line_J_exit", "line_cum_exit"),
            "Probe (custom)": ("line_J_probe", "line_cum_probe"),
        }

        self.time_label = ttk.Label(self.frm_right, text="Time [s]: 0.0")
        self.time_label.pack(fill=tk.X, pady=(8, 0))
        self.sld_time = tk.Scale(
            self.frm_right,
            from_=0,
            to=0,
            orient=tk.HORIZONTAL,
            resolution=1,
            showvalue=False,
            command=self._on_time_slider,
            state="disabled",
        )
        self.sld_time.pack(fill=tk.X)

        time_ctrl = ttk.Frame(self.frm_right)
        time_ctrl.pack(fill=tk.X, pady=(4, 6))
        self.btn_time_prev = ttk.Button(time_ctrl, text="◀", width=3, command=lambda: self._step_time(-1), state="disabled")
        self.btn_time_prev.pack(side=tk.LEFT, padx=2)

        self.time_spin_var = tk.StringVar(value="0")
        self.spn_time = ttk.Spinbox(
            time_ctrl,
            from_=0,
            to=0,
            textvariable=self.time_spin_var,
            width=8,
            justify="center",
            state="disabled",
            wrap=False,
            command=self._on_spinbox_change,
        )
        self.spn_time.pack(side=tk.LEFT, expand=True, fill=tk.X)
        self.spn_time.bind("<Return>", self._on_spinbox_event)

        self.btn_time_next = ttk.Button(time_ctrl, text="▶", width=3, command=lambda: self._step_time(1), state="disabled")
        self.btn_time_next.pack(side=tk.LEFT, padx=2)

    def _refresh_probe_layers(self) -> None:
        if not hasattr(self, "probe_layer"):
            return
        names = self.layer_table.get_layer_names()
        self.probe_layer["values"] = names
        current = self.probe_layer.get()
        if names:
            if current not in names:
                self.probe_layer.set(names[0])
        else:
            self.probe_layer.set("")

    def _build_inputs(self, parent: tk.Widget) -> None:
        defaults = Defaults()

        self.vars = {
            "Cs": tk.DoubleVar(value=defaults.Cs),
            "dt": tk.DoubleVar(value=defaults.dt),
            "t_max": tk.DoubleVar(value=defaults.t_max),
        }

        for label, key in [
            ("Surface concentration Cs [mol/m^3]", "Cs"),
            ("Time step Δt [s]", "dt"),
            ("Total time t_max [s]", "t_max"),
        ]:
            frm = ttk.Frame(parent)
            frm.pack(fill=tk.X, pady=2)
            ttk.Label(frm, text=label).pack(anchor=tk.W)
            ttk.Entry(frm, textvariable=self.vars[key], width=18).pack(fill=tk.X)

        ttk.Label(parent, text="Right boundary condition").pack(anchor=tk.W, pady=(6, 0))
        self.bc_right = tk.StringVar(value=defaults.bc_right)
        self.cmb_bc = ttk.Combobox(
            parent,
            textvariable=self.bc_right,
            values=["Dirichlet", "Neumann"],
            state="readonly",
        )
        self.cmb_bc.pack(fill=tk.X, pady=2)

        ttk.Label(parent, text="Layers (top to bottom)").pack(anchor=tk.W, pady=(8, 0))
        self.layer_table = LayerTable(parent, list(defaults.layers), on_layers_changed=self._refresh_probe_layers)
        self.layer_table.pack(fill=tk.BOTH, expand=True, pady=4)

        btn_bar = ttk.Frame(parent)
        btn_bar.pack(fill=tk.X, pady=(8, 0))
        self.btn_run = ttk.Button(btn_bar, text="Run Simulation", command=self._on_run)
        self.btn_run.pack(fill=tk.X)

        self.progress_bar = ttk.Progressbar(parent, variable=self._progress_value, maximum=100.0)
        self.progress_bar.pack(fill=tk.X, pady=(8, 0))

        self.btn_export_flux = ttk.Button(parent, text="Export Flux CSV", command=self._export_flux)
        self.btn_export_flux.pack(fill=tk.X, pady=(6, 0))
        self.btn_export_profile = ttk.Button(parent, text="Export Current Profile CSV", command=self._export_profile)
        self.btn_export_profile.pack(fill=tk.X, pady=(4, 0))

        self.btn_manual = ttk.Button(parent, text="View Manual", command=self._show_manual)
        self.btn_manual.pack(fill=tk.X, pady=(6, 0))

        ttk.Label(
            parent,
            text=CONSTRAINTS_TEXT,
            foreground="gray25",
            justify=tk.LEFT,
            wraplength=260,
        ).pack(fill=tk.X, pady=(6, 0))

        probe_frame = ttk.Labelframe(parent, text="Flux probe (optional)")
        probe_frame.pack(fill=tk.X, pady=(8, 0))

        row0 = ttk.Frame(probe_frame)
        row0.pack(fill=tk.X, pady=2)
        ttk.Label(row0, text="Position [m]").pack(side=tk.LEFT, padx=2)
        self.probe_var = tk.StringVar(value="")
        ttk.Entry(row0, textvariable=self.probe_var, width=14).pack(side=tk.LEFT, padx=2)
        ttk.Button(row0, text="Plot", command=self._on_probe_update).pack(side=tk.LEFT, padx=4)

        row1 = ttk.Frame(probe_frame)
        row1.pack(fill=tk.X, pady=2)
        ttk.Label(row1, text="Layer").pack(side=tk.LEFT, padx=2)
        self.probe_layer = ttk.Combobox(row1, state="readonly", width=18)
        self.probe_layer.pack(side=tk.LEFT, padx=2)
        ttk.Button(row1, text="Plot layer center", command=self._on_probe_layer).pack(side=tk.LEFT, padx=4)
        self._refresh_probe_layers()

        flux_select = ttk.Frame(parent)
        flux_select.pack(fill=tk.X, pady=(10, 0))
        ttk.Label(flux_select, text="Flux view").pack(side=tk.LEFT, padx=2)
        self.cmb_flux = ttk.Combobox(
            flux_select,
            textvariable=self.selected_flux,
            state="readonly",
            values=[
                "Surface (x=0)",
                "Target interface",
                "Exit (x=L)",
                "Probe (custom)",
            ],
            width=18,
        )
        self.cmb_flux.pack(side=tk.LEFT, padx=4)
        self.cmb_flux.bind("<<ComboboxSelected>>", lambda _event: self._on_flux_selection())

        self.flux_value_label = ttk.Label(parent, text="Flux: -, Cum: -", foreground="gray25", justify=tk.LEFT, wraplength=260)
        self.flux_value_label.pack(fill=tk.X, pady=(4, 0))
        self._update_flux_value_label()

    def _gather_params(self) -> Optional[SimParams]:
        try:
            layers = self.layer_table.get_layers()
            probe_position = None
            probe_text = self.probe_var.get().strip()
            if probe_text:
                probe_position = float(probe_text)
                if probe_position < 0:
                    raise ValueError("Probe position must be non-negative.")
            params = SimParams(
                layers=layers,
                Cs=self.vars["Cs"].get(),
                dt=self.vars["dt"].get(),
                t_max=self.vars["t_max"].get(),
                bc_right=self.bc_right.get(),
                probe_position=probe_position,
            )
            validate_params(params)
        except ValueError as exc:
            messagebox.showerror(
                "Invalid parameters",
                f"{exc}\n\n{CONSTRAINTS_TEXT}",
                parent=self,
            )
            return None
        if params.dt >= params.t_max:
            messagebox.showerror(
                "Invalid parameters",
                "Time step Δt must be smaller than total time t_max.\n\n" + CONSTRAINTS_TEXT,
                parent=self,
            )
            return None
        return params

    def _on_run(self) -> None:
        params = self._gather_params()
        if not params:
            self._progress_value.set(0.0)
            return

        self.btn_run.configure(state=tk.DISABLED)
        self.last_params = params
        self._progress_value.set(0.0)

        def worker() -> None:
            try:
                res = run_simulation(params, progress_callback=self._report_progress)
                self.results = res
                residual, rel_error = mass_balance_diagnostics(
                    res["k_profile"],
                    res["t"],
                    res["x"],
                    res["C_xt"],
                    res["J_source"],
                    res["J_end"],
                )
                if rel_error > 0.01:
                    self.after(
                        0,
                        lambda: messagebox.showwarning(
                            "Mass balance warning",
                            f"Residual {residual:.3e}, relative error {rel_error:.2%}",
                            parent=self,
                        ),
                    )
                self.after(0, self._update_plots)
                self.after(0, lambda: self._progress_value.set(100.0))
                self.after(0, lambda res=res: self._show_completion_dialog(res))
            except Exception as exc:  # pragma: no cover - GUI path
                self.after(0, lambda: messagebox.showerror("Simulation error", str(exc), parent=self))
                self.after(0, lambda: self._progress_value.set(0.0))
            finally:
                self.after(0, lambda: self.btn_run.configure(state=tk.NORMAL))

        threading.Thread(target=worker, daemon=True).start()

    def _update_plots(self) -> None:
        if not self.results:
            return
        r = self.results
        self._refresh_probe_layers()
        self._configure_time_controls(len(r["t"]) - 1)
        self._set_time_index(0)
        probe_text = self.probe_var.get().strip()
        if probe_text:
            try:
                position = float(probe_text)
                self._compute_probe_flux(position)
            except ValueError:
                pass
        self._refresh_flux_plot()

    def _report_progress(self, value: float) -> None:
        def update() -> None:
            clamped = max(0.0, min(100.0, value * 100.0))
            self._progress_value.set(clamped)

        self.after(0, update)

    def _refresh_flux_plot(self) -> None:
        if not self.results:
            return
        r = self.results
        update_flux_axes(
            self.artists,
            r["t"],
            r["J_source"],
            r["J_target"],
            r["J_end"],
            r["cum_source"],
            r["cum_target"],
            r["cum_end"],
            r["mass_target"],
            J_probe=r.get("J_probe"),
            cum_probe=r.get("cum_probe"),
        )
        self._apply_flux_visibility()
        self._autoscale_flux_axes()
        self._update_flux_value_label()
        self.canvas.draw_idle()

    def _on_flux_selection(self) -> None:
        self._apply_flux_visibility()
        self._autoscale_flux_axes()
        self._update_flux_value_label()

    def _apply_flux_visibility(self) -> None:
        selection = self.selected_flux.get()
        flux_key, cum_key = self._flux_visibility_map.get(selection, (None, None))

        for key in ["line_J_surface", "line_J_target", "line_J_exit", "line_J_probe"]:
            line = self.artists[key]
            visible = key == flux_key and len(line.get_xdata()) > 0
            line.set_visible(visible)

        for key in ["line_cum_surface", "line_cum_target", "line_cum_exit", "line_cum_probe"]:
            line = self.artists[key]
            visible = key == cum_key and len(line.get_xdata()) > 0
            line.set_visible(visible)

        self.artists["line_mass_target"].set_visible(selection == "Target interface")
        self._update_flux_legend()

    def _update_flux_value_label(self) -> None:
        if not hasattr(self, "flux_value_label"):
            return
        if not self.results:
            self.flux_value_label.configure(text="Flux: -, Cum: -")
            return

        mapping = {
            "Surface (x=0)": ("J_source", "cum_source"),
            "Target interface": ("J_target", "cum_target"),
            "Exit (x=L)": ("J_end", "cum_end"),
            "Probe (custom)": ("J_probe", "cum_probe"),
        }
        flux_key, cum_key = mapping.get(self.selected_flux.get(), (None, None))
        idx = min(self._current_time_index, len(self.results["t"]) - 1)

        def _value(arr_key):
            if not arr_key:
                return None
            arr = self.results.get(arr_key)
            if arr is None or len(arr) <= idx:
                return None
            return float(arr[idx])

        flux_val = _value(flux_key)
        cum_val = _value(cum_key)
        mass_val = _value("mass_target") if self.selected_flux.get() == "Target interface" else None

        flux_txt = "Flux: -" if flux_val is None else f"Flux: {flux_val:.6e} mol/(m^2·s)"
        cum_txt = "Cum: -" if cum_val is None else f"Cum: {cum_val:.6e} mol/m^2"
        mass_txt = "" if mass_val is None else f" | Mass target: {mass_val:.6e} mol/m^2"

        self.flux_value_label.configure(text=f"{flux_txt}, {cum_txt}{mass_txt}")

    def _update_flux_legend(self) -> None:
        legend = self.artists.get("ax_flux_legend")
        if legend is not None:
            legend.remove()

        ax = self.artists["ax_flux"]
        line_keys = self.artists.get("flux_line_keys", []) + self.artists.get("flux_cum_keys", [])
        lines = []
        labels = []
        for key in line_keys:
            line = self.artists.get(key)
            if line is None:
                continue
            if line.get_visible() and len(line.get_xdata()) > 0:
                lines.append(line)
                labels.append(line.get_label())

        if lines:
            legend = ax.legend(lines, labels, loc="best")
            self.artists["ax_flux_legend"] = legend
        else:
            self.artists["ax_flux_legend"] = None

    def _autoscale_flux_axes(self) -> None:
        if not self.results:
            return
        t = self.results["t"]
        if t.size == 0:
            return

        ax_flux = self.artists["ax_flux"]
        ax_flux_secondary = self.artists["ax_flux_secondary"]
        ax_flux.set_xlim(t[0], t[-1])
        ax_flux_secondary.set_xlim(t[0], t[-1])

        def _autoscale_axis(axis, keys):
            ys = []
            for key in keys:
                line = self.artists.get(key)
                if line is None or not line.get_visible():
                    continue
                data = line.get_ydata()
                if len(data):
                    ys.append(data)
            if ys:
                ymin = min(float(np.min(arr)) for arr in ys)
                ymax = max(float(np.max(arr)) for arr in ys)
                if not np.isfinite(ymin) or not np.isfinite(ymax):
                    return
                if ymin == ymax:
                    margin = abs(ymin) * 0.05 + 1e-9
                    ymin -= margin
                    ymax += margin
                axis.set_ylim(ymin, ymax)

        flux_keys = self.artists.get("flux_line_keys", [])
        cum_keys = self.artists.get("flux_cum_keys", [])
        _autoscale_axis(ax_flux, flux_keys)
        _autoscale_axis(ax_flux_secondary, cum_keys)

    def _show_completion_dialog(self, result: dict) -> None:
        msg = "Simulation complete."
        if self.last_params:
            passive_heavy = [
                layer.name or f"Layer {idx+1}"
                for idx, layer in enumerate(self.last_params.layers[:-1])
                if layer.reaction_rate == 0.0 and layer.nodes > 10
            ]
            if passive_heavy:
                msg += (
                    "\n\nConsider reducing node counts for passive layers (k = 0) to save memory: "
                    + ", ".join(passive_heavy)
                )
        messagebox.showinfo("Simulation", msg, parent=self)

    def _on_time_change(self) -> None:
        if not self.results:
            return
        idx = self._current_time_index
        r = self.results
        t_val = float(r["t"][idx])
        update_profile_axes(self.artists, r["x"], r["C_xt"][idx], r["layer_boundaries"])
        self.time_label.configure(text=f"Time [s]: {t_val:.6g}")
        self._update_flux_value_label()
        self.canvas.draw_idle()

    def _export_profile(self) -> None:
        if not self.results:
            messagebox.showinfo("Export", "No results to export.", parent=self)
            return
        idx = self._current_time_index
        r = self.results
        base = ensure_results_dir(RESULTS_DIR)
        save_csv_profile(base, r["x"], r["C_xt"][idx], float(r["t"][idx]))
        messagebox.showinfo("Export", f"Profile saved at t={r['t'][idx]:.6g}s", parent=self)

    def _configure_time_controls(self, max_index: int) -> None:
        self._max_time_index = max(0, max_index)
        has_series = self._max_time_index > 0
        self.sld_time.configure(from_=0, to=self._max_time_index)
        self.sld_time.configure(state="normal" if has_series else "disabled")
        self.btn_time_prev.configure(state="normal" if has_series else "disabled")
        self.btn_time_next.configure(state="normal" if has_series else "disabled")
        self.spn_time.configure(state="normal" if has_series else "disabled", to=self._max_time_index)
        self._current_time_index = 0
        self.time_spin_var.set("0")

    def _set_time_index(self, idx: int, source: Optional[str] = None) -> None:
        if not self.results:
            return
        idx = max(0, min(idx, self._max_time_index))
        if idx == self._current_time_index and source is not None:
            return
        self._current_time_index = idx
        if source != "slider":
            self._suppress_time_callback = True
            self.sld_time.set(idx)
            self._suppress_time_callback = False
        if source != "spinbox":
            self._suppress_time_callback = True
            self.time_spin_var.set(str(idx))
            self._suppress_time_callback = False
        self._on_time_change()

    def _on_time_slider(self, value: str) -> None:
        if self._suppress_time_callback:
            return
        try:
            idx = int(round(float(value)))
        except (TypeError, ValueError):
            return
        self._set_time_index(idx, source="slider")

    def _on_spinbox_change(self) -> None:
        if self._suppress_time_callback:
            return
        try:
            idx = int(float(self.time_spin_var.get()))
        except ValueError:
            return
        self._set_time_index(idx, source="spinbox")

    def _on_spinbox_event(self, _event: object) -> None:
        self._on_spinbox_change()

    def _step_time(self, delta: int) -> None:
        if not self.results:
            return
        self._set_time_index(self._current_time_index + delta)

    def _on_probe_update(self) -> None:
        if not self.results:
            messagebox.showinfo("Flux probe", "Run a simulation first.", parent=self)
            return
        text = self.probe_var.get().strip()
        if not text:
            self.results.pop("J_probe", None)
            self.results.pop("cum_probe", None)
            self.results.pop("probe_position", None)
            if self.selected_flux.get() == "Probe (custom)":
                self.selected_flux.set("Target interface")
            self._refresh_flux_plot()
            return
        try:
            position = float(text)
        except ValueError:
            messagebox.showerror("Flux probe", "Provide a numeric position in meters.", parent=self)
            return
        if position < 0:
            messagebox.showerror("Flux probe", "Position must be within the stack (≥ 0).", parent=self)
            return
        if not self._compute_probe_flux(position):
            return
        self._refresh_flux_plot()

    def _compute_probe_flux(self, position: float) -> bool:
        if not self.results:
            return False
        r = self.results
        x = r["x"]
        if position > x[-1]:
            messagebox.showerror(
                "Flux probe",
                f"Position exceeds stack length ({x[-1]:.6g} m).",
                parent=self,
            )
            return False
        if position == x[-1]:
            messagebox.showinfo(
                "Flux probe",
                "Probe coincides with the stack exit; use J_end instead.",
                parent=self,
            )
            return False

        idx = int(np.searchsorted(x, position, side="left"))
        if idx == 0:
            interval = 0
        else:
            if np.isclose(position, x[idx]):
                interval = idx - 1
            else:
                interval = idx - 1
        interval = max(0, min(interval, len(x) - 2))

        dx = x[interval + 1] - x[interval]
        if dx <= 0:
            messagebox.showerror("Flux probe", "Degenerate interval encountered.", parent=self)
            return False

        D_edges = r.get("D_edges")
        if D_edges is None:
            messagebox.showerror("Flux probe", "Diffusivity data unavailable for probe computation.", parent=self)
            return False

        C_xt = r["C_xt"]
        gradient = (C_xt[:, interval + 1] - C_xt[:, interval]) / dx
        J_probe = -D_edges[interval] * gradient
        cum_probe = cumulative_trapz(J_probe, r["t"]) if len(r["t"]) > 1 else np.zeros_like(J_probe)

        self.results["J_probe"] = J_probe
        self.results["cum_probe"] = cum_probe
        self.results["probe_position"] = position
        if self.selected_flux.get() != "Probe (custom)":
            self.selected_flux.set("Probe (custom)")
        return True

    def _on_probe_layer(self) -> None:
        if not self.results:
            messagebox.showinfo("Flux probe", "Run a simulation first.", parent=self)
            return
        name = self.probe_layer.get().strip()
        if not name:
            messagebox.showinfo("Flux probe", "Select a layer name.", parent=self)
            return
        layer_names = self.results.get("layer_names")
        boundaries = self.results.get("layer_boundaries")
        if layer_names is None or boundaries is None:
            messagebox.showerror("Flux probe", "Layer boundary data unavailable.", parent=self)
            return
        if name not in layer_names:
            messagebox.showerror("Flux probe", f"Layer '{name}' not found in results.", parent=self)
            return
        idx = layer_names.index(name)
        start = boundaries[idx]
        end = boundaries[idx + 1]
        midpoint = 0.5 * (start + end)
        self.probe_var.set(f"{midpoint:.6g}")
        if self._compute_probe_flux(midpoint):
            self._refresh_flux_plot()

    def _show_manual(self) -> None:
        if self._manual_window is not None:
            try:
                self._manual_window.deiconify()
                self._manual_window.lift()
                return
            except tk.TclError:
                self._manual_window = None

        win = tk.Toplevel(self)
        win.title("User Manual")
        win.geometry("820x640")
        win.transient(self)
        win.grab_set()
        win.protocol("WM_DELETE_WINDOW", lambda: self._close_manual(win))
        self._manual_window = win

        notebook = ttk.Notebook(win)
        notebook.pack(fill=tk.BOTH, expand=True)

        frame_overview = ttk.Frame(notebook, padding=10)
        notebook.add(frame_overview, text="Overview")

        if _HTML_AVAILABLE:
            html = HTMLLabel(frame_overview, html=MANUAL_HTML, background="white")
            html.pack(fill=tk.BOTH, expand=True)
        else:
            txt = scrolledtext.ScrolledText(frame_overview, wrap="word")
            txt.pack(fill=tk.BOTH, expand=True)
            txt.insert("1.0", self._manual_text_fallback())
            txt.configure(state="disabled")

        frame_equation = ttk.Frame(notebook, padding=10)
        notebook.add(frame_equation, text="Equations")
        self._populate_equation_panel(frame_equation)

    def _close_manual(self, window: tk.Toplevel) -> None:
        try:
            window.grab_release()
        except tk.TclError:
            pass
        window.destroy()
        if self._manual_window is window:
            self._manual_window = None

    def _manual_text_fallback(self) -> str:
        return textwrap.dedent("""
Diffusion–Reaction Simulator

Governing equation:
  ∂C/∂t = ∂/∂x ( D(x) ∂C/∂x ) − k(x) C

Input constraints:
  • At least one layer (final row is the reporting layer).
  • Thickness > 0, diffusivity > 0, reaction rate ≥ 0, nodes ≥ 2.
  • Cs ≥ 0, Δt > 0, and Δt < t_max.

Usage:
  • Configure layers (top→bottom) with thickness, diffusivity, reaction rate, nodes.
  • Use Arrhenius helper (T, D0, Ea) if you want D computed automatically.
  • Choose right boundary (Dirichlet sink or Neumann impermeable).
  • Run the simulation and inspect flux, cumulative uptake, and profiles.
  • Use the Flux view dropdown to focus on surface/target/exit/probe curves.
  • Export flux histories (CSV/NPZ), the concentration matrix, or a single profile.

Key metrics:
  • Flux @ surface, Flux into reporting interface, Flux @ exit, Flux @ probe
  • Cumulated flux for each location
  • Mass in reporting layer = ∫_{reporting} C(x,t) dx
""")


    def _populate_equation_panel(self, parent: tk.Widget) -> None:
        fig = Figure(figsize=(6.5, 3.0), dpi=100)
        ax = fig.add_subplot(111)
        ax.axis("off")
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)

        ax.text(
            0.5,
            0.75,
            r"$\frac{\partial C}{\partial t} = \frac{\partial}{\partial x}\left(D(x)\,\frac{\partial C}{\partial x}\right) - k(x)C$",
            ha="center",
            va="center",
            fontsize=14,
        )

        ax.text(
            0.5,
            0.45,
            r"$J = -D(x) \frac{\partial C}{\partial x}$",
            ha="center",
            va="center",
            fontsize=13,
        )

        ax.text(
            0.02,
            0.2,
            "• Crank–Nicolson time stepping (implicit midpoint)\n"
            "• Piecewise-constant D(x), k(x) per layer\n"
            "• Continuity of C and J enforced at interfaces",
            ha="left",
            va="center",
            fontsize=11,
        )

        canvas = FigureCanvasTkAgg(fig, master=parent)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def _on_close(self) -> None:
        try:
            if self._manual_window is not None:
                self._manual_window.destroy()
        except tk.TclError:
            pass
        self.destroy()
        self.quit()

    def _export_flux(self) -> None:
        if not self.results:
            messagebox.showinfo("Export", "No results to export.", parent=self)
            return
        r = self.results
        base = ensure_results_dir(RESULTS_DIR)
        save_results_npz(
            base,
            t=r["t"],
            x=r["x"],
            C_xt=r["C_xt"],
            J_source=r["J_source"],
            J_target=r["J_target"],
            J_end=r["J_end"],
            cum_source=r["cum_source"],
            cum_target=r["cum_target"],
            cum_end=r["cum_end"],
            mass_target=r["mass_target"],
            layer_boundaries=r["layer_boundaries"],
            D_nodes=r.get("D_nodes"),
            D_edges=r.get("D_edges"),
            J_probe=r.get("J_probe"),
            cum_probe=r.get("cum_probe"),
            probe_position=r.get("probe_position"),
        )
        save_csv_flux(
            base,
            r["t"],
            r["J_source"],
            r["J_target"],
            r["J_end"],
            r["cum_source"],
            r["cum_target"],
            r["cum_end"],
            r["mass_target"],
            J_probe=r.get("J_probe"),
            cum_probe=r.get("cum_probe"),
        )
        save_profiles_matrix(base, r["x"], r["t"], r["C_xt"])
        if self.last_params:
            save_metadata(
                base,
                self.last_params,
                extras={"layer_boundaries": r["layer_boundaries"].tolist()},
            )
        messagebox.showinfo(
            "Export",
            "Saved results.npz, flux_vs_time.csv, and concentration_profiles.csv",
            parent=self,
        )
