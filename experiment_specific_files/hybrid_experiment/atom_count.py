####################################################################
# Author: Alexei Gurchenko, Hosten group
# Date: 5 September 2025
####################################################################


def atom_count(camera_counts_number, gain, t_exp, pixel_format):

    atom_num, _total_power = _compute_atom_metrics(camera_counts_number, gain, t_exp, pixel_format)
    return atom_num


def total_power(camera_counts_number, gain, t_exp, pixel_format):

    _atom_num, power = _compute_atom_metrics(camera_counts_number, gain, t_exp, pixel_format)
    return power


def _compute_atom_metrics(camera_counts_number, gain, t_exp, pixel_format):

    pi = 3.141592653589793
    hbar = 1.054e-34
    c = 3e8
    lambd = 780e-9

    format_factors_dict = {
        'Mono8': 256,
        'Mono16': 1,
    }

    I_sat = 35.8 #SI, from steck
    w0 = 7.5*1e-3 /2 #beam waist 1/e2 radius

    format_factor = format_factors_dict[pixel_format]
    
    
    #laser powers, mW
    # P1 = 3.5 
    # P2 = 3.8 
    # P3 = 4.0 
    # P4 = 
    # P5 = 
    # P6 = 
    # P = (P1 + P2 + P3 + P4 + P5 + P6)*1e-3 #total power
    P = 6.3e-3  * 6 #total power
    
    
    I = 2*P/(pi*w0*w0)
    s = I/I_sat #saturation ratio
    
    eta = 0.3 # camera quantum efficiency at 780nm
    adu_gain = 0.18 #ADU gain of the camera (electrons per voltage unit)
    Gamma = 2*pi*6.065*1e6 
    detuning = 0 #in units of Gamma
    D = 21 * 1e-3 #lens aperture
    d0 = 130 * 1e-3 #cloud-to-lens distance
    solid_angle = (pi/4) * (D/d0)**2
    atom_num = camera_counts_number * 8*pi* (1 + 4*detuning**2 + s)/(Gamma*s*t_exp*eta*solid_angle) * adu_gain *10**(-gain/20) * format_factor
    total_power = camera_counts_number * adu_gain * 10**(-gain/20) * format_factor * 2*pi*hbar*c/ (t_exp*eta*lambd)

    return atom_num, total_power
