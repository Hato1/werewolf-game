import array
import sys
from typing import TYPE_CHECKING

# Pygbag doesn't support ModernGL, so we only import it on non-web platforms.
# Importlib is required to dynamically import moderngl only on non-web platforms.
# https://pygame-web.github.io/wiki/pygbag/#adding-modules
if TYPE_CHECKING:
    import moderngl
elif sys.platform != "emscripten":
    import importlib

    moderngl = importlib.import_module("moderngl")

import pygame as pg

from my_game.core.logger import get_logger

logger = get_logger(__name__)


class GLRenderer:
    # Is Render Scale still useful?
    # render scale is useful if we want to increase scale of pixel art
    RENDER_SCALE: float = 1

    LIGHT_MODE_DIRECTION = 1
    LIGHT_MODE_POINT = 2

    def __init__(self):
        self.ctx = moderngl.create_context()
        self.ctx.enable(moderngl.BLEND)
        # self.ctx.clear(1, 0, 1, 1)
        # shaders are instructions for the GPU to run.
        # these are essentially glsl files that im writing as
        # multiline strings.

        # vertex shader. doesnt do anything because we're only gonna be
        # drawing to the window's size.
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

        # fragment shader for the lit pass.
        # basically smears light colors in a direction
        lighting_shader = """
                #version 330 core

                uniform sampler2D tex;
                uniform vec2 light_position;
                uniform vec2 screen_size;
                uniform float sample_count;
                uniform float px_per_sample;
                uniform float intensity;
                uniform float light_size;
                uniform bool static_direction;

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
                        if(!static_direction)
                            weight = mix(0, 1, dist_weight);
                        else
                            weight *= 0.99;
                    }
                    sample_total += sample_bonus * intensity;
                    f_color = vec4(sample_total.r , sample_total.g , sample_total.b , 1.0);
                }
                """
        # fragment shader for unlit pass.
        # performs no changes.
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
        # program is a shader, basically. you tell opengl to draw vertecies(vertex shader),
        # then do something on the pixels within those verticies(fragment shader)
        self.program = self.ctx.program(vertex_shader=vert_shader, fragment_shader=lighting_shader)
        self.unlit_program = self.ctx.program(vertex_shader=vert_shader, fragment_shader=unlit_shader)
        self.render_object, self.unlit_render_object = self.create_render_objects()
        self.lit_surface = pg.Surface([640, 640], pg.SRCALPHA, 32)
        self.unlit_surface = pg.Surface([640, 640], pg.SRCALPHA, 32)
        self.unlit_surface.fill(pg.Color(0, 0, 0, 0))
        logger.warning("Initialised OpenGL renderer")

    def create_render_objects(self):
        scene_clamp = 1.0 / self.RENDER_SCALE
        # the quad buffer is the verts that opengl needs to draw.
        # it uses 2 vector2s for each point, being x,y and u,v coordinates
        # uvs are adjusted for render scale. not sure how to explain it,
        # but it is necessary otherwise strange visual artifacts occcur.
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

        self.reset_lit_to_defaults()
        return render_object, unlit_render_object

    # creates a texture usable by opengl from a pygame surface
    # this really doesnt need to be used anywhere but here.
    def surf_to_texture(self, surface: pg.Surface, context: moderngl.Context):
        tex: moderngl.Texture = context.texture(surface.get_size(), 4)
        tex.filter = (moderngl.NEAREST, moderngl.NEAREST)
        tex.swizzle = "BGRA"
        tex.write(surface.get_view("0"))
        return tex

    # run the lit shader.
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
        self.program["light_position"] = mouse_position_on_screen
        self.program["screen_size"] = [
            1 / (self.lit_surface.size[0] * self.RENDER_SCALE),
            1 / (self.lit_surface.size[1] * self.RENDER_SCALE),
        ]
        # self.program['time'] = self.time
        # render it
        self.render_object.render(mode=moderngl.TRIANGLE_STRIP)
        frame_tex.release()

    # run the unlit shader
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
        self.unlit_surface.fill(pg.Color(0, 0, 0, 0))

    # called every frame to actually make things visible.
    # later draw calls are done on top of the previous ones!
    # make sure your surface is transparent!
    def update(self):
        self.draw_lit()
        self.draw_unlit()

    # set the light position of the lit shader.
    def set_light_position(self, x: float, y: float):
        self.program["light_position"] = (x, y)

    # draw a surface to the the unlit surface
    def blit_to_unlit(self, surf: pg.Surface, rect: pg.Rect):
        self.unlit_surface.blit(surf, rect)

    # draw a surface to the lit surface
    def blit_to_lit(self, surf: pg.Surface, rect: pg.Rect):
        self.lit_surface.blit(surf, rect)

    # changes the intensity of the lit shader
    def set_intensity(self, intensity: float):
        self.program["intensity"] = intensity

    # uses normalized value! 1 = screen size, 0.25 is 25% of the screen size, etc.
    # can be larger than 1
    def set_light_size(self, radius: float):
        self.program["light_size"] = radius

    # changes behavior of the light.
    # POINT makes the light emit from the light_position
    # DIRECTION makes the light emit from every pixel
    def set_light_mode(self, light_mode: int):
        if light_mode == self.LIGHT_MODE_DIRECTION:
            self.program["static_direction"] = True
        elif light_mode == self.LIGHT_MODE_POINT:
            self.program["static_direction"] = False

    # px per sample is the distance in pixels the shader will check for each sample
    def set_pixel_per_sample(self, pixels: float):
        self.program["px_per_sample"] = pixels

    # sample count is the number of steps towards a light a pixel will check.
    def set_sample_count(self, samples: int):
        self.program["sample_count"] = samples

    # reset the lit material to default values
    def reset_lit_to_defaults(self):
        self.set_light_size(0.2)
        self.set_intensity(0.2)
        self.set_light_position(0.5, 0.2)
        self.set_light_mode(self.LIGHT_MODE_POINT)
        self.set_pixel_per_sample(1)
        self.set_sample_count(128)


# Notes to self from Penumana:
# use multiple passes.
# each pass a different function, i think we only need 3
# lit, outline, ui
# use a different surface for each pass
