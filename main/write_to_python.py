import os
from sympy import simplify
import config
from scipy.io import savemat
from datetime import datetime
from update import closest_key


def create_experiment(self, run_continuous = False, multiple_runs = False): # owl
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
    
    #Creating functions to calculate derived variables
    for variable in self.experiment.derived_variables:
        file.write(indentation + "def calculate_%s(%s) -> TFloat:\n"%(variable.name, variable.arguments))
        indentation += "    "
        file.write(indentation + "return %s \n\n" %variable.function)
        indentation = indentation[:-4]
    #Experimental description
    file.write(indentation + "class " + file_name[:-3] + "(EnvExperiment):\n")
    indentation += "    "
    file.write(indentation + "def build(self):\n")
    indentation += "    "
    # Setting the devices to be used 
    for device in config.list_of_devices_for_use:
        file.write(indentation + "self.setattr_device('%s')\n" %device)

    # If lookup variables are requested create and load them
    for index, lookup_variable in enumerate(self.experiment.lookup_variables):
        # We first save the lookup list and then load it from the python description of the experiment
        if lookup_variable.lookup_list_name != "":
            temp_lookup_list_path = "./temp lookup variables/temp_%d_"%index +lookup_variable.lookup_list_name
            savemat(temp_lookup_list_path, {'array':lookup_variable.lookup_list})
            file.write(indentation + "self.%s"%lookup_variable.name + " = list(loadmat('%s')['array'][0])\n"%temp_lookup_list_path)
    
    # If scan is needed prepare the variables
    if self.experiment.do_scan == True and self.experiment.scanned_variables_count > 0:
        #iterating over valid (not "None") scanned variables and creating an array to be used as a collection of names
        var_names = ""
        for variable in self.experiment.scanned_variables:
            if variable.name != "None":
                file.write(indentation + "self.%s = np.linspace(%f, %f, %d)\n"%(variable.name, variable.min_val, variable.max_val, self.experiment.number_of_steps))
                var_names += variable.name + ", "
    file.write("\n")
    indentation = indentation[:-4]
    # Overwriting the run method
    file.write(indentation + "@kernel\n")
    file.write(indentation + "def run(self):\n")
    indentation += "    "
    file.write(indentation + "self.core.reset()\n")
    file.write(indentation + "self.core.break_realtime()\n")
    file.write(indentation + "inputs = [0.0]*8\n")
    file.write(indentation + "delay(1*s)\n") # this delay is added since our reference clock is 1GHz and self.core.break_realtime moves it forward by 15000 clock cycles
    
    # This is used to trigger the camera 10 times and discard those images
    if config.allow_skipping_images == True and self.experiment.skip_images:
        file.write(indentation + "# Triggering camera 10 times in the beginning of experiment\n")
        for val in config.camera_trigger_ttl:
            file.write(indentation + "self.ttl" + str(val) + ".off()\n")
        file.write(indentation + "delay(100*ms)\n")
        file.write(indentation + "for _ in range(10):\n")
        indentation += "    "
        for val in config.camera_trigger_ttl:
            file.write(indentation + "self.ttl" + str(val) + ".on()\n")
        file.write(indentation + "delay(100*ms)\n")
        for val in config.camera_trigger_ttl:
            file.write(indentation + "self.ttl" + str(val) + ".off()\n")
        file.write(indentation + "delay(100*ms)\n")
        
        indentation = indentation[:-4]
    
    # for inital value of derived variables 
    arguments = self.experiment.derived_variables
    for argument in arguments:
        file.write(indentation + argument.name + " = " + "float("+ argument.initial_value + ")" + "\n")

    warmup_runs = self.experiment.cam_trigger_off_runs if getattr(self.experiment, "cam_trigger_off", False) else 0
    actual_runs = self.experiment.number_of_runs if multiple_runs else 1
    if actual_runs <= 0:
        actual_runs = 1
    total_runs = warmup_runs + actual_runs
    run_loop_added = False

    # Create an infinite while loop if needs to run continuously
    if run_continuous:
        file.write(indentation + "while True:\n")
        indentation += "    "
        if warmup_runs > 0:
            file.write(indentation + "if not hasattr(self, '_cam_warmup_remaining'):\n")
            indentation += "    "
            file.write(indentation + "self._cam_warmup_remaining = %d\n" % warmup_runs)
            indentation = indentation[:-4]
            file.write(indentation + "if self._cam_warmup_remaining > 0:\n")
            indentation += "    "
            file.write(indentation + "camera_enabled = False\n")
            file.write(indentation + "self._cam_warmup_remaining -= 1\n")
            indentation = indentation[:-4]
            file.write(indentation + "else:\n")
            indentation += "    "
            file.write(indentation + "camera_enabled = True\n")
            indentation = indentation[:-4]
        else:
            file.write(indentation + "camera_enabled = True\n")

    # owl begin
    if not run_continuous:
        if total_runs > 1:
            file.write(indentation + "for run_index in range(%d):   # run loop including camera warm-up\n" % total_runs)
            indentation += "    "
            run_loop_added = True
            if warmup_runs > 0:
                file.write(indentation + "camera_enabled = (run_index >= %d)\n" % warmup_runs)
            else:
                file.write(indentation + "camera_enabled = True\n")
        else:
            file.write(indentation + "camera_enabled = True\n")
    # owl end

    # 10 ns delay to avoid collision of the last edge assignment of digital channels as there is at most camera_trigger_ttl channel changes at a given time stamp
    file.write(indentation + "delay(10*ns)\n")
    # If scan is needed 
    if self.experiment.do_scan == True and self.experiment.scanned_variables_count > 0:
        #making a scanning loop 
        #introduce a flag for multi and single variable scan
        file.write(indentation + "#Beginning of the Scan\n")
        file.write(indentation + "for step in range(%d):\n" %(self.experiment.number_of_steps))
        indentation += "    "
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
        if self.delta_t != 0 and flag_ramp_up_delay == False: #owltime 
            file.write(indentation + "delay((" + str(self.delta_t) + ")*ms)\n") 
        
        flag_ramp_up_delay = False
        #ADDING FOR LOOP FOR RAMP  # owl begin
        count_indentations = 0
        for variable in self.experiment.ramped_variables:
            if self.experiment.do_ramp == True and self.experiment.ramped_variables_count > 0:
                if variable.start_ID == self.experiment.sequence[edge_index].id and already_loop_for_edge[edge_index] == False: # fish
                    if edge_index != 0: # owl
                        flag_ramp_up = True
                        flag_ramp_up_delay = True
                        flag_ramp_variable = variable
                        file.write(indentation + "for i in range(1, (%d+1)):   # ramp up loop \n" %(variable.stepsramp)) 
                        already_loop_for_edge[edge_index] = True # fish
                        indentation += "    "
                        count_indentations = count_indentations + 1  # owl end

        
        #RPC for derived variable calculation # cowww
        if edge_index > 0:
            index_of_derived_variable = self.experiment.sequence[edge_index].derived_variable_requested
            if index_of_derived_variable != -1:
                variable = self.experiment.derived_variables[index_of_derived_variable]
                file.write(indentation + "%s = calculate_%s(%s)\n"%(variable.name, variable.name, variable.arguments))

        #DIGITAL CHANNEL CHANGES
        if config.dds_channels_number > 0:
            for index, channel in enumerate(self.experiment.sequence[edge_index].digital):
                if edge_index == 0 and index % 8 == 0: #adding a 5 ms delay to make changes into TTL channels
                    file.write(indentation + "delay(5*ms)\n")

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
            
            if edge_index == 0: #adding a 10 ns delay after 8 ttl channels because otherwise it ignores the first analog channel
                file.write(indentation + "delay(10*ns)\n")
       
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
        
        #ADDING DELAY RAMP  - to make ramp and scan compatible  
        if flag_ramp_up == True:             
            try:
                temp_text_ramp =  "((" + str(self.experiment.sequence[edge_index+1].for_python) + ")" + "-" + "(" + str(self.experiment.sequence[edge_index].for_python) + "))"
                temp_text_ramp = str(simplify(temp_text_ramp)) # simplify possible only when not scan
            except:
                temp_text_ramp =  "((" + str(self.experiment.sequence[edge_index+1].for_python) + ")" + "-" + "(" + str(self.experiment.sequence[edge_index].for_python) + "))"
            file.write(indentation + "delay((" + temp_text_ramp + "/" +str(flag_ramp_variable.stepsramp) + ")*ms)  # for ramp up: time devided by steps \n") 
        # owltime # fish end 
        
        # # owl begin
        if flag_ramp_up == True: 
            flag_ramp_up = False  
            #file.write(indentation + "print('%s %s = ', %s)\n" %(("Value of ramped variable: "), str(flag_ramp_variable.name), flag_ramp_variable.functionramp))
            for indent in range(count_indentations):
                indentation = indentation[:-4] 
        # owl end
            
    ###############################################################################################
    ############################# for continuous run AFTER experiment #############################
    ###############################################################################################

    if self.experiment.do_scan == True and self.experiment.scanned_variables_count > 0:
        indentation = indentation[:-4]
    if not run_continuous and run_loop_added:
        indentation = indentation[:-4]

    if self.experiment.cont_run_after_exp == True:
        if self.experiment.do_scan == True and self.experiment.scanned_variables_count > 0:
            indentation = indentation[:-4] 

        # self.function_to_write_cont_run_after_experiment(file)

        # Create an infinite while loop if needs to run continuously
        file.write(indentation + "while True:\n")
        indentation += "    "

        # 10 ns delay to avoid collision of the last edge assignment of digital channels as there is at most 8 channel changes at a given time stamp
        file.write(indentation + "delay(10*ns)\n")
        # If scan is needed 
        if self.experiment.do_scan == True and self.experiment.scanned_variables_count > 0:
            #making a scanning loop 
            #introduce a flag for multi and single variable scan
            file.write(indentation + "#Beginning of the Scan\n")
            file.write(indentation + "for step in range(%d):\n" %(self.experiment.number_of_steps))
            indentation += "    "
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
            if self.delta_t != 0 and flag_ramp_up_delay == False: #owltime 
                file.write(indentation + "delay((" + str(self.delta_t) + ")*ms)\n") 
            
            flag_ramp_up_delay = False
            #ADDING FOR LOOP FOR RAMP  # owl begin
            count_indentations = 0
            for variable in self.experiment.ramped_variables:
                if self.experiment.do_ramp == True and self.experiment.ramped_variables_count > 0:
                    if variable.start_ID == self.experiment.sequence[edge_index].id and already_loop_for_edge[edge_index] == False: # fish
                        if edge_index != 0: # owl
                            flag_ramp_up = True
                            flag_ramp_up_delay = True
                            flag_ramp_variable = variable
                            file.write(indentation + "for i in range(1, (%d+1)):   # ramp up loop \n" %(variable.stepsramp)) 
                            already_loop_for_edge[edge_index] = True # fish
                            indentation += "    "
                            count_indentations = count_indentations + 1  # owl end

            
            #RPC for derived variable calculation
            if edge_index > 0:
                index_of_derived_variable = self.experiment.sequence[edge_index].derived_variable_requested
                if index_of_derived_variable != -1:
                    variable = self.experiment.derived_variables[index_of_derived_variable]
                    file.write(indentation + "%s = calculate_%s(%s)\n"%(variable.name, variable.name, variable.arguments))

            #DIGITAL CHANNEL CHANGES
            if config.dds_channels_number > 0:
                for index, channel in enumerate(self.experiment.sequence[edge_index].digital):
                    if edge_index == 0 and index % 8 == 0: #adding a 5 ms delay to make changes into TTL channels
                        file.write(indentation + "delay(5*ms)\n")

                    if channel.changed == True:
                        if channel.value == 1: # 1 is on 
                            if index == 8: 
                                file.write(indentation + "self.ttl" + str(index) + ".off()\n") 
                            else:
                                file.write(indentation + "self.ttl" + str(index) + ".on()\n") 
                        else:
                            file.write(indentation + "self.ttl" + str(index) + ".off()\n") 
                
                if edge_index == 0: #adding a 10 ns delay after 8 ttl channels because otherwise it ignores the first analog channel
                    file.write(indentation + "delay(10*ns)\n")
        
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
            
            #ADDING DELAY RAMP  - to make ramp and scan compatible  
            if flag_ramp_up == True:             
                try:
                    temp_text_ramp =  "((" + str(self.experiment.sequence[edge_index+1].for_python) + ")" + "-" + "(" + str(self.experiment.sequence[edge_index].for_python) + "))"
                    temp_text_ramp = str(simplify(temp_text_ramp)) # simplify possible only when not scan
                except:
                    temp_text_ramp =  "((" + str(self.experiment.sequence[edge_index+1].for_python) + ")" + "-" + "(" + str(self.experiment.sequence[edge_index].for_python) + "))"
                file.write(indentation + "delay((" + temp_text_ramp + "/" +str(flag_ramp_variable.stepsramp) + ")*ms)  # for ramp up: time devided by steps \n") 
            # owltime # fish end 
            
            # # owl begin
            if flag_ramp_up == True: 
                flag_ramp_up = False  
                #file.write(indentation + "print('%s %s = ', %s)\n" %(("Value of ramped variable: "), str(flag_ramp_variable.name), flag_ramp_variable.functionramp))
                for indent in range(count_indentations):
                    indentation = indentation[:-4] 
            # owl end

        
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
            if index % 8 == 0: #adding a 5 ms delay to make changes for more than 8 TTL channels. There is a limit of the buffer size
                file.write(indentation + "delay(5*ms)\n")
            if channel.value == 0:
                file.write(indentation + "self.ttl" + str(index) + ".off()\n")
            elif channel.value == 1:
                file.write(indentation + "self.ttl" + str(index) + ".on()\n")        
        file.write(indentation + "delay(10*ns)\n")

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
            file.write(indentation + "self.urukul" + str(urukul_num) + "_ch" + str(channel_num) + ".set(frequency = " + str(channel.frequency.value) + "*MHz, amplitude = " + str(channel.amplitude.value) + ", phase = (" + str(channel.phase.value) + ")/360)\n")    
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