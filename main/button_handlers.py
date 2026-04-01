'''
Button handlers for Quantrol GUI.

This module contains handlers for input changes, text edits, combo box selections,
and other state change events in the Quantrol control system.

Author  :   Alexei Gurchenko (refactored from source_code.py)
Email   :   alexei.gurchenko@ist.ac.at
Date    :   11.2025
Version :   2.3.3
Contact :   https://hostenlab.pages.ist.ac.at/contact/
'''


import os
import pickle
import threading
import subprocess
import json
from copy import deepcopy
from datetime import datetime
from pathlib import Path

from PyQt5.QtWidgets import QFileDialog, QDialog, QLabel, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit, QInputDialog
from PyQt5.QtGui import QFont
from PyQt5.QtCore import QObject
from scipy.io import loadmat

import write_to_python
import update
import file_io
from data_structures import Variable, ScannedVariable, RampedVariable, DerivedVariable, LookupVariable
import config



# ============================================================================
# SEQUENCE TAB BUTTON HANDLERS
# ============================================================================

def handle_save_sequence_button_clicked(self):
    '''
    Function is used when the user wants to save the sequence. In there is no file corresponsing to the sequence displayed the 
    user needs to specify its location and name. Otherwise it will orverwrite the sequence that was opened
    '''
    # Prepare experiment for saving (capture UI state)
    camera_box = self.camera_box if hasattr(self, "camera_box") else None
    save_sampled_box = self.save_sampled_box if hasattr(self, "save_sampled_box") else None
    texp_locked = self._texp_locked if hasattr(self, "_texp_locked") else None
    file_io.prepare_experiment_for_save(self.experiment, camera_box, save_sampled_box, texp_locked)
    
    if self.experiment.file_name == "":
        self.experiment.file_name = QFileDialog.getSaveFileName(self, 'Save File')[0]
        if self.experiment.file_name != "": #happens when no file name was given (canceled)
            success, message, _ = file_io.save_experiment(self.experiment)
            if success:
                self.create_file_name_label()
            self.message_to_logger(message)
    else:
        success, message, _ = file_io.save_experiment(self.experiment)
        self.message_to_logger(message)


def handle_load_sequence_button_clicked(self):
    '''
    Function is used when the user wants to load the sequence. It triggers the folder explorer and lets the user choose 
    the file to open.
    '''
    sequences_dir = file_io.get_default_directory(self.repo_path)
    loaded_file_name = QFileDialog.getOpenFileName(
        self,
        "Open File",
        str(sequences_dir),
    )[0]
    
    if loaded_file_name == "":
        return
        
    success, message, loaded_experiment = file_io.load_experiment(loaded_file_name)
    
    if not success:
        self.error_message(message, 'Error')
        return
        
    try:
        self.experiment = loaded_experiment
        
        # Ensure backward compatibility
        compat_notes = file_io.ensure_backward_compatibility(self.experiment)
        
        # Update UI button styles based on loaded settings
        if hasattr(self, 'skip_images_button'):
            if not self.experiment.skip_images:
                self.skip_images_button.setStyleSheet(""" QPushButton {background-color: red; color: white}  QToolTip {color: black}""")
        
        if hasattr(self, 'cam_trigger_off_button'):
            if not self.experiment.cam_trigger_off:
                self.cam_trigger_off_button.setStyleSheet(""" QPushButton {background-color: red; color: white}  QToolTip {color: black}""")
        
        if hasattr(self, 'cont_run_after_exp_button'):
            if self.experiment.cont_run_after_exp:
                self.cont_run_after_exp_button.setStyleSheet(""" QPushButton {background-color: green; color: white}  QToolTip {color: black}""")
            else:
                self.cont_run_after_exp_button.setStyleSheet(""" QPushButton {background-color: red; color: white}  QToolTip {color: black}""")

        self._ensure_title_lengths()
        self._ensure_variable_structures()
        
        # Trim/extend per-channel arrays so partially compatible sequences still load
        adjustment_notes = self._reconcile_loaded_sequence_layout()
        self.sequence_num_rows = len(self.experiment.sequence)
        self.update_off()
        
        # Update the state of the checkbox for doing the scan
        self.scan_table.setChecked(self.experiment.do_scan)
        # Update the state of the checkbox for doing the ramp
        self.ramp_table.setChecked(self.experiment.do_ramp) 
        # Update the label showing the sequence that is being modified 
        self.experiment.file_name = loaded_file_name
        self.create_file_name_label()
        update.from_object(self)
        
        # Restore experiment selection
        row_int = file_io.get_experiment_selection_id(self.experiment)
        if row_int is not None and hasattr(self, "experiment_list_list_widget"):
            try:
                if 0 <= row_int < self.experiment_list_list_widget.count():
                    self.experiment_list_list_widget.setCurrentRow(row_int)
                else:
                    self.experiment_list_list_widget.clearSelection()
            except Exception as restore_exc:
                self.message_to_logger(f"Could not restore experiment selection: {restore_exc}")
        
        self.message_to_logger(f"Sequence loaded from {self.experiment.file_name}")
        if adjustment_notes:
            self.message_to_logger(
                "Adjusted loaded sequence to match available hardware: " + "; ".join(adjustment_notes)
            )
        if compat_notes:
            self.message_to_logger("Compatibility updates: " + "; ".join(compat_notes))
        
        # Restore camera box state and parameters after successful load
        try:
            if hasattr(self, "camera_box"):
                self.camera_box.setChecked(self.experiment.camera_enabled)
                # Restore camera parameters
                if hasattr(self.experiment.experimental_data, 'camera'):
                    cam = self.experiment.experimental_data.camera
                    if hasattr(cam, 'camera_name') and cam.camera_name:
                        index = self.which_cam_combo.findText(cam.camera_name)
                        if index >= 0:
                            self.which_cam_combo.setCurrentIndex(index)
                    if hasattr(cam, 'gain_db') and cam.gain_db is not None:
                        self.gain_edit.setText(str(cam.gain_db))
                    if hasattr(cam, 'exposure_time_ms') and cam.exposure_time_ms is not None:
                        self.exposure_edit.setText(str(cam.exposure_time_ms))
                    if hasattr(cam, 'format_name') and cam.format_name:
                        index = self.format_combo.findText(cam.format_name)
                        if index >= 0:
                            self.format_combo.setCurrentIndex(index)
            # Restore save-sampled checkbox state if present
            if hasattr(self, "save_sampled_box"):
                try:
                    self.save_sampled_box.setChecked(getattr(self.experiment, 'save_sampled_variables', False))
                except Exception:
                    self.save_sampled_box.setChecked(False)
            # Restore T_exp_ lock state
            if hasattr(self, "lock_cb"):
                self.lock_cb.setChecked(self.experiment.texp_locked)
                self._texp_locked = self.experiment.texp_locked
                self._update_texp_lock_presentation()
        except Exception as e:
            self.message_to_logger(f"Could not restore camera settings: {e}")
            
    except Exception as e:
        self.error_message(f'Error processing loaded file: {e}', 'Error')
    finally:
        self.update_on()


def handle_save_sequence_as_button_clicked(self):
    '''
    Function is used when the user wants to save the sequence as a separate file. It will not reassign the current file name
    but just create an additional copy of the current state of the self.experiment
    '''
    # Save camera state before pickling
    if hasattr(self, "camera_box"):
        self.experiment.camera_enabled = self.camera_box.isChecked()
    if hasattr(self, "save_sampled_box"):
        self.experiment.save_sampled_variables = self.save_sampled_box.isChecked()
    if hasattr(self, "_texp_locked"):
        self.experiment.texp_locked = self._texp_locked
    
    self.experiment.file_name = QFileDialog.getSaveFileName(self, 'Save File')[0] # always ask for filename
    if self.experiment.file_name != "": #self.experiment.file_name = ""happens when no file name was given (canceled)
        try:
            with open(self.experiment.file_name, 'wb') as file:
                pickle.dump(self.experiment, file)
            self.create_file_name_label()
            self.message_to_logger("Sequence saved at %s" %self.experiment.file_name)
        except:
            self.message_to_logger("Saving attempt was not successful")
    else:
        self.message_to_logger("No file name was given. Saving unsuccessful")


def handle_insert_edge_button_clicked(self):   
    '''
    Function is used to insert a new edge. Its values are assigned to be the same as the values of the previous edge but empty name.
    Updating of tables is done by setting all channels is_changed to False and updating from object
    '''
    #appending a new edge with a unique id
    new_unique_id = self.find_unique_id_unused()
    new_edge = deepcopy(self.experiment.sequence[-1]) #copying the last edge
    new_edge.id = new_unique_id
    new_edge.name = ""
    self.experiment.sequence.append(new_edge)
    self.sequence_num_rows += 1
    #creating a corresponding variable so one can use id# as a variable
    self.experiment.variables[new_edge.id] = Variable(name = new_edge.id, value = new_edge.value, for_python = new_edge.for_python)
    self.update_off()
    #Setting DIGITAL table values to not changed
    for channel in self.experiment.sequence[-1].digital:
        channel.changed = False
    #Setting ANALOG table values to not changed
    for channel in self.experiment.sequence[-1].analog:
        channel.changed = False
    #Setting DDS table values to not changed
    for channel in self.experiment.sequence[-1].dds:
        channel.changed = False
    #Setting MIRNY table values to not changed
    for channel in self.experiment.sequence[-1].mirny:
        channel.changed = False
    #Setting SAMPLER table values to 0
    self.experiment.sequence[-1].sampler = ["0"]*8

    update.from_object(self)
    self.update_on()


def handle_delete_edge_button_clicked(self):
    '''
    Function is used when the user wants to delete selected edge. The user is not allowed to delete the default edge.
    The function is creating a backup version of the variable with corresponding id number and tries to update all tabs without that 
    variable. That way it is checking if the edge value has been used anywhere? In case of no problems it does execute the deletion
    and updates the table in each tab. Otherwise, the fucntion will reassign the variable and let the user know that the time edge is 
    being used at particular place.
    '''
    try:
        row = self.sequence_table.selectedIndexes()[0].row()
        name = self.experiment.sequence[row].id
        if row == 0: # corresponds to the default edge
            self.error_message("You can not delete the starting edge", "Protected item")
        else:
            backup = deepcopy(self.experiment.variables[name]) #backup is a variable copy in case we would need to restore changes and not allow deleting edge
            #the following is a check whether the edge has been used somewhere. First we delete a corresponding variable and then try to evaluate all the entries
            del self.experiment.variables[name]
            return_value = update.digital_analog_dds_mirny_tabs(self)
            if return_value == None: #no errors, means that the edge can be deleted
                del self.experiment.sequence[row]
                # Recompute sampler variables set after edge deletion to avoid stale sampled flags
                new_sampler_set = set()
                for edge in self.experiment.sequence:
                    try:
                        for entry in edge.sampler:
                            if entry and entry != '0':
                                new_sampler_set.add(entry)
                    except Exception:
                        pass
                # Reset all variable sampled flags
                try:
                    for var in list(self.experiment.variables.keys()):
                        try:
                            self.experiment.variables[var].is_sampled = False
                        except Exception:
                            pass
                except Exception:
                    pass
                # Mark variables that remain sampled and set their runtime value to 0
                for name in new_sampler_set:
                    if name in self.experiment.variables:
                        try:
                            self.experiment.variables[name].is_sampled = True
                            self.experiment.variables[name].value = 0
                        except Exception:
                            pass
                self.experiment.sampler_variables = new_sampler_set
                self.sequence_table.setCurrentCell(row-1, 0)
                update.from_object(self) #updating all tables
            else:
                self.experiment.variables[name] = backup
                self.error_message('The edge time value is used as a variable in %s.'%return_value, 'Can not delete used edge')
    except:
        self.error_message("Select the edge you want to delete", "No edge selected")


def handle_go_to_edge_button_clicked(self):
    '''
    Function is used to set the hardware into a specific time edge state. User needs to click the edge before pressing the button.
    After a successful execution the edge will be highlighted in green. The function recognizes the tab that is being currently displayed
    and assigns the hardware to the state of the last selected edge in that particular tab.
    '''
    try:
        # Determine current tab widget and map it to the corresponding table + row offset
        cur_widget = self.main_window.currentWidget()
        table = None
        row_offset = 0

        if cur_widget is getattr(self, 'digital_tab_widget', None):
            table = getattr(self, 'digital_dummy', None)
            row_offset = 0
        elif cur_widget is getattr(self, 'analog_tab_widget', None):
            table = getattr(self, 'analog_dummy', None)
            row_offset = 0
        elif cur_widget is getattr(self, 'dds_tab_widget', None):
            table = getattr(self, 'dds_seq', None)
            row_offset = 0
        elif cur_widget is getattr(self, 'mirny_tab_widget', None):
            table = getattr(self, 'mirny_dummy', None)
            row_offset = 0
        elif cur_widget is getattr(self, 'sampler_tab_widget', None):
            table = getattr(self, 'sampler_table', None)
            row_offset = 0
        else:
            # default to sequence table when no special tab matched
            table = getattr(self, 'sequence_table', None)
            row_offset = 0

        edge_num = None
        # Try to read selection from the active table
        if table is not None:
            sel = table.selectedIndexes()
            if sel:
                candidate = sel[0].row() - row_offset
            else:
                # Some interactions (e.g. right-click) may not change cell selection
                # but `currentRow()` may reflect the user's intended row. Use it.
                try:
                    cur = table.currentRow()
                    candidate = cur - row_offset if cur is not None else None
                except Exception:
                    candidate = None

            # validate candidate against sequence length
            seq = getattr(self, 'experiment', None)
            seq_len = len(getattr(seq, 'sequence', [])) if seq is not None else 0
            if candidate is not None and 0 <= candidate < seq_len:
                edge_num = candidate

        # Fall back to last selected edge across tabs when current tab has no valid selection
        if edge_num is None:
            edge_num = getattr(self, 'last_selected_edge_num', None)

        # Final validation against sequence length
        seq = getattr(self, 'experiment', None)
        seq_len = len(getattr(seq, 'sequence', [])) if seq is not None else 0
        if edge_num is None or not (0 <= edge_num < seq_len):
            raise ValueError('No edge selected')

        # If we fell back to last selection, update the visible table selection so UI matches
        try:
            if table is not None:
                target_row = edge_num + row_offset
                if 0 <= target_row < table.rowCount():
                    prev = getattr(self, '_suppress_selection_handler', False)
                    self._suppress_selection_handler = True
                    try:
                        table.selectRow(target_row)
                    finally:
                        self._suppress_selection_handler = prev
        except Exception:
            # non-fatal: selection sync is best-effort
            pass

        write_to_python.create_go_to_edge(self, edge_num=edge_num)
        self.message_to_logger("Go to edge file generated")
        try:
            if config.package_manager == "conda":
                submit_experiment_thread = threading.Thread(target=os.system, args=["conda activate "+ config.artiq_environment_name +" && artiq_run " + str(self.repo_path / "ARTIQ_scripts" / 'go_to_edge.py')])
            elif config.package_manager == "clang64":
                #coprint("Current directory:", os.getcwd()) #env_test
                submit_experiment_thread = threading.Thread(target=os.system, args=[str(self.repo_path / "experiment_specific_files" / "hybrid_experiment" / 'go_to_edge.bat')])
            submit_experiment_thread.start()
            self.message_to_logger("Went to edge")
            print("test: went to edge_num :", edge_num)
            #unhighlighting the previously highlighted edge if it was previously highlighted
            if self.experiment.go_to_edge_num != -1:
                self.set_color_of_the_edge(self.white, self.experiment.go_to_edge_num)
            try:
                if self.experiment.do_ramp == True:
                    self.update_sequence_edge_colors()
            except:
                pass
            #highlighting newly selected edge to go
            self.set_color_of_the_edge(self.green, edge_num)
            self.experiment.go_to_edge_num = edge_num
        except:
            self.message_to_logger("Couldn't go to edge")    
    except:
        self.error_message("Chose the edge you want the system to go","No edge selected")


# ============================================================================
# EXPERIMENT CONTROL BUTTON HANDLERS
# ============================================================================

def handle_run_experiment_button_clicked(self): 
    '''
    Function is used when the user wants to run the experiment. By calling update.digital_analog_dds_mirny_tabs(self) it updates every expression
    to make sure that all scanning variables are taken into account. After that it generates the run_experiment.py file and 
    submits the experimental description to the scheduler through artiq_run function.
    '''
    if not self._ensure_camera_experiment_selected():
        self.message_to_logger("Experiment start aborted: no experiment chosen while camera enabled")
        return
    self.count_scanned_variables()
    self.count_ramped_variables()
    update.digital_analog_dds_mirny_tabs(self) #updating all expressions in particular for_pythons of each parameter
    try:
        write_to_python.create_experiment(self)
        if self.experiment.do_ramp == True and self.startID_edge_next_to_endID_edge() == False:
            self.message_to_logger("Ramp: End ID edge is not right after Start ID edge!")
            raise ValueError("startID is not next to endID")
        self.message_to_logger("Python file generated")

        camera_launch_info = None
        delay_before_artiq = 0.0
        if hasattr(self, "camera_box") and self.camera_box.isChecked():
            try:
                camera_launch_info = self._prepare_camera_launch()
                delay_before_artiq = float(getattr(config, "camera_launch_delay_s", 5))
            except ValueError as exc:
                self.error_message(str(exc), "Camera acquisition")
                self.message_to_logger(f"Camera acquisition aborted: {exc}")
                return

        try:
            if camera_launch_info and camera_launch_info.get("metadata_dir"):
                metadata_dir = Path(camera_launch_info["metadata_dir"])
            else:
                metadata_dir = self.repo_path / 'logs'
            metadata_dir.mkdir(parents=True, exist_ok=True)
            if not getattr(self.experiment.experimental_data, "current_run_timestamp", ""):
                self.experiment.experimental_data.current_run_timestamp = datetime.now().isoformat()
            self.experiment.experimental_data.current_run_metadata_path = str(metadata_dir)
            # with open(metadata_dir / 'metadata.json', "w") as outfile:
            #     json.dump(self.to_dict(self.experiment),outfile,indent=4)
            timestamp = self.experiment.experimental_data.current_run_timestamp.replace('-', '').replace(':', '').replace('T', '_').split('.')[0]
            metadata_filename = f'metadata{timestamp}.json'
            with open(metadata_dir / metadata_filename, "w") as outfile:
                json.dump(self.to_dict(self.experiment),outfile,indent=4)

            self._record_experiment_run(metadata_dir, is_multiple_run=False)
            if camera_launch_info:
                self._start_camera_subprocess(camera_launch_info)
                self.message_to_logger("Camera acquisition started")

            submit_experiment_thread = self._start_artiq_thread(delay_s=delay_before_artiq)
            #unhighlighting the previously highlighted edge
            if self.experiment.go_to_edge_num != -1:
                self.set_color_of_the_edge(self.white, self.experiment.go_to_edge_num)
                self.experiment.go_to_edge_num = -1
            try:
                if self.experiment.do_ramp == True:
                    self.update_sequence_edge_colors()
            except:
                pass
            #needs to be done ---> logging the start of the experiment only if it was started without errors. Checking experiment stages
            self.message_to_logger("Experiment started")
        except Exception as exc:
            self.message_to_logger(f"Was not able to start experiment: {exc}")
    except Exception:
        self.message_to_logger("Was not able to generate python file")


def handle_init_hardware_button_clicked(self):
    '''
    Function is used to initialize the hardware at the default values. It generates the init_hardware.py file according to the
    default edge state and then sets the hardware in that state by running something similar to go_to_edge.py
    '''
    try:
        write_to_python.create_go_to_edge(self, edge_num=0, to_default=True)
        self.message_to_logger("init_hardware.py file generated")
        try:
            #initialize environment and submit the experiment to the scheduler
            if config.package_manager == "conda":
                submit_experiment_thread = threading.Thread(target=os.system, args=["conda activate "+ config.artiq_environment_name +" && artiq_run " + str(self.repo_path / "ARTIQ_scripts" / 'init_hardware.py')])
            elif config.package_manager == "clang64":
                # submit_experiment_thread = threading.Thread(target=os.system, args=["init_hardware.bat"])
                submit_experiment_thread = threading.Thread(target=lambda: subprocess.Popen(['cmd', '/c', str(self.repo_path / "experiment_specific_files" / "hybrid_experiment" / 'init_hardware.bat')],creationflags=subprocess.CREATE_NEW_CONSOLE))
            submit_experiment_thread.start()
            #unhighlighting the previously highlighted edge
            if self.experiment.go_to_edge_num != -1:
                self.set_color_of_the_edge(self.white, self.experiment.go_to_edge_num)
            #Highlighting the default edge and setting the go_to_edge_num to the default edge value (0)
            self.experiment.go_to_edge_num = 0
            self.set_color_of_the_edge(self.green, 0)
            self.message_to_logger("Hardware initialized at the default edge.")
        except:
            self.message_to_logger("Was not able to initialize the hardware.")        
    except:
        self.message_to_logger("Was not able to generate init_hardware.py file")


def handle_generate_run_experiment_py_button_clicked(self):
    '''
    Function is used to generate the run_experiment.py according to the experimental descirption without
    running it. It is usefull for debugging purposes.
    '''
    self.count_scanned_variables()
    self.count_ramped_variables()
    update.digital_analog_dds_mirny_tabs(self) #specifically used to update for_python version of each parameter in the sequence
    try:
        write_to_python.create_experiment(self)
        if self.experiment.do_ramp == True and self.startID_edge_next_to_endID_edge() == False:
            self.message_to_logger("Ramp: End ID edge is not right after Start ID edge!")
            raise ValueError("startID is not next to endID")
        self.message_to_logger("Python file generated")
    except:
        self.message_to_logger("Was not able to generate python file")


def handle_submit_run_experiment_py_button_clicked(self):
    '''
    Function is used to submit already existing run_experiment.py without updating it with the current state
    of the experimental description. Useful in case one needs to hard code some changes into the previously
    generated run_experiment.py file. For instance, making a 2D scan:
    
    self.a = np.linspace(a_min, a_max, number_of_steps_a)
    self.b = np.linspace(b_min, b_max, number_of_steps_b)
    
    for index_a in range(number_of_steps_a):
        for index_b in range(number_of_steps_b):
            self.ttl0(self.a[index_a])
            self.ttl1(self.b[index_b])
    '''
    if not self._ensure_camera_experiment_selected():
        self.message_to_logger("Experiment start aborted: no experiment chosen while camera enabled")
        return
    self.count_scanned_variables()
    self.count_ramped_variables()
    update.digital_analog_dds_mirny_tabs(self) #updating all expressions in particular for_pythons of each parameter
    
    camera_launch_info = None
    delay_before_artiq = 0.0
    if hasattr(self, "camera_box") and self.camera_box.isChecked():
        try:
            camera_launch_info = self._prepare_camera_launch()
            delay_before_artiq = float(getattr(config, "camera_launch_delay_s", 5))
        except ValueError as exc:
            self.error_message(str(exc), "Camera acquisition")
            self.message_to_logger(f"Camera acquisition aborted: {exc}")
            return

    try:
        if camera_launch_info and camera_launch_info.get("metadata_dir"):
            metadata_dir = Path(camera_launch_info["metadata_dir"])
        else:
            metadata_dir = self.repo_path / 'logs'
        metadata_dir.mkdir(parents=True, exist_ok=True)
        if not getattr(self.experiment.experimental_data, "current_run_timestamp", ""):
            self.experiment.experimental_data.current_run_timestamp = datetime.now().isoformat()
        self.experiment.experimental_data.current_run_metadata_path = str(metadata_dir)
        # with open(metadata_dir / 'metadata.json', "w") as outfile:
        #     json.dump(self.to_dict(self.experiment),outfile,indent=4)
        timestamp = self.experiment.experimental_data.current_run_timestamp.replace('-', '').replace(':', '').replace('T', '_').split('.')[0]
        metadata_filename = f'metadata{timestamp}.json'
        with open(metadata_dir / metadata_filename, "w") as outfile:
            json.dump(self.to_dict(self.experiment),outfile,indent=4)
        self._record_experiment_run(metadata_dir, is_multiple_run=False)
        if camera_launch_info:
            self._start_camera_subprocess(camera_launch_info)
            self.message_to_logger("Camera acquisition started")

        submit_experiment_thread = self._start_artiq_thread(delay_s=delay_before_artiq)
        #unhighlighting the previously highlighted edge
        if self.experiment.go_to_edge_num != -1:
            self.set_color_of_the_edge(self.white, self.experiment.go_to_edge_num)
            self.experiment.go_to_edge_num = -1
        try:
            if self.experiment.do_ramp == True:
                self.update_sequence_edge_colors()
        except:
            pass
        #needs to be done ---> logging the start of the experiment only if it was started without errors. Checking experiment stages
        self.message_to_logger("Experiment started")
    except Exception as exc:
        self.message_to_logger(f"Was not able to start experiment: {exc}")



def handle_continuous_run_button_clicked(self):
    '''
    Function is used when the user wants to run the specified experimental sequence continuously.
    It passes the run_continuous flag into the write_to_python.create_experiment and the rest is handled there
    '''
    if not self._ensure_camera_experiment_selected():
        self.message_to_logger("Experiment start aborted: no experiment chosen while camera enabled")
        return
    self.count_scanned_variables()
    self.count_ramped_variables()
    update.digital_analog_dds_mirny_tabs(self) #updating all expressions in particular for_pythons of each parameter
    try:
        write_to_python.create_experiment(self, run_continuous=True)
        if self.experiment.do_ramp == True and self.startID_edge_next_to_endID_edge() == False:
            self.message_to_logger("Ramp: End ID edge is not right after Start ID edge!")
            raise ValueError("startID is not next to endID")
        self.message_to_logger("Python file generated")
        try:
            #initialize environment and submit the experiment to run continuously unless it is stopped
            if config.package_manager == "conda":
                submit_run_continuously_thread = threading.Thread(target=os.system, args=["conda activate "+ config.artiq_environment_name +" && artiq_run " + str(self.repo_path / "ARTIQ_scripts" / 'run_experiment.py')])
            elif config.package_manager == "clang64":
                # submit_run_continuously_thread = threading.Thread(target=os.system, args=["run_experiment.bat"])
                submit_run_continuously_thread = threading.Thread(target=lambda: subprocess.Popen(['cmd', '/c', str(self.repo_path / "experiment_specific_files" / "hybrid_experiment" / 'cont_run.bat')],creationflags=subprocess.CREATE_NEW_CONSOLE))
            submit_run_continuously_thread.start()
            #unhighlighting the previously highlighted edge
            if self.experiment.go_to_edge_num != -1:
                self.set_color_of_the_edge(self.white, self.experiment.go_to_edge_num)
                self.experiment.go_to_egde_num = 0
            try:
                if self.experiment.do_ramp == True:
                    self.update_sequence_edge_colors()
            except:
                pass
            #needs to be done ---> logging the start of the experiment only if it was started without errors. Checking experiment stages
            self.message_to_logger("Experiment started")
        except:
            self.message_to_logger("Was not able to start experiment")
    except:
        self.message_to_logger("Was not able to generate python file")


def handle_multiple_runs_button_clicked(self):
    '''
    analog to continuous_run_button_clicked and run_experiment_button_clicked
    '''
    if not self._ensure_camera_experiment_selected():
        self.message_to_logger("Experiment start aborted: no experiment chosen while camera enabled")
        return
    self.count_scanned_variables()
    self.count_ramped_variables()
    update.digital_analog_dds_mirny_tabs(self) #updating all expressions in particular for_pythons of each parameter
    try:
        write_to_python.create_experiment(self, multiple_runs=True)
        if self.experiment.do_ramp == True and self.startID_edge_next_to_endID_edge() == False:
            self.message_to_logger("Ramp: End ID edge is not right after Start ID edge!")
            raise ValueError("startID is not next to endID")
        self.message_to_logger("Python file generated")

        camera_launch_info = None
        delay_before_artiq = 0.0
        if hasattr(self, "camera_box") and self.camera_box.isChecked():
            try:
                camera_launch_info = self._prepare_camera_launch()
                delay_before_artiq = float(getattr(config, "camera_launch_delay_s", 5))
            except ValueError as exc:
                self.error_message(str(exc), "Camera acquisition")
                self.message_to_logger(f"Camera acquisition aborted: {exc}")
                return

        try:
            if camera_launch_info and camera_launch_info.get("metadata_dir"):
                metadata_dir = Path(camera_launch_info["metadata_dir"])
            else:
                metadata_dir = self.repo_path / 'logs'
            metadata_dir.mkdir(parents=True, exist_ok=True)
            if not getattr(self.experiment.experimental_data, "current_run_timestamp", ""):
                self.experiment.experimental_data.current_run_timestamp = datetime.now().isoformat()
            self.experiment.experimental_data.current_run_metadata_path = str(metadata_dir)
            # with open(metadata_dir / 'metadata.json', "w") as outfile:
            #     json.dump(self.to_dict(self.experiment),outfile,indent=4)
            timestamp = self.experiment.experimental_data.current_run_timestamp.replace('-', '').replace(':', '').replace('T', '_').split('.')[0]
            metadata_filename = f'metadata{timestamp}.json'
            with open(metadata_dir / metadata_filename, "w") as outfile:
                json.dump(self.to_dict(self.experiment),outfile,indent=4)

            self._record_experiment_run(metadata_dir, is_multiple_run=True)
            if camera_launch_info:
                self._start_camera_subprocess(camera_launch_info)
                self.message_to_logger("Camera acquisition started")

            submit_experiment_thread = self._start_artiq_thread(delay_s=delay_before_artiq)
            #unhighlighting the previously highlighted edge
            if self.experiment.go_to_edge_num != -1:
                self.set_color_of_the_edge(self.white, self.experiment.go_to_edge_num)
                self.experiment.go_to_edge_num = -1
            try:
                if self.experiment.do_ramp == True:
                    self.update_sequence_edge_colors()
            except:
                pass
            #needs to be done ---> logging the start of the experiment only if it was started without errors. Checking experiment stages
            self.message_to_logger("Experiment started")
        except Exception as exc:
            self.message_to_logger(f"Was not able to start experiment: {exc}")
    except Exception:
        self.message_to_logger("Was not able to generate python file")


def handle_stop_continuous_run_button_clicked(self):
    '''
    Function is used when the user wants to stop continuous run. It will stop anything and run the init_hardware.py file
    '''
    self.dialog = QDialog()
    self.dialog.setGeometry(*self.scale_geom(710, 435, 400, 120))
    self.dialog.setFont(QFont('Arial', self.scale_font(14)))
    value_input = QLabel("Are you sure that you want to stop the experiment?")
    dialog_layout = QVBoxLayout()
    button_yes = QPushButton("Yes")
    button_no = QPushButton("No")
    dialog_layout.addWidget(value_input)
    dialog_buttons_layout = QHBoxLayout()
    dialog_buttons_layout.addWidget(button_yes)
    dialog_buttons_layout.addWidget(button_no)
    dialog_layout.addLayout(dialog_buttons_layout)
    self.dialog.setLayout(dialog_layout)
    button_yes.clicked.connect(lambda:self.stop_continuous_run())
    button_no.clicked.connect(lambda:self.dialog.reject())
    self.dialog.setWindowTitle("Warning!") 
    self.dialog.exec_()


# ============================================================================
# DEFAULT SETTINGS BUTTON HANDLERS
# ============================================================================

def handle_save_default_button_clicked(self):
    '''
    Function is used when the user wants to save the current state of the default edge. It first asks if the user is sure that
    it is needed to overwrite the default settings.
    '''
    #The pop-up window to preven use from accidentally overwriting the default settings
    self.dialog = QDialog()
    self.dialog.setGeometry(*self.scale_geom(710, 435, 400, 120))
    self.dialog.setFont(QFont('Arial', self.scale_font(14)))
    value_input = QLabel("Are you sure that you want to overwrite the default settings? Previous default settings will be lost!")
    dialog_layout = QVBoxLayout()
    button_update = QPushButton("Yes")
    button_cancel = QPushButton("No")
    dialog_layout.addWidget(value_input)
    dialog_buttons_layout = QHBoxLayout()
    dialog_buttons_layout.addWidget(button_update)
    dialog_buttons_layout.addWidget(button_cancel)
    dialog_layout.addLayout(dialog_buttons_layout)
    self.dialog.setLayout(dialog_layout)
    button_update.clicked.connect(lambda:self.saving_default())
    button_cancel.clicked.connect(lambda:self.dialog.reject())
    self.dialog.setWindowTitle("Warning!") 
    self.dialog.exec_()


def handle_load_default_button_clicked(self):
    '''
    Function is used when the user wants to load the default settings. This can be used when loading the old versions of experiemnts
    to overwrite the titles and default states to the updated default values.
    '''
    self.update_off()
    
    success, message, default_experiment = file_io.load_default_settings(self.repo_path)
    
    if not success:
        self.error_message(message, 'Error')
        self.update_on()
        return
    
    # Apply default settings to current experiment
    file_io.apply_default_to_experiment(self.experiment, default_experiment)
    update.from_object(self)
    self.message_to_logger(f"Default values loaded from {self.experiment.file_name}")
    self.update_on()


# ============================================================================
# SLOW DDS BUTTON HANDLERS
# ============================================================================

def handle_set_slow_dds_states_button_clicked(self):
    '''
    Function is used when the user requests to set the displayed values. It will generate the experimental description
    and artiq_run it to set only the states of the slow dds channels
    '''
    try:
        write_to_python.set_slow_dds_states(self)
        self.message_to_logger("set_slow_dds_states.py file generated")
        try:
            #initialize environment and submit the experiment to the scheduler
            if config.package_manager == "conda":
                submit_experiment_thread = threading.Thread(target=os.system, args=["conda activate "+ config.artiq_environment_name +" && artiq_run " + str(self.repo_path / "ARTIQ_scripts" / 'set_slow_dds_states.py')])
            elif config.package_manager == "clang64":
                print(str(self.repo_path / "experiment_specific_files" / "hybrid_experiment" / 'set_slow_dds_states.bat'))
                submit_experiment_thread = threading.Thread(target=os.system, args=[str(self.repo_path / "experiment_specific_files" / "hybrid_experiment" / 'set_slow_dds_states.bat')])
            submit_experiment_thread.start()
            self.message_to_logger("Slow DDS states are set")
        except:
            self.message_to_logger("Was not able to set slow DDS states")
    except:
        self.message_to_logger("Was not able to generate python file")


# ============================================================================
# VARIABLE MANAGEMENT BUTTON HANDLERS
# ============================================================================

def handle_delete_variable_button_clicked(self):
    '''
    Function is used when the user wants to delete the variable from the variables table.
    It checks if the variable is used in any expression by deleting it and trying to evaluate every expression.
    the backup is used in order to be able to revert the changes in case the variable is used somewhere.
    '''
    tab_sender = self.sender().parent()

    for child in tab_sender.findChildren(QObject):
        if hasattr(child, "is_var_table"):
            var_table = child

    selected = False
    try:
        row = var_table.selectedIndexes()[0].row()
        selected = True
    except:
        pass
    

    if selected:
        name = var_table.item(row,0).text()
        variable = self.experiment.new_variables[row]
        if name not in self.experiment.sampler_variables: # Check if the variable is being sampled 
            #Checking if the variable is being scanned or ramped
            variable_scanned = False
            variable_ramped = False 
            for variable in self.experiment.scanned_variables:
                if name == variable.name:
                    variable_scanned = True
                    break
            for variable in self.experiment.ramped_variables:
                if name == variable.name:
                    variable_ramped = True
                    break
            if variable_scanned == False and variable_ramped == False: 
                #Checking if the variable is being used in arguments of derived variables
                is_derived_argument = False
                for derived_variable in self.experiment.derived_variables:
                    arguments = derived_variable.arguments.replace(" ","").split(",")
                    for argument in arguments:
                        if variable.name == argument:
                            is_derived_argument = True
                            break
                if not is_derived_argument:
                    # Checking if the variable is being used in a lookup variables as an argument
                    is_lookup_argument = False
                    for lookup_variable in self.experiment.lookup_variables:
                        if name == lookup_variable.argument:
                            is_lookup_argument = True
                            break
                    if not is_lookup_argument:
                        backup = deepcopy(self.experiment.variables[name]) #used to be able to revert the process of deletion
                        del self.experiment.variables[name]
                        var_table.setCurrentCell(row-1,0)
                        return_value = update.digital_analog_dds_mirny_tabs(self) #we need to update only values not expressions
                        if return_value == None: #Variable can be deleted
                            del self.experiment.new_variables[row]
                            update.variable_tables(self)
                            update.all_values(self)
                        else: #Variable can not be deleted. Reverting all changes back to previous state
                            self.experiment.variables[name] = backup
                            update.variable_tables(self)
                            update.all_values(self)
                            self.error_message('The variable is used in %s.'%return_value, 'Can not delete used variable')
                    else:
                        self.error_message("The variable is used as a argument in lookup variables. Remove it from the Lookup variables table before deleting it.", "Lookup variable's argument")
                else:
                    self.error_message("The variable is used as a argument in derived variables. Remove it from the Derived variables table before deleting it.", "Derived variable's argument")
            else:
                self.error_message("The variable is scanned or ramped. Remove it from the scan or ramp table before deleting.", "Scanned or Ramped variable") 
        else:
            self.error_message("The variable is sampled. Remove it from the sampler tab before deleting.", "Sampled variable")
    else: #In case the user pressed delete variable button without selecting the variable that needs to be deleted
        self.error_message("Select the variable that needs to be deleted", "No variable selected")


def handle_create_derived_variable_button_clicked(self):
    '''
    Function is used when the user wants to create a new derived variable. It finds the lowest unused available variable name and 
    creates it. It also create the corresponding derived Variable objects  in the list derived variables.
    '''
    variable_name = self.find_derived_variable_name_unused()
    self.experiment.names_of_derived_variables.add(variable_name)
    self.experiment.derived_variables.append(DerivedVariable(name = variable_name, edge_id = "", arguments = "", function = "", initial_value = ""))
    self.experiment.variables[variable_name] = Variable(name = variable_name, value = 0.0, for_python = 0.0, is_derived = True)
    update.variables_tab(self, new_variables = False, lookup_variables = False)


def handle_create_lookup_variable_button_clicked(self):
    '''
    Function is used when the user wants to create a new lookup variable. It finds the lowest unused available variable name and 
    creates it. It also create the corresponding Variable objects  in new_variables and variables.
    '''
    variable_name = self.find_lookup_variable_name_unused()
    self.experiment.names_of_lookup_variables.add(variable_name)
    self.experiment.lookup_variables.append(LookupVariable(name = variable_name))
    self.experiment.variables[variable_name] = Variable(name = variable_name, value = 0.0, for_python = 0.0, is_lookup = True)
    update.variables_tab(self, new_variables = False, derived_variables = False)


def handle_delete_derived_variable_button_clicked(self):
    '''
    Function is used when the user wants to delete the derived variable from the table.
    '''
    try:
        row = self.derived_variables_table.selectedIndexes()[0].row()
        if row == 0:
            self.error_message("You can not delete a dummy example", "Protected variable")
        else:
            name = self.derived_variables_table.item(row,0).text()
            backup = deepcopy(self.experiment.variables[name])

            for i, dv in enumerate(self.experiment.derived_variables):
                edge_index = self.find_edge_index_by_id(dv.edge_id)
                if edge_index is not None:
                    edge = self.experiment.sequence[edge_index]
                    drv_idx = edge.derived_variable_requested

            for i, edge in enumerate(self.experiment.sequence):
                edge_id = getattr(edge, 'id', f"index_{i}")  # fallback if edge has no `id` field
                drv_idx = edge.derived_variable_requested
                if isinstance(drv_idx, int) and drv_idx >= 0 and drv_idx < len(self.experiment.derived_variables):
                    variable_name = self.experiment.derived_variables[drv_idx].name
                elif drv_idx == -1:
                    variable_name = "(none)"
                else:
                    variable_name = "(invalid index)"



            del self.experiment.variables[name]
            return_value = update.digital_analog_dds_mirny_tabs(self)
            if return_value == None: #Derived variable is not used anywhere and can be deleted
                #Undoing the edge id requested to derive the variable
                edge_index = self.find_edge_index_by_id(self.experiment.derived_variables[row-1].edge_id)
                if edge_index != None:
                    self.experiment.sequence[edge_index].derived_variable_requested = -1
                self.experiment.names_of_derived_variables.remove(name)
                del self.experiment.derived_variables[row-1] # -1 is due to the dummy variable taking the first row
                self.derived_variables_table.setCurrentCell(row-1, 0)
                update.variables_tab(self, new_variables = False, lookup_variables = False)
                #update the derived_variable_requested 
                for position, variable in enumerate(self.experiment.derived_variables):
                    try:
                        edge_index_other_var = self.find_edge_index_by_id(variable.edge_id)
                        self.experiment.sequence[edge_index_other_var].derived_variable_requested = position
                    except:
                        pass

                print("\n", "Deleting variable:", name)  
                print("==== DERIVED VARIABLE NAMES SET ====")
                print(self.experiment.names_of_derived_variables)
                print("==== CURRENT DERIVED VARIABLES AND EDGE REFERENCES ====")
                for i, dv in enumerate(self.experiment.derived_variables):
                    print(f"[{i}] name: {dv.name}, edge_id: {dv.edge_id}, arguments: {dv.arguments}, function: {dv.function}, initial_value: {dv.initial_value}")
                    edge_index = self.find_edge_index_by_id(dv.edge_id)
                    if edge_index is not None:
                        edge = self.experiment.sequence[edge_index]
                        drv_idx = edge.derived_variable_requested
                        print(f"     → Edge index: {edge_index},      → derived_variable_requested: {drv_idx}")
                        # Optional check for consistency
                        if drv_idx != i:
                            print(f"  Mismatch: edge points to index {drv_idx}, but variable is at index {i}")
                    else:
                        print("     → Edge not found")
                print("==== ALL EDGES AND THEIR DERIVED VARIABLE REFERENCES ====")
                for i, edge in enumerate(self.experiment.sequence):
                    edge_id = getattr(edge, 'id', f"index_{i}")  # fallback if edge has no `id` field
                    drv_idx = edge.derived_variable_requested
                    if isinstance(drv_idx, int) and drv_idx >= 0 and drv_idx < len(self.experiment.derived_variables):
                        variable_name = self.experiment.derived_variables[drv_idx].name
                    elif drv_idx == -1:
                        variable_name = "(none)"
                    else:
                        variable_name = "(invalid index)"
                    print(f"[{i}] edge_id: {edge_id}, derived_variable_requested: {drv_idx}, → variable: {variable_name}")
                print("\n", "\n")

            else: #Derived variable is used and can not be deleted
                self.experiment.variables[backup.name] = backup
                update.digital_analog_dds_mirny_tabs(self)
                update.variables_tab(self, new_variables = False, lookup_variables = False)
                self.error_message('The variable is used in %s.'%return_value,'Can not delete used variable')
    except: #In case the user pressed delete variable button without selecting the variable that needs to be deleted
        self.error_message("Select the variable that needs to be deleted", "No variable selected")


# ============================================================================
# EXPERIMENT LIST BUTTON HANDLERS
# ============================================================================

def handle_add_element_experiment_list_button_clicked(self):
    """Collect new experiment metadata via dialog and append it to the list."""
    #Pop up window to allow user to enter the name of the digital title
    self.dialog = QDialog()
    self.dialog.setGeometry(*self.scale_geom(710, 435, 600, 200))
    self.dialog.setFont(QFont('Arial', self.scale_font(14)))
    value_input = QLineEdit()
    value_input.setPlaceholderText("Type the name of new experiment")
    value_input_cap = QLineEdit()
    value_input_cap.setPlaceholderText("Type the x-caption for new experiment (Example: 'TOF, ms')")
    dialog_layout = QVBoxLayout()
    button_update = QPushButton("Update")
    button_cancel = QPushButton("Cancel")
    dialog_layout.addWidget(value_input)
    dialog_layout.addWidget(value_input_cap)
    dialog_buttons_layout = QHBoxLayout()
    dialog_buttons_layout.addWidget(button_update)
    dialog_buttons_layout.addWidget(button_cancel)
    dialog_layout.addLayout(dialog_buttons_layout)
    self.dialog.setLayout(dialog_layout)

    button_update.clicked.connect(lambda:self.update_experiment_names_list(name = value_input.text(),caption = value_input_cap.text()))
    button_cancel.clicked.connect(lambda:self.dialog.reject())
    self.dialog.setWindowTitle("New experiment to add") 
    self.dialog.exec_()


def handle_delete_element_experiment_list_button_clicked(self):
    """Delete the selected experiment entry from the backing store and UI."""
    row = self.experiment_list_list_widget.currentRow()

    if row < 0:
        self.error_message("Select the experiment you want to delete.", "No experiment selected")
        return

    with open(self.repo_path / "experiment_specific_files" / config.which_project / "experiment_names.json", 'r', encoding="utf-8") as handle:
        data = json.load(handle)

    key = f"{int(row)}"
    if key not in data:
        self.error_message(f"Experiment entry with key {key} was not found in experiment_names.json", "Missing experiment")
        return

    experiment_name = data[key].get("name", "").strip()

    data_root = getattr(config, "experiment_data_root", "")
    if experiment_name and data_root:
        candidate_path = Path(data_root) / experiment_name
        try:
            has_data_directory = candidate_path.exists() and candidate_path.is_dir()
        except OSError as exc:
            self.error_message(
                f"Could not access the data directory for '{experiment_name}': {exc}",
                "Filesystem error"
            )
            return

        if has_data_directory:
            confirm_dialog = QInputDialog(self)
            confirm_dialog.setWindowTitle("Confirm experiment deletion")
            confirm_dialog.setLabelText(
                "There is data in the folder with this experiment name.\n"
                "Are you sure you want to delete it? Type DELETE if you are sure."
            )
            confirm_dialog.setTextEchoMode(QLineEdit.Normal)
            confirm_dialog.resize(*self.scale_geom(0, 0, 400, 120)[2:])

            if confirm_dialog.exec_() != QDialog.Accepted or confirm_dialog.textValue().strip().upper() != "DELETE":
                return

    del data[key]

    data = self._normalize_experiment_name_keys(data)

    with open(self.repo_path / "experiment_specific_files" / config.which_project / "experiment_names.json", 'w', encoding="utf-8") as handle:
        json.dump(data, handle, indent=4)

    if experiment_name:
        self._remove_experiment_log_rows(experiment_name)

    self.experiment_list_list_widget.takeItem(row)
    remaining = self.experiment_list_list_widget.count()
    if remaining > 0:
        new_row = min(row, remaining - 1)
        self.experiment_list_list_widget.setCurrentRow(new_row)
        self.chosen_experiment_changed()
    else:
        self.experiment_list_btn_delete.setEnabled(False)
        self.experiment_list_chosen_line.clear()
        self.experiment_list_chosen_line_caption.clear()
        self.experiment.experimental_data.experiment_name = ''
        self.experiment.experimental_data.comment = ''
        self.experiment.experimental_data.path = ''
        self.experiment.experimental_data.experiment_id = -1


# ============================================================================
# DEBUG BUTTON HANDLER
# ============================================================================

def handle_dummy_button_clicked(self):
    ''' 
    Function is used to debug the program. Can be used to check the variables at different time stamps.
    Commented out examlpes might be usefull starting point. Usually debugging is done by printing values
    in the console of the VS Code and observing how parameters are being changed.
    '''
    # print("DERIVED VARIABLES")
    # for variable in self.experiment.derived_variables:
    #     print(variable.name, variable.arguments, variable.function, variable.initial_value)
    # print(len(self.experiment.derived_variables))
    # arguments = self.experiment.derived_variables
    # for argument in arguments:
    #     print(argument.name)
    
    # print("SAMPLER")
    # for edge in self.experiment.sequence:
    #     print(edge.name, edge.sampler)    

    # print("analog channel values")
    # for edge in self.experiment.sequence:
    #     for ind, channel in enumerate(edge.analog):
    #         print("Channel", ind, "val", channel.value, "evaluation", channel.evaluation, "for_python", channel.for_python)

    # print("NEW variables")
    # for item in self.experiment.new_variables:
    #     print("name: ", item.name, "value: ", item.value, "for python: ", item.for_python)
    
    # print("VARIABLES")
    # for key, item in self.experiment.variables.items():
    #     print("name: ", item.name, "value: ", item.value, "is_lookup:", item.is_lookup, "for python: ", item.for_python)
    # print("LOOKUP VARIABLES")
    # for variable in self.experiment.lookup_variables:
    #     print("name: ", variable.name, "argument:", variable.argument)

    # print("EDGES")
    # for ind, edge in enumerate(self.experiment.sequence):
    #     print("edge", ind)
    #     print("chanel", ind, "evaluation", edge.evaluation, "for_python", edge.for_python, "scanned", edge.is_scanned)
    #     print("derived variable requested", edge.derived_variable_requested)
    # print("END")

    # MIRNY
    # print("Mirny")
    # for ind, edge in enumerate(self.experiment.sequence):
    #     for mirny in edge.mirny:
    #         print(ind, mirny.frequency.is_sampled)

    # print("analog channel values")
    # for edge in self.experiment.sequence:
    #     for ind, channel in enumerate(edge.analog):
    #         print("Channel", ind, "val", channel.value, "evaluation", channel.evaluation)

    # print("scanned_variables")
    # for item in self.experiment.scanned_variables:
    #     print(item.name, item.min_val, item.max_val)

    #print(self.experiment.sampler_variables)
    #print(self.experiment.dynamic_variables_names)
    # print("new variables")
    # for item in self.experiment.new_variables:
    #     print(item.name, item.value, item.is_scanned)

    
    # for item in self.experiment.derived_variables:
    #     print(item.name)

    # for item in self.experiment.derived_variables:

        # print(item.derived_variable_requested)
    # if self.experiment.dynamic_variables[0].text() == "Freq"

    # for ind, edge in enumerate(self.experiment.sequence):
    #     print("edge number: ", ind, "id: ", edge.id, "expression: ", edge.expression, "evaluation: ", edge.evaluation, "value: " , edge.value, "for_python: ", edge.for_python)

    print(self.experiment.sequence[2].id)


def handle_clear_logger_button_clicked(main_window):
    '''Clear the logger widget.'''
    main_window.logger.clear()


def handle_add_scanned_variable_button_pressed(main_window):
    '''Add a scanned variable with name "None" and update scan_table.'''
    # default Dim is the next position in the scanned_variables list
    next_dim = len(main_window.experiment.scanned_variables) + 1
    main_window.experiment.scanned_variables.append(ScannedVariable("None", 0.0, 0.0, 0.0, Dim=next_dim))
    update.scan_table(main_window)
    update.digital_analog_dds_mirny_tabs(main_window)
    update.variable_tables(main_window)


def handle_delete_scanned_variable_button_pressed(main_window):
    '''Delete the selected scanned variable.'''
    try:
        row = main_window.scan_table_parameters.selectedIndexes()[0].row()
        variable = main_window.experiment.scanned_variables[row]
        index = main_window.index_of_a_new_variable(variable.name)
        if index != None:
            # Revert the value and scanning state of the variable
            main_window.experiment.variables[variable.name].is_scanned = False
            main_window.experiment.variables[variable.name].value = main_window.experiment.new_variables[index].value
            main_window.experiment.new_variables[index].is_scanned = False
            main_window.experiment.variables[variable.name].for_python = main_window.experiment.variables[variable.name].value
        del main_window.experiment.scanned_variables[row]
        # Reassign per-variable step indices (for_python) for remaining scanned variables
        for i, rem_var in enumerate(main_window.experiment.scanned_variables):
            if rem_var.name != "None" and rem_var.name in main_window.experiment.variables:
                main_window.experiment.variables[rem_var.name].is_scanned = True
                main_window.experiment.variables[rem_var.name].for_python = "self.%s[step%d]" % (rem_var.name, i+1)

        # Update the variables tab first to update values for evaluation
        update.variable_tables(main_window)
        update.scan_table(main_window)
        update.digital_analog_dds_mirny_tabs(main_window)
        main_window.count_scanned_variables()
        if row != 0:
            main_window.scan_table_parameters.setCurrentCell(row-1, 0)
    except:
        main_window.error_message("Select the variable that needs to be deleted", "No variable selected")


def handle_skip_images_button_clicked(main_window):
    '''Toggle initial camera trigger 10 times for image acquisition issues.'''
    main_window.experiment.skip_images = not main_window.experiment.skip_images
    if main_window.experiment.skip_images:
        main_window.skip_images_button.setStyleSheet(""" QPushButton {background-color: green; color: white}  QToolTip {color: black}""")
    else:
        main_window.skip_images_button.setStyleSheet(""" QPushButton {background-color: red; color: white}  QToolTip {color: black}""")


def handle_cam_trigger_off_button_clicked(main_window):
    '''Toggle camera trigger off to run experiment without triggering camera.'''
    main_window.experiment.cam_trigger_off = not main_window.experiment.cam_trigger_off
    if main_window.experiment.cam_trigger_off:
        main_window.cam_trigger_off_button.setStyleSheet(""" QPushButton {background-color: green; color: white}  QToolTip {color: black}""")
    else:
        main_window.cam_trigger_off_button.setStyleSheet(""" QPushButton {background-color: red; color: white}  QToolTip {color: black}""")


def handle_cont_run_after_exp_button_clicked(main_window):
    '''Toggle continuous run right after an experiment.'''
    main_window.experiment.cont_run_after_exp = not main_window.experiment.cont_run_after_exp
    if main_window.experiment.cont_run_after_exp:
        main_window.cont_run_after_exp_button.setStyleSheet(""" QPushButton {background-color: green; color: white}  QToolTip {color: black}""")
    else:
        main_window.cont_run_after_exp_button.setStyleSheet(""" QPushButton {background-color: red; color: white}  QToolTip {color: black}""")


def handle_add_ramped_variable_button_pressed(main_window):
    '''Add a ramped variable with name "None" and update ramp_table.'''
    main_window.experiment.ramped_variables.append(RampedVariable("None", 0, 0, 0.0, 0))
    update.ramp_table(main_window)
    update.digital_analog_dds_mirny_tabs(main_window)
    update.variable_tables(main_window)


def handle_delete_ramped_variable_button_pressed(main_window):
    '''Delete the selected ramped variable.'''
    try:
        row = main_window.ramp_table_parameters.selectedIndexes()[0].row()
        variable = main_window.experiment.ramped_variables[row]
        index = main_window.index_of_a_new_variable(variable.name)
        if index != None:
            # Revert the value and ramping state of the variable
            main_window.experiment.variables[variable.name].is_ramped = False
            main_window.experiment.variables[variable.name].value = main_window.experiment.new_variables[index].value
            main_window.experiment.new_variables[index].is_ramped = False
            main_window.experiment.variables[variable.name].for_python = main_window.experiment.variables[variable.name].value
        del main_window.experiment.ramped_variables[row]
        # Update the variables tab first to update values for evaluation
        update.variable_tables(main_window)
        update.ramp_table(main_window)
        update.digital_analog_dds_mirny_tabs(main_window)
        if row != 0:
            main_window.ramp_table_parameters.setCurrentCell(row-1, 0)
        try:
            if main_window.experiment.do_ramp == True:
                main_window.update_sequence_edge_colors()
        except:
            pass
    except:
        main_window.error_message("Select the variable that needs to be deleted", "No variable selected")


def handle_create_new_variable_button_clicked(main_window):
    '''Create a new user defined variable with the lowest unused available variable name.'''
    variable_name = main_window.find_new_variable_name_unused()
    main_window.experiment.new_variables.append(Variable(variable_name, 0.0, 0.0))
    main_window.experiment.variables[variable_name] = Variable(variable_name, 0.0, 0.0)
    update.variable_tables(main_window)


def handle_load_lookup_list_button_clicked(main_window):
    """Attach a lookup table file to the selected lookup variable."""
    try:
        row = main_window.lookup_variables_table.selectedIndexes()[0].row()
        lookup_variable = main_window.experiment.lookup_variables[row-1]
        if row == 0:
            main_window.error_message("You can not modify dummy variable", "Wrong variable")
        else:
            loaded_file_path = QFileDialog.getOpenFileName(main_window, "Open File")[0]
            loaded_file_name = loaded_file_path.split("/")[-1]
            if loaded_file_path != "":
                try:
                    lookup_variable.lookup_list = list(loadmat(loaded_file_path)['array'][0])
                    lookup_variable.lookup_list_name = loaded_file_name
                    main_window.update_off()
                    main_window.lookup_variables_table.item(row, 2).setText(loaded_file_name)
                    main_window.update_on()
                except:
                    main_window.error_message('Could not load the file.', 'Error')
    except:
        main_window.error_message("Select the lookup variable you want to load the lookup list for", "No variable selected selected")


def handle_delete_lookup_variable_button_clicked(main_window):
    '''Delete the selected lookup variable from the table.'''
    try:
        row = main_window.lookup_variables_table.selectedIndexes()[0].row()
        if row == 0:
            main_window.error_message("You can not delete a dummy example", "Protected variable")
        else:
            name = main_window.lookup_variables_table.item(row, 0).text()
            main_window.experiment.names_of_lookup_variables.remove(name)
            del main_window.experiment.lookup_variables[row-1]
            del main_window.experiment.variables[name]
            main_window.lookup_variables_table.setCurrentCell(row-1, 0)
            update.variables_tab(main_window, new_variables=False, derived_variables=False)
    except:
        main_window.error_message("Select the variable that needs to be deleted", "No variable selected")
