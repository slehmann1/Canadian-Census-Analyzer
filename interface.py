import sys
import tkinter
import tkinter as tk
from tkinter import ttk
from tkinter.ttk import Frame, Button, Label, Radiobutton, Checkbutton
import census
import main
import map_plot

TITLE = "Canadian Census Analyzer"
PROCESSING_METHODS = ("Mean Difference", "Mean Percent Change", "Mean Percent Difference")
GEOGRAPHY = ("Census Subdivisions", "Census Divisions", "Provinces")
DATA_CLIP = ("Yes", "No")

_year_checkbuttons = []
_pm_radio_var = None
_data_clip_var = None
_geo_var = None
_year_selectors = []
_stackcombos = []
_root = None


def generate_interface():
    """
    Create a UI to allow creation of a map
    :return: None
    """
    global _pm_radio_var, _data_clip_var, _geo_var

    root = tk.Tk()
    root.title(TITLE)
    root.geometry('1400x800')

    # Set the theme.
    # Credits to: https://github.com/rdbende/Sun-Valley-ttk-theme & https://github.com/quantumblacklabs/qbstyles
    # TKinter theme:
    root.tk.call("source", "sun-valley.tcl")
    root.tk.call("set_theme", "dark")

    tk.Label(root, text="Select the censuses to analyze data for:").pack(fill="x", pady=10)
    years_frame = Frame(root)
    years_frame.pack(fill="x", pady=10)

    for i, cen in enumerate(census.censuses):
        years_frame.grid_columnconfigure(i, weight=1)
        _year_checkbuttons.append(tk.IntVar())
        c = Checkbutton(years_frame, text=str(cen.year), var=_year_checkbuttons[i], command=year_check_change)
        c.grid(row=0, column=i)

    tk.Label(root, text="What level of geography should be displayed?").pack(fill="x", pady=10)

    geo_frame = Frame(root)
    geo_frame.pack(fill="x", pady=10)

    _geo_var = tkinter.StringVar(value=GEOGRAPHY[0])

    for i in range(0, len(GEOGRAPHY)):
        geo_frame.grid_columnconfigure(i, weight=1)
        r = Radiobutton(geo_frame, text=GEOGRAPHY[i], value=GEOGRAPHY[i], var=_geo_var)
        r.grid(row=0, column=i)

    tk.Label(root, text="Select the way to process data from multiple years:").pack(fill="x", pady=10)

    processing_frame = Frame(root)
    processing_frame.pack(fill="x", pady=10)

    _pm_radio_var = tkinter.StringVar(value=PROCESSING_METHODS[0])

    for i in range(0, len(PROCESSING_METHODS)):
        processing_frame.grid_columnconfigure(i, weight=1)
        r = Radiobutton(processing_frame, text=PROCESSING_METHODS[i], value=PROCESSING_METHODS[i], var=_pm_radio_var)
        r.grid(row=0, column=i)

    tk.Label(root, text="Should outliers be removed from the data?").pack(fill="x", pady=10)

    outlier_frame = Frame(root)
    outlier_frame.pack(fill="x", pady=10)

    _data_clip_var = tkinter.StringVar(value=DATA_CLIP[0])

    for i in range(0, len(DATA_CLIP)):
        outlier_frame.grid_columnconfigure(i, weight=1)
        r = Radiobutton(outlier_frame, text=DATA_CLIP[i], value=DATA_CLIP[i], var=_data_clip_var)
        r.grid(row=0, column=i)

    for i, cen in enumerate(census.censuses):
        _year_selectors.append(Frame(root))
        tk.Label(_year_selectors[i], text=f"Select a value of interest from year {cen.year}:").pack(fill="x", pady=10)
        _stackcombos.append(StackCombo(_year_selectors[i], cen.char_tree, None, width=150))
        _stackcombos[-1].pack(fill="x", pady=10)

    Button(root, text="Create Plot", command=create_plot).pack(fill="x", side="bottom")

    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()


def year_check_change():
    """
    Event that updates the UI when a year checkbox changes state
    :return: None
    """
    for i, check_val in enumerate(_year_checkbuttons):
        if check_val.get():
            _year_selectors[i].pack(fill="x", pady=10)
        else:
            _year_selectors[i].pack_forget()


def create_plot():
    """
    Creates a map plot based on the options that are selected within the UI
    :return: None
    """
    cen = []
    strings = []
    func = None

    for i, check_val in enumerate(_year_checkbuttons):
        if check_val.get():
            cen.append(census.censuses[i])
            strings.append(_stackcombos[i].get_final_val())

    func_name = _pm_radio_var.get()

    for i, proc_method in enumerate(PROCESSING_METHODS):
        if func_name == proc_method:
            func = map_plot.FUNC_LIST[i]
            break

    map_plot.plot_map(func_name, strings, cen, func, clipped=_data_clip_var.get() == DATA_CLIP[0], type=_geo_var.get())


def on_closing():
    """
    Handles the exit button being pressed
    :return:
    """
    print("End of program")
    sys.exit()


class StackCombo(tk.Frame):
    """
    An extension of a tkinter ComboBox, but supports nesting, thereby created stacked combo boxes.
    """
    # The number of spaces that each child is indented by
    NUM_SPACES = 5

    def __init__(self, master, node, master_combo=None, **kwargs):
        tk.Frame.__init__(self, master, **kwargs)
        self.master = master
        self.master_combo = master_combo
        self.node = node
        self.child = None

        if master_combo is not None:
            self.indent_level = master_combo.get_indent_level() + 1
            text = " " * (self.indent_level - 1) * StackCombo.NUM_SPACES + "↳"
            Label(self, text=text).pack(side="left", padx=10)
        else:
            self.indent_level = 0

        values = []
        # Remove the separator
        for i, ch in enumerate(node.children):
            values.append(ch.name.split(main.TREE_SEPARATOR)[-1])

        self.combo = ttk.Combobox(self, values=values, **kwargs)
        self.combo.bind("<<ComboboxSelected>>", self.field_change)
        self.combo.pack(side="left", fill="x", padx=10)

    @staticmethod
    def _get_child_by_name(node, name):
        for child in node.children:
            if name in child.name:
                return child

        raise Exception("No child by that name exists")

    def get_final_val(self):
        """
        Gets the value of the stack combo that is lowest down in the hierarchy, be it this stack combo or a child
        :return: A string of the stack combo text
        """
        if self.child is not None:
            return self.child.get_final_val()

        return self.combo.get()

    def field_change(self, _):
        """
        Event that is triggered when the value of the combobox changes
        :param _:
        :return:
        """

        # Destroy children
        if self.child is not None:
            self.child.destroy()

        # Add new children if there are any child nodes
        child_node = StackCombo._get_child_by_name(self.node, self.combo.get())
        if len(child_node.children) > 0:
            self.child = StackCombo(self.master, child_node, self, width=150)
            self.child.pack(fill="x", pady=10)

    def destroy(self):
        if self.child is not None:
            self.child.destroy()
        super().destroy()

    def get_indent_level(self):
        return self.indent_level
