#version 330 core

uniform float time;
in vec2 vert;
in vec2 offset;
in vec2 scale;
in vec2 texcoord;
in vec3 instance_color;
out vec2 uvs;
out vec3 color;

void main() {
    uvs = texcoord;
    gl_Position = vec4(vec2(vert.x * scale.x, vert.y * scale.x) + vec2(offset.x * abs(sin(time * 3.14 + gl_InstanceID)) + gl_InstanceID * 0.1, offset.y * abs(sin(time * 3.14 + gl_InstanceID))), 0.0, 1.0);
    color = vec3(instance_color.x,instance_color.y,instance_color.z);
}
