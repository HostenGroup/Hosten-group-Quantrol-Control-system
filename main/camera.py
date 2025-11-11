####################################################################
# Author: Alexei Gurchenko, Hosten group
# Date: 4 September 2025
####################################################################

from PyQt5.QtCore import * 
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
import PySpin
import datetime
import os
import gc
import json

import config

def camera_init(self, which_camera_to_use = 'Y', format_name = 'Mono8', gain_db = 20, t_exp = 350):
    # Pixel format
    # format_name = 'Mono8' 

    # Analog gain in dB
    # gain_db = 20

    # Exposure time in us
    # t_exp = 350 

    # Pick the number of the experiment. To add new experiment add a new entry to the 'experiment_names_dict'
    # experiment_code = 9

    # Parameters you want to put to the info file (ALL VALUES IN SI)
    par_dict = {      
        'min': 0,
        'max': 360,
        # 'text': '6dB MW att, cleanup, Y bias, pi pulse',
        'text': 'MOT jiggle',
        # 't_pulse': 0.09e-3,
        't_storage': 500e-3,
        't_loading': 200e-3,
        'freq': 10,
        # 't_wait': 10e-3,
        # 'Bx': -0.96,
        # 'By': 0.22+0.1,
        # 'Bz': 0.32,
        # 'phi(z)': 110,
        # 'dBx': 0.08,
        # 'dBy': -0.7,
        # 'dBz': 0.1,
        # 'dF_MW':0.015e6,
    }

    # Any string you want to pun to the info file
    #experiment_explanation = 'MW spectroscopy with MOT coils OFF after fixing the MOSFET circuit, waiting t_storage, trying to zero the field, fans far away' 
    experiment_explanation = '' 

    # Should be capital X or Y
    # which_camera_to_use = which 

    # Dictionary of experiments

    with open(self.repo_path / "experiment_specific_files" / config.which_project / "experiment_names.json", 'r') as f:
        experiment_dict = json.load(f)

    experiment_names_dict = {int(k): v["name"] for k, v in experiment_dict.items()}
    x_captions_dict = {int(k): v["plot_x_caption"] for k, v in experiment_dict.items()}


    process = False


    par_dict['scan'] = x_captions_dict[experiment_code]



    serial_numbers_dict = config.camera_serial_numbers_dict

    n_images = None

    info = {
        'format': format_name,
        'gain': gain_db,
        'exposure': t_exp,
        'image_number': n_images,
        'camera': which_camera_to_use,
        'camera_serial_number': serial_numbers_dict[which_camera_to_use],
        'experiment': experiment_names_dict[experiment_code],
        'comments': experiment_explanation,
        'parameters': par_dict
    }


    directory = rf'G:/Experimental Data/Hybrid/MOT_images/{experiment_names_dict[experiment_code]}'

    gc.collect()

    interrupted = False

    system = PySpin.System.GetInstance()

    cam_list = system.GetCameras()

    camera_dict = {}
    #camera_dict_inverted = {}

    if cam_list.GetSize() == 0:
        cam_list.Clear()
        system.ReleaseInstance()
        raise RuntimeError('No FLIR cameras detected.')



    for cam in cam_list:

        cam.Init()
        # Stop acquisition if running (ignore error if it wasn't)
        try:
            cam.BeginAcquisition()
            cam.EndAcquisition()
        except PySpin.SpinnakerException as ex:
            print('Error: %s' % ex)

        
        nodemap_tldevice = cam.GetTLDeviceNodeMap()


        ####################################################################
        # Get serial numbers of the cameras to verify which one is which.
        ####################################################################

        node_serial = PySpin.CStringPtr(nodemap_tldevice.GetNode('DeviceSerialNumber'))

        if PySpin.IsAvailable(node_serial) and PySpin.IsReadable(node_serial):
            serial_number = node_serial.GetValue()
            if serial_number == serial_numbers_dict['X']:
                camera_dict['X'] = cam
                #cam_name = 'X'

            elif serial_number == serial_numbers_dict['Y']: #  Y cam
                camera_dict['Y'] = cam
                #cam_name = 'Y'
            
            else:
                raise RuntimeError('Unknown camera number. Aborting.')

            #print(f'CAM {cam_name} Serial Number: {serial_number}')
        else:
            raise RuntimeError('Unable to read camera serial number.')

    #print()

    #del cam
    #del cam_name

    for cam in cam_list:
        if camera_dict[which_camera_to_use] == cam:
            cam_name = which_camera_to_use
            print(f'\nCamera to use: CAM {which_camera_to_use}\n')

            nodemap = cam.GetNodeMap()
            nodemap_tldevice = cam.GetTLDeviceNodeMap()
            self.set_cam_parameters(t_exp,gain_db,format_name)
            print()




####################################################################
# Begins acquisition and waits for hardware triggers. Each trigger should produce one image.
####################################################################

local_time = datetime.datetime.now()
date_str, time_str = local_time.strftime('%Y_%m_%d'), local_time.strftime('%H_%M_%S')
del local_time


directory_to_save = r'%s/%s/%s/%s' % (directory, date_str, time_str, cam_name)
        
cam.BeginAcquisition()

image_index = 0
timeout_ms = 5000
short_timeout = 50
num_of_timeouts = int(timeout_ms/short_timeout)
timeout_counter = 0

print('Use hardware to trigger image acquisition. Press Ctrl+C to interrupt.')
try:
    while True:

        if timeout_counter >= num_of_timeouts and image_index > 0:
            raise Exception('\nCamera timeout. Acquisition finished successfully.')
        
        try:
            image = cam.GetNextImage(short_timeout)
        except PySpin.SpinnakerException as ex:
            if '[-1011]' in str(ex):
                timeout_counter += 1
                continue
            raise

        try:
            #  Ensure image completion 
            if image.IsIncomplete():
                raise RuntimeError(f'Image CAM {cam_name} incomplete with image status {image.GetImageStatus()}')
            else:

                if not os.path.isdir(directory_to_save) and image_index == 0:
                    os.makedirs(directory_to_save)
                    time_start = datetime.datetime.now()
                    

                filename = r'%s/%s_%d.tif' % (directory_to_save, cam_name, image_index)

                image.Save(filename)
                timeout_counter = 0
                
                #print('Image saved at %s\n' % filename)
                print(f'Saved image number: {image_index + 1}')
                print('Use hardware to trigger image acquisition. Press Ctrl+C to interrupt.')
                image_index += 1
        finally:
            image.Release()


except KeyboardInterrupt:
    print('Stopped by user.')
    interrupted = True
    

except Exception as ex:
    print(str(ex))

finally:

    cam.EndAcquisition()
    del camera_dict


    for cam in cam_list:
        cam.DeInit()   
    del cam

    cam_list.Clear()
    system.ReleaseInstance()
    print('Acquisition ended. Camera deinitialised. System released.')


    if image_index >= 1 and interrupted == False:
        n_images = image_index + 1
        info.update(image_number = n_images)
        if not os.path.isdir(directory_to_save):
            os.makedirs(directory_to_save)
        with open(directory_to_save +'/info.json', 'w') as file:
            json.dump(info, file, indent = 4)
        print(rf'Files saved at {directory_to_save}')

        time_elapsed = datetime.datetime.now() - time_start 
        print(f'Elapsed time: {time_elapsed.total_seconds():.1f} s')

        with open(r'G:/Experimental Data/Hybrid/MOT_images/last_path.txt','w') as file:
            file.write(directory_to_save)

        with open(r'G:/Experimental Data/Hybrid/MOT_images/path_list.txt','a') as file:
            file.write(directory_to_save + '\n')

        if process == True:
            with open('G:\Experimental Data\Hybrid\image_processing.py') as file:
                exec(file.read())



def set_cam_parameters(self,t_exp_,gain_,format_):
    '''Set parameters of the camera'''

    ####################################################################
    # Set exposure time in microseconds (us).
    ####################################################################

    #Disable auto exposure
    node_exposure_auto = PySpin.CEnumerationPtr(nodemap.GetNode('ExposureAuto'))
    if not PySpin.IsAvailable(node_exposure_auto) or not PySpin.IsWritable(node_exposure_auto):
        raise RuntimeError('ExposureAuto node not writable.')
    node_exposure_auto_off = node_exposure_auto.GetEntryByName('Off')
    node_exposure_auto.SetIntValue(node_exposure_auto_off.GetValue())

    #Access ExposureTime
    node_exposure_time = PySpin.CFloatPtr(nodemap.GetNode('ExposureTime'))
    if not PySpin.IsAvailable(node_exposure_time) or not PySpin.IsWritable(node_exposure_time):
        raise RuntimeError('ExposureTime node not writable.')

    #Clamp requested value into allowed range
    min_exposure = node_exposure_time.GetMin()
    max_exposure = node_exposure_time.GetMax()
    t_exp_ = max(min(t_exp_, max_exposure), min_exposure)

    node_exposure_time.SetValue(t_exp_)
    print(f'Exposure set to {t_exp_:.1f} us (range {min_exposure:.1f} – {max_exposure:.1f} us)')





    ####################################################################
    # Set manual gain in decibels (dB).
    ####################################################################

    #Disable auto gain
    node_gain_auto = PySpin.CEnumerationPtr(nodemap.GetNode('GainAuto'))
    if not PySpin.IsAvailable(node_gain_auto) or not PySpin.IsWritable(node_gain_auto):
        raise RuntimeError('GainAuto node not writable.')
    node_gain_auto_off = node_gain_auto.GetEntryByName('Off')
    node_gain_auto.SetIntValue(node_gain_auto_off.GetValue())

    #Access manual Gain node
    node_gain = PySpin.CFloatPtr(nodemap.GetNode('Gain'))
    if not PySpin.IsAvailable(node_gain) or not PySpin.IsWritable(node_gain):
        raise RuntimeError('Gain node not writable.')

    #Clamp requested value into allowed range
    min_gain = node_gain.GetMin()
    max_gain = node_gain.GetMax()
    gain_db = max(min(gain_, max_gain), min_gain)

    node_gain.SetValue(gain_)
    print(f'Gain set to {gain_:.2f} dB (range {min_gain:.2f} – {max_gain:.2f} dB)')





    ####################################################################
    # Let the camera run at its maximum possible FPS (automatic).
    ####################################################################

    # Check if frame rate enable node exists (not all models have it)
    node_acq_fr_enable = PySpin.CBooleanPtr(nodemap.GetNode('AcquisitionFrameRateEnable'))
    if PySpin.IsAvailable(node_acq_fr_enable) and PySpin.IsWritable(node_acq_fr_enable):
        node_acq_fr_enable.SetValue(False)   # disables manual FPS control
    print('Frame rate is now automatic')





    ####################################################################
    # Disable Gamma.
    ####################################################################

    node_gamma_enable = PySpin.CBooleanPtr(nodemap.GetNode('GammaEnable'))
    if PySpin.IsAvailable(node_gamma_enable) and PySpin.IsWritable(node_gamma_enable):
        node_gamma_enable.SetValue(False)
        print('Gamma disabled')





    ####################################################################
    # Set EV Compensation to 0.
    ####################################################################

    ev_value = 0
    node_ev = PySpin.CFloatPtr(nodemap.GetNode('AutoExposureEVCompensation'))
    if not PySpin.IsAvailable(node_ev) or not PySpin.IsWritable(node_ev):
        raise RuntimeError('EV compensation not available on this camera.')

    # Clamp into allowed range
    ev_value = max(min(ev_value, node_ev.GetMax()), node_ev.GetMin())
    node_ev.SetValue(ev_value)
    print(f'EV compensation set to {ev_value:.2f}')





    ####################################################################
    # Set Black Level to 0%.
    ####################################################################

    black_level_value = 0
    # Access BlackLevel node
    node_bl = PySpin.CFloatPtr(nodemap.GetNode('BlackLevel'))
    if not PySpin.IsAvailable(node_bl) or not PySpin.IsWritable(node_bl):
        raise RuntimeError('BlackLevel not available or not writable on this camera.')

    # Clamp to allowed range
    black_level_value = max(min(black_level_value, node_bl.GetMax()), node_bl.GetMin())

    node_bl.SetValue(black_level_value)
    print(f'Black level set to {black_level_value:.2f} %')





    ####################################################################
    # Setting pixel format to Mono8
    ####################################################################

    pf_node = PySpin.CEnumerationPtr(nodemap.GetNode('PixelFormat'))
    if not PySpin.IsAvailable(pf_node) or not PySpin.IsWritable(pf_node):
        raise RuntimeError('PixelFormat node not writable (camera acquiring or node locked).')

    entry = pf_node.GetEntryByName(format_)
    if not PySpin.IsAvailable(entry) or not PySpin.IsReadable(entry):
        raise RuntimeError(f'Pixel format {format_} not supported by this camera.')

    pf_node.SetIntValue(entry.GetValue())
    print(f'Pixel format set to {format_}')





    ####################################################################
    # Set the sensor ADC bit depth (e.g., 8, 10, 12, 14, 16) if supported.
    ####################################################################

    adc_depth = 10
    adc_node = PySpin.CEnumerationPtr(nodemap.GetNode('AdcBitDepth'))
    if not PySpin.IsAvailable(adc_node) or not PySpin.IsWritable(adc_node):
        raise RuntimeError('AdcBitDepth not available or not writable on this camera.')

    # Enum entries are typically named 'Bit8', 'Bit10', 'Bit12', 'Bit14', 'Bit16'
    entry = adc_node.GetEntryByName(f'Bit{int(adc_depth)}')
    if not PySpin.IsAvailable(entry) or not PySpin.IsReadable(entry):
        raise RuntimeError(f'ADC depth {adc_depth}-bit not supported on this camera.')

    adc_node.SetIntValue(entry.GetValue())
    print(f'ADC depth set to {adc_depth} bit')





    ####################################################################
    # Set horizontal and vertical binning. h,v = 1 disables binning (full resolution).
    ####################################################################

    h = 1
    v = 1
    # Horizontal binning
    node_bin_h = PySpin.CIntegerPtr(nodemap.GetNode('BinningHorizontal'))
    if PySpin.IsAvailable(node_bin_h) and PySpin.IsWritable(node_bin_h):
        h = max(min(h, node_bin_h.GetMax()), node_bin_h.GetMin())
        node_bin_h.SetValue(h)
        print(f'Horizontal binning set to {h}')
    else:
        print('Horizontal binning not available on this camera.')

    # Vertical binning
    node_bin_v = PySpin.CIntegerPtr(nodemap.GetNode('BinningVertical'))
    if PySpin.IsAvailable(node_bin_v) and PySpin.IsWritable(node_bin_v):
        v = max(min(v, node_bin_v.GetMax()), node_bin_v.GetMin())
        node_bin_v.SetValue(v)
        print(f'Vertical binning set to {v}')
    else:
        print('Vertical binning not available on this camera.')





    ####################################################################
    # Reset ROI: set width & height to max, offsets to 0.
    ####################################################################

    # Width
    node_width = PySpin.CIntegerPtr(nodemap.GetNode('Width'))
    if PySpin.IsAvailable(node_width) and PySpin.IsWritable(node_width):
        max_width = node_width.GetMax()
        node_width.SetValue(max_width)
        info['width'] = max_width
        print(f'Width set to maximum: {max_width}')
    else:
        print('Width not available or not writable.')

    # Height
    node_height = PySpin.CIntegerPtr(nodemap.GetNode('Height'))
    if PySpin.IsAvailable(node_height) and PySpin.IsWritable(node_height):
        max_height = node_height.GetMax()
        node_height.SetValue(max_height)
        info['height'] = max_height
        print(f'Height set to maximum: {max_height}')
    else:
        print('Height not available or not writable.')

    # Reset offsets to 0 so ROI is aligned at the origin
    node_offset_x = PySpin.CIntegerPtr(nodemap.GetNode('OffsetX'))
    node_offset_y = PySpin.CIntegerPtr(nodemap.GetNode('OffsetY'))

    if PySpin.IsAvailable(node_offset_x) and PySpin.IsWritable(node_offset_x):
        node_offset_x.SetValue(node_offset_x.GetMin())  # usually 0
        print(f'OffsetX set to {node_offset_x.GetValue()}')

    if PySpin.IsAvailable(node_offset_y) and PySpin.IsWritable(node_offset_y):
        node_offset_y.SetValue(node_offset_y.GetMin())  # usually 0
        print(f'OffsetY set to {node_offset_y.GetValue()}')





    ####################################################################
    # Set horizontal and vertical decimation. h_d, v_d = 1 means no decimation.
    ####################################################################

    h_d = 1
    v_d = 1
    # Horizontal decimation
    node_dec_h = PySpin.CIntegerPtr(nodemap.GetNode('DecimationHorizontal'))
    if PySpin.IsAvailable(node_dec_h) and PySpin.IsWritable(node_dec_h):
        h_d = max(min(h_d, node_dec_h.GetMax()), node_dec_h.GetMin())
        node_dec_h.SetValue(h_d)
        print(f'Horizontal decimation set to {h_d}')
    else:
        print('Horizontal decimation not available on this camera.')

    # Vertical decimation
    node_dec_v = PySpin.CIntegerPtr(nodemap.GetNode('DecimationVertical'))
    if PySpin.IsAvailable(node_dec_v) and PySpin.IsWritable(node_dec_v):
        v_d = max(min(v_d, node_dec_v.GetMax()), node_dec_v.GetMin())
        node_dec_v.SetValue(v_d)
        print(f'Vertical decimation set to {v_d}')
    else:
        print('Vertical decimation not available on this camera.')




    ####################################################################
    # Set acquisition mode to continuous
    ####################################################################

    # In order to access the node entries, they have to be casted to a pointer type (CEnumerationPtr here)
    node_acquisition_mode = PySpin.CEnumerationPtr(nodemap.GetNode('AcquisitionMode'))
    if not PySpin.IsAvailable(node_acquisition_mode) or not PySpin.IsWritable(node_acquisition_mode):
        print(f'Unable to set acquisition mode to continuous (enum retrieval)')

    # Retrieve entry node from enumeration node
    node_acquisition_mode_continuous = node_acquisition_mode.GetEntryByName('Continuous')
    if not PySpin.IsAvailable(node_acquisition_mode_continuous) or not PySpin.IsReadable(
            node_acquisition_mode_continuous):
        print(f'Unable to set acquisition mode to continuous (entry retrieval)')

    acquisition_mode_continuous = node_acquisition_mode_continuous.GetValue()
    node_acquisition_mode.SetIntValue(acquisition_mode_continuous)
    print(f'Acquisition mode set to continuous')





    ####################################################################
    # Configure hardware trigger:
    # - TriggerSelector = FrameStart
    # - TriggerSource   = Line0
    # - TriggerActivation = RisingEdge
    # - TriggerMode     = On
    # - TriggerOverlap    = Off
    # - LineInverter(Line0)= False
    # - TriggerDelay    = delay_us (microseconds)
    ####################################################################

    # TriggerMode OFF to edit
    trig_mode = PySpin.CEnumerationPtr(nodemap.GetNode('TriggerMode'))
    trig_mode_off = trig_mode.GetEntryByName('Off')
    trig_mode.SetIntValue(trig_mode_off.GetValue())

    # TriggerSelector = FrameStart
    trig_sel = PySpin.CEnumerationPtr(nodemap.GetNode('TriggerSelector'))
    trig_sel.SetIntValue(trig_sel.GetEntryByName('FrameStart').GetValue())

    # TriggerSource = Line0
    trig_src = PySpin.CEnumerationPtr(nodemap.GetNode('TriggerSource'))
    trig_src.SetIntValue(trig_src.GetEntryByName('Line0').GetValue())

    # TriggerActivation = RisingEdge
    trig_act = PySpin.CEnumerationPtr(nodemap.GetNode('TriggerActivation'))
    if PySpin.IsAvailable(trig_act) and PySpin.IsWritable(trig_act):
        trig_act.SetIntValue(trig_act.GetEntryByName('RisingEdge').GetValue())

    # TriggerOverlap = Off
    trig_ovl = PySpin.CEnumerationPtr(nodemap.GetNode('TriggerOverlap'))
    if PySpin.IsAvailable(trig_ovl) and PySpin.IsWritable(trig_ovl):
        ent_off = trig_ovl.GetEntryByName('Off')
        if PySpin.IsAvailable(ent_off) and PySpin.IsReadable(ent_off):
            trig_ovl.SetIntValue(ent_off.GetValue())

    # Ensure Line0 is Input and LineInverter = False
    line_sel = PySpin.CEnumerationPtr(nodemap.GetNode('LineSelector'))
    line_mode = PySpin.CEnumerationPtr(nodemap.GetNode('LineMode'))
    line_inv  = PySpin.CBooleanPtr(nodemap.GetNode('LineInverter'))
    if PySpin.IsAvailable(line_sel) and PySpin.IsWritable(line_sel):
        ent_line0 = line_sel.GetEntryByName('Line0')
        if PySpin.IsAvailable(ent_line0) and PySpin.IsReadable(ent_line0):
            line_sel.SetIntValue(ent_line0.GetValue())
            if PySpin.IsAvailable(line_mode) and PySpin.IsWritable(line_mode):
                mode_in = line_mode.GetEntryByName('Input')
                if PySpin.IsAvailable(mode_in) and PySpin.IsReadable(mode_in):
                    line_mode.SetIntValue(mode_in.GetValue())
            if PySpin.IsAvailable(line_inv) and PySpin.IsWritable(line_inv):
                line_inv.SetValue(False)  # no inversion

    # Exposure mode timed (avoids overlap issues)
    exp_mode = PySpin.CEnumerationPtr(nodemap.GetNode('ExposureMode'))
    if PySpin.IsAvailable(exp_mode) and PySpin.IsWritable(exp_mode):
        timed = exp_mode.GetEntryByName('Timed')
        if PySpin.IsAvailable(timed) and PySpin.IsReadable(timed):
            exp_mode.SetIntValue(timed.GetValue())

    # Trigger delay (µs)

    trigger_delay = 12

    trig_delay = PySpin.CFloatPtr(nodemap.GetNode('TriggerDelay'))
    if PySpin.IsAvailable(trig_delay) and PySpin.IsWritable(trig_delay):
        # Clamp to allowed range
        dmin, dmax = trig_delay.GetMin(), trig_delay.GetMax()
        trigger_delay = max(min(trigger_delay, dmax), dmin)
        trig_delay.SetValue(trigger_delay)
    else:
        if trigger_delay not in (0, 0.0):
            raise RuntimeError('TriggerDelay not available on this camera.')

    # Turn trigger mode ON (arm for hardware trigger)
    trig_mode_on = trig_mode.GetEntryByName('On')
    trig_mode.SetIntValue(trig_mode_on.GetValue())

    print(f'Hardware trigger configured: FrameStart, Line0, RisingEdge, Overlap = Off, Inverter = False, delay = {trigger_delay:.1f} us') 
