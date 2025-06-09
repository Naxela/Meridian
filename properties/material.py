import bpy, os
from bpy.props import *

class NEST_MaterialProperties(bpy.types.PropertyGroup):

    nest_material_reflectance : FloatProperty(
        name="Reflectance",
        description="Specular intensity for non-metals on a linear scale of 0 to 1.",
        default=0.5
    )

    nest_material_texture_x_expression : StringProperty(
        name="X-Coord expression",
        description="Mathematical expressions for the x-coordinate of the Texture coordinate.",
        default=""
    )

    nest_material_texture_y_expression : StringProperty(
        name="Y-Coord expression",
        description="Mathematical expressions for the y-coordinate of the Texture coordinate.",
        default=""
    )

    nest_material_blend_mode : EnumProperty(
        items = [('Opaque', 'Opaque', 'Base color alpha values are overridden to be fully opaque (1.0)'),
                ('Blend', 'Blend', 'The base color alpha value defines the opacity of the color. Standard alpha-blending is used to blend the fragment’s color with the color behind it'),
                ('Premultiplied', 'Premultiplied', 'Similar to Blend, however assumes RGB channel values are premultiplied. For otherwise constant RGB values, behaves more like Blend for alpha values closer to 1.0, and more like Add for alpha values closer to 0.0. Can be used to avoid “border” or “outline” artifacts that can occur when using plain alpha-blended textures'),
                ('AlphaToCoverage', 'AlphaToCoverage', 'Alpha to coverage provides improved performance and better visual fidelity over Blend, as Bevy doesn’t have to sort objects when it’s in use. It’s especially useful for complex transparent objects like foliage.'),
                ('Add', 'Add', 'Combines the color of the fragments with the colors behind them in an additive process, (i.e. like light) producing lighter results. Black produces no effect. Alpha values can be used to modulate the result. Useful for effects like holograms, ghosts, lasers and other energy beams'),
                ('Multiply', 'Multiply', 'Combines the color of the fragments with the colors behind them in a multiplicative process, (i.e. like pigments) producing darker results. White produces no effect. Alpha values can be used to modulate the result. Useful for effects like stained glass, window tint film and some colored liquids')],
                name = "Alpha mode", 
                description="Sets how a material’s base color alpha channel is used for transparency", 
                default='Opaque')

    nest_material_diffuse_transmission : FloatProperty(
        name="Diffuse transmission",
        description="The amount of light transmitted diffusely. Requires enabling the PBR Transmission option",
        default=0.0
    )

    nest_material_specular_transmission : FloatProperty(
        name="Specular transmission",
        description="The amount of light transmitted specularly through the material (i.e. via refraction). Requires enabling the PBR Transmission option",
        default=0.0
    )

    nest_material_ior : FloatProperty(
        name="IOR",
        description="The index of refraction of the material",
        default=1.5
    )

    nest_material_parallax : FloatProperty(
        name="SSAO Object Thickness",
        description="This value is used to decide how far behind an object a ray of light needs to be in order to pass behind it. Any ray closer than that will be occluded",
        default=0.25
    )
