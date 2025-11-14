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


# Subclass QMainWindow to customize your application's main window
class MainWindow(QMainWindow):
    '''
    Main window that includes everything that needs to be displayed to the user
    '''
    class Edge:
        '''
        An object that is used to describe the time edge of experimental sequence
        Attributes description:
            expression  :   Mathematical expression used to describe the time edge
            evaluation  :   Expression that can be executed in python to evaluate the time edge. 
                            In case there is a scanned variable in the expression its minimum value is assigned to
                            be able to sort the sequence. It is a user responsibility to make sure that the sequence
                            of time edges will never be changed during the scan
            value       :   Time value of the edge. In case there is no scanned variable it is just the value, otherwise
                            it is a value of the expression evaluated with the minimum value of the scanned variable
            name        :   Descriptive name of the time edge to help user understand the purpose of the edge
            id          :   Unique id in the form of id0, id1, etc. It is used to let the user know what default variable
                            can be used to quickly use the value of this time edge. For example, one can offset the 
                            next time edge with respect to the previous one using "id1 + 5"
            is_scanned  :   Flag indicating if the time edge requires scanning. Even if there is a single scanned variable
                            in the edge expression, the edge becomes scanned as it is supposed to be changing at different
                            scan steps
            for_python  :   The version of the time edge description that is used in the python like experimental sequence
                            generation. It is only used in write_to_python.py and only updated when the run_experiment_button_clicked
            analog      :   List of Analog objects used to describe the state of the analog channel
            digital     :   List of Digital objects used to describe the state of the digital channel
            dds         :   List of DDS objects used to describe the state of the dds channel
            mirny       :   List of DDS objects used to describe the state of the mirny channel
            sampler     :   List of sampler channel parameters. 0 indicates that there is no requested input read. Other than 0 it can be a
                            variable name that will be used for storing the value of the input
            derived_variable_requested      :   Index of the derived variable for non zero values. -1 corresponds to no derived variables requested
                                                
        '''
        def __init__(self, name = "", id = "id0",
                     expression = "0", evaluation = 0,
                     for_python = 0, value = 0,
                     is_scanned = False, is_ramped = False,
                     derived_variable_requested = -1):
            self.expression = expression
            self.evaluation = evaluation
            self.value = value   
            self.name = name
            self.id = id
            self.is_scanned = is_scanned
            self.is_ramped = is_ramped 
            self.for_python = for_python
            self.digital = [self.Digital() for i in range(config.digital_channels_number)]
            self.analog = [self.Analog() for i in range(config.analog_channels_number)]
            self.dds = [self.DDS() for i in range(config.dds_channels_number)]
            self.mirny = [self.DDS(is_mirny = True) for i in range(config.mirny_channels_number)]
            self.sampler = ['0']*8
            self.derived_variable_requested = derived_variable_requested


        class Digital:
            '''
            An object that is used to describe the state of the digital channel
            Attributes description:
                expression  :   Mathematical expression used to describe the state of digital channel
                evaluation  :   Expression that can be executed in python to evaluate the state of digital channel
                value       :   The value of the digital channel
                for_python  :   The version of the digital channel state description that is used in the python like experimental sequence
                                generation. It is only used in write_to_python.py and only updated when the run_experiment_button_clicked
                changed     :   Flag indicating if the digital channel is required to be changed at this time edge
                is_scanned  :   Flag indicating if the digital channel state requires scanning. Even if there is a single scanned variable
                                in the expression, the channel becomes scanned as it is supposed to be changing at different
                                scan steps
                is_ramped  :   Flag indicating if the digital channel is ramped
                is_sampled  :   Flag indicating if the digital channel is sampled
                is_derived  :   Flag indicating if the digital channel is dervied
                is_lookup   :   Flag indicating if the digital channel is lookup                                
            '''
            def __init__(self, expression = "0.0", evaluation = 0.0,
                         value = 0.0, for_python = 0.0, changed = True,
                         is_scanned = False, is_ramped = False,
                         is_sampled = False, is_derived = False,
                         is_lookup = False):
                self.expression = expression
                self.evaluation = evaluation
                self.value = value
                self.for_python = for_python
                self.changed = changed
                self.is_scanned = is_scanned
                self.is_ramped = is_ramped
                self.is_sampled = is_sampled
                self.is_derived = is_derived
                self.is_lookup = is_lookup


        class Analog:
            '''
            An object that is used to describe the state of the analog channel
            Attributes description:
                expression  :   Mathematical expression used to describe the state of analog channel
                evaluation  :   Expression that can be executed in python to evaluate the state of analog channel
                value       :   The value of the analog channel
                for_python  :   The version of the analog channel value description that is used in the python like experimental sequence
                                generation. It is only used in write_to_python.py and only updated when the run_experiment_button_clicked
                changed     :   Flag indicating if the analog channel is required to be changed at this time edge
                is_scanned  :   Flag indicating if the analog channel state requires scanning. Even if there is a single scanned variable
                                in the expression, the channel becomes scanned as it is supposed to be changing at different
                                scan steps
                is_ramped  :   Flag indicating if the digital channel is ramped
                is_sampled  :   Flag indicating if the analgo channel is sampled
                is_derived  :   Flag indicating if the analog channel is dervied
                is_lookup   :   Flag indicating if the analog channel is lookup
            '''            
            def __init__(self, expression = "0.0", evaluation = 0.0,
                         value = 0.0, for_python = "0.0",
                         changed = True, is_scanned = False,
                         is_ramped = False, is_sampled = False,
                         is_derived = False, is_lookup = False):
                self.expression = expression
                self.evaluation = evaluation
                self.value = value
                self.for_python = for_python
                self.changed = changed
                self.is_scanned = is_scanned
                self.is_ramped = is_ramped
                self.is_sampled = is_sampled
                self.is_derived = is_derived
                self.is_lookup = is_lookup


        class DDS:
            '''
            An object that is used to describe the state of the dds channel
            Attributes description:
                frequency    :   An object that is used to describe the frequency state of the dds channel
                amplitude    :   An object that is used to describe the amplitude state of the dds channel
                attenuation  :   An object that is used to describe the attenuation state of the dds channel
                phase        :   An object that is used to describe the phase state of the dds channel
                state        :   An object that is used to describe the ON/OFF state of the dds channel
                changed      :   Flag indicating if the dds channel is required to be changed at this time edge
            '''
            def __init__(self, state = 0, changed = True, is_mirny = False):
                self.is_mirny = is_mirny
                if self.is_mirny == True:
                    self.frequency = self.Object(expression = "55.0", evaluation = 55.0, value = 55.0)
                    self.amplitude = self.Object(expression = "5.0", evaluation = 5.0, value = 5.0)
                else:
                    self.frequency = self.Object()
                    self.amplitude = self.Object()
                self.phase = self.Object()
                self.attenuation = self.Object()
                self.state = self.Object()
                self.changed = changed

        
            class Object:
                '''
                An object that is used to describe the state of the dds channel parameters
                Attributes description:
                    expression  :   Mathematical expression used to describe the dds channel parameter
                    evaluation  :   Expression that can be executed in python to evaluate the dds channel parameter
                    value       :   The value of the dds channel parameter
                    for_python  :   The version of the dds parameter description that is used in the python like experimental sequence
                                    generation. It is only used in write_to_python.py and only updated when the run_experiment_button_clicked
                    changed     :   Flag indicating if the dds channel parameter is required to be changed at this time edge. If any of the
                                    dds parameters is required to be changed the state is going to be updated at this time edge
                    is_scanned  :   Flag indicating if the dds channel parameter requires scanning. Even if there is a single scanned variable
                                    in the expression, the channel parameter becomes scanned as it is supposed to be changing at different
                                    scan steps
                    is_ramped  :   Flag indicating if the digital channel is ramped
                    is_sampled  :   Flag indicating if the parameter is sampled
                    is_derived  :   Flag indicating if the parameter is dervied
                    is_lookup   :   Flag indicating if the parameter is lookup                                    
                '''
                def __init__(self, expression = "0.0", evaluation = 0.0, value = 0.0, changed = True, is_scanned = False, is_ramped = False, is_sampled = False, is_derived = False, is_lookup = False):
                    self.expression = expression
                    self.evaluation = evaluation
                    self.for_python = evaluation
                    self.value = value
                    self.changed = changed   
                    self.is_scanned = is_scanned 
                    self.is_ramped = is_ramped
                    self.is_sampled = is_sampled     
                    self.is_derived = is_derived
                    self.is_lookup = is_lookup

    class Experiment:
        '''
        An object that is used to describe the entire experimental sequence, title names and state of the GUI
        Attributes description:
            title_digital_tab           :   List of the String type title names used in digital tab
            title_analog_tab            :   List of the String type title names used in analog tab
            title_dds_tab               :   List of the String type title names used in dds tab
            title_sampler_tab           :   List of the String type title names used in sampler tab
            sequence                    :   List of Edge objects describing the experimental sequence at different time stamps
            go_to_edge_num              :   Number of the edge specified to go when pressing go_to_edge button. Initialized at -1
                                            for easy check in case none of the edges has been selected yet
            new_variables               :   List of user defined variables. Used to build the variables tab and retieve the values 
                                            assigned before scanning a variable
            derived_variables           :   List of Derived_variables. Used to be able to use sampled variables in more complex functions 
                                            to allow feedback
            names_of_derived_variables  :   Set of the derived variables names. Useful to check if a variable is a derived variable
            variables                   :   Dictionary of all variables. Used to look up the values of the variables in the execution of
                                            evaluation
            sampler_variables           :   Set of variable names used for being used in a samlper
            do_scan                     :   Flag indicating if the scan is needed to be done
            number_of_steps             :   Number of steps specificed in the Scan table parameters. Default value is 1
            file_name                   :   The name of the experimental sequence. When the program is initialized the name is an empty String.
                                            Once the save_sequence button is clicked the user needs to specify the location and name of the file.
                                            Used to display the name of the sequence to let user know the purpose of the sequence.
            scanned_variables           :   List of scanned variables. Used in the write_to_python.py to generate the proper iterables for the scan
            scanned_varbiales_count     :   Number of scanned variables. Used to ignore the scan tick in case of 0 specified scanned variables.
                                            User can create several scanning variables with None as names
            continuously_running        :   Flag indicating if the continuous run is required
            slow_dds                    :   List of SLOW_DDS objects that describe the state of the slow dds output
            lookup_variables            :   List of Lookup_variables. Used to be able to use sampled variables to output a complex function using lookup list
            names_of_lookup_variables   :   Set of the lookup variables names. Useful to check if a variable is a lookup variable
        '''  
        def __init__(self):
            self.title_digital_tab = []
            self.title_analog_tab = []
            self.title_dds_tab = []
            self.title_mirny_tab = []
            self.title_sampler_tab = []
            self.title_slow_dds_tab = []
            self.sequence = [] 
            self.go_to_edge_num = -1
            self.new_variables = [] 
            self.variables = {}
            self.sampler_variables = set()
            self.derived_variables = []
            self.names_of_derived_variables = set()
            self.do_scan = False
            self.do_ramp = False
            self.number_of_steps = 1
            self.number_of_runs = 10
            self.cam_trigger_off_runs = 5
            self.file_name = ""
            self.scanned_variables = [] 
            self.scanned_variables_count = 0
            self.ramped_variables = []
            self.ramped_variables_count = 0
            self.run_continuous = False
            self.multiple_runs = False
            self.lookup_variables = []
            self.names_of_lookup_variables = set()
            self.camera_enabled = False
            self.texp_locked = False
            
    class SLOW_DDS:
        '''
        An object that is used to describe the state of the slow dds channel
        Attributes description:
            frequency    :   An object that is used to describe the frequency state of the dds channel
            amplitude    :   An object that is used to describe the amplitude state of the dds channel
            attenuation  :   An object that is used to describe the attenuation state of the dds channel
            phase        :   An object that is used to describe the phase state of the dds channel
            state        :   An object that is used to describe the ON/OFF state of the dds channel
        '''
        def __init__(self, frequency = 0.0, amplitude = 0.0, attenuation = 0.0, phase = 0.0, state = 0):
            self.frequency = frequency
            self.amplitude = amplitude
            self.attenuation = attenuation
            self.phase = phase
            self.state = state

    class ExperimentalData:
        '''
        An object that is used to describe the data acquired during experiment
        Attributes description:
            path            :   An object that is used to describe the path of the data
            device          :   An object that is used to describe the kind of device used for acquisition
            experiment_name :   An object that is used to describe the kind of experiment
            comment         :   An object that is used to describe the comment on the experiment
            experiment_id   :   An object that is used to describe the unique id of the experiment
        '''

        def __init__(self,path = '', experiment_name = '', comment = '', experiment_id = ''):
            self.path = path
            self.experiment_name = experiment_name
            self.comment = comment
            self.experiment_id = experiment_id

    class Derived_variable:
        '''
        An object that is used to describe the derived variable parameters
        Attributes description:
            name        :   Name of the scanned variable
            arguments   :   List of agruments for the function used to derive the variable
            function    :   String of the python description of the function to derive the variable
        ''' 
        def __init__(self, name, arguments, edge_id, function, initial_value):
            self.name = name
            self.arguments = arguments
            self.edge_id = edge_id
            self.function = function
            self.initial_value = initial_value 
            
    class Lookup_variable:
        '''
        An object that is used to describe the lookup variable parameters
        Attributes description:
            name                :   Name of the scanned variable
            argument            :   Argument that is a sampled variable to be used to lookup the value
            lookup_list         :   List of lookup table
            lookup_list_name    :   Name of the lookup table
        ''' 
        def __init__(self, name, argument = "", lookup_list = [], lookup_list_name = ""):
            self.name = name
            self.argument = argument
            self.lookup_list = lookup_list
            self.lookup_list_name = lookup_list_name

    class Scanned_variable:
        '''
        An object that is used to describe the scanned variable parameters
        Attributes description:
            name        :   Name of the scanned variable
            min_val     :   Minimum value assigned to the scanned variable
            max_val     :   Maximum value assigned to the scanned variable
        ''' 
        def __init__(self, name, min_val, max_val):
            self.name = name
            self.min_val = min_val
            self.max_val = max_val

    class Ramped_variable: 
        '''
        An object that is used to describe the ramped variable parameters
        Attributes description:
            name        :   Name of the ramped variable
            Start ID     :   from which ID the ramp up should start
            End ID     :   where the ramp up will end
            Functionramp  :  function by which ramped variable is changed
            Stepsramp :  steps for the for loop
        ''' 
        def __init__(self, name, start_ID, end_ID, functionramp, stepsramp):
            self.name = name
            self.start_ID = start_ID 
            self.end_ID = end_ID 
            self.functionramp = functionramp 
            self.stepsramp = stepsramp 

    class Variable: 
        '''
        An object that is used to describe all variables in self.experiment.variables decitionary
        Attributes description:
            name        :   Name of the variable
            value       :   Values of the variable. In case the variable is scanned its minimum values is assigned as its value
            is_scanned  :   Flag indicating if the variable is scanned
            for_python  :   The version of the variable description that is used in the python like experimental sequence
                            generation. It is only used in write_to_python.py and only updated when the run_experiment_button_clicked
            is_scanned  :   Flag indicatinf if the variable is a scanned variable                
            is_ramped  :   Flag indicating if the digital channel is ramped 
            is_sampled  :   Flag indicating if the variable is a sampled variable
            is_derived  :   Flag indicating if the variable is a derived variable
            is_lookup   :   Flag indicating if the variable is a lookup variable
            argument    :   Argument used for the lookup variables
        '''         
        def __init__(self, name, value, for_python, is_scanned = False, is_ramped = False, is_sampled = False, is_derived = False, is_lookup = False): 
            self.name = name
            self.value = value
            self.for_python = for_python
            self.is_scanned = is_scanned
            self.is_sampled = is_sampled
            self.is_ramped = is_ramped
            self.is_derived = is_derived
            self.is_lookup = is_lookup
            self.argument = ""
            
    class CustomThread(threading.Thread):
        '''
        An object that is used to initialize parallel threads
        '''    
        def __init__(self, group=None, target=None, name=None, args=(), kwargs=None, *, daemon=None):
            super().__init__(group, target, name, args, kwargs, daemon=daemon)        
            self._return = None

            
        def run(self):
            try:
                if self._target:
                    self._return = self._target(*self._args, **self._kwargs)
            finally:
                # Avoid a refcycle if the thread is running a function with
                # an argument that has a member that points to the thread.
                del self._target, self._args, self._kwargs                
            
    class Camera:
        '''
        
        '''
        def __init__(self,device_kind = 'camera', gain_db = 0, format_name = '', exposure_time = 350, serial_number = '', camera_name = ''):
            self.device_kind = device_kind
            self.gain_db = gain_db
            self.format_name = format_name
            self.exposure_time = exposure_time
            self.serial_number = serial_number
            self.camera_name = camera_name


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

        


        self.experiment = self.Experiment()
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
        self.white = QColor(255,255,255)
        self.yellow = QColor(255, 255, 0)
        self.cyan = QColor(0, 255, 255)
        self.purple = QColor(200, 150, 255)
        self.right_green = QColor(180, 255, 180)
        self.wrong_red = QColor(255, 0, 1)
        self._texp_locked = False
        self._updating_texp_lock = False
        self._openpyxl_missing_warned = False


        self.experiment.variables['id0'] = self.Variable(name = "id0", value = 0.0, for_python = 0.0)
        self.experiment.variables[''] = self.Variable(name = '', value = 0.0, for_python = 0.0)   #in order to be able to process expressions like -5 we need to have it as first item in decode will be "" that should be 0    
        if config.slow_dds_channels_number > 0:
            self.experiment.slow_dds = [self.SLOW_DDS() for i in range(config.slow_dds_channels_number)]
        self.experiment.experimental_data = self.ExperimentalData()
        self.experiment.experimental_data.camera = self.Camera()
        self.experiment.sequence = [self.Edge("Default")]
        
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
            self.experiment.sequence[0] = self.Edge(name="Default")
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
        self._ensure_title_list('title_digital_tab', config.digital_channels_number, prefix='D')
        self._ensure_title_list('title_analog_tab', config.analog_channels_number, prefix='A')
        self._ensure_title_list('title_dds_tab', config.dds_channels_number, prefix='DDS')
        self._ensure_title_list('title_mirny_tab', config.mirny_channels_number, prefix='M')
        self._ensure_title_list('title_sampler_tab', config.sampler_channels_number, prefix='S')
        self._ensure_title_list('title_slow_dds_tab', config.slow_dds_channels_number, prefix='slow DDS')


    def _ensure_variable_structures(self):
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
            if isinstance(candidate, self.Variable):
                normalized_variables.append(candidate)
                continue
            if isinstance(candidate, dict):
                name = candidate.get('name', '')
                value = candidate.get('value', 0.0)
                for_python = candidate.get('for_python', value)
                normalized_variables.append(
                    self.Variable(
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
                self.Variable(
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
            if isinstance(existing_entry, self.Variable):
                continue
            if isinstance(existing_entry, dict):
                self.experiment.variables[variable.name] = self.Variable(
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
                self.experiment.variables[variable.name] = self.Variable(
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
            self.experiment.variables['id0'] = self.Variable(name='id0', value=0.0, for_python=0.0)
        if '' not in self.experiment.variables:
            self.experiment.variables[''] = self.Variable(name='', value=0.0, for_python=0.0)


    def _ensure_title_list(self, attr_name, channel_count, prefix='X'):
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
        msg = QMessageBox()
        msg.setFont(QFont('Arial', 14))
        msg.setIcon(QMessageBox.Critical)
        msg.setText("Error")
        msg.setInformativeText(text)
        msg.setWindowTitle(title)
        msg.exec_()
 


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
        It takes the initial name as a String input and returns the Sring of the modified text
        '''
        to_remove = "~!@#$%^&*()-=/*+.?[]{;}:\|<>` "
        for character in to_remove:
            text = text.replace(character, "")
        return text
    

    
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
    def sequence_table_changed(self, item):
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
        if self.to_update:
            row = item.row()
            col = item.column()
            edge = self.experiment.sequence[row]
            table_item = self.sequence_table.item(row,col)
            if col == 1: # edge name changed
                edge.name = table_item.text()
                update.from_object(self)
            elif col == 3: # edge time expression changed
                if table_item.text() == "":
                    #previous edge values
                    edge.expression = self.experiment.sequence[row-1].expression #previous edge
                    edge.evaluation = self.experiment.sequence[row-1].evaluation #previous edge
                    edge.value = self.experiment.sequence[row-1].value #previous edge
                    edge.for_python = self.experiment.sequence[row-1].for_python #previous edge
                    #updating table entry
                    self.update_off()
                    table_item.setText(edge.expression)
                    self.update_on()
                else:                        
                    try:
                        expression = table_item.text()
                        (expression, evaluation, for_python, is_scanned, is_ramped, is_sampled, is_derived, is_lookup) = self.decode_input(expression)
                        exec("self.value = " + str(evaluation)) # this is done here to be able to assign value of the id# type variable
                        if self.value < 0: #restricting negative values for time
                            self.error_message("Negative values are not allowed", "Negative time value")
                            self.update_off()
                            table_item.setText(str(edge.expression))
                            self.update_on()
                        else:
                            edge.value = self.value
                            edge.evaluation = evaluation
                            edge.expression = expression
                            edge.for_python = for_python
                            edge.is_scanned = is_scanned
                            edge.is_ramped = is_ramped
                            self.experiment.variables[edge.id] = self.Variable(name = edge.id, value = edge.value, for_python = edge.for_python, is_scanned = edge.is_scanned, is_ramped = edge.is_ramped)
                            update.sequence_tab(self) 
                            update.from_object(self)
                    except:
                        self.error_message("Expression can not be evaluated", "Wrong entry")
                        self.update_off()
                        table_item.setText(str(edge.expression))
                        self.update_on()                        





    def save_sequence_button_clicked(self):
        '''
        Function is used when the user wants to save the sequence. In there is no file corresponsing to the sequence displayed the 
        user needs to specify its location and name. Otherwise it will orverwrite the sequence that was opened
        '''
        # Save camera state before pickling
        if hasattr(self, "camera_box"):
            self.experiment.camera_enabled = self.camera_box.isChecked()
        if hasattr(self, "_texp_locked"):
            self.experiment.texp_locked = self._texp_locked
        
        if self.experiment.file_name == "":
            self.experiment.file_name = QFileDialog.getSaveFileName(self, 'Save File')[0]
            if self.experiment.file_name != "": #happens when no file name was given (canceled)
                try:
                    with open(self.experiment.file_name, 'wb') as file:
                        pickle.dump(self.experiment, file)
                    self.create_file_name_label()
                    self.message_to_logger("Sequence saved at %s" %self.experiment.file_name)
                except:
                    self.message_to_logger("Saving attempt was not successful")                
        else:
            with open(self.experiment.file_name, 'wb') as file:
                pickle.dump(self.experiment, file)
            self.message_to_logger("Sequence saved at %s" %self.experiment.file_name)





    def load_sequence_button_clicked(self):
        '''
        Function is used when the user wants to load the sequence. It triggers the folder explorer and lets the user choose 
        the file to open.
        '''
        sequences_dir = self.repo_path / "sequences"
        initial_dir = sequences_dir if sequences_dir.is_dir() else self.repo_path
        loaded_file_name = QFileDialog.getOpenFileName(
            self,
            "Open File",
            str(initial_dir),
        )[0]
        if loaded_file_name != "": #happens when no file name was given (canceled)
            try:
                with open(loaded_file_name, 'rb') as file:
                    self.experiment = pickle.load(file)
                #this was only created to avoid crushing when the old versions of experiments are loaded without the skip_images attribute
                if hasattr(self.experiment, 'skip_images'):
                    pass
                else:
                    self.experiment.skip_images = False
                    self.skip_images_button.setStyleSheet(""" QPushButton {background-color: red; color: white}  QToolTip {color: black}""")
                #this was only created to avoid crushing when the old versions of experiments are loaded without the cam_trigger_off attribute
                if hasattr(self.experiment, 'cam_trigger_off'):
                    pass
                else:
                    self.experiment.cam_trigger_off = False
                    self.cam_trigger_off_button.setStyleSheet(""" QPushButton {background-color: red; color: white}  QToolTip {color: black}""")
                #this was only created to avoid crushing when the old versions of experiments are loaded without the cont_run_after_exp attribute
                if hasattr(self.experiment, 'cont_run_after_exp'):
                    pass
                else:
                    self.experiment.cont_run_after_exp = False
                    self.cont_run_after_exp_button.setStyleSheet(""" QPushButton {background-color: red; color: white}  QToolTip {color: black}""")
                #this was only created to avoid crushing when the old versions of experiments are loaded without the camera_enabled attribute
                if hasattr(self.experiment, 'camera_enabled'):
                    pass
                else:
                    self.experiment.camera_enabled = False
                #this was only created to avoid crushing when the old versions of experiments are loaded without the texp_locked attribute
                if hasattr(self.experiment, 'texp_locked'):
                    pass
                else:
                    self.experiment.texp_locked = False

                self._ensure_title_lengths()
                self._ensure_variable_structures()
                self.sequence_num_rows = len(self.experiment.sequence)
                self.update_off()
                #update the state of the checkbox for doing the scan
                self.scan_table.setChecked(self.experiment.do_scan)
                #update the state of the checkbox for doing the ramp
                self.ramp_table.setChecked(self.experiment.do_ramp) 
                #update the label showing the sequence that is being modified 
                self.experiment.file_name = loaded_file_name
                self.create_file_name_label()
                update.from_object(self)
                try:
                    exp_data = getattr(self.experiment, "experimental_data", None)
                    row = getattr(exp_data, "experiment_id", None) if exp_data else None
                    row_int = None
                    if isinstance(row, int):
                        row_int = row
                    elif isinstance(row, str):
                        row_stripped = row.strip()
                        if row_stripped.isdigit():
                            row_int = int(row_stripped)
                    if row_int is not None and hasattr(self, "experiment_list_list_widget"):
                        if 0 <= row_int < self.experiment_list_list_widget.count():
                            self.experiment_list_list_widget.setCurrentRow(row_int)
                        else:
                            self.experiment_list_list_widget.clearSelection()
                except Exception as restore_exc:
                    self.message_to_logger(f"Could not restore experiment selection: {restore_exc}")
                self.message_to_logger("Sequence loaded from %s" %self.experiment.file_name)
                
                #restore camera box state and parameters after successful load
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
                            if hasattr(cam, 'gain_db'):
                                self.gain_edit.setText(str(cam.gain_db))
                            if hasattr(cam, 'exposure_time'):
                                self.exposure_edit.setText(str(cam.exposure_time))
                            if hasattr(cam, 'format_name') and cam.format_name:
                                index = self.format_combo.findText(cam.format_name)
                                if index >= 0:
                                    self.format_combo.setCurrentIndex(index)
                    # Restore T_exp_ lock state
                    if hasattr(self, "lock_cb"):
                        self.lock_cb.setChecked(self.experiment.texp_locked)
                        self._texp_locked = self.experiment.texp_locked
                        self._update_texp_lock_presentation()
                except Exception as e:
                    self.message_to_logger(f"Could not restore camera settings: {e}")
            except Exception as e:
                self.error_message(f'Could not load the file: {e}', 'Error')
            self.update_on()





    def create_file_name_label(self):
        '''
        Function was created to make the code more readable 
        '''
        self.file_name_lable.setText(self.experiment.file_name)





    def find_unique_id(self):
        '''
        Function iterates over the id numbers from id0, id1, etc. until it finds the smallest available id number and returns it
        '''
        for id in range(10**4):
            unique_id = "id" + str(id)
            if unique_id not in self.experiment.variables:
                return unique_id
        




    def insert_edge_button_clicked(self):   
        '''
        Function is used to insert a new edge. Its values are assigned to be the same as the values of the previous edge but empty name.
        Updating of tables is done by setting all channels is_changed to False and updating from object
        '''
        #appending a new edge with a unique id
        new_unique_id = self.find_unique_id()
        new_edge = deepcopy(self.experiment.sequence[-1]) #copying the last edge
        new_edge.id = new_unique_id
        new_edge.name = ""
        self.experiment.sequence.append(new_edge)
        self.sequence_num_rows += 1
        #creating a corresponding variable so one can use id# as a variable
        self.experiment.variables[new_edge.id] = self.Variable(name = new_edge.id, value = new_edge.value, for_python = new_edge.for_python)
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





    def delete_edge_button_clicked(self):
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
                    self.sequence_table.setCurrentCell(row-1, 0)
                    update.from_object(self) #updating all tables
                else:
                    self.experiment.variables[name] = backup
                    self.error_message('The edge time value is used as a variable in %s.'%return_value, 'Can not delete used edge')
        except:
            self.error_message("Select the edge you want to delete", "No edge selected")





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
        self.dds_seq.item(edge_num+2,0).setBackground(set_color)
        self.dds_seq.item(edge_num+2,1).setBackground(set_color)
        self.dds_seq.item(edge_num+2,2).setBackground(set_color)
        self.to_update = True        




    
    def go_to_edge_button_clicked(self):
        '''
        Function is used to set the hardware into a specific time edge state. User needs to click the edge before pressing the button.
        After a successful execution the edge will be highlighted in green. The function recognizes the tab that is being currently displayed
        and assigns the hardware to the state of the last selected edge in that particular tab.
        '''
        try:                
            if self.main_window.currentIndex() == 0:
                edge_num = self.sequence_table.selectedIndexes()[0].row()
            elif self.main_window.currentIndex() == 1:
                edge_num = self.digital_dummy.selectedIndexes()[0].row()    
            elif self.main_window.currentIndex() == 2:
                edge_num = self.analog_dummy.selectedIndexes()[0].row()    
            elif self.main_window.currentIndex() == 3:
                edge_num = self.dds_seq.selectedIndexes()[0].row() - 2 # because top 2 rows are used for title   
            elif self.main_window.currentIndex() == 4:
                edge_num = self.mirny_dummy.selectedIndexes()[0].row() - 2 # because top 2 rows are used for title   
            write_to_python.create_go_to_edge(self, edge_num=edge_num)
            self.message_to_logger("Go to edge file generated")
            try:
                if config.package_manager == "conda":
                    submit_experiment_thread = threading.Thread(target=os.system, args=["conda activate %s && artiq_run ../ARTIQ_scripts/go_to_edge.py"%config.artiq_environment_name])
                elif config.package_manager == "clang64":
                    #coprint("Current directory:", os.getcwd()) #env_test
                    submit_experiment_thread = threading.Thread(target=os.system, args=[str(self.repo_path / "experiment_specific_files" / "hybrid_experiment" / 'go_to_edge.bat')])
                submit_experiment_thread.start()
                self.message_to_logger("Went to edge")
                print("edge_num", edge_num)
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


    def run_experiment_button_clicked(self): 
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
                with open(metadata_dir / 'metadata.json', "w") as outfile:
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





    def init_hardware_button_clicked(self):
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
                    submit_experiment_thread = threading.Thread(target=os.system, args=["conda activate %s && artiq_run ../ARTIQ_scripts/init_hardware.py"%config.artiq_environment_name])
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





    def generate_run_experiment_py_button_clicked(self):
        '''
        Function is used to generate the run_experiment.py according to the experimental descirption without
        running it. It is usefull for debugging purposes.
        '''
        update.digital_analog_dds_mirny_tabs(self) #specifically used to update for_python version of each parameter in the sequence
        try:
            write_to_python.create_experiment(self)
            if self.experiment.do_ramp == True and self.startID_edge_next_to_endID_edge() == False:
                self.message_to_logger("Ramp: End ID edge is not right after Start ID edge!")
                raise ValueError("startID is not next to endID")
            self.message_to_logger("Python file generated")
        except:
            self.message_to_logger("Was not able to generate python file")





    def submit_run_experiment_py_button_clicked(self):
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
        file_name = "../ARTIQ_scripts/run_experiment.py"
        if os.path.exists(file_name):
            try:
                #initialize environment and submit the experiment to the scheduler
                if config.package_manager == "conda":
                    submit_experiment_thread = threading.Thread(target=os.system, args=["conda activate %s && artiq_run ../ARTIQ_scripts/run_experiment.py"%config.artiq_environment_name])
                elif config.package_manager == "clang64":
                    # submit_experiment_thread = threading.Thread(target=os.system, args=["run_experiment.bat"])
                    submit_experiment_thread = threading.Thread(target=lambda: subprocess.Popen(['cmd', '/c', str(self.repo_path / "experiment_specific_files" / "hybrid_experiment" / 'run_experiment.bat')],creationflags=subprocess.CREATE_NEW_CONSOLE))
                submit_experiment_thread.start()
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
            except:
                self.message_to_logger("Was not able to start experiment")        
        else:
            self.message_to_logger("The file run_experiment.py is not found")
        




    def dummy_button_clicked(self):
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


      


    def save_sequence_as_button_clicked(self):
        '''
        Function is used when the user wants to save the sequence as a separate file. It will not reassign the current file name
        but just create an additional copy of the current state of the self.experiment
        '''
        # Save camera state before pickling
        if hasattr(self, "camera_box"):
            self.experiment.camera_enabled = self.camera_box.isChecked()
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





    def continuous_run_button_clicked(self):
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
                    submit_run_continuously_thread = threading.Thread(target=os.system, args=["conda activate %s && artiq_run ../ARTIQ_scripts/run_experiment.py"%config.artiq_environment_name])
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




    
    def multiple_runs_button_clicked(self):
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
                with open(metadata_dir / 'metadata.json', "w") as outfile:
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
    



        
    def stop_continuous_run_button_clicked(self):
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
                    submit_experiment_thread = threading.Thread(target=os.system, args=["conda activate %s && artiq_run ../ARTIQ_scripts/init_hardware.py"%config.artiq_environment_name])
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





    def save_default_button_clicked(self):
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

 



    def saving_default(self):
        '''
        This function is used to trigger the event of button_yes for save_default_button_clicked. When using it to accept the dialog and then
        having a flag of self.dialog.accepted in case the window was closed by clicking the close button at the 
        right top corner, the dialog was accepted by default.
        '''
        # Save camera state before pickling
        if hasattr(self, "camera_box"):
            self.experiment.camera_enabled = self.camera_box.isChecked()
        if hasattr(self, "_texp_locked"):
            self.experiment.texp_locked = self._texp_locked
        
        try:
            with open(self.repo_path / "default" / "default", 'wb') as file:
                pickle.dump(self.experiment, file)
            self.message_to_logger("Default saved at %s" %self.experiment.file_name)
        except:
            self.message_to_logger("Saving attempt was not successful")
        self.dialog.accept()
    




    def load_default_button_clicked(self):
        '''
        Function is used when the user wants to load the default settings. This can be used when loading the old versions of experiemnts
        to overwrite the titles and default states to the updated default values.
        '''
        self.update_off()
        try:
            with open(self.repo_path / "default" / "default", 'rb') as file:
                default_experiment = pickle.load(file)
            #Reassign the default values to the current self.experiment object
            self.experiment.sequence[0] = deepcopy(default_experiment.sequence[0])
            self.experiment.title_digital_tab = deepcopy(default_experiment.title_digital_tab)
            self.experiment.title_analog_tab = deepcopy(default_experiment.title_analog_tab)
            self.experiment.title_dds_tab = deepcopy(default_experiment.title_dds_tab)
            update.from_object(self)
            self.message_to_logger("Default values loaded from %s" %self.experiment.file_name)
        except:
            self.error_message('Could not load the file.', 'Error')
        self.update_on()





    def clear_logger_button_clicked(self):
        '''
        The function is used to clear the logger
        '''
        self.logger.clear()





    def scan_table_checked(self):
        '''
        Function is used when the user checks/unchecks the scan table checkbox
        '''
        if self.to_update:
            self.experiment.do_scan = self.scan_table.isChecked()
            if self.experiment.do_scan == False:
                #User unchecked the scan. Reassign the variables to the pre scanning values using self.experiment.new_variables
                for item in self.experiment.new_variables:
                    self.experiment.variables[item.name].value = item.value
                    #there is no need for manually making the variables is_scanned attribute False since it is done in decode_input as self.experiment.do_scan is false
            else: #User checked the scan. Assign the scanned variables values to the minimum value. This is required in case they are used in edge time expression to allow sorting
                for variable in self.experiment.scanned_variables:
                    if variable.name != "None":
                        self.experiment.variables[variable.name].value = variable.min_val
            update.digital_analog_dds_mirny_tabs(self)
            update.variables_tab(self, derived_variables = False)
        



    
    def add_scanned_variable_button_pressed(self):
        '''
        Function is used when the user wants to add a scanned variable. It adds a variable with the name "None" and updates the 
        scan_table to display the changes
        '''
        self.experiment.scanned_variables.append(self.Scanned_variable("None", 0.0, 0.0))
        update.scan_table(self)





    def delete_scanned_variable_button_pressed(self):
        '''
        Function is used when the user wants to delete scanned variable.        
        '''
        try:
            row = self.scan_table_parameters.selectedIndexes()[0].row()
            variable = self.experiment.scanned_variables[row]
            index = self.index_of_a_new_variable(variable.name)
            if index != None: #this is done to avoid trying to access "None" variable
                #reverting the value and scanning state of the variable that is not scanned anymore
                self.experiment.variables[variable.name].is_scanned = False
                self.experiment.variables[variable.name].value = self.experiment.new_variables[index].value #Assign the value of variable to the previous value before being scanned
                self.experiment.new_variables[index].is_scanned = False
                self.experiment.variables[variable.name].for_python = self.experiment.variables[variable.name].value
            del self.experiment.scanned_variables[row]
            #First update the variables tab in order to update the values for evaluation in following update steps
            update.variables_tab(self, derived_variables = False)
            update.scan_table(self)
            update.digital_analog_dds_mirny_tabs(self)
            if row != 0:
                self.scan_table_parameters.setCurrentCell(row-1, 0)
        except:
            self.error_message("Select the variable that needs to be deleted", "No variable selected")





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





    def number_of_steps_input_changed(self):
        '''
        Function is used when the user changes the number of steps in the scan_table.
        Input field allows simple mathematical expressions but in the end only preserves the integer values.
        There is an error message that prevents user from entering an expression resulting in 0 or negative values.
        '''
        if self.to_update: 
            try:
                expression = self.number_of_steps_input.text()
                (expression, evaluation, for_python, is_scanned, is_ramped, is_sampled, is_derived, is_lookup) = self.decode_input(expression)
                exec("self.value = " + str(evaluation))
                if self.value > 0: #check whether it is a positive integer
                    self.experiment.number_of_steps = int(self.value)
                else:
                    self.error_message("Only positive integers larger than 0 are allowed", "Wrong entry")    
            except:
                self.error_message("Expression can not be evaluated", "Wrong entry")
            self.update_off()
            self.number_of_steps_input.setText(str(self.experiment.number_of_steps))
            self.update_on()





    def number_of_runs_input_changed(self): 
        '''
        analog to number_of_steps_input_changed
        '''

        tab_names = ['number_of_runs_input_sequence','number_of_runs_input_analog',
                      'number_of_runs_input_digital','number_of_runs_input_dds',
                      'number_of_runs_input_mirny','number_of_runs_input_sampler',
                      'number_of_runs_input_variables','number_of_runs_input_acquisition','number_of_runs_input_slow_dds']
        var_table_names = [name for name in tab_names if hasattr(self, name)]

        for var_table_name in var_table_names:
            var_table_block = getattr(self, var_table_name)
            var_table_block.blockSignals(True)
        
        line = self.sender()


        if self.to_update: 
            try:
                expression = line.text()
                (expression, evaluation, for_python, is_scanned, is_ramped, is_sampled, is_derived, is_lookup) = self.decode_input(expression)
                exec("self.value = " + str(evaluation))
                if self.value > 0: 
                    self.experiment.number_of_runs = int(self.value)
                else:
                    self.error_message("Only positive integers larger than 0 are allowed", "Wrong entry")    
            except:
                self.error_message("Expression can not be evaluated", "Wrong entry")
            self.update_off()
            # self.number_of_runs_input.setText(str(self.experiment.number_of_runs))
            # update.number_of_runs(self)
            for var_table_name in var_table_names:
                var_table = getattr(self, var_table_name)
                var_table.setText(str(self.experiment.number_of_runs))
            self.update_on()

        for var_table_name in var_table_names:
            var_table_block = getattr(self, var_table_name)
            var_table_block.blockSignals(False)





    def check_if_already_scanned(self, name):
        '''
        Function takes a variable name as an input and checks if it already exists in a scanned variables list.
        This is used to avoid providing two same scanned variable. Returns True in case of duplicates and False otherwise
        '''
        for variable in self.experiment.scanned_variables:
            if variable.name == name:
                return True
        return False





    def scan_table_changed(self, item):
        '''
        Function is used when the user changes parameter of a scan table.
        Function takes no inputs, item is an internal variable that has information of the row and column of the entry that has been changed
        '''
        if self.to_update:
            row = item.row()
            col = item.column()
            table_item = self.scan_table_parameters.item(row, col)
            variable = self.experiment.scanned_variables[row]
            if col == 0: #name of the scanned variable changed
                new_variable_name = self.remove_restricted_characters(table_item.text())
                table_item.setText(new_variable_name)
                if self.check_if_already_scanned(new_variable_name) == False: #Check if the given variable is defined previously or not
                    index = self.index_of_a_new_variable(new_variable_name)
                    if self.index_of_a_new_variable(new_variable_name) != None: #Check if the varible name is defined in Variables tab
                        if new_variable_name not in self.experiment.sampler_variables: #Check if the variable name is used for sampling
                            #Proceeding with changes
                            prev_index = self.index_of_a_new_variable(variable.name)
                            if prev_index != None: #make the value of variable to the previous before being scanned.
                                #reverting the values to before scanning values and scanning states of the previous variable
                                self.experiment.variables[variable.name].value = self.experiment.new_variables[prev_index].value 
                                self.experiment.variables[variable.name].is_scanned = False 
                                self.experiment.variables[variable.name].for_python = self.experiment.variables[variable.name].value
                                self.experiment.new_variables[prev_index].is_scanned = False
                            #updating the values and scanning states of the new scanning  variable
                            variable.name = new_variable_name
                            self.experiment.variables[variable.name].value = variable.min_val
                            self.experiment.variables[variable.name].for_python = "self." + variable.name + "[step]"
                            self.experiment.variables[variable.name].is_scanned = True
                            self.experiment.new_variables[index].is_scanned = True
                        else: #The variable name enteres is used in sampler tab
                            self.error_message("The variable name you entered was already used in sampler tab", "Used variable name")
                            self.update_off()
                            table_item.setText(variable.name)
                            self.update_on()                            
                    else: #The variable name entered is not defined in a variables tab
                        self.error_message("The variable name you entered was not defined in variables tab", "Not defined variable")
                        self.update_off()
                        table_item.setText(variable.name)
                        self.update_on()
                else:
                    self.error_message("The variable name you entered was already used for scanning.", "Scanning variable duplicate")
                self.count_scanned_variables()
            elif col == 1: #min_val of the scanned variable changed
                try:
                    variable.min_val = float(table_item.text())
                    table_item.setText(str(variable.min_val))
                    if self.scan_table_parameters.item(row, 0).text() != "None": # this makes sure that we do not have to deal with "None" named variable
                        # we use the min values in order to use in sorting of the sequence tab
                        self.experiment.variables[variable.name].value = variable.min_val
                except:
                    self.error_message("Expression can not be evaluated", "Wrong entry")
            elif col == 2: #max_val of the scanned variable changed
                try:
                    variable.max_val = float(table_item.text())
                    table_item.setText(str(variable.max_val))
                except:
                    self.error_message("Expression can not be evaluated", "Wrong entry")
            update.digital_analog_dds_mirny_tabs(self)
            update.variables_tab(self, derived_variables = False)
            update.scan_table(self)       
        else:
            pass





    def skip_images_button_clicked(self):
        '''
        Function is used to toggle the initial trigger of the camera 10 times due to the problem of image acquisition.
        '''
        self.experiment.skip_images = not self.experiment.skip_images
        if self.experiment.skip_images:
            #set the color of the button to green
            self.skip_images_button.setStyleSheet(""" QPushButton {background-color: green; color: white}  QToolTip {color: black}""")
        else:
            #set the color of the button to red
            self.skip_images_button.setStyleSheet(""" QPushButton {background-color: red; color: white}  QToolTip {color: black}""")





    def cam_trigger_off_button_clicked(self):
        '''
        Camera trigger off button allows running the experiment without trigering the camera even when the corresponding tab is on.
        '''
        self.experiment.cam_trigger_off = not self.experiment.cam_trigger_off
        if self.experiment.cam_trigger_off:
            #set the color of the button to green
            self.cam_trigger_off_button.setStyleSheet(""" QPushButton {background-color: green; color: white}  QToolTip {color: black}""")
        else:
            #set the color of the button to red
            self.cam_trigger_off_button.setStyleSheet(""" QPushButton {background-color: red; color: white}  QToolTip {color: black}""")





    def cam_trigger_off_input_changed(self):
        '''
        analog to number_of_steps_input_changed
        '''
        if self.to_update: 
            try:
                expression = self.cam_trigger_off_input.text()
                (expression, evaluation, for_python, is_scanned, is_ramped, is_sampled, is_derived, is_lookup) = self.decode_input(expression)
                exec("self.value = " + str(evaluation))
                if self.value > 0: 
                    self.experiment.cam_trigger_off_runs = int(self.value)
                else:
                    self.error_message("Only positive integers larger than 0 are allowed", "Wrong entry")    
            except:
                self.error_message("Expression can not be evaluated", "Wrong entry")
            self.update_off()
            self.cam_trigger_off_input.setText(str(self.experiment.cam_trigger_off_runs))
            self.update_on()





    def cont_run_after_exp_button_clicked(self):
        '''
        Allows to run continuous run right after an experiment; used with run_experiment or multiple_runs.
        '''
        self.experiment.cont_run_after_exp = not self.experiment.cont_run_after_exp
        if self.experiment.cont_run_after_exp:
            #set the color of the button to green
            self.cont_run_after_exp_button.setStyleSheet(""" QPushButton {background-color: green; color: white}  QToolTip {color: black}""")
        else:
            #set the color of the button to red
            self.cont_run_after_exp_button.setStyleSheet(""" QPushButton {background-color: red; color: white}  QToolTip {color: black}""")





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
            update.variables_tab(self, derived_variables = False)





    def add_ramped_variable_button_pressed(self):
        '''
        analog to add_scanned_variable_button_pressed
        '''
        self.experiment.ramped_variables.append(self.Ramped_variable("None", 0, 0, 0.0, 0)) 
        update.ramp_table(self)





    def delete_ramped_variable_button_pressed(self):
        '''
        analog to delete_scaned_variable_button_pressed        
        '''
        try:
            row = self.ramp_table_parameters.selectedIndexes()[0].row()
            variable = self.experiment.ramped_variables[row]
            index = self.index_of_a_new_variable(variable.name)
            if index != None: #this is done to avoid trying to access "None" variable
                #reverting the value and scanning state of the variable that is not scanned anymore
                self.experiment.variables[variable.name].is_ramped = False
                self.experiment.variables[variable.name].value = self.experiment.new_variables[index].value #Assign the value of variable to the previous value before being scanned
                self.experiment.new_variables[index].is_ramped = False
                self.experiment.variables[variable.name].for_python = self.experiment.variables[variable.name].value
            del self.experiment.ramped_variables[row]
            #First update the variables tab in order to update the values for evaluation in following update steps
            update.variables_tab(self, derived_variables = False)
            update.ramp_table(self)
            update.digital_analog_dds_mirny_tabs(self)
            if row != 0:
                self.ramp_table_parameters.setCurrentCell(row-1, 0)
            try:
                if self.experiment.do_ramp == True:
                    self.update_sequence_edge_colors()
            except:
                pass
        except:
            self.error_message("Select the variable that needs to be deleted", "No variable selected")





    def check_if_already_ramped(self, name):
        '''
        analog to check_if_already_scaned
        '''
        for variable in self.experiment.ramped_variables:
            if variable.name == name:
                return True
        return False





    def ramp_table_changed(self, item):
        '''
        analog to scan_table_changed
        '''
        if self.to_update:
            row = item.row()
            col = item.column()
            table_item = self.ramp_table_parameters.item(row, col)
            variable = self.experiment.ramped_variables[row] 
            if col == 0: #name of the ramped variable changed
                new_variable_name = self.remove_restricted_characters(table_item.text())
                table_item.setText(new_variable_name)
                if self.check_if_already_ramped(new_variable_name) == False: #Check if the given variable is defined previously or not
                    index = self.index_of_a_new_variable(new_variable_name)
                    if self.index_of_a_new_variable(new_variable_name) != None: #Check if the varible name is defined in Variables tab
                        if new_variable_name not in self.experiment.sampler_variables: #Check if the variable name is used for sampling
                            #Proceeding with changes
                            prev_index = self.index_of_a_new_variable(variable.name)
                            if prev_index != None: #make the value of variable to the previous before being ramped.
                                #reverting the values to before ramping values and ramping states of the previous variable
                                self.experiment.variables[variable.name].functionramp = self.experiment.new_variables[prev_index].value
                                self.experiment.variables[variable.name].is_ramped = False
                                self.experiment.variables[variable.name].for_python = self.experiment.variables[variable.name].functionramp
                                self.experiment.new_variables[prev_index].is_ramped = False
                            #updating the values and ramping states of the new ramping variable
                            variable.name = new_variable_name
                            self.experiment.variables[variable.name].functionramp = variable.functionramp
                            self.experiment.variables[variable.name].for_python = str(variable.functionramp)
                            self.experiment.variables[variable.name].is_ramped = True
                            self.experiment.new_variables[index].is_ramped = True
                        else: #The variable name enteres is used in sampler tab
                            self.error_message("The variable name you entered was already used in sampler tab", "Used variable name")
                            self.update_off()
                            table_item.setText(variable.name)
                            self.update_on()                            
                    else: #The variable name entered is not defined in a variables tab
                        self.error_message("The variable name you entered was not defined in variables tab", "Not defined variable")
                        self.update_off()
                        table_item.setText(variable.name)
                        self.update_on()
                else:
                    self.error_message("The variable name you entered was already used for ramping.", "Ramping variable duplicate")
                self.count_ramped_variables()
            elif col == 1: #start_ID changed 
                try:
                    variable.start_ID = str(table_item.text()) 
                    table_item.setText(str(variable.start_ID)) 
                except:
                    self.error_message("Expression can not be evaluated", "Wrong entry")
                try:
                    if self.experiment.do_ramp == True:
                        self.update_sequence_edge_colors()
                except:
                    pass
            elif col == 2: #end_ID changed 
                try:
                    variable.end_ID = str(table_item.text()) 
                    table_item.setText(str(variable.end_ID)) 
                except:
                    self.error_message("Expression can not be evaluated", "Wrong entry")
                try:
                    if self.experiment.do_ramp == True:
                        self.update_sequence_edge_colors()
                except:
                    pass
            elif col == 3: #functionramp changed
                try:
                    variable.functionramp = str(table_item.text())
                    table_item.setText(str(variable.functionramp))
                    self.experiment.variables[variable.name].for_python = str(variable.functionramp)
                except:
                    self.error_message("Expression can not be evaluated", "Wrong entry")
            elif col == 4:  #stepsramp changed
                try:
                    variable.stepsramp = int(table_item.text())
                    table_item.setText(str(variable.stepsramp))
                except:
                    self.error_message("Expression can not be evaluated", "Wrong entry")

            update.digital_analog_dds_mirny_tabs(self)
            update.variables_tab(self, derived_variables = False)
            update.ramp_table(self)       
        else:
            pass
    


        

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





    def digital_table_changed(self, item):
        '''
        Function is used when the user changes the values in the digital table. It ensures that the expressions are integer values
        0 or 1. The user can delete the input and the function will assign the value of the previous edge and unhighlight the channel
        indicating that it should not be changed and will only display previously set value.
        '''
        if self.to_update:
            row = item.row()
            col = item.column()
            table_item = self.digital_table.item(row,col)
            channel = self.experiment.sequence[row].digital[col-4]
            if table_item.text() == "": #User deleted the value. The function will display the previously set state
                if row == 0: #default edge 
                    self.error_message("You can not delete initial value!", "Default value is protected!")
                    self.update_off()
                    table_item.setText(channel.expression)
                    self.update_on()
                else:
                    channel.changed = False
                    update.digital_tab(self)
            else:   #User entered a new state
                try: 
                    #Checking whether the expression can be evaluated and the value is within allowed range
                    expression = table_item.text()
                    (expression, evaluation, for_python, is_scanned, is_ramped, is_sampled, is_derived, is_lookup) = self.decode_input(expression)
                    exec("self.value = " + evaluation)
                    if (self.value == 0 or self.value == 1):
                        channel.changed = True
                        update.digital_tab(self)
                    else:
                        #Reverting back the previously accepted expression
                        self.update_off()
                        table_item.setText(str(channel.expression))
                        self.update_on()
                        self.error_message("Only value '1' or '0' are expected!", "Wrong entry!")
                except:
                    #Return the previously assigned value if the expression can not be evaluated
                    self.update_off()
                    if channel.changed:
                        table_item.setText(channel.expression)
                    else:
                        table_item.setText(str(channel.value))
                    self.update_on()
                    self.error_message("Expression can not be evaluated", "Wrong entry")





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





    def analog_table_changed(self, item):
        '''
        Function is used when the user changes the values in the analog table. It ensures that the expressions are float values in the 
        range between -9.9 to +9.9. The user can delete the input and the function will assign the value of the previous edge and unhighlight the channel
        indicating that it should not be changed and will only display previously set value.
        '''
        if self.to_update:
            row = item.row()
            col = item.column()
            channel = self.experiment.sequence[row].analog[col - 4]
            table_item = self.analog_table.item(row,col)
            if table_item.text() == "": #User deleted the value. The function will display the previously set state
                if row == 0: # default edge
                    self.error_message("You can not delete initial value!", "Initial value is needed!")
                    self.update_off()
                    table_item.setText(channel.expression)
                    self.update_on()
                else:
                    channel.changed = False
                    update.analog_tab(self)
            else: #User entered a new state
                try:
                    #Checking whether the expression can be evaluated and the value is within allowed range                    
                    expression = table_item.text()
                    (expression, evaluation, for_python, is_scanned, is_ramped, is_sampled, is_derived, is_lookup) = self.decode_input(expression)
                    exec("self.value =" + evaluation)
                    if (self.value <= 9.9 and self.value >= -9.9):
                        channel.expression = expression
                        channel.evaluation = evaluation
                        channel.value = self.value
                        channel.is_scanned = is_scanned
                        channel.is_ramped = is_ramped 
                        channel.for_python = for_python 
                        channel.changed = True
                        update.analog_tab(self)
                    else:
                        #Reverting back the previously accepted expression                    
                        self.update_off()
                        table_item.setText(channel.expression)
                        self.update_on()
                        self.error_message("Only values between '+9.9' and '-9.9' are expected", "Wrong entry")
                except:
                    #Return the previously assigned value if the expression can not be evaluated                    
                    self.update_off()
                    table_item.setText(channel.expression)
                    self.update_on()
                    self.error_message('Expression can not be evaluated', 'Wrong entry')





    #DDS TAB RELATED FUNCTIONS
    def dds_table_changed(self, item):
        '''
        Function is used when the user changes the values in the dds table. It ensures that the expressions can be evaluated in the
        allowed input values range. The user can delete the input and the function will assign the value of the previous edge and 
        unhighlight the channel indicating that it should not be changed and will only display previously set value.
        '''        
        if self.to_update:
            row = item.row()
            col = item.column()
            edge_num = row
            channel = (col - 1)//6 #4 columns for edge and separation. division by 5 channel settings and 1 separation
            setting = col - 1 - 6 * channel # the number is a sequential value of setting. Frequency is 0, Amplitude 1, attenuation 2, phase 3, state 4
            if self.dds_table.item(row,col).text() == "": #User deleted the value. The function will display the previously set state
                if edge_num == 0: #Default edge
                    self.error_message("You can not delete initial value!", "Initial value is needed!")
                    self.update_off()
                    exec("self.dds_table.item(row,col).setText(str(self.experiment.sequence[edge_num].dds[channel].%s.expression))" %self.setting_dict[setting])
                    self.update_on()
                else: #Other than a default edge
                    #Removing background color
                    self.update_off()
                    for index_setting in range(5):
                        self.dds_table.item(row, channel*6 + 1 + index_setting).setBackground(self.white)
                    self.experiment.sequence[edge_num].dds[channel].changed = False
                    self.update_on()
                    update.dds_tab(self)
            else:   #User entered a new input value
                try:
                    #Checking whether the expression can be evaluated and the value is within allowed range                     
                    expression = self.dds_table.item(row,col).text()
                    (expression, evaluation, for_python, is_scanned, is_ramped, is_sampled, is_derived, is_lookup) = self.decode_input(expression)
                    exec("self.dummy_val =" + evaluation)
                    maximum, minimum = self.max_dict_dds[setting], self.min_dict_dds[setting]
                    if (self.dummy_val <= maximum and self.dummy_val >= minimum): 
                        exec("self.experiment.sequence[edge_num].dds[channel].%s.expression = expression" %self.setting_dict[setting])
                        exec("self.experiment.sequence[edge_num].dds[channel].%s.evaluation = evaluation" %self.setting_dict[setting])
                        exec("self.experiment.sequence[edge_num].dds[channel].%s.for_python = for_python" %self.setting_dict[setting])
                        exec("self.experiment.sequence[edge_num].dds[channel].%s.value = self.dummy_val" %self.setting_dict[setting])
                        exec("self.experiment.sequence[edge_num].dds[channel].%s.for_python = for_python" %self.setting_dict[setting])
                        self.experiment.sequence[edge_num].dds[channel].changed = True
                        update.dds_tab(self)
                    else:
                        #Reverting back the previously accepted expression                            
                        self.error_message("Only values between %f and %f are expected" %(minimum, maximum), "Wrong entry")
                        self.update_off()
                        exec("self.dds_table.item(row,col).setText(str(self.experiment.sequence[edge_num].dds[channel].%s.expression))" %self.setting_dict[setting])
                        self.update_on()
                except:
                    #Return the previously assigned value if the expression can not be evaluated                       
                    self.update_off()
                    exec("self.dds_table.item(row,col).setText(str(self.experiment.sequence[edge_num].dds[channel].%s.expression))" %self.setting_dict[setting])
                    self.update_on()
                    self.error_message('Expression can not be evaluated', 'Wrong entry')            


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
        if name != "":
            self.experiment.title_dds_tab[index] = "DDS%d"%(index) + " " + name
        else:
            self.experiment.title_dds_tab[index] = "DDS%d"%(index)
        self.dds_table_header.item(0,6*index+1).setText(self.experiment.title_dds_tab[index])
        self.dialog.accept()


    def dds_table_header_changed(self, item):
        '''
        Function is used when the user wants to change the name of the dds title. 
        It overwrites the value of the corresponding title name in the experiment object so when it is saved the changes are persitent.
        '''
        if self.to_update:
            col = item.column()
            print(col)
            self.experiment.title_dds_tab[(col - 1)//6 + 4] = self.dds_table_header.item(0,col).text() # title has 3 leading names and a separator





    #MIRNY TAB RELATED FUNCTIONS
    def mirny_table_changed(self, item):
        '''
        Function is used when the user changes the values in the mirny table. It ensures that the expressions can be evaluated in the
        allowed input values range. The user can delete the input and the function will assign the value of the previous edge and 
        unhighlight the channel indicating that it should not be changed and will only display previously set value.
        '''        
        if self.to_update:
            row = item.row()
            col = item.column()
            if col % 6 == 0:
                return
            edge_num = row
            channel = col // 6
            setting = col - (channel * 6) - 1 # Frequency is 0, Amplitude 1, attenuation 2, phase 3, state 4
            if edge_num < 0 or edge_num >= len(self.experiment.sequence):
                return
            if self.mirny_table.item(row,col).text() == "": #User deleted the value. The function will display the previously set state
                if edge_num == 0: #Default edge
                    self.error_message("You can not delete initial value!", "Initial value is needed!")
                    self.update_off()
                    exec("self.mirny_table.item(row,col).setText(str(self.experiment.sequence[edge_num].mirny[channel].%s.expression))" %self.setting_dict[setting])
                    self.update_on()
                else: #Other than a default edge
                    #Removing background color
                    self.update_off()
                    for index_setting in range(5):
                        cell = self.mirny_table.item(row, channel*6 + 1 + index_setting)
                        if cell is not None:
                            cell.setBackground(self.white)
                    self.experiment.sequence[edge_num].mirny[channel].changed = False
                    self.update_on()
                    update.mirny_tab(self)
            else:   #User entered a new input value
                try:
                    #Checking whether the expression can be evaluated and the value is within allowed range                     
                    expression = self.mirny_table.item(row,col).text()
                    (expression, evaluation, for_python, is_scanned, is_ramped, is_sampled, is_derived, is_lookup) = self.decode_input(expression)
                    exec("self.dummy_val =" + evaluation)
                    maximum, minimum = self.max_dict_mirny[setting], self.min_dict_mirny[setting]
                    if (self.dummy_val <= maximum and self.dummy_val >= minimum): 
                        exec("self.experiment.sequence[edge_num].mirny[channel].%s.expression = expression" %self.setting_dict[setting])
                        exec("self.experiment.sequence[edge_num].mirny[channel].%s.evaluation = evaluation" %self.setting_dict[setting])
                        exec("self.experiment.sequence[edge_num].mirny[channel].%s.for_python = for_python" %self.setting_dict[setting])
                        exec("self.experiment.sequence[edge_num].mirny[channel].%s.value = self.dummy_val" %self.setting_dict[setting])
                        exec("self.experiment.sequence[edge_num].mirny[channel].%s.for_python = for_python" %self.setting_dict[setting])
                        self.experiment.sequence[edge_num].mirny[channel].changed = True
                        update.mirny_tab(self)
                    else:
                        #Reverting back the previously accepted expression                            
                        self.error_message("Only values between %f and %f are expected" %(minimum, maximum), "Wrong entry")
                        self.update_off()
                        exec("self.mirny_table.item(row,col).setText(str(self.experiment.sequence[edge_num].mirny[channel].%s.expression))" %self.setting_dict[setting])
                        self.update_on()
                except:
                    #Return the previously assigned value if the expression can not be evaluated                       
                    self.update_off()
                    exec("self.mirny_table.item(row,col).setText(str(self.experiment.sequence[edge_num].mirny[channel].%s.expression))" %self.setting_dict[setting])
                    self.update_on()
                    self.error_message('Expression can not be evaluated', 'Wrong entry')            





    def mirny_dummy_header_changed(self, item):
        '''
        Function is used when the user wants to change the name of the mirny title. 
        It overwrites the value of the corresponding title name in the experiment object so when it is saved the changes are persitent.
        '''
        if self.to_update:
            col = item.column()
            row = item.row()
            if row == 0 and col % 6 == 1:
                channel_index = col // 6
                target_index = channel_index + 4
                while len(self.experiment.title_mirny_tab) <= target_index:
                    self.experiment.title_mirny_tab.append(f"M{len(self.experiment.title_mirny_tab) - 4}")
                self.experiment.title_mirny_tab[target_index] = self.mirny_dummy_header.item(0,col).text()





    #SLOW_DDS TAB RELATED FUNCTIONS
    def slow_dds_table_changed(self, item):
        '''
        Function is used when the user changes the values in the slow_dds table. It ensures that the expressions can be evaluated in the
        allowed input values range. The user can delete the input and the function will assign the value of the previous edge and 
        unhighlight the channel indicating that it should not be changed and will only display previously set value.
        '''        
        if self.to_update:
            row = item.row()
            col = item.column()
            channel = (col - 1)//6 #4 columns for edge and separation. division by 5 channel settings and 1 separation
            setting = col - 1 - 6 * channel # the number is a sequential value of setting. Frequency is 0, Amplitude 1, attenuation 2, phase 3, state 4
            if row == 2: #Table entry was changed
                if self.slow_dds_table.item(row,col).text() == "": #User deleted the value. The function will display the previously set state
                    self.error_message("You can not delete the value!", "Some value is required!")
                    self.update_off()
                    exec("self.slow_dds_table.item(row,col).setText(str(self.experiment.slow_dds[channel].%s))" %self.setting_dict[setting])
                    exec("self.slow_dds_table.item(row,col).setToolTip(str(self.experiment.slow_dds[channel].%s))" %self.setting_dict[setting])
                    self.update_on()
                else:   #User entered a new input value
                    try:
                        #Checking whether the expression can be evaluated and the value is within allowed range                     
                        expression = self.slow_dds_table.item(row,col).text()
                        (expression, evaluation, for_python, is_scanned, is_ramped, is_sampled, is_derived, is_lookup) = self.decode_input(expression)
                        exec("self.dummy_val =" + evaluation)
                        maximum, minimum = self.max_dict_dds[setting], self.min_dict_dds[setting]
                        if (self.dummy_val <= maximum and self.dummy_val >= minimum): #Change accepted
                            if setting == 0: #frequency
                                self.dummy_val = float(self.dummy_val) #Was checked to have at least a 1 Hz level resolution
                            elif setting == 1: #amplitude
                                self.dummy_val = int(float(self.dummy_val)*1000)/1000 # Keep only up to 3rd digit (0.1234 --> 0.123)
                            elif setting == 2: #attenuation
                                self.dummy_val = round(float(self.dummy_val)/0.5)*0.5 #Round up to 0.5
                            elif setting == 3: #phase
                                self.dummy_val = round(float(self.dummy_val)/0.36)*0.36 # Keep only up to 3rd digit (0.1234 --> 0.123) of phase that is represented as 1 -- > 360. 0.001 --> 0.36 in degrees 
                            elif setting == 4: #state
                                self.dummy_val = int(self.dummy_val)
                            exec("self.experiment.slow_dds[channel].%s = self.dummy_val" %self.setting_dict[setting])
                            self.update_off()
                            exec("self.slow_dds_table.item(row,col).setText(str(self.experiment.slow_dds[channel].%s))" %self.setting_dict[setting])
                            exec("self.slow_dds_table.item(row,col).setToolTip(str(self.experiment.slow_dds[channel].%s))" %self.setting_dict[setting])
                            self.update_on()
                            for parameter in range(5): #Changing the color of the entire channel
                                if self.experiment.slow_dds[channel].state == 1:
                                    self.update_off()
                                    self.slow_dds_table.item(row,(col - 1)//6 * 6 + parameter + 1).setBackground(self.green)
                                    self.update_on()
                                else:
                                    self.update_off()
                                    self.slow_dds_table.item(row,(col - 1)//6 * 6 + parameter + 1).setBackground(self.red)
                                    self.update_on()
                        else:
                            #Reverting back the previously accepted expression                            
                            self.error_message("Only values between %f and %f are expected" %(minimum, maximum), "Wrong entry")
                            self.update_off()
                            exec("self.slow_dds_table.item(row,col).setText(str(self.experiment.slow_dds[channel].%s))" %self.setting_dict[setting])
                            exec("self.slow_dds_table.item(row,col).setToolTip(str(self.experiment.slow_dds[channel].%s))" %self.setting_dict[setting])
                            self.update_on()
                    except:
                        #Return the previously assigned value if the expression can not be evaluated                       
                        self.update_off()
                        exec("self.slow_dds_table.item(row,col).setText(str(self.experiment.slow_dds[channel].%s))" %self.setting_dict[setting])
                        exec("self.slow_dds_table.item(row,col).setToolTip(str(self.experiment.slow_dds[channel].%s))" %self.setting_dict[setting])
                        self.update_on()
                        self.error_message('Expression can not be evaluated', 'Wrong entry')            
            elif row == 0: #Channel title was changed
                self.experiment.title_slow_dds_tab[(col)//6 + 4] = self.slow_dds_table.item(0,col).text() 





    def set_slow_dds_states_button_clicked(self):
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
                    submit_experiment_thread = threading.Thread(target=os.system, args=["conda activate %s && artiq_run ../ARTIQ_scripts/set_slow_dds_states.py"%config.artiq_environment_name])
                elif config.package_manager == "clang64":
                    print(str(self.repo_path / "experiment_specific_files" / "hybrid_experiment" / 'set_slow_dds_states.bat'))
                    submit_experiment_thread = threading.Thread(target=os.system, args=[str(self.repo_path / "experiment_specific_files" / "hybrid_experiment" / 'set_slow_dds_states.bat')])
                submit_experiment_thread.start()
                self.message_to_logger("Slow DDS states are set")
            except:
                self.message_to_logger("Was not able to set slow DDS states")
        except:
            self.message_to_logger("Was not able to generate python file")
    




    #VARIABLES TAB RELATED FUNCTIONS
    def find_new_variable_name_unused(self):
        '''
        Function itereates over the variable names of form var_1, var_2, etc. and returns the lowest available variable name
        '''
        for i in range(1, 1000):
            name = "var_" + str(i)
            if name not in self.experiment.variables:
                return name





    def delete_variable_button_clicked(self):
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





    def create_new_variable_button_clicked(self):
        '''
        Function is used when the user wants to create a new user defined variable. It finds the lowest unused available variable name and 
        creates it with initial value of 0.0. It also creates the corresponding Variable objects  in new_variables and variables.
        '''
        variable_name = self.find_new_variable_name_unused()
        self.experiment.new_variables.append(self.Variable(variable_name, 0.0, 0.0))
        self.experiment.variables[variable_name] = self.Variable(variable_name, 0.0, 0.0)
        # update.all_tabs(self,derived_variables = False)
        update.variable_tables(self)



    def block_all_signals(self, block=True):
        self.blockSignals(block)
        for child in self.findChildren(QObject):
            child.blockSignals(block)
    


    def variables_table_changed(self, item):
        '''
        Function is used when the user changes the values in the variables table. It makes sure that in case the name is changed
        the previous variable was not used in the expression of any parameter in the sequence. In case the previous variable is
        used in any epxression the function will let user know about the first occurence of that variable and revert the name. 
        It also makes sure that if the variable is used the expression when its value is changed the expression evaluation remains in the
        allowed parameters range.       
        '''
        
        

        if self.to_update:
            row = item.row()
            col = item.column()
            # if not explicit_sender:
            #     var_table_sender = self.sender()
            #     table_item = var_table_sender.item(row,col)
            # else:
            table_item = item
            
            variable = self.experiment.new_variables[row]

            if col == 0: #Variable name was changed
                if variable.name == "T_exp_" and getattr(self, "_texp_locked", False):
                    self.update_off()
                    table_item.setText(variable.name)
                    self.update_on()
                    return
                if variable.name not in self.experiment.sampler_variables: # Check if the variable is being sampled 
                    #Checking if the variable is being scanned or ramped 
                    variable_scanned = False
                    variable_ramped = False 
                    for item in self.experiment.scanned_variables:
                        if variable.name == item.name:
                            variable_scanned = True
                            break
                    for item in self.experiment.ramped_variables:
                        if variable.name == item.name:
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
                                if variable.name == lookup_variable.argument:
                                    is_lookup_argument = True
                                    break
                            if not is_lookup_argument:
                                new_name = self.remove_restricted_characters(table_item.text())
                                #Restricting the user from using the reserved default variable names in the form of id1, id2, etc.
                                if new_name[0:2] == "id" and new_name[2] in "0123456789":
                                    self.error_message("Variable names starting with id and following with integers are reserved for default edge time variables", "Invalid variable name")
                                elif new_name == "None": #Restricting the user from defining the variable name "None" as it is reserved by the Scan table
                                    self.error_message("Variable name None is reserved by the scan table. Please choose another name", "Invalid variable name")
                                    self.update_off()
                                    table_item.setText(variable.name)  
                                    update.variable_tables(self)     
                                    self.update_on()             
                                elif new_name in self.experiment.variables:#Restricting the user from defining the variable name as already defined variable names to avoid having duplicates
                                    self.error_message('Variable name is already used', 'Invalid variable name')
                                    self.update_off()
                                    table_item.setText(variable.name)  
                                    update.variable_tables(self)     
                                    self.update_on()                         
                                else: # The varibable name is almost among allowed, only the integer or float without other caracters should be checked.
                                    only_numbers = False
                                    try:
                                        float(new_name) #does not allow defining variable names that contains only integers without characters
                                        only_numbers = True
                                    except:
                                        pass
                                    if only_numbers: #Restricting the user from defining a variable name using only numbers
                                        self.update_off()
                                        table_item.setText(variable.name)  
                                        update.variable_tables(self)     
                                        self.update_on()                         
                                        self.error_message('Variable name can not be in a form of a number', 'Invalid variable name')
                                    else:
                                        #Allowed variable name. Now checking if it is used in any expression or not. It is done by deleting the variable and trying to evaluate every expression
                                        #variable.value is used as a back up if evaluation is not possible since we do not change self.experiment.new_variables to check if the variable is used or not
                                        backup = deepcopy(self.experiment.variables[variable.name])
                                        del self.experiment.variables[variable.name]
                                        return_value = update.digital_analog_dds_mirny_tabs(self) # we need to update value. In other words evaluate evaluations. No need to udpage expressions
                                        if return_value == None: #The previous variable was not used anywhere and can be changed
                                            self.experiment.variables[new_name] = backup
                                            self.experiment.variables[new_name].name = new_name
                                            self.experiment.variables[new_name].is_scanned = False
                                            self.experiment.variables[new_name].is_ramped = False
                                            variable.name = new_name
                                            self.update_off()
                                            table_item.setText(variable.name)
                                            update.variable_tables(self)
                                            self.update_on()                            
                                        else: #The previous variable was used somewhere. Reverting the name to the previous 
                                            self.error_message('The variable is used in %s.'%return_value, 'Can not delete used variable')
                                            self.experiment.variables[backup.name] = backup
                                            self.update_off()
                                            table_item.setText(backup.name)
                                            update.variable_tables(self)
                                            self.update_on()
                            else:
                                self.update_off()
                                table_item.setText(variable.name)
                                update.variable_tables(self)
                                self.update_on()                          
                                self.error_message("The variable is used as an argument in lookup variables. Remove it from the Lookup variables table before changing its name.", "Lookup variable's argument")
                        else:
                            self.update_off()
                            table_item.setText(variable.name)
                            update.variable_tables(self)
                            self.update_on()                          
                            self.error_message("The variable is used as an argument in derived variables. Remove it from the Derived variables table before changing its name.", "Derived variable's argument")
                    else:
                        self.update_off()
                        table_item.setText(variable.name)
                        update.variable_tables(self)
                        self.update_on()                          
                        self.error_message("The variable is scanned or ramped. Remove it from the scan or ramp table before deleting.", "Scanned or Ramped variable")
                else:
                    self.update_off()
                    table_item.setText(variable.name)
                    update.variable_tables(self)
                    self.update_on()                      
                    self.error_message("The variable is sampled. Remove it from the sampler tab before changing its name.", "Sampled variable")
            elif col == 1: #variable value was changed
                if variable.name == "T_exp_" and getattr(self, "_texp_locked", False):
                    self.update_off()
                    table_item.setText(str(variable.value))
                    self.update_on()
                    return
                #variable.value is used as a back up if evaluation is not possible since we do not change self.experiment.new_variables to check if the variable is used or not
                try:
                    #Checking if the new value resulting in the values allowed for each parameter it is used in
                    self.experiment.variables[variable.name].value = float(int(float(table_item.text())*1e6)/1e6)
                    # self.experiment.variables[variable.name].value = float(table_item.text())

                    return_value = update.digital_analog_dds_mirny_tabs(self) # we do not need to update expressions only update values.

                    if return_value == None: #The value can be updated
                        variable.value = self.experiment.variables[variable.name].value
                        self.experiment.variables[variable.name].for_python = variable.value
                        variable.for_python = variable.value
                        self.update_off()
                        table_item.setText(str(variable.value))
                        self.update_on()
                        # update.digital_analog_dds_mirny_tabs(self)
                        update.variable_tables(self)
                        update.all_values(self)
                        if variable.name == "T_exp_":
                            self._sync_camera_exposure_from_variable()
                    else: #The value can not be updated, reverting every evaluation done before.
                        self.error_message("Evaluation is out of allowed range occured in %s. Variable value can not be assigned" %return_value, "Wrong entry")
                        self.experiment.variables[variable.name].value = variable.value 
                        self.experiment.variables[variable.name].for_python = variable.value
                        self.update_off()
                        table_item.setText(str(variable.value))
                        self.update_on()
                        update.variable_tables(self)
                        update.all_values(self)
                        if variable.name == "T_exp_":
                            self._sync_camera_exposure_from_variable()
                        

                except: #Restricting the user from using anything but the integer values and floating numbers
                    self.update_off()
                    table_item.setText(str(variable.value))
                    self.update_on()
                    # update.digital_analog_dds_mirny_tabs(self, update_expressions_and_evaluations=False)   
                    update.variable_tables(self)
                      
                    update.all_values(self)              
                    self.error_message("Only integers and floating numbers are allowed.", "Wrong entry")
                    if variable.name == "T_exp_":
                        self._sync_camera_exposure_from_variable()

            




    def find_derived_variable_name_unused(self):
        '''
        Function itereates over the variable names of form derived_1, derived_2, etc. and returns the lowest available variable name
        '''
        for i in range(1, 1000):
            name = "derived_" + str(i)
            if name not in self.experiment.names_of_derived_variables:
                return name





    def create_derived_variable_button_clicked(self):
        '''
        Function is used when the user wants to create a new derived variable. It finds the lowest unused available variable name and 
        creates it. It also create the corresponding derived Variable objects  in the list derived variables.
        '''
        variable_name = self.find_derived_variable_name_unused()
        self.experiment.names_of_derived_variables.add(variable_name)
        self.experiment.derived_variables.append(self.Derived_variable(name = variable_name, edge_id = "", arguments = "", function = "", initial_value = ""))
        self.experiment.variables[variable_name] = self.Variable(name = variable_name, value = 0.0, for_python = 0.0, is_derived = True)
        update.variables_tab(self, new_variables = False, lookup_variables = False)





    def find_lookup_variable_name_unused(self):
        '''
        Function itereates over the variable names of form derived_1, derived_2, etc. and returns the lowest available variable name
        '''
        for i in range(1, 1000):
            name = "lookup_" + str(i)
            if name not in self.experiment.names_of_lookup_variables:
                return name





    def create_lookup_variable_button_clicked(self):
        '''
        Function is used when the user wants to create a new lookup variable. It finds the lowest unused available variable name and 
        creates it. It also create the corresponding Variable objects  in new_variables and variables.
        '''
        variable_name = self.find_lookup_variable_name_unused()
        self.experiment.names_of_lookup_variables.add(variable_name)
        self.experiment.lookup_variables.append(self.Lookup_variable(name = variable_name))
        self.experiment.variables[variable_name] = self.Variable(name = variable_name, value = 0.0, for_python = 0.0, is_lookup = True)
        update.variables_tab(self, new_variables = False, derived_variables = False)





    def find_edge_index_by_id(self, id):
        '''
        Function is used to find the index of the edge by its id value. It iterates over all edges and returns the 
        index when the id matches the edge.id
        '''
        for index, edge in enumerate(self.experiment.sequence):
            if edge.id == id:
                return index





    def delete_derived_variable_button_clicked(self):
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





    def load_lookup_list_button_clicked(self):
        try:
            row = self.lookup_variables_table.selectedIndexes()[0].row()
            lookup_variable = self.experiment.lookup_variables[row-1]
            if row == 0: # Default edge
                self.error_message("You can not modify dummy variable", "Wrong variable")    
            else: # Allowed look up variable was selected
                loaded_file_path = QFileDialog.getOpenFileName(self, "Open File")[0]
                loaded_file_name = loaded_file_path.split("/")[-1]
                if loaded_file_path != "": #happens when no file name was given (canceled)
                    try:
                        lookup_variable.lookup_list = list(loadmat(loaded_file_path)['array'][0])
                        lookup_variable.lookup_list_name = loaded_file_name
                        self.update_off()
                        self.lookup_variables_table.item(row, 2).setText(loaded_file_name)
                        self.update_on()
                    except:
                        self.error_message('Could not load the file.', 'Error')
        except:
            self.error_message("Select the lookup variable you want to load the lookup list for", "No variable selected selected")
        




    def delete_lookup_variable_button_clicked(self):
        '''
        Function is used when the user wants to delete the lookup variable from the table.
        '''
        try:
            row = self.lookup_variables_table.selectedIndexes()[0].row()
            if row == 0:
                self.error_message("You can not delete a dummy example", "Protected variable")
            else:
                name = self.lookup_variables_table.item(row,0).text()
                self.experiment.names_of_lookup_variables.remove(name)
                del self.experiment.lookup_variables[row-1] # -1 is due to the dummy variable taking the first row
                del self.experiment.variables[name]
                self.lookup_variables_table.setCurrentCell(row-1, 0)
                update.variables_tab(self, new_variables = False, derived_variables = False)
        except: #In case the user pressed delete variable button without selecting the variable that needs to be deleted
            self.error_message("Select the variable that needs to be deleted", "No variable selected")





    def derived_variables_table_changed(self, item):
        '''
        Function is used when the user changes the values in the derived variables table. 
        '''
        if self.to_update:
            row = item.row()
            col = item.column()
            variable = self.experiment.derived_variables[row-1] # due to the dummy variable being 1st
            table_item_text = self.derived_variables_table.item(row,col).text().replace(" ","")
            self.update_off()
            self.derived_variables_table.item(row,col).setText(table_item_text)
            self.update_on()
            if col == 0: #Variable name was changed
                if table_item_text not in self.experiment.variables:
                    backup = deepcopy(self.experiment.variables[variable.name])
                    del self.experiment.variables[variable.name]
                    return_value = update.digital_analog_dds_mirny_tabs(self)
                    if return_value == None: #The previous variable was not used and the name can be changed
                        self.experiment.names_of_derived_variables.remove(variable.name)
                        self.experiment.names_of_derived_variables.add(table_item_text)
                        backup.name = table_item_text
                        variable.name = table_item_text
                        self.experiment.variables[backup.name] = backup
                    else: #The previous variable was used and the name can not be changed
                        self.error_message("The variable is used in %s"%return_value, "Used variable")
                        self.experiment.variables[backup.name] = backup
                        self.update_off()
                        self.derived_variables_table.item(row,col).setText(backup.name)
                        self.update_on()
                else:
                    self.error_message("Variable name is already used", "Wrong variable name")
                    self.update_off()
                    self.derived_variables_table.item(row,col).setText(self.experiment.derived_variables[row-1].name)
                    self.update_on()
            if col == 1: #Variable arguments were changed
                #Checking if the variables in the arguments are sampled variables
                arguments = table_item_text.split(",")
                not_a_sampled_variable = False
                for argument in arguments:
                    if argument not in self.experiment.sampler_variables:
                        not_a_sampled_variable = True
                        #break
                    if argument in self.experiment.names_of_derived_variables:
                        not_a_sampled_variable = False                        
                        break
                if not_a_sampled_variable: #Reverting back the Arguments table entry
                    self.error_message("Arguments include not sampled variables. First create variables in variables tab and then add them to the sampler to make them sampled","Not sampled arguments")
                    self.update_off()
                    self.derived_variables_table.item(row,col).setText(self.experiment.derived_variables[row-1].arguments)
                    self.update_on()
                else:
                    variable.arguments = table_item_text
            if col == 2: #Variable execution edge was changed
                new_edge_id = table_item_text
                if self.find_edge_index_by_id(new_edge_id) == None:
                    self.error_message("The edge id was not found. Please enter correct id value", "Wrong id entered")
                    self.update_off()
                    self.derived_variables_table.item(row,col).setText(variable.edge_id)
                    self.update_on()
                elif new_edge_id == "id0":
                    self.error_message("User is restricted from using id0 for requesting derivation of variable. All other edges are allowed.","Default edge!")
                    self.update_off()
                    self.derived_variables_table.item(row,col).setText(variable.edge_id)
                    self.update_on()
                else:
                    if variable.edge_id != "":  #In case it was another id before we need to make that edge.derived_variable_requested to 0 which means that it is not requested
                        edge_index = self.find_edge_index_by_id(variable.edge_id)
                        self.experiment.sequence[edge_index].derived_variable_requested = -1
                    #Assigning the edge.derived_variable_requested value 
                    variable.edge_id = table_item_text
                    edge_index = self.find_edge_index_by_id(variable.edge_id)
                    self.experiment.sequence[edge_index].derived_variable_requested = row-1 # -1 because the dummy variable is the first one
            if col == 3: #Variable function was changed
                variable.function = table_item_text
            if col == 4: 
                variable.initial_value = table_item_text
                if variable.name in self.experiment.variables:
                    #print("in loop", vars(self.experiment.variables[variable.name]))
                    self.update_off()
                    if variable.initial_value == "":
                        self.experiment.variables[variable.name].value = (variable.initial_value)
                        self.update_on()
                    else: 
                        self.experiment.variables[variable.name].value = float(variable.initial_value)
                        self.update_on()
                #print(vars(self.experiment.variables[variable.name]))





    def lookup_variables_table_changed(self, item):
        '''
        Function is used when the user changes the values in the lookup variables table. 
        '''
        if self.to_update:
            row = item.row()
            col = item.column()
            variable = self.experiment.lookup_variables[row-1] # due to the dummy variable being 1st
            table_item_text = self.lookup_variables_table.item(row,col).text().replace(" ","")
            self.update_off()
            self.lookup_variables_table.item(row,col).setText(table_item_text)
            self.update_on()
            if col == 0: #Variable name was changed
                if table_item_text not in self.experiment.variables:
                    backup = deepcopy(self.experiment.variables[variable.name])
                    del self.experiment.variables[variable.name]
                    return_value = update.digital_analog_dds_mirny_tabs(self)
                    if return_value == None: #The previous variable was not used and the name can be changed
                        self.experiment.names_of_lookup_variables.remove(variable.name)
                        self.experiment.names_of_lookup_variables.add(table_item_text)
                        backup.name = table_item_text
                        variable.name = table_item_text
                        self.experiment.variables[backup.name] = backup
                    else: #The previous variable was used and the name can not be changed
                        self.error_message("The variable is used in %s"%return_value, "Used variable")
                        self.experiment.variables[backup.name] = backup
                        self.update_off()
                        self.lookup_variables_table.item(row,col).setText(backup.name)
                        self.update_on()
                else:
                    self.error_message("Variable name is already used", "Wrong variable name")
                    self.update_off()
                    self.lookup_variables_table.item(row, col).setText(self.experiment.lookup_variables[row-1].name)
                    self.update_on()
            if col == 1: #Variable argument was changed
                #Checking if the variable in the argument is a sampled variable
                if table_item_text not in self.experiment.sampler_variables:
                    self.error_message("Argument include not sampled variable. First create a variable in variables tab and then add it in the sampler to make it sampled", "Not sampled argument")
                    self.update_off()
                    self.lookup_variables_table.item(row, col).setText(self.experiment.lookup_variables[row-1].argument)
                    self.update_on()
                else:
                    variable.argument = table_item_text
                    self.experiment.variables[variable.name].argument = table_item_text





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





    def sampler_table_changed(self, item):
        '''
        Function is used when the user changes the values in the sampler table. It ensures that the expressions are integer values
        0 or variable name defined in variables tab. The user can delete the input and the function will assign the value to 0 and unhighlight the channel
        '''
        if self.to_update:
            row = item.row()
            col = item.column()
            table_item = self.sampler_table.item(row, col)
            table_entry = self.sampler_table.item(row,col).text()
            channel = self.experiment.sequence[row].sampler[col-4] # channel is a variable name or 0
            #Checking if the variable is used in derived variables table as an argument
            not_in_derived_variables = True
            for derived_variable in self.experiment.derived_variables:
                arguments = derived_variable.arguments.split(",")
                for argument in arguments:
                    if channel == argument:
                        not_in_derived_variables = False
                        break
            if not_in_derived_variables:
                not_in_lookup_variables = True
                #Checking if the variable is used in lookup variables
                for lookup_variable in self.experiment.lookup_variables:
                    if channel == lookup_variable.argument:
                        not_in_lookup_variables = False
                        break
                if not_in_lookup_variables:
                    if table_entry == "" or table_entry == "0" or table_entry == "0.0": #User deleted the value or set it to 0. The function will assign 0 value
                        if channel in self.experiment.sampler_variables: #if the previous value of the sampler was a variable we need to revert back the variables tab value and activate editing
                            self.experiment.sampler_variables.remove(channel)
                            update.variables_tab(self, derived_variables = False)
                        self.update_off()
                        table_item.setText("0")
                        self.update_on()
                    else: #User attempted to assign a variable name to the sampler input
                        if table_entry in self.experiment.variables: #Check if the variable name is defined in the variables tab
                            if self.experiment.variables[table_entry].is_scanned == False and self.experiment.variables[table_entry].is_ramped == False: #Check if the variable name is not scanned
                                if table_entry not in self.experiment.sampler_variables:
                                    #Remove the previous variable from the sampler variables if it was not 0 before the human entry
                                    if channel in self.experiment.sampler_variables:
                                        self.experiment.sampler_variables.remove(channel)
                                    self.experiment.sequence[row].sampler[col-4] = table_entry #Updating the sampler value
                                    self.experiment.sampler_variables.add(table_entry) #Adding a new variable to the sampler variables set
                                    update.variables_tab(self, derived_variables = False)
                                else:
                                    self.update_off()
                                    table_item.setText(str(channel))
                                    self.update_on()
                                    self.error_message("Variable you entered is already used in sampler. Duplicates are not allowed.", "Reuse of the variable")        
                            else:
                                self.update_off()
                                table_item.setText(str(channel))
                                self.update_on()
                                self.error_message("Variable you entered is in the Scan or Ramp table. First remove it from there.", "Scanned / Ramped variable")
                        else:
                            self.update_off()
                            table_item.setText(str(channel))
                            self.update_on()
                            self.error_message("Variable you entered is not found in the variables table. First create the variable there.", "No variable found")
                    update.sampler_tab(self) 
                    update.digital_analog_dds_mirny_tabs(self) 
                else:
                    self.error_message("Variable is used in a lookup variables table as an argument. First remove it from all lookup variable arguments", "Used sampled variable")
                    self.update_off()
                    table_item.setText(channel)
                    self.update_on()
            else:
                self.error_message("Variable is used in a derived variables table as an argument. First remove it from all derived variable arguments", "Used sampled variable")
                self.update_off()
                table_item.setText(channel)
                self.update_on()

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

    def update_chosen_experiment(self):
        with open(self.repo_path / "experiment_specific_files" / config.which_project / "experiment_names.json", 'r') as f:
            data = json.load(f)

        row = self.experiment_list_list_widget.currentRow()

        if row < 0:
            self.experiment_list_btn_delete.setEnabled(False)
            self.experiment_list_chosen_line.clear()
            self.experiment_list_chosen_line_caption.clear()
            self.experiment.experimental_data.experiment_name = ''
            self.experiment.experimental_data.comment = ''
            self.experiment.experimental_data.path = ''
            self.experiment.experimental_data.experiment_id = ''
            return

        self.experiment_list_btn_delete.setEnabled(len(self.experiment_list_list_widget.selectedItems()) > 0)
        # items = self.experiment_list_list_widget.selectedItems()
        key = f"{int(row)}"
        if key not in data:
            self.message_to_logger(f"Experiment entry with key {key} was not found in experiment_names.json")
            return

        name = data[key]["name"]
        caption = data[key]["plot_x_caption"]

        base_path = getattr(config, "experiment_data_root", "")
        if base_path:
            self.experiment.experimental_data.path = str(Path(base_path) / name)
        else:
            self.experiment.experimental_data.path = ""
        self.experiment_list_chosen_line.setText(name)
        self.experiment_list_chosen_line_caption.setText(caption)
        self.experiment.experimental_data.experiment_name = name
        self.experiment.experimental_data.comment = caption
        self.experiment.experimental_data.experiment_id = int(row)

    def experiment_caption_changed(self):
        self.dialog = QDialog()
        self.dialog.setGeometry(*self.scale_geom(710, 435, 600, 200))
        self.dialog.setFont(QFont('Arial', self.scale_font(14)))
        # value_input = QLineEdit()
        # value_input.setPlaceholderText("Type the name of new experiment")
        value_input_cap = QLineEdit()
        value_input_cap.setPlaceholderText("Type the x-caption for the experiment (Example: 'TOF, ms')")
        dialog_layout = QVBoxLayout()
        button_update = QPushButton("Update")
        button_cancel = QPushButton("Cancel")
        # dialog_layout.addWidget(value_input)
        dialog_layout.addWidget(value_input_cap)
        dialog_buttons_layout = QHBoxLayout()
        dialog_buttons_layout.addWidget(button_update)
        dialog_buttons_layout.addWidget(button_cancel)
        dialog_layout.addLayout(dialog_buttons_layout)
        self.dialog.setLayout(dialog_layout)

        button_update.clicked.connect(lambda:self.update_experiment_names_list(caption = value_input_cap.text(),last = False))
        button_cancel.clicked.connect(lambda:self.dialog.reject())
        self.dialog.setWindowTitle("Change experiment caption") 
        self.dialog.exec_()


    def update_experiment_names_list(self,name = '',caption = '',last = True):
        
        with open(self.repo_path / "experiment_specific_files" / config.which_project / "experiment_names.json", 'r') as f:
            data = json.load(f)

        if last == True:

            last_key = list(data.keys())[-1]

            
            data[f"{int(last_key) + 1}"] = {}
            data[f"{int(last_key) + 1}"]["name"] = name
            data[f"{int(last_key) + 1}"]["plot_x_caption"] = caption

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


        with open(self.repo_path / "experiment_specific_files" / config.which_project / "experiment_names.json", 'w') as f:
            json.dump(data,f,indent = 4)
        # update.acquisition_tab(self)
        




    def add_element_experiment_list_button_clicked(self):
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

    def delete_element_experiment_list_button_clicked(self):
        # sender = self.sender()

        row = self.experiment_list_list_widget.currentRow()

        with open(self.repo_path / "experiment_specific_files" / config.which_project / "experiment_names.json", 'r') as f:
            data = json.load(f)

            del data[f"{int(row)}"]

        
        with open(self.repo_path / "experiment_specific_files" / config.which_project / "experiment_names.json", 'w') as f:
            json.dump(data,f,indent = 4)

        self.experiment_list_list_widget.takeItem(row)
        # update.acquisition_tab(self)


    def _ensure_camera_experiment_selected(self):
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


    def _prepare_camera_launch(self):
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
        self.experiment.experimental_data.camera.exposure_time = exposure_value
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

        return {
            "argv": argv,
            "cwd": str(camera_script.parent),
            "output_dir": str(run_directory),
            "metadata_dir": str(run_base_dir),
            "timestamp": timestamp.isoformat()
        }


    def _start_camera_subprocess(self, launch_info):
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

        thread = threading.Thread(target=runner, daemon=True)
        thread.start()
        return thread


    def _start_artiq_thread(self, delay_s=0.0, run_continuous=False):
        delay_seconds = float(delay_s) if delay_s else 0.0

        if config.package_manager == "conda":
            command = f"conda activate {config.artiq_environment_name} && artiq_run ../ARTIQ_scripts/run_experiment.py"

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

        thread = threading.Thread(target=runner, daemon=True)
        thread.start()
        return thread


    def _record_experiment_run(self, metadata_dir, *, is_multiple_run=False):
        db_path = getattr(config, "experiment_database_path", "")
        if not db_path:
            return
        try:
            openpyxl_module = importlib.import_module("openpyxl")
        except ImportError:
            if not self._openpyxl_missing_warned:
                self.message_to_logger("openpyxl not installed - experiment log will not be updated.")
                self._openpyxl_missing_warned = True
            return

        Workbook = getattr(openpyxl_module, "Workbook", None)
        load_workbook = getattr(openpyxl_module, "load_workbook", None)
        if Workbook is None or load_workbook is None:
            if not self._openpyxl_missing_warned:
                self.message_to_logger("openpyxl is missing workbook support - experiment log updates disabled.")
                self._openpyxl_missing_warned = True
            return

        try:
            data_validation_module = importlib.import_module("openpyxl.worksheet.datavalidation")
            DataValidation = getattr(data_validation_module, "DataValidation", None)
        except ImportError:
            DataValidation = None

        try:
            utils_module = importlib.import_module("openpyxl.utils")
            get_column_letter = getattr(utils_module, "get_column_letter", None)
        except ImportError:
            get_column_letter = None

        try:
            styles_module = importlib.import_module("openpyxl.styles")
            PatternFill = getattr(styles_module, "PatternFill", None)
            Font = getattr(styles_module, "Font", None)
            Alignment = getattr(styles_module, "Alignment", None)
            Border = getattr(styles_module, "Border", None)
            Side = getattr(styles_module, "Side", None)
        except ImportError:
            PatternFill = None
            Font = None
            Alignment = None
            Border = None
            Side = None
        if Border is None or Side is None:
            try:
                borders_module = importlib.import_module("openpyxl.styles.borders")
                Border = getattr(borders_module, "Border", Border)
                Side = getattr(borders_module, "Side", Side)
            except ImportError:
                Border = Border or None
                Side = Side or None

        desired_headers = [
            "Date\n(dd.mm.yyyy)",
            "Experiment",
            "Time",
            "Scanned variable",
            "Scan range",
            "Scan steps",
            "Number of runs",
            "Good data\n(Y/N)",
            "Data path",
            "Comment"
        ]
        default_column_width = 25
        row_height = 20
        header_row_height = 30
        header_aliases = {
            "Scanned variables": "Scanned variable",
            "Scan ranges": "Scan range",
            "Comments": "Comment",
            "Date (dd.mm.yyyy)": "Date\n(dd.mm.yyyy)",
            "Good data (Y/N)": "Good data\n(Y/N)"
        }

        metadata_path = Path(metadata_dir)
        db_file = Path(db_path)
        try:
            db_file.parent.mkdir(parents=True, exist_ok=True)
            if db_file.exists():
                workbook = load_workbook(db_file)
                sheet = workbook.active
            else:
                workbook = Workbook()
                sheet = workbook.active
                sheet.title = "Experiments"

        except Exception as exc:
            self.message_to_logger(f"Could not update experiment log: {exc}")
            return

        def restructure_sheet_if_needed():
            existing_headers = []
            if sheet.max_row >= 1:
                existing_headers = [cell.value if cell.value is not None else "" for cell in sheet[1]]
            if not any(existing_headers):
                if sheet.max_row:
                    sheet.delete_rows(1, sheet.max_row)
                sheet.append(desired_headers)
                return
            if existing_headers == desired_headers:
                return
            rows_snapshot = []
            for row in sheet.iter_rows(min_row=2):
                info = {}
                for idx, cell in enumerate(row):
                    header_key = existing_headers[idx] if idx < len(existing_headers) else f"__extra_{idx}"
                    canonical_key = header_aliases.get(header_key, header_key)
                    info[canonical_key] = (cell.value, cell.hyperlink.target if cell.hyperlink else None)
                rows_snapshot.append(info)
            sheet.delete_rows(1, sheet.max_row)
            sheet.append(desired_headers)

            def get_value(info, key, default=""):
                packed = info.get(key)
                if packed is None:
                    return default
                value, _ = packed
                return value if value is not None else default

            def get_link(info, key):
                packed = info.get(key)
                if packed is None:
                    return None
                _, link = packed
                return link

            for stored in rows_snapshot:
                row_values = [
                    get_value(stored, "Date\n(dd.mm.yyyy)"),
                    get_value(stored, "Experiment"),
                    get_value(stored, "Time"),
                    get_value(stored, "Scanned variable"),
                    get_value(stored, "Scan range"),
                    get_value(stored, "Scan steps"),
                    get_value(stored, "Number of runs"),
                    get_value(stored, "Good data\n(Y/N)"),
                    "path",
                    get_value(stored, "Comment")
                ]
                sheet.append(row_values)
                current_row = sheet.max_row
                date_cell_snapshot = sheet.cell(row=current_row, column=1)
                if isinstance(date_cell_snapshot.value, (datetime, date)):
                    date_cell_snapshot.number_format = "dd.mm.yyyy"
                link_target = get_link(stored, "Data path")
                if not link_target:
                    link_target = get_value(stored, "Data path")
                if link_target:
                    data_cell = sheet.cell(row=current_row, column=9)
                    data_cell.value = "path"
                    data_cell.hyperlink = link_target
                    data_cell.style = "Hyperlink"
                sheet.row_dimensions[current_row].height = row_height

        restructure_sheet_if_needed()

        header_fill = PatternFill(fill_type="solid", fgColor="D9D9D9") if PatternFill else None
        header_font = Font(bold=True) if Font else None
        header_alignment = Alignment(horizontal="center", vertical="center", wrap_text=True) if Alignment else None
        header_border_side = Side(style="thin", color="000000") if Side else None

        for idx, header in enumerate(desired_headers, start=1):
            cell = sheet.cell(row=1, column=idx, value=header)
            if header_font:
                cell.font = header_font
            if header_fill:
                cell.fill = header_fill
            if header_alignment:
                cell.alignment = header_alignment
            if Border and header_border_side:
                cell.border = Border(
                    left=header_border_side,
                    right=header_border_side,
                    top=header_border_side,
                    bottom=header_border_side
                )

        if get_column_letter is not None:
            width_map = {
                1: 14,  # Date
                3: 10,  # Time
                5: 20,  # Scan range
                6: 16,  # Scan points number
                7: 16,  # Number of runs
                8: 10,  # Good data
                9: 10,  # Data path
                10: 40  # Comment
            }
            for col_idx in range(1, len(desired_headers) + 1):
                column_letter = get_column_letter(col_idx)
                width = width_map.get(col_idx, default_column_width)
                sheet.column_dimensions[column_letter].width = width

        sheet.row_dimensions[1].height = header_row_height
        sheet.freeze_panes = "A2"

        timestamp_iso = getattr(self.experiment.experimental_data, "current_run_timestamp", "")
        try:
            run_ts = datetime.fromisoformat(timestamp_iso) if timestamp_iso else datetime.now()
        except ValueError:
            run_ts = datetime.now()

        experiment_name = getattr(self.experiment.experimental_data, "experiment_name", "") or ""
        date_value = run_ts.date()
        time_value = run_ts.time().replace(microsecond=0)

        scanned_variables = []
        scan_ranges = []
        for variable in getattr(self.experiment, "scanned_variables", []):
            name = getattr(variable, "name", "")
            if name and name != "None":
                scanned_variables.append(str(name))
                min_val = getattr(variable, "min_val", "")
                max_val = getattr(variable, "max_val", "")
                scan_ranges.append(f"{min_val} -> {max_val}")

        scan_points = 1
        if getattr(self.experiment, "do_scan", False) and getattr(self.experiment, "scanned_variables_count", 0) > 0:
            try:
                scan_points = int(getattr(self.experiment, "number_of_steps", 1))
            except (TypeError, ValueError):
                scan_points = 1
            if scan_points <= 0:
                scan_points = 1

        number_of_runs_value = getattr(self.experiment, "number_of_runs", 1)
        try:
            number_of_runs_value = int(number_of_runs_value)
        except (TypeError, ValueError):
            number_of_runs_value = 1
        if number_of_runs_value <= 0:
            number_of_runs_value = 1
        if not is_multiple_run:
            number_of_runs_value = 1

        pending_entries = self._load_pending_log_entries()

        current_entry = {
            "date": date_value.isoformat(),
            "experiment": experiment_name,
            "time": time_value.strftime("%H:%M:%S"),
            "scanned_variables": scanned_variables,
            "scan_ranges": scan_ranges,
            "scan_points": int(scan_points),
            "number_of_runs": int(number_of_runs_value),
            "good_data": "",
            "metadata_path": str(metadata_path),
            "comment": ""
        }

        entries_to_write = list(pending_entries)
        entries_to_write.append(current_entry)

        def append_entry_to_sheet(entry_dict):
            date_field = entry_dict.get("date")
            if isinstance(date_field, date):
                date_obj = date_field
            elif isinstance(date_field, datetime):
                date_obj = date_field.date()
            elif isinstance(date_field, str):
                try:
                    date_obj = date.fromisoformat(date_field)
                except ValueError:
                    try:
                        date_obj = datetime.fromisoformat(date_field).date()
                    except ValueError:
                        date_obj = datetime.now().date()
            else:
                date_obj = datetime.now().date()

            time_field = entry_dict.get("time")
            if isinstance(time_field, datetime):
                time_obj = time_field.time().replace(microsecond=0)
            elif isinstance(time_field, str):
                try:
                    time_obj = datetime.strptime(time_field, "%H:%M:%S").time()
                except ValueError:
                    try:
                        time_obj = datetime.fromisoformat(time_field).time()
                    except ValueError:
                        time_obj = time_field
            else:
                time_obj = time_field if time_field else datetime.now().time().replace(microsecond=0)

            scanned_field = entry_dict.get("scanned_variables", [])
            if isinstance(scanned_field, (list, tuple)):
                scanned_str = "; ".join(str(item) for item in scanned_field if item not in (None, ""))
            else:
                scanned_str = str(scanned_field) if scanned_field is not None else ""

            range_field = entry_dict.get("scan_ranges", [])
            if isinstance(range_field, (list, tuple)):
                ranges_str = "; ".join(str(item) for item in range_field if item not in (None, ""))
            else:
                ranges_str = str(range_field) if range_field is not None else ""

            scan_points_field = entry_dict.get("scan_points", 1)
            try:
                scan_points_value = int(scan_points_field)
            except (TypeError, ValueError):
                scan_points_value = 1
            if scan_points_value <= 0:
                scan_points_value = 1

            number_of_runs_field = entry_dict.get("number_of_runs", 1)
            try:
                number_of_runs_int = int(number_of_runs_field)
            except (TypeError, ValueError):
                number_of_runs_int = 1
            if number_of_runs_int <= 0:
                number_of_runs_int = 1

            good_data_value = entry_dict.get("good_data", "") or ""
            comment_value = entry_dict.get("comment", "") or ""
            metadata_value = entry_dict.get("metadata_path", "")

            row_values_local = [
                date_obj,
                entry_dict.get("experiment", ""),
                time_obj,
                scanned_str,
                ranges_str,
                scan_points_value,
                number_of_runs_int,
                good_data_value,
                "path" if metadata_value else "",
                comment_value
            ]

            sheet.append(row_values_local)
            row_index = sheet.max_row
            date_cell_local = sheet.cell(row=row_index, column=1)
            if isinstance(date_cell_local.value, (datetime, date)):
                date_cell_local.number_format = "d.m.yyyy"
            if metadata_value:
                data_cell_local = sheet.cell(row=row_index, column=9)
                data_cell_local.value = "path"
                data_cell_local.hyperlink = metadata_value
                data_cell_local.style = "Hyperlink"
            sheet.row_dimensions[row_index].height = row_height

        for entry_dict in entries_to_write:
            append_entry_to_sheet(entry_dict)

        if DataValidation is not None:
            target_range = "H2:H1048576"
            existing_range = False
            if hasattr(sheet, "data_validations"):
                for dv in sheet.data_validations.dataValidation:
                    if any(str(rng) == target_range for rng in dv.ranges):
                        existing_range = True
                        break
            if not existing_range:
                dv = DataValidation(type="list", formula1='"[ ],[x]"', allow_blank=True)
                dv.error = "Select [x] once the dataset is validated."
                dv.prompt = "Switch to [x] when the run produced good data."
                sheet.add_data_validation(dv)
                dv.add(target_range)

        for row_idx in range(2, sheet.max_row + 1):
            sheet.row_dimensions[row_idx].height = row_height

        try:
            workbook.save(db_file)
        except PermissionError:
            self._set_pending_log_entries(entries_to_write)
            self.message_to_logger("Experiment log update deferred: close the Excel workbook to allow writing. Pending entries will be retried automatically.")
            return
        except Exception as exc:
            self._set_pending_log_entries(entries_to_write)
            self.message_to_logger(f"Could not update experiment log (will retry later): {exc}")
            return

        if pending_entries:
            self.message_to_logger("Previously pending experiment log entries were written to the log file.")
        self._set_pending_log_entries([])


    def _pending_log_entries_path(self):
        return self.repo_path / "logs" / "pending_experiment_log_entries.json"


    def _load_pending_log_entries(self):
        if hasattr(self, "_pending_log_entries_cache"):
            return list(self._pending_log_entries_cache)

        path = self._pending_log_entries_path()
        entries = []
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as handle:
                    data = json.load(handle)
                    if isinstance(data, list):
                        entries = data
            except Exception as exc:
                self.message_to_logger(f"Could not read pending experiment log entries: {exc}")
        self._pending_log_entries_cache = entries
        return list(entries)


    def _set_pending_log_entries(self, entries):
        entries_list = list(entries)
        self._pending_log_entries_cache = entries_list
        path = self._pending_log_entries_path()
        try:
            if entries_list:
                path.parent.mkdir(parents=True, exist_ok=True)
                with open(path, "w", encoding="utf-8") as handle:
                    json.dump(entries_list, handle, indent=2)
            else:
                if path.exists():
                    path.unlink()
        except Exception as exc:
            self.message_to_logger(f"Could not update pending experiment log file: {exc}")


    def camera_which_cam_changed(self):
        text_ = self.which_cam_combo.currentText()
        self.experiment.experimental_data.camera.camera_name = text_
        serial_number = config.camera_serial_numbers_dict.get(text_)
        self.experiment.experimental_data.camera.serial_number = serial_number if serial_number is not None else ''


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
            self.experiment.experimental_data.camera.exposure_time = texp_var.value
            self._set_camera_exposure_line(texp_var.value)

    def _handle_texp_lock_toggled(self, locked):
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
                        item.setBackground(self.light_grey)
                    else:
                        if current_flags != Qt.NoItemFlags:
                            item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled | Qt.ItemIsEditable)
                        item.setBackground(self.white)
        finally:
            self.to_update = previous_update_state
            self._updating_texp_lock = False

    def camera_gain_changed(self):
        gain_text = self.gain_edit.text().strip()
        previous_gain = self.experiment.experimental_data.camera.gain_db
        if gain_text == "":
            self.error_message("Gain cannot be empty", "Wrong entry")
            self.gain_edit.setText(str(previous_gain))
            return
        try:
            gain_value = float(gain_text)
        except ValueError:
            self.error_message("Gain must be a number", "Wrong entry")
            self.gain_edit.setText(str(previous_gain))
            return

        self.experiment.experimental_data.camera.gain_db = gain_value
        self.gain_edit.setText(str(gain_value))


    def camera_exposure_changed(self):
        texp_key = "T_exp_"
        texp_str = self.exposure_edit.text().strip()
        if texp_str == "":
            self.error_message("Exposure time cannot be empty", "Wrong entry")
            self._set_camera_exposure_line(self.experiment.experimental_data.camera.exposure_time)
            return
        try:
            texp_ = float(texp_str)
        except ValueError:
            self.error_message("Exposure time must be a number", "Wrong entry")
            self._set_camera_exposure_line(self.experiment.experimental_data.camera.exposure_time)
            return

        self.experiment.experimental_data.camera.exposure_time = texp_
        self._set_camera_exposure_line(texp_)

        index = self._get_texp_variable_index()
        if index is None:
            variable = self.Variable(texp_key, texp_, texp_)
            self.experiment.variables[texp_key] = variable
            self.experiment.new_variables.append(variable)
        else:
            variable = self.experiment.new_variables[index]
            variable.value = texp_
            variable.for_python = texp_
            self.experiment.variables[texp_key].value = texp_
            self.experiment.variables[texp_key].for_python = texp_

        update.variable_tables(self)

        
        


    def camera_image_format_changed(self):
        self.experiment.experimental_data.camera.format_name = self.format_combo.currentText()




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