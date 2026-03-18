"""
Master test runner for Meridian addon

Run from Blender:
1. Open Blender
2. Go to Scripting workspace
3. Open this file
4. Run script

Or from command line:
blender --background --python "path/to/run_all_tests.py"
"""

import unittest
import sys
import os

# Add addon directory to path
addon_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if addon_dir not in sys.path:
    sys.path.insert(0, addon_dir)

# Import all test modules
from tests import test_calibration, test_helpers


def run_all_tests():
    """Discover and run all tests"""

    print("\n" + "="*70)
    print("MERIDIAN ADDON - TEST SUITE")
    print("="*70 + "\n")

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test modules
    suite.addTests(loader.loadTestsFromModule(test_calibration))
    suite.addTests(loader.loadTestsFromModule(test_helpers))

    # Run tests with verbose output
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Print summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Skipped: {len(result.skipped)}")

    if result.wasSuccessful():
        print("\n✓ ALL TESTS PASSED")
    else:
        print("\n✗ SOME TESTS FAILED")

    print("="*70 + "\n")

    return result


if __name__ == '__main__':
    run_all_tests()
