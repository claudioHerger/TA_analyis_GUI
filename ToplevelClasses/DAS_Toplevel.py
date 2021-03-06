import tkinter as tk
import matplotlib
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import seaborn as sns
from matplotlib.figure import Figure
import os
import numpy as np
import gc

from SupportClasses import ToolTip

class DAS_Window(tk.Toplevel):
    def __init__(self, parent, tab_index, DAS, wavelengths, resulting_fit_parameters_dict, components_list, filename, start_time, full_path_to_final_dir):
        super().__init__(parent)
        self.parent = parent
        self.mapped = True
        self.dx = 40
        self.dy = 40
        self.list_position = len(self.parent.DAS_toplevels)
        self.geometry(f'+{400+self.list_position*self.dx}+{100+self.list_position*self.dy}')

        self.filename = os.path.basename(filename)
        self.full_path_to_final_dir = full_path_to_final_dir

        self.title('DAS for SVDGF tab: ' + str(tab_index + 1) + " - file: "+self.filename)
        self.make_figure_and_frame()

        self.DAS = DAS
        self.wavelengths = wavelengths
        self.resulting_fit_parameters_dict = resulting_fit_parameters_dict
        self.components_list = components_list

        self.start_time = start_time
        self.decay_constants = ['{:.2f}'.format(self.resulting_fit_parameters_dict['tau_component%i' % (j)].value) for j in self.components_list]
        try:
            self.decay_constants_std_errors = ['{:.2f}'.format(self.resulting_fit_parameters_dict['tau_component%i' % (j)].stderr) for j in self.components_list]
        except TypeError:
            self.decay_constants_std_errors = ["not computed" for _ in self.components_list]

        self.nr_of_DAS = self.DAS.shape[1]
        self.which_DAS_list = [i for i in range(self.nr_of_DAS)]
        self.update_DAS_plot()
        self.make_checkbuttons()

        self.btn_close = tk.Button(self, text='Close', command=self.destroy_and_give_focus_to_other_toplevel)
        self.btn_close.grid(padx=3, pady=5, sticky="se", column=99)

        self.btn_save_current_figures = tk.Button(self, text='save current figure', command=self.save_current_figures_to_file)
        self.ttp_btn_save_current_figures = ToolTip.CreateToolTip(self.btn_save_current_figures, \
        'This saves the current figure to the same file as saving the data of the SVDGF data tab buttons does. ')
        self.btn_save_current_figures.grid(padx=3, pady=5, sticky="sw", column=98, row=self.btn_close.grid_info()["row"])

        self.btn_close_all = tk.Button(self, text='Close all', command=self.destroy_all)
        self.btn_close_all.grid(padx=3, pady=5, sticky="sw", row=self.btn_close.grid_info()["row"])

        return None

    def make_figure_and_frame(self):
        self.frm_DAS_figure = tk.Frame(self)
        self.frm_DAS_figure.columnconfigure(0, weight=1)
        self.frm_DAS_figure.rowconfigure(0, weight=1)

        self.num_ticks = 5
        self.label_format = '{:.1f}'

        matplotlib.style.use("default")
        matplotlib.rcParams.update({'axes.labelsize': 14.0, 'axes.titlesize': 14.0, 'xtick.labelsize':14, 'ytick.labelsize':14, 'legend.fontsize':12, "axes.edgecolor":"black", "axes.linewidth":1, "axes.grid": True, "grid.linestyle":"--"})

        self.fig = Figure(figsize=(7,5))
        self.ax = self.fig.add_subplot(1,1,1)

        self.canvas = FigureCanvasTkAgg(self.fig, self.frm_DAS_figure)
        self.canvas.draw_idle()

        self.frm_DAS_figure.grid(row=0, columnspan=99)
        self.canvas.get_tk_widget().grid(row=0, column=0, sticky="nsew")

        return None

    def update_DAS_plot(self):
        self.ax.clear()

        # the index of the position of yticks
        self.xticks = np.linspace(0, len(self.wavelengths) - 1, self.num_ticks, dtype=np.int)
        # the content of labels of these yticks
        self.xticklabels = [float(self.wavelengths[idx]) for idx in self.xticks]
        self.xticklabels = [self.label_format.format(x) for x in self.xticklabels]

        for i in self.which_DAS_list:
            self.ax.plot(self.wavelengths, self.DAS[:, i], label=fr'DAS_comp{self.components_list[i]}, $\tau$ = {self.decay_constants[i]} $\pm$ {self.decay_constants_std_errors[i]}')

        self.ax.legend()
        self.ax.set_xticks(self.xticks)
        self.ax.set_xticklabels(self.xticklabels)
        self.ax.set_ylabel("DAS amplitude")
        self.ax.set_xlabel("wavelengths")
        self.basefilename = os.path.splitext(os.path.basename(self.filename))[0]
        self.ax.set_title("DAS for " + self.basefilename + " start time:" + self.label_format.format(float(self.start_time)))

        self.fig.tight_layout()
        self.canvas.draw_idle()

    def update_which_DAS_list(self):
        self.which_DAS_list = []
        for i in range(len(self.DAS_checkbutton_vars)):
            if self.DAS_checkbutton_vars[i].get() == 1:
                self.which_DAS_list.append(i)

        if self.which_DAS_list != []:
            self.update_DAS_plot()
        else:
            tk.messagebox.showerror("No DAS selected to plot!", "at least one checkbox must be checked for me to do something!")
            self.lift()
            return None

    def make_checkbuttons(self):
        self.DAS_checkbutton_vars = [tk.IntVar() for _ in range(self.nr_of_DAS)]

        for i in range(self.nr_of_DAS):
            self.DAS_checkbutton_vars[i].set(0)

        self.DAS_checkbuttons = [tk.Checkbutton(self, text=checkbox, variable=self.DAS_checkbutton_vars[checkbox], onvalue=1, offvalue=0) for checkbox in range(self.nr_of_DAS)]

        for checkbox in range(self.nr_of_DAS):
            self.DAS_checkbuttons[checkbox].grid(row=2, column=checkbox+1)

        self.btn_update_DAS_plot = tk.Button(self, text='update DAS plot', command=self.update_which_DAS_list)
        self.btn_update_DAS_plot.grid(padx=3, pady=5, sticky="se", column=self.DAS_checkbuttons[-1].grid_info()["column"]+1, row=2)

        return None

    def save_current_figures_to_file(self):
        print("saving current DAS figure to file!")

        # check if directory exists:
        if not os.path.exists(self.full_path_to_final_dir):
            os.makedirs(self.full_path_to_final_dir)

        # save current figures:
        self.fig.savefig(self.full_path_to_final_dir+"/DAS_fig_"+str(self.which_DAS_list)+".png")

        return None

    def destroy_all(self):
        for toplevel in self.parent.DAS_toplevels:
            toplevel.mapped = False
            toplevel.destroy()
            toplevel.delete_attributes()
        self.parent.DAS_toplevels = []
        self.parent.parent.lift()

        return None

    def destroy_and_give_focus_to_other_toplevel(self):
        self.destroy()
        self.mapped = False
        self.parent.DAS_toplevels.remove(self)

        # keep other still existing toplevels in focus
        self.parent.parent.lift()       # if user has main gui in background, now gets back to if closing the toplevel
        for toplevel in self.parent.DAS_toplevels:
            if toplevel.mapped:
                toplevel.lift()

        self.delete_attributes()

        return None

    def delete_attributes(self):
        attr_lst = list(vars(self))
        attr_lst.remove('parent')
        for attr in attr_lst:
            delattr(self, attr)

        del attr_lst

        gc.collect()

        return None
