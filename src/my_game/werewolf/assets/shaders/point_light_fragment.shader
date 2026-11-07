#version 330 core

uniform sampler2D tex;
uniform sampler2D mask;
uniform sampler2D normals;

uniform bool ignore_mask;
uniform vec2 light_position;
uniform vec2 screen_size;
uniform float sample_count;
uniform float px_per_sample;
uniform float intensity;
uniform float light_size;
uniform bool static_direction;
uniform bool ignore_distance;

in vec2 uvs;
out vec4 f_color;

float remap(float value, float min1, float max1, float min2, float max2) {
  return min2 + (value - min1) * (max2 - min2) / (max1 - min1);
}

void main() {
    vec2 sample_dir = vec2(-screen_size.y, -screen_size.y);
    if(light_position != vec2(0,0) && !static_direction){
        sample_dir = -normalize(uvs - light_position) * screen_size;
    }
    float aspect = screen_size.y/ screen_size.x;
    float inv_aspect = screen_size.x/ screen_size.y;

    vec2 corrected_uvs = vec2(uvs.x,uvs.y);
    corrected_uvs.x *= aspect;
    corrected_uvs.x -= (light_position.x * (aspect - 1.0));

    float start_distance = distance(light_position, corrected_uvs);
    vec3 sample_total = texture(tex,uvs).rgb;
    vec3 sample_bonus = vec3(0,0,0);
    float weight = 1;

    vec3 light_color = vec3(1, 0.75, 0.45);

    vec2 sample_dir_to_light = normalize(light_position - uvs);
    vec3 normal_sample = texture(normals, uvs).rgb;
    vec2 sample_normals = vec2(remap(normal_sample.r, 0, 1, -1, 1), -remap(normal_sample.g, 0, 1, -1, 1));
    float normal_influence = clamp(dot(sample_normals, sample_dir_to_light), 0, 1);
    if(normal_sample.rgb == vec3(0,0,0))
        normal_influence = 1;
    float dist_weight = clamp(1 - ((start_distance)/light_size), 0, 1);
    sample_total += light_color * ((dist_weight * normal_influence) * intensity);
    f_color = vec4(sample_total.r , sample_total.g , sample_total.b , 1.0);
}
