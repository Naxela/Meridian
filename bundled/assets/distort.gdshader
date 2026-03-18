shader_type spatial;
render_mode unshaded;

uniform sampler2D SCREEN_TEXTURE : hint_screen_texture, filter_linear_mipmap;
uniform sampler2D normal_map : hint_normal;
uniform float strength : hint_range(0.0, 0.05) = 0.01;

void fragment() {
    vec3 n = texture(normal_map, UV).rgb;
    vec2 offset = (n.xy - 0.5) * 2.0 * strength;
    ALBEDO = texture(SCREEN_TEXTURE, SCREEN_UV + offset).rgb;
}