#[compute]
#version 450

// Downsample pass: 2x downsample with 13-tap filter for anti-aliasing
// Uses the downsample filter from Call of Duty: Advanced Warfare / Jimenez 2014
// Input:  Previous mip level (sampler)
// Output: Next mip level (image, half the size)

layout(local_size_x = 8, local_size_y = 8, local_size_z = 1) in;

layout(set = 0, binding = 0) uniform sampler2D input_tex;
layout(rgba16f, set = 0, binding = 1) uniform writeonly image2D output_tex;

layout(push_constant, std430) uniform Params {
    float src_width;
    float src_height;
    float dst_width;
    float dst_height;
} params;

void main() {
    ivec2 pos = ivec2(gl_GlobalInvocationID.xy);
    ivec2 output_size = imageSize(output_tex);

    if (pos.x >= output_size.x || pos.y >= output_size.y) {
        return;
    }

    vec2 src_texel = 1.0 / vec2(params.src_width, params.src_height);
    vec2 uv = (vec2(pos) + 0.5) / vec2(output_size);

    // 13-tap downsample filter (Jimenez 2014)
    // Samples in a pattern that covers the 4x4 source texel area
    //
    //   a . b . c
    //   . d . e .
    //   f . g . h
    //   . i . j .
    //   k . l . m
    //
    // Weighted to give better results than a simple box filter

    vec3 a = texture(input_tex, uv + src_texel * vec2(-2.0, -2.0)).rgb;
    vec3 b = texture(input_tex, uv + src_texel * vec2( 0.0, -2.0)).rgb;
    vec3 c = texture(input_tex, uv + src_texel * vec2( 2.0, -2.0)).rgb;

    vec3 d = texture(input_tex, uv + src_texel * vec2(-1.0, -1.0)).rgb;
    vec3 e = texture(input_tex, uv + src_texel * vec2( 1.0, -1.0)).rgb;

    vec3 f = texture(input_tex, uv + src_texel * vec2(-2.0,  0.0)).rgb;
    vec3 g = texture(input_tex, uv).rgb;
    vec3 h = texture(input_tex, uv + src_texel * vec2( 2.0,  0.0)).rgb;

    vec3 i = texture(input_tex, uv + src_texel * vec2(-1.0,  1.0)).rgb;
    vec3 j = texture(input_tex, uv + src_texel * vec2( 1.0,  1.0)).rgb;

    vec3 k = texture(input_tex, uv + src_texel * vec2(-2.0,  2.0)).rgb;
    vec3 l = texture(input_tex, uv + src_texel * vec2( 0.0,  2.0)).rgb;
    vec3 m = texture(input_tex, uv + src_texel * vec2( 2.0,  2.0)).rgb;

    // Apply weighted combination
    // Center diamond (d, e, i, j) gets 0.5 weight
    // Corner crosses get 0.125 weight each
    vec3 result = (d + e + i + j) * 0.25 * 0.5;
    result += (a + b + d + g) * 0.25 * 0.125;  // top-left
    result += (b + c + e + g) * 0.25 * 0.125;  // top-right
    result += (d + g + i + f) * 0.25 * 0.125;  // bottom-left  (reuse f instead of k area)
    result += (g + e + j + h) * 0.25 * 0.125;  // bottom-right

    // Additional corner samples for better coverage
    result += (a + c + k + m) * 0.25 * 0.125;  // outer corners

    imageStore(output_tex, pos, vec4(result, 1.0));
}
