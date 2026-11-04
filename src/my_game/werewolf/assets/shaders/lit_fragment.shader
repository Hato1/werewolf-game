#version 330 core

uniform sampler2D tex;
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

void main() {
    vec2 sample_dir = vec2(-screen_size.y, -screen_size.y);
    if(light_position != vec2(0,0) && !static_direction){
        sample_dir = -normalize(uvs - light_position) * screen_size;
    }
    float start_distance = distance(light_position, uvs);
    vec3 sample_total = texture(tex,uvs).rgb;
    vec3 sample_bonus = vec3(0,0,0);
    float weight = 1;

    for(int i = 0; i < sample_count; i++){
        vec2 sample_pos = uvs + ((sample_dir) * (i * px_per_sample));
        float distance = distance(sample_pos, light_position);
        vec2 sample_dir_to_light = normalize(light_position - sample_pos);
        if(dot(sample_dir_to_light, normalize(sample_dir)) < 0.7 && !static_direction){
            //end early
            float percent_left = 1 - (i / (sample_count));
            sample_bonus += vec3(sample_total.x, sample_total.y, sample_total.z) * percent_left;
            break;
        }
        vec3 sample = texture(tex, sample_pos).rgb;
        //sample_total += vec3(light_size - (distance), 0 ,0);
        float dist_weight = clamp(1 - ((distance + start_distance)/light_size), 0, 1);
        sample_bonus += vec3(sample.x, sample.y, sample.z) * weight / (i + 1);
        if(!static_direction && !ignore_distance)
            weight = mix(0, 1, dist_weight);
        else
            weight *= 0.99;
    }
    sample_total += sample_bonus * intensity;
    f_color = vec4(sample_total.r , sample_total.g , sample_total.b , 1.0);
}
