#version 330 core

uniform sampler2D tex;
in vec2 uvs;
//in float outline_intensity;
in vec3 color;
out vec4 f_color;

void main() {
    vec4 sample = texture(tex, uvs ).rgba;
    f_color = vec4(vec3(sample.r,sample.g,sample.b),1);
}
