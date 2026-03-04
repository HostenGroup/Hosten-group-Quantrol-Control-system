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

def calculate_SSB(SSB,sampleSPOL)->TFloat: 
    return SSB+(-0.780+sampleSPOL)*0.20 

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
        self.df = list(np.linspace(178.000000, 181.000000, 50))
        self.datt = list(np.linspace(0.000000, 25.000000, 15))


    def prepare(self): 
        # Create persistent dataset (persist=True -> stored in LMDB database)
        self.set_dataset("data", [], persist=True,archive=False)

    @kernel
    def run(self):
        self.core.reset()
        self.core.break_realtime()
        inputs = [0.0]*8
        delay(1*s)
        SSB = float(228.5)
        test = 0.0
        T_exp_ = 0.35
        dt = 0.0
        sampleSPOL = 0.0
        samplePPOL = 0.0
        MWpi = 0.118
        for run_index in range(6):   # run loop including camera warm-up: warmup = 5, actual = 1, total = 6
            # Trigger camera 10 times without saving images
            if run_index == 5:
                for _ in range(10):
                    self.ttl8.pulse(1*ms)
                    self.ttl9.pulse(1*ms)
                    delay(200*ms)
            camera_enabled = (run_index >= 5)   # warm-up run check
            delay(100*ns)
            #Beginning of the Scan
            for step1 in range(15):
                for step in range(50):
                    df = self.df[step]
                    datt = self.datt[step1]
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
                    self.ttl11.on()
                    self.ttl12.off()
                    self.ttl13.off()
                    self.ttl14.off()
                    self.ttl15.off()
                    delay(1000*ns)
                    self.zotino0.write_dac(0, 0.0005)
                    self.zotino0.write_dac(1, -5.0)
                    self.zotino0.write_dac(2, 3.0)
                    self.zotino0.write_dac(3, -5.0)
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
                    self.urukul0_ch2.set_att((0.0)*dB) 
                    self.urukul0_ch2.set(frequency = (80.0)*MHz, amplitude = (20.0)/100 , phase = (0.0)/360)
                    self.urukul0_ch2.sw.off() 
                    self.urukul0_ch3.set_att((0.0)*dB) 
                    self.urukul0_ch3.set(frequency = (80.0)*MHz, amplitude = (20.0)/100 , phase = (0.0)/360)
                    self.urukul0_ch3.sw.off() 
                    self.urukul1_ch0.set_att((10.0)*dB) 
                    self.urukul1_ch0.set(frequency = (80.0)*MHz, amplitude = (40.0)/100 , phase = (0.0)/360)
                    self.urukul1_ch0.sw.off() 
                    self.urukul1_ch1.set_att((0.5)*dB) 
                    self.urukul1_ch1.set(frequency = (self.df[step])*MHz, amplitude = (30.0)/100 , phase = (0.0)/360)
                    self.urukul1_ch1.sw.on() 
                    self.urukul1_ch2.set_att((0.0)*dB) 
                    self.urukul1_ch2.set(frequency = (365.319)*MHz, amplitude = (29.0)/100 , phase = (0.0)/360)
                    self.urukul1_ch2.sw.off() 
                    self.urukul1_ch3.set_att((4.0)*dB) 
                    self.urukul1_ch3.set(frequency = (SSB)*MHz, amplitude = (10.0)/100 , phase = (0.0)/360)
                    self.urukul1_ch3.sw.on() 
                    self.urukul2_ch0.set_att((0.0)*dB) 
                    self.urukul2_ch0.set(frequency = (100.0)*MHz, amplitude = (100.0)/100 , phase = (0.0)/360)
                    self.urukul2_ch0.sw.off() 
                    self.urukul2_ch1.set_att((30.0)*dB) 
                    self.urukul2_ch1.set(frequency = (80.0)*MHz, amplitude = (15.0)/100 , phase = (0.0)/360)
                    self.urukul2_ch1.sw.off() 
                    self.urukul2_ch2.set_att((20.0)*dB) 
                    self.urukul2_ch2.set(frequency = (80.0)*MHz, amplitude = (20.0)/100 , phase = (0.0)/360)
                    self.urukul2_ch2.sw.off() 
                    self.urukul2_ch3.set_att((0.0)*dB) 
                    self.urukul2_ch3.set(frequency = (80.0)*MHz, amplitude = (70.0)/100 , phase = (0.0)/360)
                    self.urukul2_ch3.sw.on() 
                    #Edge number 1 name of edge: Flush begin
                    delay((10.0)*ms)
                    self.zotino0.write_dac(7, 5.0)
                    self.zotino0.load()
                    self.urukul1_ch2.set_att((0.0)*dB) 
                    self.urukul1_ch2.set(frequency = (365.319)*MHz, amplitude = (29.0)/100 , phase = (0.0)/360)
                    self.urukul1_ch2.sw.off() 
                    #Edge number 2 name of edge: Turn on 780 (locking)
                    delay((100.0)*ms)
                    self.urukul2_ch1.set_att((30.0)*dB) 
                    self.urukul2_ch1.set(frequency = (80.0)*MHz, amplitude = (15.0)/100 , phase = (0.0)/360)
                    self.urukul2_ch1.sw.on() 
                    self.urukul2_ch2.set_att((10.0)*dB) 
                    self.urukul2_ch2.set(frequency = (80.0)*MHz, amplitude = (20.0)/100 , phase = (0.0)/360)
                    self.urukul2_ch2.sw.off() 
                    #Edge number 3 name of edge: Sample sPol 780
                    delay((60.0)*ms)
                    # Sampler input readout
                    self.sampler0.sample(inputs)
                    sampleSPOL = inputs[1]
                    #Edge number 4 name of edge: Turn off 780 (locking)
                    delay((70.0)*ms)
                    self.ttl11.off()
                    self.zotino0.write_dac(9, 0.45)
                    self.zotino0.load()
                    self.urukul2_ch1.set_att((30.0)*dB) 
                    self.urukul2_ch1.set(frequency = (80.0)*MHz, amplitude = (15.0)/100 , phase = (0.0)/360)
                    self.urukul2_ch1.sw.off() 
                    #Edge number 5 name of edge: Flush end
                    delay((20.0)*ms)
                    self.zotino0.write_dac(7, 0.0)
                    self.zotino0.load()
                    #Edge number 6 name of edge: Z cam trigger (background)
                    delay((1.0)*ms)
                    if camera_enabled:
                        self.ttl8.on()
                    else:
                        self.ttl8.off()
                    #Edge number 7 name of edge: Exposure begin
                    delay((0.0299999999999727)*ms)
                    self.ttl8.off()
                    self.urukul0_ch2.set_att((0.0)*dB) 
                    self.urukul0_ch2.set(frequency = (80.0)*MHz, amplitude = (20.0)/100 , phase = (0.0)/360)
                    self.urukul0_ch2.sw.on() 
                    self.urukul1_ch0.set_att((10.0)*dB) 
                    self.urukul1_ch0.set(frequency = (80.0)*MHz, amplitude = (40.0)/100 , phase = (0.0)/360)
                    self.urukul1_ch0.sw.on() 
                    #Edge number 8 name of edge: Exposure end/coils on
                    delay((0.300000000000011)*ms)
                    self.zotino0.write_dac(0, -0.75)
                    self.zotino0.write_dac(6, 5.0)
                    self.zotino0.load()
                    self.urukul0_ch2.set_att((0.0)*dB) 
                    self.urukul0_ch2.set(frequency = (80.0)*MHz, amplitude = (20.0)/100 , phase = (0.0)/360)
                    self.urukul0_ch2.sw.off() 
                    self.urukul1_ch0.set_att((10.0)*dB) 
                    self.urukul1_ch0.set(frequency = (80.0)*MHz, amplitude = (40.0)/100 , phase = (0.0)/360)
                    self.urukul1_ch0.sw.off() 
                    #Edge number 9 name of edge: Cont Load begin
                    delay((10.0)*ms)
                    self.urukul0_ch1.set_att((0.5)*dB) 
                    self.urukul0_ch1.set(frequency = (387.25)*MHz, amplitude = (30.0)/100 , phase = (0.0)/360)
                    self.urukul0_ch1.sw.on() 
                    self.urukul0_ch2.set_att((0.0)*dB) 
                    self.urukul0_ch2.set(frequency = (80.0)*MHz, amplitude = (20.0)/100 , phase = (0.0)/360)
                    self.urukul0_ch2.sw.on() 
                    self.urukul0_ch3.set_att((0.0)*dB) 
                    self.urukul0_ch3.set(frequency = (80.0)*MHz, amplitude = (20.0)/100 , phase = (0.0)/360)
                    self.urukul0_ch3.sw.on() 
                    self.urukul1_ch0.set_att((10.0)*dB) 
                    self.urukul1_ch0.set(frequency = (80.0)*MHz, amplitude = (40.0)/100 , phase = (0.0)/360)
                    self.urukul1_ch0.sw.on() 
                    #Edge number 10 name of edge: Cont Load end
                    delay((499.9999999999999)*ms)
                    self.ttl8.off()
                    self.urukul1_ch0.set_att((27.0)*dB) 
                    self.urukul1_ch0.set(frequency = (80.0)*MHz, amplitude = (40.0)/100 , phase = (0.0)/360)
                    self.urukul1_ch0.sw.off() 
                    #Edge number 11 name of edge: 1527 Ramp begin
                    for i in range(1, (20+1)):   # ramp up loop 
                        self.zotino0.write_dac(9, 0.45+0.0225*i)
                        self.zotino0.load()
                        self.urukul0_ch2.set_att((19.0)*dB) 
                        self.urukul0_ch2.set(frequency = (80.0)*MHz, amplitude = (20.0)/100 , phase = (0.0)/360)
                        self.urukul0_ch2.sw.on() 
                        self.urukul0_ch3.set_att((19.0)*dB) 
                        self.urukul0_ch3.set(frequency = (80.0)*MHz, amplitude = (20.0)/100 , phase = (0.0)/360)
                        self.urukul0_ch3.sw.on() 
                        self.urukul1_ch0.set_att((27.0)*dB) 
                        self.urukul1_ch0.set(frequency = (80.0)*MHz, amplitude = (40.0)/100 , phase = (0.0)/360)
                        self.urukul1_ch0.sw.off() 
                        delay((50.00000000000000/20)*ms)  # for ramp up: time devided by steps 
                    #Edge number 12 name of edge: 1527 Ramp end
                    self.zotino0.write_dac(9, 0.9)
                    self.zotino0.load()
                    self.urukul0_ch2.set_att((19.0)*dB) 
                    self.urukul0_ch2.set(frequency = (80.0)*MHz, amplitude = (20.0)/100 , phase = (0.0)/360)
                    self.urukul0_ch2.sw.off() 
                    self.urukul0_ch3.set_att((19.0)*dB) 
                    self.urukul0_ch3.set(frequency = (80.0)*MHz, amplitude = (20.0)/100 , phase = (0.0)/360)
                    self.urukul0_ch3.sw.off() 
                    self.urukul1_ch0.set_att((27.0)*dB) 
                    self.urukul1_ch0.set(frequency = (80.0)*MHz, amplitude = (40.0)/100 , phase = (0.0)/360)
                    self.urukul1_ch0.sw.off() 
                    #Edge number 13 name of edge: Storage begin (free space det.)
                    self.zotino0.write_dac(6, 0.0)
                    self.zotino0.write_dac(9, 0.45)
                    self.zotino0.load()
                    #Edge number 14 name of edge: Off coils / Quant axis By
                    self.zotino0.write_dac(0, 0.0005)
                    self.zotino0.write_dac(1, -4.0)
                    self.zotino0.write_dac(3, -0.95)
                    self.zotino0.load()
                    #Edge number 15 name of edge: Cool/Rep ramp begin
                    delay((1.0)*ms)
                    for i in range(1, (20+1)):   # ramp up loop 
                        self.zotino0.write_dac(2, 3+0.3*i)
                        self.zotino0.load()
                        self.urukul0_ch0.set_att((0.0)*dB) 
                        self.urukul0_ch0.set(frequency = (225.85-0.315*i)*MHz, amplitude = (90.0)/100 , phase = (0.0)/360)
                        self.urukul0_ch0.sw.on() 
                        self.urukul0_ch1.set_att((0.5)*dB) 
                        self.urukul0_ch1.set(frequency = (386.5+4.15*i)*MHz, amplitude = (30.0)/100 , phase = (0.0)/360)
                        self.urukul0_ch1.sw.on() 
                        delay((10.00000000000000/20)*ms)  # for ramp up: time devided by steps 
                    #Edge number 16 name of edge: Cool/Rep ramp end
                    self.zotino0.write_dac(2, 9.0)
                    self.zotino0.load()
                    self.urukul0_ch0.set_att((0.0)*dB) 
                    self.urukul0_ch0.set(frequency = (219.55)*MHz, amplitude = (90.0)/100 , phase = (0.0)/360)
                    self.urukul0_ch0.sw.on() 
                    self.urukul0_ch1.set_att((0.5)*dB) 
                    self.urukul0_ch1.set(frequency = (470.0)*MHz, amplitude = (30.0)/100 , phase = (0.0)/360)
                    self.urukul0_ch1.sw.on() 
                    #Edge number 17 name of edge: Opt pump begin
                    delay((25.0)*ms)
                    self.urukul0_ch2.set_att((18.0)*dB) 
                    self.urukul0_ch2.set(frequency = (80.0)*MHz, amplitude = (20.0)/100 , phase = (0.0)/360)
                    self.urukul0_ch2.sw.on() 
                    self.urukul1_ch0.set_att((27.0)*dB) 
                    self.urukul1_ch0.set(frequency = (80.0)*MHz, amplitude = (40.0)/100 , phase = (0.0)/360)
                    self.urukul1_ch0.sw.on() 
                    #Edge number 18 name of edge: Opt pump end
                    delay((0.04999999999999716)*ms)
                    self.urukul0_ch2.set_att((18.0)*dB) 
                    self.urukul0_ch2.set(frequency = (80.0)*MHz, amplitude = (20.0)/100 , phase = (0.0)/360)
                    self.urukul0_ch2.sw.off() 
                    self.urukul1_ch0.set_att((27.0)*dB) 
                    self.urukul1_ch0.set(frequency = (80.0)*MHz, amplitude = (40.0)/100 , phase = (0.0)/360)
                    self.urukul1_ch0.sw.off() 
                    #Edge number 19 name of edge: Cool/Rep ramp begin
                    delay((1.0)*ms)
                    for i in range(1, (20+1)):   # ramp up loop 
                        self.urukul0_ch0.set_att((0.0)*dB) 
                        self.urukul0_ch0.set(frequency = (219.55+0.315*i)*MHz, amplitude = (90.0)/100 , phase = (0.0)/360)
                        self.urukul0_ch0.sw.on() 
                        self.urukul0_ch1.set_att((0.5)*dB) 
                        self.urukul0_ch1.set(frequency = (470-4.40*i)*MHz, amplitude = (30.0)/100 , phase = (0.0)/360)
                        self.urukul0_ch1.sw.on() 
                        delay((10.00000000000000/20)*ms)  # for ramp up: time devided by steps 
                    #Edge number 20 name of edge: Cool/Rep ramp end
                    self.urukul0_ch0.set_att((0.0)*dB) 
                    self.urukul0_ch0.set(frequency = (225.85)*MHz, amplitude = (90.0)/100 , phase = (0.0)/360)
                    self.urukul0_ch0.sw.on() 
                    self.urukul0_ch1.set_att((0.5)*dB) 
                    self.urukul0_ch1.set(frequency = (381.25)*MHz, amplitude = (30.0)/100 , phase = (0.0)/360)
                    self.urukul0_ch1.sw.on() 
                    #Edge number 21 name of edge: Push begin
                    delay((10.0)*ms)
                    self.zotino0.write_dac(7, 5.0)
                    self.zotino0.load()
                    #Edge number 22 name of edge: Push end
                    delay((0.04999999999989768)*ms)
                    self.zotino0.write_dac(7, 0.0)
                    self.zotino0.load()
                    #Edge number 23 name of edge: Quant axis Bz
                    delay((1.0)*ms)
                    self.zotino0.write_dac(2, 1.55)
                    self.zotino0.write_dac(3, 1.0)
                    self.zotino0.load()
                    #Edge number 24 name of edge: MW pi-pulse begin
                    delay((30.0)*ms)
                    self.urukul1_ch2.set_att((0.0)*dB) 
                    self.urukul1_ch2.set(frequency = (365.319)*MHz, amplitude = (29.0)/100 , phase = (0.0)/360)
                    self.urukul1_ch2.sw.on() 
                    #Edge number 25 name of edge: MW pi-pulse end
                    delay((0.1180000000001087)*ms)
                    self.urukul1_ch2.set_att((0.0)*dB) 
                    self.urukul1_ch2.set(frequency = (365.319)*MHz, amplitude = (29.0)/100 , phase = (0.0)/360)
                    self.urukul1_ch2.sw.off() 
                    #Edge number 26 name of edge: Repump begin
                    self.urukul1_ch0.set_att((27.0)*dB) 
                    self.urukul1_ch0.set(frequency = (80.0)*MHz, amplitude = (40.0)/100 , phase = (0.0)/360)
                    self.urukul1_ch0.sw.on() 
                    #Edge number 27 name of edge: Repump end
                    delay((1.0)*ms)
                    self.urukul1_ch0.set_att((27.0)*dB) 
                    self.urukul1_ch0.set(frequency = (80.0)*MHz, amplitude = (40.0)/100 , phase = (0.0)/360)
                    self.urukul1_ch0.sw.off() 
                    #Edge number 28 name of edge: MW pi-pulse begin
                    self.urukul1_ch2.set_att((0.0)*dB) 
                    self.urukul1_ch2.set(frequency = (365.319)*MHz, amplitude = (29.0)/100 , phase = (0.0)/360)
                    self.urukul1_ch2.sw.on() 
                    #Edge number 29 name of edge: MW pi-pulse end
                    delay((0.117999999999995)*ms)
                    self.urukul1_ch2.set_att((0.0)*dB) 
                    self.urukul1_ch2.set(frequency = (365.319)*MHz, amplitude = (29.0)/100 , phase = (0.0)/360)
                    self.urukul1_ch2.sw.off() 
                    #Edge number 30 name of edge: Push begin
                    self.zotino0.write_dac(7, 5.0)
                    self.zotino0.load()
                    #Edge number 31 name of edge: Push end
                    delay((0.04999999999999716)*ms)
                    self.zotino0.write_dac(7, 0.0)
                    self.zotino0.load()
                    #Edge number 32 name of edge: Quant By ramp begin
                    delay((1.0)*ms)
                    for i in range(1, (20+1)):   # ramp up loop 
                        self.zotino0.write_dac(2, 1.55+0.3*i)
                        self.zotino0.write_dac(3, -0.95)
                        self.zotino0.load()
                        delay((10.00000000000000/20)*ms)  # for ramp up: time devided by steps 
                    #Edge number 33 name of edge: Quant By ramp end
                    self.zotino0.write_dac(2, 9.0)
                    self.zotino0.load()
                    #Edge number 34 name of edge: Raman trigger
                    delay((44.98)*ms)
                    self.ttl10.on()
                    #Edge number 35 name of edge: Raman 2 pulse begin
                    delay((0.01999999999999602)*ms)
                    self.ttl10.off()
                    self.urukul2_ch2.set_att((self.datt[step1])*dB) 
                    self.urukul2_ch2.set(frequency = (80.0)*MHz, amplitude = (20.0)/100 , phase = (0.0)/360)
                    self.urukul2_ch2.sw.on() 
                    #Edge number 36 name of edge: Raman 2 pulse end
                    delay((0.04999999999991189)*ms)
                    self.urukul2_ch2.set_att((self.datt[step1])*dB) 
                    self.urukul2_ch2.set(frequency = (80.0)*MHz, amplitude = (20.0)/100 , phase = (0.0)/360)
                    self.urukul2_ch2.sw.off() 
                    #Edge number 37 name of edge: Push begin
                    delay((1.0)*ms)
                    self.zotino0.write_dac(7, 5.0)
                    self.zotino0.load()
                    #Edge number 38 name of edge: Push end
                    delay((0.04999999999999716)*ms)
                    self.zotino0.write_dac(7, 0.0)
                    self.zotino0.load()
                    #Edge number 39 name of edge: Storage end (free space det.)
                    delay((3.514000000000095)*ms)
                    self.zotino0.write_dac(8, 0.01)
                    self.zotino0.write_dac(9, 0.01)
                    self.zotino0.load()
                    #Edge number 40 name of edge: Z cam trigger (meas)
                    delay((1.0)*ms)
                    if camera_enabled:
                        self.ttl8.on()
                    else:
                        self.ttl8.off()
                    #Edge number 41 name of edge: Exposure begin
                    delay((0.03000000000000114)*ms)
                    self.ttl8.off()
                    self.urukul0_ch2.set_att((0.0)*dB) 
                    self.urukul0_ch2.set(frequency = (80.0)*MHz, amplitude = (20.0)/100 , phase = (0.0)/360)
                    self.urukul0_ch2.sw.on() 
                    self.urukul1_ch0.set_att((10.0)*dB) 
                    self.urukul1_ch0.set(frequency = (80.0)*MHz, amplitude = (40.0)/100 , phase = (0.0)/360)
                    self.urukul1_ch0.sw.on() 
                    #Edge number 42 name of edge: Exposure end
                    delay((0.2999999999999972)*ms)
                    self.zotino0.write_dac(8, 0.75)
                    self.zotino0.write_dac(9, 0.45)
                    self.zotino0.load()
                    self.urukul0_ch2.set_att((0.0)*dB) 
                    self.urukul0_ch2.set(frequency = (80.0)*MHz, amplitude = (20.0)/100 , phase = (0.0)/360)
                    self.urukul0_ch2.sw.off() 
                    self.urukul1_ch0.set_att((10.0)*dB) 
                    self.urukul1_ch0.set(frequency = (80.0)*MHz, amplitude = (40.0)/100 , phase = (0.0)/360)
                    self.urukul1_ch0.sw.off() 
                    #Edge number 43 name of edge: Return dipole trap / Bias fields
                    delay((0.1000000000000085)*ms)
                    self.zotino0.write_dac(1, -5.0)
                    self.zotino0.write_dac(2, 3.0)
                    self.zotino0.write_dac(3, -5.0)
                    self.zotino0.load()
                    #Edge number 44 name of edge: Calculate fb
                    delay((25.0)*ms)
                    SSB = calculate_SSB(SSB,sampleSPOL)
                    #Edge number 45 name of edge: Return dipole trap end
                    delay((24.999999999999996)*ms)

                    print("SSB:", SSB)
                    print("sampleSPOL:", sampleSPOL)

                    #exiting the scan at the first step if camera is not enabled 
                    if not camera_enabled: 
                        break 

