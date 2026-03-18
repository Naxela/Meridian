#[compute]
#version 450

// Upsample pass: Bilinear upsample from smaller mip + additive blend
// Uses a 9-tap tent filter for smooth upsampling (avoids blocky artifacts).
// The result is scaled by a per-mip weight and additively blended with
// the existing content of the larger mip, accumulating bloom contributions
// from all levels.
//
// Input:  Smaller mip (sampler, bilinear filtered)
// Output: Larger mip (image, read-write for additive blend)

layout(local_size_x = 8, local_size_y = 8, local_size_z = 1) in;

layout(set = 0, binding = 0) uniform sampler2D input_small;
layout(rgba16f, set = 0, binding = 1) uniform image2D output_large;

layout(push_constant, std430) uniform Params {
    float dst_width;
    float dst_height;
    float src_width;
    float src_height;
    float mip_weight;   // Per-mip intensity multiplier
    float _pad1;
    float _pad2;
    float _pad3;
} params;

void main() {
    ivec2 pos = ivec2(gl_GlobalInvocationID.xy);
    ivec2 dst_size = ivec2(params.dst_width, params.dst_height);

    if (pos.x >= dst_size.x || pos.y >= dst_size.y) {
        return;
    }

    vec2 uv = (vec2(pos) + 0.5) / vec2(dst_size);
    vec2 texel = 1.0 / vec2(params.src_width, params.src_height);

    // 9-tap tent filter (3x3 bilinear, weighted)
    //
    //  1  2  1
    //  2  4  2  / 16
    //  1  2  1
    //
    vec3 result = vec3(0.0);
    result += texture(input_small, uv + texel * vec2(-1.0, -1.0)).rgb * 1.0;
    result += texture(input_small, uv + texel * vec2( 0.0, -1.0)).rgb * 2.0;
    result += texture(input_small, uv + texel * vec2( 1.0, -1.0)).rgb * 1.0;
    result += texture(input_small, uv + texel * vec2(-1.0,  0.0)).rgb * 2.0;
    result += texture(input_small, uv).rgb * 4.0;
    result += texture(input_small, uv + texel * vec2( 1.0,  0.0)).rgb * 2.0;
    result += texture(input_small, uv + texel * vec2(-1.0,  1.0)).rgb * 1.0;
    result += texture(input_small, uv + texel * vec2( 0.0,  1.0)).rgb * 2.0;
    result += texture(input_small, uv + texel * vec2( 1.0,  1.0)).rgb * 1.0;
    result /= 16.0;

    // Apply per-mip weight
    result *= params.mip_weight;

    // Additive blend with existing content in the larger mip
    vec3 existing = imageLoad(output_large, pos).rgb;
    imageStore(output_large, pos, vec4(existing + result, 1.0));
}
