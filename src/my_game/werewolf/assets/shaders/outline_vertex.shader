#version 330 core

in vec2 vert;
in vec2 offset;
in vec2 scale;
in vec2 texcoord;
in float outline_amount;
out vec2 uvs;
out float outline_intensity;

void main() {
    uvs = texcoord;
    gl_Position = vec4(vec2(vert.x * scale.x, vert.y * scale.y) + vec2(offset.x, offset.y), 0.0, 1.0);
    outline_intensity = outline_amount;
}
