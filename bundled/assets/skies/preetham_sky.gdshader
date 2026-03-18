shader_type sky;

// ─── Tweakable parameters (show up as sliders in the inspector) ───
uniform float turbidity : hint_range(1.0, 40.0, 0.1) = 2.0;
uniform float rayleigh_coeff : hint_range(0.0, 4.0, 0.01) = 2.5;
uniform float mie_coefficient : hint_range(0.0, 0.1, 0.001) = 0.005;
uniform float mie_directional_g : hint_range(0.0, 0.999, 0.001) = 0.80;
uniform float exposure : hint_range(0.01, 10.0, 0.01) = 1.0;

// ─── Sun disc & glow ───
// sun_size: angular diameter in degrees. Earth's sun is ~0.53°.
// Crank it up for a huge alien star, or down for a distant dim one.
uniform float sun_size : hint_range(0.1, 10.0, 0.01) = 0.53;
uniform float sun_intensity_mult : hint_range(0.0, 5.0, 0.01) = 1.0;
// Soft glow halo around the sun — mimics the bloom from the original
// Blender glow.py post-process, but computed in-shader.
uniform float sun_glow_intensity : hint_range(0.0, 2.0, 0.01) = 0.3;
uniform float sun_glow_falloff : hint_range(1.0, 16.0, 0.1) = 4.0;

// ─── Custom tint ───
// Multiplied into the final sky color. At strength 0 it has no effect.
// Use this to push the sky toward colors that pure scattering can't produce
// (e.g. Titan's orange tholin haze, or a sickly green alien atmosphere).
uniform vec4 sky_tint : source_color = vec4(1.0, 1.0, 1.0, 1.0);
uniform float tint_strength : hint_range(0.0, 1.0, 0.01) = 0.0;

// ─── Atmosphere preset ───
// Selects pre-computed Rayleigh & Mie scattering coefficients for different
// planetary atmospheres. See Python snippet below to compute your own.
uniform int atmosphere : hint_enum("Earth", "Mars", "Dense", "Alien") = 0;

// ─── Pre-computed scattering coefficients ───
// These replace the total_rayleigh() and total_mie() functions to avoid
// extreme float ranges (1e-18 * 1e+14) that can collapse on some GPUs.
// The values are evaluated at float64 precision on a CPU ahead of time.
//
// ┌──────────────────────────────────────────────────────────────────────┐
// │ RECOMPUTING / ADDING PRESETS                                       │
// │                                                                    │
// │ Rayleigh (per channel):                                           │
// │   R(λ) = (8π³(n²-1)²(6+3pn)) / (3N·λ⁴·(6-7pn))                 │
// │                                                                    │
// │ Mie per unit turbidity (per channel):                             │
// │   M(λ) = 0.434 * 0.2 * 1e-17 * π * (2π/λ)^(v-2) * K            │
// │   (note: the original code wrote 10e-18, which equals 1e-17)      │
// │                                                                    │
// │ Source parameters to change per atmosphere:                        │
// │   n  = refractive index    N  = molecular density (molecules/m³)  │
// │   pn = depolarization      K  = Mie K coefficients (vec3 RGB)     │
// │   lambda = (680e-9, 550e-9, 450e-9) in meters, v = 4.0           │
// │                                                                    │
// │ Python:                                                           │
// │   import math; pi = math.pi                                       │
// │   n = 1.0003; N = 2.545e25; pn = 0.035  # change these           │
// │   lambdas = [680e-9, 550e-9, 450e-9]                              │
// │   K = [0.686, 0.678, 0.666]; v = 4.0    # and these              │
// │   for i, L in enumerate(lambdas):                                 │
// │       R = (8*pi**3*(n**2-1)**2*(6+3*pn))/(3*N*L**4*(6-7*pn))     │
// │       M = 0.434 * 0.2e-17 * pi * (2*pi/L)**(v-2) * K[i]         │
// │       print(f"R={R:.10e}  M={M:.4e}")                             │
// └──────────────────────────────────────────────────────────────────────┘

// ── Earth: standard blue sky ──
// n=1.0003, N=2.545e25, pn=0.035, K=(0.686, 0.678, 0.666)
const vec3 RAYLEIGH_EARTH = vec3(5.8045429963e-6, 1.3562911420e-5, 3.0265902469e-5);
const vec3 MIE_EARTH      = vec3(1.5971e-4, 2.4129e-4, 3.5406e-4);

// ── Mars: thin CO2 atmosphere, dusty red/salmon sky ──
// Rayleigh ~2% of Earth (very thin), Mie K=(0.9, 0.5, 0.3) red-shifted dust
const vec3 RAYLEIGH_MARS = vec3(1.1609085993e-7, 2.7125822840e-7, 6.0531804938e-7);
const vec3 MIE_MARS      = vec3(2.0953e-4, 1.7794e-4, 1.5949e-4);

// ── Dense: thick Titan-like atmosphere, deep indigo, heavy haze ──
// Rayleigh 3x Earth, Mie K=(0.5, 0.7, 0.9) blue-shifted haze
const vec3 RAYLEIGH_DENSE = vec3(1.7413628989e-5, 4.0688734260e-5, 9.0797707406e-5);
const vec3 MIE_DENSE      = vec3(1.1641e-4, 2.4912e-4, 4.7846e-4);

// ── Alien: green/teal Mie haze, slightly thinner Rayleigh ──
// Rayleigh 70% of Earth, Mie K=(0.3, 0.9, 0.4) strong green scatter
const vec3 RAYLEIGH_ALIEN = vec3(4.0631800974e-6, 9.4940379939e-6, 2.1186131728e-5);
const vec3 MIE_ALIEN      = vec3(6.9845e-5, 3.2029e-4, 2.1265e-4);

const float RAYLEIGH_ZENITH_LENGTH = 8.4e3;
const float MIE_ZENITH_LENGTH = 1.25e3;
const vec3 UP = vec3(0.0, 1.0, 0.0);

const float EE = 1000.0;

const float CUTOFF_ANGLE = PI / 1.95;
const float STEEPNESS = 1.5;

// Returns scattering coefficients for the selected atmosphere preset
void get_atmosphere(out vec3 rayleigh_total, out vec3 mie_per_turbidity) {
	if (atmosphere == 1) {
		rayleigh_total = RAYLEIGH_MARS;
		mie_per_turbidity = MIE_MARS;
	} else if (atmosphere == 2) {
		rayleigh_total = RAYLEIGH_DENSE;
		mie_per_turbidity = MIE_DENSE;
	} else if (atmosphere == 3) {
		rayleigh_total = RAYLEIGH_ALIEN;
		mie_per_turbidity = MIE_ALIEN;
	} else {
		rayleigh_total = RAYLEIGH_EARTH;
		mie_per_turbidity = MIE_EARTH;
	}
}

// ─── Phase functions ───
float rayleigh_phase(float cos_theta) {
	return (3.0 / (16.0 * PI)) * (1.0 + cos_theta * cos_theta);
}

// Henyey-Greenstein phase function
float hg_phase(float cos_theta, float g) {
	float g2 = g * g;
	return (1.0 / (4.0 * PI))
		 * ((1.0 - g2) / pow(1.0 - 2.0 * g * cos_theta + g2, 1.5));
}

// ─── Sun intensity with earth shadow ───
float sun_intensity(float zenith_angle_cos) {
	return EE * max(0.0, 1.0 - exp(-((CUTOFF_ANGLE - acos(zenith_angle_cos)) / STEEPNESS)));
}

// ─── Main sky function ───
void sky() {
	vec3 direction = EYEDIR;
	vec3 sun_dir = LIGHT0_DIRECTION;

	// Sun fade at horizon.
	// Original used sunPos.z/500 with an unnormalized vector (Blender Z-up).
	// LIGHT0_DIRECTION is normalized and Godot is Y-up, so sun_dir.y replaces
	// that directly — the exponential gives a smooth horizon transition.
	float sunfade = 1.0 - clamp(1.0 - exp(-sun_dir.y), 0.0, 1.0);

	// Reduce rayleigh scattering as sun approaches horizon (redder sunsets)
	float rayleigh_adj = rayleigh_coeff - (1.0 * (1.0 - sunfade));

	// Sun illuminance at current elevation
	float sun_e = sun_intensity(dot(sun_dir, UP));

	// ── Extinction (absorption + out-scattering) ──
	vec3 rayleigh_total;
	vec3 mie_per_turbidity;
	get_atmosphere(rayleigh_total, mie_per_turbidity);

	vec3 beta_r = rayleigh_total * rayleigh_adj;
	vec3 beta_m = mie_per_turbidity * turbidity * mie_coefficient;

	// Optical path length — clamp zenith angle to avoid the singularity at 90°
	float zenith_angle = acos(max(0.0, dot(UP, direction)));
	float denom = cos(zenith_angle) + 0.15 * pow(93.885 - ((zenith_angle * 180.0) / PI), -1.253);
	float s_r = RAYLEIGH_ZENITH_LENGTH / denom;
	float s_m = MIE_ZENITH_LENGTH / denom;

	// Combined extinction factor
	vec3 fex = exp(-(beta_r * s_r + beta_m * s_m));

	// ── In-scattering ──
	float cos_theta = dot(direction, sun_dir);

	float r_phase = rayleigh_phase(cos_theta * 0.5 + 0.5);
	vec3 beta_r_theta = beta_r * r_phase;

	float m_phase = hg_phase(cos_theta, mie_directional_g);
	vec3 beta_m_theta = beta_m * m_phase;

	vec3 scatter_ratio = (beta_r_theta + beta_m_theta) / (beta_r + beta_m);

	vec3 lin = pow(sun_e * scatter_ratio * (1.0 - fex), vec3(1.5));
	lin *= mix(
		vec3(1.0),
		pow(sun_e * scatter_ratio * fex, vec3(0.5)),
		clamp(pow(1.0 - dot(UP, sun_dir), 5.0), 0.0, 1.0)
	);

	// ── Night sky base + solar disc + glow ──
	vec3 l0 = vec3(0.1) * fex;

	// Sun disc — compute angular diameter from uniform (degrees → cosine)
	float sun_angular_cos = cos(sun_size * (PI / 180.0) * 0.5);
	float sundisk = smoothstep(
		sun_angular_cos,
		sun_angular_cos + 0.00002,
		cos_theta
	);
	l0 += (sun_e * 19000.0 * sun_intensity_mult * fex) * sundisk;

	// Soft glow halo around the sun — approximates the bloom from glow.py.
	// Uses a power curve on the angular proximity to the sun.
	float sun_angle = acos(clamp(cos_theta, -1.0, 1.0));
	float glow = exp(-sun_glow_falloff * sun_angle * sun_angle);
	l0 += sun_glow_intensity * sun_e * fex * glow;

	// ── Output linear HDR — let Godot's environment tonemapper handle the rest ──
	vec3 tex_color = (lin + l0) * 0.04;
	tex_color += vec3(0.0, 0.001, 0.0025) * 0.3;

	// Simple exposure control
	vec3 color = tex_color * (exposure * 2.0);

	// Apply custom tint — mix between untinted and tinted based on strength
	vec3 tinted = color * sky_tint.rgb;
	color = mix(color, tinted, tint_strength);

	COLOR = color;
}
