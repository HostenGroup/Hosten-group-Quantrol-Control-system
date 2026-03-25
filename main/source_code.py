'''
    |||||||   ||    ||    ||    ||    ||  ||||||||  ||||||    |||||   ||
    ||   ||   ||    ||   ||||   |||   ||     ||     ||   ||  ||   ||  ||
    ||   ||   ||    ||  ||  ||  || || ||     ||     ||   ||  ||   ||  ||
    ||   ||   ||    ||  ||||||  ||  | ||     ||     ||||||   ||   ||  ||
    ||   ||   ||    ||  ||  ||  ||   |||     ||     ||  ||   ||   ||  ||
    ||||||||   ||||||   ||  ||  ||    ||     ||     ||   ||   |||||   ||||||
          ||

Quantrol is used as a high level solution built on top of artiq infrastructure to allow scientists to use precise
timing control system with no prerequisite of coding. It features an easy to interpret table based experimental
sequence description, variables use and scan, input values allowed range check and many more.

Author  :   Vyacheslav Li (until 2.0), Andrea Pupic, Alexei Gurchenko (later versions)
Email   :   vyacheslav.li.1991@gmail.com, andrea.pupic@ist.ac.at, alexei.gurchenko@ist.ac.at
Date    :   07.30.2024 (2.0)
Update  :   09.2025 
Version :   2.3.3
Contact :   https://hostenlab.pages.ist.ac.at/contact/
'''

from os import error
import os
import sys
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
import write_to_python
import tabs
import pickle
from datetime import datetime, date
from copy import deepcopy
import update
import threading
import subprocess
import time
import config
from scipy.io import savemat, loadmat
# import pandas as pd
import json
import importlib
from pathlib import Path

# Import data structures from data_structures module
from data_structures import (
    Edge, Experiment, SlowDDS, ExperimentalData,
    DerivedVariable, LookupVariable, ScannedVariable, RampedVariable,
    Variable, CustomThread, Camera, Digital, Analog, DDS
)

# Import validation functions
from validation import (
    show_error_message, remove_restricted_characters, 
    validate_positive_number, validate_range
)

# Import file I/O functions
import file_io

# Import handlers
import other_handlers
import button_handlers
import change_handlers


# Subclass QMainWindow to customize your application's main window
class MainWindow(QMainWindow):
    '''
    Main window that includes everything that needs to be displayed to the user
    '''
    
    def __init__(self):
        super().__init__()

        
        #MAIN PAGE LAYOUT
        self.setWindowTitle("Quantrol. %s Group" %config.research_group_name)
        self.main_window = QTabWidget()
        self.setCentralWidget(self.main_window)

        ORIG_W = 1920
        ORIG_H = 1200

        # self.setGeometry(*self.scale_geom(0,0,1920,1200))
        tup = self._fit_to_work_area()
        CURRENT_W = tup[2]
        CURRENT_H = tup[3]
        
       

        #Declaring global variables

        # Geometry
        self.SCALE_W = float(1.0*CURRENT_W/ORIG_W)
        self.SCALE_H = float(1.0*CURRENT_H/ORIG_H)
        self.button_w = 200
        self.button_h = 30
        self.top_margin = 30
        self.sep = 10
        self.variables_table_width = 250
        self.bottom_buttons_y_val = 1200 - 2*self.button_h - 2*10 - self.button_h
        self.button_font = 12
        self.text_font = 12


        
        

        
        self.repo_path = Path(__file__).resolve().parent.parent

        


        self.experiment = Experiment()
        self.sequence_num_rows = 1
        self.setting_dict = {0:"frequency", 1:"amplitude", 2:"attenuation", 3:"phase", 4:"state"}
        self.max_dict_dds = {0: 500,
                             1: 100,
                             2: 31.5,
                             3: 360,
                             4: 1} 
        
        self.min_dict_dds = {0: 0,
                             1: 0,
                             2: 0,
                             3: 0,
                             4: 0} 
        
        self.mirny_amp_values_dBm = {0: -4.0,
                                     1: -1.0,
                                     2: 2.0,
                                     3: 5.0}
        
        self.max_dict_mirny = {0: 4000,
                               1: float("inf"),
                               2: 31.5,
                               3: 360,
                               4: 1} #max and min needs to be checked
        
        self.min_dict_mirny = {0: 54,
                               1: -1*float("inf"),
                               2: 0,
                               3: 0,
                               4: 0}  #max and min needs to be checked
        
        self.to_update = False
        self.green = QColor(37,211,102)
        self.red = QColor(247,140,140)
        self.grey = QColor(100,100,100)
        self.light_grey = QColor(211,211,211)
        self.cameo_pink = QColor(239,187,204)
        self.mimi_pink = QColor(255,218,233)
        self.melon = QColor(254,186,173)
        self.white = QColor(255,255,255)
        self.yellow = QColor(255, 255, 0)
        self.cyan = QColor(0, 255, 255)
        self.purple = QColor(200, 150, 255)
        self.right_green = QColor(180, 255, 180)
        self.wrong_red = QColor(255, 0, 1)
        self.texp_color = self.mimi_pink
        self._texp_locked = False
        self._updating_texp_lock = False
        self._openpyxl_missing_warned = False
        self.live_camera_window = None
        self._live_camera_import_error_shown = False


        self.experiment.variables['id0'] = Variable(name = "id0", value = 0.0, for_python = 0.0)
        self.experiment.variables[''] = Variable(name = '', value = 0.0, for_python = 0.0)   #in order to be able to process expressions like -5 we need to have it as first item in decode will be "" that should be 0    
        self.experiment.experimental_data = ExperimentalData()
        self.experiment.experimental_data.camera = Camera()
        self.experiment.sequence = [Edge(name = "Default")]
        
        self.init_default_values() #Reads the default state file and initializes the values
        self._ensure_title_lengths()
        self._ensure_variable_structures()
        tabs.sequence_tab_build(self)
        tabs.variables_tab_build(self)
        tabs.acquisition_tab_build(self)
        if config.digital_channels_number > 0:
            tabs.digital_tab_build(self)
        if config.analog_channels_number > 0:
            tabs.analog_tab_build(self)
        if config.dds_channels_number > 0:
            tabs.dds_tab_build(self)
        if config.sampler_channels_number > 0:
            tabs.sampler_tab_build(self)
        if config.mirny_channels_number > 0:
            tabs.mirny_tab_build(self)
        if config.slow_dds_channels_number > 0:
            tabs.slow_dds_tab_build(self)
        
        # tabs.making_separator(self)
       
        #ADDING TABS TO MAIN WINDOW
        self.main_window.addTab(self.sequence_tab_widget, "Sequence")
        self.main_window.addTab(self.acquisition_tab_widget, "Acquisition")
        if config.digital_channels_number > 0:
            self.main_window.addTab(self.digital_tab_widget, "Digital")
        if config.analog_channels_number > 0:
           self.main_window.addTab(self.analog_tab_widget, "Analog")
        if config.dds_channels_number > 0:
            self.main_window.addTab(self.dds_tab_widget, "DDS")
        if config.mirny_channels_number > 0:
            self.main_window.addTab(self.mirny_tab_widget, "Mirny")
        self.main_window.addTab(self.variables_tab_widget, "Variables")
        if config.sampler_channels_number > 0:
            self.main_window.addTab(self.sampler_tab_widget, "Sampler")
        if config.slow_dds_channels_number > 0:
            self.main_window.addTab(self.slow_dds_tab_widget, "Slow DDS")
        self.to_update = True


    '''
    ||||||  ||    ||  ||    ||  |||||| |||||||| ||||||   |||||   ||    ||  ||||||||
    ||      ||    ||  |||   ||  ||  ||    ||      ||    ||   ||  |||   ||  ||    ||
    ||      ||    ||  || || ||  ||        ||      ||    ||   ||  || || ||    ||    
    ||||||  ||    ||  ||  | ||  ||        ||      ||    ||   ||  ||  | ||      ||  
    ||      ||    ||  ||   |||  ||  ||    ||      ||    ||   ||  ||   |||  ||    ||
    ||       ||||||   ||    ||  ||||||    ||    ||||||   |||||   ||    ||  ||||||||
    '''





    def _fit_to_work_area(self):
        '''
        The function sets the geometry of the main window to the size of the working area of the screen
        '''
        self.showNormal()
        QApplication.processEvents()

        screen = self.windowHandle().screen() or QGuiApplication.primaryScreen()
        work = screen.availableGeometry()

        # frame margins
        frame = self.frameGeometry()
        client = self.geometry()
        ml = client.x() - frame.x()
        mt = client.y() - frame.y()
        mr = frame.right() - client.right()
        mb = frame.bottom() - client.bottom()

        # set so client fills work area
        work_adj = work.adjusted(ml, mt, -mr, -mb)
        self.setGeometry(work_adj)
        return work_adj.x(), work_adj.y(), work_adj.width(), work_adj.height()

    def scale_geom(self,x,y,w,h):
        '''
        The function is used to scale the geometry
        '''
        return ( int(x*self.SCALE_W), int(y*self.SCALE_H), int(w*self.SCALE_W), int(h*self.SCALE_H) )
        
    def scale_font(self,s):
        '''
        The function is used to scale the font
        '''
        
        return int(s*min(self.SCALE_W, self.SCALE_H))
        # return int(s*(self.SCALE_W * self.SCALE_H)**(0.5))
        # return int(s*(self.SCALE_W + self.SCALE_H)/2)

    def init_default_values(self):
        '''
        The function downloads the default state and initializes it by assigning the current experimental
        to the default values
        '''
        default_path = self.repo_path / "default" / "default"
        incompatible = False
        file_not_found = False
        try:
            with open(default_path, 'rb') as file:
                default_experiment = pickle.load(file)
        except FileNotFoundError:
            file_not_found = True
            default_experiment = None
        except Exception as e:
            default_experiment = None
        
        if default_experiment is not None:
            try:
                compatible = True
                
                # Check digital channels
                if len(default_experiment.sequence[0].digital) != config.digital_channels_number:
                    compatible = False
                
                # Check analog channels
                if len(default_experiment.sequence[0].analog) != config.analog_channels_number:
                    compatible = False
                
                # Check DDS channels
                if len(default_experiment.sequence[0].dds) != config.dds_channels_number:
                    compatible = False
                
                # Check sampler channels
                if len(default_experiment.sequence[0].sampler) != config.sampler_channels_number:
                    compatible = False
                
                # Check Mirny channels
                if len(default_experiment.sequence[0].mirny) != config.mirny_channels_number:
                    compatible = False
                
                # Check slow DDS only if configured
                if config.slow_dds_channels_number > 0:
                    if not hasattr(default_experiment, 'slow_dds'):
                        compatible = False
                    elif len(default_experiment.slow_dds) != config.slow_dds_channels_number:
                        compatible = False
                
                if compatible:
                    #reassign the default values to the current self.experiment object
                    self.experiment.sequence[0] = deepcopy(default_experiment.sequence[0])
                    self.experiment.title_digital_tab = deepcopy(default_experiment.title_digital_tab)
                    self.experiment.title_analog_tab = deepcopy(default_experiment.title_analog_tab)
                    self.experiment.title_dds_tab = deepcopy(default_experiment.title_dds_tab)
                    self.experiment.title_mirny_tab = deepcopy(default_experiment.title_mirny_tab)
                    self.experiment.title_sampler_tab = deepcopy(default_experiment.title_sampler_tab)
                    self._ensure_variable_structures()
                    if config.slow_dds_channels_number > 0 and hasattr(default_experiment, 'title_slow_dds_tab'):
                        self.experiment.title_slow_dds_tab = deepcopy(default_experiment.title_slow_dds_tab)
                else:
                    incompatible = True
            except Exception as e:
                incompatible = True
        
        if file_not_found or incompatible:
            self.experiment.sequence[0] = Edge(name="Default")
            if config.digital_channels_number > 0:
                self.experiment.title_digital_tab = ["#", "Name", "Time (ms)", ""] + [f"D{i}" for i in range(config.digital_channels_number)]
            if config.analog_channels_number > 0:
                self.experiment.title_analog_tab = ["#", "Name", "Time (ms)", ""] + [f"A{i}" for i in range(config.analog_channels_number)]
            if config.dds_channels_number > 0:
                self.experiment.title_dds_tab = ["#", "Name", "Time (ms)", ""] + [f"DDS{i}" for i in range(config.dds_channels_number)]            
            if config.mirny_channels_number > 0:
                self.experiment.title_mirny_tab = ["#", "Name", "Time (ms)", ""] + [f"M{i}" for i in range(config.mirny_channels_number)]            
            if config.sampler_channels_number > 0:
                self.experiment.title_sampler_tab = ["#", "Name", "Time (ms)", ""] + [f"S{i}" for i in range(config.sampler_channels_number)]            
            if config.slow_dds_channels_number > 0:
                self.experiment.title_slow_dds_tab = ["#", "Name", "Time (ms)", ""] + [f"slow DDS{i}" for i in range(config.slow_dds_channels_number)]            
            if incompatible:
                self.error_message('Default file is incompatible. Initializing the DEFAULT default values and updating the default file.', 'Error')
            elif file_not_found:
                self.error_message('Default file is not found. Initializing the DEFAULT default values and updating the default file.', 'Error')
            os.makedirs(self.repo_path / "default", exist_ok=True)
            save_path = self.repo_path / "default" / "default"
            with open(save_path, 'wb') as file:
                pickle.dump(self.experiment, file)


    def _ensure_title_lengths(self):
        """Ensure each per-tab title list matches the configured channel counts."""
        self._ensure_title_list('title_digital_tab', config.digital_channels_number, prefix='D')
        self._ensure_title_list('title_analog_tab', config.analog_channels_number, prefix='A')
        self._ensure_title_list('title_dds_tab', config.dds_channels_number, prefix='DDS')
        self._ensure_title_list('title_mirny_tab', config.mirny_channels_number, prefix='M')
        self._ensure_title_list('title_sampler_tab', config.sampler_channels_number, prefix='S')
        self._ensure_title_list('title_slow_dds_tab', config.slow_dds_channels_number, prefix='slow DDS')


    def _ensure_variable_structures(self):
        """Normalize experiment variable records into self.Variable objects."""
        raw_new_variables = getattr(self.experiment, 'new_variables', [])
        if isinstance(raw_new_variables, list):
            candidate_variables = raw_new_variables
        else:
            try:
                candidate_variables = list(raw_new_variables)
            except TypeError:
                candidate_variables = []

        normalized_variables = []
        for candidate in candidate_variables:
            if isinstance(candidate, Variable):
                normalized_variables.append(candidate)
                continue
            if isinstance(candidate, dict):
                name = candidate.get('name', '')
                value = candidate.get('value', 0.0)
                for_python = candidate.get('for_python', value)
                normalized_variables.append(
                    Variable(
                        name=name,
                        value=value,
                        for_python=for_python,
                        is_scanned=candidate.get('is_scanned', False),
                        is_ramped=candidate.get('is_ramped', False),
                        is_sampled=candidate.get('is_sampled', False),
                        is_derived=candidate.get('is_derived', False),
                        is_lookup=candidate.get('is_lookup', False),
                    )
                )
                continue
            name = getattr(candidate, 'name', None)
            if name is None:
                continue
            value = getattr(candidate, 'value', 0.0)
            for_python = getattr(candidate, 'for_python', value)
            normalized_variables.append(
                Variable(
                    name=name,
                    value=value,
                    for_python=for_python,
                    is_scanned=getattr(candidate, 'is_scanned', False),
                    is_ramped=getattr(candidate, 'is_ramped', False),
                    is_sampled=getattr(candidate, 'is_sampled', False),
                    is_derived=getattr(candidate, 'is_derived', False),
                    is_lookup=getattr(candidate, 'is_lookup', False),
                )
            )

        self.experiment.new_variables = normalized_variables

        variables_dict = getattr(self.experiment, 'variables', None)
        if not isinstance(variables_dict, dict):
            variables_dict = {}
        self.experiment.variables = variables_dict

        for variable in self.experiment.new_variables:
            existing_entry = self.experiment.variables.get(variable.name)
            if isinstance(existing_entry, Variable):
                continue
            if isinstance(existing_entry, dict):
                self.experiment.variables[variable.name] = Variable(
                    name=existing_entry.get('name', variable.name),
                    value=existing_entry.get('value', variable.value),
                    for_python=existing_entry.get('for_python', variable.for_python),
                    is_scanned=existing_entry.get('is_scanned', variable.is_scanned),
                    is_ramped=existing_entry.get('is_ramped', variable.is_ramped),
                    is_sampled=existing_entry.get('is_sampled', variable.is_sampled),
                    is_derived=existing_entry.get('is_derived', variable.is_derived),
                    is_lookup=existing_entry.get('is_lookup', variable.is_lookup),
                )
            else:
                self.experiment.variables[variable.name] = Variable(
                    name=variable.name,
                    value=getattr(existing_entry, 'value', variable.value),
                    for_python=getattr(existing_entry, 'for_python', variable.for_python),
                    is_scanned=getattr(existing_entry, 'is_scanned', variable.is_scanned),
                    is_ramped=getattr(existing_entry, 'is_ramped', variable.is_ramped),
                    is_sampled=getattr(existing_entry, 'is_sampled', variable.is_sampled),
                    is_derived=getattr(existing_entry, 'is_derived', variable.is_derived),
                    is_lookup=getattr(existing_entry, 'is_lookup', variable.is_lookup),
                )

        if 'id0' not in self.experiment.variables:
            self.experiment.variables['id0'] = Variable(name='id0', value=0.0, for_python=0.0)
        if '' not in self.experiment.variables:
            self.experiment.variables[''] = Variable(name='', value=0.0, for_python=0.0)


    def _adjust_edge_channel_list(self, edge, attr_name, expected_count, factory, factory_kwargs=None, source_items=None):
        """Trim or extend an edge's channel list to match current channel count."""
        trimmed = 0
        added = 0
        try:
            items = getattr(edge, attr_name)
        except AttributeError:
            items = []

        if isinstance(items, list):
            working = list(items)
        else:
            try:
                working = list(items)
            except TypeError:
                working = []

        if expected_count <= 0:
            trimmed = len(working)
            working = []
        else:
            if len(working) > expected_count:
                trimmed = len(working) - expected_count
                working = working[:expected_count]
            elif len(working) < expected_count:
                missing = expected_count - len(working)
                # Top up the list with default objects so remaining columns render
                for _ in range(missing):
                    target_index = len(working)
                    template = None
                    if source_items and target_index < len(source_items):
                        try:
                            template = deepcopy(source_items[target_index])
                        except Exception:
                            template = None
                    if template is not None:
                        new_item = template
                        if hasattr(new_item, 'changed'):
                            new_item.changed = False
                        for nested_attr in ('frequency', 'amplitude', 'attenuation', 'phase', 'state'):
                            nested = getattr(new_item, nested_attr, None)
                            if hasattr(nested, 'changed'):
                                nested.changed = False
                    else:
                        if factory_kwargs:
                            new_item = factory(**factory_kwargs)
                        else:
                            new_item = factory()
                    working.append(new_item)
                added = missing

        setattr(edge, attr_name, working)
        return trimmed, added


    def _adjust_edge_sampler_list(self, edge, expected_count):
        """Normalize sampler channel storage for a single edge."""
        trimmed = 0
        added = 0
        try:
            items = getattr(edge, 'sampler')
        except AttributeError:
            items = []

        if isinstance(items, list):
            working = list(items)
        else:
            try:
                working = list(items)
            except TypeError:
                working = []

        if expected_count <= 0:
            trimmed = len(working)
            working = []
        else:
            if len(working) > expected_count:
                trimmed = len(working) - expected_count
                working = working[:expected_count]
            elif len(working) < expected_count:
                missing = expected_count - len(working)
                # Pad sampler list with inert placeholders when hardware has more inputs
                working.extend(['0'] * missing)
                added = missing

        setattr(edge, 'sampler', working)
        return trimmed, added


    def _adjust_slow_dds(self, expected_count):
        """Align slow DDS collection with the configured channel count."""
        trimmed = 0
        added = 0
        slow_dds = getattr(self.experiment, 'slow_dds', None)
        if isinstance(slow_dds, list):
            working = list(slow_dds)
        else:
            try:
                working = list(slow_dds)
            except TypeError:
                working = []

        if expected_count <= 0:
            trimmed = len(working)
            working = []
        else:
            if len(working) > expected_count:
                trimmed = len(working) - expected_count
                working = working[:expected_count]
            elif len(working) < expected_count:
                missing = expected_count - len(working)
                # Populate newly available slots with default slow DDS objects
                for _ in range(missing):
                    working.append(SlowDDS())
                added = missing

        self.experiment.slow_dds = working
        return trimmed, added


    def _reconcile_loaded_sequence_layout(self):
        """Align loaded sequence channel data with current hardware configuration."""
        # Track truncation/extension counts for each channel family so we can inform the user
        stats = {
            'digital': {'trimmed': 0, 'added': 0},
            'analog': {'trimmed': 0, 'added': 0},
            'dds': {'trimmed': 0, 'added': 0},
            'mirny': {'trimmed': 0, 'added': 0},
            'sampler': {'trimmed': 0, 'added': 0},
            'slow_dds': {'trimmed': 0, 'added': 0},
        }

        sequence = getattr(self.experiment, 'sequence', [])
        if not isinstance(sequence, list):
            try:
                sequence = list(sequence)
            except TypeError:
                sequence = []
            self.experiment.sequence = sequence

        channel_specs = [
            ('digital', config.digital_channels_number, Digital, None),
            ('analog', config.analog_channels_number, Analog, None),
            ('dds', config.dds_channels_number, DDS, None),
            ('mirny', config.mirny_channels_number, DDS, {'is_mirny': True}),
        ]

        for index, edge in enumerate(sequence):
            for name, expected, factory, kwargs in channel_specs:
                filtered_kwargs = kwargs if kwargs else None
                source_items = None
                if index > 0:
                    try:
                        source_items = getattr(sequence[index - 1], name)
                    except AttributeError:
                        source_items = None
                # Only seed defaults on the very first edge; later edges inherit the previous edge state
                trimmed, added = self._adjust_edge_channel_list(edge, name, expected, factory, filtered_kwargs, source_items)
                stats[name]['trimmed'] += trimmed
                stats[name]['added'] += added
            trimmed, added = self._adjust_edge_sampler_list(edge, config.sampler_channels_number)
            stats['sampler']['trimmed'] += trimmed
            stats['sampler']['added'] += added

        trimmed, added = self._adjust_slow_dds(config.slow_dds_channels_number)
        stats['slow_dds']['trimmed'] += trimmed
        stats['slow_dds']['added'] += added

        # Convert raw adjustment counts into short human-friendly log messages
        friendly_names = {
            'digital': 'digital',
            'analog': 'analog',
            'dds': 'DDS',
            'mirny': 'Mirny',
            'sampler': 'sampler',
            'slow_dds': 'slow DDS',
        }

        notes = []
        for key, label in friendly_names.items():
            trimmed = stats[key]['trimmed']
            added = stats[key]['added']
            if not trimmed and not added:
                continue
            parts = []
            if trimmed:
                parts.append(f"removed {trimmed}")
            if added:
                noun = "default" if added == 1 else "defaults"
                parts.append(f"added {added} {noun}")
            notes.append(f"{label}: {', '.join(parts)}")

        return notes


    def _ensure_title_list(self, attr_name, channel_count, prefix='X'):
        """Pad or trim a title list so it aligns with the expected channel count."""
        if channel_count <= 0:
            setattr(self.experiment, attr_name, [])
            return

        base_titles = ["#", "Name", "Time (ms)", ""]
        existing = getattr(self.experiment, attr_name, None)
        if isinstance(existing, list):
            titles = list(existing)
        elif existing is None:
            titles = []
        else:
            try:
                titles = list(existing)
            except TypeError:
                titles = []

        # Ensure the leading columns exist
        for idx in range(4):
            if len(titles) <= idx:
                titles.append(base_titles[idx])
            elif idx < len(base_titles) and not titles[idx]:
                titles[idx] = base_titles[idx]

        required_len = 4 + channel_count
        # Extend with default names if missing
        next_index = max(0, len(titles) - 4)
        while len(titles) < required_len:
            titles.append(f"{prefix}{next_index}")
            next_index += 1

        # Trim excess entries if there are more than expected
        if len(titles) > required_len:
            titles = titles[:required_len]

        setattr(self.experiment, attr_name, titles)


    def message_to_logger(self, message):
        '''
        The function is taking a message in terms of the String and displays it into the logger with the current time stamp
        where the time is the system time now
        '''
        self.logger.appendPlainText(datetime.now().strftime("%D %H:%M:%S - ") + message)



    def update_on(self):
        '''
        Function that sets the self.to_update to true. It was created to make the code more readable
        '''
        self.to_update = True



    def update_off(self):
        '''
        Function that sets the self.to_update to false. It was created to make the code more readable
        '''
        self.to_update = False



    def error_message(self, text, title):
        '''
        Function that takes text and title and creates an error pop up message with the provided title and text
        '''
        show_error_message(text, title)
 

    def decode_input(self, text):
        '''
        Function is used to decode the user input in a form of a simple mathematical expression. It interprets chunks of text 
        until the next mathematical operator or the end of the text.
        '''
        index = 0
        output_eval = ""
        output_expression = ""
        output_for_python = ""
        current = ""
        is_scanned = False
        is_ramped = False
        is_sampled = False
        is_derived = False
        is_lookup = False
        text = text.replace(" ", "") # removing spaces
        text += "+" #Adding a plus in the end of the text in order to avoid typing additional operation for the last element
        while index < len(text):
            #Adding the next character
            current += text[index]
            index += 1
            if text[index] == "-" or text[index] == "+" or text[index] == "/" or text[index] == "*":
                current.replace(" ", "")
                try: #If the current convertible to float type of value
                    # float_current = float(current)
                    float_current = float(int(float(current)*1e6)/1e6) # rounding numbers down to 6 decimal places
                    output_expression += str(float_current) + text[index]
                    output_eval += str(float_current) + text[index]
                    output_for_python += str(float_current) + text[index]
                except: #If the current is a variable name
                    output_expression += current + text[index]
                    output_eval += "self.experiment.variables['" + current + "'].value" + text[index]
                    variable = self.experiment.variables[current]
                    if self.experiment.do_scan and variable.is_scanned:#if scanned assign the python form else assign the value
                        is_scanned = True
                        output_for_python += str(self.experiment.variables[current].for_python) + text[index]
                    elif self.experiment.do_ramp and variable.is_ramped: #if ramped assign the python form else assign the value
                        is_ramped = True 
                        output_for_python += str(self.experiment.variables[current].for_python) + text[index] 
                    elif current in self.experiment.sampler_variables: #if sampled assign the name itself
                        output_for_python += "%s" %current + text[index]
                        is_sampled = True
                    elif variable.is_derived: #if derived assign the name itself
                        output_for_python += "%s" %current + text[index]
                        is_derived = True
                    elif variable.is_lookup: #if lookup assign the self.name[argument] 
                        output_for_python += "self.%s[(%s-1)/0.1]"%(current, self.experiment.variables[current].argument) + text[index]
                        is_lookup = True
                    else:
                        output_for_python += str(variable.value) + text[index]
                current = ""
                index += 1
        # Removing all additional characters in the end. Making a+2+ into a+2
        output_eval = output_eval[:-1]
        output_for_python = output_for_python[:-1]
        output_expression = output_expression[:-1]
        # If for_python can be evaluated, then just store the value. Otherwise we keep the original form
        try:
            exec("self.temp =" + output_for_python)
            output_for_python = str(float(self.temp))
        except:
            pass
        # If evaluation can be evaluated, then store the value. Otherwise we keep the original form
        try:
            output_eval = str(float(output_eval))
        except:
            pass
        return (output_expression, output_eval, output_for_python, is_scanned, is_ramped, is_sampled, is_derived, is_lookup)


    def remove_restricted_characters(self, text):
        '''
        Function is used to remove the restricted characters from the variable names.
        It takes the initial name as a String input and returns the String of the modified text
        '''
        return remove_restricted_characters(text)
    

    
    def update_sequence_edge_colors(self): 
        # update color of sequence edges:
        # green when start_id is right before end_id, red when edge between start_id and end_id, which all other edges and when ramp not checked 
        for edge_index in range(self.sequence_num_rows):  # initialize all to white
            id_item = self.sequence_table.item(edge_index, 2)
            id_item.setBackground(self.white)
        for variable in self.experiment.ramped_variables: # go through all variable and color the edges
            row_start_id = None
            id_item_start_id = None
            row_end_id = None
            id_item_end_id = None
            for edge_index in range(self.sequence_num_rows):  
                id_item = self.sequence_table.item(edge_index, 2)
                if variable.start_ID == self.experiment.sequence[edge_index].id:
                    row_start_id = edge_index
                    id_item_start_id = id_item
                if variable.end_ID == self.experiment.sequence[edge_index].id:
                    row_end_id = edge_index
                    id_item_end_id = id_item
            try:
                if variable.start_ID == self.experiment.sequence[row_start_id].id and row_start_id == row_end_id-1:
                    try:
                        id_item_start_id.setBackground(self.right_green)
                        id_item_end_id.setBackground(self.right_green)
                    except ValueError:
                        pass
                elif variable.start_ID == self.experiment.sequence[row_start_id].id and row_start_id != row_end_id-1:
                    try:
                        id_item_start_id.setBackground(self.wrong_red)
                        id_item_end_id.setBackground(self.wrong_red)
                    except ValueError:
                        pass
                if variable.end_ID == self.experiment.sequence[row_end_id].id and row_end_id == row_start_id+1:
                    try:
                        id_item_start_id.setBackground(self.right_green)
                        id_item_end_id.setBackground(self.right_green)
                    except ValueError:
                        pass
                elif variable.end_ID == self.experiment.sequence[row_end_id].id and row_end_id != row_start_id+1:
                    try:
                        id_item_start_id.setBackground(self.wrong_red)
                        id_item_end_id.setBackground(self.wrong_red)
                    except ValueError:
                        pass
            except:
                pass 


    
    def startID_edge_next_to_endID_edge(self): 
        # check if all end ID edges right after start ID edges for all ramp variables
        startID_next_to_endID = True
        for variable in self.experiment.ramped_variables: # go through all variable and color the edges
            row_start_id = None
            row_end_id = None
            for edge_index in range(self.sequence_num_rows):  
                if variable.start_ID == self.experiment.sequence[edge_index].id:
                    row_start_id = edge_index
                if variable.end_ID == self.experiment.sequence[edge_index].id:
                    row_end_id = edge_index
            if row_end_id != row_start_id+1:
                startID_next_to_endID = False 
                break
        return startID_next_to_endID
    


    #SEQUENCE TAB RELATED FUNCTIONS

    def create_file_name_label(self):
        '''
        Function was created to make the code more readable 
        '''
        self.file_name_lable.setText(self.experiment.file_name)




    
    
    def set_color_of_the_edge(self, set_color, edge_num):
        '''
        Function is used to highlight or unhighlight the edge. For example, when the user wants the system to go_to_edge
        it will color it after successful execution. Or, when the user runs the sequence the highlighted edge should be unhighlighted
        '''
        self.to_update = False # this is done in order to avoid sequence table changed event
        self.sequence_table.item(edge_num,0).setBackground(set_color)
        self.sequence_table.item(edge_num,1).setBackground(set_color)
        self.sequence_table.item(edge_num,2).setBackground(set_color)
        self.sequence_table.item(edge_num,3).setBackground(set_color)
        self.sequence_table.item(edge_num,4).setBackground(set_color)
        self.digital_dummy.item(edge_num,0).setBackground(set_color)
        self.digital_dummy.item(edge_num,1).setBackground(set_color)
        self.digital_dummy.item(edge_num,2).setBackground(set_color)
        self.analog_dummy.item(edge_num,0).setBackground(set_color)
        self.analog_dummy.item(edge_num,1).setBackground(set_color)
        self.analog_dummy.item(edge_num,2).setBackground(set_color)
        self.dds_seq.item(edge_num,0).setBackground(set_color)
        self.dds_seq.item(edge_num,1).setBackground(set_color)
        self.dds_seq.item(edge_num,2).setBackground(set_color)
        self.to_update = True        
    
    
    def count_scanned_variables(self):
        '''
        Function iterates over all scanned variables that are not "None" and assigns the total count to 
        self.experiment.scanned_variables_count. The function does not return anything
        '''
        count = 0
        for variable in self.experiment.scanned_variables:
            if variable.name != "None":
                count += 1
        self.experiment.scanned_variables_count = count

    
    def count_ramped_variables(self):
        '''
        analog to count_scanned_variables(self)
        '''
        countr = 0
        for variable in self.experiment.ramped_variables:
            if variable.name != "None":
                countr += 1
        self.experiment.ramped_variables_count = countr
    
    
    def stop_continuous_run(self):
        '''
        This function is used to trigger the event of button_yes for stop_continuous_run_button_clicked. When using it to accept the dialog and then
        having a flag of self.dialog.accepted in case the window was closed by clicking the close button at the 
        right top corner, the dialog was accepted by default.
        '''
        try:
            write_to_python.create_go_to_edge(self, edge_num=0, to_default=True)
            self.message_to_logger("init_hardware.py file generated")
            try:
                if config.package_manager == "conda":
                    submit_experiment_thread = threading.Thread(target=os.system, args=["conda activate "+ config.artiq_environment_name +" && artiq_run " + str(self.repo_path / "ARTIQ_scripts" / 'init_hardware.py')])
                elif config.package_manager == "clang64":
                    submit_experiment_thread = threading.Thread(target=lambda: subprocess.Popen(['cmd', '/c', str(self.repo_path / "experiment_specific_files" / "hybrid_experiment" / 'init_hardware.bat')],creationflags=subprocess.CREATE_NEW_CONSOLE))
                submit_experiment_thread.start()
                self.message_to_logger("Experiment was stopped. Hardware is set to the default values")
                #unhighlighting the previously highlighted edge
                if self.experiment.go_to_edge_num != -1:
                    self.set_color_of_the_edge(self.white, self.experiment.go_to_edge_num)
                try:
                    if self.experiment.do_ramp == True:
                        self.update_sequence_edge_colors()
                except:
                    pass
                #Highlighting the default edge and setting the go_to_edge_num to the default edge value (0)
                self.experiment.go_to_edge_num = 0
                self.set_color_of_the_edge(self.green, 0)
            except:
                self.message_to_logger("Could not stop the experiment.")
        except:
            self.message_to_logger("Could not generate init_hardware.py file")    
        self.dialog.accept()    
    
    def saving_default(self):
        '''
        This function is used to trigger the event of button_yes for save_default_button_clicked. When using it to accept the dialog and then
        having a flag of self.dialog.accepted in case the window was closed by clicking the close button at the 
        right top corner, the dialog was accepted by default.
        '''
        # Update camera state before saving
        if hasattr(self, "camera_box"):
            self.experiment.camera_enabled = self.camera_box.isChecked()
        if hasattr(self, "_texp_locked"):
            self.experiment.texp_locked = self._texp_locked
        
        success, message = file_io.save_default_settings(self.experiment, self.repo_path)
        self.message_to_logger(message)
        self.dialog.accept()



    
    def index_of_a_new_variable(self, name):
        '''
        Function is used to find the index of the user defined variable by the name. It takes the variable name and
        iterates over all user defined variables to find the match and return the index of that variable in case it
        is present and None otherwise.
        '''
        index = None
        for ind, variable in enumerate(self.experiment.new_variables):
            if variable.name == name:
                index = ind
                break
        return index






    def check_if_already_scanned(self, name):
        '''
        Function takes a variable name as an input and checks if it already exists in a scanned variables list.
        This is used to avoid providing two same scanned variable. Returns True in case of duplicates and False otherwise
        '''
        for variable in self.experiment.scanned_variables:
            if variable.name == name:
                return True
        return False





    def ramp_table_checked(self):
        '''
        analog to scan_table_checked
        '''
        if self.to_update:
            self.experiment.do_ramp = self.ramp_table.isChecked()
            if self.experiment.do_ramp == False:
                #User unchecked the ramp. Reassign the variables to the pre ramping values using self.experiment.new_variables
                for item in self.experiment.new_variables: 
                    self.experiment.variables[item.name].functionramp = item.value 
                    for row in range(self.sequence_num_rows): 
                        id_item = self.sequence_table.item(row, 2)
                        try:
                            id_item.setBackground(self.white) # update color of sequence edges, all white when ramp not checked
                        except ValueError:
                            pass 
                
            else:  #ramp is checked
                for variable in self.experiment.ramped_variables:
                    if variable.name != "None":
                        self.experiment.variables[variable.name].functionramp = variable.functionramp 
                    # update color of sequence edges, green when start_id is right before end_id, red when edge between start_id and end_id
                    self.update_sequence_edge_colors()
                    
            update.digital_analog_dds_mirny_tabs(self)
            update.variable_tables(self)




    def check_if_already_ramped(self, name):
        '''
        analog to check_if_already_scaned
        '''
        for variable in self.experiment.ramped_variables:
            if variable.name == name:
                return True
        return False





    #DIGITAL TAB RELATED FUNCTIONS
    def update_digital_table_header(self, index, name):
        '''
        Fucntion is used to update the digital table title name. It takes the index of the title and the name and updates it
        '''
        if name != "":
            self.experiment.title_digital_tab[index] = "D%d"%(index - 4) + "\n" + name
        else:
            self.experiment.title_digital_tab[index] = "D%d"%(index - 4)
        self.digital_table.setHorizontalHeaderLabels(self.experiment.title_digital_tab)
        self.dialog.accept()



    def digital_table_header_clicked(self, logicalIndex):
        '''
        Function is used when the user wants to change the digital table title name by clicking it.
        ligicalIndex is the internal item of the digital table header that reflects the index of the header clicked.
        '''
        index = logicalIndex
        if index > 3:
            #Pop up window to allow user to enter the name of the digital title
            self.dialog = QDialog()
            self.dialog.setGeometry(*self.scale_geom(710, 435, 400, 120))
            self.dialog.setFont(QFont('Arial', self.scale_font(14)))
            value_input = QLineEdit()
            dialog_layout = QVBoxLayout()
            button_update = QPushButton("update")
            button_cancel = QPushButton("cancel")
            dialog_layout.addWidget(value_input)
            dialog_buttons_layout = QHBoxLayout()
            dialog_buttons_layout.addWidget(button_update)
            dialog_buttons_layout.addWidget(button_cancel)
            dialog_layout.addLayout(dialog_buttons_layout)
            self.dialog.setLayout(dialog_layout)
            button_update.clicked.connect(lambda:self.update_digital_table_header(index, value_input.text()))
            button_cancel.clicked.connect(lambda:self.dialog.reject())
            self.dialog.setWindowTitle("Custom name for the channel") 
            self.dialog.exec_()
        else:
            pass





    #ANALOG TABLE RELATED
    def update_analog_table_header(self, index, name):
        '''
        Function is used to update the analog table title name. It takes the index of the title and the name and updates it
        '''
        if name != "":
            self.experiment.title_analog_tab[index] = "A%d"%(index - 4) + "\n" + name
        else:
            self.experiment.title_analog_tab[index] = "A%d"%(index - 4)
        self.analog_table.setHorizontalHeaderLabels(self.experiment.title_analog_tab)
        self.dialog.accept()





    def analog_table_header_clicked(self, logicalIndex):
        '''
        Function is used when the user wants to change the analog table title name by clicking it.
        ligicalIndex is the internal item of the analog table header that reflects the index of the header clicked.
        '''
        index = logicalIndex
        if index > 3:
            self.dialog = QDialog()
            self.dialog.setGeometry(*self.scale_geom(710, 435, 400, 120))
            self.dialog.setFont(QFont('Arial', self.scale_font(14)))
            value_input = QLineEdit()
            dialog_layout = QVBoxLayout()
            button_update = QPushButton("update")
            button_cancel = QPushButton("cancel")
            dialog_layout.addWidget(value_input)
            dialog_buttons_layout = QHBoxLayout()
            dialog_buttons_layout.addWidget(button_update)
            dialog_buttons_layout.addWidget(button_cancel)
            dialog_layout.addLayout(dialog_buttons_layout)
            self.dialog.setLayout(dialog_layout)
            button_update.clicked.connect(lambda:self.update_analog_table_header(index, value_input.text()))
            button_cancel.clicked.connect(lambda: self.dialog.reject())
            self.dialog.setWindowTitle("Custom name for the channel") 
            self.dialog.exec_()





    #DDS TAB RELATED FUNCTIONS
    def dds_table_header_clicked(self, row, column):
        '''
        Function is used when the user wants to change the dds table title name by clicking it.
        ligicalIndex is the internal item of the dds table header that reflects the index of the header clicked.
        '''

        if row == 0 and column % 6 != 0:
            
            index = column // 6

            #Pop up window to allow user to enter the name of the digital title
            self.dialog = QDialog()
            self.dialog.setGeometry(*self.scale_geom(710, 435, 400, 120))
            self.dialog.setFont(QFont('Arial', self.scale_font(14)))
            value_input = QLineEdit()
            dialog_layout = QVBoxLayout()
            button_update = QPushButton("update")
            button_cancel = QPushButton("cancel")
            dialog_layout.addWidget(value_input)
            dialog_buttons_layout = QHBoxLayout()
            dialog_buttons_layout.addWidget(button_update)
            dialog_buttons_layout.addWidget(button_cancel)
            dialog_layout.addLayout(dialog_buttons_layout)
            self.dialog.setLayout(dialog_layout)
            button_update.clicked.connect(lambda:self.update_dds_table_header(index, value_input.text()))
            button_cancel.clicked.connect(lambda:self.dialog.reject())
            self.dialog.setWindowTitle("Custom name for the channel") 
            self.dialog.exec_()
        else:
            pass

    
    def update_dds_table_header(self, index, name):
        """Rename a DDS channel header while keeping the default prefix numbering."""
        if name != "":
            self.experiment.title_dds_tab[index+4] = "DDS%d"%(index) + " " + name
        else:
            self.experiment.title_dds_tab[index+4] = "DDS%d"%(index)
        self.dds_table_header.item(0,6*index+1).setText(self.experiment.title_dds_tab[index+4])
        self.dialog.accept()



    def find_unique_id_unused(self):
        '''
        Function iterates over the id numbers from id0, id1, etc. until it finds the smallest available id number and returns it
        '''
        for id in range(10**4):
            unique_id = "id" + str(id)
            if unique_id not in self.experiment.variables:
                return unique_id

    def find_new_variable_name_unused(self):
        '''
        Function itereates over the variable names of form var_1, var_2, etc. and returns the lowest available variable name
        '''
        for i in range(1, 1000):
            name = "var_" + str(i)
            if name not in self.experiment.variables:
                return name

    def find_derived_variable_name_unused(self):
        '''
        Function itereates over the variable names of form derived_1, derived_2, etc. and returns the lowest available variable name
        '''
        for i in range(1, 1000):
            name = "derived_" + str(i)
            if name not in self.experiment.names_of_derived_variables:
                return name
            
    def find_lookup_variable_name_unused(self):
        '''
        Function itereates over the variable names of form derived_1, derived_2, etc. and returns the lowest available variable name
        '''
        for i in range(1, 1000):
            name = "lookup_" + str(i)
            if name not in self.experiment.names_of_lookup_variables:
                return name
            
    def find_edge_index_by_id(self, id):
        '''
        Function is used to find the index of the edge by its id value. It iterates over all edges and returns the 
        index when the id matches the edge.id
        '''
        for index, edge in enumerate(self.experiment.sequence):
            if edge.id == id:
                return index
    



    #SAMPLER TAB RELATED FUNCTIONS
    def update_sampler_table_header(self, index, name):
        '''
        Function is used to update the sampler table title name. It takes the index of the title and the name and updates it
        '''
        if name != "":
            self.experiment.title_sampler_tab[index] = "S%d"%(index - 4) + "\n" + name
        else:
            self.experiment.title_sampler_tab[index] = "S%d"%(index - 4)        
        self.sampler_table.setHorizontalHeaderLabels(self.experiment.title_sampler_tab)
        self.dialog.accept()





    def sampler_table_header_clicked(self, logicalIndex):
        '''
        Function is used when the user wants to change the sampler table title name by clicking it.
        ligicalIndex is the internal item of the sampler table header that reflects the index of the header clicked.
        '''
        index = logicalIndex
        if index > 3:
            #Pop up window to allow user to enter the name of the sampler title
            self.dialog = QDialog()
            self.dialog.setGeometry(*self.scale_geom(710, 435, 400, 120))
            self.dialog.setFont(QFont('Arial', self.scale_font(14)))
            value_input = QLineEdit()
            dialog_layout = QVBoxLayout()
            button_update = QPushButton("update")
            button_cancel = QPushButton("cancel")
            dialog_layout.addWidget(value_input)
            dialog_buttons_layout = QHBoxLayout()
            dialog_buttons_layout.addWidget(button_update)
            dialog_buttons_layout.addWidget(button_cancel)
            dialog_layout.addLayout(dialog_buttons_layout)
            self.dialog.setLayout(dialog_layout)
            button_update.clicked.connect(lambda:self.update_sampler_table_header(index, value_input.text()))
            button_cancel.clicked.connect(lambda:self.dialog.reject())
            self.dialog.setWindowTitle("Custom name for the channel") 
            self.dialog.exec_()
        else:
            pass


    def to_dict(self,obj):
        """Recursively convert an object and its attributes to a dictionary."""
        if isinstance(obj, (int, float, str, bool, type(None))):
            return obj
        if isinstance(obj, (list, tuple, set)):
            return [self.to_dict(i) for i in obj]
        if isinstance(obj, dict):
            return {k: self.to_dict(v) for k, v in obj.items()}

        # for class instances
        result = {}
        for attr, value in obj.__dict__.items():

            condition = str(attr)[:2] != 'is' \
                and str(attr) != 'changed' \
                and str(attr) != 'for_python' \
                and str(attr) != 'evaluation'
            if condition:
                result[attr] = self.to_dict(value)
        return result

    def update_experiment_names_list(self,name = '',caption = '',last = True):
        
        with open(self.repo_path / "experiment_specific_files" / config.which_project / "experiment_names.json", 'r', encoding="utf-8") as f:
            data = json.load(f)

        if last == True:
            if data:
                try:
                    next_index = max(int(key) for key in data.keys()) + 1
                except ValueError:
                    next_index = len(data)
            else:
                next_index = 0

            data[str(next_index)] = {}
            data[str(next_index)]["name"] = name
            data[str(next_index)]["plot_x_caption"] = caption

            self.experiment_list_list_widget.addItem(name)
            self.dialog.accept()
        else:
            row = self.experiment_list_list_widget.currentRow()
            if row < 0:
                return
            key = f"{int(row)}"
            if key not in data:
                self.message_to_logger(f"Experiment entry with key {key} was not found in experiment_names.json")
                return
            data[key]["plot_x_caption"] = caption
            self.experiment.experimental_data.comment = caption

        data = self._normalize_experiment_name_keys(data)

        with open(self.repo_path / "experiment_specific_files" / config.which_project / "experiment_names.json", 'w', encoding="utf-8") as f:
            json.dump(data,f,indent = 4)
        # update.acquisition_tab(self)

    def _ensure_camera_experiment_selected(self):
        """Return True when a camera experiment is chosen, otherwise warn the user."""
        if not hasattr(self, "camera_box") or not self.camera_box.isChecked():
            return True

        experiment_selected = False
        if hasattr(self, "experiment_list_list_widget"):
            experiment_selected = self.experiment_list_list_widget.currentRow() >= 0
        if not experiment_selected:
            experiment_name = getattr(self.experiment.experimental_data, "experiment_name", "")
            experiment_selected = bool(str(experiment_name).strip())
        if not experiment_selected and hasattr(self, "experiment_list_chosen_line"):
            experiment_selected = bool(self.experiment_list_chosen_line.text().strip())

        if experiment_selected:
            return True

        self.error_message("Experiment is not chosen. Choose an experiment.", "Camera acquisition")
        return False

    def _get_live_camera_parameters(self):
        """Validate and return camera settings used by the live-view window."""
        camera_name = (self.which_cam_combo.currentText() or "").strip()
        if not camera_name:
            raise ValueError("Select a camera before starting live view.")

        serial_number = config.camera_serial_numbers_dict.get(camera_name)
        if serial_number is None:
            raise ValueError(f"Camera '{camera_name}' is not configured in config.camera_serial_numbers_dict.")

        gain_text = (self.gain_edit.text() or "").strip()
        if gain_text == "":
            raise ValueError("Specify camera gain before starting live view.")
        try:
            gain_value = float(gain_text)
        except ValueError as exc:
            raise ValueError("Camera gain must be a numeric value.") from exc

        exposure_text = (self.exposure_edit.text() or "").strip()
        if exposure_text == "":
            raise ValueError("Specify camera exposure time before starting live view.")
        try:
            exposure_value = float(exposure_text)
        except ValueError as exc:
            raise ValueError("Camera exposure time must be a numeric value.") from exc

        format_name = (self.format_combo.currentText() or "").strip()
        if not format_name:
            raise ValueError("Select an image format before starting live view.")

        self.experiment.experimental_data.camera.camera_name = camera_name
        self.experiment.experimental_data.camera.serial_number = serial_number
        self.experiment.experimental_data.camera.gain_db = gain_value
        self.experiment.experimental_data.camera.exposure_time_ms = exposure_value
        self.experiment.experimental_data.camera.format_name = format_name

        return camera_name, format_name, gain_value, exposure_value

    def _open_live_camera_window(self):
        """Create and show the live camera window if it is not already open."""
        if self.live_camera_window is not None:
            self.live_camera_window.show()
            self.live_camera_window.raise_()
            self.live_camera_window.activateWindow()
            return

        camera_name, format_name, gain_value, exposure_value = self._get_live_camera_parameters()

        try:
            live_module = importlib.import_module("camera_live_display")
            LiveCameraWindow = getattr(live_module, "LiveCameraWindow")
        except Exception as exc:
            if not self._live_camera_import_error_shown:
                self._live_camera_import_error_shown = True
                self.error_message(
                    f"Could not import live camera module: {exc}",
                    "Live camera",
                )
            raise

        self.live_camera_window = LiveCameraWindow(
            camera_name=camera_name,
            pixel_format=format_name,
            gain_db=gain_value,
            exposure_ms=exposure_value,
        )
        self.live_camera_window.destroyed.connect(lambda *_: setattr(self, "live_camera_window", None))
        self.live_camera_window.show()

        if hasattr(self, "live_subtract_checkbox") and self.live_subtract_checkbox.isChecked():
            self.live_camera_window.set_subtraction_enabled(True)
            self.live_camera_window.arm_next_subtraction_reference()

        self.message_to_logger("Live camera window opened")

    def _close_live_camera_window(self):
        """Close and release the live camera window if it exists."""
        if self.live_camera_window is None:
            return
        try:
            self.live_camera_window.close()
        finally:
            self.live_camera_window = None
        self.message_to_logger("Live camera window closed")

    def handle_live_camera_toggled(self, checked):
        """Open or close the live camera window when the UI checkbox changes."""
        if hasattr(self, "live_subtract_checkbox"):
            self.live_subtract_checkbox.setEnabled(bool(checked))
        if hasattr(self, "live_subtract_reset_button"):
            can_reset = bool(checked) and bool(getattr(self, "live_subtract_checkbox", None) and self.live_subtract_checkbox.isChecked())
            self.live_subtract_reset_button.setEnabled(can_reset)

        if checked:
            try:
                self._open_live_camera_window()
            except Exception as exc:
                self.error_message(str(exc), "Live camera")
                if hasattr(self, "live_camera_checkbox"):
                    self.live_camera_checkbox.blockSignals(True)
                    self.live_camera_checkbox.setChecked(False)
                    self.live_camera_checkbox.blockSignals(False)
                if hasattr(self, "live_subtract_checkbox"):
                    self.live_subtract_checkbox.setEnabled(False)
                if hasattr(self, "live_subtract_reset_button"):
                    self.live_subtract_reset_button.setEnabled(False)
        else:
            self._close_live_camera_window()

    def handle_live_subtraction_toggled(self, enabled):
        """Enable/disable live subtraction and capture the next frame as reference when enabled."""
        if hasattr(self, "live_subtract_reset_button"):
            self.live_subtract_reset_button.setEnabled(bool(enabled) and bool(getattr(self, "live_camera_checkbox", None) and self.live_camera_checkbox.isChecked()))

        if self.live_camera_window is None:
            return

        self.live_camera_window.set_subtraction_enabled(bool(enabled))
        if enabled:
            self.live_camera_window.arm_next_subtraction_reference()
            self.message_to_logger("Live subtraction enabled; waiting for next acquired frame as reference")
        else:
            self.message_to_logger("Live subtraction disabled")

    def handle_live_subtraction_reset_clicked(self):
        """Reset subtraction by capturing a new reference from the next acquired frame."""
        if not hasattr(self, "live_camera_checkbox") or not self.live_camera_checkbox.isChecked() or self.live_camera_window is None:
            self.error_message("Enable Live camera first.", "Live subtraction")
            return

        if hasattr(self, "live_subtract_checkbox") and not self.live_subtract_checkbox.isChecked():
            self.live_subtract_checkbox.setChecked(True)
        else:
            self.live_camera_window.set_subtraction_enabled(True)

        self.live_camera_window.reset_subtraction_reference()
        self.message_to_logger("Live subtraction reset; next acquired frame will be used as reference")


    def _prepare_camera_launch(self):
        """Validate camera settings and build the launch metadata dictionary."""
        if not hasattr(self, "camera_box") or not self.camera_box.isChecked():
            return None

        camera_python_raw = getattr(config, "camera_env_python", "")
        camera_python_raw = camera_python_raw.strip() if isinstance(camera_python_raw, str) else ""
        if not camera_python_raw:
            raise ValueError("Camera Python interpreter path is not configured (config.camera_env_python).")

        camera_python = Path(camera_python_raw)
        if not camera_python.exists():
            raise ValueError(f"Camera Python interpreter was not found at {camera_python}")

        camera_script = self.repo_path / "main" / "camera.py"
        if not camera_script.exists():
            raise ValueError(f"Camera control script not found at {camera_script}")

        camera_name = (self.which_cam_combo.currentText() or "").strip()
        if not camera_name:
            raise ValueError("Select a camera before starting acquisition.")

        serial_number = config.camera_serial_numbers_dict.get(camera_name)
        if serial_number is None:
            raise ValueError(f"Camera '{camera_name}' is not configured in config.camera_serial_numbers_dict.")

        gain_text = (self.gain_edit.text() or "").strip()
        if gain_text == "":
            raise ValueError("Specify camera gain before starting acquisition.")
        try:
            gain_value = float(gain_text)
        except ValueError as exc:
            raise ValueError("Camera gain must be a numeric value.") from exc

        exposure_text = (self.exposure_edit.text() or "").strip()
        if exposure_text == "":
            raise ValueError("Specify camera exposure time before starting acquisition.")
        try:
            exposure_value = float(exposure_text)
        except ValueError as exc:
            raise ValueError("Camera exposure time must be a numeric value.") from exc

        format_name = (self.format_combo.currentText() or "").strip()
        if not format_name:
            raise ValueError("Select an image format before starting acquisition.")

        experiment_row = self.experiment_list_list_widget.currentRow()
        experiment_code = experiment_row if experiment_row >= 0 else 0

        info_text = (self.experiment.experimental_data.comment or "").strip()
        base_path = (self.experiment.experimental_data.path or "").strip()
        experiment_name = (self.experiment.experimental_data.experiment_name or self.experiment_list_chosen_line.text() or "").strip()
        if not base_path:
            data_root = getattr(config, "experiment_data_root", "")
            if data_root:
                if experiment_name:
                    base_path = str(Path(data_root) / experiment_name)
                else:
                    base_path = data_root
        timestamp = datetime.now()
        date_part = timestamp.strftime("%Y_%m_%d")
        time_part = timestamp.strftime("%H_%M_%S")
        if base_path:
            run_base_dir = Path(base_path) / date_part / time_part
        else:
            run_base_dir = Path(self.repo_path / "logs" / "camera_runs" / date_part / time_part)
        run_directory = run_base_dir / camera_name

        if base_path:
            self.experiment.experimental_data.path = base_path
        self.experiment.experimental_data.current_run_path = str(run_directory)
        self.experiment.experimental_data.current_run_metadata_path = str(run_base_dir)
        self.experiment.experimental_data.current_run_timestamp = timestamp.isoformat()
        self.experiment.experimental_data.camera.camera_name = camera_name
        self.experiment.experimental_data.camera.serial_number = serial_number
        self.experiment.experimental_data.camera.gain_db = gain_value
        self.experiment.experimental_data.camera.exposure_time_ms = exposure_value
        self.experiment.experimental_data.camera.format_name = format_name
        self.experiment.experimental_data.experiment_id = experiment_code
        if not self.experiment.experimental_data.experiment_name:
            self.experiment.experimental_data.experiment_name = experiment_name

        argv = [
            str(camera_python),
            str(camera_script),
            "--camera", camera_name,
            "--format", format_name,
            "--gain-db", f"{gain_value}",
            "--exposure-ms", f"{exposure_value}",
            "--experiment-code", str(experiment_code),
            "--repo-root", str(self.repo_path),
        ]

        parents = run_directory.parents
        if len(parents) >= 3:
            output_root = parents[2]
        elif parents:
            output_root = parents[-1]
        else:
            output_root = run_directory
        argv.extend(["--output-root", str(output_root)])
        argv.extend(["--target-dir", str(run_directory)])
        if info_text:
            argv.extend(["--info-text", info_text])
        if getattr(self.experiment, "skip_images", False) and getattr(config, "allow_skipping_images", False):
            skip_count = getattr(config, "skip_images_trigger_count", 10)
            if skip_count > 0:
                argv.extend(["--drop-initial-count", str(int(skip_count))])

        # Optional: stage image saving to a local directory for speed, then copy to the final target dir at the end.
        if getattr(config, "camera_stage_locally", False):
            argv.append("--stage-local")
            stage_dir = getattr(config, "camera_stage_dir", "")
            if isinstance(stage_dir, str) and stage_dir.strip():
                argv.extend(["--stage-dir", stage_dir.strip()])

        return {
            "argv": argv,
            "cwd": str(camera_script.parent),
            "output_dir": str(run_directory),
            "metadata_dir": str(run_base_dir),
            "timestamp": timestamp.isoformat()
        }


    def _start_camera_subprocess(self, launch_info):
        """Spawn the camera helper process in a background thread."""
        if not launch_info:
            return None

        argv = launch_info.get("argv", [])
        cwd = launch_info.get("cwd")
        creationflags = getattr(subprocess, "CREATE_NEW_CONSOLE", 0)

        def runner():
            kwargs = {}
            if cwd:
                kwargs["cwd"] = cwd
            if creationflags:
                kwargs["creationflags"] = creationflags
            try:
                subprocess.Popen(argv, **kwargs)
            except Exception as exc:
                # Avoid GUI calls from worker threads; log via stdout for troubleshooting.
                print(f"Failed to start camera acquisition: {exc}")

        thread = threading.Thread(target=runner)
        thread.start()
        return thread


    def _start_artiq_thread(self, delay_s=0.0, run_continuous=False):
        """Start the ARTIQ runner in a detached thread for the configured platform."""
        delay_seconds = float(delay_s) if delay_s else 0.0

        if config.package_manager == "conda":
            command = "conda activate "+ config.artiq_environment_name +" && artiq_run " + str(self.repo_path / "ARTIQ_scripts" / 'run_experiment.py')

            def runner():
                if delay_seconds > 0:
                    time.sleep(delay_seconds)
                os.system(command)

        elif config.package_manager == "clang64":
            bat_name = 'cont_run.bat' if run_continuous else 'run_experiment.bat'
            bat_path = self.repo_path / "experiment_specific_files" / config.which_project / bat_name
            if not bat_path.exists():
                raise FileNotFoundError(f"Required batch file not found: {bat_path}")
            creationflags = getattr(subprocess, "CREATE_NEW_CONSOLE", 0)

            def runner():
                if delay_seconds > 0:
                    time.sleep(delay_seconds)
                kwargs = {}
                if creationflags:
                    kwargs["creationflags"] = creationflags
                subprocess.Popen(['cmd', '/c', str(bat_path)], **kwargs)

        else:
            raise RuntimeError(f"Unsupported package manager: {config.package_manager}")

        thread = threading.Thread(target=runner)
        thread.start()
        return thread


    def _record_experiment_run(self, metadata_dir, *, is_multiple_run=False):
        """Append the latest run metadata to the experiment spreadsheet when possible."""
        cache_dict = {"_pending_log_entries_cache": getattr(self, "_pending_log_entries_cache", None)}
        openpyxl_warned = getattr(self, "_openpyxl_missing_warned", False)
        
        success, message, openpyxl_warned = file_io.record_experiment_run(
            self.experiment, 
            self.repo_path, 
            metadata_dir,
            is_multiple_run=is_multiple_run,
            cache_dict=cache_dict,
            openpyxl_missing_warned=openpyxl_warned
        )
        
        self._openpyxl_missing_warned = openpyxl_warned
        if "_pending_log_entries_cache" in cache_dict:
            self._pending_log_entries_cache = cache_dict["_pending_log_entries_cache"]
        
        if message:
            self.message_to_logger(message)


    def _remove_experiment_log_rows(self, experiment_name):
        """Remove rows in the experiment log workbook that match the given experiment name."""
        success, message = file_io.remove_experiment_log_rows(experiment_name, self.repo_path)
        if message:
            self.message_to_logger(message)


    def _normalize_experiment_name_keys(self, mapping):
        """Return a copy of the experiment metadata with sequential string keys."""
        if not isinstance(mapping, dict):
            return {}

        try:
            sorted_items = sorted(mapping.items(), key=lambda item: int(item[0]))
        except (ValueError, TypeError):
            sorted_items = list(mapping.items())

        normalized = {}
        for idx, (_, value) in enumerate(sorted_items):
            normalized[str(idx)] = value
        return normalized


    def _load_pending_log_entries(self):
        """Retrieve any deferred experiment log entries from disk into memory."""
        cache_dict = {"_pending_log_entries_cache": getattr(self, "_pending_log_entries_cache", None)} if hasattr(self, "_pending_log_entries_cache") else {}
        entries = file_io.load_pending_log_entries(self.repo_path, cache_dict)
        if "_pending_log_entries_cache" in cache_dict:
            self._pending_log_entries_cache = cache_dict["_pending_log_entries_cache"]
        return entries


    def _set_pending_log_entries(self, entries):
        """Persist the supplied pending log entries and refresh the cache."""
        cache_dict = {"_pending_log_entries_cache": getattr(self, "_pending_log_entries_cache", None)} if hasattr(self, "_pending_log_entries_cache") else {}
        error_msg = file_io.set_pending_log_entries(self.repo_path, entries, cache_dict)
        if "_pending_log_entries_cache" in cache_dict:
            self._pending_log_entries_cache = cache_dict["_pending_log_entries_cache"]
        if error_msg:
            self.message_to_logger(error_msg)


    def _get_texp_variable_index(self):
        """Return the index of T_exp_ in new_variables, or None if absent."""
        texp_key = "T_exp_"
        for idx, variable in enumerate(self.experiment.new_variables):
            if variable.name == texp_key:
                return idx
        return None

    def _set_camera_exposure_line(self, value):
        """Update the exposure QLineEdit without re-triggering handlers."""
        if hasattr(self, "exposure_edit"):
            self.exposure_edit.blockSignals(True)
            if value in (None, ""):
                self.exposure_edit.clear()
            else:
                self.exposure_edit.setText(str(value))
            self.exposure_edit.blockSignals(False)

    def _sync_camera_exposure_from_variable(self):
        """When T_exp_ changes elsewhere, reflect it in the camera UI and model."""
        texp_var = self.experiment.variables.get("T_exp_")
        if texp_var is not None:
            self.experiment.experimental_data.camera.exposure_time_ms = texp_var.value
            self._set_camera_exposure_line(texp_var.value)

    def handle_texp_lock_toggled(self, locked):
        """Handle lock checkbox toggles for the exposure control and variable tables."""
        self._texp_locked = bool(locked)
        if hasattr(self, "exposure_edit"):
            self.exposure_edit.setEnabled(not self._texp_locked)
        self._update_texp_lock_presentation()

    def _update_texp_lock_presentation(self):
        """Adjust T_exp_ row editability and styling across variable tables."""
        if getattr(self, "_updating_texp_lock", False):
            return
        row_index = self._get_texp_variable_index()
        if row_index is None:
            return

        self._updating_texp_lock = True
        previous_update_state = self.to_update
        self.to_update = False

        tables = [
            getattr(self, "variables_table_variables", None),
            getattr(self, "variables_table_sequence", None),
            getattr(self, "variables_table_acquisition", None),
            getattr(self, "variables_table_digital", None),
            getattr(self, "variables_table_analog", None),
            getattr(self, "variables_table_dds", None),
            getattr(self, "variables_table_mirny", None),
            getattr(self, "variables_table_slow_dds", None),
            getattr(self, "variables_table_sampler", None),
        ]

        try:
            for table in tables:
                if table is None or row_index >= table.rowCount():
                    continue
                max_col = min(2, table.columnCount())
                for col in range(max_col):
                    item = table.item(row_index, col)
                    if item is None:
                        continue
                    current_flags = item.flags()
                    if self._texp_locked:
                        if current_flags != Qt.NoItemFlags and current_flags != (Qt.ItemIsSelectable | Qt.ItemIsEnabled):
                            item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                        item.setBackground(self.texp_color)
                    else:
                        if current_flags != Qt.NoItemFlags:
                            item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled | Qt.ItemIsEditable)
                        item.setBackground(self.white)
        finally:
            self.to_update = previous_update_state
            self._updating_texp_lock = False

    def closeEvent(self, event):
        """Ensure auxiliary windows and worker threads are shut down with the main GUI."""
        try:
            self._close_live_camera_window()
        finally:
            super().closeEvent(event)

def run():
    '''
    Main function that starts the application and invokes the window
    '''
    app = QApplication(sys.argv)
    window = MainWindow()
    window.showMaximized()
    try:
        sys.exit(app.exec_())
        
    except:
        print("Exiting")





if __name__ == "__main__":
    run()
