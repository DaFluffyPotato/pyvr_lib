import sys
import time
import math
import random
import noise

import pygame
from OpenGL import GL
import glm

from mgllib.xrwin import XRWindow
from mgllib.glfwwin import XRGLFWWin
from mgllib.mgl import MGL
from mgllib.elements import ElementSingleton
from mgllib.model.obj import OBJ
from mgllib.camera import Camera
from mgllib.player_body import PlayerBody
from mgllib.world.world import World, BLOCK_SCALE
from mgllib.world.decor import Decor
from mgllib.skybox import Skybox
from mgllib.vritem import Knife, M4, Magazine
from mgllib.model.polygon import Polygon, TETRAHEDRON
from mgllib.npc import NPC
from mgllib.sound import Sounds
from mgllib.entity import Entity
from mgllib.hud import HUD

class Demo(ElementSingleton):
    def __init__(self):
        super().__init__()

        self.window = XRWindow(self, (1920, 1080))

        self.pg_window = None

        self.start_time = time.time()

        pygame.init()

        self.font = pygame.font.Font('data/rubik_medium.ttf', size=28)

    def place_monument(self, pos):
        for y in range(5):
            self.world.add_block('chiseled_stone', (1 + pos[0], y + pos[1] - 1, 1 + pos[2]), rebuild=False)
            self.world.add_block('chiseled_stone', (-1 + pos[0], y + pos[1] - 1, 1 + pos[2]), rebuild=False)
            self.world.add_block('chiseled_stone', (-1 + pos[0], y + pos[1] - 1, -1 + pos[2]), rebuild=False)
            self.world.add_block('chiseled_stone', (1 + pos[0], y + pos[1] - 1, -1 + pos[2]), rebuild=False)
            
            t = 'log'
            if y == 4:
                t = 'chiseled_stone'
                self.world.add_block('chiseled_stone', (1 + pos[0], y + pos[1] - 1, 0 + pos[2]), rebuild=False)
                self.world.add_block('chiseled_stone', (0 + pos[0], y + pos[1] - 1, 1 + pos[2]), rebuild=False)
                self.world.add_block('chiseled_stone', (-1 + pos[0], y + pos[1] - 1, 0 + pos[2]), rebuild=False)
                self.world.add_block('chiseled_stone', (0 + pos[0], y + pos[1] - 1, -1 + pos[2]), rebuild=False)
            self.world.add_block(t, (2 + pos[0], y + pos[1] - 1, 2 + pos[2]), rebuild=False)
            self.world.add_block(t, (-2 + pos[0], y + pos[1] - 1, 2 + pos[2]), rebuild=False)
            self.world.add_block(t, (-2 + pos[0], y + pos[1] - 1, -2 + pos[2]), rebuild=False)
            self.world.add_block(t, (2 + pos[0], y + pos[1] - 1, -2 + pos[2]), rebuild=False)

    def init_mgl(self):
        self.mgl = MGL()

        self.sounds = Sounds('data/sfx')

        self.main_shader = self.mgl.program('data/shaders/default.vert', 'data/shaders/default.frag')
        self.decor_shader = self.mgl.program('data/shaders/decor.vert', 'data/shaders/default.frag')
        self.grass_shader = self.mgl.program('data/shaders/grass.vert', 'data/shaders/default.frag')
        self.tree_shader = self.mgl.program('data/shaders/tree.vert', 'data/shaders/default.frag')
        self.npc_shader = self.mgl.program('data/shaders/npc.vert', 'data/shaders/npc.frag')
        self.tracer_shader = self.mgl.program('data/shaders/default.vert', 'data/shaders/tracer.frag')
        self.no_norm_shader = self.mgl.program('data/shaders/no_norm.vert', 'data/shaders/no_norm.frag')

        self.hand_obj = OBJ('data/models/hand/hand.obj', self.main_shader, centered=True)

        self.watch_obj = OBJ('data/models/watch/watch.obj', self.main_shader)

        self.helmet_res = OBJ('data/models/helmet/helmet.obj', self.main_shader)
        self.head_res = OBJ('data/models/head/head.obj', self.npc_shader)
        self.body_res = OBJ('data/models/body/body.obj', self.npc_shader)

        self.world = World(self.main_shader)

        self.hud = HUD()

        self.skybox = Skybox('data/textures/skybox', self.mgl.program('data/shaders/skybox.vert', 'data/shaders/skybox.frag'))

        self.knife_res = OBJ('data/models/knife/knife.obj', self.main_shader, centered=False)
        self.m4_res = OBJ('data/models/m4/m4.obj', self.main_shader, centered=False)
        self.m4_mag_res = OBJ('data/models/m4/mag.obj', self.main_shader, centered=False)
        self.m4_rack_res = OBJ('data/models/m4/rack.obj', self.main_shader, centered=False)

        self.casing_res = OBJ('data/models/casing/casing.obj', self.main_shader, centered=False)

        self.tracer_res = OBJ('data/models/tracer/tracer.obj', self.tracer_shader, centered=False, simple=True)

        self.spark_res = Polygon(TETRAHEDRON, self.mgl.program('data/shaders/polygon.vert', 'data/shaders/polygon.frag'))

        self.grass_res = OBJ('data/models/grass/grass.obj', self.grass_shader, centered=False, save_geometry=True, no_build=True)
        self.tree_res = OBJ('data/models/tree/tree.obj', self.tree_shader, centered=False, save_geometry=True, no_build=True)
        
        self.items = [M4(self.m4_res, (0, 1, i - 5)) for i in range(10)]
        for i in range(3):
            self.items.append(Knife(self.knife_res, (7, 1, i - 1)))

        self.npcs = []

        self.tracers = []
        self.particles = []

        monuments = []
        for x in range(128):
            for z in range(128):
                height = int((noise.pnoise2(x * 0.08, z * 0.08, octaves=2) * 0.5 + 0.5) * 5 + 1)
                for y in range(height):
                    t = 'dirt'
                    if y == height - 1:
                        t = 'grass'
                        if (abs(x) + abs(z)) > 8:
                            if random.random() < 0.003:
                                monuments.append((x - 64, y - 5, z - 64))
                    self.world.add_block(t, (x - 64, y - 6, z - 64), rebuild=False)

        for monument in monuments:
            self.place_monument(monument)

        for chunk in self.world.chunks.values():
            for block in chunk.blocks.values():
                block_pos = block.world_pos
                if (block.block_id == 'grass') and (not self.world.get_block((block_pos[0], block_pos[1] + 1, block_pos[2]))):
                    # open grass block

                    height = noise.pnoise2(x * 0.08, z * 0.08, octaves=2) * 0.5 + 0.5

                    if random.random() > height:
                        if random.random() < 0.5:
                            p = block.scaled_world_pos
                            self.world.add_decor(Decor(self.grass_res, (p[0] + BLOCK_SCALE * 0.5, p[1] + BLOCK_SCALE, p[2] + BLOCK_SCALE * 0.5)))
                    
                    if random.random() < height:
                        if random.random() < 0.03:
                            p = block.scaled_world_pos
                            self.world.add_decor(Decor(self.tree_res, (p[0] + BLOCK_SCALE * 0.5, p[1] + BLOCK_SCALE, p[2] + BLOCK_SCALE * 0.5), rot=glm.rotate(random.random() * math.pi * 2, (0, 1, 0))))

        self.world.rebuild()
        self.world.rebuild_decor()
        self.world.gen_navmesh((0, 0, 0))

        self.hand_entity = self.hand_obj.new_entity()
        self.hand_entity.transform.scale = [0.045, 0.045, 0.045]

        self.e['XRCamera'].light_pos = [0.5, 1, 1]

        self.player = PlayerBody()

        self.score = 0
    
    @property
    def watch_text(self):
        return str(self.score)

    def run(self):
        self.window.run()

    def single_update(self):
        self.hud.update()
        self.player.cycle()
        for item in list(self.items):
            for hand in self.player.hands:
                item.handle_interactions(hand)
            kill = item.update()
            if kill:
                self.items.remove(item)

        for tracer in list(self.tracers):
            kill = tracer.update()
            if kill:
                self.tracers.remove(tracer)

        for particle in list(self.particles):
            kill = particle.update()
            if kill:
                self.particles.remove(particle)

        for npc in list(self.npcs):
            kill = npc.update()
            if kill:
                self.npcs.remove(npc)

        while len(self.npcs) < 5:
            spawn_pos = (random.randint(-40, 40), 10, random.randint(-40, 40))
            player_dis = glm.length(glm.vec3(self.player.world_pos.pos).xz - glm.vec3(spawn_pos).xz)
            if player_dis > 15:
                self.npcs.append(NPC(spawn_pos))
        
        self.player.late_cycle()

    def update(self, view_index):
        if view_index == 0:
            self.single_update()

        self.e['XRCamera'].cycle()

        self.skybox.render(self.e['XRCamera'])

        for item in self.items:
            item.render(self.e['XRCamera'])

        for tracer in self.tracers:
            tracer.render(self.e['XRCamera'])
        
        for particle in self.particles:
            particle.render(self.e['XRCamera'])

        for npc in self.npcs:
            npc.render(self.e['XRCamera'])

        for i, hand in enumerate(self.player.hands):
            self.hand_entity.transform.quaternion = glm.quat(hand.aim_rot[3], *(hand.aim_rot[:3])) * glm.quat(glm.rotate(math.pi / 2, glm.vec3(0, 1, 0)))
            if hand.interacting and hand.interacting.hand_override:
                self.hand_entity.transform.pos = hand.interacting.hand_override
            elif hand.interacting and (hand.interacting.parent.alt_grip == hand.interacting):
                self.hand_entity.transform.pos = hand.interacting.world_pos
            else:    
                self.hand_entity.transform.pos = list(hand.pos)
            self.hand_entity.render(self.e['XRCamera'])

        self.player.render(self.e['XRCamera'])

        self.world.render(self.e['XRCamera'], decor_uniforms={'time': time.time() - self.start_time})

        self.hud.render()

Demo().run()
