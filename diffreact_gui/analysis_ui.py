"""
UI components for the Analysis tab (doping analysis).

This module contains all UI elements for experimental data input,
capacitor model configuration, and analysis visualization.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import Optional, Callable, Dict, List
import numpy as np
import csv

from .models import CapacitorParams, ExperimentalData
from .analysis import calculate_capacitance, calculate_dq_grid, prepare_plot_data
from .plots import create_analysis_figure, update_analysis_plot
from .utils import save_experimental_data, load_experimental_data

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk


class ExperimentalDataTable(ttk.Frame):
    """
    Excel-style 2D table widget for voltage measurements.

    Allows users to input voltage values in a grid format with
    row and column headers representing experimental conditions.
    Automatically calculates dq values when capacitor parameters change.
    """

    def __init__(
        self,
        parent,
        on_data_changed: Optional[Callable] = None,
        **kwargs
    ):
        """
        Initialize experimental data table.

        Args:
            parent: Parent widget
            on_data_changed: Callback when data changes (receives no arguments)
            **kwargs: Additional arguments passed to Frame
        """
        super().__init__(parent, **kwargs)

        self._on_data_changed = on_data_changed

        # Data storage
        self.row_values: List[float] = []
        self.col_values: List[float] = []
        self.voltage_data: Dict[tuple, float] = {}  # {(row_idx, col_idx): voltage}
        self.dq_data: Dict[tuple, float] = {}  # {(row_idx, col_idx): dq}

        # Capacitor params (cached for dq calculation)
        self._capacitor_params: Optional[CapacitorParams] = None

        # Build UI
        self._build_ui()

    def _build_ui(self):
        """Build table UI."""
        # Controls frame
        ctrl_frame = ttk.Frame(self)
        ctrl_frame.pack(fill=tk.X, padx=4, pady=4)

        ttk.Button(ctrl_frame, text="+ Row", command=self._add_row, width=8).pack(side=tk.LEFT, padx=2)
        ttk.Button(ctrl_frame, text="- Row", command=self._remove_row, width=8).pack(side=tk.LEFT, padx=2)
        ttk.Button(ctrl_frame, text="+ Col", command=self._add_col, width=8).pack(side=tk.LEFT, padx=2)
        ttk.Button(ctrl_frame, text="- Col", command=self._remove_col, width=8).pack(side=tk.LEFT, padx=2)

        # Table frame with scrollbars
        table_frame = ttk.Frame(self)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        # Scrollbars
        vsb = ttk.Scrollbar(table_frame, orient="vertical")
        hsb = ttk.Scrollbar(table_frame, orient="horizontal")

        # Treeview
        self.tree = ttk.Treeview(
            table_frame,
            columns=(),
            show="tree headings",
            height=8,
            yscrollcommand=vsb.set,
            xscrollcommand=hsb.set
        )

        vsb.config(command=self.tree.yview)
        hsb.config(command=self.tree.xview)

        # Grid layout
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)

        # Bind single-click for editing (Excel-like)
        self.tree.bind("<Button-1>", self._on_cell_click)

        # Entry widget for inline editing
        self.edit_entry = None
        self.edit_item = None
        self.edit_column = None

        # CSV import/export
        csv_frame = ttk.Frame(self)
        csv_frame.pack(fill=tk.X, padx=4, pady=4)

        ttk.Button(csv_frame, text="📂 Load CSV", command=self._load_csv, width=15).pack(side=tk.LEFT, padx=2)
        ttk.Button(csv_frame, text="💾 Save CSV", command=self._save_csv, width=15).pack(side=tk.LEFT, padx=2)

        # Initialize with default 3x3 grid
        self.row_values = [100.0, 200.0, 300.0]
        self.col_values = [300.0, 350.0, 400.0]
        self._rebuild_table()

    def _rebuild_table(self):
        """Rebuild table structure from current row/col values."""
        # Clear existing columns and items
        self.tree.delete(*self.tree.get_children())

        # Set up columns: first column is row header, rest are col values
        col_ids = ["row_header"] + [f"col_{i}" for i in range(len(self.col_values))]
        self.tree.config(columns=col_ids)

        # Configure column widths
        self.tree.column("#0", width=0, stretch=False)  # Hide tree column
        self.tree.column("row_header", width=100, anchor=tk.CENTER)
        self.tree.heading("row_header", text="Row \\ Col")

        for i, col_val in enumerate(self.col_values):
            col_id = f"col_{i}"
            self.tree.column(col_id, width=100, anchor=tk.CENTER)
            self.tree.heading(col_id, text=f"{col_val:.2e}")

        # Insert rows
        for row_idx, row_val in enumerate(self.row_values):
            values = [f"{row_val:.2e}"]  # Row header
            for col_idx in range(len(self.col_values)):
                # Get voltage value (default 0.0)
                voltage = self.voltage_data.get((row_idx, col_idx), 0.0)
                values.append(f"{voltage:.3f}")

            self.tree.insert("", "end", iid=f"row_{row_idx}", values=values)

    def _add_row(self):
        """Add a new row to the table."""
        # Default: increment last row value by 100
        if self.row_values:
            new_val = self.row_values[-1] + 100.0
        else:
            new_val = 100.0

        self.row_values.append(new_val)
        self._rebuild_table()
        self._notify_change()

    def _remove_row(self):
        """Remove last row from the table."""
        if not self.row_values:
            return

        # Remove data associated with last row
        row_idx = len(self.row_values) - 1
        for col_idx in range(len(self.col_values)):
            self.voltage_data.pop((row_idx, col_idx), None)
            self.dq_data.pop((row_idx, col_idx), None)

        self.row_values.pop()
        self._rebuild_table()
        self._notify_change()

    def _add_col(self):
        """Add a new column to the table."""
        # Default: increment last col value by 50
        if self.col_values:
            new_val = self.col_values[-1] + 50.0
        else:
            new_val = 300.0

        self.col_values.append(new_val)
        self._rebuild_table()
        self._notify_change()

    def _remove_col(self):
        """Remove last column from the table."""
        if not self.col_values:
            return

        # Remove data associated with last column
        col_idx = len(self.col_values) - 1
        for row_idx in range(len(self.row_values)):
            self.voltage_data.pop((row_idx, col_idx), None)
            self.dq_data.pop((row_idx, col_idx), None)

        self.col_values.pop()
        self._rebuild_table()
        self._notify_change()

    def _on_cell_click(self, event):
        """Handle single-click on cell for Excel-like inline editing."""
        # Close any existing edit entry
        self._close_edit_entry()

        # Get clicked region
        region = self.tree.identify_region(event.x, event.y)
        column = self.tree.identify_column(event.x)
        item = self.tree.identify_row(event.y)

        # Check if clicked on column header
        if region == "heading":
            if column == "#0":
                # Ignore tree column
                return
            elif column == "#1":
                # Row header column label - ignore for now
                return
            # Edit column header
            col_idx = int(column.replace("#", "")) - 2
            if 0 <= col_idx < len(self.col_values):
                self._edit_column_header(col_idx, event.x, event.y)
            return

        # Check if clicked on cell
        if region == "cell":
            if not item or column == "#0":
                # Ignore tree column
                return

            # Check if clicked on row header (column #1)
            if column == "#1":
                # Edit row header
                row_idx = int(item.split("_")[1])
                if 0 <= row_idx < len(self.row_values):
                    self._edit_row_header(item, row_idx, event.x, event.y)
                return

            # Extract row and column indices
            row_idx = int(item.split("_")[1])
            col_idx = int(column.replace("#", "")) - 2

            if 0 <= row_idx < len(self.row_values) and 0 <= col_idx < len(self.col_values):
                self._edit_cell_inline(item, column, row_idx, col_idx, event.x, event.y)

    def _edit_cell_inline(self, item, column, row_idx, col_idx, x, y):
        """Create inline entry widget for editing cell."""
        # Get cell bounding box
        bbox = self.tree.bbox(item, column)
        if not bbox:
            return

        # Get current value
        current_voltage = self.voltage_data.get((row_idx, col_idx), 0.0)

        # Create entry widget
        self.edit_entry = ttk.Entry(self.tree, width=10)
        self.edit_entry.insert(0, str(current_voltage))
        self.edit_entry.select_range(0, tk.END)
        self.edit_entry.focus()

        # Position entry widget over cell
        self.edit_entry.place(x=bbox[0], y=bbox[1], width=bbox[2], height=bbox[3])

        # Store edit context
        self.edit_item = item
        self.edit_column = column
        self.edit_row_idx = row_idx
        self.edit_col_idx = col_idx
        self.edit_is_header = False

        # Bind events
        self.edit_entry.bind("<Return>", lambda e: self._save_cell_edit())
        self.edit_entry.bind("<FocusOut>", lambda e: self._save_cell_edit())
        self.edit_entry.bind("<Escape>", lambda e: self._close_edit_entry())

    def _edit_column_header(self, col_idx, x, y):
        """Create inline entry widget for editing column header."""
        # Get header bounding box
        column_id = f"#{col_idx + 2}"

        # Approximate header position (Treeview doesn't provide bbox for headers)
        # We'll position it based on column position
        col_x = 0
        for i in range(col_idx + 2):
            col_name = f"#{i}" if i == 0 else f"#{i}"
            if i == 0:
                col_x += 100  # Tree column
            elif i == 1:
                col_x += 100  # Row header column
            else:
                col_x += 100  # Data columns

        # Create entry widget
        self.edit_entry = ttk.Entry(self.tree, width=10)
        self.edit_entry.insert(0, str(self.col_values[col_idx]))
        self.edit_entry.select_range(0, tk.END)
        self.edit_entry.focus()

        # Position entry widget (approximate header position)
        self.edit_entry.place(x=col_x, y=0, width=100, height=20)

        # Store edit context
        self.edit_item = None
        self.edit_column = column_id
        self.edit_col_idx = col_idx
        self.edit_is_header = True
        self.edit_is_col_header = True

        # Bind events
        self.edit_entry.bind("<Return>", lambda e: self._save_header_edit())
        self.edit_entry.bind("<FocusOut>", lambda e: self._save_header_edit())
        self.edit_entry.bind("<Escape>", lambda e: self._close_edit_entry())

    def _edit_row_header(self, item, row_idx, x, y):
        """Create inline entry widget for editing row header."""
        # Get cell bounding box for the row header
        bbox = self.tree.bbox(item, "#1")
        if not bbox:
            return

        # Create entry widget
        self.edit_entry = ttk.Entry(self.tree, width=10)
        self.edit_entry.insert(0, str(self.row_values[row_idx]))
        self.edit_entry.select_range(0, tk.END)
        self.edit_entry.focus()

        # Position entry widget over row header cell
        self.edit_entry.place(x=bbox[0], y=bbox[1], width=bbox[2], height=bbox[3])

        # Store edit context
        self.edit_item = item
        self.edit_column = "#1"
        self.edit_row_idx = row_idx
        self.edit_is_header = True
        self.edit_is_col_header = False
        self.edit_is_row_header = True

        # Bind events
        self.edit_entry.bind("<Return>", lambda e: self._save_header_edit())
        self.edit_entry.bind("<FocusOut>", lambda e: self._save_header_edit())
        self.edit_entry.bind("<Escape>", lambda e: self._close_edit_entry())

    def _save_cell_edit(self):
        """Save the edited cell value."""
        if not self.edit_entry or self.edit_is_header:
            return

        try:
            new_value = float(self.edit_entry.get())
            row_idx = self.edit_row_idx
            col_idx = self.edit_col_idx

            self.voltage_data[(row_idx, col_idx)] = new_value
            self._recalculate_dq(row_idx, col_idx)
            self._rebuild_table()
            self._notify_change()

        except ValueError:
            messagebox.showerror("Invalid Input", "Please enter a valid number")

        self._close_edit_entry()

    def _save_header_edit(self):
        """Save the edited column or row header value."""
        if not self.edit_entry or not self.edit_is_header:
            return

        try:
            new_value = float(self.edit_entry.get())

            if self.edit_is_col_header:
                col_idx = self.edit_col_idx
                self.col_values[col_idx] = new_value
                self._rebuild_table()
                self._notify_change()
            elif hasattr(self, 'edit_is_row_header') and self.edit_is_row_header:
                row_idx = self.edit_row_idx
                self.row_values[row_idx] = new_value
                self._rebuild_table()
                self._notify_change()

        except ValueError:
            messagebox.showerror("Invalid Input", "Please enter a valid number")

        self._close_edit_entry()

    def _close_edit_entry(self):
        """Close and destroy the edit entry widget."""
        if self.edit_entry:
            self.edit_entry.destroy()
            self.edit_entry = None
            self.edit_item = None
            self.edit_column = None
            self.edit_is_header = False

    def _recalculate_dq(self, row_idx: int, col_idx: int):
        """Recalculate dq for a specific cell."""
        if self._capacitor_params is None:
            return

        voltage = self.voltage_data.get((row_idx, col_idx), 0.0)
        C = calculate_capacitance(self._capacitor_params)
        dq = C * (voltage - self._capacitor_params.V0)
        self.dq_data[(row_idx, col_idx)] = dq

    def update_capacitor_params(self, params: CapacitorParams):
        """
        Update capacitor parameters and recalculate all dq values.

        Args:
            params: New capacitor parameters
        """
        self._capacitor_params = params

        # Recalculate all dq values
        for row_idx in range(len(self.row_values)):
            for col_idx in range(len(self.col_values)):
                self._recalculate_dq(row_idx, col_idx)

        self._notify_change()

    def get_experimental_data(
        self,
        name: str,
        fixed_var: str,
        fixed_value: float,
        row_var: str,
        col_var: str
    ) -> ExperimentalData:
        """
        Get ExperimentalData object from current table state.

        Args:
            name: Dataset name
            fixed_var: Fixed variable name
            fixed_value: Fixed variable value
            row_var: Row variable name
            col_var: Column variable name

        Returns:
            ExperimentalData object

        Raises:
            ValueError: If capacitor params not set or data incomplete
        """
        if self._capacitor_params is None:
            raise ValueError("Capacitor parameters not set")

        # Build voltage and dq grids
        voltage_grid = np.zeros((len(self.row_values), len(self.col_values)))
        dq_grid = np.zeros((len(self.row_values), len(self.col_values)))

        for row_idx in range(len(self.row_values)):
            for col_idx in range(len(self.col_values)):
                voltage_grid[row_idx, col_idx] = self.voltage_data.get((row_idx, col_idx), 0.0)
                dq_grid[row_idx, col_idx] = self.dq_data.get((row_idx, col_idx), 0.0)

        return ExperimentalData(
            name=name,
            capacitor=self._capacitor_params,
            fixed_var=fixed_var,
            fixed_value=fixed_value,
            row_var=row_var,
            row_values=np.array(self.row_values),
            col_var=col_var,
            col_values=np.array(self.col_values),
            voltage_grid=voltage_grid,
            dq_grid=dq_grid,
        )

    def load_experimental_data(self, exp_data: ExperimentalData):
        """
        Load experimental data into the table.

        Args:
            exp_data: ExperimentalData object to load
        """
        self._capacitor_params = exp_data.capacitor
        self.row_values = exp_data.row_values.tolist()
        self.col_values = exp_data.col_values.tolist()

        # Load voltage data
        self.voltage_data.clear()
        self.dq_data.clear()

        for row_idx in range(len(self.row_values)):
            for col_idx in range(len(self.col_values)):
                self.voltage_data[(row_idx, col_idx)] = exp_data.voltage_grid[row_idx, col_idx]
                self.dq_data[(row_idx, col_idx)] = exp_data.dq_grid[row_idx, col_idx]

        self._rebuild_table()
        self._notify_change()

    def _load_csv(self):
        """Load voltage data from CSV file."""
        filename = filedialog.askopenfilename(
            title="Load Voltage Data CSV",
            filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")]
        )

        if not filename:
            return

        try:
            with open(filename, 'r', newline='') as f:
                reader = csv.reader(f)
                rows = list(reader)

            if len(rows) < 2:
                raise ValueError("CSV must have at least 2 rows (header + data)")

            # First row is column headers (skip first cell which is "Row\Col")
            col_values_str = rows[0][1:]
            self.col_values = [float(v) for v in col_values_str]

            # Subsequent rows: first cell is row value, rest are voltages
            self.row_values = []
            self.voltage_data.clear()

            for row_idx, row in enumerate(rows[1:]):
                row_val = float(row[0])
                self.row_values.append(row_val)

                for col_idx, voltage_str in enumerate(row[1:]):
                    if col_idx < len(self.col_values):
                        voltage = float(voltage_str) if voltage_str.strip() else 0.0
                        self.voltage_data[(row_idx, col_idx)] = voltage

            # Recalculate dq for all cells
            if self._capacitor_params:
                for row_idx in range(len(self.row_values)):
                    for col_idx in range(len(self.col_values)):
                        self._recalculate_dq(row_idx, col_idx)

            self._rebuild_table()
            self._notify_change()

            messagebox.showinfo("Success", f"Loaded data from {filename}")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load CSV:\n{str(e)}")

    def _save_csv(self):
        """Save voltage data to CSV file."""
        filename = filedialog.asksaveasfilename(
            title="Save Voltage Data CSV",
            defaultextension=".csv",
            filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")]
        )

        if not filename:
            return

        try:
            with open(filename, 'w', newline='') as f:
                writer = csv.writer(f)

                # Header row
                header = ["Row\\Col"] + [f"{v:.6e}" for v in self.col_values]
                writer.writerow(header)

                # Data rows
                for row_idx, row_val in enumerate(self.row_values):
                    row_data = [f"{row_val:.6e}"]
                    for col_idx in range(len(self.col_values)):
                        voltage = self.voltage_data.get((row_idx, col_idx), 0.0)
                        row_data.append(f"{voltage:.6f}")
                    writer.writerow(row_data)

            messagebox.showinfo("Success", f"Saved data to {filename}")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to save CSV:\n{str(e)}")

    def _notify_change(self):
        """Notify parent of data change."""
        if self._on_data_changed:
            self._on_data_changed()


class AnalysisControls(ttk.Frame):
    """
    Analysis controls for the Analysis tab.

    Provides UI controls for capacitor parameters, experimental data,
    and plot configuration. Designed to be placed in the left panel.
    """

    def __init__(self, parent, app_ref=None, **kwargs):
        """
        Initialize Analysis controls.

        Args:
            parent: Parent widget
            app_ref: Reference to main App instance (for accessing simulation results and graphs)
            **kwargs: Additional arguments passed to Frame
        """
        super().__init__(parent, **kwargs)

        self.app_ref = app_ref

        # Current state
        self.current_exp_data: Optional[ExperimentalData] = None
        self.saved_datasets: Dict[str, ExperimentalData] = {}

class AnalysisTab(ttk.Frame):
    """
    Main Analysis tab for doping analysis.

    Combines capacitor parameter input, experimental data table,
    plot controls, and visualization in a single interface.
    """

    def __init__(self, parent, app_ref=None, **kwargs):
        """
        Initialize Analysis tab.

        Args:
            parent: Parent widget
            app_ref: Reference to main App instance (for accessing simulation results)
            **kwargs: Additional arguments passed to Frame
        """
        super().__init__(parent, **kwargs)

        self.app_ref = app_ref

        # Current state
        self.current_exp_data: Optional[ExperimentalData] = None
        self.saved_datasets: Dict[str, ExperimentalData] = {}

        # Data source mode
        self.data_source_mode = tk.StringVar(value="current")  # "current" or "loaded"

        # Variable selection state
        self.fixed_var = tk.StringVar(value="position")
        self.row_var = tk.StringVar(value="time")
        self.col_var = tk.StringVar(value="temperature")

        # Capacitor parameter variables
        self.var_epsilon_r = tk.StringVar(value="3.9")
        self.var_A = tk.StringVar(value="1e-4")
        self.var_d = tk.StringVar(value="1e-9")
        self.var_V0 = tk.StringVar(value="0.0")
        self.var_fixed_value = tk.StringVar(value="1e-6")

        # Capacitance display
        self.var_capacitance = tk.StringVar(value="N/A")

        # Dataset name
        self.var_dataset_name = tk.StringVar(value="Dataset_1")

        # Plot control variables
        self.var_x_axis = tk.StringVar(value="temperature")
        self.var_sim_y = tk.StringVar(value="C")
        self.var_sim_filter_1 = tk.StringVar(value="100.0")
        self.var_sim_filter_2 = tk.StringVar(value="1e-6")
        self.var_exp_filter = tk.StringVar(value="100.0")

        # Build UI
        self._build_ui()

        # Update capacitor params callback
        self.var_epsilon_r.trace_add("write", lambda *args: self._update_capacitance())
        self.var_A.trace_add("write", lambda *args: self._update_capacitance())
        self.var_d.trace_add("write", lambda *args: self._update_capacitance())
        self.var_V0.trace_add("write", lambda *args: self._update_capacitance())

        # Update variable selections
        self.fixed_var.trace_add("write", lambda *args: self._update_variable_selections())
        self.var_x_axis.trace_add("write", lambda *args: self._update_filter_labels())

    def _build_ui(self):
        """Build the Analysis tab UI."""
        # Since this tab now occupies the full right panel, we can use full width
        # Use PanedWindow for resizable left controls and right plot
        paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True)

        # Left panel: Controls (30% of width)
        frm_left = ttk.Frame(paned)
        paned.add(frm_left, weight=1)

        # Right panel: Plot (70% of width)
        frm_right = ttk.Frame(paned)
        paned.add(frm_right, weight=2)

        # Create scrollable canvas for left panel
        canvas = tk.Canvas(frm_left)
        scrollbar = ttk.Scrollbar(frm_left, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # Mouse wheel scrolling
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # === Capacitor Parameters ===
        cap_frame = ttk.LabelFrame(scrollable_frame, text="Capacitor Model Parameters", padding=10)
        cap_frame.pack(fill=tk.X, padx=10, pady=5)

        label_font = ("TkDefaultFont", 10)
        entry_font = ("TkDefaultFont", 10)

        row = 0
        ttk.Label(cap_frame, text="Relative Permittivity εᵣ:", font=label_font).grid(row=row, column=0, sticky="w", padx=5, pady=3)
        ttk.Entry(cap_frame, textvariable=self.var_epsilon_r, width=18, font=entry_font).grid(row=row, column=1, padx=5, pady=3)
        ttk.Label(cap_frame, text="(dimensionless)", font=label_font).grid(row=row, column=2, sticky="w", padx=5, pady=3)

        row += 1
        ttk.Label(cap_frame, text="Electrode Area A:", font=label_font).grid(row=row, column=0, sticky="w", padx=5, pady=3)
        ttk.Entry(cap_frame, textvariable=self.var_A, width=18, font=entry_font).grid(row=row, column=1, padx=5, pady=3)
        ttk.Label(cap_frame, text="[m²]", font=label_font).grid(row=row, column=2, sticky="w", padx=5, pady=3)

        row += 1
        ttk.Label(cap_frame, text="Distance d:", font=label_font).grid(row=row, column=0, sticky="w", padx=5, pady=3)
        ttk.Entry(cap_frame, textvariable=self.var_d, width=18, font=entry_font).grid(row=row, column=1, padx=5, pady=3)
        ttk.Label(cap_frame, text="[m]", font=label_font).grid(row=row, column=2, sticky="w", padx=5, pady=3)

        row += 1
        ttk.Label(cap_frame, text="Reference Voltage V₀:", font=label_font).grid(row=row, column=0, sticky="w", padx=5, pady=3)
        ttk.Entry(cap_frame, textvariable=self.var_V0, width=18, font=entry_font).grid(row=row, column=1, padx=5, pady=3)
        ttk.Label(cap_frame, text="[V]", font=label_font).grid(row=row, column=2, sticky="w", padx=5, pady=3)

        row += 1
        ttk.Label(cap_frame, text="Capacitance C:", font=label_font).grid(row=row, column=0, sticky="w", padx=5, pady=3)
        ttk.Label(cap_frame, textvariable=self.var_capacitance, foreground="blue", font=("TkDefaultFont", 10, "bold")).grid(row=row, column=1, sticky="w", padx=5, pady=3)
        ttk.Label(cap_frame, text="[F]", font=label_font).grid(row=row, column=2, sticky="w", padx=5, pady=3)

        # === Data Source Mode Selection ===
        mode_frame = ttk.LabelFrame(scrollable_frame, text="Data Source Mode", padding=10)
        mode_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(mode_frame, text="Select data source for plotting:", font=label_font).pack(anchor="w", padx=5, pady=3)

        mode_radio_frame = ttk.Frame(mode_frame)
        mode_radio_frame.pack(fill=tk.X, padx=20, pady=5)

        ttk.Radiobutton(
            mode_radio_frame,
            text="Use Current Table Data (Live editing)",
            variable=self.data_source_mode,
            value="current",
            command=self._on_data_source_changed
        ).pack(side=tk.LEFT, padx=10)

        ttk.Radiobutton(
            mode_radio_frame,
            text="Use Loaded Dataset (From file)",
            variable=self.data_source_mode,
            value="loaded",
            command=self._on_data_source_changed
        ).pack(side=tk.LEFT, padx=10)

        # Status label
        self.lbl_data_source_status = ttk.Label(mode_frame, text="Mode: Using current table data", foreground="green", font=("TkDefaultFont", 9, "italic"))
        self.lbl_data_source_status.pack(anchor="w", padx=5, pady=3)

        # === Variable Selection ===
        var_frame = ttk.LabelFrame(scrollable_frame, text="Experimental Data Setup", padding=10)
        var_frame.pack(fill=tk.X, padx=10, pady=5)

        bold_font = ("TkDefaultFont", 10, "bold")

        ttk.Label(var_frame, text="Fixed Variable:", font=bold_font).grid(row=0, column=0, sticky="w", padx=5, pady=5)

        fixed_radio_frame = ttk.Frame(var_frame)
        fixed_radio_frame.grid(row=1, column=0, columnspan=3, sticky="w", padx=20, pady=2)

        radio_font = ("TkDefaultFont", 10)
        ttk.Radiobutton(fixed_radio_frame, text="Temperature [K]", variable=self.fixed_var, value="temperature").pack(side=tk.LEFT, padx=10)
        ttk.Radiobutton(fixed_radio_frame, text="Time [s]", variable=self.fixed_var, value="time").pack(side=tk.LEFT, padx=10)
        ttk.Radiobutton(fixed_radio_frame, text="Position [m]", variable=self.fixed_var, value="position").pack(side=tk.LEFT, padx=10)

        ttk.Label(var_frame, text="Fixed Value:", font=label_font).grid(row=2, column=0, sticky="w", padx=5, pady=3)
        ttk.Entry(var_frame, textvariable=self.var_fixed_value, width=18, font=entry_font).grid(row=2, column=1, padx=5, pady=3)
        self.lbl_fixed_unit = ttk.Label(var_frame, text="[m]", font=label_font)
        self.lbl_fixed_unit.grid(row=2, column=2, sticky="w", padx=5, pady=3)

        ttk.Separator(var_frame, orient="horizontal").grid(row=3, column=0, columnspan=3, sticky="ew", pady=10)

        ttk.Label(var_frame, text="Row Variable:", font=bold_font).grid(row=4, column=0, sticky="w", padx=5, pady=3)
        self.combo_row_var = ttk.Combobox(var_frame, textvariable=self.row_var, state="readonly", width=18, font=entry_font)
        self.combo_row_var.grid(row=4, column=1, padx=5, pady=3)

        ttk.Label(var_frame, text="Column Variable:", font=bold_font).grid(row=5, column=0, sticky="w", padx=5, pady=3)
        self.combo_col_var = ttk.Combobox(var_frame, textvariable=self.col_var, state="readonly", width=18, font=entry_font)
        self.combo_col_var.grid(row=5, column=1, padx=5, pady=3)

        # === Experimental Data Table ===
        table_frame = ttk.LabelFrame(scrollable_frame, text="Voltage Measurements (V)", padding=10)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.data_table = ExperimentalDataTable(table_frame, on_data_changed=self._on_table_data_changed)
        self.data_table.pack(fill=tk.BOTH, expand=True)

        # === Dataset Management ===
        dataset_frame = ttk.LabelFrame(scrollable_frame, text="Dataset Management", padding=10)
        dataset_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(dataset_frame, text="Dataset Name:").grid(row=0, column=0, sticky="w", padx=5, pady=2)
        self.entry_dataset_name = ttk.Entry(dataset_frame, textvariable=self.var_dataset_name, width=20)
        self.entry_dataset_name.grid(row=0, column=1, padx=5, pady=2)

        btn_frame = ttk.Frame(dataset_frame)
        btn_frame.grid(row=1, column=0, columnspan=2, pady=10)

        self.btn_save_dataset = ttk.Button(btn_frame, text="💾 Save Dataset", command=self._save_dataset, width=15)
        self.btn_save_dataset.pack(side=tk.LEFT, padx=5)
        self.btn_load_dataset = ttk.Button(btn_frame, text="📂 Load Dataset", command=self._load_dataset, width=15)
        self.btn_load_dataset.pack(side=tk.LEFT, padx=5)

        ttk.Label(dataset_frame, text="Saved Datasets:").grid(row=2, column=0, sticky="w", padx=5, pady=2)
        self.combo_saved_datasets = ttk.Combobox(dataset_frame, state="readonly", width=20)
        self.combo_saved_datasets.grid(row=2, column=1, padx=5, pady=2)
        self.combo_saved_datasets.bind("<<ComboboxSelected>>", self._on_dataset_selected)

        # File save/load buttons
        file_btn_frame = ttk.Frame(dataset_frame)
        file_btn_frame.grid(row=3, column=0, columnspan=2, pady=5)

        self.btn_save_to_file = ttk.Button(file_btn_frame, text="💾 Save to File", command=self._save_to_file, width=15)
        self.btn_save_to_file.pack(side=tk.LEFT, padx=5)
        self.btn_load_from_file = ttk.Button(file_btn_frame, text="📂 Load from File", command=self._load_from_file, width=15)
        self.btn_load_from_file.pack(side=tk.LEFT, padx=5)

        # === Plot Controls ===
        plot_ctrl_frame = ttk.LabelFrame(scrollable_frame, text="Analysis Plot Controls", padding=10)
        plot_ctrl_frame.pack(fill=tk.X, padx=10, pady=5)

        row = 0
        ttk.Label(plot_ctrl_frame, text="X-axis Variable:", font=bold_font).grid(row=row, column=0, sticky="w", padx=5, pady=3)
        self.combo_x_axis = ttk.Combobox(plot_ctrl_frame, textvariable=self.var_x_axis, state="readonly", width=18, font=entry_font, values=["temperature", "time", "position"])
        self.combo_x_axis.grid(row=row, column=1, padx=5, pady=3)

        row += 1
        ttk.Label(plot_ctrl_frame, text="Simulation Y Variable:", font=bold_font).grid(row=row, column=0, sticky="w", padx=5, pady=3)
        self.combo_sim_y = ttk.Combobox(plot_ctrl_frame, textvariable=self.var_sim_y, state="readonly", width=18, font=entry_font,
                                        values=["C", "J_source", "J_end", "J_target", "cum_source", "cum_end", "cum_target", "mass_target"])
        self.combo_sim_y.grid(row=row, column=1, padx=5, pady=3)

        row += 1
        ttk.Separator(plot_ctrl_frame, orient="horizontal").grid(row=row, column=0, columnspan=2, sticky="ew", pady=5)

        row += 1
        ttk.Label(plot_ctrl_frame, text="Filters (Simulation):", font=bold_font).grid(row=row, column=0, columnspan=2, sticky="w", padx=5, pady=3)

        row += 1
        self.lbl_sim_filter_1 = ttk.Label(plot_ctrl_frame, text="Time [s]:", font=label_font)
        self.lbl_sim_filter_1.grid(row=row, column=0, sticky="w", padx=5, pady=3)
        ttk.Entry(plot_ctrl_frame, textvariable=self.var_sim_filter_1, width=18, font=entry_font).grid(row=row, column=1, padx=5, pady=3)

        row += 1
        self.lbl_sim_filter_2 = ttk.Label(plot_ctrl_frame, text="Position [m]:", font=label_font)
        self.lbl_sim_filter_2.grid(row=row, column=0, sticky="w", padx=5, pady=3)
        ttk.Entry(plot_ctrl_frame, textvariable=self.var_sim_filter_2, width=18, font=entry_font).grid(row=row, column=1, padx=5, pady=3)

        row += 1
        ttk.Separator(plot_ctrl_frame, orient="horizontal").grid(row=row, column=0, columnspan=2, sticky="ew", pady=5)

        row += 1
        ttk.Label(plot_ctrl_frame, text="Filters (Experimental):", font=bold_font).grid(row=row, column=0, columnspan=2, sticky="w", padx=5, pady=3)

        row += 1
        self.lbl_exp_filter = ttk.Label(plot_ctrl_frame, text="Time [s]:", font=label_font)
        self.lbl_exp_filter.grid(row=row, column=0, sticky="w", padx=5, pady=3)
        ttk.Entry(plot_ctrl_frame, textvariable=self.var_exp_filter, width=18, font=entry_font).grid(row=row, column=1, padx=5, pady=3)

        row += 1
        ttk.Separator(plot_ctrl_frame, orient="horizontal").grid(row=row, column=0, columnspan=2, sticky="ew", pady=5)

        row += 1
        # Log scale toggle
        self.var_log_scale = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            plot_ctrl_frame,
            text="Use logarithmic Y-axis scale",
            variable=self.var_log_scale,
            command=None  # No immediate update, only on Update Plot button
        ).grid(row=row, column=0, columnspan=2, sticky="w", padx=5, pady=5)

        row += 1
        btn_font = ("TkDefaultFont", 10, "bold")
        ttk.Button(plot_ctrl_frame, text="📊 Update Plot", command=self._update_plot, width=25).grid(row=row, column=0, columnspan=2, pady=10)

        # === Right Panel: Plot ===
        # Create analysis figure
        fig, ax_sim, ax_exp, artists = create_analysis_figure()
        self.analysis_fig = fig
        self.analysis_artists = artists

        # Embed in tkinter
        self.analysis_canvas = FigureCanvasTkAgg(fig, master=frm_right)
        self.analysis_canvas.draw_idle()
        analysis_canvas_widget = self.analysis_canvas.get_tk_widget()
        analysis_canvas_widget.pack(fill=tk.BOTH, expand=True)

        # Make canvas responsive to window resize
        def _on_canvas_resize(event):
            try:
                fig.tight_layout()
                self.analysis_canvas.draw_idle()
            except Exception:
                pass  # Ignore resize errors during initialization
        analysis_canvas_widget.bind("<Configure>", _on_canvas_resize)

        # Toolbar
        self.analysis_toolbar = NavigationToolbar2Tk(self.analysis_canvas, frm_right)
        self.analysis_toolbar.update()

        # Save graph button
        save_graph_frame = ttk.Frame(frm_right)
        save_graph_frame.pack(fill=tk.X, pady=5, padx=10)

        # Style for larger buttons
        style = ttk.Style()
        style.configure('Large.TButton', padding=6, font=("TkDefaultFont", 10))

        ttk.Button(save_graph_frame, text="💾 Save Graph PNG", command=self._save_graph_png, width=22, style='Large.TButton').pack(side=tk.LEFT, padx=5)
        ttk.Button(save_graph_frame, text="💾 Save Graph SVG", command=self._save_graph_svg, width=22, style='Large.TButton').pack(side=tk.LEFT, padx=5)

        # Initial update
        self._update_capacitance()
        self._update_variable_selections()
        self._update_filter_labels()
        self._on_data_source_changed()  # Set initial button states

    def _update_capacitance(self):
        """Update capacitance display when parameters change."""
        try:
            epsilon_r = float(self.var_epsilon_r.get())
            A = float(self.var_A.get())
            d = float(self.var_d.get())
            V0 = float(self.var_V0.get())

            if epsilon_r <= 0 or A <= 0 or d <= 0:
                self.var_capacitance.set("Invalid (must be > 0)")
                return

            params = CapacitorParams(epsilon_r=epsilon_r, A=A, d=d, V0=V0)
            C = calculate_capacitance(params)
            self.var_capacitance.set(f"{C:.6e}")

            # Update table with new params
            self.data_table.update_capacitor_params(params)

        except ValueError:
            self.var_capacitance.set("N/A")

    def _update_variable_selections(self):
        """Update row/col variable comboboxes based on fixed variable."""
        fixed = self.fixed_var.get()
        all_vars = ["temperature", "time", "position"]
        available = [v for v in all_vars if v != fixed]

        self.combo_row_var.config(values=available)
        self.combo_col_var.config(values=available)

        # Auto-select if current selection is invalid
        if self.row_var.get() == fixed or self.row_var.get() not in available:
            self.row_var.set(available[0])
        if self.col_var.get() == fixed or self.col_var.get() not in available:
            self.col_var.set(available[1] if len(available) > 1 else available[0])

        # Ensure row and col are different
        if self.row_var.get() == self.col_var.get() and len(available) > 1:
            # Swap
            other = [v for v in available if v != self.row_var.get()][0]
            self.col_var.set(other)

        # Update fixed value unit label
        unit_map = {"temperature": "[K]", "time": "[s]", "position": "[m]"}
        self.lbl_fixed_unit.config(text=unit_map.get(fixed, ""))

    def _on_table_data_changed(self):
        """Handle changes in experimental data table."""
        # Could update plot here if needed
        pass

    def _on_data_source_changed(self):
        """Handle data source mode change."""
        mode = self.data_source_mode.get()

        if mode == "current":
            # Use Current Table Data mode
            self.lbl_data_source_status.config(
                text="Mode: Using current table data (live editing enabled)",
                foreground="green"
            )
            # Enable dataset management buttons for memory save
            self.btn_save_dataset.config(state="normal")
            self.btn_save_to_file.config(state="disabled")  # Disable file save (use Save Dataset first)
            # Load from file is always available
            self.btn_load_from_file.config(state="normal")

        elif mode == "loaded":
            # Use Loaded Dataset mode
            if self.current_exp_data is None:
                self.lbl_data_source_status.config(
                    text="Mode: No dataset loaded (please load from file)",
                    foreground="orange"
                )
            else:
                self.lbl_data_source_status.config(
                    text=f"Mode: Using loaded dataset '{self.current_exp_data.name}'",
                    foreground="blue"
                )
            # Disable memory save (not needed in loaded mode)
            self.btn_save_dataset.config(state="disabled")
            # Enable file operations
            self.btn_save_to_file.config(state="normal")
            self.btn_load_from_file.config(state="normal")

    def _save_dataset(self):
        """Save current experimental data as a dataset."""
        try:
            # Get capacitor params
            params = self._get_capacitor_params()

            # Get variable configuration
            name = self.var_dataset_name.get().strip()
            if not name:
                messagebox.showerror("Error", "Please enter a dataset name")
                return

            fixed_var = self.fixed_var.get()
            fixed_value = float(self.var_fixed_value.get())
            row_var = self.row_var.get()
            col_var = self.col_var.get()

            # Validate variable selection
            if fixed_var == row_var or fixed_var == col_var or row_var == col_var:
                messagebox.showerror("Error", "Variables must be distinct")
                return

            # Get experimental data from table
            exp_data = self.data_table.get_experimental_data(
                name=name,
                fixed_var=fixed_var,
                fixed_value=fixed_value,
                row_var=row_var,
                col_var=col_var
            )

            # Save to dictionary
            self.saved_datasets[name] = exp_data
            self.current_exp_data = exp_data

            # Update combobox
            dataset_names = list(self.saved_datasets.keys())
            self.combo_saved_datasets.config(values=dataset_names)
            self.combo_saved_datasets.set(name)

            messagebox.showinfo("Success", f"Dataset '{name}' saved successfully")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to save dataset:\n{str(e)}")

    def _load_dataset(self):
        """Load selected dataset from saved datasets."""
        selected = self.combo_saved_datasets.get()
        if not selected:
            messagebox.showwarning("Warning", "Please select a dataset from the dropdown")
            return

        if selected not in self.saved_datasets:
            messagebox.showerror("Error", f"Dataset '{selected}' not found")
            return

        try:
            exp_data = self.saved_datasets[selected]

            # Load into UI
            self.var_dataset_name.set(exp_data.name)
            self.fixed_var.set(exp_data.fixed_var)
            self.var_fixed_value.set(str(exp_data.fixed_value))
            self.row_var.set(exp_data.row_var)
            self.col_var.set(exp_data.col_var)

            # Load capacitor params
            self.var_epsilon_r.set(str(exp_data.capacitor.epsilon_r))
            self.var_A.set(str(exp_data.capacitor.A))
            self.var_d.set(str(exp_data.capacitor.d))
            self.var_V0.set(str(exp_data.capacitor.V0))

            # Load table data
            self.data_table.load_experimental_data(exp_data)

            self.current_exp_data = exp_data

            messagebox.showinfo("Success", f"Dataset '{selected}' loaded successfully")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load dataset:\n{str(e)}")

    def _on_dataset_selected(self, event):
        """Handle dataset selection from combobox."""
        # Auto-load when selected
        self._load_dataset()

    def _get_capacitor_params(self) -> CapacitorParams:
        """Get current capacitor parameters."""
        epsilon_r = float(self.var_epsilon_r.get())
        A = float(self.var_A.get())
        d = float(self.var_d.get())
        V0 = float(self.var_V0.get())

        if epsilon_r <= 0 or A <= 0 or d <= 0:
            raise ValueError("Capacitor parameters must be positive")

        return CapacitorParams(epsilon_r=epsilon_r, A=A, d=d, V0=V0)

    def get_current_experimental_data(self) -> Optional[ExperimentalData]:
        """
        Get current experimental data.

        Returns:
            ExperimentalData object, or None if not available
        """
        return self.current_exp_data

    def _update_filter_labels(self):
        """Update filter labels based on X-axis selection."""
        x_var = self.var_x_axis.get()
        all_vars = ["temperature", "time", "position"]
        filter_vars = [v for v in all_vars if v != x_var]

        # Update simulation filter labels
        unit_map = {"temperature": "[K]", "time": "[s]", "position": "[m]"}
        name_map = {"temperature": "Temperature", "time": "Time", "position": "Position"}

        if len(filter_vars) >= 1:
            self.lbl_sim_filter_1.config(text=f"{name_map[filter_vars[0]]} {unit_map[filter_vars[0]]}:")
        if len(filter_vars) >= 2:
            self.lbl_sim_filter_2.config(text=f"{name_map[filter_vars[1]]} {unit_map[filter_vars[1]]}:")

        # Update experimental filter label (only one filter needed - the non-row, non-col variable)
        if self.current_exp_data:
            exp_filter_var = [v for v in all_vars if v != x_var and v != self.current_exp_data.fixed_var]
            if exp_filter_var:
                self.lbl_exp_filter.config(text=f"{name_map[exp_filter_var[0]]} {unit_map[exp_filter_var[0]]}:")

    def _update_plot(self):
        """Update analysis plot with current data."""
        try:
            # Check if simulation results available
            if not self.app_ref or not hasattr(self.app_ref, 'results') or not self.app_ref.results:
                messagebox.showwarning("Warning", "Please run a simulation first")
                return

            # Get experimental data based on current mode
            mode = self.data_source_mode.get()
            exp_data = None

            if mode == "current":
                # Use current table data
                try:
                    # Get capacitor params
                    params = self._get_capacitor_params()

                    # Get variable configuration
                    fixed_var = self.fixed_var.get()
                    fixed_value = float(self.var_fixed_value.get())
                    row_var = self.row_var.get()
                    col_var = self.col_var.get()

                    # Validate variable selection
                    if fixed_var == row_var or fixed_var == col_var or row_var == col_var:
                        messagebox.showerror("Error", "Fixed, row, and column variables must be distinct")
                        return

                    # Get experimental data from table
                    exp_data = self.data_table.get_experimental_data(
                        name="Current Table Data",
                        fixed_var=fixed_var,
                        fixed_value=fixed_value,
                        row_var=row_var,
                        col_var=col_var
                    )

                except ValueError as e:
                    messagebox.showerror("Error", f"Failed to get experimental data:\n{str(e)}")
                    return

            elif mode == "loaded":
                # Use loaded dataset
                if self.current_exp_data is None:
                    messagebox.showwarning("Warning", "No dataset loaded. Please load a dataset from file.")
                    return
                exp_data = self.current_exp_data

            if exp_data is None:
                messagebox.showwarning("Warning", "No experimental data available")
                return

            sim_results = self.app_ref.results

            # Get plot parameters
            x_axis_var = self.var_x_axis.get()
            sim_y_var = self.var_sim_y.get()

            # Build filter dictionaries
            all_vars = ["temperature", "time", "position"]
            filter_vars = [v for v in all_vars if v != x_axis_var]

            sim_filters = {}
            if len(filter_vars) >= 1:
                sim_filters[filter_vars[0]] = float(self.var_sim_filter_1.get())
            if len(filter_vars) >= 2:
                sim_filters[filter_vars[1]] = float(self.var_sim_filter_2.get())

            exp_filter_var = [v for v in all_vars if v != x_axis_var and v != exp_data.fixed_var]
            exp_filter = {}
            if exp_filter_var:
                exp_filter[exp_filter_var[0]] = float(self.var_exp_filter.get())

            # Check if temperature sweep
            is_temp_sweep = "temperatures" in sim_results and sim_results["temperatures"] is not None

            # Prepare plot data
            x_values, sim_y_values, exp_y_values = prepare_plot_data(
                sim_results,
                exp_data,
                x_axis_var,
                sim_y_var,
                sim_filters,
                exp_filter,
                is_temperature_sweep=is_temp_sweep
            )

            # Create labels
            unit_map = {"temperature": "Temperature [K]", "time": "Time [s]", "position": "Position [m]"}
            x_label = unit_map.get(x_axis_var, x_axis_var)

            sim_y_labels = {
                "C": "Concentration [mol/m³]",
                "J_source": "Flux at x=0 [mol/(m²·s)]",
                "J_end": "Flux at x=L [mol/(m²·s)]",
                "J_target": "Flux at interface [mol/(m²·s)]",
                "cum_source": "Cumulative at x=0 [mol/m²]",
                "cum_end": "Cumulative at x=L [mol/m²]",
                "cum_target": "Cumulative at interface [mol/m²]",
                "mass_target": "Mass in target [mol/m²]",
            }
            sim_y_label = sim_y_labels.get(sim_y_var, sim_y_var)

            # Build filter info string
            filter_info_parts = []
            for var, val in sim_filters.items():
                filter_info_parts.append(f"{var}={val:.3e}")
            filter_info = ", ".join(filter_info_parts)

            # Get log scale setting
            use_log_scale = self.var_log_scale.get()

            # Update plot
            update_analysis_plot(
                self.analysis_artists,
                x_values,
                sim_y_values,
                exp_y_values,
                x_label,
                sim_y_label,
                x_var_name=x_axis_var.capitalize(),
                filter_info=filter_info,
                use_log_scale=use_log_scale
            )

            # Redraw canvas
            self.analysis_canvas.draw_idle()

        except Exception as e:
            messagebox.showerror("Error", f"Failed to update plot:\n{str(e)}")

    def _save_to_file(self):
        """Save current experimental data to JSON file."""
        if not self.current_exp_data:
            messagebox.showwarning("Warning", "No dataset to save. Please save a dataset first.")
            return

        filename = filedialog.asksaveasfilename(
            title="Save Experimental Data",
            defaultextension=".json",
            filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")]
        )

        if not filename:
            return

        try:
            save_experimental_data(self.current_exp_data, filename, base_path="")
            messagebox.showinfo("Success", f"Data saved to {filename}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save file:\n{str(e)}")

    def _load_from_file(self):
        """Load experimental data from JSON file."""
        filename = filedialog.askopenfilename(
            title="Load Experimental Data",
            filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")]
        )

        if not filename:
            return

        try:
            exp_data = load_experimental_data(filename, base_path="")

            # Load into UI
            self.var_dataset_name.set(exp_data.name)
            self.fixed_var.set(exp_data.fixed_var)
            self.var_fixed_value.set(str(exp_data.fixed_value))
            self.row_var.set(exp_data.row_var)
            self.col_var.set(exp_data.col_var)

            # Load capacitor params
            self.var_epsilon_r.set(str(exp_data.capacitor.epsilon_r))
            self.var_A.set(str(exp_data.capacitor.A))
            self.var_d.set(str(exp_data.capacitor.d))
            self.var_V0.set(str(exp_data.capacitor.V0))

            # Load table data
            self.data_table.load_experimental_data(exp_data)

            # Save to memory
            self.saved_datasets[exp_data.name] = exp_data
            self.current_exp_data = exp_data

            # Update combobox
            dataset_names = list(self.saved_datasets.keys())
            self.combo_saved_datasets.config(values=dataset_names)
            self.combo_saved_datasets.set(exp_data.name)

            # Switch to "loaded" mode
            self.data_source_mode.set("loaded")
            self._on_data_source_changed()

            messagebox.showinfo("Success", f"Data loaded from {filename}\nSwitched to 'Use Loaded Dataset' mode.")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load file:\n{str(e)}")

    def _save_graph_png(self):
        """Save current graph as PNG."""
        filename = filedialog.asksaveasfilename(
            title="Save Graph as PNG",
            defaultextension=".png",
            filetypes=[("PNG Files", "*.png"), ("All Files", "*.*")]
        )

        if not filename:
            return

        try:
            self.analysis_fig.savefig(filename, dpi=300, bbox_inches='tight')
            messagebox.showinfo("Success", f"Graph saved to {filename}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save graph:\n{str(e)}")

    def _save_graph_svg(self):
        """Save current graph as SVG."""
        filename = filedialog.asksaveasfilename(
            title="Save Graph as SVG",
            defaultextension=".svg",
            filetypes=[("SVG Files", "*.svg"), ("All Files", "*.*")]
        )

        if not filename:
            return

        try:
            self.analysis_fig.savefig(filename, format='svg', bbox_inches='tight')
            messagebox.showinfo("Success", f"Graph saved to {filename}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save graph:\n{str(e)}")
