import array
import sys
from typing import TYPE_CHECKING

from my_game import constants
from my_game.werewolf.assets import Images

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
    RENDER_SCALE: tuple = 4, 4
    TIME: float = 0
    LIGHT_MODE_DIRECTION = 1
    LIGHT_MODE_POINT = 2

    def __init__(self):
        self.ctx = moderngl.create_context()
        self.ctx.enable(moderngl.BLEND)
        self.outline_render_list = []
        self.ctx.clear(0.33, 0.33, 0.33, 1)
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
        outline_vert_shader = """
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
                            gl_Position = vec4(vec2(vert.x * scale.x, vert.y * scale.x) + vec2(offset.x * sin(time + gl_InstanceID), 0.1 + offset.y * sin(time + gl_InstanceID)), 0.0, 1.0);
                            color = vec3(instance_color.x,instance_color.y,instance_color.z);
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

        outline_shader = """
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
            """
        # program is a shader, basically. you tell opengl to draw vertecies(vertex shader),
        # then do something on the pixels within those verticies(fragment shader)
        self.program = self.ctx.program(vertex_shader=vert_shader, fragment_shader=lighting_shader)
        self.unlit_program = self.ctx.program(vertex_shader=vert_shader, fragment_shader=unlit_shader)
        self.outline_program = self.ctx.program(vertex_shader=outline_vert_shader, fragment_shader=outline_shader)

        self.render_object, self.unlit_render_object, self.outline_render_object = self.create_render_objects()
        self.lit_surface = pg.Surface(constants.SCREEN_SIZE, pg.SRCALPHA, 32)
        self.unlit_surface = pg.Surface(constants.SCREEN_SIZE, pg.SRCALPHA, 32)
        self.unlit_surface.fill(pg.Color(0, 0, 0, 0))
        self.lit_surface.fill(pg.Color(0, 0, 0, 0))
        self.outline_surface = pg.Surface(constants.SCREEN_SIZE, pg.SRCALPHA, 32)
        self.outline_surface.fill(pg.Color(0, 0, 0, 0))
        logger.warning("Initialised OpenGL renderer")

    def create_render_objects(self):
        # scene_clamp = [1.0/self.RENDER_SCALE[0], 1.0/self.RENDER_SCALE[1]]
        scene_clamp = [1, 1]
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
                    scene_clamp[0],
                    0.0,
                    -1.0,
                    -1.0,
                    0.0,
                    scene_clamp[1],
                    1.0,
                    -1.0,
                    scene_clamp[0],
                    scene_clamp[1],
                ],
            )
        )
        render_object = self.ctx.vertex_array(self.program, [(quad_buffer, "2f 2f", "vert", "texcoord")])
        unlit_render_object = self.ctx.vertex_array(self.unlit_program, [(quad_buffer, "2f 2f", "vert", "texcoord")])
        # colors = [[1, 0, 0], [0, 1, 0], [0, 0, 1], [1, 1, 1], [0, 1, 1], [1, 1, 0], [1, 0, 1]]
        offset_buffer = self.ctx.buffer(data=array.array("f", [-0.1, 0, -0.2, 0, -0.3, 0, 0, 0.4]))
        scale_buffer = self.ctx.buffer(data=array.array("f", [0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5]))
        outline_render_object = self.ctx.vertex_array(
            self.outline_program,
            [
                (quad_buffer, "2f 2f", "vert", "texcoord"),
                (offset_buffer, "2f /i", "offset"),
                (scale_buffer, "2f /i", "scale"),
            ],
        )

        self.reset_lit_to_defaults()
        return render_object, unlit_render_object, outline_render_object

    # creates a texture usable by opengl from a pygame surface
    # this really doesnt need to be used anywhere but here.
    def surf_to_texture(self, surface: pg.Surface, context: moderngl.Context):
        tex: moderngl.Texture = context.texture(surface.get_size(), 4)
        tex.filter = (moderngl.NEAREST, moderngl.NEAREST)
        tex.swizzle = "BGRA"
        tex.write(surface.get_view("0"))
        return tex

    def add_outline_render_object(self, object: OutlinedRenderObject):
        self.outline_render_list.append(object)

    def create_outline_render_object(
        self, surf: pg.Surface, intensity: float, _z_index: int, offset: tuple, scale: tuple
    ):
        return OutlinedRenderObject(surf, intensity, _z_index, offset, scale)

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
            (pg.mouse.get_pos()[0] / self.lit_surface.size[0]),
            (pg.mouse.get_pos()[1] / self.lit_surface.size[1]),
        )
        self.program["light_position"] = mouse_position_on_screen
        self.program["screen_size"] = [
            1 / (self.lit_surface.size[0] * self.RENDER_SCALE[0]),
            1 / (self.lit_surface.size[1] * self.RENDER_SCALE[1]),
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
        self.draw_outlined_objects()
        self.draw_unlit()
        self.TIME += 0.02

    # most complicated pass because each instance of an object needs to run the outline shader.
    def draw_outlined_objects(self):
        # use foreach to set vertext offset
        # for entry in self.outline_render_list:
        #    pass
        surf = Images.TEST_SHADER.load()
        # self.blit_to_unlit(surf, surf.get_rect())
        # print(surf.get_rect())
        # self.outline_surface.blit(surf,surf.get_rect())
        o_frame_tex = self.surf_to_texture(surf, self.ctx)
        o_frame_tex.use(2)
        self.outline_program["tex"] = 2
        self.outline_program["time"] = self.TIME

        self.outline_render_object.render(mode=moderngl.TRIANGLE_STRIP, instances=4)
        self.outline_render_list.clear()
        o_frame_tex.release()
        self.outline_surface.fill(pg.Color(0, 0, 0, 0))

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

    # does the distance to a light influence the intensity of the lit effect?
    # setting light mode to DIRECTION effectively sets this to true
    def set_ignore_distance(self, *, do_ignore: bool):
        self.program["ignore_distance"] = do_ignore

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
        self.set_light_size(0.1)
        self.set_intensity(0.2)
        self.set_light_position(0.5, 0.2)
        self.set_light_mode(self.LIGHT_MODE_POINT)
        self.set_pixel_per_sample(1)
        self.set_sample_count(128)
        self.set_ignore_distance(do_ignore=True)

    # scales a surface to fit based on current render scale and window scale
    def resize_surface_to_fit(self, surf: pg.Surface):
        raw_size = surf.get_rect()
        var_percent_size = [raw_size[2] / 480, raw_size[3] / 270]
        var_scale = [(var_percent_size[0] * constants.SCREEN_SIZE[0]), (var_percent_size[1] * constants.SCREEN_SIZE[1])]
        return pg.transform.scale(surface=surf, size=[var_scale[0], var_scale[1]])

    # returns a rect of where the ui should be based on screen size
    def get_ui_rect_side(self):
        var_percent_size = [0.75, 1]
        var_scale = [(var_percent_size[0] * constants.SCREEN_SIZE[0]), (var_percent_size[1] * constants.SCREEN_SIZE[1])]
        return pg.Rect(var_scale[0], 0, 480 * (0.25 * constants.SCREEN_SIZE[0]), 1080 * var_scale[1])

    def get_ui_rect(self):
        var_percent_size = [1, 0.359259259]
        var_scale = [(var_percent_size[0] * constants.SCREEN_SIZE[0]), (var_percent_size[1] * constants.SCREEN_SIZE[1])]
        return pg.Rect(
            0, (constants.SCREEN_SIZE[1] * (1 - var_percent_size[1])), 1920 * var_scale[0], 1080 * var_scale[1]
        )


# Notes to self from Penumana:
# use multiple passes.
# each pass a different function, i think we only need 3
# lit, outline, ui
# use a different surface for each pass


# janky solution to get instanced rendering
class OutlinedRenderObject:
    surface: pg.Surface
    highlight_intensity: float
    z_index: int
    offset: tuple
    scale: tuple

    def __init__(self, surf: pg.Surface, intensity: float, _z_index: int, offset: tuple, scale: tuple):
        self.surface = surf
        self.highlight_intensity = intensity
        self.z_index = _z_index
        self.offset = offset
        self.scale = scale


# for multiple light sources in a scene
class SceneLight:
    size: float  # in pixels
    intensity: float  # intensity of the effect, lower number means softer influence
