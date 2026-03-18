"""
Calibration settings for Blender to Godot conversion

This file contains calibration coefficients to fine-tune the conversion
from Blender to Godot, particularly for light intensity values.

Blender and Godot use different units and scales for lights, so these
coefficients help achieve a more accurate 1:1 visual match.
"""

# ===== LIGHT CALIBRATION =====

# Light energy/intensity multipliers
# These are MULTIPLIED with the Blender light energy value
# Adjust these values to match Blender's appearance in Godot

LIGHT_ENERGY_MULTIPLIER = {
    'SUN': 1.0,       # Directional light multiplier
    'POINT': 0.01,     # Omni light multiplier
    'SPOT': 1.0,      # Spot light multiplier
}

# Additional additive offset (applied AFTER multiplication)
# These are ADDED to the light energy after multiplication
# Use this for fine-tuning baseline brightness

LIGHT_ENERGY_OFFSET = {
    'SUN': 0.0,
    'POINT': 0.0,
    'SPOT': 0.0,
}

# Example adjustments (commented out):
# If Godot lights appear too dim:
# LIGHT_ENERGY_MULTIPLIER = {
#     'SUN': 2.0,
#     'POINT': 1.5,
#     'SPOT': 1.5,
# }

# If Godot lights appear too bright:
# LIGHT_ENERGY_MULTIPLIER = {
#     'SUN': 0.5,
#     'POINT': 0.7,
#     'SPOT': 0.7,
# }


def calibrate_light_energy(light_type, blender_energy):
    """
    Calibrate light energy from Blender to Godot

    Args:
        light_type (str): Type of light ('SUN', 'POINT', 'SPOT')
        blender_energy (float): Original energy value from Blender

    Returns:
        float: Calibrated energy value for Godot
    """
    multiplier = LIGHT_ENERGY_MULTIPLIER.get(light_type, 1.0)
    offset = LIGHT_ENERGY_OFFSET.get(light_type, 0.0)

    calibrated = (blender_energy * multiplier) + offset

    return max(0.0, calibrated)  # Ensure non-negative


# ===== FUTURE CALIBRATION SETTINGS =====
# Add more calibration settings here as needed:
# - Camera FOV adjustments
# - Material property conversions
# - Physics scale factors
# - etc.
