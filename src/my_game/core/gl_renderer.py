import array
import sys
from enum import Enum
from typing import TYPE_CHECKING

from my_game import constants
from my_game.werewolf.assets import Shaders

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


class RenderPassType(Enum):
    LIT_PASS = 0
    OUTLINE_PASS = 1
    UNLIT_PASS = 2


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
        self.vert_shader = Shaders.load(Shaders.STANDARD_VERT)

        # fragment shader for the lit pass.
        # basically smears light colors in a direction
        self.outline_vert_shader = Shaders.load(Shaders.OUTLINE_VERT)

        # fragment shader for the lit pass.
        # basically smears light colors in a direction
        self.lighting_shader = Shaders.load(Shaders.LIT_FRAG)
        # fragment shader for unlit pass.
        # performs no changes.
        self.unlit_shader = Shaders.load(Shaders.UNLIT_FRAG)
        # with open("src/my_game/werewolf/assets/shaders/outline_fragment.shader", "r", encoding="utf-8") as f:
        self.outline_shader = Shaders.load(Shaders.OUTLINE_FRAG)
        # program is a shader, basically. you tell opengl to draw vertecies(vertex shader),
        # then do something on the pixels within those verticies(fragment shader)
        self.program = self.ctx.program(vertex_shader=self.vert_shader, fragment_shader=self.lighting_shader)
        self.unlit_program = self.ctx.program(vertex_shader=self.vert_shader, fragment_shader=self.unlit_shader)
        self.outline_program = self.ctx.program(
            vertex_shader=self.outline_vert_shader, fragment_shader=self.outline_shader
        )

        self.render_object, self.unlit_render_object, self.outline_render_object = self.create_render_objects()
        self.lit_surface = pg.Surface(constants.SCREEN_SIZE, pg.SRCALPHA, 32)
        self.unlit_surface = pg.Surface(constants.SCREEN_SIZE, pg.SRCALPHA, 32)
        self.unlit_surface.fill(pg.Color(0, 0, 0, 0))
        self.lit_surface.fill(pg.Color(0, 0, 0, 0))
        self.mask_surface = pg.Surface(constants.SCREEN_SIZE, pg.SRCALPHA, 32)
        self.mask_surface.fill(pg.Color(0, 0, 0, 0))
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

        # texture_buffer = self.ctx.buffer(data=[])
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
        tex.repeat_x = False
        tex.repeat_y = False
        tex.swizzle = "BGRA"
        tex.write(surface.get_view("0"))
        return tex

    # add an object to the draw queue. the queue is cleared after each frame.
    def queue_outline_render_object(self, object: OutlinedRenderObject):
        self.outline_render_list.append(object)

    # create a render object to use with the draw queue.
    def create_outline_render_object(
        self, surf: pg.Surface, intensity: float, _z_index: int, offset: tuple, pixel_size: tuple
    ):
        screen_size = self.pixel_to_screen_size(pixel_size)
        return OutlinedRenderObject(
            surf, intensity, _z_index, self.pixel_to_screen_offset(offset, screen_size), screen_size
        )

    # run the lit shader.
    def draw_lit(self):
        # these need to be done every frame

        # convert surface to texture
        frame_tex = self.surf_to_texture(self.lit_surface, self.ctx)
        mask_tex = self.surf_to_texture(self.mask_surface, self.ctx)
        # use this texture
        frame_tex.use(0)
        mask_tex.use(1)
        # set uniform tex to using 0
        self.program["tex"] = 0
        self.program["mask"] = 1
        self.program["ignore_mask"] = False
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
        mask_tex.release()

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

    # called during draw outlined objects. draws X images with different
    def update_outline_render_pass(self, iterations, instace_count, surface: pg.Surface, transforms):

        o_frame_tex = self.surf_to_texture(surface.convert_alpha(), self.ctx)
        single_pass_outline_program = self.ctx.program(
            vertex_shader=self.outline_vert_shader, fragment_shader=self.outline_shader
        )
        o_frame_tex.use(2)
        single_pass_outline_program["tex"] = 2
        # single_pass_outline_program["time"] = self.TIME

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
                    1,
                    0.0,
                    -1.0,
                    -1.0,
                    0.0,
                    1,
                    1.0,
                    -1.0,
                    1,
                    1,
                ],
            )
        )
        transform_buffer = self.ctx.buffer(data=transforms)

        single_pass_render_object = self.ctx.vertex_array(
            single_pass_outline_program,
            [
                (quad_buffer, "2f 2f", "vert", "texcoord"),
                (transform_buffer, "2f 2f 1f /i", "offset", "scale", "outline_amount"),
            ],
        )
        single_pass_render_object.render(mode=moderngl.TRIANGLE_STRIP, instances=instace_count)

        o_frame_tex.release()

    # most complicated pass because each instance of an object needs to run the outline shader.
    def draw_outlined_objects(self):
        # use foreach to set vertext offset
        # self.outline_program["time"] = self.TIME

        # example of what to do when you want to draw an outlined object
        # gl_renderer.queue_outline_render_object(
        #    gl_renderer.create_outline_render_object(
        #    surf=Images.TEST_SHADER_0.load(),
        #    intensity=0.25,
        #    _z_index=2,
        #    offset=(0, 64),
        #    pixel_size=(64, 64),
        #    )
        # )

        # hahaha transform, like the werewolfs.
        transforms = array.array("f", [])

        prev_surface = self.mask_surface
        instances_of_texture = 0

        self.outline_render_list.sort(key=lambda x: x.z_index)
        for i in range(len(self.outline_render_list)):
            entry: OutlinedRenderObject = self.outline_render_list[i]
            surf = entry.surface
            if prev_surface == self.mask_surface:
                prev_surface = surf
            # only draw instances when there's a different surface
            if surf != prev_surface and instances_of_texture != 0:
                if prev_surface != self.mask_surface:
                    self.update_outline_render_pass(i, instances_of_texture, prev_surface, transforms)
                    transforms.clear()
                    instances_of_texture = 1
                    prev_surface = surf

            transforms.append(entry.offset[0])
            transforms.append(entry.offset[1])
            transforms.append(entry.scale[0])
            transforms.append(entry.scale[1])
            transforms.append(entry.highlight_intensity)
            instances_of_texture += 1
        # draw any remaining instances
        if instances_of_texture != 0:
            self.update_outline_render_pass(
                len(self.outline_render_list), instances_of_texture, prev_surface, transforms
            )
        self.outline_render_list.clear()

    # convert pixels into screen size units
    def pixel_to_screen_size(self, pixel_size: tuple):
        screen_size = constants.SCREEN_SIZE
        return [
            (pixel_size[0] / screen_size[0]) * self.RENDER_SCALE[0] / 2,
            (pixel_size[1] / screen_size[1]) * self.RENDER_SCALE[1] / 2,
        ]

    # converts pygame's pixel offset to the renderer's screen offset
    def pixel_to_screen_offset(self, pixel_position: tuple, screen_size: tuple):
        scaled = self.pixel_to_screen_size(pixel_position)
        scaled[1] *= -1
        return [scaled[0] + (screen_size[0]) - 1, scaled[1] - screen_size[1] + 1]

    # set the light position of the lit shader.
    def set_light_position(self, x: float, y: float):
        self.program["light_position"] = (x, y)

    # draw a surface to the the unlit surface
    def blit_to_unlit(self, surf: pg.Surface, rect: pg.Rect):
        self.unlit_surface.blit(surf, rect)

    # draw a surface to the lit surface
    def blit_to_lit(self, surf: pg.Surface, rect: pg.Rect):
        self.lit_surface.blit(surf, rect)

    def blit_to_light_mask(self, surf: pg.Surface, rect: pg.Rect):
        self.mask_surface.blit(surf, rect)

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
        self.set_light_size(0.6)
        self.set_intensity(0.2)
        self.set_light_position(0.5, 0.2)
        self.set_light_mode(self.LIGHT_MODE_POINT)
        self.set_pixel_per_sample(1)
        self.set_sample_count(128)
        self.set_ignore_distance(do_ignore=False)

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


# data class for an object to be drawn by the outline pass
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
