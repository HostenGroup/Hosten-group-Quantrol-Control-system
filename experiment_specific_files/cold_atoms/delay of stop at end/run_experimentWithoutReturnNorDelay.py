from artiq.experiment import *
import numpy as np
from scipy.io import loadmat
import os
import subprocess
from datetime import datetime
from pathlib import Path 
import sys 
import threading 
sys.path.append(str(Path(__file__).resolve().parent.parent)) 
import main.config as config 
from main.run_experiment_utils import start_artiq_thread  

save_sampled_box_checked = True
camera_box_checked = False

def calculate_SSB(SSB,sampleSPOL)->TFloat: 
    return SSB+(-1.13+sampleSPOL)*0.3 

def calculate_dV(samplePPOL,samplePPOL2)->TFloat: 
    return (samplePPOL-samplePPOL2) 

def calculate_Rex(N0,dV,kappaP,rset)->TFloat: 
    return float(round(100-rset/(1+kappaP/(2.9*N0)*dV)*100)) 

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


    def prepare(self): 
        # Create persistent dataset (persist=True -> stored in LMDB database)
        self.set_dataset("data", [], persist=True,archive=False)

    @kernel
    def run(self):
        self.create_run_active_file() 
        do_stop = 0 
        self.core.reset()
        self.core.break_realtime()
        inputs = [0.0]*8
        delay(1*s)
        SSB = float(228.555)
        dV = float(1)
        Rex = float(1)
        test = 0.0
        T_exp_ = 0.35
        sampleSPOL = 0.0
        datt = 20.0
        df = 365.3
        MWpi = 0.11
        SSBtrap = 228.601
        Pmw = 1.0
        PRa2 = 0.0
        RApi = 0.009
        MWfreq = 365.319425
        dphase = 0.0
        var_1 = 0.0
        samplePPOL = 0.0
        samplePPOL2 = 0.0
        rset = 0.7
        molpumpatt = 19.0
        kappaP = 1394000.0
        Phwhm = 0.9
        N0 = 750000.0
        for run_index in range(1):   # run loop including camera warm-up: warmup = 0, actual = 1, total = 1
            run_index_no_warumup = run_index - 0 # real run index for actual runs, will be negative for warm-up runs
            # Trigger camera 10 times without saving images
            if run_index == 0:
                for _ in range(10):
                    self.ttl8.pulse(1*ms)
                    self.ttl9.pulse(1*ms)
                    delay(200*ms)
            camera_enabled = True
            delay(100*ns)
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
            self.ttl12.on()
            self.ttl13.on()
            self.ttl14.off()
            self.ttl15.off()
            delay(1000*ns)
            self.zotino0.write_dac(0, 0.0005)
            self.zotino0.write_dac(1, -4.5)
            self.zotino0.write_dac(2, 2.031)
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
            self.urukul0_ch2.set_att((6.5)*dB) 
            self.urukul0_ch2.set(frequency = (80.0)*MHz, amplitude = (20.0)/100 , phase = (0.0)/360)
            self.urukul0_ch2.sw.off() 
            self.urukul0_ch3.set_att((7.0)*dB) 
            self.urukul0_ch3.set(frequency = (80.0)*MHz, amplitude = (20.0)/100 , phase = (0.0)/360)
            self.urukul0_ch3.sw.off() 
            self.urukul1_ch0.set_att((10.0)*dB) 
            self.urukul1_ch0.set(frequency = (80.0)*MHz, amplitude = (40.0)/100 , phase = (0.0)/360)
            self.urukul1_ch0.sw.off() 
            self.urukul1_ch1.set_att((0.5)*dB) 
            self.urukul1_ch1.set(frequency = (182.65)*MHz, amplitude = (30.0)/100 , phase = (0.0)/360)
            self.urukul1_ch1.sw.on() 
            self.urukul1_ch2.set_att((0.0)*dB) 
            self.urukul1_ch2.set(frequency = (365.319425)*MHz, amplitude = (29.0)/100 , phase = (0.0)/360)
            self.urukul1_ch2.sw.off() 
            self.urukul1_ch3.set_att((4.0)*dB) 
            self.urukul1_ch3.set(frequency = (SSB)*MHz, amplitude = (10.0)/100 , phase = (0.0)/360)
            self.urukul1_ch3.sw.on() 
            self.urukul2_ch0.set_att((0.0)*dB) 
            self.urukul2_ch0.set(frequency = (100.0)*MHz, amplitude = (100.0)/100 , phase = (0.0)/360)
            self.urukul2_ch0.sw.off() 
            self.urukul2_ch1.set_att((23.0)*dB) 
            self.urukul2_ch1.set(frequency = (80.0)*MHz, amplitude = (15.0)/100 , phase = (0.0)/360)
            self.urukul2_ch1.sw.on() 
            self.urukul2_ch2.set_att((0.0)*dB) 
            self.urukul2_ch2.set(frequency = (80.0)*MHz, amplitude = (20.0)/100 , phase = (0.0)/360)
            self.urukul2_ch2.sw.off() 
            self.urukul2_ch3.set_att((0.0)*dB) 
            self.urukul2_ch3.set(frequency = (80.0)*MHz, amplitude = (70.0)/100 , phase = (0.0)/360)
            self.urukul2_ch3.sw.on() 
            self.sampler0.init()
            #Edge number 1 name of edge: Flush (push) begin
            delay((1.0)*ms)
            self.ttl0.on()
            self.zotino0.write_dac(7, 5.0)
            self.zotino0.load()
            #Edge number 2 name of edge: Flush (push) end
            delay((75.0)*ms)
            self.zotino0.write_dac(7, 0.0)
            self.zotino0.load()
            #Edge number 3 name of edge: Turn on Raman 1 (locking)
            delay((1.0)*ms)
            self.ttl15.on()
            self.urukul2_ch1.set_att((22.0)*dB) 
            #Edge number 4 name of edge: Sample sPol 780
            delay((2.5)*ms)
            # Sampler input readout
            self.sampler0.sample(inputs)
            sampleSPOL = inputs[2]
            #Edge number 5 name of edge: Turn off Raman 1 (locking)
            delay((2.5)*ms)
            self.ttl11.off()
            self.ttl12.off()
            self.ttl15.off()
            #Edge number 6 name of edge: Set Raman 2
            delay((0.5)*ms)
            self.ttl10.on()
            self.urukul1_ch1.set(frequency = (178.1)*MHz, amplitude = (30.0)/100 , phase = (0.0)/360)
            self.urukul2_ch1.set_att((23.0)*dB) 
            self.urukul2_ch2.set_att((31.5)*dB) 
            self.urukul2_ch2.set(frequency = (80.0)*MHz, amplitude = (1.5)/100 , phase = (0.0)/360)
            #Edge number 7 name of edge: Turn on Raman 2 (locking)
            delay((0.5)*ms)
            self.urukul2_ch2.sw.on() 
            #Edge number 8 name of edge: Sample pPol
            delay((0.0499999999999972)*ms)
            # Sampler input readout
            self.sampler0.sample(inputs)
            samplePPOL = inputs[3]
            #Edge number 9 name of edge: Turn off Raman 2 (locking)
            delay((0.150000000000006)*ms)
            self.ttl10.off()
            self.urukul2_ch2.sw.off() 
            #Edge number 10 name of edge: Set Raman 2 and Offset
            delay((0.5)*ms)
            self.urukul1_ch1.set(frequency = (182.65)*MHz, amplitude = (30.0)/100 , phase = (0.0)/360)
            self.urukul2_ch2.set_att((0.0)*dB) 
            self.urukul2_ch2.set(frequency = (80.0)*MHz, amplitude = (20.0)/100 , phase = (0.0)/360)
            #Edge number 11 name of edge: Z cam trigger (background)
            delay((0.5)*ms)
            if camera_enabled:
                self.ttl8.on()
            else:
                self.ttl8.off()
            #Edge number 12 name of edge: Exposure begin
            delay((0.0300000000000011)*ms)
            self.ttl8.off()
            self.urukul0_ch2.sw.on() 
            self.urukul1_ch0.sw.on() 
            #Edge number 13 name of edge: Exposure end/coils on
            delay((0.299999999999997)*ms)
            self.zotino0.write_dac(0, -0.75)
            self.zotino0.write_dac(6, 5.0)
            self.zotino0.load()
            self.urukul0_ch2.sw.off() 
            self.urukul1_ch0.sw.off() 
            #Edge number 14 name of edge: Cont Load begin
            delay((10.0)*ms)
            self.urukul0_ch1.set(frequency = (386.8)*MHz, amplitude = (30.0)/100 , phase = (0.0)/360)
            self.urukul0_ch2.sw.on() 
            self.urukul0_ch3.sw.on() 
            self.urukul1_ch0.sw.on() 
            #Edge number 15 name of edge: Cont Load end
            delay((100.0)*ms)
            self.urukul1_ch0.set_att((27.0)*dB) 
            self.urukul1_ch0.sw.off() 
            #Edge number 16 name of edge: 1527 Ramp begin
            for i in range(1, (20+1)):   # ramp up loop 
                self.zotino0.write_dac(9, 0.45+(0.9-0.45)/(20)*i)
                self.zotino0.load()
                self.urukul0_ch2.set_att((19.0)*dB) 
                self.urukul0_ch3.set_att((19.0)*dB) 
                delay((50.0000000000000/20)*ms)  # for ramp up: time devided by steps 
            #Edge number 17 name of edge: 1527 Ramp end
            self.zotino0.write_dac(9, 0.9)
            self.zotino0.load()
            self.urukul0_ch2.sw.off() 
            self.urukul0_ch3.sw.off() 
            #Edge number 18 name of edge: Storage begin (free space det.)
            self.zotino0.write_dac(6, 0.0)
            self.zotino0.write_dac(9, 0.45)
            self.zotino0.load()
            #Edge number 19 name of edge: MOT coils OFF
            self.zotino0.write_dac(0, 0.0005)
            self.zotino0.load()
            #Edge number 20 name of edge: Cool0/Bz zero ramp begin
            delay((10.0)*ms)
            for i in range(1, (20+1)):   # ramp up loop 
                self.zotino0.write_dac(3, -6+((6-0.95)/20)*i)
                self.zotino0.load()
                self.urukul0_ch1.set(frequency = (386.5+1.95*i)*MHz, amplitude = (30.0)/100 , phase = (0.0)/360)
                delay((20.0000000000000/20)*ms)  # for ramp up: time devided by steps 
            #Edge number 21 name of edge: Cool0/Bz zero ramp end
            self.zotino0.write_dac(3, -0.95)
            self.zotino0.load()
            self.urukul0_ch1.set(frequency = (425.0)*MHz, amplitude = (30.0)/100 , phase = (0.0)/360)
            #Edge number 22 name of edge: Molasses begin
            delay((20.0)*ms)
            self.urukul0_ch2.sw.on() 
            self.urukul0_ch3.sw.on() 
            self.urukul1_ch0.sw.on() 
            #Edge number 23 name of edge: Molasses end
            delay((8.0)*ms)
            self.urukul0_ch2.sw.off() 
            self.urukul0_ch3.sw.off() 
            self.urukul1_ch0.sw.off() 
            #Edge number 24 name of edge: Cool/Rep/QuantBy ramp begin
            delay((10.0)*ms)
            for i in range(1, (20+1)):   # ramp up loop 
                self.zotino0.write_dac(2, 2.03+((9-2.03)/20)*i)
                self.zotino0.load()
                self.urukul0_ch0.set(frequency = (225.85-0.315*i)*MHz, amplitude = (90.0)/100 , phase = (0.0)/360)
                self.urukul0_ch1.set(frequency = (425+2.25*i)*MHz, amplitude = (30.0)/100 , phase = (0.0)/360)
                delay((20.0000000000000/20)*ms)  # for ramp up: time devided by steps 
            #Edge number 25 name of edge: Cool/Rep/QuantBy ramp end
            self.zotino0.write_dac(2, 9.0)
            self.zotino0.load()
            self.urukul0_ch0.set(frequency = (219.55)*MHz, amplitude = (90.0)/100 , phase = (0.0)/360)
            self.urukul0_ch1.set(frequency = (470.0)*MHz, amplitude = (30.0)/100 , phase = (0.0)/360)
            #Edge number 26 name of edge: Opt pump begin
            delay((20.0)*ms)
            self.urukul0_ch2.sw.on() 
            self.urukul0_ch3.sw.on() 
            self.urukul1_ch0.sw.on() 
            #Edge number 27 name of edge: Opt pump end
            delay((0.0500000000000114)*ms)
            self.urukul0_ch2.sw.off() 
            self.urukul0_ch3.sw.off() 
            self.urukul1_ch0.sw.off() 
            #Edge number 28 name of edge: Cool/Rep ramp begin
            delay((1.0)*ms)
            for i in range(1, (20+1)):   # ramp up loop 
                self.urukul0_ch0.set(frequency = (219.55+0.315*i)*MHz, amplitude = (90.0)/100 , phase = (0.0)/360)
                self.urukul0_ch1.set(frequency = (470-4.40*i)*MHz, amplitude = (30.0)/100 , phase = (0.0)/360)
                delay((10.0000000000000/20)*ms)  # for ramp up: time devided by steps 
            #Edge number 29 name of edge: Cool/Rep ramp end
            self.urukul0_ch0.set(frequency = (225.85)*MHz, amplitude = (90.0)/100 , phase = (0.0)/360)
            self.urukul0_ch1.set(frequency = (381.25)*MHz, amplitude = (30.0)/100 , phase = (0.0)/360)
            #Edge number 30 name of edge: Push begin
            delay((10.0)*ms)
            self.zotino0.write_dac(7, 5.0)
            self.zotino0.load()
            #Edge number 31 name of edge: Push end
            delay((0.0500000000000114)*ms)
            self.zotino0.write_dac(7, 0.0)
            self.zotino0.load()
            #Edge number 32 name of edge: MW pi-pulse begin
            delay((5.0)*ms)
            self.urukul1_ch2.sw.on() 
            #Edge number 33 name of edge: MW pi-pulse end
            delay((0.110000000000014)*ms)
            self.urukul1_ch2.sw.off() 
            #Edge number 34 name of edge: Repump begin
            self.urukul1_ch0.sw.on() 
            #Edge number 35 name of edge: Repump end
            delay((1.0)*ms)
            self.urukul1_ch0.sw.off() 
            #Edge number 36 name of edge: MW pi-pulse begin
            self.urukul1_ch2.sw.on() 
            #Edge number 37 name of edge: MW pi-pulse end
            delay((0.110000000000014)*ms)
            self.urukul1_ch2.sw.off() 
            #Edge number 38 name of edge: Push begin
            self.zotino0.write_dac(7, 5.0)
            self.zotino0.load()
            #Edge number 39 name of edge: Push end
            delay((0.05000000000000737)*ms)
            self.zotino0.write_dac(7, 0.0)
            self.zotino0.load()
            #Edge number 40 name of edge: Set Raman 2
            delay((0.5)*ms)
            self.ttl10.on()
            self.urukul1_ch1.set(frequency = (177.4)*MHz, amplitude = (30.0)/100 , phase = (0.0)/360)
            self.urukul2_ch2.set_att((31.5)*dB) 
            self.urukul2_ch2.set(frequency = (80.0)*MHz, amplitude = (1.5)/100 , phase = (0.0)/360)
            #Edge number 41 name of edge: Turn on Raman 2 (locking)
            delay((0.5)*ms)
            self.urukul2_ch2.sw.on() 
            #Edge number 42 name of edge: Sample pPol
            delay((0.050000000000019806)*ms)
            # Sampler input readout
            self.sampler0.sample(inputs)
            samplePPOL2 = inputs[4]
            #Edge number 43 name of edge: Turn off Raman 2 (locking)
            delay((0.14999999999997282)*ms)
            self.ttl10.off()
            self.urukul2_ch2.sw.off() 
            #Edge number 44 name of edge: SSB Raman Jump
            delay((20.0)*ms)
            self.urukul1_ch1.set(frequency = (187.65)*MHz, amplitude = (30.0)/100 , phase = (0.0)/360)
            self.urukul2_ch2.set_att((0.0)*dB) 
            self.urukul2_ch2.set(frequency = (80.0)*MHz, amplitude = (20.0)/100 , phase = (0.0)/360)
            #Edge number 45 name of edge: Calc. dV
            delay((5.0)*ms)
            dV = calculate_dV(samplePPOL,samplePPOL2)
            #Edge number 46 name of edge: Calc. Rex
            delay((15.0)*ms)
            Rex = calculate_Rex(N0,dV,kappaP,rset)
            #Edge number 47 name of edge: MW pulse (atom lock)
            delay((15.0)*ms)
            #Edge number 48 name of edge: MW pulse end (atom lock)
            #Edge number 49 name of edge: Push begin
            delay((1.0)*ms)
            #Edge number 50 name of edge: Push end
            delay((0.05000000000000737)*ms)
            self.zotino0.write_dac(7, 0.0)
            self.zotino0.load()
            #Edge number 51 name of edge: MW pulse (EXTRA)
            #Edge number 52 name of edge: MW pulse end (EXTRA)
            delay((1.0)*ms)
            #Edge number 53 name of edge: Digital switch Ant to Mod
            delay((1.0)*ms)
            self.ttl12.off()
            #Edge number 54 name of edge: Raman Pulse begin
            delay((1.0)*ms)
            #Edge number 55 name of edge: Raman Pulse end
            delay((1.0)*ms)
            #Edge number 56 name of edge: Storage end (free space det.)
            delay((25.0)*ms)
            self.zotino0.write_dac(8, 0.01)
            self.zotino0.write_dac(9, 0.01)
            self.zotino0.load()
            #Edge number 57 name of edge: Push begin (for double crop)
            delay((0.5)*ms)
            self.zotino0.write_dac(7, 0.0)
            self.zotino0.load()
            #Edge number 58 name of edge: Push end
            delay((0.050000000000019806)*ms)
            self.zotino0.write_dac(7, 0.0)
            self.zotino0.load()
            #Edge number 59 name of edge: Z cam trigger (meas)
            delay((0.55000000000001)*ms)
            if camera_enabled:
                self.ttl8.on()
            else:
                self.ttl8.off()
            #Edge number 60 name of edge: Exposure begin
            delay((0.02999999999997005)*ms)
            self.ttl8.off()
            self.urukul0_ch2.set_att((6.5)*dB) 
            self.urukul0_ch2.sw.on() 
            self.urukul1_ch0.set_att((10.0)*dB) 
            self.urukul1_ch0.sw.on() 
            #Edge number 61 name of edge: Exposure end
            delay((0.30000000000001004)*ms)
            self.urukul0_ch2.sw.off() 
            self.urukul1_ch0.sw.off() 
            #Edge number 62 name of edge: Return dipole trap
            delay((0.10000000000002007)*ms)
            self.zotino0.write_dac(8, 0.75)
            self.zotino0.write_dac(9, 0.45)
            self.zotino0.load()
            self.urukul1_ch1.set(frequency = (182.65)*MHz, amplitude = (30.0)/100 , phase = (0.0)/360)
            #Edge number 63 name of edge: By3/Bz3 ramp begin
            for i in range(1, (20+1)):   # ramp up loop 
                self.zotino0.write_dac(2, 9-((9-2.03)/20)*i)
                self.zotino0.write_dac(3, -0.95-((6-0.95)/20)*i)
                self.zotino0.load()
                delay((20.000000000000000/20)*ms)  # for ramp up: time devided by steps 
            #Edge number 64 name of edge: By3/Bz3 ramp end
            self.zotino0.write_dac(2, 2.031)
            self.zotino0.write_dac(3, -6.0)
            self.zotino0.load()
            #Edge number 65 name of edge: Calculate feedback ssb
            delay((20.0)*ms)
            SSB = calculate_SSB(SSB,sampleSPOL)
            #Edge number 66 name of edge: Final edge
            delay((20.000000000000046)*ms)

            # For save sample variables
            self.store_sample(run_index_no_warumup, sampleSPOL, samplePPOL, samplePPOL2, SSB, dV, Rex)

            delay(20*ms)
            print("SSB:", SSB)
            delay(20*ms)
            print("SSB:", SSB)
            delay(20*ms)
            print("sampleSPOL:", sampleSPOL)

            delay(20*ms)
            print("dV:", dV)
            delay(20*ms)
            print("samplePPOL:", samplePPOL)
            delay(20*ms)
            print("samplePPOL2:", samplePPOL2)

            delay(20*ms)
            print("Rex:", Rex)
            delay(20*ms)
            print("N0:", N0)
            delay(20*ms)
            print("dV:", dV)
            delay(20*ms)
            print("kappaP:", kappaP)
            delay(20*ms)
            print("rset:", rset)
            self.copy_dataset_file()  # add saved sampled variables to a txt file 

            if do_stop == 1:
                self.execute_stop()
            if do_stop == 2:
                self.execute_new()

            do_stop = self.check_host_stop()

            self.core.break_realtime()

        self.print_end_exp()  # print end of experiment in the end of the run 

    @rpc
    def print_end_exp(self):
        self.repo_path = Path(__file__).resolve().parent.parent
        path = Path(self.repo_path) / 'ARTIQ_scripts' / 'run_active_flag.txt' 
        if path.exists(): 
            path.unlink() 
        print("End of experiment")

    @rpc
    def create_run_active_file(self):
        self.repo_path = Path(__file__).resolve().parent.parent
        path = Path(self.repo_path) / 'ARTIQ_scripts' / 'run_active_flag.txt' 
        try: 
            path.parent.mkdir(parents=True, exist_ok=True) 
            path.touch() 
        except Exception: 
            pass 

    @rpc
    def check_host_stop(self) -> TInt32:
        stop_exp_file = Path(__file__).resolve().parent / 'stop_exp_flag.txt'
        new_exp_file = Path(__file__).resolve().parent / 'new_exp_flag.txt'
        self.repo_path = Path(__file__).resolve().parent.parent
        try:
            if stop_exp_file.exists():
                stop_exp_file.unlink()  # delete the stop flag file
                return 1
            if new_exp_file.exists(): 
                new_exp_file.unlink()  # delete the new_exp_file marker file
                return 2
        except Exception as exc:
            print('check_host_stop error:', exc)
        return 0

    @rpc
    def execute_stop(self):
        self.repo_path = Path(__file__).resolve().parent.parent
        try:
            if config.package_manager == 'conda':
                submit_experiment_thread = threading.Thread(target=os.system, args=['conda activate ' + config.artiq_environment_name + ' && artiq_run ' + str(self.repo_path / 'ARTIQ_scripts' / 'init_hardware.py')])
            elif config.package_manager == 'clang64':
                submit_experiment_thread = threading.Thread(target=lambda: subprocess.Popen(['cmd', '/c', str(self.repo_path / 'experiment_specific_files' / 'hybrid_experiment' / 'init_hardware.bat')],creationflags=subprocess.CREATE_NEW_CONSOLE))
            submit_experiment_thread.start()
        except Exception as exc:
            print('Could not execute go_to_edge:', exc)

    @rpc
    def execute_new(self):
        self.repo_path = Path(__file__).resolve().parent.parent
        submit_experiment_thread = start_artiq_thread(self.repo_path)

    @rpc
    def store_sample(self, run_index, sampleSPOL, samplePPOL, samplePPOL2, SSB, dV, Rex):
        self.append_to_dataset("data", (int(run_index), sampleSPOL, samplePPOL, samplePPOL2, SSB, dV, Rex))

    @rpc
    def copy_dataset_file(self):
        experiment_name = 'Raman transition'
        experimental_path = 'G:\\Experimental Data\\Atom Interferometer experiment\\Raman\\Raman transition\\2026_04_23\\16_50_25'
        experimental_metadata_path = 'G:\\Experimental Data\\Atom Interferometer experiment\\Raman\\Raman transition\\2026_04_23\\16_50_25'
        target_directory = Path(experimental_metadata_path) if experimental_metadata_path else (Path(experimental_path) if experimental_path else None)
        if target_directory is None:
            today = datetime.now().strftime('%Y_%m_%d')
            exp_dir = experiment_name if experiment_name else 'unspecified_experiment'
            target_directory = Path(config.experiment_data_root) / exp_dir / today
        try:
            target_directory.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            print(f'Could not create target directory {target_directory}: {e}')
        folder_name = target_directory.name
        folder_date = datetime.now().strftime('%Y%m%d')
        folder_time = folder_name[-8:].replace('_', '') if len(folder_name) >= 8 else datetime.now().strftime('%H%M%S')
        target_file = target_directory / f"dataset_db_copy_{folder_date}_{folder_time}.txt"
        data = self.get_dataset('data', archive=False)
        column_names = ['int(run_index)', 'sampleSPOL', 'samplePPOL', 'samplePPOL2', 'SSB', 'dV', 'Rex']
        with open(target_file, "w") as f:
            f.write(", ".join(column_names) + "\n")
            f.writelines(f"{entry}\n" for entry in data)
