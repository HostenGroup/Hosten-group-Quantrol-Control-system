"""
Test script for refactored modules
"""
import sys
sys.path.insert(0, 'main')

from pathlib import Path
import pickle
import file_io
from experiment_data import Experiment, Edge, ExperimentalData, Camera
from validation import show_error_message, remove_restricted_characters, ExpressionParser

def test_imports():
    print("✓ All modules imported successfully")

def test_validation():
    # Test remove_restricted_characters
    result = remove_restricted_characters("test-var_123")
    assert result == "testvar_123", f"Expected 'testvar_123', got '{result}'"
    print("✓ Validation: remove_restricted_characters works")
    
    # Test ExpressionParser with experiment object
    exp = Experiment()
    parser = ExpressionParser(exp, do_scan=False, do_ramp=False)
    result = parser.decode_input("2+2")
    # decode_input returns a tuple, check that it doesn't raise an error
    assert isinstance(result, tuple), f"Expected tuple, got {type(result)}"
    print("✓ Validation: ExpressionParser instantiates and runs")

def test_experiment_data():
    # Test creating experiment data
    exp = Experiment()
    exp.sequence = [Edge()]
    exp.experimental_data = ExperimentalData()
    
    # Test Camera with None defaults
    cam = Camera()
    assert cam.gain_db is None, "Camera gain_db should default to None"
    assert cam.exposure_time_ms is None, "Camera exposure_time_ms should default to None"
    print("✓ ExperimentData: Classes instantiate correctly")
    print("✓ ExperimentData: Camera has None defaults")

def test_file_io_save_load():
    # Create test experiment
    exp = Experiment()
    exp.sequence = [Edge()]
    exp.experimental_data = ExperimentalData()
    exp.file_name = "test_original.pkl"
    
    # Test save_experiment
    test_file = "test_save.pkl"
    success, msg, saved_path = file_io.save_experiment(exp, test_file)
    assert success, f"Save failed: {msg}"
    assert Path(test_file).exists(), "Saved file doesn't exist"
    print(f"✓ FileIO: save_experiment works - {msg}")
    
    # Test load_experiment
    success, msg, loaded_exp = file_io.load_experiment(test_file)
    assert success, f"Load failed: {msg}"
    assert hasattr(loaded_exp, 'sequence'), "Loaded experiment missing sequence"
    # The file_name is preserved from the saved object, not updated to the new path
    assert loaded_exp.file_name == "test_original.pkl", "File name should be preserved from save"
    print(f"✓ FileIO: load_experiment works")
    
    # Test backward compatibility
    notes = file_io.ensure_backward_compatibility(loaded_exp)
    print(f"✓ FileIO: ensure_backward_compatibility works ({len(notes)} notes)")
    
    # Cleanup
    Path(test_file).unlink()
    print("✓ FileIO: Test file cleaned up")

def test_file_io_defaults():
    # Create test experiment
    exp = Experiment()
    exp.sequence = [Edge()]
    exp.experimental_data = ExperimentalData()
    
    repo_path = Path.cwd()
    
    # Test save_default_settings
    success, msg = file_io.save_default_settings(exp, repo_path)
    assert success, f"Save default failed: {msg}"
    print(f"✓ FileIO: save_default_settings works - {msg}")
    
    # Test load_default_settings
    success, msg, default_exp = file_io.load_default_settings(repo_path)
    assert success, f"Load default failed: {msg}"
    assert hasattr(default_exp, 'sequence'), "Loaded default missing sequence"
    print(f"✓ FileIO: load_default_settings works")
    
    # Test apply_default_to_experiment
    new_exp = Experiment()
    new_exp.sequence = [Edge(), Edge()]  # Different length
    file_io.apply_default_to_experiment(new_exp, default_exp)
    assert new_exp.sequence[0] is not default_exp.sequence[0], "Should be deep copy"
    print("✓ FileIO: apply_default_to_experiment works")

def test_file_io_helpers():
    # Test get_default_directory
    repo_path = Path.cwd()
    default_dir = file_io.get_default_directory(repo_path)
    assert default_dir.name == "sequences", f"Expected 'sequences', got '{default_dir.name}'"
    print(f"✓ FileIO: get_default_directory works - {default_dir}")
    
    # Test prepare_experiment_for_save
    exp = Experiment()
    exp.experimental_data = ExperimentalData()
    exp.experimental_data.camera = Camera()
    
    # Mock camera_box object
    class MockCameraBox:
        def isChecked(self):
            return True
    
    file_io.prepare_experiment_for_save(exp, camera_box=MockCameraBox(), texp_locked=False)
    assert exp.camera_enabled == True
    assert exp.texp_locked == False
    print("✓ FileIO: prepare_experiment_for_save works")
    
    # Test get_experiment_selection_id
    exp.experimental_data.experiment_id = 5
    row = file_io.get_experiment_selection_id(exp)
    assert row == 5, f"Expected 5, got {row}"
    
    exp.experimental_data.experiment_id = "10"
    row = file_io.get_experiment_selection_id(exp)
    assert row == 10, f"Expected 10, got {row}"
    print("✓ FileIO: get_experiment_selection_id works")

if __name__ == "__main__":
    print("\n=== Testing Refactored Modules ===\n")
    
    try:
        test_imports()
        test_validation()
        test_experiment_data()
        test_file_io_save_load()
        test_file_io_defaults()
        test_file_io_helpers()
        
        print("\n=== All Tests Passed! ✓ ===\n")
        print("Summary:")
        print("  - experiment_data.py: Working correctly")
        print("  - validation.py: Working correctly")
        print("  - file_io.py: Working correctly")
        print("  - All integrations: Working correctly")
        
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
