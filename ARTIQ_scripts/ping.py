from artiq.experiment import *
class Ping(EnvExperiment):
    def build(self): self.setattr_device("core")
    @kernel
    def run(self): pass
