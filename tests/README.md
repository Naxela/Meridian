# Meridian Addon - Unit Tests

This directory contains unit tests for the Meridian addon.

## Running Tests

### Method 1: From Blender UI (Easiest)

1. Open Blender
2. Open the **Scripting** workspace
3. In the Python console, run:
   ```python
   bpy.ops.mx.run_tests()
   ```
4. Check the console for test results

### Method 2: From Blender Scripting Workspace

1. Open Blender
2. Go to **Scripting** workspace
3. Open the file: `tests/run_all_tests.py`
4. Click **Run Script** button
5. Check the console for results

### Method 3: Command Line (Headless)

Run tests without opening the Blender GUI:

```bash
blender --background --python "path/to/meridian/tests/run_all_tests.py"
```

### Method 4: Command Line with Expression

Quick one-liner:

```bash
blender --background --python-expr "import bpy; bpy.ops.mx.run_tests()"
```

## Test Structure

```
tests/
├── __init__.py              # Package marker
├── README.md                # This file
├── run_all_tests.py         # Master test runner
├── test_calibration.py      # Tests for light calibration
└── test_helpers.py          # Tests for helper functions
```

## Writing New Tests

### 1. Create a new test file

Create a file named `test_<feature>.py` in the `tests/` directory:

```python
"""
Unit tests for <feature>
"""

import unittest
import sys
import os

# Add addon to path
addon_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if addon_dir not in sys.path:
    sys.path.insert(0, addon_dir)

# Import what you want to test
from your_module import your_function


class TestYourFeature(unittest.TestCase):
    """Test your feature"""

    def test_something(self):
        """Test description"""
        result = your_function(input_value)
        self.assertEqual(result, expected_value)

    def test_something_else(self):
        """Another test"""
        result = your_function(different_input)
        self.assertIsNotNone(result)


def run_tests():
    """Run all tests and return results"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    suite.addTests(loader.loadTestsFromTestCase(TestYourFeature))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result


if __name__ == '__main__':
    run_tests()
```

### 2. Add your test to the master runner

Edit `run_all_tests.py` and add:

```python
from tests import test_calibration, test_helpers, test_your_feature  # Add here

# In run_all_tests() function:
suite.addTests(loader.loadTestsFromModule(test_your_feature))  # Add here
```

## Common Assertions

```python
# Equality
self.assertEqual(a, b)
self.assertNotEqual(a, b)

# Truth
self.assertTrue(x)
self.assertFalse(x)

# Existence
self.assertIsNone(x)
self.assertIsNotNone(x)

# Type checking
self.assertIsInstance(obj, MyClass)

# Membership
self.assertIn(item, collection)
self.assertNotIn(item, collection)

# Numeric comparisons
self.assertGreater(a, b)
self.assertLess(a, b)
self.assertAlmostEqual(a, b, places=7)  # For floats

# Exceptions
self.assertRaises(ExceptionType, function, arg1, arg2)
with self.assertRaises(ExceptionType):
    risky_operation()
```

## Testing Best Practices

1. **Test one thing per test method**
   - Each test should validate one specific behavior
   - Use descriptive names: `test_calibrate_sun_with_multiplier`

2. **Use setUp() and tearDown()**
   ```python
   def setUp(self):
       """Run before each test"""
       self.test_data = create_test_data()

   def tearDown(self):
       """Run after each test"""
       cleanup_test_data()
   ```

3. **Test edge cases**
   - Null/None values
   - Empty collections
   - Negative numbers
   - Very large numbers
   - Boundary conditions

4. **Don't test external dependencies**
   - Mock file I/O
   - Mock network calls
   - Mock Godot executable calls

5. **Keep tests fast**
   - Avoid time.sleep()
   - Don't create actual files unless necessary
   - Use in-memory data structures

## Continuous Integration

To integrate with CI/CD pipelines, run:

```bash
blender --background --python tests/run_all_tests.py -- --exitcode
```

This will exit with code 0 on success, non-zero on failure.

## Debugging Failed Tests

When a test fails, check:

1. **Console output** - Shows which test failed and why
2. **Assertion error** - Shows expected vs actual values
3. **Traceback** - Shows where in your code the error occurred

Add debug output in your tests:

```python
def test_something(self):
    result = calculate_something(input)
    print(f"DEBUG: input={input}, result={result}")
    self.assertEqual(result, expected)
```

## Example Test Session

```
======================================================================
MERIDIAN ADDON - TEST SUITE
======================================================================

test_calibrate_point_default (test_calibration.TestCalibration) ... ok
test_calibrate_spot_default (test_calibration.TestCalibration) ... ok
test_calibrate_sun_default (test_calibration.TestCalibration) ... ok
test_calibrate_with_offset (test_calibration.TestCalibration) ... ok
test_multiplier_has_all_types (test_calibration.TestCalibrationDictionaries) ... ok
test_scene_name_cleaning (test_helpers.TestHelperMethods) ... ok
test_blender_to_godot_coordinate_conversion (test_helpers.TestMatrixConversion) ... ok

----------------------------------------------------------------------
Ran 7 tests in 0.003s

OK

======================================================================
TEST SUMMARY
======================================================================
Tests run: 7
Failures: 0
Errors: 0
Skipped: 0

✓ ALL TESTS PASSED
======================================================================
```

## Resources

- [Python unittest documentation](https://docs.python.org/3/library/unittest.html)
- [Blender Python API](https://docs.blender.org/api/current/)
- [Test-Driven Development (TDD)](https://en.wikipedia.org/wiki/Test-driven_development)
