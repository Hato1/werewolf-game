#version 330 core

uniform sampler2D tex;
in vec2 uvs;
in float outline_intensity;
in vec3 color;
out vec4 f_color;

void main() {
    vec4 sample = texture(tex, uvs ).rgba;

    float up = texture(tex, uvs + vec2(0, 0.02)).a;
    float down = texture(tex, uvs + vec2(0, -0.02)).a;
    float left = texture(tex, uvs + vec2(0.02, 0)).a;
    float right = texture(tex, uvs + vec2(-0.02, 0)).a;

    float m = sample.a - max(max(up, down), max(left, right));
    float i = outline_intensity * abs(m);
    //if(uvs.x<=0.025 || uvs.x >= 0.975 || uvs.y <= 0.025 || uvs.y >= 0.975)
    //    i = outline_intensity;

    vec3 color_out = vec3(mix(sample.r, 1, i), mix(sample.g, 0, i), mix(sample.b, 0, i));

    f_color = vec4(color_out.rgb,sample.a + abs(m));
}
