from __future__ import annotations

import math
import textwrap
import threading
import tkinter as tk
from tkinter import messagebox, ttk, simpledialog
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
from .plots import create_figures, update_flux_axes, update_profile_axes, update_temperature_axes, update_c_time_axes
from .solver import mass_balance_diagnostics, run_simulation, run_temperature_sweep
from .utils import (
    cumulative_trapz,
    ensure_results_dir,
    save_csv_flux,
    save_profiles_matrix,
    save_metadata,
    save_results_npz,
    validate_params,
    load_materials_library,
    add_material_to_library,
    save_temperature_sweep_excel,
)


class MaterialLibraryDialog(tk.Toplevel):
    """Dialog for browsing and selecting materials from library."""

    def __init__(self, parent):
        super().__init__(parent)
        self.title("Material Library")
        self.geometry("500x400")
        self.transient(parent)
        self.grab_set()

        self.selected_material = None
        self.materials = load_materials_library()

        # Create UI
        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(fill="both", expand=True)

        # Left: List of materials
        left_frame = ttk.Frame(main_frame)
        left_frame.pack(side="left", fill="both", expand=True, padx=(0, 10))

        ttk.Label(left_frame, text="Available Materials:").pack(anchor="w")

        # Listbox with scrollbar
        list_frame = ttk.Frame(left_frame)
        list_frame.pack(fill="both", expand=True, pady=4)

        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side="right", fill="y")

        self.listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set)
        self.listbox.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.listbox.yview)

        # Populate listbox
        for name in sorted(self.materials.keys()):
            self.listbox.insert("end", name)

        self.listbox.bind("<<ListboxSelect>>", self._on_select)

        # Right: Material properties
        right_frame = ttk.Frame(main_frame)
        right_frame.pack(side="right", fill="both", expand=True)

        ttk.Label(right_frame, text="Material Properties:").pack(anchor="w")

        self.props_text = scrolledtext.ScrolledText(right_frame, wrap="word", height=15, width=30, state="disabled")
        self.props_text.pack(fill="both", expand=True, pady=4)

        # Buttons
        btn_frame = ttk.Frame(self, padding=10)
        btn_frame.pack(fill="x")

        ttk.Button(btn_frame, text="Apply", command=self._apply).pack(side="right", padx=2)
        ttk.Button(btn_frame, text="Delete", command=self._delete).pack(side="right", padx=2)
        ttk.Button(btn_frame, text="Cancel", command=self.destroy).pack(side="right", padx=2)

    def _on_select(self, event=None):
        """Display selected material properties."""
        selection = self.listbox.curselection()
        if not selection:
            return

        idx = selection[0]
        name = self.listbox.get(idx)
        mat = self.materials.get(name, {})

        # Format properties
        props = f"Material: {name}\n\n"
        if "D0" in mat and "Ea" in mat:
            props += f"D0:  {mat['D0']:.6g} m²/s\n"
            props += f"Ea:  {mat['Ea']:.6g} eV\n"
            props += f"\n(Arrhenius mode)\n"
        elif "diffusivity" in mat:
            props += f"D:   {mat['diffusivity']:.6g} m²/s\n"
            props += f"\n(Direct mode)\n"

        if "reaction_rate" in mat:
            props += f"\nk:   {mat['reaction_rate']:.6g} 1/s\n"

        # Display in text widget
        self.props_text.config(state="normal")
        self.props_text.delete("1.0", "end")
        self.props_text.insert("1.0", props)
        self.props_text.config(state="disabled")

    def _apply(self):
        """Apply selected material and close dialog."""
        selection = self.listbox.curselection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a material first.", parent=self)
            return

        idx = selection[0]
        self.selected_material = self.listbox.get(idx)
        self.destroy()

    def _delete(self):
        """Delete selected material from library."""
        selection = self.listbox.curselection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a material to delete.", parent=self)
            return

        idx = selection[0]
        name = self.listbox.get(idx)

        if messagebox.askyesno("Confirm Delete", f"Delete material '{name}' from library?", parent=self):
            del self.materials[name]
            from .utils import save_materials_library
            save_materials_library(self.materials)
            self.listbox.delete(idx)
            self.props_text.config(state="normal")
            self.props_text.delete("1.0", "end")
            self.props_text.config(state="disabled")
            messagebox.showinfo("Deleted", f"Material '{name}' removed from library.", parent=self)


class LayerTable(ttk.Frame):
    """A small widget to manage multilayer parameter entries."""

    columns = ("name", "thickness", "diffusivity", "Ea", "reaction", "nodes")

    def __init__(
        self,
        master: tk.Widget,
        layers: List[LayerParam],
        *,
        on_layers_changed: Optional[callable] = None,
    ) -> None:
        super().__init__(master)
        self._on_layers_changed = on_layers_changed
        self._use_arrhenius = tk.BooleanVar(value=False)
        self._layer_data: List[LayerParam] = []  # Store full LayerParam objects

        self.tree = ttk.Treeview(self, columns=self.columns, show="headings", height=6)
        for col, heading in zip(
            self.columns,
            ["Name", "Thickness [m]", "D [m^2/s]", "Ea [eV]", "k [1/s]", "Nodes"],
        ):
            self.tree.heading(col, text=heading)
            self.tree.column(col, width=100, anchor=tk.CENTER)
        self.tree.pack(fill=tk.BOTH, expand=True)

        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        # Mode selector
        mode_frame = ttk.Frame(self)
        mode_frame.pack(fill=tk.X, pady=4)
        ttk.Radiobutton(mode_frame, text="Use D directly", variable=self._use_arrhenius, value=False, command=self._toggle_input_mode).pack(side=tk.LEFT, padx=4)
        ttk.Radiobutton(mode_frame, text="Use D0 + Ea (Arrhenius)", variable=self._use_arrhenius, value=True, command=self._toggle_input_mode).pack(side=tk.LEFT, padx=4)

        self.entry_vars = {
            "name": tk.StringVar(value="Layer"),
            "thickness": tk.StringVar(value="1e-7"),
            "diffusivity": tk.StringVar(value="1e-14"),
            "D0": tk.StringVar(value="1e-6"),
            "Ea": tk.StringVar(value="1.0"),
            "reaction": tk.StringVar(value="0.0"),
            "nodes": tk.StringVar(value="101"),
        }

        form = ttk.Frame(self)
        form.pack(fill=tk.X, pady=4)

        # Common fields
        row = 0
        ttk.Label(form, text="Name").grid(row=row, column=0, sticky="w", padx=2, pady=2)
        ttk.Entry(form, textvariable=self.entry_vars["name"], width=18).grid(row=row, column=1, padx=2, pady=2)

        row += 1
        ttk.Label(form, text="Thickness [m]").grid(row=row, column=0, sticky="w", padx=2, pady=2)
        ttk.Entry(form, textvariable=self.entry_vars["thickness"], width=18).grid(row=row, column=1, padx=2, pady=2)

        row += 1
        self.lbl_diffusivity = ttk.Label(form, text="D [m^2/s]")
        self.lbl_diffusivity.grid(row=row, column=0, sticky="w", padx=2, pady=2)
        self.entry_diffusivity = ttk.Entry(form, textvariable=self.entry_vars["diffusivity"], width=18)
        self.entry_diffusivity.grid(row=row, column=1, padx=2, pady=2)

        row += 1
        self.lbl_D0 = ttk.Label(form, text="D0 [m^2/s]")
        self.lbl_D0.grid(row=row, column=0, sticky="w", padx=2, pady=2)
        self.entry_D0 = ttk.Entry(form, textvariable=self.entry_vars["D0"], width=18)
        self.entry_D0.grid(row=row, column=1, padx=2, pady=2)

        row += 1
        self.lbl_Ea = ttk.Label(form, text="Ea [eV]")
        self.lbl_Ea.grid(row=row, column=0, sticky="w", padx=2, pady=2)
        self.entry_Ea = ttk.Entry(form, textvariable=self.entry_vars["Ea"], width=18)
        self.entry_Ea.grid(row=row, column=1, padx=2, pady=2)

        row += 1
        ttk.Label(form, text="k [1/s]").grid(row=row, column=0, sticky="w", padx=2, pady=2)
        ttk.Entry(form, textvariable=self.entry_vars["reaction"], width=18).grid(row=row, column=1, padx=2, pady=2)

        row += 1
        ttk.Label(form, text="Nodes").grid(row=row, column=0, sticky="w", padx=2, pady=2)
        ttk.Entry(form, textvariable=self.entry_vars["nodes"], width=18).grid(row=row, column=1, padx=2, pady=2)

        form.grid_columnconfigure(1, weight=1)

        # Initially show D input mode
        self._toggle_input_mode()

        btn_bar = ttk.Frame(self)
        btn_bar.pack(fill=tk.X, pady=4)
        ttk.Button(btn_bar, text="Add", command=self._add).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_bar, text="Update", command=self._update).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_bar, text="Remove", command=self._remove).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_bar, text="↑", width=3, command=lambda: self._move(-1)).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_bar, text="↓", width=3, command=lambda: self._move(1)).pack(side=tk.LEFT, padx=2)

        # Material Library
        lib_frame = ttk.Labelframe(self, text="Material Library")
        lib_frame.pack(fill=tk.X, pady=4)
        lib_row1 = ttk.Frame(lib_frame)
        lib_row1.pack(fill=tk.X, padx=4, pady=2)
        ttk.Button(lib_row1, text="Save to Library", command=self._save_to_library).pack(side=tk.LEFT, padx=2)
        ttk.Button(lib_row1, text="Load from Library", command=self._load_from_library).pack(side=tk.LEFT, padx=2)

        for layer in layers:
            self._insert_layer(layer)
        if layers:
            first_id = self.tree.get_children()[0]
            self.tree.selection_set(first_id)
            self.tree.focus(first_id)
            self._on_select()
        self._notify_layers_changed()

    def _insert_layer(self, layer: LayerParam, index: Optional[int] = None) -> None:
        """Insert a layer into the tree and internal storage."""
        if index is None:
            index = len(self._layer_data)
        self._layer_data.insert(index, layer)

        # Display D0 if available, otherwise D
        display_d = f"{layer.D0:.6g}" if layer.D0 is not None else f"{layer.diffusivity:.6g}"
        suffix = " (D0)" if layer.D0 is not None else ""

        # Display Ea if available
        display_ea = f"{layer.Ea:.6g}" if layer.Ea is not None else "-"

        self.tree.insert(
            "",
            index,
            values=(
                layer.name,
                f"{layer.thickness:.6g}",
                display_d + suffix,
                display_ea,
                f"{layer.reaction_rate:.6g}",
                str(layer.nodes),
            ),
        )

    def _toggle_input_mode(self) -> None:
        """Toggle between D-only and D0+Ea input modes."""
        use_arr = self._use_arrhenius.get()
        if use_arr:
            # Hide D, show D0 and Ea
            self.lbl_diffusivity.grid_remove()
            self.entry_diffusivity.grid_remove()
            self.lbl_D0.grid()
            self.entry_D0.grid()
            self.lbl_Ea.grid()
            self.entry_Ea.grid()
        else:
            # Show D, hide D0 and Ea
            self.lbl_diffusivity.grid()
            self.entry_diffusivity.grid()
            self.lbl_D0.grid_remove()
            self.entry_D0.grid_remove()
            self.lbl_Ea.grid_remove()
            self.entry_Ea.grid_remove()

    def _on_select(self, _event: Optional[tk.Event] = None) -> None:
        item = self._selected_item()
        if not item:
            return
        idx = self.tree.index(item)
        if idx >= len(self._layer_data):
            return
        layer = self._layer_data[idx]

        # Populate form fields from stored LayerParam
        self.entry_vars["name"].set(layer.name)
        self.entry_vars["thickness"].set(f"{layer.thickness:.6g}")
        self.entry_vars["diffusivity"].set(f"{layer.diffusivity:.6g}")
        self.entry_vars["reaction"].set(f"{layer.reaction_rate:.6g}")
        self.entry_vars["nodes"].set(str(layer.nodes))

        if layer.D0 is not None and layer.Ea is not None:
            self.entry_vars["D0"].set(f"{layer.D0:.6g}")
            self.entry_vars["Ea"].set(f"{layer.Ea:.6g}")
            self._use_arrhenius.set(True)
        else:
            self._use_arrhenius.set(False)
        self._toggle_input_mode()

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
        idx = self.tree.index(item)
        try:
            layer = self._layer_from_entries()
        except ValueError as exc:
            messagebox.showerror("Invalid layer", str(exc), parent=self)
            return

        # Update internal storage
        self._layer_data[idx] = layer

        # Update tree display
        display_d = f"{layer.D0:.6g}" if layer.D0 is not None else f"{layer.diffusivity:.6g}"
        suffix = " (D0)" if layer.D0 is not None else ""
        display_ea = f"{layer.Ea:.6g}" if layer.Ea is not None else "-"
        self.tree.item(
            item,
            values=(
                layer.name,
                f"{layer.thickness:.6g}",
                display_d + suffix,
                display_ea,
                f"{layer.reaction_rate:.6g}",
                str(layer.nodes),
            ),
        )
        self._notify_layers_changed()

    def _remove(self) -> None:
        item = self._selected_item()
        if not item:
            return
        idx = self.tree.index(item)
        self._layer_data.pop(idx)
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

        # Move in internal storage
        layer = self._layer_data.pop(index)
        self._layer_data.insert(new_index, layer)

        # Move in tree
        self.tree.move(item, parent, new_index)
        self._notify_layers_changed()

    def _layer_from_entries(self) -> LayerParam:
        try:
            name = self.entry_vars["name"].get().strip() or "Layer"
            thickness = float(self.entry_vars["thickness"].get())
            reaction = float(self.entry_vars["reaction"].get())
            nodes = int(self.entry_vars["nodes"].get())
        except ValueError as exc:
            raise ValueError("Layer fields must be numeric") from exc

        if nodes < 2:
            raise ValueError("Nodes must be ≥ 2")
        if thickness <= 0:
            raise ValueError("Thickness must be positive")
        if reaction < 0:
            raise ValueError("Reaction rate must be ≥ 0")

        # Determine which mode we're in
        use_arr = self._use_arrhenius.get()
        D0_val = None
        Ea_val = None

        if use_arr:
            # Arrhenius mode: use D0 and Ea
            try:
                D0_val = float(self.entry_vars["D0"].get())
                Ea_val = float(self.entry_vars["Ea"].get())
            except ValueError as exc:
                raise ValueError("D0 and Ea must be numeric") from exc
            if D0_val <= 0:
                raise ValueError("D0 must be positive")
            # For tree display, we'll use D0 as a placeholder
            diffusivity = D0_val
        else:
            # Direct D mode
            try:
                diffusivity = float(self.entry_vars["diffusivity"].get())
            except ValueError as exc:
                raise ValueError("Diffusivity must be numeric") from exc
            if diffusivity <= 0:
                raise ValueError("Diffusivity must be positive")

        return LayerParam(
            name=name,
            thickness=thickness,
            diffusivity=diffusivity,
            reaction_rate=reaction,
            nodes=nodes,
            D0=D0_val,
            Ea=Ea_val
        )

    def get_layers(self) -> List[LayerParam]:
        """Return the list of stored LayerParam objects."""
        return list(self._layer_data)

    def get_layer_names(self) -> List[str]:
        return [layer.name for layer in self._layer_data]

    def _notify_layers_changed(self) -> None:
        if self._on_layers_changed is not None:
            self._on_layers_changed()

    def _save_to_library(self) -> None:
        """Save current entry values to material library."""
        try:
            layer = self._layer_from_entries()
        except ValueError as exc:
            messagebox.showerror("Invalid material", str(exc), parent=self)
            return

        # Ask for material name
        name = tk.simpledialog.askstring("Save Material", "Enter material name:", parent=self)
        if not name:
            return

        try:
            add_material_to_library(
                name=name,
                D0=layer.D0,
                Ea=layer.Ea,
                diffusivity=layer.diffusivity if layer.D0 is None else None,
                reaction_rate=layer.reaction_rate
            )
            messagebox.showinfo("Success", f"Material '{name}' saved to library.", parent=self)
        except Exception as exc:
            messagebox.showerror("Error", f"Failed to save material: {exc}", parent=self)

    def _load_from_library(self) -> None:
        """Load material properties from library using dialog."""
        materials = load_materials_library()
        if not materials:
            messagebox.showinfo("Empty Library", "No materials found in library.", parent=self)
            return

        # Show material library dialog
        dialog = MaterialLibraryDialog(self)
        self.wait_window(dialog)

        # Check if a material was selected
        if dialog.selected_material:
            name = dialog.selected_material
            mat = materials[name]

            # Apply to entry fields
            if "D0" in mat and "Ea" in mat:
                self.entry_vars["D0"].set(f"{mat['D0']:.6g}")
                self.entry_vars["Ea"].set(f"{mat['Ea']:.6g}")
                self._use_arrhenius.set(True)
            elif "diffusivity" in mat:
                self.entry_vars["diffusivity"].set(f"{mat['diffusivity']:.6g}")
                self._use_arrhenius.set(False)

            if "reaction_rate" in mat:
                self.entry_vars["reaction"].set(f"{mat['reaction_rate']:.6g}")

            self._toggle_input_mode()
            messagebox.showinfo("Success", f"Material '{name}' loaded from library.", parent=self)


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Multilayer Diffusion–Reaction Simulator")
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self.results: Optional[dict] = None
        self.last_params: Optional[SimParams] = None
        self.is_temperature_sweep: bool = False
        self._current_time_index = 0
        self._max_time_index = 0
        self._suppress_time_callback = False
        self._progress_value = tk.DoubleVar(value=0.0)
        self._manual_window: Optional[tk.Toplevel] = None
        self.selected_flux = tk.StringVar(value="Target interface")
        self._abort_event = threading.Event()
        self._simulation_thread: Optional[threading.Thread] = None

        # Main container with PanedWindow for resizable panels
        self.paned_window = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        self.paned_window.grid(row=0, column=0, sticky="nsew")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Left panel with control buttons at top
        self.frm_left = ttk.Frame(self.paned_window, padding=6)
        self.frm_right = ttk.Frame(self.paned_window, padding=6)

        self.paned_window.add(self.frm_left, weight=0)
        self.paned_window.add(self.frm_right, weight=1)

        # Fixed control bar at top of left panel
        self.control_bar = ttk.Frame(self.frm_left)
        self.control_bar.pack(side="top", fill="x", pady=(0, 8))

        # Create symbol buttons (▶ for Run, ■ for Stop, 💾 for Save)
        self.btn_run = ttk.Button(self.control_bar, text="▶ Run", width=8, command=self._on_run)
        self.btn_run.pack(side=tk.LEFT, padx=2)

        self.btn_abort = ttk.Button(self.control_bar, text="■ Stop", width=8, command=self._on_abort, state=tk.DISABLED)
        self.btn_abort.pack(side=tk.LEFT, padx=2)

        self.btn_save = ttk.Button(self.control_bar, text="💾 Save", width=8, command=self._export_flux)
        self.btn_save.pack(side=tk.LEFT, padx=2)

        # Progress bar in control bar
        self.progress_bar = ttk.Progressbar(self.control_bar, variable=self._progress_value, maximum=100.0, length=120)
        self.progress_bar.pack(side=tk.LEFT, padx=4, fill=tk.X, expand=True)

        # Tab control for Setup / Results
        self.notebook = ttk.Notebook(self.frm_left)
        self.notebook.pack(side="top", fill="both", expand=True)

        # Setup tab (simulation parameters)
        self.setup_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.setup_frame, text="Setup")

        # Results tab (visualization controls)
        self.results_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.results_frame, text="Results")

        # Create canvas and scrollbar for setup tab
        self.canvas_setup = tk.Canvas(self.setup_frame, width=550)
        self.scrollbar_setup = ttk.Scrollbar(self.setup_frame, orient="vertical", command=self.canvas_setup.yview)
        self.scrollable_setup = ttk.Frame(self.canvas_setup)

        self.scrollable_setup.bind(
            "<Configure>",
            lambda e: self.canvas_setup.configure(scrollregion=self.canvas_setup.bbox("all"))
        )

        self.canvas_setup.create_window((0, 0), window=self.scrollable_setup, anchor="nw")
        self.canvas_setup.configure(yscrollcommand=self.scrollbar_setup.set)

        # Mouse wheel scrolling for setup tab
        def _on_mousewheel_setup(event):
            self.canvas_setup.yview_scroll(int(-1*(event.delta/120)), "units")
        self.canvas_setup.bind_all("<MouseWheel>", _on_mousewheel_setup)

        self.canvas_setup.pack(side="left", fill="both", expand=True)
        self.scrollbar_setup.pack(side="right", fill="y")

        # Create canvas and scrollbar for results tab
        self.canvas_results = tk.Canvas(self.results_frame, width=550)
        self.scrollbar_results = ttk.Scrollbar(self.results_frame, orient="vertical", command=self.canvas_results.yview)
        self.scrollable_results = ttk.Frame(self.canvas_results)

        self.scrollable_results.bind(
            "<Configure>",
            lambda e: self.canvas_results.configure(scrollregion=self.canvas_results.bbox("all"))
        )

        self.canvas_results.create_window((0, 0), window=self.scrollable_results, anchor="nw")
        self.canvas_results.configure(yscrollcommand=self.scrollbar_results.set)

        # Mouse wheel scrolling for results tab
        def _on_mousewheel_results(event):
            self.canvas_results.yview_scroll(int(-1*(event.delta/120)), "units")
        self.canvas_results.bind_all("<MouseWheel>", _on_mousewheel_results)

        self.canvas_results.pack(side="left", fill="both", expand=True)
        self.scrollbar_results.pack(side="right", fill="y")

        # Build UI elements
        self._build_setup_tab(self.scrollable_setup)
        self._build_results_tab(self.scrollable_results)

        fig, artists = create_figures()
        self.artists = artists
        self.canvas = FigureCanvasTkAgg(fig, master=self.frm_right)
        self.canvas.draw_idle()
        # Use fill=BOTH but expand=False to prevent graph from taking all space
        # This ensures controls below remain visible
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=False)
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

    def _build_setup_tab(self, parent: tk.Widget) -> None:
        """Build the Setup tab with simulation parameters."""
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

        # Temperature sweep (optional)
        temp_frame = ttk.Labelframe(parent, text="Temperature Sweep (optional)")
        temp_frame.pack(fill=tk.X, pady=(6, 0))
        ttk.Label(temp_frame, text="Temperatures [K] (comma-separated):").pack(anchor=tk.W, padx=4, pady=2)
        self.temp_list_var = tk.StringVar(value="")
        ttk.Entry(temp_frame, textvariable=self.temp_list_var, width=18).pack(fill=tk.X, padx=4, pady=2)
        ttk.Label(temp_frame, text="Example: 300, 350, 400, 450", foreground="gray40", font=("TkDefaultFont", 8)).pack(anchor=tk.W, padx=4)

        ttk.Label(parent, text="Layers (top to bottom)").pack(anchor=tk.W, pady=(8, 0))
        self.layer_table = LayerTable(parent, list(defaults.layers), on_layers_changed=self._refresh_probe_layers)
        self.layer_table.pack(fill=tk.BOTH, expand=True, pady=4)

        self.btn_manual = ttk.Button(parent, text="View Manual", command=self._show_manual)
        self.btn_manual.pack(fill=tk.X, pady=(6, 0))

        ttk.Label(
            parent,
            text=CONSTRAINTS_TEXT,
            foreground="gray25",
            justify=tk.LEFT,
            wraplength=260,
        ).pack(fill=tk.X, pady=(6, 0))

    def _build_results_tab(self, parent: tk.Widget) -> None:
        """Build the Results tab with visualization controls organized by graph."""

        # ========== Section 1: Graph 1 - Flux & Uptake vs Time ==========
        graph1_frame = ttk.LabelFrame(parent, text="Graph 1: Flux & Uptake vs Time", padding=4)
        graph1_frame.pack(fill=tk.X, pady=(4, 0))

        # Flux probe
        probe_subframe = ttk.Frame(graph1_frame)
        probe_subframe.pack(fill=tk.X, pady=2)
        ttk.Label(probe_subframe, text="Flux probe (optional)", font=("TkDefaultFont", 9, "bold")).pack(anchor=tk.W)

        row0 = ttk.Frame(probe_subframe)
        row0.pack(fill=tk.X, pady=2)
        ttk.Label(row0, text="Position [m]").pack(side=tk.LEFT, padx=2)
        self.probe_var = tk.StringVar(value="")
        ttk.Entry(row0, textvariable=self.probe_var, width=14).pack(side=tk.LEFT, padx=2)
        ttk.Button(row0, text="Plot", command=self._on_probe_update).pack(side=tk.LEFT, padx=4)

        row1 = ttk.Frame(probe_subframe)
        row1.pack(fill=tk.X, pady=2)
        ttk.Label(row1, text="Layer").pack(side=tk.LEFT, padx=2)
        self.probe_layer = ttk.Combobox(row1, state="readonly", width=18)
        self.probe_layer.pack(side=tk.LEFT, padx=2)
        ttk.Button(row1, text="Plot layer center", command=self._on_probe_layer).pack(side=tk.LEFT, padx=4)
        self._refresh_probe_layers()

        # Flux view selector
        flux_select = ttk.Frame(graph1_frame)
        flux_select.pack(fill=tk.X, pady=(6, 2))
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

        # Temperature selection for Graph 1 (only visible for temperature sweep)
        temp_select_g1 = ttk.Frame(graph1_frame)
        temp_select_g1.pack(fill=tk.X, pady=2)
        ttk.Label(temp_select_g1, text="Temperature").pack(side=tk.LEFT, padx=2)
        self.selected_temperature = tk.StringVar()
        self.cmb_temperature = ttk.Combobox(
            temp_select_g1,
            textvariable=self.selected_temperature,
            state="readonly",
            values=[],
            width=12,
        )
        self.cmb_temperature.pack(side=tk.LEFT, padx=4)
        self.cmb_temperature.bind("<<ComboboxSelected>>", lambda _event: self._on_temperature_selection())
        # Initially hide temperature selector
        temp_select_g1.pack_forget()
        self.temp_select_frame = temp_select_g1

        # Flux value display
        self.flux_value_label = ttk.Label(graph1_frame, text="Flux: -, Cum: -", foreground="gray25", justify=tk.LEFT, wraplength=260)
        self.flux_value_label.pack(fill=tk.X, pady=(4, 0))
        self._update_flux_value_label()

        # ========== Section 2: Graph 2 - C vs Time ==========
        graph2_frame = ttk.LabelFrame(parent, text="Graph 2: Concentration vs Time", padding=4)
        graph2_frame.pack(fill=tk.X, pady=(6, 0))

        ttk.Label(graph2_frame, text="Position [m]:").pack(anchor=tk.W, padx=2, pady=2)
        self.c_time_position_var = tk.StringVar(value="")
        pos_row_g2 = ttk.Frame(graph2_frame)
        pos_row_g2.pack(fill=tk.X, padx=2, pady=2)
        ttk.Entry(pos_row_g2, textvariable=self.c_time_position_var, width=14).pack(side=tk.LEFT, padx=2)

        ttk.Label(graph2_frame, text="Temperature(s) [K, comma-separated]:").pack(anchor=tk.W, padx=2, pady=(6, 2))
        self.c_time_temps_var = tk.StringVar(value="")
        temp_row_g2 = ttk.Frame(graph2_frame)
        temp_row_g2.pack(fill=tk.X, padx=2, pady=2)
        ttk.Entry(temp_row_g2, textvariable=self.c_time_temps_var, width=14).pack(side=tk.LEFT, padx=2)
        ttk.Button(temp_row_g2, text="Update", command=self._update_c_time_plot).pack(side=tk.LEFT, padx=4)

        # ========== Section 3: Graph 3 - Concentration Profile (C vs x) ==========
        graph3_frame = ttk.LabelFrame(parent, text="Graph 3: Concentration Profile (C vs x)", padding=4)
        graph3_frame.pack(fill=tk.X, pady=(6, 0))

        ttk.Label(graph3_frame, text="Time [s]:").pack(anchor=tk.W, padx=2, pady=2)
        self.profile_time_var = tk.StringVar(value="")
        time_row_g3 = ttk.Frame(graph3_frame)
        time_row_g3.pack(fill=tk.X, padx=2, pady=2)
        ttk.Entry(time_row_g3, textvariable=self.profile_time_var, width=14).pack(side=tk.LEFT, padx=2)
        ttk.Button(time_row_g3, text="Go to time", command=self._go_to_time).pack(side=tk.LEFT, padx=4)

        # Temperature selection for Graph 3 (only visible for temperature sweep)
        temp_select_g3 = ttk.Frame(graph3_frame)
        temp_select_g3.pack(fill=tk.X, pady=(6, 2))
        ttk.Label(temp_select_g3, text="Temperature").pack(side=tk.LEFT, padx=2)
        self.selected_temperature_g3 = tk.StringVar()
        self.cmb_temperature_g3 = ttk.Combobox(
            temp_select_g3,
            textvariable=self.selected_temperature_g3,
            state="readonly",
            values=[],
            width=12,
        )
        self.cmb_temperature_g3.pack(side=tk.LEFT, padx=4)
        self.cmb_temperature_g3.bind("<<ComboboxSelected>>", lambda _event: self._on_temperature_selection_g3())
        # Initially hide temperature selector
        temp_select_g3.pack_forget()
        self.temp_select_frame_g3 = temp_select_g3

        # ========== Section 4: Graph 4 - C vs Temperature ==========
        graph4_frame = ttk.LabelFrame(parent, text="Graph 4: Concentration vs Temperature", padding=4)
        graph4_frame.pack(fill=tk.X, pady=(6, 0))

        ttk.Label(graph4_frame, text="Position [m]:").pack(anchor=tk.W, padx=2, pady=2)
        self.temp_plot_position_var = tk.StringVar(value="")
        pos_row_g4 = ttk.Frame(graph4_frame)
        pos_row_g4.pack(fill=tk.X, padx=2, pady=2)
        ttk.Entry(pos_row_g4, textvariable=self.temp_plot_position_var, width=14).pack(side=tk.LEFT, padx=2)

        ttk.Label(graph4_frame, text="Time(s) [s, comma-separated]:").pack(anchor=tk.W, padx=2, pady=(6, 2))
        self.temp_plot_times_var = tk.StringVar(value="")
        time_row_g4 = ttk.Frame(graph4_frame)
        time_row_g4.pack(fill=tk.X, padx=2, pady=2)
        ttk.Entry(time_row_g4, textvariable=self.temp_plot_times_var, width=14).pack(side=tk.LEFT, padx=2)
        ttk.Button(time_row_g4, text="Update", command=self._update_temperature_plot).pack(side=tk.LEFT, padx=4)

    def _gather_params(self) -> Optional[SimParams]:
        try:
            layers = self.layer_table.get_layers()
            probe_position = None
            probe_text = self.probe_var.get().strip()
            if probe_text:
                probe_position = float(probe_text)
                if probe_position < 0:
                    raise ValueError("Probe position must be non-negative.")

            # Parse temperature list
            temperatures = None
            temp_text = self.temp_list_var.get().strip()
            if temp_text:
                temp_strs = [s.strip() for s in temp_text.split(",")]
                temperatures = [float(t) for t in temp_strs if t]
                if any(T <= 0 for T in temperatures):
                    raise ValueError("All temperatures must be positive.")
                # Check if using D0/Ea mode when temperature sweep is requested
                if temperatures:
                    for layer in layers:
                        if layer.D0 is None or layer.Ea is None:
                            raise ValueError("Temperature sweep requires all layers to have D0 and Ea defined. Please use 'Use D0 + Ea (Arrhenius)' mode.")

            # Check if any layer is using Arrhenius mode without temperature input
            has_arrhenius = any(layer.D0 is not None and layer.Ea is not None for layer in layers)
            if has_arrhenius and not temperatures:
                raise ValueError("Arrhenius mode (D0 + Ea) requires temperature values to be specified. Please enter temperatures (comma-separated) or switch to direct diffusivity mode.")

            params = SimParams(
                layers=layers,
                Cs=self.vars["Cs"].get(),
                dt=self.vars["dt"].get(),
                t_max=self.vars["t_max"].get(),
                bc_right=self.bc_right.get(),
                probe_position=probe_position,
                temperatures=temperatures,
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
        self.btn_abort.configure(state=tk.NORMAL)
        self._abort_event.clear()
        self.last_params = params
        self._progress_value.set(0.0)

        def worker() -> None:
            try:
                # Check if temperature sweep is requested
                if params.temperatures:
                    # Run temperature sweep
                    res = run_temperature_sweep(params, progress_callback=self._report_progress, abort_event=self._abort_event)
                    if self._abort_event.is_set():
                        self.after(0, lambda: messagebox.showinfo("Aborted", "Temperature sweep was aborted by user.", parent=self))
                        self.after(0, lambda: self._progress_value.set(0.0))
                        return
                    self.results = res
                    self.is_temperature_sweep = True
                    # For temperature sweep, show the first temperature's data in plots
                    first_T = res["temperatures"][0]
                    first_result = res["results_by_temp"][first_T]
                    residual, rel_error = mass_balance_diagnostics(
                        first_result["k_profile"],
                        first_result["t"],
                        first_result["x"],
                        first_result["C_xt"],
                        first_result["J_source"],
                        first_result["J_end"],
                    )
                    if rel_error > 0.01:
                        self.after(
                            0,
                            lambda: messagebox.showwarning(
                                "Mass balance warning",
                                f"First temperature ({first_T}K): Residual {residual:.3e}, relative error {rel_error:.2%}",
                                parent=self,
                            ),
                        )
                else:
                    # Run single simulation
                    res = run_simulation(params, progress_callback=self._report_progress, abort_event=self._abort_event)
                    if self._abort_event.is_set():
                        self.after(0, lambda: messagebox.showinfo("Aborted", "Simulation was aborted by user.", parent=self))
                        self.after(0, lambda: self._progress_value.set(0.0))
                        return
                    self.results = res
                    self.is_temperature_sweep = False
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
                if not self._abort_event.is_set():
                    import traceback
                    error_details = f"{type(exc).__name__}: {str(exc)}\n\nFull traceback:\n{traceback.format_exc()}"
                    self.after(0, lambda err=error_details: self._show_error_dialog(err))
                self.after(0, lambda: self._progress_value.set(0.0))
            finally:
                self.after(0, lambda: self.btn_run.configure(state=tk.NORMAL))
                self.after(0, lambda: self.btn_abort.configure(state=tk.DISABLED))

        self._simulation_thread = threading.Thread(target=worker, daemon=True)
        self._simulation_thread.start()

    def _on_abort(self) -> None:
        """Abort the currently running simulation."""
        self._abort_event.set()
        self.btn_abort.configure(state=tk.DISABLED)

    def _update_plots(self) -> None:
        if not self.results:
            return
        r = self.results

        # Handle temperature sweep vs single simulation
        if self.is_temperature_sweep:
            # Setup temperature selector
            temps = r["temperatures"]
            temp_values = [f"{T:.1f} K" for T in temps]
            self.cmb_temperature["values"] = temp_values
            self.selected_temperature.set(temp_values[0])
            self.temp_select_frame.pack(fill=tk.X, pady=(5, 0))

            # Setup Graph 3 temperature selector (synced with Graph 1)
            self.cmb_temperature_g3["values"] = temp_values
            self.selected_temperature_g3.set(temp_values[0])
            self.temp_select_frame_g3.pack(fill=tk.X, pady=(6, 2))

            # For temperature sweep, use the first temperature's data for plotting
            first_T = temps[0]
            plot_data = r["results_by_temp"][first_T]
        else:
            # Hide temperature selectors for single simulation
            self.temp_select_frame.pack_forget()
            self.temp_select_frame_g3.pack_forget()
            plot_data = r

        self._refresh_probe_layers()
        self._configure_time_controls(len(plot_data["t"]) - 1)
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

    def _get_selected_temperature(self) -> float:
        """Get the currently selected temperature for temperature sweep mode."""
        if not self.is_temperature_sweep:
            return None
        temp_str = self.selected_temperature.get()
        if not temp_str:
            return self.results["temperatures"][0]
        # Extract temperature value from string like "300.0 K"
        return float(temp_str.replace(" K", ""))

    def _on_temperature_selection(self) -> None:
        """Handle temperature selection change."""
        if not self.results or not self.is_temperature_sweep:
            return
        # Refresh plots with newly selected temperature
        self._refresh_flux_plot()
        self._on_time_change()

    def _refresh_flux_plot(self) -> None:
        if not self.results:
            return
        r = self.results

        # Get data for plotting (handle temperature sweep)
        current_temp = None
        if self.is_temperature_sweep:
            selected_T = self._get_selected_temperature()
            current_temp = selected_T
            plot_data = r["results_by_temp"][selected_T]
        else:
            plot_data = r

        # For probe data, check main results dict (where probe data is stored)
        J_probe = r.get("J_probe")
        cum_probe = r.get("cum_probe")

        update_flux_axes(
            self.artists,
            plot_data["t"],
            plot_data["J_source"],
            plot_data["J_target"],
            plot_data["J_end"],
            plot_data["cum_source"],
            plot_data["cum_target"],
            plot_data["cum_end"],
            plot_data["mass_target"],
            J_probe=J_probe,
            cum_probe=cum_probe,
            temperature=current_temp,
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

        r = self.results

        # Get data for display (handle temperature sweep)
        if self.is_temperature_sweep:
            selected_T = self._get_selected_temperature()
            plot_data = r["results_by_temp"][selected_T]
        else:
            plot_data = r

        mapping = {
            "Surface (x=0)": ("J_source", "cum_source"),
            "Target interface": ("J_target", "cum_target"),
            "Exit (x=L)": ("J_end", "cum_end"),
            "Probe (custom)": ("J_probe", "cum_probe"),
        }
        flux_key, cum_key = mapping.get(self.selected_flux.get(), (None, None))
        idx = min(self._current_time_index, len(plot_data["t"]) - 1)

        def _value(arr_key):
            if not arr_key:
                return None
            # For probe data, check main results dict
            if arr_key in ("J_probe", "cum_probe"):
                arr = r.get(arr_key)
            else:
                arr = plot_data.get(arr_key)
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

        # Get data for plotting (handle temperature sweep)
        current_temp = None
        if self.is_temperature_sweep:
            selected_T = self._get_selected_temperature()
            current_temp = selected_T
            plot_data = r["results_by_temp"][selected_T]
        else:
            plot_data = r

        t_val = float(plot_data["t"][idx])
        update_profile_axes(self.artists, plot_data["x"], plot_data["C_xt"][idx], plot_data["layer_boundaries"], temperature=current_temp)
        self.time_label.configure(text=f"Time [s]: {t_val:.6g}")
        self._update_flux_value_label()
        self.canvas.draw_idle()

    def _update_temperature_plot(self) -> None:
        """Update the temperature vs concentration plot at the selected position and time(s)."""
        if not self.results or not self.is_temperature_sweep:
            messagebox.showinfo("No data", "Temperature plot is only available for temperature sweep simulations.", parent=self)
            return

        position_text = self.temp_plot_position_var.get().strip()
        if not position_text:
            messagebox.showwarning("Input required", "Please enter a position [m] for the temperature plot.", parent=self)
            return

        try:
            position = float(position_text)
        except ValueError:
            messagebox.showerror("Invalid input", "Position must be a valid number.", parent=self)
            return

        r = self.results
        temperatures = r["temperatures"]
        x = r["x"]
        t = r["t"]

        # Find nearest grid point to requested position
        x_idx = np.argmin(np.abs(x - position))
        actual_position = x[x_idx]

        # Parse time values (comma-separated)
        times_text = self.temp_plot_times_var.get().strip()
        if not times_text:
            # Default: use current time slider position
            time_indices = [self._current_time_index]
            time_values = [t[self._current_time_index]]
        else:
            try:
                time_values = [float(s.strip()) for s in times_text.split(",") if s.strip()]
                if not time_values:
                    raise ValueError("No valid time values")

                # Find nearest time indices
                time_indices = [np.argmin(np.abs(t - tv)) for tv in time_values]
                # Get actual time values from grid
                time_values = [t[idx] for idx in time_indices]
            except ValueError as e:
                messagebox.showerror("Invalid input", f"Time values must be comma-separated numbers.\nError: {e}", parent=self)
                return

        # Extract concentrations for all temperatures at each requested time
        # concentrations_list: list of (time_value, concentration_array)
        concentrations_list = [(time_values[i], r["C_Txt"][:, time_indices[i], x_idx]) for i in range(len(time_values))]

        # Update the plot with multiple time series
        update_temperature_axes(self.artists, temperatures, concentrations_list, actual_position)
        self.canvas.draw_idle()

    def _update_c_time_plot(self) -> None:
        """Update the C vs Time plot at the selected position for selected temperature(s)."""
        if not self.results or not self.is_temperature_sweep:
            messagebox.showinfo("No data", "C vs Time plot is only available for temperature sweep simulations.", parent=self)
            return

        position_text = self.c_time_position_var.get().strip()
        if not position_text:
            messagebox.showwarning("Input required", "Please enter a position [m] for the C vs Time plot.", parent=self)
            return

        try:
            position = float(position_text)
        except ValueError:
            messagebox.showerror("Invalid input", "Position must be a valid number.", parent=self)
            return

        r = self.results
        x = r["x"]
        t = r["t"]

        # Find nearest grid point to requested position
        x_idx = np.argmin(np.abs(x - position))
        actual_position = x[x_idx]

        # Parse temperature values (comma-separated)
        temps_text = self.c_time_temps_var.get().strip()
        if not temps_text:
            # Default: use current selected temperature
            selected_T = self._get_selected_temperature()
            temperature_values = [selected_T]
        else:
            try:
                temperature_values = [float(s.strip()) for s in temps_text.split(",") if s.strip()]
                if not temperature_values:
                    raise ValueError("No valid temperature values")

                # Validate temperatures exist in results
                available_temps = r["temperatures"]
                for temp_val in temperature_values:
                    if temp_val not in available_temps:
                        # Find nearest available temperature
                        nearest_T = available_temps[np.argmin(np.abs(available_temps - temp_val))]
                        messagebox.showwarning(
                            "Temperature not found",
                            f"Temperature {temp_val} K not in simulation. Using nearest: {nearest_T} K",
                            parent=self
                        )
                        temperature_values[temperature_values.index(temp_val)] = nearest_T
            except ValueError as e:
                messagebox.showerror("Invalid input", f"Temperature values must be comma-separated numbers.\nError: {e}", parent=self)
                return

        # Extract concentrations for each temperature across all time
        # concentrations_list: list of (temperature_value, concentration_array)
        concentrations_list = [(temp_val, r["results_by_temp"][temp_val]["C_xt"][:, x_idx]) for temp_val in temperature_values]

        # Update the plot with multiple temperature series
        update_c_time_axes(self.artists, t, concentrations_list, actual_position)
        self.canvas.draw_idle()

    def _go_to_time(self) -> None:
        """Go to the specified time in seconds (Graph 3 control)."""
        if not self.results:
            messagebox.showinfo("No data", "Please run a simulation first.", parent=self)
            return

        time_text = self.profile_time_var.get().strip()
        if not time_text:
            messagebox.showwarning("Input required", "Please enter a time [s] to go to.", parent=self)
            return

        try:
            target_time = float(time_text)
        except ValueError:
            messagebox.showerror("Invalid input", "Time must be a valid number.", parent=self)
            return

        # Get time array from current results
        if self.is_temperature_sweep:
            selected_T = self._get_selected_temperature()
            t = self.results["results_by_temp"][selected_T]["t"]
        else:
            t = self.results["t"]

        # Find nearest time index
        time_idx = np.argmin(np.abs(t - target_time))
        actual_time = t[time_idx]

        # Update to this time index
        self._set_time_index(time_idx)

        # Provide feedback
        messagebox.showinfo("Time set", f"Moved to nearest time: {actual_time:.6g} s (index {time_idx})", parent=self)

    def _on_temperature_selection_g3(self) -> None:
        """Handle temperature selection change for Graph 3."""
        if not self.results or not self.is_temperature_sweep:
            return
        # Sync with main temperature selector
        temp_str = self.selected_temperature_g3.get()
        if temp_str:
            self.selected_temperature.set(temp_str)
        # Refresh profile plot
        self._on_time_change()


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

        # For temperature sweep, use first temperature's data for probe computation
        if self.is_temperature_sweep:
            first_T = r["temperatures"][0]
            r = r["results_by_temp"][first_T]

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

        # Store probe results
        # For temperature sweep, store in main results dict (not in results_by_temp)
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

        # For temperature sweep, use first temperature's data
        r = self.results
        if self.is_temperature_sweep:
            first_T = r["temperatures"][0]
            r = r["results_by_temp"][first_T]

        layer_names = r.get("layer_names")
        boundaries = r.get("layer_boundaries")
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

    def _show_error_dialog(self, error_message: str) -> None:
        """Show a copyable error dialog with full details."""
        error_win = tk.Toplevel(self)
        error_win.title("Simulation Error")
        error_win.geometry("700x400")

        # Label
        ttk.Label(error_win, text="An error occurred during simulation:", font=("TkDefaultFont", 10, "bold")).pack(pady=10)

        # Scrolled text widget for error message (read-only but selectable)
        from tkinter import scrolledtext
        text_widget = scrolledtext.ScrolledText(error_win, wrap=tk.WORD, width=80, height=20)
        text_widget.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
        text_widget.insert(tk.END, error_message)
        text_widget.config(state="disabled")  # Make read-only but still allows selection and copying

        # Enable Ctrl+A to select all
        text_widget.bind("<Control-a>", lambda e: text_widget.tag_add(tk.SEL, "1.0", tk.END))
        text_widget.bind("<Control-A>", lambda e: text_widget.tag_add(tk.SEL, "1.0", tk.END))

        # Button frame
        btn_frame = ttk.Frame(error_win)
        btn_frame.pack(pady=5)

        def copy_to_clipboard():
            self.clipboard_clear()
            self.clipboard_append(error_message)
            messagebox.showinfo("Copied", "Error message copied to clipboard!", parent=error_win)

        ttk.Button(btn_frame, text="Copy to Clipboard", command=copy_to_clipboard).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Close", command=error_win.destroy).pack(side=tk.LEFT, padx=5)

    def _export_flux(self) -> None:
        if not self.results:
            messagebox.showinfo("Export", "No results to export.", parent=self)
            return
        r = self.results
        try:
            base = ensure_results_dir(RESULTS_DIR)
        except Exception as exc:
            messagebox.showerror("Export", f"Failed to create results directory: {exc}", parent=self)
            return

        if self.is_temperature_sweep:
            try:
                # Temperature sweep: save as Excel file with temperature-labeled sheets
                from pathlib import Path
                base_path = Path(base)

                # Save Excel file with all temperatures
                excel_path = save_temperature_sweep_excel(
                    base,
                    r["temperatures"],
                    r["results_by_temp"],
                )

                # Also save NPZ for programmatic access
                np.savez(
                    base_path / "results_temperature_sweep.npz",
                    temperatures=r["temperatures"],
                    x=r["x"],
                    t=r["t"],
                    C_Txt=r["C_Txt"],
                    J_surface_Tt=r["J_surface_Tt"],
                    J_target_Tt=r["J_target_Tt"],
                    J_end_Tt=r["J_end_Tt"],
                    J_probe_Tt=r.get("J_probe_Tt"),
                )

                if self.last_params:
                    save_metadata(
                        base,
                        self.last_params,
                        extras={
                            "is_temperature_sweep": True,
                            "temperatures": r["temperatures"].tolist(),
                            "layer_boundaries": r["results_by_temp"][r["temperatures"][0]]["layer_boundaries"].tolist(),
                        },
                    )

                messagebox.showinfo(
                    "Export",
                    f"Saved temperature sweep results to {base}:\n- results_temperature_sweep.xlsx (Excel file with {len(r['temperatures'])} temperature sheets)\n- results_temperature_sweep.npz",
                    parent=self,
                )
            except Exception as exc:
                import traceback
                error_details = f"{type(exc).__name__}: {str(exc)}\n\nFull traceback:\n{traceback.format_exc()}"
                self._show_error_dialog(f"Export failed:\n{error_details}")
        else:
            # Single simulation: save as before
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
