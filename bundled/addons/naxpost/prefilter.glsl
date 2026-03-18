#[compute]
#version 450

// Prefilter pass: Extract pixels above luminance threshold
// Supports:
//   - Strength: pre-multiplier on scene color before thresholding
//   - HDR Scale: controls how aggressively HDR values contribute
//   - HDR Luminance Cap: clamps maximum luminance to prevent fireflies
//
// Input:  Full-resolution scene color (sampler)
// Output: Half-resolution bright pixels (image)

layout(local_size_x = 8, local_size_y = 8, local_size_z = 1) in;

layout(set = 0, binding = 0) uniform sampler2D input_color;
layout(rgba16f, set = 0, binding = 1) uniform writeonly image2D output_bright;

layout(push_constant, std430) uniform Params {
    float threshold;
    float soft_knee;
    float src_width;
    float src_height;
    float strength;       // Pre-multiplier on input luminance
    float hdr_scale;      // HDR contribution scaling
    float hdr_lum_cap;    // Maximum luminance clamp (0 = disabled)
    float _pad;
} params;

// Reduce fireflies with a 2x2 box filter during downsample
vec3 sample_box(vec2 uv, vec2 texel_size) {
    vec3 a = texture(input_color, uv + texel_size * vec2(-0.5, -0.5)).rgb;
    vec3 b = texture(input_color, uv + texel_size * vec2( 0.5, -0.5)).rgb;
    vec3 c = texture(input_color, uv + texel_size * vec2(-0.5,  0.5)).rgb;
    vec3 d = texture(input_color, uv + texel_size * vec2( 0.5,  0.5)).rgb;
    return (a + b + c + d) * 0.25;
}

// Soft threshold curve (Call of Duty: Advanced Warfare technique)
vec3 apply_threshold(vec3 color) {
    float brightness = max(color.r, max(color.g, color.b));
    float knee = params.threshold * params.soft_knee;
    float soft = brightness - params.threshold + knee;
    soft = clamp(soft, 0.0, 2.0 * knee);
    soft = soft * soft / (4.0 * knee + 0.00001);
    float contribution = max(soft, brightness - params.threshold);
    contribution /= max(brightness, 0.00001);
    return color * max(contribution, 0.0);
}

void main() {
    ivec2 pos = ivec2(gl_GlobalInvocationID.xy);
    ivec2 output_size = imageSize(output_bright);

    if (pos.x >= output_size.x || pos.y >= output_size.y) {
        return;
    }

    vec2 texel_size = 1.0 / vec2(params.src_width, params.src_height);
    vec2 uv = (vec2(pos) + 0.5) / vec2(output_size);

    // Sample with box filter to reduce fireflies
    vec3 color = sample_box(uv, texel_size);

    // Apply strength (pre-multiplier)
    color *= params.strength;

    // Apply HDR luminance cap if enabled (value > 0)
    if (params.hdr_lum_cap > 0.0) {
        float lum = max(color.r, max(color.g, color.b));
        if (lum > params.hdr_lum_cap) {
            color *= params.hdr_lum_cap / lum;
        }
    }

    // Apply HDR scale: boost values above 1.0 more aggressively
    // hdr_scale controls how much extra contribution HDR values get
    // At scale=1.0 this is neutral; higher values amplify bright areas
    float lum = max(color.r, max(color.g, color.b));
    if (lum > 1.0 && params.hdr_scale > 0.0) {
        float hdr_boost = 1.0 + (lum - 1.0) * (params.hdr_scale - 1.0);
        hdr_boost = max(hdr_boost, 0.0);
        color *= hdr_boost / max(lum, 0.00001);
    }

    // Apply luminance threshold
    vec3 bright = apply_threshold(color);

    imageStore(output_bright, pos, vec4(bright, 1.0));
}
