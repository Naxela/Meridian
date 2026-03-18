"""
Unit tests for calibration module
Run from Blender's scripting workspace or via command line:
blender --background --python-expr "import bpy; bpy.ops.mx.run_tests()"
"""

import unittest
import sys
import os

# Add addon to path
addon_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if addon_dir not in sys.path:
    sys.path.insert(0, addon_dir)

from calibration import calibrate_light_energy, LIGHT_ENERGY_MULTIPLIER, LIGHT_ENERGY_OFFSET


class TestCalibration(unittest.TestCase):
    """Test light calibration functions"""

    def test_calibrate_sun_default(self):
        """Test SUN light with default calibration (1.0 multiplier, 0.0 offset)"""
        result = calibrate_light_energy('SUN', 5.0)
        self.assertEqual(result, 5.0)

    def test_calibrate_point_default(self):
        """Test POINT light with default calibration"""
        result = calibrate_light_energy('POINT', 10.0)
        expected = 10.0 * LIGHT_ENERGY_MULTIPLIER['POINT'] + LIGHT_ENERGY_OFFSET['POINT']
        self.assertEqual(result, expected)

    def test_calibrate_spot_default(self):
        """Test SPOT light with default calibration"""
        result = calibrate_light_energy('SPOT', 15.0)
        self.assertEqual(result, 15.0)

    def test_calibrate_unknown_type(self):
        """Test unknown light type falls back to 1.0 multiplier"""
        result = calibrate_light_energy('UNKNOWN', 5.0)
        self.assertEqual(result, 5.0)

    def test_calibrate_negative_clamping(self):
        """Test that negative results are clamped to 0.0"""
        # Temporarily modify calibration values
        original = LIGHT_ENERGY_MULTIPLIER['SUN']
        LIGHT_ENERGY_MULTIPLIER['SUN'] = -2.0

        result = calibrate_light_energy('SUN', 5.0)
        self.assertEqual(result, 0.0)

        # Restore original
        LIGHT_ENERGY_MULTIPLIER['SUN'] = original

    def test_calibrate_with_offset(self):
        """Test calibration with offset applied"""
        # Temporarily modify calibration values
        original_mult = LIGHT_ENERGY_MULTIPLIER['POINT']
        original_offset = LIGHT_ENERGY_OFFSET['POINT']

        LIGHT_ENERGY_MULTIPLIER['POINT'] = 2.0
        LIGHT_ENERGY_OFFSET['POINT'] = 1.5

        # (5.0 * 2.0) + 1.5 = 11.5
        result = calibrate_light_energy('POINT', 5.0)
        self.assertEqual(result, 11.5)

        # Restore original
        LIGHT_ENERGY_MULTIPLIER['POINT'] = original_mult
        LIGHT_ENERGY_OFFSET['POINT'] = original_offset


class TestCalibrationDictionaries(unittest.TestCase):
    """Test that calibration dictionaries have correct structure"""

    def test_multiplier_has_all_types(self):
        """Test LIGHT_ENERGY_MULTIPLIER has entries for all light types"""
        self.assertIn('SUN', LIGHT_ENERGY_MULTIPLIER)
        self.assertIn('POINT', LIGHT_ENERGY_MULTIPLIER)
        self.assertIn('SPOT', LIGHT_ENERGY_MULTIPLIER)

    def test_offset_has_all_types(self):
        """Test LIGHT_ENERGY_OFFSET has entries for all light types"""
        self.assertIn('SUN', LIGHT_ENERGY_OFFSET)
        self.assertIn('POINT', LIGHT_ENERGY_OFFSET)
        self.assertIn('SPOT', LIGHT_ENERGY_OFFSET)

    def test_multiplier_values_are_numeric(self):
        """Test all multiplier values are numbers"""
        for light_type, value in LIGHT_ENERGY_MULTIPLIER.items():
            self.assertIsInstance(value, (int, float))

    def test_offset_values_are_numeric(self):
        """Test all offset values are numbers"""
        for light_type, value in LIGHT_ENERGY_OFFSET.items():
            self.assertIsInstance(value, (int, float))


def run_tests():
    """Run all tests and return results"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test cases
    suite.addTests(loader.loadTestsFromTestCase(TestCalibration))
    suite.addTests(loader.loadTestsFromTestCase(TestCalibrationDictionaries))

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result


if __name__ == '__main__':
    # Run tests when script is executed directly
    run_tests()
