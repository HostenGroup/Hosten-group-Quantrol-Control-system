from artiq.experiment import *
import numpy as np
from scipy.io import loadmat
import os
from datetime import datetime
from pathlib import Path 
import sys 
sys.path.append(str(Path(__file__).resolve().parent.parent)) 
import main.config as config 

save_sampled_box_checked = False
camera_box_checked = False

class run_experiment(EnvExperiment):
    def build(self):
        self.setattr_device('core')
        
        # Urukul 0
        self.setattr_device('urukul0_cpld')
        self.setattr_device('urukul0_ch0')
        self.setattr_device('urukul0_ch1')
        self.setattr_device('urukul0_ch2')
        self.setattr_device('urukul0_ch3')
        
        # Urukul 1
        self.setattr_device('urukul1_cpld')
        self.setattr_device('urukul1_ch0')
        self.setattr_device('urukul1_ch1')
        self.setattr_device('urukul1_ch2')
        self.setattr_device('urukul1_ch3')
        
        # Urukul 2
        self.setattr_device('urukul2_cpld')
        self.setattr_device('urukul2_ch0')
        self.setattr_device('urukul2_ch1')
        self.setattr_device('urukul2_ch2')
        self.setattr_device('urukul2_ch3')
        
        # TTLs
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
        
        # DAC & Sampler
        self.setattr_device('zotino0')
        self.setattr_device('sampler0')
        
        self.dds_cpld: CPLD = self.get_device("urukul2_cpld")
        self.dds_ch: AD9910 = self.get_device("urukul2_ch2")
        
        kernel_invariants = getattr(self, "kernel_invariants", set())
        self.kernel_invariants = kernel_invariants | {"dds_cpld", "dds_ch"}
        self.dtt = list(np.linspace(1.000000, 2.000000, 50))

    @kernel
    def init_dds(self, dds):
        dds.init()
        dds.set_att(6.*dB)
        dds.cfg_sw(False)
    
    @kernel
    def config_raman(self, dds, cpld):
        dds.set(frequency=80*MHz, phase=0.0, amplitude=0.2, profile=1)
        dds.set(frequency=80*MHz, phase=0.0, amplitude=0.01, profile=2)
        delay(10*us)
        cpld.set_profile(1)
        delay(20*us)   

    @kernel
    def run(self):
        # 1. ALWAYS RESET CORE FIRST
        self.core.reset()
        self.core.break_realtime()

        # 2. INITIALIZE ALL CPLDs (Crucial to prevent SPI bus hangs)
        self.urukul0_cpld.init()
        self.urukul1_cpld.init()
        self.dds_cpld.init()
        self.zotino0.init()
        delay(1*ms)

        # 3. INITIALIZE ALL USED DDS CHANNELS
        self.init_dds(self.urukul0_ch0)
        self.init_dds(self.urukul0_ch1)
        self.init_dds(self.urukul0_ch2)
        self.init_dds(self.urukul0_ch3)
        self.init_dds(self.urukul1_ch0)
        self.init_dds(self.urukul1_ch1)
        self.init_dds(self.urukul1_ch2)
        self.init_dds(self.urukul1_ch3)
        self.init_dds(self.urukul2_ch0)
        self.init_dds(self.urukul2_ch1)
        self.init_dds(self.dds_ch)
        self.init_dds(self.urukul2_ch3)
        
        # 4. CONFIGURE STATIC HARDWARE ONCE
        self.config_raman(self.dds_ch, self.dds_cpld)
        self.dds_ch.cfg_sw(False)
        
        delay(3*s)
        
        # --- Pre-load static Zotino voltages ---
        self.zotino0.write_dac(0, 0.0005)
        self.zotino0.write_dac(1, -4.5)
        self.zotino0.write_dac(2, 0.025)
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
        delay(1*ms) # brief timeline advance after SPI dump

        # --- Pre-load static Urukul settings (Using decimals to save CPU math) ---
        self.urukul0_ch0.set_att(0.0*dB) 
        self.urukul0_ch0.set(frequency=225.85*MHz, amplitude=0.9, phase=0.0)
        self.urukul0_ch0.sw.on() 
        self.urukul0_ch1.set_att(0.5*dB) 
        self.urukul0_ch1.set(frequency=381.25*MHz, amplitude=0.3, phase=0.0)
        self.urukul0_ch1.sw.on() 
        self.urukul0_ch2.set_att(6.5*dB) 
        self.urukul0_ch2.set(frequency=80.0*MHz, amplitude=0.2, phase=0.0)
        self.urukul0_ch2.sw.off() 
        self.urukul0_ch3.set_att(7.0*dB) 
        self.urukul0_ch3.set(frequency=80.0*MHz, amplitude=0.2, phase=0.0)
        self.urukul0_ch3.sw.off() 
        
        self.urukul1_ch0.set_att(10.0*dB) 
        self.urukul1_ch0.set(frequency=80.0*MHz, amplitude=0.4, phase=0.0)
        self.urukul1_ch0.sw.off() 
        self.urukul1_ch1.set_att(0.5*dB) 
        self.urukul1_ch1.set(frequency=182.65*MHz, amplitude=0.3, phase=0.0)
        self.urukul1_ch1.sw.on() 
        self.urukul1_ch2.set_att(0.0*dB) 
        self.urukul1_ch2.set(frequency=365.319425*MHz, amplitude=0.29, phase=0.0)
        self.urukul1_ch2.sw.off() 
        self.urukul1_ch3.set_att(4.0*dB) 
        self.urukul1_ch3.set(frequency=228.555*MHz, amplitude=0.1, phase=0.0)
        self.urukul1_ch3.sw.on() 
        
        self.urukul2_ch0.set_att(0.0*dB) 
        self.urukul2_ch0.set(frequency=100.0*MHz, amplitude=1.0, phase=0.0)
        self.urukul2_ch0.sw.off() 
        self.urukul2_ch1.set_att(30.0*dB) 
        self.urukul2_ch1.set(frequency=80.0*MHz, amplitude=0.15, phase=0.0)
        self.urukul2_ch1.sw.off() 
        self.urukul2_ch3.set_att(0.0*dB) 
        self.urukul2_ch3.set(frequency=80.0*MHz, amplitude=0.7, phase=0.0)
        self.urukul2_ch3.sw.on() 
        
        self.core.break_realtime() # Clear accumulated computation time before main loop
        inputs = [0.0]*8

        for run_index in range(1):
            if run_index == 0:
                for _ in range(10):
                    self.ttl8.pulse(1*ms)
                    self.ttl9.pulse(1*ms)
                    delay(200*ms)
            
            camera_enabled = True
            delay(100*ns)
            
            # --- Beginning of the Scan ---
            for step1 in range(100):
                self.core.break_realtime() # Small slack buffer per loop
                dtt = self.dtt[step1]
                
                #Edge number 0 name of edge: DefaulT
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
                self.ttl11.on()
                self.ttl12.on()
                self.ttl13.off()
                self.ttl14.off()
                self.ttl15.off()
                
                # NOTE: Zotino and Urukul statics were moved OUTSIDE the loop!
                
                #Edge number 1 name of edge: on
                delay(1.0*us)
                self.dds_ch.set_profile(1) 
                delay(0.5*us)
                self.urukul2_ch2.sw.on()
                delay(1.0*us)
                self.urukul2_ch2.sw.off()
                delay(0.5*us)
                self.dds_ch.set_profile(2)
                delay(0.5*us)
                self.urukul2_ch2.sw.on()
                delay(1.0*us)
                self.urukul2_ch2.sw.off()
                delay(0.5*us)
                self.dds_ch.set_profile(1)
                delay(0.5*us)
                self.urukul2_ch2.sw.on()          
                delay(1.0*us)
                self.urukul2_ch2.sw.off()
                delay(0.5*us)
                self.dds_ch.set_profile(2)
                delay(0.5*us)
                self.urukul2_ch2.sw.on()
                delay(1.0*us)
                self.urukul2_ch2.sw.off()
                #Edge number 3 name of edge: hold
                delay(1*s) 
                if not camera_enabled: 
                    break 

        self.print_end_exp()

    @rpc
    def print_end_exp(self):
        print("End of experiment")