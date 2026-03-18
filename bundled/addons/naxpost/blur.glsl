#[compute]
#version 450

// Directional blur pass: 1D Gaussian blur along the streak axis
// This is the key shader that creates the anamorphic look.
// By blurring only along one axis, we get the characteristic
// horizontal or vertical streaks.
//
// Uses 13 taps with Gaussian weights for smooth falloff.
// Run twice per mip level for effectively 25-tap coverage.
//
// Input:  Mip texture (sampler, for bilinear filtering)
// Output: Blurred texture (image)

layout(local_size_x = 8, local_size_y = 8, local_size_z = 1) in;

layout(set = 0, binding = 0) uniform sampler2D input_tex;
layout(rgba16f, set = 0, binding = 1) uniform writeonly image2D output_tex;

layout(push_constant, std430) uniform Params {
    float tex_width;
    float tex_height;
    float dir_x;     // Blur direction X * streak_stretch
    float dir_y;     // Blur direction Y * streak_stretch
} params;

// 13-tap Gaussian kernel (sigma ~= 4.0, normalized)
const int KERNEL_SIZE = 13;
const float weights[KERNEL_SIZE] = float[](
    0.0162, 0.0336, 0.0615, 0.0989,
    0.1399, 0.1740, 0.1906,
    0.1740, 0.1399, 0.0989,
    0.0615, 0.0336, 0.0162
);

void main() {
    ivec2 pos = ivec2(gl_GlobalInvocationID.xy);
    ivec2 tex_size = imageSize(output_tex);

    if (pos.x >= tex_size.x || pos.y >= tex_size.y) {
        return;
    }

    vec2 uv = (vec2(pos) + 0.5) / vec2(tex_size);
    vec2 texel = 1.0 / vec2(params.tex_width, params.tex_height);

    // Direction vector in texel space, scaled by streak stretch
    vec2 blur_dir = vec2(params.dir_x, params.dir_y) * texel;

    vec3 result = vec3(0.0);
    int half_size = KERNEL_SIZE / 2;

    for (int i = 0; i < KERNEL_SIZE; i++) {
        float offset = float(i - half_size);
        vec2 sample_uv = uv + blur_dir * offset;
        result += texture(input_tex, sample_uv).rgb * weights[i];
    }

    imageStore(output_tex, pos, vec4(result, 1.0));
}
