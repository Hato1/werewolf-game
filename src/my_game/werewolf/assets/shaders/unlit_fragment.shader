#version 330 core
//displays the image as is. no funny business
uniform sampler2D tex;

in vec2 uvs;
out vec4 f_color;

void main() {
    vec4 sample = texture(tex, uvs ).rgba;
    f_color = vec4(sample.r, sample.g, sample.b, sample.a);
}
