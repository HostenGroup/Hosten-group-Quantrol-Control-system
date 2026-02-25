from artiq.experiment import *
import numpy as np


class RunExperiment(EnvExperiment):

    def build(self):
        self.setattr_device("core")
        self.setattr_device("sampler0")
        self.setattr_device("urukul2_ch1")

    def prepare(self):
        # Create persistent dataset
        # broadcast=True → live dashboard updates
        # persist=True → stored in LMDB database
        self.set_dataset(
            "adc_data",
            [],
            broadcast=True,
            persist=True
        )

    # ----------------------------------------
    # Kernel (real-time hardware control)
    # ----------------------------------------
    @kernel
    def run(self):
        self.core.reset()
        self.core.break_realtime()

        inputs = [0.0]*8

        for run_index in range(6): # number of runs

            for step in range(100):

                delay(100*ms)
                delay(20*ms)

                self.sampler0.sample(inputs)

                # Send single value to host
                self.store_sample(run_index, step, inputs[1])  

    # ----------------------------------------
    # Host side (dataset storage)
    # ----------------------------------------
    @rpc
    def store_sample(self, run_index, step, value):

        # Store tuple (run, step, value)
        self.append_to_dataset(
            "adc_data",
            (run_index, step, value)
        )




#  ----------------------------------------
#  Comments and thoughts
#  ----------------------------------------
# ARTIQ does not “send multiple files.” It loads one experiment file, which can import other Python files.
# 
# add this in run_experiment.py:
# from sampled_variables import process

# add this to the end of sampled_variables.py:
# def process(data):
# return sum(data)/len(data)