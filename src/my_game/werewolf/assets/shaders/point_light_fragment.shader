#version 330 core

uniform sampler2D tex;
uniform sampler2D mask;
uniform sampler2D normals;


uniform bool ignore_mask;
uniform vec3 light_position;
uniform vec2 screen_size;
uniform float sample_count;
uniform float px_per_sample;
uniform float intensity;
uniform float light_size;
uniform bool static_direction;
uniform bool ignore_distance;


//you get 6 point lights and you'll like it!
uniform vec4 light_position_radius[6];
uniform vec4 light_color_intensity[6];
uniform float light_flicker_intensity[6];

uniform vec3 ambient_light;

uniform float Time;

in vec2 uvs;
out vec4 f_color;

float remap(float value, float min1, float max1, float min2, float max2) {
  return min2 + (value - min1) * (max2 - min2) / (max1 - min1);
}

vec3 permute(vec3 x) { return mod(((x*34.0)+1.0)*x, 289.0); }

//simplex noise function i got from https://gist.github.com/patriciogonzalezvivo/670c22f3966e662d2f83
float snoise(vec2 v){
  const vec4 C = vec4(0.211324865405187, 0.366025403784439,
           -0.577350269189626, 0.024390243902439);
  vec2 i  = floor(v + dot(v, C.yy) );
  vec2 x0 = v -   i + dot(i, C.xx);
  vec2 i1;
  i1 = (x0.x > x0.y) ? vec2(1.0, 0.0) : vec2(0.0, 1.0);
  vec4 x12 = x0.xyxy + C.xxzz;
  x12.xy -= i1;
  i = mod(i, 289.0);
  vec3 p = permute( permute( i.y + vec3(0.0, i1.y, 1.0 ))
  + i.x + vec3(0.0, i1.x, 1.0 ));
  vec3 m = max(0.5 - vec3(dot(x0,x0), dot(x12.xy,x12.xy),
    dot(x12.zw,x12.zw)), 0.0);
  m = m*m ;
  m = m*m ;
  vec3 x = 2.0 * fract(p * C.www) - 1.0;
  vec3 h = abs(x) - 0.5;
  vec3 ox = floor(x + 0.5);
  vec3 a0 = x - ox;
  m *= 1.79284291400159 - 0.85373472095314 * ( a0*a0 + h*h );
  vec3 g;
  g.x  = a0.x  * x0.x  + h.x  * x0.y;
  g.yz = a0.yz * x12.xz + h.yz * x12.yw;
  return 130.0 * dot(m, g);
}

float evaluate_flicker(float light_intensity, float flicker_amount, int index){
    return mix(light_intensity,light_intensity * remap(snoise(vec2(Time,index * 16.0)), -1, 1, 0, 1), flicker_amount); //
}

vec3 process_light(int index, vec2 uvs){
    if(light_position_radius[index].a <= 0)
        return vec3(0,0,0);

    vec3 light_pos = light_position_radius[index].rgb;
    float light_radius = light_position_radius[index].a;
    vec3 _light_color = light_color_intensity[index].rgb;
    float light_intensity = light_color_intensity[index].a;
    float flicker = light_flicker_intensity[index];


    float aspect = screen_size.y/ screen_size.x;

    vec2 corrected_uvs = vec2(uvs.x,uvs.y);
    corrected_uvs.x *= aspect;
    corrected_uvs.x -= (light_pos.x * (aspect - 1.0));

    vec4 normal_sample = texture(normals, uvs);
    vec3 sample_normals = vec3(remap(normal_sample.r, 0, 1, -1, 1), -remap(normal_sample.g, 0, 1, -1, 1), -remap(normal_sample.b, 0, 1, -1, 1));
    vec3 world_position = vec3(
        corrected_uvs.x + ((sample_normals.r * normal_sample.a) * screen_size.x),
        corrected_uvs.y + ((sample_normals.g * normal_sample.a) * screen_size.y),
        normal_sample.a);

    float start_distance = distance(light_pos, world_position);
    vec3 sample_bonus = vec3(0,0,0);
    float weight = 1;
    vec3 sample_dir_to_light = normalize(light_pos - world_position);
    float normal_influence = clamp(dot(sample_normals, sample_dir_to_light), 0, 1);
    if(normal_sample.rgb == vec3(0,0,0))
        normal_influence = 1;

    float dist_weight = clamp(1 - ((start_distance)/light_radius), 0, 1);
    return _light_color * ((dist_weight * normal_influence) * evaluate_flicker(light_intensity, flicker, index));
}

void main() {
    vec3 light_color = vec3(1, 0.75, 0.45);
    vec3 sample_base = texture(tex,uvs).rgb;
    vec3 light_samples = vec3(0,0,0);
    float light_mask = 0;
    for(int i = 0; i < light_color_intensity.length(); i++){
        vec3 light = process_light(i, uvs);
        light_samples += light;
        light_mask += light.x + light.y + light.z;
    }
    vec3 sample_total = sample_base + (light_samples);

    f_color = vec4(sample_total.r , sample_total.g , sample_total.b , 1.0);
}
