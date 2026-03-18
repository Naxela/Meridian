#[compute]
#version 450

// Composite pass: Blend the final bloom result onto the scene color buffer
// Supports:
//   - Color tinting (warm/cool/colored bloom)
//   - Additive blend (classic bloom, can blow out)
//   - Screen blend (softer, preserves highlights, HDR-safe via Reinhard)
//   - Softlight blend (subtle, cinematic, good for low-intensity bloom)
//   - Replace blend (bloom replaces scene - useful for debugging)
//
// Input:  Bloom texture at mip 0 (sampler, half-res, bilinear upsampled)
// Output: Scene color buffer (image, read-write)

layout(local_size_x = 8, local_size_y = 8, local_size_z = 1) in;

layout(set = 0, binding = 0) uniform sampler2D bloom_tex;
layout(rgba16f, set = 0, binding = 1) uniform image2D scene_color;

layout(push_constant, std430) uniform Params {
    float screen_width;
    float screen_height;
    float intensity;
    float blend_mode;    // 0 = additive, 1 = screen, 2 = softlight, 3 = replace
    float tint_r;
    float tint_g;
    float tint_b;
    float bloom_mix;     // Mix factor: 0 = scene only, 1 = full bloom blend
} params;

// Pegtop softlight formula (smooth, no hard transitions)
vec3 softlight(vec3 base, vec3 blend_val) {
    return (1.0 - 2.0 * blend_val) * base * base + 2.0 * blend_val * base;
}

void main() {
    ivec2 pos = ivec2(gl_GlobalInvocationID.xy);
    ivec2 screen_size = ivec2(params.screen_width, params.screen_height);

    if (pos.x >= screen_size.x || pos.y >= screen_size.y) {
        return;
    }

    vec2 uv = (vec2(pos) + 0.5) / vec2(screen_size);

    // Sample bloom (bilinear upsampled from half res)
    vec3 bloom = texture(bloom_tex, uv).rgb;

    // Apply tint color
    vec3 tint = vec3(params.tint_r, params.tint_g, params.tint_b);
    bloom *= tint;

    // Apply intensity
    bloom *= params.intensity;

    // Read existing scene color
    vec3 scene = imageLoad(scene_color, pos).rgb;

    vec3 result;
    int mode = int(params.blend_mode + 0.5);

    if (mode == 0) {
        // Additive: simple add
        result = scene + bloom;
    } else if (mode == 1) {
        // Screen blend (HDR-safe via Reinhard tonemap roundtrip)
        vec3 scene_tm = scene / (1.0 + scene);
        vec3 bloom_tm = bloom / (1.0 + bloom);
        vec3 blended = 1.0 - (1.0 - scene_tm) * (1.0 - bloom_tm);
        blended = min(blended, vec3(0.999));
        result = blended / (1.0 - blended);
    } else if (mode == 2) {
        // Softlight: subtle, cinematic look
        // Tonemap to [0,1] for softlight, then reverse
        vec3 scene_tm = scene / (1.0 + scene);
        vec3 bloom_tm = bloom / (1.0 + bloom);
        vec3 blended = softlight(scene_tm, bloom_tm);
        blended = min(blended, vec3(0.999));
        result = blended / (1.0 - blended);
    } else {
        // Replace: bloom replaces scene (debug/artistic)
        result = bloom;
    }

    // Apply bloom mix factor (0 = no bloom, 1 = full effect)
    result = mix(scene, result, params.bloom_mix);

    imageStore(scene_color, pos, vec4(result, 1.0));
}
