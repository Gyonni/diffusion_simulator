from __future__ import annotations

import threading
import tkinter as tk
from tkinter import messagebox, ttk
from typing import List, Optional

from tkinter import scrolledtext

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
  <li>Export flux histories (CSV/NPZ) or the current profile (CSV) via the buttons on the left.</li>
</ol>

<h2>Input Constraints</h2>
<ul>
  <li>At least one layer; final layer is the absorbing target.</li>
  <li>Layer thickness &gt; 0, diffusivity &gt; 0, reaction rate ≥ 0, nodes ≥ 2.</li>
  <li>Surface concentration C<sub>s</sub> ≥ 0.</li>
  <li>Δt &gt; 0 and less than t<sub>max</sub>. Very large Δt will be reduced automatically.</li>
</ul>

<h2>Key Quantities</h2>
<ul>
  <li><strong>J<sub>source</sub></strong> = −D&nbsp;∂C/∂x at x = 0</li>
  <li><strong>J<sub>target</sub></strong>: flux across the final interface</li>
  <li><strong>mass<sub>target</sub></strong>(t) = ∫<sub>target</sub> C(x,t) dx</li>
  <li><strong>ℓ</strong> = √(D/k) reported for the target layer; ensure ℓ/Δx ≥ 10 for accuracy.</li>
</ul>

<h2>Tips</h2>
<ul>
  <li>Δt is automatically capped using the smallest (Δx)²/D to reduce boundary oscillations.</li>
  <li>Use minimal node counts for passive layers (k = 0) to save memory; the target layer needs finer resolution.</li>
  <li>Use the CLI (<code>python -m diffreact_gui.main --cli --debug</code>) for quick batch runs.</li>
</ul>
"""

CONSTRAINTS_TEXT = (
    "Input requirements:\n"
    "  • At least one layer (last row is the target).\n"
    "  • Thickness > 0, diffusivity > 0, reaction rate ≥ 0, nodes ≥ 2.\n"
    "  • Surface concentration Cs ≥ 0.\n"
    "  • Δt > 0 and Δt < t_max.\n"
)

from .config import Defaults, RESULTS_DIR
from .models import LayerParam, SimParams
from .plots import create_figures, update_flux_axes, update_profile_axes
from .solver import mass_balance_diagnostics, run_simulation
from .utils import (
    ensure_results_dir,
    save_csv_flux,
    save_csv_profile,
    save_metadata,
    save_results_npz,
    validate_params,
)


class LayerTable(ttk.Frame):
    """A small widget to manage multilayer parameter entries."""

    columns = ("name", "thickness", "diffusivity", "reaction", "nodes")

    def __init__(self, master: tk.Widget, layers: List[LayerParam]) -> None:
        super().__init__(master)

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

        btn_bar = ttk.Frame(self)
        btn_bar.pack(fill=tk.X, pady=4)
        ttk.Button(btn_bar, text="Add", command=self._add).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_bar, text="Update", command=self._update).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_bar, text="Remove", command=self._remove).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_bar, text="↑", width=3, command=lambda: self._move(-1)).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_bar, text="↓", width=3, command=lambda: self._move(1)).pack(side=tk.LEFT, padx=2)

        ttk.Label(
            self,
            text="* 마지막 행이 흡수 물질 (Target Layer) 입니다.",
            foreground="gray",
        ).pack(anchor=tk.W, pady=(2, 0))

        for layer in layers:
            self._insert_layer(layer)
        if layers:
            first_id = self.tree.get_children()[0]
            self.tree.selection_set(first_id)
            self.tree.focus(first_id)
            self._on_select()

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

    def _remove(self) -> None:
        item = self._selected_item()
        if not item:
            return
        self.tree.delete(item)

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
        self.layer_table = LayerTable(parent, list(defaults.layers))
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

    def _gather_params(self) -> Optional[SimParams]:
        try:
            layers = self.layer_table.get_layers()
            params = SimParams(
                layers=layers,
                Cs=self.vars["Cs"].get(),
                dt=self.vars["dt"].get(),
                t_max=self.vars["t_max"].get(),
                bc_right=self.bc_right.get(),
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
        update_flux_axes(
            self.artists,
            r["t"],
            r["J_source"],
            r["J_target"],
            r["J_end"],
            r["cum_target"],
            r["mass_target"],
        )
        self._configure_time_controls(len(r["t"]) - 1)
        self._set_time_index(0)
        self.canvas.draw_idle()

    def _report_progress(self, value: float) -> None:
        def update() -> None:
            clamped = max(0.0, min(100.0, value * 100.0))
            self._progress_value.set(clamped)

        self.after(0, update)

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
        return (
            "Diffusion–Reaction Simulator\n\n"
            "Governing equation:\n"
            "  ∂C/∂t = ∂/∂x ( D(x) ∂C/∂x ) − k(x) C\n\n"
            "Input constraints:\n"
            "  • At least one layer (final layer is the absorbing target).\n"
            "  • Thickness > 0, diffusivity > 0, reaction rate ≥ 0, nodes ≥ 2.\n"
            "  • Cs ≥ 0, Δt > 0, and Δt < t_max.\n\n"
            "Usage:\n"
            "  • Configure layers (top→bottom) with thickness, diffusivity, reaction rate, nodes.\n"
            "  • Set surface concentration Cs, Δt, and total time.\n"
            "  • Choose right boundary (Dirichlet sink or Neumann impermeable).\n"
            "  • Run the simulation and inspect flux, cumulative uptake, and profiles.\n"
            "  • Export flux histories (CSV/NPZ) or the current profile (CSV).\n\n"
            "Key fluxes:\n"
            "  J_source = −D ∂C/∂x |_(x=0)\n"
            "  J_target = flux into the final layer\n"
            "  mass_target(t) = ∫_{target} C(x,t) dx\n"
        )

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
        )
        if self.last_params:
            save_metadata(
                base,
                self.last_params,
                extras={"layer_boundaries": r["layer_boundaries"].tolist()},
            )
        messagebox.showinfo("Export", "Saved results.npz and flux_vs_time.csv", parent=self)
