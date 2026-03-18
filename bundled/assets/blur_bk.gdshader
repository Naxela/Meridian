shader_type spatial;
render_mode unshaded;
uniform sampler2D SCREEN_TEXTURE : hint_screen_texture, filter_linear_mipmap;
uniform sampler2D normal_map : hint_normal;
uniform float strength : hint_range(0.0, 0.05) = 0.01;
uniform float blur_radius : hint_range(0.0, 10.0) = 3.0;
uniform float blur_lod : hint_range(0.0, 5.0) = 2.0;
uniform bool high_quality = false;
uniform bool reflections_enabled = true;
uniform float reflection_strength : hint_range(0.0, 1.0) = 0.3;
uniform float fresnel_power : hint_range(0.0, 5.0) = 2.0;
uniform vec4 tint_color : source_color = vec4(0.8, 0.9, 1.0, 1.0);

void fragment() {
    vec3 n = texture(normal_map, UV).rgb;
    vec2 offset = (n.xy - 0.5) * 2.0 * strength;
    vec2 uv = SCREEN_UV + offset;

    vec3 refracted;
    if (high_quality) {
        vec2 pixel_size = 1.0 / vec2(textureSize(SCREEN_TEXTURE, 0));
        vec3 color = vec3(0.0);
        float total_weight = 0.0;
        for (int x = -3; x <= 3; x++) {
            for (int y = -3; y <= 3; y++) {
                float weight = exp(-float(x * x + y * y) / (2.0 * blur_radius));
                color += texture(SCREEN_TEXTURE, uv + vec2(float(x), float(y)) * pixel_size * blur_radius).rgb * weight;
                total_weight += weight;
            }
        }
        refracted = color / total_weight;
    } else {
        refracted = textureLod(SCREEN_TEXTURE, uv, blur_lod).rgb;
    }

    refracted *= tint_color.rgb;

    if (reflections_enabled) {
        float fresnel = pow(1.0 - abs(dot(NORMAL, VIEW)), fresnel_power);
        vec3 reflect_dir = reflect(-VIEW, NORMAL);
        vec3 env_reflection = textureLod(SCREEN_TEXTURE, SCREEN_UV + reflect_dir.xy * 0.1, blur_lod).rgb;
        ALBEDO = mix(refracted, env_reflection, fresnel * reflection_strength);
    } else {
        ALBEDO = refracted;
    }
}