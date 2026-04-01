'''
Change handlers for Quantrol GUI.

This module contains handlers for input changes, text edits, combo box selections,
and other state change events in the Quantrol control system.

Author  :   Alexei Gurchenko (refactored from source_code.py)
Email   :   alexei.gurchenko@ist.ac.at
Date    :   11.2025
Version :   2.3.3
Contact :   https://hostenlab.pages.ist.ac.at/contact/
'''

import json
import update
import config
from copy import deepcopy
from pathlib import Path
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton
from PyQt5.QtGui import QFont
from data_structures import Variable


# ==============================================================================
# INPUT CHANGE HANDLERS
# ==============================================================================

def handle_number_of_steps_input_changed(main_window):
    '''Update number of steps for scanning.'''
    if main_window.to_update:
        try:
            expression = main_window.number_of_steps_input.text()
            (expression, evaluation, for_python, is_scanned, is_ramped, is_sampled, is_derived, is_lookup) = main_window.decode_input(expression)
            exec("main_window.value = " + str(evaluation), {"main_window": main_window})
            if main_window.value > 0:
                main_window.experiment.number_of_steps = int(main_window.value)
            else:
                main_window.error_message("Only positive integers larger than 0 are allowed", "Wrong entry")
        except Exception:
            main_window.error_message("Expression can not be evaluated", "Wrong entry")
        main_window.update_off()
        main_window.number_of_steps_input.setText(str(main_window.experiment.number_of_steps))
        main_window.update_on()


def handle_number_of_runs_input_changed(main_window):
    '''Update number of runs for multiple run mode.'''
    if main_window.to_update:
        try:
            tab_names = [
                "number_of_runs_input",
                "number_of_runs_input_sequence",
                "number_of_runs_input_analog",
                "number_of_runs_input_digital",
                "number_of_runs_input_dds",
                "number_of_runs_input_mirny",
                "number_of_runs_input_sampler",
                "number_of_runs_input_variables",
                "number_of_runs_input_acquisition",
                "number_of_runs_input_slow_dds",
            ]
            var_table_names = [name for name in tab_names if hasattr(main_window, name)]
            for var_table_name in var_table_names:
                getattr(main_window, var_table_name).blockSignals(True)

            line = main_window.sender() if hasattr(main_window, "sender") else None
            active_line = line if hasattr(line, "text") else main_window.number_of_runs_input
            expression = active_line.text()
            (expression, evaluation, for_python, is_scanned, is_ramped, is_sampled, is_derived, is_lookup) = main_window.decode_input(expression)
            exec("main_window.value = " + str(evaluation), {"main_window": main_window})
            if main_window.value > 0:
                main_window.experiment.number_of_runs = int(main_window.value)
            else:
                main_window.error_message("Only positive integers larger than 0 are allowed", "Wrong entry")
        except Exception:
            main_window.error_message("Expression can not be evaluated", "Wrong entry")
        finally:
            main_window.update_off()
            for var_table_name in var_table_names:
                getattr(main_window, var_table_name).setText(str(main_window.experiment.number_of_runs))
            main_window.update_on()
            for var_table_name in var_table_names:
                getattr(main_window, var_table_name).blockSignals(False)


def handle_experiment_caption_changed(main_window):
    """Prompt the user for a replacement caption for the selected experiment."""
    main_window.dialog = QDialog()
    main_window.dialog.setGeometry(*main_window.scale_geom(710, 435, 600, 200))
    main_window.dialog.setFont(QFont('Arial', main_window.scale_font(14)))
    value_input_cap = QLineEdit()
    value_input_cap.setPlaceholderText("Type the x-caption for the experiment (Example: 'TOF, ms')")
    dialog_layout = QVBoxLayout()
    button_update = QPushButton("Update")
    button_cancel = QPushButton("Cancel")
    dialog_layout.addWidget(value_input_cap)
    dialog_buttons_layout = QHBoxLayout()
    dialog_buttons_layout.addWidget(button_update)
    dialog_buttons_layout.addWidget(button_cancel)
    dialog_layout.addLayout(dialog_buttons_layout)
    main_window.dialog.setLayout(dialog_layout)

    button_update.clicked.connect(lambda: main_window.update_experiment_names_list(caption=value_input_cap.text(), last=False))
    button_cancel.clicked.connect(lambda: main_window.dialog.reject())
    main_window.dialog.setWindowTitle("Change experiment caption")
    main_window.dialog.exec_()


# ==============================================================================
# CAMERA HANDLERS
# ==============================================================================

def handle_camera_which_cam_changed(main_window):
    """Sync camera selections with stored metadata and serial numbers."""
    text_ = main_window.which_cam_combo.currentText()
    main_window.experiment.experimental_data.camera.camera_name = text_
    serial_number = config.camera_serial_numbers_dict.get(text_)
    main_window.experiment.experimental_data.camera.serial_number = serial_number if serial_number is not None else ''


def handle_camera_gain_changed(main_window):
    """Validate the gain entry and apply it to the experiment model."""
    if getattr(main_window, "_camera_gain_handling", False):
        return
    main_window._camera_gain_handling = True
    try:
        gain_text = main_window.gain_edit.text().strip()
        previous_gain = main_window.experiment.experimental_data.camera.gain_db
        if gain_text == "":
            main_window.error_message("Gain cannot be empty", "Wrong entry")
            main_window.gain_edit.setText(str(previous_gain))
            return
        try:
            gain_value = float(gain_text)
        except ValueError:
            main_window.error_message("Gain must be a number", "Wrong entry")
            main_window.gain_edit.setText(str(previous_gain))
            return

        gain_bounds = getattr(config, "camera_gain_minmax", None)
        if isinstance(gain_bounds, (list, tuple)) and len(gain_bounds) == 2:
            try:
                gain_min = float(gain_bounds[0])
                gain_max = float(gain_bounds[1])
                if gain_min > gain_max:
                    gain_min, gain_max = gain_max, gain_min
                if gain_value < gain_min or gain_value > gain_max:
                    main_window.error_message(
                        f"Value for Gain should be within [{gain_min}, {gain_max}]",
                        "Wrong entry",
                    )
                    main_window.gain_edit.setText(str(previous_gain))
                    return
            except (TypeError, ValueError):
                pass

        main_window.experiment.experimental_data.camera.gain_db = gain_value
        main_window.gain_edit.setText(str(gain_value))
    finally:
        main_window._camera_gain_handling = False


def handle_camera_exposure_changed(main_window):
    """Update camera exposure and ensure the T_exp_ variable stays in sync."""
    if getattr(main_window, "_camera_exposure_handling", False):
        return
    main_window._camera_exposure_handling = True
    try:
        texp_key = "T_exp_"
        texp_str = main_window.exposure_edit.text().strip()
        previous_texp = main_window.experiment.experimental_data.camera.exposure_time_ms
        if texp_str == "":
            main_window.error_message("Exposure time cannot be empty", "Wrong entry")
            main_window._set_camera_exposure_line(previous_texp)
            return
        try:
            texp_ = float(texp_str)
        except ValueError:
            main_window.error_message("Exposure time must be a number", "Wrong entry")
            main_window._set_camera_exposure_line(previous_texp)
            return

        exposure_bounds_ms = None
        exposure_bounds_us = getattr(config, "camera_exp_us_minmax", None)
        if isinstance(exposure_bounds_us, (list, tuple)) and len(exposure_bounds_us) == 2:
            try:
                exposure_bounds_ms = [float(exposure_bounds_us[0]) / 1000.0, float(exposure_bounds_us[1]) / 1000.0]
            except (TypeError, ValueError):
                exposure_bounds_ms = None
        if exposure_bounds_ms is None:
            exposure_bounds = getattr(config, "camera_exp_minmax", None)
            if isinstance(exposure_bounds, (list, tuple)) and len(exposure_bounds) == 2:
                try:
                    exposure_bounds_ms = [float(exposure_bounds[0]), float(exposure_bounds[1])]
                except (TypeError, ValueError):
                    exposure_bounds_ms = None

        if exposure_bounds_ms is not None:
            exposure_min, exposure_max = exposure_bounds_ms
            if exposure_min > exposure_max:
                exposure_min, exposure_max = exposure_max, exposure_min
            if texp_ < exposure_min or texp_ > exposure_max:
                min_display = f"{exposure_min:g}"
                max_display = f"{exposure_max:g}"
                main_window.error_message(
                    f"Value of exposure time should be within [{min_display}, {max_display}] ms",
                    "Wrong entry",
                )
                main_window._set_camera_exposure_line(previous_texp)
                return

        main_window.experiment.experimental_data.camera.exposure_time_ms = texp_
        main_window._set_camera_exposure_line(texp_)

        index = main_window._get_texp_variable_index()
        if index is None:
            variable = Variable(texp_key, texp_, texp_)
            main_window.experiment.variables[texp_key] = variable
            main_window.experiment.new_variables.append(variable)
        else:
            variable = main_window.experiment.new_variables[index]
            variable.value = texp_
            variable.for_python = texp_
            main_window.experiment.variables[texp_key].value = texp_
            main_window.experiment.variables[texp_key].for_python = texp_

        update.variable_tables(main_window)
    finally:
        main_window._camera_exposure_handling = False


def handle_camera_image_format_changed(main_window):
    """Persist the chosen image format for camera acquisitions."""
    main_window.experiment.experimental_data.camera.format_name = main_window.format_combo.currentText()


# ==============================================================================
# TABLE CHANGE HANDLERS
# ==============================================================================

def handle_sequence_table_changed(main_window, item):
    '''
    This function is triggered when the sequence table entry is changed. There are two possible locations of the change.
    column 1 corresponds to the change of the name of the edge
            This will just reassign the edge.name parameter to the new value.
    column 3 corresponds to the change of the time expression. There are two distinct cases for user entry
            1) when the entry is empty, then it will assign the previous edge values and update the table entries accordingly
            2) when the entru is not empty it will try to evaluate it and in case of positive result assign it to the edge
               and update the table. Otherwise it will throw an error
    Function takes no inputs, item is an internal variable that has information of the row and column of the entry that has been changed
    '''
    if main_window.to_update:
        row = item.row()
        col = item.column()
        edge = main_window.experiment.sequence[row]
        table_item = main_window.sequence_table.item(row,col)
        if col == 1: # edge name changed
            edge.name = table_item.text()
            update.from_object(main_window)
        elif col == 3: # edge time expression changed
            if table_item.text() == "":
                #previous edge values
                edge.expression = main_window.experiment.sequence[row-1].expression #previous edge
                edge.evaluation = main_window.experiment.sequence[row-1].evaluation #previous edge
                edge.value = main_window.experiment.sequence[row-1].value #previous edge
                edge.for_python = main_window.experiment.sequence[row-1].for_python #previous edge
                #updating table entry
                main_window.update_off()
                table_item.setText(edge.expression)
                main_window.update_on()
            else:                        
                try:
                    expression = table_item.text()
                    (expression, evaluation, for_python, is_scanned, is_ramped, is_sampled, is_derived, is_lookup) = main_window.decode_input(expression)
                    exec("main_window.value = " + str(evaluation), {"self": main_window, "main_window": main_window}) # this is done here to be able to assign value of the id# type variable
                    if main_window.value < 0: #restricting negative values for time
                        main_window.error_message("Negative values are not allowed", "Negative time value")
                        main_window.update_off()
                        table_item.setText(str(edge.expression))
                        main_window.update_on()
                    else:
                        edge.value = main_window.value
                        edge.evaluation = evaluation
                        edge.expression = expression
                        edge.for_python = for_python
                        edge.is_scanned = is_scanned
                        edge.is_ramped = is_ramped
                        main_window.experiment.variables[edge.id] = Variable(name = edge.id, value = edge.value, for_python = edge.for_python, is_scanned = edge.is_scanned, is_ramped = edge.is_ramped)
                        update.sequence_tab(main_window) 
                        update.from_object(main_window)
                except:
                    main_window.error_message("Expression can not be evaluated", "Wrong entry")
                    main_window.update_off()
                    table_item.setText(str(edge.expression))
                    main_window.update_on()


def handle_scan_table_changed(main_window, item):
    '''
    Function is used when the user changes parameter of a scan table.
    Function takes no inputs, item is an internal variable that has information of the row and column of the entry that has been changed
    '''
    if main_window.to_update:
        row = item.row()
        col = item.column()
        table_item = main_window.scan_table_parameters.item(row, col)
        variable = main_window.experiment.scanned_variables[row]
        if col == 4: # Dim (ordering) changed (Dim is last column)
            try:
                new_dim = int(table_item.text())
                if new_dim <= 0:
                    raise ValueError
                variable.Dim = new_dim
            except Exception:
                main_window.error_message("Only positive integers larger than 0 are allowed", "Wrong entry")
                main_window.update_off()
                # reset display to current value
                dim_display = getattr(variable, 'Dim', row+1)
                main_window.scan_table_parameters.item(row, 4).setText(str(dim_display))
                main_window.update_on()
            else:
                # Reorder scanned_variables according to Dim (ascending). Missing dims go to the end preserving original order.
                enumerated = [(v, i) for i, v in enumerate(main_window.experiment.scanned_variables)]
                def sort_key(pair):
                    v, idx = pair
                    return (v.Dim if (getattr(v, 'Dim', None) is not None) else 10**9, idx)
                enumerated_sorted = sorted(enumerated, key=sort_key)
                main_window.experiment.scanned_variables = [v for v, _ in enumerated_sorted]
                # Reassign per-variable step indices (for_python) for remaining scanned variables
                for i, rem_var in enumerate(main_window.experiment.scanned_variables):
                    if rem_var.name != "None" and rem_var.name in main_window.experiment.variables:
                        main_window.experiment.variables[rem_var.name].is_scanned = True
                        main_window.experiment.variables[rem_var.name].for_python = "self.%s[step%d]" % (rem_var.name, i+1)
        elif col == 0: #name of the scanned variable changed
            new_variable_name = main_window.remove_restricted_characters(table_item.text())
            table_item.setText(new_variable_name)
            if main_window.check_if_already_scanned(new_variable_name) == False: #Check if the given variable is defined previously or not
                index = main_window.index_of_a_new_variable(new_variable_name)
                if main_window.index_of_a_new_variable(new_variable_name) != None: #Check if the varible name is defined in Variables tab
                    if new_variable_name not in main_window.experiment.sampler_variables: #Check if the variable name is used for sampling
                        #Proceeding with changes
                        prev_index = main_window.index_of_a_new_variable(variable.name)
                        if prev_index != None: #make the value of variable to the previous before being scanned.
                            #reverting the values to before scanning values and scanning states of the previous variable
                            main_window.experiment.variables[variable.name].value = main_window.experiment.new_variables[prev_index].value 
                            main_window.experiment.variables[variable.name].is_scanned = False 
                            main_window.experiment.variables[variable.name].for_python = main_window.experiment.variables[variable.name].value
                            main_window.experiment.new_variables[prev_index].is_scanned = False
                        #updating the values and scanning states of the new scanning  variable
                        variable.name = new_variable_name
                        main_window.experiment.variables[variable.name].value = variable.min_val
                        main_window.experiment.variables[variable.name].for_python = "self." + variable.name + "[step%d]" % (row+1)
                        main_window.experiment.variables[variable.name].is_scanned = True
                        main_window.experiment.new_variables[index].is_scanned = True
                    else: #The variable name enteres is used in sampler tab
                        main_window.error_message("The variable name you entered was already used in sampler tab", "Used variable name")
                        main_window.update_off()
                        table_item.setText(variable.name)
                        main_window.update_on()                            
                else: #The variable name entered is not defined in a variables tab
                    main_window.error_message("The variable name you entered was not defined in variables tab", "Not defined variable")
                    main_window.update_off()
                    table_item.setText(variable.name)
                    main_window.update_on()
            else:
                main_window.error_message("The variable name you entered was already used for scanning.", "Scanning variable duplicate")
            main_window.count_scanned_variables()
        elif col == 1: #min_val of the scanned variable changed
            try:
                variable.min_val = float(table_item.text())
                table_item.setText(str(variable.min_val))
                if main_window.scan_table_parameters.item(row, 0).text() != "None": # this makes sure that we do not have to deal with "None" named variable
                    # we use the min values in order to use in sorting of the sequence tab
                    main_window.experiment.variables[variable.name].value = variable.min_val
            except:
                main_window.error_message("Expression can not be evaluated", "Wrong entry")
        elif col == 2: #max_val of the scanned variable changed
            try:
                variable.max_val = float(table_item.text())
                table_item.setText(str(variable.max_val))
            except:
                main_window.error_message("Expression can not be evaluated", "Wrong entry")
        elif col == 3: # number of scans for this scanned variable
            try:
                expression = table_item.text()
                (expression, evaluation, for_python, is_scanned, is_ramped, is_sampled, is_derived, is_lookup) = main_window.decode_input(expression)
                exec("main_window.value = " + str(evaluation), {"main_window": main_window})
                if int(main_window.value) > 0:
                    variable.num_scan_steps = int(main_window.value)
                    table_item.setText(str(variable.num_scan_steps))
                else:
                    main_window.error_message("Only positive integers larger than 0 are allowed", "Wrong entry")
            except Exception:
                main_window.error_message("Expression can not be evaluated", "Wrong entry")
        update.digital_analog_dds_mirny_tabs(main_window)
        update.variable_tables(main_window)
        update.scan_table(main_window)


def handle_cam_trigger_off_input_changed(main_window):
    '''
    analog to number_of_steps_input_changed
    '''
    if main_window.to_update: 
        try:
            expression = main_window.cam_trigger_off_input.text()
            (expression, evaluation, for_python, is_scanned, is_ramped, is_sampled, is_derived, is_lookup) = main_window.decode_input(expression)
            exec("main_window.value = " + str(evaluation))
            if main_window.value > 0: 
                main_window.experiment.cam_trigger_off_runs = int(main_window.value)
            else:
                main_window.error_message("Only positive integers larger than 0 are allowed", "Wrong entry")    
        except:
            main_window.error_message("Expression can not be evaluated", "Wrong entry")
        main_window.update_off()
        main_window.cam_trigger_off_input.setText(str(main_window.experiment.cam_trigger_off_runs))
        main_window.update_on()


def handle_ramp_table_changed(main_window, item):
    '''
    analog to scan_table_changed
    '''
    if main_window.to_update:
        row = item.row()
        col = item.column()
        table_item = main_window.ramp_table_parameters.item(row, col)
        variable = main_window.experiment.ramped_variables[row] 
        if col == 0: #name of the ramped variable changed
            new_variable_name = main_window.remove_restricted_characters(table_item.text())
            table_item.setText(new_variable_name)
            if main_window.check_if_already_ramped(new_variable_name) == False: #Check if the given variable is defined previously or not
                index = main_window.index_of_a_new_variable(new_variable_name)
                if main_window.index_of_a_new_variable(new_variable_name) != None: #Check if the varible name is defined in Variables tab
                    if new_variable_name not in main_window.experiment.sampler_variables: #Check if the variable name is used for sampling
                        #Proceeding with changes
                        prev_index = main_window.index_of_a_new_variable(variable.name)
                        if prev_index != None: #make the value of variable to the previous before being ramped.
                            #reverting the values to before ramping values and ramping states of the previous variable
                            main_window.experiment.variables[variable.name].functionramp = main_window.experiment.new_variables[prev_index].value
                            main_window.experiment.variables[variable.name].is_ramped = False
                            main_window.experiment.variables[variable.name].for_python = main_window.experiment.variables[variable.name].functionramp
                            main_window.experiment.new_variables[prev_index].is_ramped = False
                        #updating the values and ramping states of the new ramping variable
                        variable.name = new_variable_name
                        main_window.experiment.variables[variable.name].functionramp = variable.functionramp
                        main_window.experiment.variables[variable.name].for_python = str(variable.functionramp)
                        main_window.experiment.variables[variable.name].is_ramped = True
                        main_window.experiment.new_variables[index].is_ramped = True
                    else: #The variable name enteres is used in sampler tab
                        main_window.error_message("The variable name you entered was already used in sampler tab", "Used variable name")
                        main_window.update_off()
                        table_item.setText(variable.name)
                        main_window.update_on()                            
                else: #The variable name entered is not defined in a variables tab
                    main_window.error_message("The variable name you entered was not defined in variables tab", "Not defined variable")
                    main_window.update_off()
                    table_item.setText(variable.name)
                    main_window.update_on()
            else:
                main_window.error_message("The variable name you entered was already used for ramping.", "Ramping variable duplicate")
            main_window.count_ramped_variables()
        elif col == 1: #start_ID changed 
            try:
                variable.start_ID = str(table_item.text()) 
                table_item.setText(str(variable.start_ID)) 
            except:
                main_window.error_message("Expression can not be evaluated", "Wrong entry")
            try:
                if main_window.experiment.do_ramp == True:
                    main_window.update_sequence_edge_colors()
            except:
                pass
        elif col == 2: #end_ID changed 
            try:
                variable.end_ID = str(table_item.text()) 
                table_item.setText(str(variable.end_ID)) 
            except:
                main_window.error_message("Expression can not be evaluated", "Wrong entry")
            try:
                if main_window.experiment.do_ramp == True:
                    main_window.update_sequence_edge_colors()
            except:
                pass
        elif col == 3: #functionramp changed
            try:
                variable.functionramp = str(table_item.text())
                table_item.setText(str(variable.functionramp))
                main_window.experiment.variables[variable.name].for_python = str(variable.functionramp)
            except:
                main_window.error_message("Expression can not be evaluated", "Wrong entry")
        elif col == 4:  #stepsramp changed
            try:
                variable.stepsramp = int(table_item.text())
                table_item.setText(str(variable.stepsramp))
            except:
                main_window.error_message("Expression can not be evaluated", "Wrong entry")

        update.digital_analog_dds_mirny_tabs(main_window)
        update.variable_tables(main_window)
        update.ramp_table(main_window)


def handle_digital_table_changed(main_window, item):
    '''
    Function is used when the user changes the values in the digital table. It ensures that the expressions are integer values
    0 or 1. The user can delete the input and the function will assign the value of the previous edge and unhighlight the channel
    indicating that it should not be changed and will only display previously set value.
    '''
    if main_window.to_update:
        row = item.row()
        col = item.column()
        table_item = main_window.digital_table.item(row,col)
        channel = main_window.experiment.sequence[row].digital[col-4]
        if table_item.text() == "": #User deleted the value. The function will display the previously set state
            if row == 0: #default edge 
                main_window.error_message("You can not delete initial value!", "Default value is protected!")
                main_window.update_off()
                table_item.setText(channel.expression)
                main_window.update_on()
            else:
                channel.changed = False
                update.digital_tab(main_window)
        else:   #User entered a new state
            try: 
                #Checking whether the expression can be evaluated and the value is within allowed range
                expression = table_item.text()
                (expression, evaluation, for_python, is_scanned, is_ramped, is_sampled, is_derived, is_lookup) = main_window.decode_input(expression)
                exec("main_window.value = " + evaluation, {"self": main_window, "main_window": main_window})
                if (main_window.value == 0 or main_window.value == 1):
                    channel.changed = True
                    update.digital_tab(main_window)
                else:
                    #Reverting back the previously accepted expression
                    main_window.update_off()
                    table_item.setText(str(channel.expression))
                    main_window.update_on()
                    main_window.error_message("Only value '1' or '0' are expected!", "Wrong entry!")
            except:
                #Return the previously assigned value if the expression can not be evaluated
                main_window.update_off()
                if channel.changed:
                    table_item.setText(channel.expression)
                else:
                    table_item.setText(str(channel.value))
                main_window.update_on()
                main_window.error_message("Expression can not be evaluated", "Wrong entry")


def handle_analog_table_changed(main_window, item):
    '''
    Function is used when the user changes the values in the analog table. It ensures that the expressions are float values in the 
    range between -9.9 to +9.9. The user can delete the input and the function will assign the value of the previous edge and unhighlight the channel
    indicating that it should not be changed and will only display previously set value.
    '''
    if main_window.to_update:
        row = item.row()
        col = item.column()
        channel = main_window.experiment.sequence[row].analog[col - 4]
        table_item = main_window.analog_table.item(row,col)
        if table_item.text() == "": #User deleted the value. The function will display the previously set state
            if row == 0: # default edge
                main_window.error_message("You can not delete initial value!", "Initial value is needed!")
                main_window.update_off()
                table_item.setText(channel.expression)
                main_window.update_on()
            else:
                channel.changed = False
                update.analog_tab(main_window)
        else: #User entered a new state
            try:
                #Checking whether the expression can be evaluated and the value is within allowed range                    
                expression = table_item.text()
                (expression, evaluation, for_python, is_scanned, is_ramped, is_sampled, is_derived, is_lookup) = main_window.decode_input(expression)
                exec("main_window.value =" + evaluation, {"self": main_window, "main_window": main_window})
                if (main_window.value <= 9.9 and main_window.value >= -9.9):
                    channel.expression = expression
                    channel.evaluation = evaluation
                    channel.value = main_window.value
                    channel.is_scanned = is_scanned
                    channel.is_ramped = is_ramped 
                    channel.for_python = for_python 
                    channel.changed = True
                    update.analog_tab(main_window)
                else:
                    #Reverting back the previously accepted expression                    
                    main_window.update_off()
                    table_item.setText(channel.expression)
                    main_window.update_on()
                    main_window.error_message("Only values between '+9.9' and '-9.9' are expected", "Wrong entry")
            except:
                #Return the previously assigned value if the expression can not be evaluated                    
                main_window.update_off()
                table_item.setText(channel.expression)
                main_window.update_on()
                main_window.error_message('Expression can not be evaluated', 'Wrong entry')


def handle_dds_table_changed(main_window, item):
    '''
    Function is used when the user changes the values in the dds table. It ensures that the expressions can be evaluated in the
    allowed input values range. The user can delete the input and the function will assign the value of the previous edge and 
    unhighlight the channel indicating that it should not be changed and will only display previously set value.
    '''        
    if main_window.to_update:
        row = item.row()
        col = item.column()
        edge_num = row
        channel = (col - 1)//6 #4 columns for edge and separation. division by 5 channel settings and 1 separation
        setting = col - 1 - 6 * channel # the number is a sequential value of setting. Frequency is 0, Amplitude 1, attenuation 2, phase 3, state 4
        if main_window.dds_table.item(row,col).text() == "": #User deleted the value. The function will display the previously set state
            if edge_num == 0: #Default edge
                main_window.error_message("You can not delete initial value!", "Initial value is needed!")
                main_window.update_off()
                exec("main_window.dds_table.item(row,col).setText(str(main_window.experiment.sequence[edge_num].dds[channel].%s.expression))" %main_window.setting_dict[setting])
                main_window.update_on()
            else: #Other than a default edge
                #Removing background color
                main_window.update_off()
                for index_setting in range(5):
                    main_window.dds_table.item(row, channel*6 + 1 + index_setting).setBackground(main_window.white)
                main_window.experiment.sequence[edge_num].dds[channel].changed = False
                main_window.update_on()
                update.dds_tab(main_window)
        else:   #User entered a new input value
            try:
                #Checking whether the expression can be evaluated and the value is within allowed range                     
                expression = main_window.dds_table.item(row,col).text()
                (expression, evaluation, for_python, is_scanned, is_ramped, is_sampled, is_derived, is_lookup) = main_window.decode_input(expression)
                exec("main_window.dummy_val =" + evaluation, {"self": main_window, "main_window": main_window})
                maximum, minimum = main_window.max_dict_dds[setting], main_window.min_dict_dds[setting]
                if (main_window.dummy_val <= maximum and main_window.dummy_val >= minimum): 
                    exec("main_window.experiment.sequence[edge_num].dds[channel].%s.expression = expression" %main_window.setting_dict[setting])
                    exec("main_window.experiment.sequence[edge_num].dds[channel].%s.evaluation = evaluation" %main_window.setting_dict[setting])
                    exec("main_window.experiment.sequence[edge_num].dds[channel].%s.for_python = for_python" %main_window.setting_dict[setting])
                    exec("main_window.experiment.sequence[edge_num].dds[channel].%s.value = main_window.dummy_val" %main_window.setting_dict[setting])
                    exec("main_window.experiment.sequence[edge_num].dds[channel].%s.for_python = for_python" %main_window.setting_dict[setting])
                    main_window.experiment.sequence[edge_num].dds[channel].changed = True
                    update.dds_tab(main_window)
                else:
                    #Reverting back the previously accepted expression                            
                    main_window.error_message("Only values between %f and %f are expected" %(minimum, maximum), "Wrong entry")
                    main_window.update_off()
                    exec("main_window.dds_table.item(row,col).setText(str(main_window.experiment.sequence[edge_num].dds[channel].%s.expression))" %main_window.setting_dict[setting])
                    main_window.update_on()
            except:
                #Return the previously assigned value if the expression can not be evaluated                       
                main_window.update_off()
                exec("main_window.dds_table.item(row,col).setText(str(main_window.experiment.sequence[edge_num].dds[channel].%s.expression))" %main_window.setting_dict[setting])
                main_window.update_on()
                main_window.error_message('Expression can not be evaluated', 'Wrong entry')


def handle_dds_table_header_changed(main_window, item):
    '''
    Function is used when the user wants to change the name of the dds title. 
    It overwrites the value of the corresponding title name in the experiment object so when it is saved the changes are persitent.
    '''
    if main_window.to_update:
        col = item.column()
        print(col)
        main_window.experiment.title_dds_tab[(col - 1)//6 + 4] = main_window.dds_table_header.item(0,col).text() # title has 3 leading names and a separator


def handle_mirny_table_changed(main_window, item):
    '''
    Function is used when the user changes the values in the mirny table. It ensures that the expressions can be evaluated in the
    allowed input values range. The user can delete the input and the function will assign the value of the previous edge and 
    unhighlight the channel indicating that it should not be changed and will only display previously set value.
    '''        
    if main_window.to_update:
        row = item.row()
        col = item.column()
        if col % 6 == 0:
            return
        edge_num = row
        channel = col // 6
        setting = col - (channel * 6) - 1 # Frequency is 0, Amplitude 1, attenuation 2, phase 3, state 4
        if edge_num < 0 or edge_num >= len(main_window.experiment.sequence):
            return
        if main_window.mirny_table.item(row,col).text() == "": #User deleted the value. The function will display the previously set state
            if edge_num == 0: #Default edge
                main_window.error_message("You can not delete initial value!", "Initial value is needed!")
                main_window.update_off()
                exec("main_window.mirny_table.item(row,col).setText(str(main_window.experiment.sequence[edge_num].mirny[channel].%s.expression))" %main_window.setting_dict[setting])
                main_window.update_on()
            else: #Other than a default edge
                #Removing background color
                main_window.update_off()
                for index_setting in range(5):
                    cell = main_window.mirny_table.item(row, channel*6 + 1 + index_setting)
                    if cell is not None:
                        cell.setBackground(main_window.white)
                main_window.experiment.sequence[edge_num].mirny[channel].changed = False
                main_window.update_on()
                update.mirny_tab(main_window)
        else:   #User entered a new input value
            try:
                #Checking whether the expression can be evaluated and the value is within allowed range                     
                expression = main_window.mirny_table.item(row,col).text()
                (expression, evaluation, for_python, is_scanned, is_ramped, is_sampled, is_derived, is_lookup) = main_window.decode_input(expression)
                exec("main_window.dummy_val =" + evaluation, {"self": main_window, "main_window": main_window})
                maximum, minimum = main_window.max_dict_mirny[setting], main_window.min_dict_mirny[setting]
                if (main_window.dummy_val <= maximum and main_window.dummy_val >= minimum): 
                    exec("main_window.experiment.sequence[edge_num].mirny[channel].%s.expression = expression" %main_window.setting_dict[setting])
                    exec("main_window.experiment.sequence[edge_num].mirny[channel].%s.evaluation = evaluation" %main_window.setting_dict[setting])
                    exec("main_window.experiment.sequence[edge_num].mirny[channel].%s.for_python = for_python" %main_window.setting_dict[setting])
                    exec("main_window.experiment.sequence[edge_num].mirny[channel].%s.value = main_window.dummy_val" %main_window.setting_dict[setting])
                    exec("main_window.experiment.sequence[edge_num].mirny[channel].%s.for_python = for_python" %main_window.setting_dict[setting])
                    main_window.experiment.sequence[edge_num].mirny[channel].changed = True
                    update.mirny_tab(main_window)
                else:
                    #Reverting back the previously accepted expression                            
                    main_window.error_message("Only values between %f and %f are expected" %(minimum, maximum), "Wrong entry")
                    main_window.update_off()
                    exec("main_window.mirny_table.item(row,col).setText(str(main_window.experiment.sequence[edge_num].mirny[channel].%s.expression))" %main_window.setting_dict[setting])
                    main_window.update_on()
            except:
                #Return the previously assigned value if the expression can not be evaluated                       
                main_window.update_off()
                exec("main_window.mirny_table.item(row,col).setText(str(main_window.experiment.sequence[edge_num].mirny[channel].%s.expression))" %main_window.setting_dict[setting])
                main_window.update_on()
                main_window.error_message('Expression can not be evaluated', 'Wrong entry')


def handle_mirny_dummy_header_changed(main_window, item):
    '''
    Function is used when the user wants to change the name of the mirny title. 
    It overwrites the value of the corresponding title name in the experiment object so when it is saved the changes are persitent.
    '''
    if main_window.to_update:
        col = item.column()
        row = item.row()
        if row == 0 and col % 6 == 1:
            channel_index = col // 6
            target_index = channel_index + 4
            while len(main_window.experiment.title_mirny_tab) <= target_index:
                main_window.experiment.title_mirny_tab.append(f"M{len(main_window.experiment.title_mirny_tab) - 4}")
            main_window.experiment.title_mirny_tab[target_index] = main_window.mirny_dummy_header.item(0,col).text()


def handle_slow_dds_table_changed(main_window, item):
    '''
    Function is used when the user changes the values in the slow_dds table. It ensures that the expressions can be evaluated in the
    allowed input values range. The user can delete the input and the function will assign the value of the previous edge and 
    unhighlight the channel indicating that it should not be changed and will only display previously set value.
    '''        
    if main_window.to_update:
        row = item.row()
        col = item.column()
        channel = (col - 1)//6 #4 columns for edge and separation. division by 5 channel settings and 1 separation
        setting = col - 1 - 6 * channel # the number is a sequential value of setting. Frequency is 0, Amplitude 1, attenuation 2, phase 3, state 4
        if row == 2: #Table entry was changed
            if main_window.slow_dds_table.item(row,col).text() == "": #User deleted the value. The function will display the previously set state
                main_window.error_message("You can not delete the value!", "Some value is required!")
                main_window.update_off()
                exec("main_window.slow_dds_table.item(row,col).setText(str(main_window.experiment.slow_dds[channel].%s))" %main_window.setting_dict[setting])
                exec("main_window.slow_dds_table.item(row,col).setToolTip(str(main_window.experiment.slow_dds[channel].%s))" %main_window.setting_dict[setting])
                main_window.update_on()
            else:   #User entered a new input value
                try:
                    #Checking whether the expression can be evaluated and the value is within allowed range                     
                    expression = main_window.slow_dds_table.item(row,col).text()
                    (expression, evaluation, for_python, is_scanned, is_ramped, is_sampled, is_derived, is_lookup) = main_window.decode_input(expression)
                    exec("main_window.dummy_val =" + evaluation)
                    maximum, minimum = main_window.max_dict_dds[setting], main_window.min_dict_dds[setting]
                    if (main_window.dummy_val <= maximum and main_window.dummy_val >= minimum): #Change accepted
                        if setting == 0: #frequency
                            main_window.dummy_val = float(main_window.dummy_val) #Was checked to have at least a 1 Hz level resolution
                        elif setting == 1: #amplitude
                            main_window.dummy_val = int(float(main_window.dummy_val)*1000)/1000 # Keep only up to 3rd digit (0.1234 --> 0.123)
                        elif setting == 2: #attenuation
                            main_window.dummy_val = round(float(main_window.dummy_val)/0.5)*0.5 #Round up to 0.5
                        elif setting == 3: #phase
                            main_window.dummy_val = round(float(main_window.dummy_val)/0.36)*0.36 # Keep only up to 3rd digit (0.1234 --> 0.123) of phase that is represented as 1 -- > 360. 0.001 --> 0.36 in degrees 
                        elif setting == 4: #state
                            main_window.dummy_val = int(main_window.dummy_val)
                        exec("main_window.experiment.slow_dds[channel].%s = main_window.dummy_val" %main_window.setting_dict[setting])
                        main_window.update_off()
                        exec("main_window.slow_dds_table.item(row,col).setText(str(main_window.experiment.slow_dds[channel].%s))" %main_window.setting_dict[setting])
                        exec("main_window.slow_dds_table.item(row,col).setToolTip(str(main_window.experiment.slow_dds[channel].%s))" %main_window.setting_dict[setting])
                        main_window.update_on()
                        for parameter in range(5): #Changing the color of the entire channel
                            if main_window.experiment.slow_dds[channel].state == 1:
                                main_window.update_off()
                                main_window.slow_dds_table.item(row,(col - 1)//6 * 6 + parameter + 1).setBackground(main_window.green)
                                main_window.update_on()
                            else:
                                main_window.update_off()
                                main_window.slow_dds_table.item(row,(col - 1)//6 * 6 + parameter + 1).setBackground(main_window.red)
                                main_window.update_on()
                    else:
                        #Reverting back the previously accepted expression                            
                        main_window.error_message("Only values between %f and %f are expected" %(minimum, maximum), "Wrong entry")
                        main_window.update_off()
                        exec("main_window.slow_dds_table.item(row,col).setText(str(main_window.experiment.slow_dds[channel].%s))" %main_window.setting_dict[setting])
                        exec("main_window.slow_dds_table.item(row,col).setToolTip(str(main_window.experiment.slow_dds[channel].%s))" %main_window.setting_dict[setting])
                        main_window.update_on()
                except:
                    #Return the previously assigned value if the expression can not be evaluated                       
                    main_window.update_off()
                    exec("main_window.slow_dds_table.item(row,col).setText(str(main_window.experiment.slow_dds[channel].%s))" %main_window.setting_dict[setting])
                    exec("main_window.slow_dds_table.item(row,col).setToolTip(str(main_window.experiment.slow_dds[channel].%s))" %main_window.setting_dict[setting])
                    main_window.update_on()
                    main_window.error_message('Expression can not be evaluated', 'Wrong entry')            
        elif row == 0: #Channel title was changed
            main_window.experiment.title_slow_dds_tab[(col)//6 + 4] = main_window.slow_dds_table.item(0,col).text()


def handle_variables_table_changed(main_window, item):
    '''
    Function is used when the user changes the values in the variables table. It makes sure that in case the name is changed
    the previous variable was not used in the expression of any parameter in the sequence. In case the previous variable is
    used in any epxression the function will let user know about the first occurence of that variable and revert the name. 
    It also makes sure that if the variable is used the expression when its value is changed the expression evaluation remains in the
    allowed parameters range.       
    '''
    if main_window.to_update:
        row = item.row()
        col = item.column()
        table_item = item
        
        variable = main_window.experiment.new_variables[row]

        if col == 0: #Variable name was changed
            if variable.name == "T_exp_" and getattr(main_window, "_texp_locked", False):
                main_window.update_off()
                table_item.setText(variable.name)
                main_window.update_on()
                return
            if variable.name not in main_window.experiment.sampler_variables: # Check if the variable is being sampled 
                #Checking if the variable is being scanned or ramped 
                variable_scanned = False
                variable_ramped = False 
                for item in main_window.experiment.scanned_variables:
                    if variable.name == item.name:
                        variable_scanned = True
                        break
                for item in main_window.experiment.ramped_variables:
                    if variable.name == item.name:
                        variable_ramped = True
                        break
                if variable_scanned == False and variable_ramped == False: 
                    #Checking if the variable is being used in arguments of derived variables
                    is_derived_argument = False
                    for derived_variable in main_window.experiment.derived_variables:
                        arguments = derived_variable.arguments.replace(" ","").split(",")
                        for argument in arguments:
                            if variable.name == argument:
                                is_derived_argument = True
                                break
                    if not is_derived_argument:
                        # Checking if the variable is being used in a lookup variables as an argument
                        is_lookup_argument = False
                        for lookup_variable in main_window.experiment.lookup_variables:
                            if variable.name == lookup_variable.argument:
                                is_lookup_argument = True
                                break
                        if not is_lookup_argument:
                            new_name = main_window.remove_restricted_characters(table_item.text())
                            #Restricting the user from using the reserved default variable names in the form of id1, id2, etc.
                            if new_name[0:2] == "id" and new_name[2] in "0123456789":
                                main_window.error_message("Variable names starting with id and following with integers are reserved for default edge time variables", "Invalid variable name")
                            elif new_name == "None": #Restricting the user from defining the variable name "None" as it is reserved by the Scan table
                                main_window.error_message("Variable name None is reserved by the scan table. Please choose another name", "Invalid variable name")
                                main_window.update_off()
                                table_item.setText(variable.name)  
                                update.variable_tables(main_window)     
                                main_window.update_on()             
                            elif new_name in main_window.experiment.variables:#Restricting the user from defining the variable name as already defined variable names to avoid having duplicates
                                main_window.error_message('Variable name is already used', 'Invalid variable name')
                                main_window.update_off()
                                table_item.setText(variable.name)  
                                update.variable_tables(main_window)     
                                main_window.update_on()                         
                            else: # The varibable name is almost among allowed, only the integer or float without other caracters should be checked.
                                only_numbers = False
                                try:
                                    float(new_name) #does not allow defining variable names that contains only integers without characters
                                    only_numbers = True
                                except:
                                    pass
                                if only_numbers: #Restricting the user from defining a variable name using only numbers
                                    main_window.update_off()
                                    table_item.setText(variable.name)  
                                    update.variable_tables(main_window)     
                                    main_window.update_on()                         
                                    main_window.error_message('Variable name can not be in a form of a number', 'Invalid variable name')
                                else:
                                    #Allowed variable name. Now checking if it is used in any expression or not. It is done by deleting the variable and trying to evaluate every expression
                                    #variable.value is used as a back up if evaluation is not possible since we do not change main_window.experiment.new_variables to check if the variable is used or not
                                    backup = deepcopy(main_window.experiment.variables[variable.name])
                                    del main_window.experiment.variables[variable.name]
                                    return_value = update.digital_analog_dds_mirny_tabs(main_window) # we need to update value. In other words evaluate evaluations. No need to udpage expressions
                                    if return_value == None: #The previous variable was not used anywhere and can be changed
                                        main_window.experiment.variables[new_name] = backup
                                        main_window.experiment.variables[new_name].name = new_name
                                        main_window.experiment.variables[new_name].is_scanned = False
                                        main_window.experiment.variables[new_name].is_ramped = False
                                        variable.name = new_name
                                        main_window.update_off()
                                        table_item.setText(variable.name)
                                        update.variable_tables(main_window)
                                        main_window.update_on()                            
                                    else: #The previous variable was used somewhere. Reverting the name to the previous 
                                        main_window.error_message('The variable is used in %s.'%return_value, 'Can not delete used variable')
                                        main_window.experiment.variables[backup.name] = backup
                                        main_window.update_off()
                                        table_item.setText(backup.name)
                                        update.variable_tables(main_window)
                                        main_window.update_on()
                        else:
                            main_window.update_off()
                            table_item.setText(variable.name)
                            update.variable_tables(main_window)
                            main_window.update_on()                          
                            main_window.error_message("The variable is used as an argument in lookup variables. Remove it from the Lookup variables table before changing its name.", "Lookup variable's argument")
                    else:
                        main_window.update_off()
                        table_item.setText(variable.name)
                        update.variable_tables(main_window)
                        main_window.update_on()                          
                        main_window.error_message("The variable is used as an argument in derived variables. Remove it from the Derived variables table before changing its name.", "Derived variable's argument")
                else:
                    main_window.update_off()
                    table_item.setText(variable.name)
                    update.variable_tables(main_window)
                    main_window.update_on()                          
                    main_window.error_message("The variable is scanned or ramped. Remove it from the scan or ramp table before deleting.", "Scanned or Ramped variable")
            else:
                main_window.update_off()
                table_item.setText(variable.name)
                update.variable_tables(main_window)
                main_window.update_on()                      
                main_window.error_message("The variable is sampled. Remove it from the sampler tab before changing its name.", "Sampled variable")
        elif col == 1: #variable value was changed
            if variable.name == "T_exp_" and getattr(main_window, "_texp_locked", False):
                main_window.update_off()
                table_item.setText(str(variable.value))
                main_window.update_on()
                return
            #variable.value is used as a back up if evaluation is not possible since we do not change main_window.experiment.new_variables to check if the variable is used or not
            try:
                #Checking if the new value resulting in the values allowed for each parameter it is used in
                main_window.experiment.variables[variable.name].value = float(int(float(table_item.text())*1e6)/1e6)
                # main_window.experiment.variables[variable.name].value = float(table_item.text())

                return_value = update.digital_analog_dds_mirny_tabs(main_window) # we do not need to update expressions only update values.

                if return_value == None: #The value can be updated
                    variable.value = main_window.experiment.variables[variable.name].value
                    # Preserve scan/ramp expressions; only overwrite for_python for plain variables
                    if not (variable.is_scanned or variable.is_ramped or variable.is_sampled or variable.is_derived or variable.is_lookup):
                        variable.for_python = variable.value
                        main_window.experiment.variables[variable.name].for_python = variable.value
                    main_window.update_off()
                    table_item.setText(str(variable.value))
                    main_window.update_on()
                    # update.digital_analog_dds_mirny_tabs(main_window)
                    update.variable_tables(main_window)
                    update.all_values(main_window)
                    if variable.name == "T_exp_":
                        main_window._sync_camera_exposure_from_variable()
                else: #The value can not be updated, reverting every evaluation done before.
                    main_window.error_message("Evaluation is out of allowed range occured in %s. Variable value can not be assigned" %return_value, "Wrong entry")
                    main_window.experiment.variables[variable.name].value = variable.value 
                    main_window.experiment.variables[variable.name].for_python = variable.value
                    main_window.update_off()
                    table_item.setText(str(variable.value))
                    main_window.update_on()
                    update.variable_tables(main_window)
                    update.all_values(main_window)
                    if variable.name == "T_exp_":
                        main_window._sync_camera_exposure_from_variable()
                    

            except: #Restricting the user from using anything but the integer values and floating numbers
                main_window.update_off()
                table_item.setText(str(variable.value))
                main_window.update_on()
                # update.digital_analog_dds_mirny_tabs(main_window, update_expressions_and_evaluations=False)   
                update.variable_tables(main_window)
                  
                update.all_values(main_window)              
                main_window.error_message("Only integers and floating numbers are allowed.", "Wrong entry")
                if variable.name == "T_exp_":
                    main_window._sync_camera_exposure_from_variable()
def handle_lookup_variables_table_changed(main_window, item):
    """Handle changes to the lookup variables table."""
    if main_window.to_update:
        row, col = item.row(), item.column()
        variable = main_window.experiment.lookup_variables[row - 1]  # due to the dummy variable being 1st
        table_item_text = main_window.lookup_variables_table.item(row, col).text().replace(" ", "")
        main_window.update_off()
        main_window.lookup_variables_table.item(row, col).setText(table_item_text)
        main_window.update_on()
        
        if col == 0:  # Variable name was changed
            if table_item_text not in main_window.experiment.variables:
                backup = deepcopy(main_window.experiment.variables[variable.name])
                del main_window.experiment.variables[variable.name]
                return_value = update.digital_analog_dds_mirny_tabs(main_window)
                if return_value == None:  # The previous variable was not used and the name can be changed
                    main_window.experiment.names_of_lookup_variables.remove(variable.name)
                    main_window.experiment.names_of_lookup_variables.add(table_item_text)
                    backup.name = table_item_text
                    variable.name = table_item_text
                    main_window.experiment.variables[backup.name] = backup
                else:  # The previous variable was used and the name can not be changed
                    main_window.error_message("The variable is used in %s" % return_value, "Used variable")
                    main_window.experiment.variables[backup.name] = backup
                    main_window.update_off()
                    main_window.lookup_variables_table.item(row, col).setText(backup.name)
                    main_window.update_on()
            else:
                main_window.error_message("Variable name is already used", "Wrong variable name")
                main_window.update_off()
                main_window.lookup_variables_table.item(row, col).setText(main_window.experiment.lookup_variables[row - 1].name)
                main_window.update_on()
        
        if col == 1:  # Variable argument was changed
            if table_item_text and table_item_text not in main_window.experiment.variables and table_item_text not in main_window.experiment.names_of_derived_variables:
                main_window.error_message(
                    "Argument must reference an existing variable or derived variable.",
                    "Invalid argument",
                )
                main_window.update_off()
                main_window.lookup_variables_table.item(row, col).setText(main_window.experiment.lookup_variables[row - 1].argument)
                main_window.update_on()
            else:
                variable.argument = table_item_text
                main_window.experiment.variables[variable.name].argument = table_item_text


def handle_derived_variables_table_changed(main_window, item):
    """Handle changes to the derived variables table."""
    if main_window.to_update:
        row, col = item.row(), item.column()
        variable = main_window.experiment.derived_variables[row - 1]  # due to the dummy variable being 1st
        table_item_text = main_window.derived_variables_table.item(row, col).text().replace(" ", "")
        main_window.update_off()
        main_window.derived_variables_table.item(row, col).setText(table_item_text)
        main_window.update_on()
        
        if col == 0:  # Variable name was changed
            if table_item_text not in main_window.experiment.variables:
                backup = deepcopy(main_window.experiment.variables[variable.name])
                del main_window.experiment.variables[variable.name]
                return_value = update.digital_analog_dds_mirny_tabs(main_window)
                if return_value == None:  # The previous variable was not used and the name can be changed
                    main_window.experiment.names_of_derived_variables.remove(variable.name)
                    main_window.experiment.names_of_derived_variables.add(table_item_text)
                    backup.name = table_item_text
                    variable.name = table_item_text
                    main_window.experiment.variables[backup.name] = backup
                else:  # The previous variable was used and the name can not be changed
                    main_window.error_message("The variable is used in %s" % return_value, "Used variable")
                    main_window.experiment.variables[backup.name] = backup
                    main_window.update_off()
                    main_window.derived_variables_table.item(row, col).setText(backup.name)
                    main_window.update_on()
            else:
                main_window.error_message("Variable name is already used", "Wrong variable name")
                main_window.update_off()
                main_window.derived_variables_table.item(row, col).setText(main_window.experiment.derived_variables[row - 1].name)
                main_window.update_on()
        if col == 1:  # Variable arguments were changed
            arguments = [arg for arg in table_item_text.split(",") if arg]
            invalid_arguments = []
            for argument in arguments:
                if argument in main_window.experiment.names_of_derived_variables:
                    continue
                if argument not in main_window.experiment.variables:
                    invalid_arguments.append(argument)
            if invalid_arguments:
                invalid_list = ", ".join(invalid_arguments)
                main_window.error_message(
                    f"Arguments must reference existing variables or derived variables. Unknown: {invalid_list}",
                    "Invalid arguments",
                )
                main_window.update_off()
                main_window.derived_variables_table.item(row, col).setText(main_window.experiment.derived_variables[row - 1].arguments)
                main_window.update_on()
            else:
                normalized_arguments = ",".join(arguments)
                variable.arguments = normalized_arguments
                if normalized_arguments != table_item_text:
                    main_window.update_off()
                    main_window.derived_variables_table.item(row, col).setText(normalized_arguments)
                    main_window.update_on()
        if col == 2:  # Variable execution edge was changed
            new_edge_id = table_item_text
            if main_window.find_edge_index_by_id(new_edge_id) == None:
                main_window.error_message("The edge id was not found. Please enter correct id value", "Wrong id entered")
                main_window.update_off()
                main_window.derived_variables_table.item(row, col).setText(variable.edge_id)
                main_window.update_on()
            elif new_edge_id == "id0":
                main_window.error_message("User is restricted from using id0 for requesting derivation of variable. All other edges are allowed.", "Default edge!")
                main_window.update_off()
                main_window.derived_variables_table.item(row, col).setText(variable.edge_id)
                main_window.update_on()
            else:
                if variable.edge_id != "":  # In case it was another id before we need to make that edge.derived_variable_requested to 0 which means that it is not requested
                    edge_index = main_window.find_edge_index_by_id(variable.edge_id)
                    main_window.experiment.sequence[edge_index].derived_variable_requested = -1
                # Assigning the edge.derived_variable_requested value
                variable.edge_id = table_item_text
                edge_index = main_window.find_edge_index_by_id(variable.edge_id)
                main_window.experiment.sequence[edge_index].derived_variable_requested = row - 1  # -1 because the dummy variable is the first one
        if col == 3:  # Variable function was changed
            variable.function = table_item_text
        if col == 4:
            variable.initial_value = table_item_text
            if variable.name in main_window.experiment.variables:
                main_window.update_off()
                if variable.initial_value == "":
                    main_window.experiment.variables[variable.name].value = (variable.initial_value)
                    main_window.update_on()
                else:
                    main_window.experiment.variables[variable.name].value = float(variable.initial_value)
                    main_window.update_on()


def handle_sampler_table_changed(main_window, item):
    """Handle changes to the sampler table."""
    if main_window.to_update:
        row, col = item.row(), item.column()
        table_item = main_window.sampler_table.item(row, col)
        table_entry = main_window.sampler_table.item(row, col).text()
        channel = main_window.experiment.sequence[row].sampler[col - 4]  # channel is a variable name or 0
        
        # Checking if the variable is used in derived variables table as an argument
        not_in_derived_variables = True
        for derived_variable in main_window.experiment.derived_variables:
            arguments = derived_variable.arguments.split(",")
            for argument in arguments:
                if channel == argument:
                    not_in_derived_variables = False
                    break
        if not_in_derived_variables:
            not_in_lookup_variables = True
            # Checking if the variable is used in lookup variables
            for lookup_variable in main_window.experiment.lookup_variables:
                if channel == lookup_variable.argument:
                    not_in_lookup_variables = False
                    break
            if not_in_lookup_variables:
                if table_entry == "" or table_entry == "0" or table_entry == "0.0":  # User deleted the value or set it to 0. The function will assign 0 value
                    if channel in main_window.experiment.sampler_variables:  # if the previous value of the sampler was a variable we need to revert back the variables tab value and activate editing
                        main_window.experiment.sampler_variables.remove(channel)
                        # clear sampled flag on the variable and restore its original stored value if present
                        if channel in main_window.experiment.variables:
                            try:
                                main_window.experiment.variables[channel].is_sampled = False
                                idx = main_window.index_of_a_new_variable(channel)
                                if idx is not None:
                                    # restore value/for_python to the value stored in new_variables
                                    main_window.experiment.variables[channel].value = main_window.experiment.new_variables[idx].value
                                    main_window.experiment.variables[channel].for_python = main_window.experiment.new_variables[idx].for_python
                            except Exception:
                                pass
                        update.variable_tables(main_window)
                        update.variables_tab(main_window, derived_variables=False)
                    main_window.update_off()
                    table_item.setText("0")
                    main_window.update_on()
                else:  # User attempted to assign a variable name to the sampler input
                    if table_entry in main_window.experiment.variables:  # Check if the variable name is defined in the variables tab
                        if main_window.experiment.variables[table_entry].is_scanned == False and main_window.experiment.variables[table_entry].is_ramped == False:  # Check if the variable name is not scanned
                            if table_entry not in main_window.experiment.sampler_variables:
                                # Remove the previous variable from the sampler variables if it was not 0 before the human entry
                                if channel in main_window.experiment.sampler_variables:
                                    main_window.experiment.sampler_variables.remove(channel)
                                main_window.experiment.sequence[row].sampler[col - 4] = table_entry  # Updating the sampler value
                                main_window.experiment.sampler_variables.add(table_entry)  # Adding a new variable to the sampler variables set
                                # mark the variable as sampled and clear its stored value to indicate sampling
                                if table_entry in main_window.experiment.variables:
                                    try:
                                        main_window.experiment.variables[table_entry].is_sampled = True
                                        main_window.experiment.variables[table_entry].value = 0
                                    except Exception:
                                        pass
                                update.variable_tables(main_window)
                                update.variables_tab(main_window, derived_variables=False)
                            else:
                                main_window.update_off()
                                table_item.setText(str(channel))
                                main_window.update_on()
                                main_window.error_message("Variable you entered is already used in sampler. Duplicates are not allowed.", "Reuse of the variable")
                        else:
                            main_window.update_off()
                            table_item.setText(str(channel))
                            main_window.update_on()
                            main_window.error_message("Variable you entered is in the Scan or Ramp table. First remove it from there.", "Scanned / Ramped variable")
                    else:
                        main_window.update_off()
                        table_item.setText(str(channel))
                        main_window.update_on()
                        main_window.error_message("Variable you entered is not found in the variables table. First create the variable there.", "No variable found")
                update.sampler_tab(main_window)
                update.digital_analog_dds_mirny_tabs(main_window)
            else:
                main_window.error_message("Variable is used in a lookup variables table as an argument. First remove it from all lookup variable arguments", "Used sampled variable")
                main_window.update_off()
                table_item.setText(channel)
                main_window.update_on()
        else:
            main_window.error_message("Variable is used in a derived variables table as an argument. First remove it from all derived variable arguments", "Used sampled variable")
            main_window.update_off()
            table_item.setText(channel)
            main_window.update_on()


def handle_chosen_experiment_changed(main_window):
    """Handle changes to the chosen experiment selection."""
    row = main_window.experiment_list_list_widget.currentRow()
    
    if row < 0:
        main_window.experiment_list_btn_delete.setEnabled(False)
        main_window.experiment_list_chosen_line.clear()
        main_window.experiment_list_chosen_line_caption.clear()
        main_window.experiment.experimental_data.experiment_name = ''
        main_window.experiment.experimental_data.comment = ''
        main_window.experiment.experimental_data.path = ''
        main_window.experiment.experimental_data.experiment_id = ''
        return
    
    main_window.experiment_list_btn_delete.setEnabled(len(main_window.experiment_list_list_widget.selectedItems()) > 0)
    
    with open(main_window.repo_path / "experiment_specific_files" / config.which_project / "experiment_names.json", 'r') as f:
        data = json.load(f)
    
    key = f"{int(row)}"
    if key not in data:
        main_window.message_to_logger(f"Experiment entry with key {key} was not found in experiment_names.json")
        return
    
    name = data[key]["name"]
    caption = data[key]["plot_x_caption"]
    
    base_path = getattr(config, "experiment_data_root", "")
    if base_path:
        main_window.experiment.experimental_data.path = str(Path(base_path) / name)
    else:
        main_window.experiment.experimental_data.path = ""
    main_window.experiment_list_chosen_line.setText(name)
    main_window.experiment_list_chosen_line_caption.setText(caption)
    main_window.experiment.experimental_data.experiment_name = name
    main_window.experiment.experimental_data.comment = caption
    main_window.experiment.experimental_data.experiment_id = int(row)
