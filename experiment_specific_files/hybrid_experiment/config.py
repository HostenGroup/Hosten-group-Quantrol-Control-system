'''
This is an example of a config file that is used in the Hosten lab, cold atoms team.

In case you do not have digital, analog, dds, or sampler channels simply set their channels_number values to 0

Skipping images is a functionality very specific to our experimental setup. It triggers the image acquisition
camera as we observed that first several images might probabilistically be faulty. Feel free to set it to False

For the list_of_devices_for_initialization you can have a look at your device_db.py file to see what options do you have
'''

import sys
from pathlib import Path

digital_channels_number = 16
analog_channels_number = 16
dds_channels_number = 16
mirny_channels_number = 4
slow_dds_channels_number = 4
sampler_channels_number = 8

which_project = 'hybrid_experiment'
# which_project = 'cold_atoms'

package_manager = "clang64" #it can be either conda or clang64
artiq_environment_name = "artiq" # it can be either artiq or artiq_5 for Hosten lab systems
analog_card = "fastino" # it can be either fastino or zotino for Hosten lab systems
research_group_name = "Hosten"
camera_trigger_ttl = [0,1,4]
camera_serial_numbers_dict = {
    'X':'22433340',
    'Y':'22433344',
    'Z':'22114656'
}
experiment_data_root = r"G:\Experimental Data\Hybrid\MOT_images"

experiment_database_path = str(Path(experiment_data_root).parent / "Hybrid_exp_db.xlsx")

# Construct camera_env_python path based on current Python environment

_current_python = Path(sys.executable)
repository_path = Path(__file__).resolve().parent.parent

_python_envs_path = Path(str(_current_python).split('python_envs')[0]) / 'python_envs'

camera_env_python = str(repository_path.parent.parent.parent / 'Documents' / 'python_envs' / 'camera_env' / 'Scripts' / 'python.exe')

camera_gain_minmax = [0.00,47.98]
camera_exp_us_minmax = [19.0,30000000]

camera_launch_delay_s = 5
allow_skipping_images = True
skip_images_trigger_count = 10

# Camera saving performance:
# If your experiment output directory is on a network drive (e.g. G:\) or is slow because of antivirus scanning,
# enabling local staging will save images to a local folder first and copy them to the final directory after
# acquisition finishes.
camera_stage_locally = False
camera_stage_dir = str(repository_path / "temp_images")


slow_dds_channels = [
    "urukul3_ch0",
    "urukul3_ch1",
    "urukul3_ch2",
    "urukul3_ch3"
] # The sequence of the channels should be corresponding to the sequence in the slow DDS tab. The first one in the slow_dds_channels list will be the slow_DDS0 and so on
list_of_devices_for_initialization = [
    "urukul0_cpld",
    "urukul0_ch0",
    "urukul0_ch1",
    "urukul0_ch2",
    "urukul0_ch3",
    "urukul1_cpld",
    "urukul1_ch0",
    "urukul1_ch1",
    "urukul1_ch2",
    "urukul1_ch3",
    "urukul2_cpld",
    "urukul2_ch0",
    "urukul2_ch1",
    "urukul2_ch2",
    "urukul2_ch3",
    "mirny0_cpld",
    "mirny0_ch0",
    "mirny0_ch1",
    "mirny0_ch2",
    "mirny0_ch3",
    "fastino0",
    "sampler0"
]

list_of_devices_for_use = [
    "core",
    "urukul0_cpld",
    "urukul0_ch0",
    "urukul0_ch1",
    "urukul0_ch2",
    "urukul0_ch3",
    "urukul1_cpld",
    "urukul1_ch0",
    "urukul1_ch1",
    "urukul1_ch2",
    "urukul1_ch3",
    "urukul2_cpld",
    "urukul2_ch0",
    "urukul2_ch1",
    "urukul2_ch2",
    "urukul2_ch3",
    "urukul3_cpld",
    "urukul3_ch0",
    "urukul3_ch1",
    "urukul3_ch2",
    "urukul3_ch3",
    "mirny0_cpld",
    "mirny0_ch0",
    "mirny0_ch1",
    "mirny0_ch2",
    "mirny0_ch3",
    "ttl0",
    "ttl1",
    "ttl2",
    "ttl3",
    "ttl4",
    "ttl5",
    "ttl6",
    "ttl7",
    "ttl8",
    "ttl9",
    "ttl10",
    "ttl11",
    "ttl12",
    "ttl13",
    "ttl14",
    "ttl15",
    "fastino0",
    "sampler0"
]