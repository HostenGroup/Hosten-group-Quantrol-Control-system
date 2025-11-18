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

from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtGui import QFont


def show_error_message(text: str, title: str):
    '''
    Display an error pop-up message with the provided title and text.
    
    Args:
        text: The error message text to display
        title: The window title for the error dialog
    '''
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
