from artiq.experiment import *
import numpy as np
from scipy.io import loadmat
import os
import shutil
from datetime import datetime
from pathlib import Path 
import sys 
sys.path.append(str(Path(__file__).resolve().parent.parent)) 
import main.config as config 

class run_experiment(EnvExperiment):
    def build(self):
        self.setattr_device('core')
        self.setattr_device('urukul0_cpld')
        self.setattr_device('urukul0_ch0')
        self.setattr_device('urukul0_ch1')
        self.setattr_device('urukul0_ch2')
        self.setattr_device('urukul0_ch3')
        self.setattr_device('urukul1_cpld')
        self.setattr_device('urukul1_ch0')
        self.setattr_device('urukul1_ch1')
        self.setattr_device('urukul1_ch2')
        self.setattr_device('urukul1_ch3')
        self.setattr_device('urukul2_cpld')
        self.setattr_device('urukul2_ch0')
        self.setattr_device('urukul2_ch1')
        self.setattr_device('urukul2_ch2')
        self.setattr_device('urukul2_ch3')
        self.setattr_device('ttl0')
        self.setattr_device('ttl1')
        self.setattr_device('ttl2')
        self.setattr_device('ttl3')
        self.setattr_device('ttl4')
        self.setattr_device('ttl5')
        self.setattr_device('ttl6')
        self.setattr_device('ttl7')
        self.setattr_device('ttl8')
        self.setattr_device('ttl9')
        self.setattr_device('ttl10')
        self.setattr_device('ttl11')
        self.setattr_device('ttl12')
        self.setattr_device('ttl13')
        self.setattr_device('ttl14')
        self.setattr_device('ttl15')
        self.setattr_device('zotino0')
        self.setattr_device('sampler0')
        self.dt = list(np.linspace(0.000000, 0.000000, 5))


    def prepare(self): 
        # Create persistent dataset (persist=True -> stored in LMDB database)
        self.set_dataset("data", [], persist=True,archive=False)

    @kernel
    def run(self):
        self.core.reset()
        self.core.break_realtime()
        inputs = [0.0]*8
        delay(1*s)
        samp1 = 0.0
        samp2 = 0.0
        for run_index in range(1):   # run loop including camera warm-up: warmup = 0, actual = 1, total = 1
            # Trigger camera 10 times without saving images
            if run_index == 0:
                for _ in range(10):
                    self.ttl8.pulse(1*ms)
                    self.ttl9.pulse(1*ms)
                    delay(200*ms)
            camera_enabled = True
            delay(100*ns)
            #Beginning of the Scan
            for step in range(5):
                dt = self.dt[step]
                #Edge number 0 name of edge: Default
                delay(1000*ns)
                self.ttl0.off()
                self.ttl1.off()
                self.ttl2.off()
                self.ttl3.off()
                self.ttl4.off()
                self.ttl5.off()
                self.ttl6.off()
                self.ttl7.off()
                delay(1000*ns)
                self.ttl8.off()
                self.ttl9.off()
                self.ttl10.off()
                self.ttl11.off()
                self.ttl12.off()
                self.ttl13.off()
                self.ttl14.off()
                self.ttl15.off()
                delay(1000*ns)
                self.zotino0.write_dac(0, 0.0005)
                self.zotino0.write_dac(1, -6.0)
                self.zotino0.write_dac(2, 3.0)
                self.zotino0.write_dac(3, -6.0)
                self.zotino0.write_dac(4, 0.0)
                self.zotino0.write_dac(5, 0.0)
                self.zotino0.write_dac(6, 0.0)
                self.zotino0.write_dac(7, 0.0)
                self.zotino0.write_dac(8, 0.75)
                self.zotino0.write_dac(9, 0.45)
                self.zotino0.write_dac(10, 0.0)
                self.zotino0.write_dac(11, 0.0)
                self.zotino0.write_dac(12, 0.0)
                self.zotino0.write_dac(13, 0.0)
                self.zotino0.write_dac(14, 0.0)
                self.zotino0.write_dac(15, 0.0)
                self.zotino0.load()
                self.urukul0_ch0.set_att((0.0)*dB) 
                self.urukul0_ch0.set(frequency = (225.85)*MHz, amplitude = (90.0)/100 , phase = (0.0)/360)
                self.urukul0_ch0.sw.on() 
                self.urukul0_ch1.set_att((0.5)*dB) 
                self.urukul0_ch1.set(frequency = (381.25)*MHz, amplitude = (30.0)/100 , phase = (0.0)/360)
                self.urukul0_ch1.sw.on() 
                self.urukul0_ch2.set_att((6.0)*dB) 
                self.urukul0_ch2.set(frequency = (80.0)*MHz, amplitude = (20.0)/100 , phase = (0.0)/360)
                self.urukul0_ch2.sw.off() 
                self.urukul0_ch3.set_att((6.0)*dB) 
                self.urukul0_ch3.set(frequency = (80.0)*MHz, amplitude = (20.0)/100 , phase = (0.0)/360)
                self.urukul0_ch3.sw.off() 
                self.urukul1_ch0.set_att((10.0)*dB) 
                self.urukul1_ch0.set(frequency = (80.0)*MHz, amplitude = (40.0)/100 , phase = (0.0)/360)
                self.urukul1_ch0.sw.off() 
                self.urukul1_ch1.set_att((0.5)*dB) 
                self.urukul1_ch1.set(frequency = (182.0)*MHz, amplitude = (30.0)/100 , phase = (0.0)/360)
                self.urukul1_ch1.sw.on() 
                self.urukul1_ch2.set_att((0.0)*dB) 
                self.urukul1_ch2.set(frequency = (365.32)*MHz, amplitude = (29.0)/100 , phase = (0.0)/360)
                self.urukul1_ch2.sw.off() 
                self.urukul1_ch3.set_att((4.0)*dB) 
                self.urukul1_ch3.set(frequency = (228.24)*MHz, amplitude = (10.0)/100 , phase = (0.0)/360)
                self.urukul1_ch3.sw.on() 
                self.urukul2_ch0.set_att((0.0)*dB) 
                self.urukul2_ch0.set(frequency = (100.0)*MHz, amplitude = (100.0)/100 , phase = (0.0)/360)
                self.urukul2_ch0.sw.off() 
                self.urukul2_ch1.set_att((31.5)*dB) 
                self.urukul2_ch1.set(frequency = (80.0)*MHz, amplitude = (15.0)/100 , phase = (0.0)/360)
                self.urukul2_ch1.sw.off() 
                self.urukul2_ch2.set_att((31.5)*dB) 
                self.urukul2_ch2.set(frequency = (80.0)*MHz, amplitude = (20.0)/100 , phase = (0.0)/360)
                self.urukul2_ch2.sw.off() 
                self.urukul2_ch3.set_att((0.0)*dB) 
                self.urukul2_ch3.set(frequency = (80.0)*MHz, amplitude = (70.0)/100 , phase = (0.0)/360)
                self.urukul2_ch3.sw.on() 
                #Edge number 1 name of edge: sample
                delay((10.0)*ms)
                # Sampler input readout
                self.sampler0.sample(inputs)
                samp1 = inputs[1]
                samp2 = inputs[2]
                #Edge number 2 name of edge: save
                delay((10.0)*ms)
                for i in range(1, (0+1)):   # ramp up loop 
                    delay((400.000000000000/0)*ms)  # for ramp up: time devided by steps 
                #Edge number 3 name of edge: end

                # For save sample variables
                if camera_enabled:
                    run_index = 1-1   # real number of runs 
                    self.store_sample(run_index, step, samp1, samp2)

                #exiting the scan at the first step if camera is not enabled 
                if not camera_enabled: 
                    break 

        self.copy_dataset_file()  # add saved sampled variables to a txt file 

        self.print_end_exp()  # print end of experiment in the end of the run 

    @rpc
    def print_end_exp(self):
        print("End of experiment")

    @rpc
    def store_sample(self, run_index, step, samp1, samp2):
        self.append_to_dataset("data", (int(run_index), int(step), samp1, samp2))

    @rpc
    def copy_dataset_file(self):
        # Define where you want the copy saved
        source_file = Path(__file__).parent.parent / "dataset_db.pyon"
 
        today_folder = datetime.now().strftime("%Y%m%d")
        target_directory = Path(config.experiment_data_root) / "save sampled variables"  / today_folder 
        target_directory.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        target_file = target_directory / f"dataset_db_copy_{timestamp}.txt"
        shutil.copy2(source_file, target_file)
