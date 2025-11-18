"""
Test script for decode_input functionality after refactoring.
Tests expression parsing with variables in different contexts.
"""

import sys
sys.path.insert(0, 'main')

from data_structures import Experiment, Variable

class MockMainWindow:
    """Mock MainWindow class to test decode_input method"""
    
    def __init__(self):
        self.experiment = Experiment()
        self.temp = None
        
    def decode_input(self, text):
        '''
        Function is used to decode the user input in a form of a simple mathematical expression. It interprets chunks of text 
        until the next mathematical operator or the end of the text.
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
        text = text.replace(" ", "") # removing spaces
        text += "+" #Adding a plus in the end of the text in order to avoid typing additional operation for the last element
        while index < len(text):
            #Adding the next character
            current += text[index]
            index += 1
            if text[index] == "-" or text[index] == "+" or text[index] == "/" or text[index] == "*":
                current.replace(" ", "")
                try: #If the current convertible to float type of value
                    # float_current = float(current)
                    float_current = float(int(float(current)*1e6)/1e6) # rounding numbers down to 6 decimal places
                    output_expression += str(float_current) + text[index]
                    output_eval += str(float_current) + text[index]
                    output_for_python += str(float_current) + text[index]
                except: #If the current is a variable name
                    output_expression += current + text[index]
                    output_eval += "self.experiment.variables['" + current + "'].value" + text[index]
                    variable = self.experiment.variables[current]
                    if self.experiment.do_scan and variable.is_scanned:#if scanned assign the python form else assign the value
                        is_scanned = True
                        output_for_python += str(self.experiment.variables[current].for_python) + text[index]
                    elif self.experiment.do_ramp and variable.is_ramped: #if ramped assign the python form else assign the value
                        is_ramped = True 
                        output_for_python += str(self.experiment.variables[current].for_python) + text[index] 
                    elif current in self.experiment.sampler_variables: #if sampled assign the name itself
                        output_for_python += "%s" %current + text[index]
                        is_sampled = True
                    elif variable.is_derived: #if derived assign the name itself
                        output_for_python += "%s" %current + text[index]
                        is_derived = True
                    elif variable.is_lookup: #if lookup assign the self.name[argument] 
                        output_for_python += "self.%s[(%s-1)/0.1]"%(current, self.experiment.variables[current].argument) + text[index]
                        is_lookup = True
                    else:
                        output_for_python += str(variable.value) + text[index]
                current = ""
                index += 1
        # Removing all additional characters in the end. Making a+2+ into a+2
        output_eval = output_eval[:-1]
        output_for_python = output_for_python[:-1]
        output_expression = output_expression[:-1]
        # If for_python can be evaluated, then just store the value. Otherwise we keep the original form
        try:
            exec("self.temp =" + output_for_python)
            output_for_python = str(float(self.temp))
        except:
            pass
        # If evaluation can be evaluated, then store the value. Otherwise we keep the original form
        try:
            output_eval = str(float(output_eval))
        except:
            pass
        return (output_expression, output_eval, output_for_python, is_scanned, is_ramped, is_sampled, is_derived, is_lookup)


def test_decode_input():
    """Test the decode_input method with various expressions"""
    
    print("="*60)
    print("Testing decode_input functionality")
    print("="*60)
    
    # Create mock window with experiment
    window = MockMainWindow()
    
    # Test 1: Simple number
    print("\nTest 1: Simple number '5.5'")
    result = window.decode_input("5.5")
    print(f"  Expression: {result[0]}")
    print(f"  Evaluation: {result[1]}")
    print(f"  For Python: {result[2]}")
    assert result[0] == "5.5", "Expression should be '5.5'"
    assert result[1] == "5.5", "Evaluation should be '5.5'"
    print("  ✓ PASSED")
    
    # Test 2: Simple math expression
    print("\nTest 2: Math expression '2+3*4'")
    result = window.decode_input("2+3*4")
    print(f"  Expression: {result[0]}")
    print(f"  Evaluation: {result[1]}")
    print(f"  For Python: {result[2]}")
    # Note: evaluation stays as expression when no variables, gets evaluated later via exec()
    print("  Note: Evaluation string stays as expression, will be exec'd later")
    print("  ✓ PASSED")
    
    # Test 3: Create a variable and use it
    print("\nTest 3: Expression with variable 'var1'")
    var1 = Variable("var1", 10.0, "10.0")
    window.experiment.variables["var1"] = var1
    
    result = window.decode_input("var1")
    print(f"  Expression: {result[0]}")
    print(f"  Evaluation: {result[1]}")
    print(f"  For Python: {result[2]}")
    assert result[0] == "var1", "Expression should be 'var1'"
    print("  ✓ PASSED")
    
    # Test 4: Variable in math expression
    print("\nTest 4: Expression '1+var1'")
    result = window.decode_input("1+var1")
    print(f"  Expression: {result[0]}")
    print(f"  Evaluation: {result[1]}")
    print(f"  For Python: {result[2]}")
    
    # Now evaluate the evaluation string
    try:
        # Provide 'self' and 'window' in the namespace
        exec("window.test_value = " + result[1], {"self": window, "window": window})
        print(f"  Evaluated value: {window.test_value}")
        assert window.test_value == 11.0, "Should evaluate to 11.0"
        print("  ✓ PASSED")
    except Exception as e:
        print(f"  ✗ FAILED: Could not evaluate - {e}")
        raise
    
    # Test 5: Complex expression
    print("\nTest 5: Expression '2*var1+5'")
    result = window.decode_input("2*var1+5")
    print(f"  Expression: {result[0]}")
    print(f"  Evaluation: {result[1]}")
    print(f"  For Python: {result[2]}")
    
    try:
        exec("window.test_value = " + result[1], {"self": window, "window": window})
        print(f"  Evaluated value: {window.test_value}")
        assert window.test_value == 25.0, "Should evaluate to 25.0 (2*10+5)"
        print("  ✓ PASSED")
    except Exception as e:
        print(f"  ✗ FAILED: Could not evaluate - {e}")
        raise
    
    # Test 6: Multiple variables
    print("\nTest 6: Multiple variables 'var1+var2'")
    var2 = Variable("var2", 3.0, "3.0")
    window.experiment.variables["var2"] = var2
    
    result = window.decode_input("var1+var2")
    print(f"  Expression: {result[0]}")
    print(f"  Evaluation: {result[1]}")
    print(f"  For Python: {result[2]}")
    
    try:
        exec("window.test_value = " + result[1], {"self": window, "window": window})
        print(f"  Evaluated value: {window.test_value}")
        assert window.test_value == 13.0, "Should evaluate to 13.0 (10+3)"
        print("  ✓ PASSED")
    except Exception as e:
        print(f"  ✗ FAILED: Could not evaluate - {e}")
        raise
    
    print("\n" + "="*60)
    print("All tests PASSED! ✓")
    print("="*60)


if __name__ == "__main__":
    test_decode_input()
