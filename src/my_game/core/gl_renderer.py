import array

import moderngl
import pygame as pg

from my_game.core.logger import get_logger

logger = get_logger(__name__)


# Set OpenGL context attributes for Pygame before creating the window.
# Without this the OpenGL context may not be created with the desired version and profile.
# And on some platforms, failing to set these attributes may result in an incompatible OpenGL context.
pg.init()
pg.display.gl_set_attribute(pg.GL_CONTEXT_MAJOR_VERSION, 3)
pg.display.gl_set_attribute(pg.GL_CONTEXT_MINOR_VERSION, 3)
pg.display.gl_set_attribute(pg.GL_CONTEXT_PROFILE_MASK, pg.GL_CONTEXT_PROFILE_CORE)
pg.display.gl_set_attribute(pg.GL_CONTEXT_FORWARD_COMPATIBLE_FLAG, 1)


class GLRenderer:
    # Is Render Scale still useful?
    RENDER_SCALE: float = 1

    def __init__(self):
        self.ctx = moderngl.create_context()
        self.ctx.enable(moderngl.BLEND)
        # self.ctx.clear(1, 0, 1, 1)
        vert_shader = """
                #version 330 core

                in vec2 vert;
                in vec2 texcoord;
                out vec2 uvs;

                void main() {
                uvs = texcoord;
                gl_Position = vec4(vert, 0.0, 1.0);
                }
                """

        lighting_shader = """
                #version 330 core

                uniform sampler2D tex;
                uniform vec2 mouse_pos;
                uniform vec2 screen_size;
                uniform float sample_count;
                uniform float px_per_sample;

                in vec2 uvs;
                out vec4 f_color;

                void main() {
                    vec2 sample_dir = vec2(0, -screen_size.y);
                    if(mouse_pos != vec2(0,0))
                        sample_dir = -normalize(uvs - mouse_pos) * screen_size;
                    float start_distance = distance(mouse_pos, uvs);
                    float brightness = 1;
                    vec3 sample_total = texture(tex,uvs).rgb;
                    float weight = 1;


                    for(int i = 0; i < sample_count; i++){
                        vec2 sample_pos = uvs + ((sample_dir) * (i * px_per_sample));
                        float distance = distance(sample_pos, mouse_pos);
                        vec3 sample = texture(tex, sample_pos).rgb;
                        //sample_total += vec3(brightness - (distance), 0 ,0);
                        float dist_weight = clamp(1 - ((distance + start_distance)/brightness), 0, 1);
                        sample_total += vec3(sample.x, sample.y, sample.z) * weight / (i + 1);
                        weight = mix(0, 1, dist_weight);
                    }
                    f_color = vec4(sample_total.r , sample_total.g , sample_total.b , 1.0);
                }
                """
        unlit_shader = """
                #version 330 core

                uniform sampler2D tex;

                in vec2 uvs;
                out vec4 f_color;

                void main() {
                    vec4 sample = texture(tex, uvs ).rgba;
                    f_color = vec4(sample.r, sample.g, sample.b, sample.a);
                }
                """
        self.program = self.ctx.program(vertex_shader=vert_shader, fragment_shader=lighting_shader)
        self.unlit_program = self.ctx.program(vertex_shader=vert_shader, fragment_shader=unlit_shader)
        self.render_object, self.unlit_render_object = self.create_render_objects()
        self.lit_surface = pg.Surface([640, 640])
        self.unlit_surface = pg.Surface([640, 640], pg.SRCALPHA, 32)
        self.unlit_surface.fill(pg.Color(0, 0, 0, 0))
        logger.warning("Initialised OpenGL renderer")

    def create_render_objects(self):
        scene_clamp = 1.0 / self.RENDER_SCALE
        quad_buffer = self.ctx.buffer(
            data=array.array(
                "f",
                [
                    # position (x,y), uv coord
                    -1.0,
                    1.0,
                    0.0,
                    0.0,
                    1.0,
                    1.0,
                    scene_clamp,
                    0.0,
                    -1.0,
                    -1.0,
                    0.0,
                    scene_clamp,
                    1.0,
                    -1.0,
                    scene_clamp,
                    scene_clamp,
                ],
            )
        )
        render_object = self.ctx.vertex_array(self.program, [(quad_buffer, "2f 2f", "vert", "texcoord")])
        unlit_render_object = self.ctx.vertex_array(self.unlit_program, [(quad_buffer, "2f 2f", "vert", "texcoord")])

        self.program["sample_count"] = 32
        self.program["px_per_sample"] = 1

        return render_object, unlit_render_object

    def surf_to_texture(self, surface: pg.Surface, context: moderngl.Context):
        tex: moderngl.Texture = context.texture(surface.get_size(), 4)
        tex.filter = (moderngl.NEAREST, moderngl.NEAREST)
        tex.swizzle = "BGRA"
        tex.write(surface.get_view("0"))
        return tex

    def draw_lit(self):
        # these need to be done every frame

        # convert surface to texture
        frame_tex = self.surf_to_texture(self.lit_surface, self.ctx)
        # use this texture
        frame_tex.use(0)
        # set uniform tex to using 0
        self.program["tex"] = 0
        mouse_position_on_screen = (
            (pg.mouse.get_pos()[0] / self.lit_surface.size[0]) * (1 / self.RENDER_SCALE),
            (pg.mouse.get_pos()[1] / self.lit_surface.size[1]) * (1 / self.RENDER_SCALE),
        )
        self.program["mouse_pos"] = mouse_position_on_screen
        self.program["screen_size"] = [
            1 / (self.lit_surface.size[0] * self.RENDER_SCALE),
            1 / (self.lit_surface.size[1] * self.RENDER_SCALE),
        ]
        # self.program['time'] = self.time
        # render it
        self.render_object.render(mode=moderngl.TRIANGLE_STRIP)
        frame_tex.release()

    def draw_unlit(self):
        frame_tex = self.surf_to_texture(self.unlit_surface, self.ctx)
        # use this texture
        frame_tex.use(1)
        # set uniform tex to using 1
        self.unlit_program["tex"] = 1
        # self.program['time'] = self.time
        # render it
        self.unlit_render_object.render(mode=moderngl.TRIANGLE_STRIP)
        frame_tex.release()

    def update(self):
        self.draw_lit()
        self.draw_unlit()

    def set_light_position(self, x: float, y: float):
        self.program["mouse_pos"] = (x, y)

    def blit_to_unlit(self, surf: pg.Surface, rect: pg.Rect):
        self.unlit_surface.blit(surf, rect)

    def blit_to_lit(self, surf: pg.Surface, rect: pg.Rect):
        self.lit_surface.blit(surf, rect)


# Notes to self from Penumana:
# use multiple passes.
# each pass a different function, i think we only need 3
# lit, outline, ui
# use a different surface for each pass
