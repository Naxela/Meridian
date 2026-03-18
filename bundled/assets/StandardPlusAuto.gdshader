shader_type spatial;
render_mode blend_mix,depth_draw_opaque,cull_back,diffuse_burley,specular_schlick_ggx;

uniform vec4 albedo : source_color = vec4(1.0);
uniform sampler2D texture_albedo : source_color, hint_default_white, filter_linear_mipmap, repeat_enable;
uniform sampler2D texture_lightmap : source_color, filter_linear, repeat_enable;
uniform float lightmap_strength : hint_range(0,2) = 1.0;
uniform bool use_bicubic_lightmap = true;
uniform bool lightmap_view = false;
uniform float roughness : hint_range(0,1) = 1.0;
uniform sampler2D texture_metallic : hint_default_white,filter_linear_mipmap,repeat_enable;
uniform vec4 metallic_texture_channel = vec4(1.0, 0.0, 0.0, 0.0);
uniform sampler2D texture_roughness : hint_roughness_g,filter_linear_mipmap,repeat_enable;
uniform float specular = 0.5;
uniform float metallic = 0.0;
uniform float metallic_specular = 1.0;
uniform sampler2D texture_normal : hint_roughness_normal,filter_linear_mipmap,repeat_enable;
uniform float normal_scale : hint_range(-16,16) = 1.0;
uniform sampler2D texture_emission : source_color, hint_default_black,filter_linear_mipmap,repeat_enable;
uniform vec4 emission : source_color = vec4(0.0, 0.0, 0.0, 1.0);
uniform float emission_energy = 1.0;
uniform sampler2D texture_ao : hint_default_white,filter_linear_mipmap,repeat_enable;
uniform float ao_light_affect = 0.0;
uniform vec3 uv1_scale = vec3(1.0, 1.0, 1.0);
uniform vec3 uv1_offset = vec3(0.0, 0.0, 0.0);
uniform vec3 uv2_scale = vec3(1.0, 1.0, 1.0);
uniform vec3 uv2_offset = vec3(0.0, 0.0, 0.0);

// B-spline bicubic filtering (matching Godot's implementation)
// w0, w1, w2, and w3 are the four cubic B-spline basis functions
float w0(float a) {
	return (1.0 / 6.0) * (a * (a * (-a + 3.0) - 3.0) + 1.0);
}

float w1(float a) {
	return (1.0 / 6.0) * (a * a * (3.0 * a - 6.0) + 4.0);
}

float w2(float a) {
	return (1.0 / 6.0) * (a * (a * (-3.0 * a + 3.0) + 3.0) + 1.0);
}

float w3(float a) {
	return (1.0 / 6.0) * (a * a * a);
}

// g0 and g1 are the two amplitude functions
float g0(float a) {
	return w0(a) + w1(a);
}

float g1(float a) {
	return w2(a) + w3(a);
}

// h0 and h1 are the two offset functions
float h0(float a) {
	return -1.0 + w1(a) / (w0(a) + w1(a));
}

float h1(float a) {
	return 1.0 + w3(a) / (w2(a) + w3(a));
}

vec4 texture_bicubic(sampler2D tex, vec2 uv) {
	vec2 texture_size = vec2(textureSize(tex, 0));
	vec2 texel_size = vec2(1.0) / texture_size;

	uv = uv * texture_size + vec2(0.5);

	vec2 iuv = floor(uv);
	vec2 fuv = fract(uv);

	float g0x = g0(fuv.x);
	float g1x = g1(fuv.x);
	float h0x = h0(fuv.x);
	float h1x = h1(fuv.x);
	float h0y = h0(fuv.y);
	float h1y = h1(fuv.y);

	vec2 p0 = (vec2(iuv.x + h0x, iuv.y + h0y) - vec2(0.5)) * texel_size;
	vec2 p1 = (vec2(iuv.x + h1x, iuv.y + h0y) - vec2(0.5)) * texel_size;
	vec2 p2 = (vec2(iuv.x + h0x, iuv.y + h1y) - vec2(0.5)) * texel_size;
	vec2 p3 = (vec2(iuv.x + h1x, iuv.y + h1y) - vec2(0.5)) * texel_size;

	return (g0(fuv.y) * (g0x * texture(tex, p0) + g1x * texture(tex, p1))) +
	       (g1(fuv.y) * (g0x * texture(tex, p2) + g1x * texture(tex, p3)));
}

void vertex() {
	UV = UV * uv1_scale.xy + uv1_offset.xy;
	UV2 = UV2 * uv2_scale.xy + uv2_offset.xy;
}

void fragment() {
	vec2 base_uv = UV;
	vec2 lightmap_uv = UV2;

	// Albedo
	vec4 albedo_tex = texture(texture_albedo, base_uv);
	albedo_tex *= COLOR;

	// Lightmap with B-spline bicubic sampling
	vec4 lightmap_tex;
	if (use_bicubic_lightmap) {
		lightmap_tex = texture_bicubic(texture_lightmap, lightmap_uv);
	} else {
		lightmap_tex = texture(texture_lightmap, lightmap_uv);
	}
	lightmap_tex = mix(vec4(1.0), lightmap_tex, lightmap_strength);

	if (lightmap_view) {
		ALBEDO = lightmap_tex.rgb;
	} else {
		ALBEDO = albedo.rgb * albedo_tex.rgb * lightmap_tex.rgb;
	}

	// Metallic
	float metallic_tex = dot(texture(texture_metallic, base_uv), metallic_texture_channel);
	METALLIC = metallic_tex * metallic;
	SPECULAR = specular * metallic_specular;

	// Roughness
	vec4 roughness_texture_channel = vec4(0.0, 1.0, 0.0, 0.0);
	float roughness_tex = dot(texture(texture_roughness, base_uv), roughness_texture_channel);
	ROUGHNESS = roughness_tex * roughness;

	// Normal
	NORMAL_MAP = texture(texture_normal, base_uv).rgb;
	NORMAL_MAP_DEPTH = normal_scale;

	// Emission
	vec3 emission_tex = texture(texture_emission, base_uv).rgb;
	EMISSION = (emission.rgb + emission_tex) * emission_energy;

	// AO
	AO = texture(texture_ao, base_uv).r;
	AO_LIGHT_AFFECT = ao_light_affect;
}