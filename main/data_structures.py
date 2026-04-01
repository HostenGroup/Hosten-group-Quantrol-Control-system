'''
Data structures for Quantrol experimental sequences.

This module contains all the core data classes used to represent experiments,
time edges, channel states, variables, and hardware configurations.

Author  :   Alexei Gurchenko (refactored from source_code.py)
Email   :   alexei.gurchenko@ist.ac.at
Date    :   11.2025
Version :   2.3.3
Contact :   https://hostenlab.pages.ist.ac.at/contact/
'''

import threading
import config





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
        self.slow_dds = [SlowDDS() for i in range(config.slow_dds_channels_number)]



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
        self.digital = [Digital() for i in range(config.digital_channels_number)]
        self.analog = [Analog() for i in range(config.analog_channels_number)]
        self.dds = [DDS() for i in range(config.dds_channels_number)]
        self.mirny = [DDS(is_mirny = True) for i in range(config.mirny_channels_number)]
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


class DDSParameter:
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
    def __init__(self, expression = "0.0", evaluation = 0.0, value = 0.0, changed = True, 
                 is_scanned = False, is_ramped = False, is_sampled = False, 
                 is_derived = False, is_lookup = False):
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
            self.frequency = DDSParameter(expression = "55.0", evaluation = 55.0, value = 55.0)
            self.amplitude = DDSParameter(expression = "5.0", evaluation = 5.0, value = 5.0)
        else:
            self.frequency = DDSParameter()
            self.amplitude = DDSParameter()
        self.phase = DDSParameter()
        self.attenuation = DDSParameter()
        self.state = DDSParameter()
        self.changed = changed





class SlowDDS:
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
    def __init__(self, path=None, experiment_name=None, comment=None, experiment_id=None):
        self.path = path
        self.experiment_name = experiment_name
        self.comment = comment
        self.experiment_id = experiment_id



class DerivedVariable:
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


class LookupVariable:
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


class ScannedVariable:
    '''
    An object that is used to describe the scanned variable parameters
    Attributes description:
        name        :   Name of the scanned variable
        min_val     :   Minimum value assigned to the scanned variable
        max_val     :   Maximum value assigned to the scanned variable
    ''' 
    def __init__(self, name, min_val, max_val, num_scan_steps, Dim=None):
        self.name = name
        self.min_val = min_val
        self.max_val = max_val
        # check if num_scan_steps is a positive integer, otherwise default to 1
        try:
            self.num_scan_steps = int(num_scan_steps)
            if self.num_scan_steps <= 0:
                self.num_scan_steps = 1
        except Exception:
            self.num_scan_steps = 1
        # Dim: integer ordering for scanned variables. None means "use list order".
        try:
            self.Dim = None if Dim is None else int(Dim)
            if self.Dim is not None and self.Dim <= 0:
                self.Dim = None
        except Exception:
            self.Dim = None


class RampedVariable: 
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
    def __init__(self, name, value, for_python, is_scanned = False, is_ramped = False, 
                 is_sampled = False, is_derived = False, is_lookup = False): 
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
    An object that is used to describe camera configuration
    '''
    def __init__(self, gain_db=None, format_name=None, 
                 exposure_time_ms=None, serial_number=None, 
                 camera_name=None):
        self.gain_db = gain_db
        self.format_name = format_name
        self.exposure_time_ms = exposure_time_ms
        self.serial_number = serial_number
        self.camera_name = camera_name
