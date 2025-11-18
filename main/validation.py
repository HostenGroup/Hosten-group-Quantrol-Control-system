'''
Input validation and expression parsing for Quantrol.

This module contains functions for validating and parsing user input expressions,
sanitizing text input, and displaying error messages.

Author  :   Vyacheslav Li (until 2.0), Andrea Pupic, Alexei Gurchenko (later versions)
Email   :   vyacheslav.li.1991@gmail.com, andrea.pupic@ist.ac.at, alexei.gurchenko@ist.ac.at
Date    :   07.30.2024 (2.0)
Update  :   11.2025 
Version :   2.3.3
Contact :   https://hostenlab.pages.ist.ac.at/contact/
'''


def show_error_message(text: str, title: str):
    '''
    Display an error pop-up message with the provided title and text.
    
    Args:
        text: The error message text to display
        title: The window title for the error dialog
    '''
    from PyQt5.QtWidgets import QMessageBox
    from PyQt5.QtGui import QFont
    
    msg = QMessageBox()
    msg.setFont(QFont('Arial', 14))
    msg.setIcon(QMessageBox.Critical)
    msg.setText("Error")
    msg.setInformativeText(text)
    msg.setWindowTitle(title)
    msg.exec_()


def remove_restricted_characters(text: str) -> str:
    '''
    Remove restricted characters from variable names.
    
    Args:
        text: Initial name as a string
        
    Returns:
        Modified text with restricted characters removed
    '''
    to_remove = "~!@#$%^&*()-=/*+.?[]{;}:\|<>` "
    for character in to_remove:
        text = text.replace(character, "")
    return text


class ExpressionParser:
    '''
    Parser for mathematical expressions with variables.
    
    This class handles parsing and evaluating user input expressions that may contain
    variables, mathematical operators, and different variable types (scanned, ramped, 
    sampled, derived, lookup).
    '''
    
    def __init__(self, experiment, do_scan=False, do_ramp=False):
        '''
        Initialize the expression parser.
        
        Args:
            experiment: The Experiment object containing variables and configuration
            do_scan: Flag indicating if scanning is enabled
            do_ramp: Flag indicating if ramping is enabled
        '''
        self.experiment = experiment
        self.do_scan = do_scan
        self.do_ramp = do_ramp
        
    def decode_input(self, text: str) -> tuple:
        '''
        Decode user input in the form of a simple mathematical expression.
        
        Interprets chunks of text until the next mathematical operator or the end of the text.
        
        Args:
            text: Mathematical expression string with variables and operators
            
        Returns:
            Tuple containing:
                - output_expression: Cleaned expression string
                - output_eval: Expression for Python evaluation
                - output_for_python: Expression for ARTIQ code generation
                - is_scanned: Flag if expression contains scanned variables
                - is_ramped: Flag if expression contains ramped variables
                - is_sampled: Flag if expression contains sampled variables
                - is_derived: Flag if expression contains derived variables
                - is_lookup: Flag if expression contains lookup variables
        '''
        index = 0
        output_eval = ""
        output_expression = ""
        output_for_python = ""
        current = ""
        is_scanned = False
        is_ramped = False
        is_sampled = False
        is_derived = False
        is_lookup = False
        
        text = text.replace(" ", "")  # Remove spaces
        text += "+"  # Add a plus at the end to avoid typing additional operation for the last element
        
        while index < len(text):
            # Adding the next character
            current += text[index]
            index += 1
            
            if text[index] in ["-", "+", "/", "*"]:
                current = current.replace(" ", "")
                
                try:  # If current is convertible to float
                    # Round numbers down to 6 decimal places
                    float_current = float(int(float(current) * 1e6) / 1e6)
                    output_expression += str(float_current) + text[index]
                    output_eval += str(float_current) + text[index]
                    output_for_python += str(float_current) + text[index]
                    
                except:  # If current is a variable name
                    output_expression += current + text[index]
                    output_eval += "self.experiment.variables['" + current + "'].value" + text[index]
                    variable = self.experiment.variables[current]
                    
                    if self.do_scan and variable.is_scanned:  # If scanned assign the python form else assign the value
                        is_scanned = True
                        output_for_python += str(self.experiment.variables[current].for_python) + text[index]
                        
                    elif self.do_ramp and variable.is_ramped:  # If ramped assign the python form else assign the value
                        is_ramped = True
                        output_for_python += str(self.experiment.variables[current].for_python) + text[index]
                        
                    elif current in self.experiment.sampler_variables:  # If sampled assign the name itself
                        output_for_python += "%s" % current + text[index]
                        is_sampled = True
                        
                    elif variable.is_derived:  # If derived assign the name itself
                        output_for_python += "%s" % current + text[index]
                        is_derived = True
                        
                    elif variable.is_lookup:  # If lookup assign the self.name[argument]
                        output_for_python += "self.%s[(%s-1)/0.1]" % (current, self.experiment.variables[current].argument) + text[index]
                        is_lookup = True
                        
                    else:
                        output_for_python += str(variable.value) + text[index]
                        
                current = ""
                index += 1
                
        # Remove all additional characters at the end. Making a+2+ into a+2
        output_eval = output_eval[:-1]
        output_for_python = output_for_python[:-1]
        output_expression = output_expression[:-1]
        
        # If for_python can be evaluated, then just store the value. Otherwise keep the original form
        try:
            temp = None
            exec("temp = " + output_for_python, {"temp": temp})
            output_for_python = str(float(temp))
        except:
            pass
            
        # If evaluation can be evaluated, then store the value. Otherwise keep the original form
        try:
            output_eval = str(float(output_eval))
        except:
            pass
            
        return (output_expression, output_eval, output_for_python, is_scanned, is_ramped, is_sampled, is_derived, is_lookup)


def validate_positive_number(value: float, error_callback=None) -> bool:
    '''
    Validate that a number is non-negative.
    
    Args:
        value: The number to validate
        error_callback: Optional callback function to call on validation error
        
    Returns:
        True if valid (>= 0), False otherwise
    '''
    if value < 0:
        if error_callback:
            error_callback("Negative values are not allowed", "Negative value")
        return False
    return True


def validate_range(value: float, min_val: float, max_val: float, 
                   param_name: str = "Value", error_callback=None) -> bool:
    '''
    Validate that a value is within a specified range.
    
    Args:
        value: The value to validate
        min_val: Minimum allowed value
        max_val: Maximum allowed value
        param_name: Name of the parameter (for error message)
        error_callback: Optional callback function to call on validation error
        
    Returns:
        True if valid, False otherwise
    '''
    if value < min_val or value > max_val:
        if error_callback:
            error_callback(
                f"{param_name} must be between {min_val} and {max_val}",
                "Value out of range"
            )
        return False
    return True
