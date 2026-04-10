import os
from sympy import simplify
import config 
from scipy.io import savemat
from datetime import datetime
from update import closest_key


def create_experiment(self, run_continuous = False, multiple_runs = False):
    '''
    Function is used to create the description of the experimental sequence.   
    Python like description is saved as run_experiment.py
    run_continuous is used as a flag to indicate if the continuous run is required.
    '''
    #CREATING A FILE
    file_name = "run_experiment.py"
    file_path = self.repo_path / "ARTIQ_scripts" / file_name
    if not os.path.exists(file_path):
        with open(file_path, 'w'): pass
    #IMPORT AND BUILD FUNCTIONS
    file = open(file_path,'w')
    indentation = ""
    file.write(indentation + "from artiq.experiment import *\n")
    file.write(indentation + "import numpy as np\n")
    file.write(indentation + "from scipy.io import loadmat\n")
    file.write(indentation + "import os\n")
    file.write(indentation + "import subprocess\n")
    file.write(indentation + "from datetime import datetime\n")
    file.write(indentation + "from pathlib import Path \n")
    file.write(indentation + "import sys \n")
    file.write(indentation + "sys.path.append(str(Path(__file__).resolve().parent.parent)) \n")
    file.write(indentation + "import main.config as config \n")
    file.write(indentation + "\n")

    # Persisted flags from GUI
    save_sampled_box_checked_flag = bool(getattr(self.experiment, 'save_sampled_variables', False))
    camera_box_checked_flag = bool(getattr(self.experiment, 'camera_enabled', False))
    stop_at_end_of_sequence_flag = bool(getattr(self.experiment, 'stop_at_end_of_sequence', False))
    file.write(indentation + f"save_sampled_box_checked = {save_sampled_box_checked_flag}\n")
    file.write(indentation + f"camera_box_checked = {camera_box_checked_flag}\n")
    # file.write(indentation + f"stop_at_end_of_sequence = {stop_at_end_of_sequence_flag}\n")

    file.write("\n")
    
    #Creating functions to calculate derived variables
    for variable in self.experiment.derived_variables:
        file.write(indentation + "def calculate_%s(%s)->TFloat: \n"%(variable.name, variable.arguments))
        indentation += "    "
        file.write(indentation + "return %s \n\n" %variable.function)
        indentation = indentation[:-4]
    #Experimental description
    file.write(indentation + "class " + file_name[:-3] + "(EnvExperiment):\n")
    indentation += "    "
    file.write(indentation + "def build(self):\n")
    indentation += "    "
    # Setting the DEVICES to be used 
    for device in config.list_of_devices_for_use:
        file.write(indentation + "self.setattr_device('%s')\n" %device)


    # If LOOKUP variables are requested create and load them
    for index, lookup_variable in enumerate(self.experiment.lookup_variables):
        # We first save the lookup list and then load it from the python description of the experiment
        if lookup_variable.lookup_list_name != "":
            temp_lookup_list_path = "./temp lookup variables/temp_%d_"%index +lookup_variable.lookup_list_name
            savemat(temp_lookup_list_path, {'array':lookup_variable.lookup_list})
            file.write(indentation + "self.%s"%lookup_variable.name + " = list(loadmat('%s')['array'][0])\n"%temp_lookup_list_path)
    

    # If SCAN is needed prepare the variables
    if self.experiment.do_scan == True and self.experiment.scanned_variables_count > 0:
        #iterating over valid (not "None") scanned variables and creating an array to be used as a collection of names
        var_names = ""
        for variable in self.experiment.scanned_variables:
            if variable.name != "None":
                num = getattr(variable, 'num_scan_steps', 1)
                file.write(indentation + "self.%s = list(np.linspace(%f, %f, %d))\n"%(variable.name, variable.min_val, variable.max_val, int(num)))
                var_names += variable.name + ", "
    file.write("\n")
    indentation = indentation[:-4]


    #check if there are any sampled variables - need?
    has_sampled = any(
        channel != "0"
        for edge in self.experiment.sequence
        for channel in edge.sampler)
    
    # If a varialbe is sampled, we create an array for it to store the sampled values 
    if save_sampled_box_checked_flag == True and not run_continuous:
        file.write("\n")
        file.write(indentation + "def prepare(self): \n")
        indentation += "    "
        file.write(indentation + "# Create persistent dataset (persist=True -> stored in LMDB database)\n")
        file.write(indentation + "self.set_dataset(\"data\", [], persist=True,archive=False)\n\n")
        indentation = indentation[:-4]


    # Overwriting the run method
    file.write(indentation + "@kernel\n")
    indentation_kernel = indentation
    file.write(indentation + "def run(self):\n")
    indentation += "    "
    file.write(indentation + "self.core.reset()\n")
    file.write(indentation + "self.core.break_realtime()\n")
    file.write(indentation + "inputs = [0.0]*8\n")
    file.write(indentation + "delay(1*s)\n") # this delay is added since our reference clock is 1GHz and self.core.break_realtime moves it forward by 15000 clock cycles
    

    # for inital value of derived variables 
    arguments = self.experiment.derived_variables
    for argument in arguments:
        file.write(indentation + argument.name + " = " + "float("+ argument.initial_value + ")" + "\n")


    # initialize regular (non-scanned) variables so expressions have bindings
    base_variables = []
    for variable in getattr(self.experiment, "new_variables", []):
        if variable.name in ("", "None"):
            continue
        if getattr(variable, "is_scanned", False):
            continue
        if getattr(variable, "is_ramped", False):
            continue
        if getattr(variable, "is_sampled", False):
            continue
        if getattr(variable, "is_derived", False):
            continue
        if getattr(variable, "is_lookup", False):
            continue
        base_variables.append(variable)

    for variable in base_variables:
        value_expr = variable.for_python if str(variable.for_python).strip() != "" else variable.value
        file.write(indentation + f"{variable.name} = {value_expr}\n")

    warmup_runs = self.experiment.cam_trigger_off_runs if getattr(self.experiment, "cam_trigger_off", False) else 0
    actual_runs = self.experiment.number_of_runs if multiple_runs else 1
    if actual_runs <= 0:
        actual_runs = 1
    total_runs = warmup_runs + actual_runs
    run_loop_added = False
    # file.write(f"#warmup = {warmup_runs}, actual = {actual_runs}, total = {total_runs}\n")


    indentation_flag = 0
    # Create an infinite while loop if needs to run continuously
    if run_continuous:
        file.write(indentation + "while True:\n")
        indentation += "    "
        indentation_flag += 1
        file.write(indentation + "camera_enabled = True   # continuous run\n")
        file.write(indentation + "run_index = 0\n")
        # file.write(indentation + "self.core.break_realtime()\n")
        # if warmup_runs > 0:
        #     file.write(indentation + "if not hasattr(self, '_cam_warmup_remaining'):\n")
        #     indentation += "    "
        #     file.write(indentation + "self._cam_warmup_remaining = %d\n" % warmup_runs)
        #     file.write(indentation + "self._cam_warmup_triggered = False\n")
        #     indentation = indentation[:-4]
        #     file.write(indentation + "if self._cam_warmup_remaining > 0:\n")
        #     indentation += "    "
        #     file.write(indentation + "camera_enabled = False   # warm-up run\n")
        #     file.write(indentation + "self._cam_warmup_remaining -= 1\n")
        #     indentation = indentation[:-4]
        #     file.write(indentation + "elif not self._cam_warmup_triggered:\n")
        #     indentation += "    "
        #     file.write(indentation + "# Camera warm-up trigger: execute once after cam_trigger_off runs\n")
            
        #     if config.allow_skipping_images == True and self.experiment.skip_images:
        #         skip_count = getattr(config, "skip_images_trigger_count", 10)
        #         file.write(indentation + f"for _ in range({skip_count}):\n")
        #         indentation += "    "
        #         for val in config.camera_trigger_ttl:
        #             file.write(indentation + "self.ttl" + str(val) + ".pulse(10*ms)\n")
        #         file.write(indentation + "delay(100*ms)\n")
        #         indentation = indentation[:-4]
        #     file.write(indentation + "self._cam_warmup_triggered = True\n")
        #     file.write(indentation + "camera_enabled = True\n")
        #     indentation = indentation[:-4]
        #     file.write(indentation + "else:\n")
        #     indentation += "    "
        #     file.write(indentation + "camera_enabled = True\n")
        #     indentation = indentation[:-4]
        # else:
        #     file.write(indentation + "camera_enabled = True\n")

    if not run_continuous:
        
        file.write(indentation + "for run_index in range(%d):   # run loop including camera warm-up: warmup = %d, actual = %d, total = %d\n" % (total_runs, warmup_runs, actual_runs, total_runs))
        indentation += "    "
        file.write(indentation + "run_index_no_warumup = run_index - %d # real run index for actual runs, will be negative for warm-up runs\n" % warmup_runs)
        indentation_flag += 1
        run_loop_added = True
        # Skip-image runs: trigger camera warm-up shots without saving
        if config.allow_skipping_images == True and self.experiment.skip_images:
            skip_count = getattr(config, "skip_images_trigger_count", 10)
            file.write(indentation + f"# Trigger camera {skip_count} times without saving images\n")
            # file.write(indentation + "self.core.break_realtime()\n")
            file.write(indentation + f"if run_index == {warmup_runs}:\n")
            indentation += "    "
            file.write(indentation + f"for _ in range({skip_count}):\n")
            indentation += "    "
            for val in config.camera_trigger_ttl:
                file.write(indentation + "self.ttl" + str(val) + ".pulse(1*ms)\n")
            file.write(indentation + "delay(200*ms)\n")
            indentation = indentation[:-4]
            indentation = indentation[:-4]
        if warmup_runs > 0:
            file.write(indentation + "camera_enabled = (run_index >= %d)   # warm-up run check\n" % warmup_runs)
        else:
            file.write(indentation + "camera_enabled = True\n")

    # 100 ns delay to avoid collision of the last edge assignment of digital channels as there is at most camera_trigger_ttl channel changes at a given time stamp
    file.write(indentation + "delay(100*ns)\n")
    # If scan is needed 
    if self.experiment.do_scan == True and self.experiment.scanned_variables_count > 0:
        file.write(indentation + "#Beginning of the Scan\n")
        # open nested loops: step1, step2, ... for each scanned variable in order
        opened = 0
        for idx, variable in enumerate(self.experiment.scanned_variables):
            if variable.name != "None":
                num = getattr(variable, 'num_scan_steps', 1)
                file.write(indentation + "for step%d in range(%d):\n" % (idx+1, int(num)))
                indentation += "    "
                opened += 1
        # assign current scanned values to variable names (use step indices)
        for idx, variable in enumerate(self.experiment.scanned_variables):
            if variable.name != "None":
                file.write(indentation + f"{variable.name} = self.{variable.name}[step{idx+1}]\n")
        indentation_flag += opened
    self.delta_t = 0 

    #flag_init is used to indicate that there is no need for a delay calculation for the first row
    flag_init = 0
    flag_ramp_up = False
    sampled_names = []
    already_loop_for_edge = [False] * (self.sequence_num_rows)
    for edge_index in range(self.sequence_num_rows):
        file.write(indentation + "#Edge number " + str(edge_index) + " name of edge: " + self.experiment.sequence[edge_index].name + "\n")
        if flag_init == 0: # in the first iteration it does not need to do anything as delta_t is assigned to 0
            flag_init = 1
        else:
            #Brackets are needed to take into account that for_python can be a mathematical expression with signs
            try:
                temp_text = "(" + str(self.experiment.sequence[edge_index].for_python) + ")" + "-" + "(" + str(self.experiment.sequence[edge_index-1].for_python) + ")"
                self.delta_t = str(simplify(temp_text))
            except:
                self.delta_t = temp_text
            try: #this try is used to try evaluating the expression. It will only be able to do so in case it is scanned
                exec("self.delta_t = " + self.delta_t)
            except:
                pass
        #ADDING A DELAY
        if self.delta_t != 0 and flag_ramp_up_delay == False:
            file.write(indentation + "delay((" + str(self.delta_t) + ")*ms)\n") 
        
        flag_ramp_up_delay = False
        # ADDING FOR LOOP FOR RAMP
        count_indent = 0
        for variable in self.experiment.ramped_variables:
            if self.experiment.do_ramp == True and self.experiment.ramped_variables_count > 0:
                if variable.start_ID == self.experiment.sequence[edge_index].id and already_loop_for_edge[edge_index] == False:
                    if edge_index != 0:
                        flag_ramp_up = True
                        flag_ramp_up_delay = True
                        flag_ramp_variable = variable
                        file.write(indentation + "for i in range(1, (%d+1)):   # ramp up loop \n" %(variable.stepsramp)) 
                        already_loop_for_edge[edge_index] = True
                        indentation += "    "
                        count_indent = count_indent + 1

        
        # RPC for derived variable calculation: handle multiple derived variables per edge
        if edge_index > 0:
            edge_id = getattr(self.experiment.sequence[edge_index], 'id', '')
            if edge_id:
                for variable in self.experiment.derived_variables:
                    if getattr(variable, 'edge_id', '') == edge_id:
                        file.write(indentation + "%s = calculate_%s(%s)\n" % (variable.name, variable.name, variable.arguments))

        #DIGITAL CHANNEL CHANGES
        if config.dds_channels_number > 0:
            for index, channel in enumerate(self.experiment.sequence[edge_index].digital):
                if edge_index == 0 and index % 8 == 0: #adding a 1000 ns delay to make changes into TTL channels
                    file.write(indentation + "delay(1000*ns)\n")

                if channel.changed == True:
                    if index in config.camera_trigger_ttl:
                        if channel.value == 1:
                            file.write(indentation + "if camera_enabled:\n")
                            indentation += "    "
                            file.write(indentation + "self.ttl" + str(index) + ".on()\n")
                            indentation = indentation[:-4]
                            file.write(indentation + "else:\n")
                            indentation += "    "
                            file.write(indentation + "self.ttl" + str(index) + ".off()\n")
                            indentation = indentation[:-4]
                        else:
                            file.write(indentation + "self.ttl" + str(index) + ".off()\n")
                    else:
                        if channel.value == 1: # 1 is on 
                            file.write(indentation + "self.ttl" + str(index) + ".on()\n") 
                        else:
                            file.write(indentation + "self.ttl" + str(index) + ".off()\n") 
            
            if edge_index == 0: #adding a 1000 ns delay after 8 ttl channels because otherwise it ignores the first analog channel
                file.write(indentation + "delay(1000*ns)\n")
       
        #ANALOG CHANNEL CHANGES
        if config.analog_channels_number > 0:
            #Assigning zotino card values
            if config.analog_card == "zotino":
                flag_zotino_change_needed = False      
                for index, channel in enumerate(self.experiment.sequence[edge_index].analog):
                    if channel.changed == True:
                        flag_zotino_change_needed = True
                        file.write(indentation + "self.zotino0.write_dac(%d, %s)\n" %(index, channel.for_python)) 
                        
                if flag_zotino_change_needed:
                    file.write(indentation + "self.zotino0.load()\n")
                    
            #Assigning fastino card values
            elif config.analog_card == "fastino":
                first_analog_channel = True          
                number_of_channels_changed = 0          
                for index, channel in enumerate(self.experiment.sequence[edge_index].analog):
                    if channel.changed == True:
                        number_of_channels_changed += 1
                        if edge_index == 0 or index > 0: #adds a delay only for the default edge and in sace of 
                            file.write(indentation + "delay(10*ns)\n")    
                        file.write(indentation + "self.fastino0.set_dac(%d, %s)\n" %(index,channel.for_python))
                #Moving the time cursor back
                if number_of_channels_changed > 1:
                    file.write(indentation + "delay(-%d0*ns)\n" %(number_of_channels_changed-1))
            
        #DDS CHANNEL CHANGES
        if config.dds_channels_number > 0:
            for index, channel in enumerate(self.experiment.sequence[edge_index].dds):
                if channel.changed == True:
                    urukul_num = int(index // 4)
                    channel_num = int(index % 4)
                    file.write(indentation + "self.urukul" + str(urukul_num) + "_ch" + str(channel_num) + ".set_att((" + str(channel.attenuation.for_python) + ")*dB) \n")    
                    file.write(indentation + "self.urukul" + str(urukul_num) + "_ch" + str(channel_num) + ".set(frequency = (" + str(channel.frequency.for_python) + ")*MHz, amplitude = (" + str(channel.amplitude.for_python) + ")/100 , phase = (" + str(channel.phase.for_python) + ")/360)\n")    
                    if channel.state.value == 1:
                        file.write(indentation + "self.urukul" + str(urukul_num) + "_ch" + str(channel_num) + ".sw.on() \n")
                    else:
                        file.write(indentation + "self.urukul" + str(urukul_num) + "_ch" + str(channel_num) + ".sw.off() \n")

        #MIRNY CHANNEL CHANGES
        if config.mirny_channels_number > 0:
            for index, channel in enumerate(self.experiment.sequence[edge_index].mirny):
                if channel.changed == True:
                    mirny_num = int(index // 4)
                    channel_num = int(index % 4)
                    file.write(indentation + "self.mirny" + str(mirny_num) + "_ch" + str(channel_num) + ".set_att((" + str(channel.attenuation.for_python) + ")*dB) \n")    
                    file.write(indentation + "self.mirny" + str(mirny_num) + "_ch" + str(channel_num) + ".set_frequency(%s*MHz)\n"%str(channel.frequency.for_python))
                    file.write(indentation + "self.mirny" + str(mirny_num) + "_ch" + str(channel_num) + ".set_output_power_mu(%s)\n"%str(int(closest_key(self.mirny_amp_values_dBm ,float(channel.amplitude.for_python)))))   
                    if channel.state.value == 1:
                        file.write(indentation + "self.mirny" + str(mirny_num) + "_ch" + str(channel_num) + ".sw.on() \n")
                    else:
                        file.write(indentation + "self.mirny" + str(mirny_num) + "_ch" + str(channel_num) + ".sw.off() \n")

                    
        #SAMPLER CHANNELS
        if config.sampler_channels_number > 0:
            input_readout_is_requested = False
            for index, channel in enumerate(self.experiment.sequence[edge_index].sampler):
                if channel != "0":
                    input_readout_is_requested = True
            if input_readout_is_requested == True:
                file.write(indentation + "# Sampler input readout\n")
                file.write(indentation + "self.sampler0.sample(inputs)\n")
                for index, channel in enumerate(self.experiment.sequence[edge_index].sampler):
                    if channel != "0":
                        file.write(indentation + "%s = inputs[%d]\n" %(channel, index))
                        sampled_names.append(channel) # for save sampled variables
        
        #ADDING DELAY RAMP  - to make ramp and scan compatible  
        if flag_ramp_up == True:             
            try:
                temp_text_ramp =  "((" + str(self.experiment.sequence[edge_index+1].for_python) + ")" + "-" + "(" + str(self.experiment.sequence[edge_index].for_python) + "))"
                temp_text_ramp = str(simplify(temp_text_ramp)) # simplify possible only when not scan
            except:
                temp_text_ramp =  "((" + str(self.experiment.sequence[edge_index+1].for_python) + ")" + "-" + "(" + str(self.experiment.sequence[edge_index].for_python) + "))"
            file.write(indentation + "delay((" + temp_text_ramp + "/" +str(flag_ramp_variable.stepsramp) + ")*ms)  # for ramp up: time devided by steps \n") 
        
        if flag_ramp_up == True: 
            flag_ramp_up = False  
            for indent in range(count_indent):
                indentation = indentation[:-4] 

    if save_sampled_box_checked_flag == True and not run_continuous:
        file.write('\n' + indentation + "# For save sample variables\n")
        args_str = ""
        if sampled_names:
            args_str += ", ".join(sampled_names)

        if self.experiment.do_scan == True and self.experiment.scanned_variables_count > 0:
            # determine which step variables exist (step1, step2, ...)
            step_var_names = [f"step{idx+1}" for idx, variable in enumerate(self.experiment.scanned_variables) if getattr(variable, 'name', "") != "None"]
        else:
            step_var_names = []

        # build call arguments: steps (if any) followed by sampled variable names
        if step_var_names:
            call_args_list = step_var_names + sampled_names
            call_args = ", ".join(call_args_list)
            file.write(indentation + "self.store_sample(run_index_no_warumup, %s)\n" % (call_args if call_args else ""))
        else:
            # no per-variable steps: keep legacy single `step` argument
            file.write(indentation + "self.store_sample(run_index_no_warumup%s)\n" % (", " + args_str if args_str else ""))


    for variable in self.experiment.derived_variables: # to print the values of all arguments in dervied variables (feedback)
        args_list = variable.arguments.split(",")
        file.write('\n')
        for arg in args_list:
            arg = arg.strip()
            file.write(f'{indentation}delay(5*ms)\n')        
            file.write(f'{indentation}print("{arg}:", {arg})\n')        
        
    if self.experiment.do_scan == True and self.experiment.scanned_variables_count > 0:
        step_var_names = [f"step{idx+1}" for idx, variable in enumerate(self.experiment.scanned_variables) if getattr(variable, 'name', "") != "None"]

        for _ in range(len(step_var_names)):
            file.write('\n' + indentation + "#exiting the scan at the first step if camera is not enabled \n")            
            file.write(indentation + "if not camera_enabled: \n")
            indentation += '    '
            file.write(indentation + "break \n")
            indentation = indentation[:-4]
            indentation = indentation[:-4]
            indentation_flag -= 1
        indentation = indentation[:-4*(indentation_flag)]

    if save_sampled_box_checked_flag == True and not run_continuous:
        file.write(indentation + "self.copy_dataset_file()  # add saved sampled variables to a txt file \n")
    
    if not run_continuous:
        file.write('\n' + indentation + 'self.print_end_exp()  # print end of experiment in the end of the run \n')

    # If GUI requested stop_at_end_of_sequence, check host flag and trigger go_to_edge from host
    file.write('\n')
    if stop_at_end_of_sequence_flag == True:
        file.write(indentation + 'if self.check_host_stop_and_run():  # if true stops the experiment\n')
        file.write(indentation + "    return\n")
        file.write('\n')







        

        
        


    ###############################################################################################
    ############################# for continuous run AFTER experiment #############################
    ###############################################################################################


    # if not run_continuous and run_loop_added:
    #     indentation = indentation[:-4]


    if self.experiment.cont_run_after_exp and not run_continuous:
        file.write("\n")
        indentation = indentation_kernel + "    "
        # self.function_to_write_cont_run_after_experiment(file)

        # Create an infinite while loop if needs to run continuously
        file.write(indentation + "while True:\n")
        indentation += "    "
        file.write(indentation + "camera_enabled = False  # Camera disabled during post-experiment continuous run\n")

        # 1000 ns delay to avoid collision of the last edge assignment of digital channels as there is at most 8 channel changes at a given time stamp
        file.write(indentation + "delay(1000*ns)\n")
        # If scan is needed 
        if self.experiment.do_scan == True and self.experiment.scanned_variables_count > 0:
            #making a scanning loop (use per-variable `num_scan_steps`)
            file.write(indentation + "#Beginning of the Scan\n")
            # open nested loops based on per-variable step counts
            opened = 0
            for idx, variable in enumerate(self.experiment.scanned_variables):
                if variable.name != "None":
                    num = getattr(variable, 'num_scan_steps', 1)
                    file.write(indentation + "for step%d in range(%d):\n" % (idx+1, int(num)))
                    indentation += "    "
                    opened += 1
            for idx, variable in enumerate(self.experiment.scanned_variables):
                if variable.name != "None":
                    file.write(indentation + f"{variable.name} = self.{variable.name}[step{idx+1}]\n")
        self.delta_t = 0 

        #flag_init is used to indicate that there is no need for a delay calculation for the first row
        flag_init = 0
        flag_ramp_up = False
        already_loop_for_edge = [False] * (self.sequence_num_rows)
        for edge_index in range(self.sequence_num_rows):
            file.write(indentation + "#Edge number " + str(edge_index) + " name of edge: " + self.experiment.sequence[edge_index].name + "\n")
            if flag_init == 0: # in the first iteration it does not need to do anything as delta_t is assigned to 0
                flag_init = 1
            else:
                #Brackets are needed to take into account that for_python can be a mathematical expression with signs
                try:
                    temp_text = "(" + str(self.experiment.sequence[edge_index].for_python) + ")" + "-" + "(" + str(self.experiment.sequence[edge_index-1].for_python) + ")"
                    self.delta_t = str(simplify(temp_text))
                except:
                    self.delta_t = temp_text
                try: #this try is used to try evaluating the expression. It will only be able to do so in case it is scanned
                    exec("self.delta_t = " + self.delta_t)
                except:
                    pass
            #ADDING A DELAY
            if self.delta_t != 0 and flag_ramp_up_delay == False:
                file.write(indentation + "delay((" + str(self.delta_t) + ")*ms)\n") 
            
            flag_ramp_up_delay = False
            # ADDING FOR LOOP FOR RAMP
            count_indent = 0
            for variable in self.experiment.ramped_variables:
                if self.experiment.do_ramp == True and self.experiment.ramped_variables_count > 0:
                    if variable.start_ID == self.experiment.sequence[edge_index].id and already_loop_for_edge[edge_index] == False:
                        if edge_index != 0:
                            flag_ramp_up = True
                            flag_ramp_up_delay = True
                            flag_ramp_variable = variable
                            file.write(indentation + "for i in range(1, (%d+1)):   # ramp up loop \n" %(variable.stepsramp)) 
                            already_loop_for_edge[edge_index] = True
                            indentation += "    "
                            count_indent = count_indent + 1

            
            #RPC for derived variable calculation: handle multiple derived variables per edge
            if edge_index > 0:
                edge_id = getattr(self.experiment.sequence[edge_index], 'id', '')
                if edge_id:
                    for variable in self.experiment.derived_variables:
                        if getattr(variable, 'edge_id', '') == edge_id:
                            file.write(indentation + "%s = calculate_%s(%s)\n" % (variable.name, variable.name, variable.arguments))

            #DIGITAL CHANNEL CHANGES
            if config.dds_channels_number > 0:
                for index, channel in enumerate(self.experiment.sequence[edge_index].digital):
                    if edge_index == 0 and index % 8 == 0: #adding a 1000 ns delay to make changes into TTL channels
                        file.write(indentation + "delay(1000*ns)\n")

                    if channel.changed == True:
                        if index in config.camera_trigger_ttl:
                            if channel.value == 1:
                                file.write(indentation + "if camera_enabled:\n")
                                indentation += "    "
                                file.write(indentation + "self.ttl" + str(index) + ".on()\n")
                                indentation = indentation[:-4]
                                file.write(indentation + "else:\n")
                                indentation += "    "
                                file.write(indentation + "self.ttl" + str(index) + ".off()\n")
                                indentation = indentation[:-4]
                            else:
                                file.write(indentation + "self.ttl" + str(index) + ".off()\n")
                        else:
                            if channel.value == 1: # 1 is on 
                                file.write(indentation + "self.ttl" + str(index) + ".on()\n") 
                            else:
                                file.write(indentation + "self.ttl" + str(index) + ".off()\n") 
                
                if edge_index == 0: #adding a 1000 ns delay after 8 ttl channels because otherwise it ignores the first analog channel
                    file.write(indentation + "delay(1000*ns)\n")
        
            #ANALOG CHANNEL CHANGES
            if config.analog_channels_number > 0:
                #Assigning zotino card values
                if config.analog_card == "zotino":
                    flag_zotino_change_needed = False      
                    for index, channel in enumerate(self.experiment.sequence[edge_index].analog):
                        if channel.changed == True:
                            flag_zotino_change_needed = True
                            expr = str(channel.for_python)
                            for sv_idx, sv in enumerate(self.experiment.scanned_variables):
                                sv_name = getattr(sv, 'name', '')
                                if sv_name and sv_name != "None":
                                    expr = expr.replace(f"self.{sv_name}[step{sv_idx+1}]", sv_name)
                                    expr = expr.replace(f"self.{sv_name}[step]", sv_name)
                            file.write(indentation + "self.zotino0.write_dac(%d, %s)\n" %(index, expr)) 
                            
                    if flag_zotino_change_needed:
                        file.write(indentation + "self.zotino0.load()\n")
                        
                #Assigning fastino card values
                elif config.analog_card == "fastino":
                    first_analog_channel = True          
                    number_of_channels_changed = 0          
                    for index, channel in enumerate(self.experiment.sequence[edge_index].analog):
                        if channel.changed == True:
                            number_of_channels_changed += 1
                            if edge_index == 0 or index > 0: #adds a delay only for the default edge and in sace of 
                                file.write(indentation + "delay(10*ns)\n")    
                            expr = str(channel.for_python)
                            for sv_idx, sv in enumerate(self.experiment.scanned_variables):
                                sv_name = getattr(sv, 'name', '')
                                if sv_name and sv_name != "None":
                                    expr = expr.replace(f"self.{sv_name}[step{sv_idx+1}]", sv_name)
                                    expr = expr.replace(f"self.{sv_name}[step]", sv_name)
                            file.write(indentation + "self.fastino0.set_dac(%d, %s)\n" %(index,expr))
                    #Moving the time cursor back
                    if number_of_channels_changed > 1:
                        file.write(indentation + "delay(-%d0*ns)\n" %(number_of_channels_changed-1))
                
            #DDS CHANNEL CHANGES
            if config.dds_channels_number > 0:
                for index, channel in enumerate(self.experiment.sequence[edge_index].dds):
                    if channel.changed == True:
                        urukul_num = int(index // 4)
                        channel_num = int(index % 4)
                        att_expr = str(channel.attenuation.for_python)
                        freq_expr = str(channel.frequency.for_python)
                        amp_expr = str(channel.amplitude.for_python)
                        phase_expr = str(channel.phase.for_python)
                        for sv_idx, sv in enumerate(self.experiment.scanned_variables):
                            sv_name = getattr(sv, 'name', '')
                            if sv_name and sv_name != "None":
                                att_expr = att_expr.replace(f"self.{sv_name}[step{sv_idx+1}]", sv_name)
                                att_expr = att_expr.replace(f"self.{sv_name}[step]", sv_name)
                                freq_expr = freq_expr.replace(f"self.{sv_name}[step{sv_idx+1}]", sv_name)
                                freq_expr = freq_expr.replace(f"self.{sv_name}[step]", sv_name)
                                amp_expr = amp_expr.replace(f"self.{sv_name}[step{sv_idx+1}]", sv_name)
                                amp_expr = amp_expr.replace(f"self.{sv_name}[step]", sv_name)
                                phase_expr = phase_expr.replace(f"self.{sv_name}[step{sv_idx+1}]", sv_name)
                                phase_expr = phase_expr.replace(f"self.{sv_name}[step]", sv_name)
                        file.write(indentation + "self.urukul" + str(urukul_num) + "_ch" + str(channel_num) + ".set_att((" + att_expr + ")*dB) \n")    
                        file.write(indentation + "self.urukul" + str(urukul_num) + "_ch" + str(channel_num) + ".set(frequency = (" + freq_expr + ")*MHz, amplitude = (" + amp_expr + ")/100 , phase = (" + phase_expr + ")/360)\n")    
                        if channel.state.value == 1:
                            file.write(indentation + "self.urukul" + str(urukul_num) + "_ch" + str(channel_num) + ".sw.on() \n")
                        else:
                            file.write(indentation + "self.urukul" + str(urukul_num) + "_ch" + str(channel_num) + ".sw.off() \n")

            #MIRNY CHANNEL CHANGES
            if config.mirny_channels_number > 0:
                for index, channel in enumerate(self.experiment.sequence[edge_index].mirny):
                    if channel.changed == True:
                        mirny_num = int(index // 4)
                        channel_num = int(index % 4)
                        file.write(indentation + "self.mirny" + str(mirny_num) + "_ch" + str(channel_num) + ".set_att((" + str(channel.attenuation.for_python) + ")*dB) \n")    
                        file.write(indentation + "self.mirny" + str(mirny_num) + "_ch" + str(channel_num) + ".set_frequency(%s*MHz)\n"%str(channel.frequency.for_python))    
                        file.write(indentation + "self.mirny" + str(mirny_num) + "_ch" + str(channel_num) + ".set_output_power_mu(%s)\n"%str(int(closest_key(self.mirny_amp_values_dBm ,float(channel.amplitude.for_python)))))
                        if channel.state.value == 1:
                            file.write(indentation + "self.mirny" + str(mirny_num) + "_ch" + str(channel_num) + ".sw.on() \n")
                        else:
                            file.write(indentation + "self.mirny" + str(mirny_num) + "_ch" + str(channel_num) + ".sw.off() \n")

                        
            #SAMPLER CHANNELS
            if config.sampler_channels_number > 0:
                input_readout_is_requested = False
                for index, channel in enumerate(self.experiment.sequence[edge_index].sampler):
                    if channel != "0":
                        input_readout_is_requested = True
                if input_readout_is_requested == True:
                    file.write(indentation + "# Sampler input readout\n")
                    file.write(indentation + "self.sampler0.sample(inputs)\n")
                    for index, channel in enumerate(self.experiment.sequence[edge_index].sampler):
                        if channel != "0":
                            file.write(indentation + "%s = inputs[%d]\n" %(channel, index))
            
            #ADDING DELAY RAMP  - to make ramp and scan compatible  
            if flag_ramp_up == True:             
                try:
                    temp_text_ramp =  "((" + str(self.experiment.sequence[edge_index+1].for_python) + ")" + "-" + "(" + str(self.experiment.sequence[edge_index].for_python) + "))"
                    temp_text_ramp = str(simplify(temp_text_ramp)) # simplify possible only when not scan
                except:
                    temp_text_ramp =  "((" + str(self.experiment.sequence[edge_index+1].for_python) + ")" + "-" + "(" + str(self.experiment.sequence[edge_index].for_python) + "))"
                file.write(indentation + "delay((" + temp_text_ramp + "/" +str(flag_ramp_variable.stepsramp) + ")*ms)  # for ramp up: time devided by steps \n") 
            
            if flag_ramp_up == True: 
                flag_ramp_up = False  
                #file.write(indentation + "print('%s %s = ', %s)\n" %(("Value of ramped variable: "), str(flag_ramp_variable.name), flag_ramp_variable.functionramp))
                for indent in range(count_indent):
                    indentation = indentation[:-4] 


    ##################################################################
    ##################### RPC functions ##############################
    ##################################################################

    if not run_continuous:
        indentation = indentation_kernel
        file.write(indentation + "@rpc\n")
        file.write(indentation + "def print_end_exp(self):\n")
        indentation += '    '
        file.write(indentation + "print(\"End of experiment\")\n")
        indentation = indentation[:-4]

    # RPC helper: check host-side stop flag and run init_hardware if requested
    if stop_at_end_of_sequence_flag == True:
        file.write('\n')
        file.write(indentation + "@rpc\n")
        file.write(indentation + "def check_host_stop_and_run(self):\n")
        indentation += '    '
        file.write(indentation + "stop_file = Path(__file__).resolve().parent / 'stop_flag.txt'\n")
        file.write(indentation + "try:\n")
        indentation += '    '
        file.write(indentation + "if stop_file.exists():\n")
        indentation += '    '
        file.write(indentation + "# run init_hardware.py on the host (matches GUI behaviour)\n")
        file.write(indentation + "init_path = Path(__file__).resolve().parent / 'init_hardware.py'\n")
        file.write(indentation + "try:\n")
        indentation += '    '
        file.write(indentation + "if config.package_manager == 'conda':\n")
        indentation += '    '
        file.write(indentation + "os.system('conda activate ' + config.artiq_environment_name + ' && artiq_run ' + str(init_path))\n")
        indentation = indentation[:-4]
        file.write(indentation + "elif config.package_manager == 'clang64':\n")
        indentation += '    '
        file.write(indentation + "try:\n")
        indentation += '    '
        file.write(indentation + "proc = subprocess.run(['cmd', '/c', str(init_path)], check=False)\n")
        indentation = indentation[:-4]
        file.write(indentation + "except Exception:\n")
        indentation += '    '
        file.write(indentation + "os.system('artiq_run ' + str(init_path))\n")
        indentation = indentation[:-4]
        indentation = indentation[:-4]
        indentation = indentation[:-4]
        file.write(indentation + "except Exception as exc:\n")
        indentation += '    '
        file.write(indentation + "print('Could not execute init_hardware:', exc)\n")
        indentation = indentation[:-4]
        file.write(indentation + "# Do not delete the stop flag here; leave it for manual clearing\n")
        file.write(indentation + "stop_file.unlink()\n")
        file.write(indentation + "return True\n")
        indentation = indentation[:-4]
        file.write(indentation + "return False  # if there is no file the experiment is not stopped\n")
        indentation = indentation[:-4]
        file.write(indentation + "except Exception as exc:\n")
        indentation += '    '
        file.write(indentation + "print('check_host_stop_and_run error:', exc)\n")
        file.write(indentation + "return False\n")
    
    if save_sampled_box_checked_flag == True and not run_continuous:
        file.write('\n')
        file.write("    @rpc\n")
        # determine per-variable step names
        if self.experiment.do_scan == True and self.experiment.scanned_variables_count > 0:
            # determine which step variables exist (step1, step2, ...)
            step_var_names = [f"step{idx+1}" for idx, variable in enumerate(self.experiment.scanned_variables) if getattr(variable, 'name', "") != "None"]
        else:
            step_var_names = []

        if step_var_names:
            signature_args_list = step_var_names + sampled_names
            signature_args = ", ".join(signature_args_list)
            file.write(f"    def store_sample(self, run_index, {signature_args}):\n")
            # build tuple for dataset: run_index, all steps as ints, then sampled values
            tuple_parts = ["int(run_index)"] + [f"int({s})" for s in step_var_names]
            if sampled_names:
                tuple_parts += sampled_names
            file.write(f"        self.append_to_dataset(\"data\", ({', '.join(tuple_parts)}))\n")
        else:
            # legacy single step
            file.write("    def store_sample(self, run_index%s):\n" % (", " + args_str if args_str else ""))
            file.write("        self.append_to_dataset(\"data\", (int(run_index)%s))\n" % (", " + args_str if args_str else ""))

        file.write('\n')
        file.write(indentation + "@rpc\n")
        file.write(indentation + "def copy_dataset_file(self):\n")
        indentation += '    '

        exp_name = (getattr(self.experiment, 'experimental_data', None) and getattr(self.experiment.experimental_data, 'experiment_name', '')) or ""
        experimental_path = (getattr(self.experiment, 'experimental_data', None) and getattr(self.experiment.experimental_data, 'current_run_path', '')) or ""
        experimental_metadata_path = (getattr(self.experiment, 'experimental_data', None) and getattr(self.experiment.experimental_data, 'current_run_metadata_path', '')) or ""
        file.write(indentation + f"experiment_name = {repr(exp_name)}\n")
        file.write(indentation + f"experimental_path = {repr(experimental_path)}\n")
        file.write(indentation + f"experimental_metadata_path = {repr(experimental_metadata_path)}\n")

        
        file.write(indentation + "target_directory = Path(experimental_metadata_path) if experimental_metadata_path else (Path(experimental_path) if experimental_path else None)\n")
        file.write(indentation + "if target_directory is None:\n")
        file.write(indentation + "    today = datetime.now().strftime('%Y_%m_%d')\n")
        file.write(indentation + "    exp_dir = experiment_name if experiment_name else 'unspecified_experiment'\n")
        file.write(indentation + "    target_directory = Path(config.experiment_data_root) / exp_dir / today\n")
        file.write(indentation + "try:\n")
        file.write(indentation + "    target_directory.mkdir(parents=True, exist_ok=True)\n")
        file.write(indentation + "except Exception as e:\n")
        file.write(indentation + "    print(f'Could not create target directory {target_directory}: {e}')\n")
        file.write(indentation + "folder_name = target_directory.name\n")
        file.write(indentation + "folder_date = datetime.now().strftime('%Y%m%d')\n")
        file.write(indentation + "folder_time = folder_name[-8:].replace('_', '') if len(folder_name) >= 8 else datetime.now().strftime('%H%M%S')\n")
        file.write(indentation + "target_file = target_directory / f\"dataset_db_copy_{folder_date}_{folder_time}.txt\"\n")
        file.write(indentation + "data = self.get_dataset('data')\n")
        file.write(indentation + "with open(target_file, \"w\") as f:\n")
        file.write(indentation + "    f.writelines(f\"{entry}\\n\" for entry in data)\n")
        
    file.close()


def create_go_to_edge(self, edge_num, to_default = False):
    '''
    Function is used to write a description of experiment that will go to the edge selected in a tab.
    The description is saved as go_to_edge.py   
    The flag to_default is used to be able to go to default edge in the init_hardware function
    '''
    if to_default:
        # Set the edge value to default edge
        edge = 0
        file_name = "init_hardware.py"
    else:
        # The edge is defined by the currently selected tab as a last selected row in that tab
        edge = edge_num
        file_name = "go_to_edge.py"
    self.experiment.go_to_edge = edge
    file_path = self.repo_path / "ARTIQ_scripts" / file_name
    # Create a file if it is missing
    if not os.path.exists(file_path):
        with open(file_path, 'w'): pass
    file = open(file_path,'w')
    
    # Importing libraries and overwriting the build method
    indentation = ""
    file.write(indentation + "from artiq.experiment import *\n\n")
    file.write(indentation + "class " + file_name[:-3] + "(EnvExperiment):\n")
    indentation += "    "
    file.write(indentation + "def build(self):\n")
    indentation += "    "
    # Setting the devices to be used 
    for device in config.list_of_devices_for_use:
        file.write(indentation + "self.setattr_device('%s')\n" %device)
    
    file.write("\n")
    indentation = indentation[:-4]
    # Overwriting the run method
    file.write(indentation + "@kernel\n")
    file.write(indentation + "def run(self):\n")
    indentation += "    "
    file.write(indentation + "self.core.reset()\n")
    file.write(indentation + "self.core.break_realtime()\n")
   
    # Initializing the devices 
    if file_name == "init_hardware.py":
        for device in config.list_of_devices_for_initialization:
            file.write(indentation + "self.%s.init()\n"%device)
   
    
    # DIGITAL CHANNEL CHANGES
    if config.digital_channels_number > 0:
        for index, channel in enumerate(self.experiment.sequence[edge].digital):
            if index % 8 == 0: #adding a 1 ms delay to make changes for more than 8 TTL channels. There is a limit of the buffer size
                file.write(indentation + "delay(1*ms)\n")
            if channel.value == 0:
                file.write(indentation + "self.ttl" + str(index) + ".off()\n")
            elif channel.value == 1:
                file.write(indentation + "self.ttl" + str(index) + ".on()\n")        
        file.write(indentation + "delay(1*ms)\n")

    # ANALOG CHANNEL CHANGES
    if config.analog_channels_number > 0:
        # Assigning zotino card changes
        if config.analog_card == "zotino":
            for index, channel in enumerate(self.experiment.sequence[edge].analog):
                file.write(indentation + "self.zotino0.write_dac(%d, %.6f)\n" %(index, channel.value))
            file.write(indentation + "self.zotino0.load()\n")
            
        # Assigning fastino card changes
        elif config.analog_card == "fastino":
            #Since we do not care about timing here we can add a redundant delay of 10 ns
            for index, channel in enumerate(self.experiment.sequence[edge].analog):
                file.write(indentation + "delay(10*ns)\n")    
                file.write(indentation + "self.fastino0.set_dac(%d, %.6f)\n" %(index, channel.value))         

    # DDS CHANNEL CHANGES
    if config.dds_channels_number > 0:
        for index, channel in enumerate(self.experiment.sequence[edge].dds):
            urukul_num = int(index // 4)
            channel_num = int(index % 4)
            file.write(indentation + "self.urukul" + str(urukul_num) + "_ch" + str(channel_num) + ".set_att(" + str(channel.attenuation.value) + "*dB) \n")    
            file.write(indentation + "self.urukul" + str(urukul_num) + "_ch" + str(channel_num) + ".set(frequency = " + str(channel.frequency.value) + "*MHz, amplitude = " + str(channel.amplitude.value) + "/100, phase = (" + str(channel.phase.value) + ")/360)\n")    
            if channel.state.value == 1:
                file.write(indentation + "self.urukul" + str(urukul_num) + "_ch" + str(channel_num) + ".sw.on() \n")    
            elif channel.state.value == 0:
                file.write(indentation + "self.urukul" + str(urukul_num) + "_ch" + str(channel_num) + ".sw.off() \n")                

    # MIRNY CHANNEL CHANGES
    if config.mirny_channels_number > 0:
        for index, channel in enumerate(self.experiment.sequence[edge].mirny):
            mirny_num = int(index // 4)
            channel_num = int(index % 4)
            file.write(indentation + "self.mirny" + str(mirny_num) + "_ch" + str(channel_num) + ".set_att(" + str(channel.attenuation.value) + "*dB) \n")    
            file.write(indentation + "self.mirny" + str(mirny_num) + "_ch" + str(channel_num) + ".set_frequency(%s*MHz)\n"%str(channel.frequency.for_python))    
            file.write(indentation + "self.mirny" + str(mirny_num) + "_ch" + str(channel_num) + ".set_output_power_mu(%s)\n"%str(int(closest_key(self.mirny_amp_values_dBm ,float(channel.amplitude.for_python)))))
            if channel.state.value == 1:
                file.write(indentation + "self.mirny" + str(mirny_num) + "_ch" + str(channel_num) + ".sw.on() \n")
            elif channel.state.value == 0:
                file.write(indentation + "self.mirny" + str(mirny_num) + "_ch" + str(channel_num) + ".sw.off() \n")                
            
    file.close()
    
    
def set_slow_dds_states(self):
    '''
    Function is used to write a description of experiment that will set the displayed states for slow dds channels
    The description is saved as set_slow_dds.py   
    '''
    file_name = "set_slow_dds_states.py"
    file_path = self.repo_path / "ARTIQ_scripts" / file_name
    # Create a file if it is missing
    if not os.path.exists(file_path):
        with open(file_path, 'w'): pass
    file = open(file_path,'w')
    
    # Importing libraries and overwriting the build method
    indentation = ""
    file.write(indentation + "from artiq.experiment import *\n\n")
    file.write(indentation + "class " + file_name[:-3] + "(EnvExperiment):\n")
    indentation += "    "
    file.write(indentation + "def build(self):\n")
    indentation += "    "
    # Setting the devices to be used 
    for device in config.list_of_devices_for_use:
        file.write(indentation + "self.setattr_device('%s')\n" %device)
    
    file.write("\n")
    indentation = indentation[:-4]
    # Overwriting the run method
    file.write(indentation + "@kernel\n")
    file.write(indentation + "def run(self):\n")
    indentation += "    "
    file.write(indentation + "self.core.reset()\n")
    file.write(indentation + "self.core.break_realtime()\n")
   
    # SLOW DDS CHANNEL STATES
    for index, channel in enumerate(self.experiment.slow_dds):
        file.write(indentation + "self.%s"%config.slow_dds_channels[index] + ".set_att(" + str(channel.attenuation) + "*dB) \n")    
        file.write(indentation + "self.%s"%config.slow_dds_channels[index] + ".set(frequency = " + str(channel.frequency) + "*MHz, amplitude = " + str(channel.amplitude) + ", phase = (" + str(channel.phase) + ")/360)\n")    
        if channel.state == 1:
            file.write(indentation + "self.%s"%config.slow_dds_channels[index] + ".cfg_sw(True) \n")
        elif channel.state == 0:
            file.write(indentation + "self.%s"%config.slow_dds_channels[index] + ".cfg_sw(False) \n")
    file.close()




    
