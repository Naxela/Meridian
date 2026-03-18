shader_type spatial;
render_mode blend_mix, depth_test_disabled, depth_draw_never, cull_front, unshaded, shadows_disabled;

// ─── Atmosphere geometry ───
// planet_radius: ratio of planet surface to atmosphere shell (the mesh).
// At 0.9, the planet fills 90% of the sphere and the atmosphere is the outer 10%.
// Example: planet mesh = 500m radius, atmosphere mesh = 550m radius
//          → planet_radius = 500 / 550 = 0.909
uniform float planet_radius : hint_range(0.5, 0.99, 0.001) = 0.85;

// density_falloff: how quickly density drops with altitude.
// Low values (1-3) = thick, even atmosphere. High values (8+) = thin skin.
uniform float density_falloff : hint_range(0.1, 20.0, 0.1) = 4.0;

// atmosphere_height: virtual atmosphere thickness in meters for scattering.
// This decouples the visual look from actual mesh size. Earth's scale height
// is ~8400m. Set this to match the feel you want regardless of mesh radius.
// Example: your shell is 50m thick, but set this to 8400 for Earth-like density.
uniform float atmosphere_height : hint_range(100.0, 100000.0, 100.0) = 8400.0;

// density_scale: additional density multiplier on top of atmosphere_height.
uniform float density_scale : hint_range(0.01, 5.0, 0.01) = 1.0;

// ─── Scattering parameters (same as sky shader) ───
uniform float turbidity : hint_range(1.0, 40.0, 0.1) = 2.0;
uniform float rayleigh_coeff : hint_range(0.0, 4.0, 0.01) = 2.5;
uniform float mie_coefficient : hint_range(0.0, 0.1, 0.001) = 0.005;
uniform float mie_directional_g : hint_range(0.0, 0.999, 0.001) = 0.80;
uniform float exposure : hint_range(0.01, 20.0, 0.01) = 1.0;

// ─── Sun ───
// sun_intensity: brightness of the sun for scattering calculations.
uniform float sun_brightness : hint_range(0.0, 100.0, 0.1) = 22.0;

// sun_direction: world-space direction TOWARD the sun.
// Must match your DirectionalLight3D. Sync with the script below, or set manually.
//
// ┌──────────────────────────────────────────────────────────────────────┐
// │ SYNC SCRIPT — attach to the atmosphere MeshInstance3D:              │
// │                                                                    │
// │   @export var sun_light : DirectionalLight3D                       │
// │                                                                    │
// │   func _process(_delta):                                           │
// │       var mat = mesh.surface_get_material(0) as ShaderMaterial     │
// │       if mat and sun_light:                                        │
// │           mat.set_shader_parameter("sun_direction",                │
// │               sun_light.global_basis.z)                            │
// └──────────────────────────────────────────────────────────────────────┘
uniform vec3 sun_direction = vec3(0.0, 1.0, 0.0);

// ─── Custom tint ───
uniform vec4 sky_tint : source_color = vec4(1.0, 1.0, 1.0, 1.0);
uniform float tint_strength : hint_range(0.0, 1.0, 0.01) = 0.0;

// ─── Atmosphere preset ───
uniform int atmosphere : hint_enum("Earth", "Mars", "Dense", "Alien") = 0;

// ─── Pre-computed scattering coefficients (same as sky shader) ───
const vec3 RAYLEIGH_EARTH = vec3(5.8045429963e-6, 1.3562911420e-5, 3.0265902469e-5);
const vec3 MIE_EARTH      = vec3(1.5971e-4, 2.4129e-4, 3.5406e-4);

const vec3 RAYLEIGH_MARS = vec3(1.1609085993e-7, 2.7125822840e-7, 6.0531804938e-7);
const vec3 MIE_MARS      = vec3(2.0953e-4, 1.7794e-4, 1.5949e-4);

const vec3 RAYLEIGH_DENSE = vec3(1.7413628989e-5, 4.0688734260e-5, 9.0797707406e-5);
const vec3 MIE_DENSE      = vec3(1.1641e-4, 2.4912e-4, 4.7846e-4);

const vec3 RAYLEIGH_ALIEN = vec3(4.0631800974e-6, 9.4940379939e-6, 2.1186131728e-5);
const vec3 MIE_ALIEN      = vec3(6.9845e-5, 3.2029e-4, 2.1265e-4);

// ─── Ray march quality ───
// 16 view samples × 8 light samples = 128 evaluations per pixel.
// Sufficient for a single atmosphere shell covering part of the screen.
const int VIEW_SAMPLES = 16;
const int LIGHT_SAMPLES = 8;

// ─── Varying ───
varying vec3 v_world_pos;

// ─── Functions ───

void get_atmosphere_coeffs(out vec3 r_total, out vec3 m_total) {
	if (atmosphere == 1)      { r_total = RAYLEIGH_MARS;  m_total = MIE_MARS; }
	else if (atmosphere == 2) { r_total = RAYLEIGH_DENSE; m_total = MIE_DENSE; }
	else if (atmosphere == 3) { r_total = RAYLEIGH_ALIEN; m_total = MIE_ALIEN; }
	else                      { r_total = RAYLEIGH_EARTH; m_total = MIE_EARTH; }
}

float rayleigh_phase(float cos_theta) {
	return (3.0 / (16.0 * PI)) * (1.0 + cos_theta * cos_theta);
}

float hg_phase(float cos_theta, float g) {
	float g2 = g * g;
	return (1.0 / (4.0 * PI))
		 * ((1.0 - g2) / pow(1.0 - 2.0 * g * cos_theta + g2, 1.5));
}

// Ray-sphere intersection (sphere at origin).
// Returns (near_t, far_t). Both negative if no hit.
vec2 ray_sphere(vec3 origin, vec3 dir, float radius) {
	float b = 2.0 * dot(origin, dir);
	float c = dot(origin, origin) - radius * radius;
	float disc = b * b - 4.0 * c;
	if (disc < 0.0) return vec2(-1.0, -1.0);
	float sq = sqrt(disc);
	return vec2((-b - sq) * 0.5, (-b + sq) * 0.5);
}

// Atmospheric density at a point in object space.
// Exponential falloff from planet surface to atmosphere edge.
float atmo_density(vec3 pos) {
	float height = length(pos) - planet_radius;
	float normalized = height / (1.0 - planet_radius);
	return exp(-normalized * density_falloff) * density_scale;
}

// ─── Vertex ───
void vertex() {
	v_world_pos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
}

// ─── Fragment ───
void fragment() {
	// ── Work in object space: sphere at origin, radius 1.0 ──
	mat4 inv_model = inverse(MODEL_MATRIX);
	vec3 cam = (inv_model * vec4(CAMERA_POSITION_WORLD, 1.0)).xyz;
	vec3 frag = (inv_model * vec4(v_world_pos, 1.0)).xyz;
	vec3 ray_dir = normalize(frag - cam);

	// Sun direction in object space
	vec3 sun_dir = normalize((inv_model * vec4(normalize(sun_direction), 0.0)).xyz);

	// ── Ray-sphere intersections ──
	vec2 atmo_hit = ray_sphere(cam, ray_dir, 1.0);
	vec2 planet_hit = ray_sphere(cam, ray_dir, planet_radius);

	// No atmosphere intersection (safety check)
	if (atmo_hit.y < 0.0) discard;

	// Entry: start of atmosphere or camera position (whichever is further along the ray)
	float t_start = max(atmo_hit.x, 0.0);
	// Exit: end of atmosphere, but stop at planet surface if the ray hits it
	float t_end = atmo_hit.y;
	if (planet_hit.x > 0.0) {
		t_end = min(t_end, planet_hit.x);
	}

	if (t_start >= t_end) discard;

	// ── Scattering coefficients ──
	vec3 beta_r, beta_m;
	get_atmosphere_coeffs(beta_r, beta_m);
	beta_r *= rayleigh_coeff;
	beta_m *= turbidity * mie_coefficient;

	// ── Path scale ──
	// The scattering coefficients (beta_r, beta_m) are in m⁻¹, but ray marching
	// happens in object space where the atmosphere shell has radius 1.0.
	// We need to convert object-space step distances to real-world meters.
	//
	// The shell thickness in object space is (1.0 - planet_radius). We map this
	// to atmosphere_height meters, so the scattering math sees the correct
	// optical depth regardless of actual mesh size.
	//
	// Example: planet=500m, shell=550m → planet_radius=0.909, shell_thickness=0.091
	//          atmosphere_height=8400 → path_scale = 8400 / 0.091 ≈ 92308
	//          A step of 0.001 in object space = 92.3 meters of atmosphere.
	float shell_thickness = 1.0 - planet_radius;
	float path_scale = atmosphere_height / max(shell_thickness, 0.001);

	// ── Ray march along the view ray ──
	float step_size = (t_end - t_start) / float(VIEW_SAMPLES);

	vec3 total_r_scatter = vec3(0.0);
	vec3 total_m_scatter = vec3(0.0);
	float optical_depth_r = 0.0;
	float optical_depth_m = 0.0;

	for (int i = 0; i < 16; i++) { // VIEW_SAMPLES = 16
		float t = t_start + (float(i) + 0.5) * step_size;
		vec3 pos = cam + ray_dir * t;

		float density = atmo_density(pos);
		float scaled_step = step_size * path_scale;

		// Accumulate optical depth along view ray
		optical_depth_r += density * scaled_step;
		optical_depth_m += density * scaled_step;

		// ── Light ray: optical depth from this point toward the sun ──
		vec2 sun_atmo = ray_sphere(pos, sun_dir, 1.0);

		// Check if planet blocks the sun (shadow)
		vec2 sun_planet = ray_sphere(pos, sun_dir, planet_radius);
		bool in_shadow = (sun_planet.x > 0.0 && sun_planet.y > 0.0);

		if (!in_shadow && sun_atmo.y > 0.0) {
			float sun_path = sun_atmo.y;
			float sun_step = sun_path / float(LIGHT_SAMPLES);
			float light_depth_r = 0.0;
			float light_depth_m = 0.0;

			for (int j = 0; j < 8; j++) { // LIGHT_SAMPLES = 8
				float st = (float(j) + 0.5) * sun_step;
				vec3 sun_pos = pos + sun_dir * st;
				float sd = atmo_density(sun_pos);
				float ss = sun_step * path_scale;
				light_depth_r += sd * ss;
				light_depth_m += sd * ss;
			}

			// Combined extinction: camera→point + point→sun
			vec3 attenuation = exp(-(
				beta_r * (optical_depth_r + light_depth_r) +
				beta_m * (optical_depth_m + light_depth_m)
			));

			total_r_scatter += density * attenuation * scaled_step;
			total_m_scatter += density * attenuation * scaled_step;
		}
	}

	// ── Phase functions ──
	float cos_theta = dot(ray_dir, sun_dir);
	float r_phase = rayleigh_phase(cos_theta);
	float m_phase = hg_phase(cos_theta, mie_directional_g);

	// ── Final in-scattered light ──
	vec3 inscatter = sun_brightness * (
		total_r_scatter * beta_r * r_phase +
		total_m_scatter * beta_m * m_phase
	);

	// ── Extinction (how much the atmosphere absorbs background light) ──
	vec3 extinction = exp(-(beta_r * optical_depth_r + beta_m * optical_depth_m));

	// ── Apply tint and exposure ──
	vec3 color = inscatter * exposure;
	color = mix(color, color * sky_tint.rgb, tint_strength);

	// Alpha: how opaque the atmosphere is (1 = fully opaque, 0 = transparent)
	float alpha = 1.0 - (extinction.r + extinction.g + extinction.b) / 3.0;

	ALBEDO = color;
	ALPHA = clamp(alpha, 0.0, 1.0);
}
