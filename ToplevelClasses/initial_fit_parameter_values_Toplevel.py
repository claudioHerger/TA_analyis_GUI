import ast
import re
import tkinter as tk
import numpy as np
import gc

from FunctionsUsedByPlotClasses import (get_closest_nr_from_array_like, get_retained_rightSVs_leftSVs_singularvs, get_TA_data_after_start_time)
from SupportClasses import ToolTip
from ToplevelClasses import CompareRightSVsWithFit_Toplevel

class initial_fit_parameters_Window(tk.Toplevel):
    def __init__(self, parent, initial_values_file_name, current_values, assign_handler, components_list, use_user_defined_fit_function, target_model_configuration_file, data_file_name, full_path_to_final_dir, matrix_bounds_dict):
        """a toplevel window to inspect the initial fit parameter values in the SVDGF procedure.
        Whenever these values are changed, the new ones will be used for each fit until the user selects to change them again.
        In order to reuse these selected values once the user quits and restarts the program, the values are written to a file.
        From there they are again read when the user starts the program again.

        Args:
            parent (tk.Frame): the root window.
            initial_values_file_name (str): file to write new initial fit parameter values in
            current_values (dict): dictionary of currently used initial fit parameter values
            assign_handler (function): method that handles the assignement of new initial fit values in main Gui which instantiates the toplevel.
            components_list (list of ints): list of components selected.
            use_user_defined_fit_function (bool): whether or not to use the user defined fit function.
            target_model_configuration_file (str): path to target model configuration file.
            data_file_name (str): path to data file
            full_path_to_final_dir (str): path to save figures and data to (figure in compare window).
            matrix_bounds_dict (dict): contains the indeces that dictate the which part of complete data matrix to use
        """


        super().__init__(parent)
        self.parent = parent
        self.old_initial_fit_parameter_values = current_values
        self.intial_values_file_name = initial_values_file_name
        self.assign_handler = assign_handler

        self.title('Set the initial fit parameter values - used for each fit.')

        # properties used for rightSVs vs initial fit parameter values window
        self.components_list = components_list
        self.use_user_defined_fit_function = use_user_defined_fit_function
        self.data_file_name = data_file_name
        self.full_path_to_final_dir = full_path_to_final_dir
        self.matrix_bounds_dict = matrix_bounds_dict
        if not self.matrix_bounds_dict == {}:
            self.min_wavelength_index = self.matrix_bounds_dict["min_wavelength_index"]
            self.max_wavelength_index = self.matrix_bounds_dict["max_wavelength_index"]
            self.min_time_delay_index = self.matrix_bounds_dict["min_time_delay_index"]
            self.max_time_delay_index = self.matrix_bounds_dict["max_time_delay_index"]
        self.target_model_configuration_file = target_model_configuration_file

        self.btn_quit = tk.Button(self, text="Quit", command=lambda: self.ignore_and_quit())
        ttp_btn_quit = ToolTip.CreateToolTip(self.btn_quit, \
        'Quit this window and use the last saved fit parameters.')
        self.btn_quit.grid(padx=10, pady=10, sticky="se", row=99, column=3)

        self.display_fit_parameters_labels_and_entries()

        self.btn_assign_new_fit_parameter_values = tk.Button(self, text="use entered values", command=self.assign_new_values_if_correct_format)
        ttp_btn_assign_new_fit_parameter_values = ToolTip.CreateToolTip(self.btn_assign_new_fit_parameter_values, \
        'Saves the entered values to file and closes the window.')
        self.btn_assign_new_fit_parameter_values.grid(padx=10, pady=10, sticky="sw", row=99, column=0)

        self.btn_help = tk.Button(self, text="help", command=self.display_help_window)
        ttp_btn_help = ToolTip.CreateToolTip(self.btn_help, \
        'If you are confused by the number of parameters.')
        self.btn_help.grid(padx=10, row=0, column=0)

        self.btn_add_more_parameters = tk.Button(self, text="add more parameters", command=self.add_more_parameters_and_widgets)
        ttp_btn_add_more_parameters = ToolTip.CreateToolTip(self.btn_add_more_parameters, \
        'Adds another entry to write amplitudes into, also adds some default values at the end of the lists in the already existing entries.')
        self.btn_add_more_parameters.grid(padx=10, pady=10, sticky="sw", row=99, column=1)

        self.btn_remove_parameters = tk.Button(self, text="remove last parameters", command=self.remove_last_parameters)
        ttp_btn_remove_parameters = ToolTip.CreateToolTip(self.btn_remove_parameters, \
        'Removes the parameters for the last component.')
        self.btn_remove_parameters.grid(pady=10, sticky="se", row=99, column=2)

        self.btn_show_rSVs_as_reconstructed_by_initial_fit_param_values = tk.Button(self, text="show/update rSVs as reconstructed\nby initial values", command=self.update_show_rSVs_window)
        ttp_btn_show_rSVs_as_reconstructed_by_initial_fit_param_values = ToolTip.CreateToolTip(self.btn_show_rSVs_as_reconstructed_by_initial_fit_param_values, \
        'open or update a window to compare the weighted right singular vectors $\sigma_i * V_i$ (of the checked components) with the fit function $f_i$ as computed'
        ' from the entered initial fit parameter values', optional_x_direction_bump=150, optional_y_direction_bump=50)
        self.btn_show_rSVs_as_reconstructed_by_initial_fit_param_values.grid(row=2, column=3, rowspan=2, padx=3)

        self.focus_set()
        self.bind("<Return>", lambda x: self.update_show_rSVs_window())


    def get_summands_of_user_defined_fit_function_from_file(self, target_model_configuration_file):
        try:
            with open(target_model_configuration_file, mode='r') as dict_file:
                summands_of_user_defined_fit_function = ast.literal_eval(dict_file.read().strip())
        except (SyntaxError, FileNotFoundError):
            raise ValueError("getting the user defined summands for fit function from file failed, or the dict was empty.\n"
                            +"Check the file!\n"
                            +"computation is discontinued!")

        return summands_of_user_defined_fit_function

    def parse_summands_of_user_defined_fit_function_to_actual_code(self, all_summands_dict: dict):
        parsed_summands_list = []

        selected_components_summands_dict = {}
        for component in self.components_list:
            selected_components_summands_dict[f"summand_component{component}"] = all_summands_dict[f"summand_component{component}"]

        for summand_str in selected_components_summands_dict.values():
            parsed_summands_list.append(self.parse_summand(summand_str))

        return parsed_summands_list

    def parse_summand(self, summand_str: str):
        if summand_str == "":
            return "0"
        summand_str_with_time_delays_parsed = summand_str.replace("t", "time_delays")
        summand_str_with_decay_constants_parsed = summand_str_with_time_delays_parsed
        list_of_ks_in_summand_str = re.findall(r'k\d+', summand_str_with_time_delays_parsed)
        for k_str in list_of_ks_in_summand_str:
            summand_str_with_decay_constants_parsed = re.sub(r'k\d+', f"taus[\"component{k_str[1:]}\"]", summand_str_with_decay_constants_parsed, count=1)

        summand_str_with_brackets_added = "(" +summand_str_with_decay_constants_parsed+ ")"

        return summand_str_with_brackets_added

    def set_new_initial_values_dicts_for_compare_window(self):
        try:
            self.initial_decay_constants_dict={f'tau_component{component}':self.new_initial_fit_parameter_values["time_constants"][component] for component in self.components_list}

            self.initial_amplitude_values_dict = {}
            for component in self.components_list:
                for i in range(len(self.components_list)):
                    self.initial_amplitude_values_dict[f'amp_rSV{i}_component{component}'] = self.new_initial_fit_parameter_values[f'amps_rSV{i}'][component]
        except (IndexError, KeyError):
            tk.messagebox.showerror("Error", "you need to have at least as many initial fit parameter values (both time constants and amplitudes) as you have components selected!"+
                                             f"\nSelected components when you openend this window: {self.components_list}")
            self.lift()
            return "invalid"

        return "valid"

    def update_show_rSVs_window(self):
        if not hasattr(self, "compareWindow"):
            self.show_rightSVs_window()
            return None

        try:
            self.compareWindow.winfo_ismapped()

            if self.check_if_valid_numbers_entered() == "invalid":
                return None

            if self.set_new_initial_values_dicts_for_compare_window() == "invalid":
                return None

            self.compareWindow.reconstruct_rSVs_from_fit_results_using_intial_values(self.initial_decay_constants_dict, self.initial_amplitude_values_dict)

            self.compareWindow.update_axes()
        except AttributeError:
            self.show_rightSVs_window()

    def show_rightSVs_window(self):

        if self.check_if_valid_numbers_entered() == "invalid":
            return None

        if (self.data_file_name == "" or self.data_file_name == "no file selected"):
            tk.messagebox.showerror("Error", "For this you need to have selected a datafile first")
            self.lift()
            return None

        if self.set_new_initial_values_dicts_for_compare_window() == "invalid":
            return None

        try:
            self.data_matrix_complete, self.time_delays, self.wavelengths = get_TA_data_after_start_time.run(self.data_file_name, "-999999")
            if not self.matrix_bounds_dict == {}:
                self.data_matrix = self.data_matrix_complete[self.min_wavelength_index:self.max_wavelength_index+1, self.min_time_delay_index:self.max_time_delay_index+1]
                self.time_delays = self.time_delays[self.min_time_delay_index:self.max_time_delay_index+1]
                self.wavelengths = self.wavelengths[self.min_wavelength_index:self.max_wavelength_index+1]
            else:
                self.data_matrix = self.data_matrix_complete
            # set start time to the actual time delay that is closest to user input (is used in tab title)
            self.start_time = self.time_delays[0]
        except ValueError as error:
            tk.messagebox.showerror("error", str(error)+"\n\nTherefore you wont have any right singular vectors to compare.")
            self.lift()
            return None

        # self.time_delays = self.time_delays[self.time_delays.index(self.start_time):]

        # get the selected rSVs, singular values and lSVs - input is TA data after time and self.components_list
        self.retained_rSVs, self.retained_lSVs, self.retained_singular_values = get_retained_rightSVs_leftSVs_singularvs.run(self.data_matrix, self.components_list)

        # parse model function if used
        if self.use_user_defined_fit_function:
            try:
                self.summands_of_user_defined_fit_function = self.get_summands_of_user_defined_fit_function_from_file(self.target_model_configuration_file)
                self.parsed_summands_of_user_defined_fit_function = self.parse_summands_of_user_defined_fit_function_to_actual_code(self.summands_of_user_defined_fit_function)
            except ValueError as error:
                tk.messagebox.showerror("Warning,", "an exception occurred!""\nProbably due to a problem with the user defined fit function file!\n"+
                                    f"Exception {type(error)} message: \n"+ str(error)+"\n")
                self.lift()
                return None

        # make the window
        try:
            if not self.use_user_defined_fit_function:
                self.compareWindow = CompareRightSVsWithFit_Toplevel.CompareWindow(self.parent, self.use_user_defined_fit_function, 0, self.components_list, self.time_delays, self.retained_rSVs, self.retained_singular_values, self.initial_decay_constants_dict, self.initial_amplitude_values_dict, self.data_file_name, self.full_path_to_final_dir, is_from_initial_values_window=True, start_time=self.start_time, matrix_bounds_dict=self.matrix_bounds_dict)
            else:
                self.compareWindow = CompareRightSVsWithFit_Toplevel.CompareWindow(self.parent, self.use_user_defined_fit_function, 0, self.components_list, self.time_delays, self.retained_rSVs, self.retained_singular_values, self.initial_decay_constants_dict, self.initial_amplitude_values_dict, self.data_file_name, self.full_path_to_final_dir, parsed_summands_of_user_defined_fit_function=self.parsed_summands_of_user_defined_fit_function, is_from_initial_values_window=True, start_time=self.start_time, matrix_bounds_dict=self.matrix_bounds_dict)
            self.compareWindow.run()
        except KeyError as error:
            tk.messagebox.showerror("error", "an error occured when trying to open the window to compare the right SVs with the fit function output using the entered initial values!\n"
                                    +f"type of error: {type(error)}, \nerrormsg: {error}")
            self.lift()

        return None

    def remove_last_parameters(self):
        try:
            self.row_labels[-1].grid_forget()
            self.row_labels = self.row_labels[0:-1]

            self.new_values_entries[-1].grid_forget()
            self.new_values_entries = self.new_values_entries[0:-1]
        except IndexError:
            tk.messagebox.showwarning(title="Warning", message=f"No more parameters to remove!")
            self.lift()
            return None

        try:
            for entry_index, entry in enumerate(self.new_values_entries):
                curr_list = ast.literal_eval(self.new_values_entries[entry_index].get())
                entry.delete(0, len(str(curr_list)))
                curr_list = curr_list[0:-1]
                entry.insert(0, str(curr_list))
        except SyntaxError:
            tk.messagebox.showwarning(title="Warning.", message=f"One of your remaining entered lists could not be evaluated to a list.")
            self.lift()
            return None

        self.add_up_and_down_key_bindings_to_entries()

        return None

    def add_more_parameters_and_widgets(self):
        if self.new_values_entries != []:
            self.row_labels.append(tk.Label(self))
            self.row_labels[-1]["text"] = f"amps_rSV{len(self.row_labels)-2}"

            self.new_values_entries.append(tk.Entry(self, width=50, justify=tk.RIGHT))
            self.new_values_entries[-1].insert(0, self.new_values_entries[1].get())

            self.row_labels[-1].grid(padx=10, sticky="nsew", row=self.row_labels[-2].grid_info()["row"]+1, column=0)
            self.old_values_labels[-1].grid(padx=10, sticky="nsew", row=self.old_values_labels[-2].grid_info()["row"]+1, column=1)
            self.new_values_entries[-1].grid(sticky="nsew", row=self.new_values_entries[-2].grid_info()["row"]+1, column=2)

        else:
            self.old_initial_fit_parameter_values = {"time_constants": [50], "amps_rSV0": [0.7]}
            self.display_fit_parameters_labels_and_entries()
            return None

        for entry_index, entry in enumerate(self.new_values_entries):
            if self.new_values_entries[entry_index].get() == "":
                if entry_index == 0:
                    entry.insert(len(entry.get())-1, "[50]")
                else:
                    entry.insert(len(entry.get())-1, "[0.7]")
            else:
                try:
                    curr_list = ast.literal_eval(self.new_values_entries[entry_index].get())
                    if entry_index == 0:
                        if curr_list == []:
                            entry.insert(len(entry.get())-1, "50")
                        else:
                            entry.insert(len(entry.get())-1, ", 50")
                    else:
                        if curr_list == []:
                            entry.insert(len(entry.get())-1, "0.7")
                        else:
                            entry.insert(len(entry.get())-1, ", 0.7")
                except SyntaxError:
                    tk.messagebox.showwarning(title="Warning.", message=f"One of your remaining entered lists could not be evaluated to a list.")
                    self.lift()
                    return None

        self.add_up_and_down_key_bindings_to_entries()

        return None

    def display_help_window(self):
        helpful_information = """given a set of selected components, there will be a corresponding set of right singular vectors (rSV) V_i to fit.
        For each V_i there will be an individual fit function f_i.\n
        The generic fit function has nrOfSelectedComponents decay constants and
        nrOfSelectedComponents * nrOfSelectedComponents amplitudes.
        So all in all there are nrOfSelectedComponents * (nrOfSelectedComponents+1) parameters.

        The parameter lists in the entries each need to contain at least as many values as the maximum component nr + 1.
        I.e. if the selected components are [0,1,3]: each parameter list needs to contain at least 4 values,
        as the fit procedure tries to access these lists at the indeces corresponding to the selected componets list, e.g. [0,1,3].

        If that condition is not fulfilled, the fit procedure will use default parameters and inform you about the error.

        Pressing the 'use entered values' button attempts to parse the values to floats, if it fails you will be informed.
        """
        tk.messagebox.showinfo(title="hopefully helpful information window", message=re.sub('^[ \t]*',"",helpful_information, flags=re.MULTILINE), parent=self, default = "ok", )
        return None

    def add_up_and_down_key_bindings_to_entries(self):
        for i in range(len(self.new_values_entries)):
            if i+1 < len(self.new_values_entries):
                self.new_values_entries[i].bind("<Key-Down>", lambda event, idx=i: self.handle_down_key_press(event, idx))
            if i > 0:
                self.new_values_entries[i].bind("<Key-Up>", lambda event, idx=i: self.handle_up_key_press(event, idx))

        return None

    def display_fit_parameters_labels_and_entries(self):
        self.column_labels = [tk.Label(self, text="old values:"), tk.Label(self, text="new values:")]
        self.components_label = tk.Label(self, text="comp0, 1, 2, ...")
        self.components_label2 = tk.Label(self, text="comp0, 1, 2, ...")
        for index,col_label in enumerate(self.column_labels):
            col_label.grid(padx=10, sticky="nsew", row=0, column=index+1)
        self.components_label.grid(padx=10, sticky="nsew", row=1, column=1)
        self.components_label2.grid(padx=10, sticky="nsew", row=1, column=2)

        self.row_labels = []
        self.old_values_labels = []
        self.new_values_entries = []
        for i, (key, values) in enumerate(self.old_initial_fit_parameter_values.items()):
            self.row_labels.append(tk.Label(self, text=key))
            self.old_values_labels.append(tk.Label(self, text=str(values)))
            self.new_values_entries.append(tk.Entry(self, width=50, justify=tk.RIGHT))
            self.row_labels[i].grid(padx=10, sticky="nsew", row=i+2, column=0)
            self.old_values_labels[i].grid(padx=10, sticky="nsew", row=i+2, column=1)
            self.new_values_entries[i].insert(0, self.old_values_labels[i]["text"])
            self.new_values_entries[i].grid(sticky="nsew", row=i+2, column=2)

        self.add_up_and_down_key_bindings_to_entries()

        return None

    def handle_up_key_press(self, event, index):
        self.new_values_entries[index-1].focus()
        self.new_values_entries[index-1].icursor(tk.END)
        return None

    def handle_down_key_press(self, event, index):
        self.new_values_entries[index+1].focus()
        self.new_values_entries[index+1].icursor(tk.END)
        return None

    def traverse_list(self, data_item):
        if isinstance(data_item, list):
            for value in data_item:
                for subvalue in self.traverse_list(value):
                    yield subvalue
        else:
            yield data_item

    def entries_contain_number_strings_only(self):
        self.new_initial_fit_parameter_values = {}

        for i in range(len(self.new_values_entries)):
            if self.new_values_entries[i].get() == "[]":
                return "invalid"

        for i, label in enumerate(self.row_labels):
            try:
                curr_list = ast.literal_eval(self.new_values_entries[i].get())
            except (ValueError, SyntaxError):
                self.new_initial_fit_parameter_values = "invalid"
                break

            curr_list_contains_non_numeric_string = False

            # if there are nested lists in entries, break
            if (len(np.array(curr_list).shape) != 1):
                self.new_initial_fit_parameter_values = "invalid"
                break
            for nr_string in self.traverse_list(curr_list):
                if not self.string_is_number(str(nr_string)):
                    curr_list_contains_non_numeric_string = True
            if not curr_list_contains_non_numeric_string:
                self.new_initial_fit_parameter_values[label["text"]] = curr_list
            else:
                # if the parsing of one user entered values fails, i do not want to use any of them!
                self.new_initial_fit_parameter_values = "invalid"
                break

        return self.new_initial_fit_parameter_values

    def string_is_number(self, some_string):
        try:
            if some_string.lower() in ("nan", "-nan", "-inf", "inf"):
                return False
            if some_string == "0": return True
            float(some_string.lstrip("0"))   # lstrip("0") removes leading "0"s. i think at some point python uses octal numeral system (base 8) (if i did not remove leading "0"s)
            return True
        except ValueError:
            return False

    def check_if_valid_numbers_entered(self):
        self.new_initial_fit_parameter_values = self.entries_contain_number_strings_only()
        if self.new_initial_fit_parameter_values == "invalid":
            tk.messagebox.showwarning(title="Warning: parsing error.", message=f"Either your entered values could not be successfully parsed to floats,\n"+
                                                                                "or there is some other ploblem with your entered lists! Check them again.")

            self.lift()

        return self.new_initial_fit_parameter_values

    def assign_new_values_if_correct_format(self):
        self.check_if_valid_numbers_entered()
        if self.new_initial_fit_parameter_values == "invalid":
            return None

        # write user entered values to file, then assign them to parent object
        with open(file=self.intial_values_file_name, mode="w") as file:
            file.write(str(self.new_initial_fit_parameter_values))

        self.assign_handler(self.new_initial_fit_parameter_values)

        self.ignore_and_quit()

    def ignore_and_quit(self):
        if hasattr(self, "compareWindow"):
            try:
                self.compareWindow.delete_attrs_and_destroy()
            except AttributeError:
                pass # compareWindow has already been destroyed / closed

        self.delete_attrs_and_destroy()

    def delete_attrs_and_destroy(self):
        self.destroy()
        self.delete_attrs()

        return None

    def delete_attrs(self):
        attr_lst = list(vars(self))
        attr_lst.remove('parent')
        for attr in attr_lst:
            delattr(self, attr)

        del attr_lst

        gc.collect()

        return None
