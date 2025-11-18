'''
Miscellaneous (not buttons and not changes) handlers for Quantrol GUI.

This module contains standalone event handler logic for the Quantrol control system.
These are simpler handlers that don't require complex internal state manipulation.
More complex handlers remain in source_code.py as methods.

Author  :   Alexei Gurchenko (refactored from source_code.py)
Email   :   alexei.gurchenko@ist.ac.at
Date    :   11.2025
Version :   2.3.3
Contact :   https://hostenlab.pages.ist.ac.at/contact/
'''

import json
import update
from PyQt5.QtWidgets import QListWidgetItem, QFileDialog
from scipy.io import loadmat
from data_structures import ScannedVariable, RampedVariable, DerivedVariable, LookupVariable, Variable
from validation import show_error_message, remove_restricted_characters



def handle_scan_table_checked(main_window):
    '''Handle scan table checkbox state change.'''
    if main_window.to_update:
        main_window.experiment.do_scan = main_window.scan_table.isChecked()
        
        if not main_window.experiment.do_scan:
            # User unchecked scan - restore pre-scan values
            for item in main_window.experiment.new_variables:
                main_window.experiment.variables[item.name].value = item.value
        else:
            # User checked scan - assign scanned variables to min values
            for variable in main_window.experiment.scanned_variables:
                if variable.name != "None":
                    main_window.experiment.variables[variable.name].value = variable.min_val
        
        update.digital_analog_dds_mirny_tabs(main_window)
        update.variable_tables(main_window)


def handle_ramp_table_checked(main_window):
    '''Handle ramp table checkbox state change.'''
    if main_window.to_update:
        main_window.experiment.do_ramp = main_window.ramp_table.isChecked()
        if main_window.experiment.do_ramp == False:
            # User unchecked the ramp
            for item in main_window.experiment.new_variables: 
                main_window.experiment.variables[item.name].functionramp = item.value 
                for row in range(main_window.sequence_num_rows): 
                    id_item = main_window.sequence_table.item(row, 2)
                    try:
                        id_item.setBackground(main_window.white)
                    except ValueError:
                        pass 
        else:  # ramp is checked
            for variable in main_window.experiment.ramped_variables:
                if variable.name != "None":
                    main_window.experiment.variables[variable.name].functionramp = variable.functionramp 
                # update color of sequence edges
                main_window.update_sequence_edge_colors()
                
        update.digital_analog_dds_mirny_tabs(main_window)
        update.variable_tables(main_window)


