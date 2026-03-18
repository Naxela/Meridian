#[compute]
#version 450

// Work group size
layout(local_size_x = 8, local_size_y = 8, local_size_z = 1) in;

// Set 0: per-dispatch resources
layout(rgba16f, set = 0, binding = 0) uniform restrict writeonly image2D screen_image;
layout(rgba16f, set = 0, binding = 1) uniform restrict readonly  image2D source_image;
layout(set = 0, binding = 2) uniform sampler2D chromatic_aberration_lut;

// Set 1: parameters via uniform buffer (avoids push constant size limits)
layout(set = 1, binding = 0, std140) uniform Params {
    // Effect toggles
    uint enable_chromatic_aberration;
    uint enable_vignette;
    uint enable_sharpen;
    uint enable_colorgrading;

    // Chromatic Aberration
    float ca_intensity;
    int ca_max_samples;
    float _pad0;
    float _pad1;

    // Vignette
    float vignette_intensity;
    float vignette_smoothness;
    float vignette_roundness;
    float _pad2;
    vec4 vignette_color;

    // Sharpen
    vec4 sharpen_color;
    float sharpen_size;
    float sharpen_strength;
    float _pad3;
    float _pad4;

    // Colorgrading globals
    float whitebalance;
    float shadow_max;
    float highlight_min;
    float _pad5;
    vec4 globalTint;
    vec4 globalSaturation;
    vec4 globalContrast;
    vec4 globalGamma;
    vec4 globalGain;
    vec4 globalOffset;

    // Shadows
    vec4 shadowSaturation;
    vec4 shadowContrast;
    vec4 shadowGamma;
    vec4 shadowGain;
    vec4 shadowOffset;

    // Midtones
    vec4 midtoneSaturation;
    vec4 midtoneContrast;
    vec4 midtoneGamma;
    vec4 midtoneGain;
    vec4 midtoneOffset;

    // Highlights
    vec4 highlightSaturation;
    vec4 highlightContrast;
    vec4 highlightGamma;
    vec4 highlightGain;
    vec4 highlightOffset;
} params;

// ============================================================================
// Colorgrading library (inlined from colorgrading_lib.gdshaderinc)
// ============================================================================

#define LUMINANCE_PRESERVATION 0.75
#define EPSILON 1e-10
#define LUMA1 0.2722287168
#define LUMA2 0.6740817658
#define LUMA3 0.0536895174

float LumaKey(vec3 color) {
    return dot(color, vec3(LUMA1, LUMA2, LUMA3));
}

vec3 ColorTemperatureToRGB(float temperatureInKelvins) {
    vec3 retColor;
    temperatureInKelvins = clamp(temperatureInKelvins, 1000.0, 40000.0) / 100.0;

    if (temperatureInKelvins <= 66.0) {
        retColor.r = 1.0;
        retColor.g = clamp(0.39008157876901960784 * log(temperatureInKelvins) - 0.63184144378862745098, 0.0, 1.0);
    } else {
        float t = temperatureInKelvins - 60.0;
        retColor.r = clamp(1.29293618606274509804 * pow(t, -0.1332047592), 0.0, 1.0);
        retColor.g = clamp(1.12989086089529411765 * pow(t, -0.0755148492), 0.0, 1.0);
    }

    if (temperatureInKelvins >= 66.0)
        retColor.b = 1.0;
    else if (temperatureInKelvins <= 19.0)
        retColor.b = 0.0;
    else
        retColor.b = clamp(0.54320678911019607843 * log(temperatureInKelvins - 10.0) - 1.19625408914, 0.0, 1.0);

    return retColor;
}

float Luminance(vec3 color) {
    float fmin = min(min(color.r, color.g), color.b);
    float fmax = max(max(color.r, color.g), color.b);
    return (fmax + fmin) / 2.0;
}

vec3 HUEtoRGB(float H) {
    float R = abs(H * 6.0 - 3.0) - 1.0;
    float G = 2.0 - abs(H * 6.0 - 2.0);
    float B = 2.0 - abs(H * 6.0 - 4.0);
    return clamp(vec3(R, G, B), vec3(0.0), vec3(1.0));
}

vec3 HSLtoRGB(in vec3 HSL) {
    vec3 RGB = HUEtoRGB(HSL.x);
    float C = (1.0 - abs(2.0 * HSL.z - 1.0)) * HSL.y;
    return (RGB - 0.5) * C + vec3(HSL.z);
}

vec3 RGBtoHCV(vec3 RGB) {
    vec4 P = (RGB.g < RGB.b) ? vec4(RGB.bg, -1.0, 2.0 / 3.0) : vec4(RGB.gb, 0.0, -1.0 / 3.0);
    vec4 Q = (RGB.r < P.x) ? vec4(P.xyw, RGB.r) : vec4(RGB.r, P.yzx);
    float C = Q.x - min(Q.w, Q.y);
    float H = abs((Q.w - Q.y) / (6.0 * C + EPSILON) + Q.z);
    return vec3(H, C, Q.x);
}

vec3 RGBtoHSL(vec3 RGB) {
    vec3 HCV = RGBtoHCV(RGB);
    float L = HCV.z - HCV.y * 0.5;
    float S = HCV.y / (1.0 - abs(L * 2.0 - 1.0) + EPSILON);
    return vec3(HCV.x, S, L);
}

vec3 ToneColorCorrection(vec3 Color, vec3 ColorSaturation, vec3 ColorContrast, vec3 ColorGamma, vec3 ColorGain, vec3 ColorOffset) {
    float ColorLuma = LumaKey(Color);
    Color = max(vec3(0.0), mix(vec3(ColorLuma), Color, ColorSaturation));
    float ContrastCorrectionCoefficient = 0.18;
    Color = pow(Color * (1.0 / ContrastCorrectionCoefficient), ColorContrast) * ContrastCorrectionCoefficient;
    Color = pow(Color, 1.0 / ColorGamma);
    Color = Color.rgb * ColorGain + (ColorOffset - 1.0);
    return Color;
}

vec3 FinalizeColorCorrection(vec3 Color, mat3 ColorSaturation, mat3 ColorContrast, mat3 ColorGamma, mat3 ColorGain, mat3 ColorOffset, vec2 Toneweights) {
    float CCShadowsMax = Toneweights.x;
    float CCHighlightsMin = Toneweights.y;

    float ColorLuma = LumaKey(Color);
    float CCWeightShadows = 1.0 - smoothstep(0.0, CCShadowsMax, ColorLuma);
    float CCWeightHighlights = smoothstep(CCHighlightsMin, 1.0, ColorLuma);
    float CCWeightMidtones = 1.0 - CCWeightShadows - CCWeightHighlights;

    vec3 CCColorShadows = ToneColorCorrection(Color, ColorSaturation[0], ColorContrast[0], ColorGamma[0], ColorGain[0], ColorOffset[0]);
    vec3 CCColorMidtones = ToneColorCorrection(Color, ColorSaturation[1], ColorContrast[1], ColorGamma[1], ColorGain[1], ColorOffset[1]);
    vec3 CCColorHighlights = ToneColorCorrection(Color, ColorSaturation[2], ColorContrast[2], ColorGamma[2], ColorGain[2], ColorOffset[2]);

    return CCColorShadows * CCWeightShadows + CCColorMidtones * CCWeightMidtones + CCColorHighlights * CCWeightHighlights;
}

// ============================================================================
// Effect functions
// ============================================================================

vec3 chromatic_aberration(vec2 uv, ivec2 image_size) {
    vec2 start_pos = uv;
    vec2 end_pos = mix(start_pos, vec2(0.5), params.ca_intensity);

    float texel_length = length((end_pos - start_pos) * vec2(image_size));
    int sample_count = min(int(ceil(texel_length)), params.ca_max_samples);

    vec3 color;
    if (sample_count > 1) {
        ivec2 lut_size = textureSize(chromatic_aberration_lut, 0);
        float lut_u_offset = 0.5 / float(lut_size.x);

        vec3 sample_sum = vec3(0.0);
        vec3 modulate_sum = vec3(0.0);

        for (int sample_index = 0; sample_index < sample_count; sample_index++) {
            float t = (float(sample_index) + 0.5) / float(sample_count);

            vec2 sample_uv = mix(start_pos, end_pos, t);
            ivec2 sample_coord = clamp(ivec2(sample_uv * vec2(image_size)), ivec2(0), image_size - ivec2(1));
            vec3 sample_color = imageLoad(source_image, sample_coord).rgb;

            float lut_u = mix(lut_u_offset, 1.0 - lut_u_offset, t);
            vec3 modulate = textureLod(chromatic_aberration_lut, vec2(lut_u, 0.5), 0.0).rgb;

            sample_sum += sample_color * modulate;
            modulate_sum += modulate;
        }

        color = sample_sum / modulate_sum;
    } else {
        color = imageLoad(source_image, ivec2(uv * vec2(image_size))).rgb;
    }

    return color;
}

vec3 apply_vignette(vec2 uv, vec3 color) {
    vec2 center = vec2(0.5);
    vec2 dist = abs(uv - center);

    float vignette_distance;
    if (params.vignette_roundness > 0.99) {
        vignette_distance = length(uv - center);
    } else if (params.vignette_roundness < 0.01) {
        vignette_distance = max(dist.x, dist.y);
    } else {
        float circular = length(uv - center);
        float rectangular = max(dist.x, dist.y);
        vignette_distance = mix(rectangular, circular, params.vignette_roundness);
    }

    float vignette_factor = 1.0 - smoothstep(params.vignette_smoothness - 0.3, params.vignette_smoothness, vignette_distance);
    vignette_factor = mix(1.0, vignette_factor, params.vignette_intensity);

    return mix(params.vignette_color.xyz, color, vignette_factor);
}

vec3 apply_sharpen(vec2 uv, vec3 color, ivec2 image_size) {
    vec2 texStep = 1.0 / vec2(image_size);

    ivec2 coord1 = clamp(ivec2((uv + vec2(-texStep.x, -texStep.y) * params.sharpen_size) * vec2(image_size)), ivec2(0), image_size - ivec2(1));
    ivec2 coord2 = clamp(ivec2((uv + vec2( texStep.x, -texStep.y) * params.sharpen_size) * vec2(image_size)), ivec2(0), image_size - ivec2(1));
    ivec2 coord3 = clamp(ivec2((uv + vec2(-texStep.x,  texStep.y) * params.sharpen_size) * vec2(image_size)), ivec2(0), image_size - ivec2(1));
    ivec2 coord4 = clamp(ivec2((uv + vec2( texStep.x,  texStep.y) * params.sharpen_size) * vec2(image_size)), ivec2(0), image_size - ivec2(1));

    vec3 col1 = imageLoad(source_image, coord1).rgb;
    vec3 col2 = imageLoad(source_image, coord2).rgb;
    vec3 col3 = imageLoad(source_image, coord3).rgb;
    vec3 col4 = imageLoad(source_image, coord4).rgb;

    vec3 colavg = (col1 + col2 + col3 + col4) * 0.25;
    float edgeMagnitude = length(color - colavg);

    vec3 result;
    if (params.sharpen_strength >= 0.0) {
        result = mix(color, params.sharpen_color.xyz, min(edgeMagnitude * params.sharpen_strength * 2.0, 1.0));
    } else {
        float blur_amount = min(edgeMagnitude * abs(params.sharpen_strength) * 2.0, 1.0);
        result = mix(color, colavg, blur_amount);
    }

    return result;
}

vec3 apply_colorgrading(vec3 final_color) {
    vec3 ColorTempRGB = ColorTemperatureToRGB(params.whitebalance);
    float originalLuminance = Luminance(final_color);
    vec3 blended = mix(final_color, final_color * ColorTempRGB, 1.0);
    vec3 resultHSL = RGBtoHSL(blended);
    vec3 luminancePreservedRGB = HSLtoRGB(vec3(resultHSL.x, resultHSL.y, originalLuminance));
    final_color = mix(blended, luminancePreservedRGB, LUMINANCE_PRESERVATION);

    mat3 CCSaturation = mat3(
        params.globalSaturation.xyz * params.shadowSaturation.xyz,
        params.globalSaturation.xyz * params.midtoneSaturation.xyz,
        params.globalSaturation.xyz * params.highlightSaturation.xyz
    );
    mat3 CCContrast = mat3(
        params.globalContrast.xyz * params.shadowContrast.xyz,
        params.globalContrast.xyz * params.midtoneContrast.xyz,
        params.globalContrast.xyz * params.highlightContrast.xyz
    );
    mat3 CCGamma = mat3(
        params.globalGamma.xyz * params.shadowGamma.xyz,
        params.globalGamma.xyz * params.midtoneGamma.xyz,
        params.globalGamma.xyz * params.highlightGamma.xyz
    );
    mat3 CCGain = mat3(
        params.globalGain.xyz * params.shadowGain.xyz,
        params.globalGain.xyz * params.midtoneGain.xyz,
        params.globalGain.xyz * params.highlightGain.xyz
    );
    mat3 CCOffset = mat3(
        params.globalOffset.xyz * params.shadowOffset.xyz,
        params.globalOffset.xyz * params.midtoneOffset.xyz,
        params.globalOffset.xyz * params.highlightOffset.xyz
    );

    vec2 ToneWeights = vec2(params.shadow_max, params.highlight_min);
    final_color = FinalizeColorCorrection(final_color, CCSaturation, CCContrast, CCGamma, CCGain, CCOffset, ToneWeights);
    final_color *= params.globalTint.xyz;

    return final_color;
}

// ============================================================================
// Main
// ============================================================================

void main() {
    ivec2 coords = ivec2(gl_GlobalInvocationID.xy);
    ivec2 image_size = imageSize(screen_image);

    if (coords.x >= image_size.x || coords.y >= image_size.y) {
        return;
    }

    vec2 uv = (vec2(coords) + 0.5) / vec2(image_size);
    vec3 final_color;

    if (params.enable_chromatic_aberration != 0u) {
        final_color = chromatic_aberration(uv, image_size);
    } else {
        final_color = imageLoad(source_image, coords).rgb;
    }

    if (params.enable_vignette != 0u) {
        final_color = apply_vignette(uv, final_color);
    }

    if (params.enable_sharpen != 0u) {
        final_color = apply_sharpen(uv, final_color, image_size);
    }

    if (params.enable_colorgrading != 0u) {
        final_color = apply_colorgrading(final_color);
    }

    imageStore(screen_image, coords, vec4(final_color, 1.0));
}
