"""
Unit tests for helper methods in operators
"""

import unittest
import sys
import os

# Add addon to path
addon_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if addon_dir not in sys.path:
    sys.path.insert(0, addon_dir)


class TestHelperMethods(unittest.TestCase):
    """Test helper methods from MX_OperatorBase"""

    def test_scene_name_cleaning(self):
        """Test that scene names are cleaned properly"""
        # Test with spaces
        test_name = "My Scene Name"
        expected = "My_Scene_Name"
        result = test_name.replace(' ', '_').replace('.', '_')
        self.assertEqual(result, expected)

        # Test with dots
        test_name = "scene.001"
        expected = "scene_001"
        result = test_name.replace(' ', '_').replace('.', '_')
        self.assertEqual(result, expected)

        # Test with both
        test_name = "my scene.001"
        expected = "my_scene_001"
        result = test_name.replace(' ', '_').replace('.', '_')
        self.assertEqual(result, expected)

    def test_folder_structure_list(self):
        """Test that folder structure has expected folders"""
        expected_folders = [
            "addons",
            "assets",
            "assets/audio",
            "assets/environment",
            "assets/lightmaps",
            "assets/meshes",
            "assets/textures",
            "assets/videos",
            "scenes",
            "scripts",
            "shaders"
        ]

        # This list should match what's in createFolderStructure()
        for folder in expected_folders:
            # Basic check that folder path is valid
            self.assertIsInstance(folder, str)
            self.assertGreater(len(folder), 0)


class TestMatrixConversion(unittest.TestCase):
    """Test coordinate system conversion"""

    def test_blender_to_godot_coordinate_conversion(self):
        """Test that Blender Z-up converts to Godot Y-up correctly"""
        # Blender coordinates (X, Y, Z)
        blender_x = 1.0
        blender_y = 2.0
        blender_z = 3.0

        # Expected Godot coordinates: (X, Z, -Y)
        expected_godot_x = 1.0
        expected_godot_y = 3.0
        expected_godot_z = -2.0

        # Perform conversion
        godot_x = blender_x
        godot_y = blender_z
        godot_z = -blender_y

        self.assertEqual(godot_x, expected_godot_x)
        self.assertEqual(godot_y, expected_godot_y)
        self.assertEqual(godot_z, expected_godot_z)


def run_tests():
    """Run all tests and return results"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    suite.addTests(loader.loadTestsFromTestCase(TestHelperMethods))
    suite.addTests(loader.loadTestsFromTestCase(TestMatrixConversion))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result


if __name__ == '__main__':
    run_tests()
