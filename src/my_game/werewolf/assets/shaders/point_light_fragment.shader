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

in vec2 uvs;
out vec4 f_color;

float remap(float value, float min1, float max1, float min2, float max2) {
  return min2 + (value - min1) * (max2 - min2) / (max1 - min1);
}

vec3 process_light(int index, vec2 uvs){
    if(light_position_radius[index].a <= 0)
        return vec3(0,0,0);

    vec3 light_pos = light_position_radius[index].rgb;
    float light_radius = light_position_radius[index].a;
    vec3 _light_color = light_color_intensity[index].rgb;
    float light_intensity = light_color_intensity[index].a;

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
    return _light_color * ((dist_weight * normal_influence) * light_intensity);
}

void main() {
    vec3 light_color = vec3(1, 0.75, 0.45);
    vec3 sample_total = texture(tex,uvs).rgb;
    //vec4 normal_sample = texture(normals, uvs);
    //vec3 sample_normals = vec3(remap(normal_sample.r, 0, 1, -1, 1), -remap(normal_sample.g, 0, 1, -1, 1), -remap(normal_sample.b, 0, 1, -1, 1));
    //vec3 world_position = vec3(
    //    corrected_uvs.x + ((sample_normals.r * normal_sample.a) * screen_size.x),
    //    corrected_uvs.y + ((sample_normals.g * normal_sample.a) * screen_size.y),
    //    normal_sample.a);

    //float start_distance = distance(light_position.xyz, world_position);
    //vec3 sample_total = texture(tex,uvs).rgb;
    //vec3 sample_bonus = vec3(0,0,0);
    //float weight = 1;
    //vec3 sample_dir_to_light = normalize(light_position - world_position);
    //float normal_influence = clamp(dot(sample_normals, sample_dir_to_light), 0, 1);
    //if(normal_sample.rgb == vec3(0,0,0))
    //   normal_influence = 1;

    //float dist_weight = clamp(1 - ((start_distance)/light_size), 0, 1);
    //sample_total += light_color * ((dist_weight * normal_influence) * intensity);

    for(int i = 0; i < light_color_intensity.length(); i++){
        sample_total += process_light(i, uvs);
    }

    f_color = vec4(sample_total.r , sample_total.g , sample_total.b , 1.0);
}
