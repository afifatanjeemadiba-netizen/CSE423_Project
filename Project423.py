from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
import math
import random
import time

WINDOW_WIDTH = 1000
WINDOW_HEIGHT = 700
MOVE_SPEED = 0.015
CAMERA_TURN_SPEED = 2.5
JUMP_SPEED = 0.18
GRAVITY = -0.015
MAX_FALL_SPEED = -0.5
FRICTION = 0.85
AIR_FRICTION = 0.92
PLAYER_HEIGHT = 1.8
PLAYER_WIDTH = 0.6
PLAYER_HEIGHT_09 = PLAYER_HEIGHT * 0.9
PLAYER_WIDTH_HALF = PLAYER_WIDTH / 2.0

# UTILITY CLASSES

class Vector3:
    def __init__(self, x=0, y=0, z=0):
        self.x, self.y, self.z = x, y, z
    def __add__(self, other):
        return Vector3(self.x + other.x, self.y + other.y, self.z + other.z)
    def __sub__(self, other):
        return Vector3(self.x - other.x, self.y - other.y, self.z - other.z)
    def __mul__(self, scalar):
        return Vector3(self.x * scalar, self.y * scalar, self.z * scalar)
    def length(self):
        return math.sqrt(self.x**2 + self.y**2 + self.z**2)
    def normalize(self):
        length = self.length()
        if length > 0:
            return Vector3(self.x/length, self.y/length, self.z/length)
        return Vector3(0, 0, 0)
    def dot(self, other):
        return self.x * other.x + self.y * other.y + self.z * other.z
class GameObject:
    def __init__(self, position=Vector3(), size=1.0):
        self.position = position
        self.size = size
        self.active = True

        #Get bounding box for collision detection

    def get_bounds(self):
        return {
            'min_x': self.position.x - self.size/2,
            'max_x': self.position.x + self.size/2,
            'min_z': self.position.z - self.size/2,
            'max_z': self.position.z + self.size/2
        }
    
class EnhancedBullet(GameObject):
    def __init__(self, position, direction, speed=0.5, is_player_bullet=True):
        super().__init__(position, 0.15)
        self.direction = direction.normalize()
        self.speed = speed
        self.lifetime = 700
        self.is_player_bullet = is_player_bullet
        self.trail_positions = [Vector3(position.x, position.y, position.z) for _ in range(6)]
        self.arena = None

    """Update enemy behavior based on type"""

    def update(self):
        if not self.active:
            return
        prev_pos = Vector3(self.position.x, self.position.y, self.position.z)
        new_pos = self.position + self.direction * self.speed
        if abs(new_pos.x) > 9.8 or abs(new_pos.z) > 9.8:
            self.active = False
            return
        if self.arena:
            steps = max(int(self.speed * 10), 1)
            for step in range(1, steps + 1):
                t = step / steps
                check_x = prev_pos.x + (new_pos.x - prev_pos.x) * t
                check_z = prev_pos.z + (new_pos.z - prev_pos.z) * t
                tile_type = self.arena.get_tile_at(check_x, check_z)
                if tile_type == 1:
                    self.active = False
                    return
        self.position = new_pos
        self.trail_positions.pop()
        self.trail_positions.insert(0, Vector3(self.position.x, self.position.y, self.position.z))
        self.lifetime -= 1
        if self.lifetime <= 0:
            self.active = False
    def draw(self):
        if not self.active:
            return
        for i in range(1, len(self.trail_positions)):
            alpha = 1.0 - (i / len(self.trail_positions))
            if self.is_player_bullet:
                glColor3f(0.0 * alpha, 1.0 * alpha, 1.0 * alpha)
            else:
                glColor3f(1.0 * alpha, 0.2 * alpha, 0.0 * alpha)
            glPushMatrix()
            pos = self.trail_positions[i]
            glTranslatef(pos.x, pos.y, pos.z)
            glutSolidSphere(self.size * (1.0 - i * 0.12), 8, 8)
            glPopMatrix()
        glPushMatrix()
        glTranslatef(self.position.x, self.position.y, self.position.z)
        if self.is_player_bullet:
            glColor3f(0.0, 0.8, 1.0)
        else:
            glColor3f(1.0, 0.0, 0.0)
        glutSolidSphere(self.size, 10, 10)
        glPopMatrix()
class Enemy(GameObject):
    def __init__(self, position, enemy_type="hunter"):
        super().__init__(position, 0.9)
        self.enemy_type = enemy_type
        self.health = 6 if enemy_type == "boss" else 2
        self.max_health = self.health
        self.last_shot = 0
        self.shoot_cooldown = 150
        self.rotation_y = 0
        self.alert_level = 0
        self.move_timer = 0
    def update(self, player_pos, arena):
        if not self.active:
            return
        distance_to_player = (player_pos - self.position).length()

        # FEATURE enemy behavior based on type

        if self.enemy_type == "hunter":
            if distance_to_player > 1.8:
                direction = (player_pos - self.position).normalize()
                base_speed = 0.004

                #alert level increase when player is close

                if distance_to_player < 10:
                    self.alert_level = min(120, self.alert_level + 2)
                    base_speed *= (1 + self.alert_level * 0.008)
                new_pos = self.position + direction * base_speed
                if not self.check_collision(new_pos, arena):
                    self.position = new_pos
                    self.rotation_y = math.degrees(math.atan2(direction.x, direction.z))
        elif self.enemy_type == "sniper":
            self.last_shot += 1
            direction = (player_pos - self.position).normalize()
            self.rotation_y = math.degrees(math.atan2(direction.x, direction.z))

            # Maintain distance from player

            if distance_to_player < 5:
                retreat_dir = (self.position - player_pos).normalize()
                new_pos = self.position + retreat_dir * 0.002
                if not self.check_collision(new_pos, arena):
                    self.position = new_pos

            # Move slightly sideways to avoid being a static target

            elif distance_to_player > 12:
                approach_dir = (player_pos - self.position).normalize()
                new_pos = self.position + approach_dir * 0.003
                if not self.check_collision(new_pos, arena):
                    self.position = new_pos

        # Boss moves slowly and shoots frequently

        elif self.enemy_type == "boss":
            direction = (player_pos - self.position).normalize()# Move towards towards player slowly
            self.rotation_y = math.degrees(math.atan2(direction.x, direction.z)) # Face player
            self.move_timer += 1 # Increment move timer
            if self.move_timer % 120 == 0:
                if distance_to_player > 4.0:
                    new_pos = self.position + direction * 0.003
                    if not self.check_collision(new_pos, arena):
                        self.position = new_pos
            self.last_shot += 1

    def check_collision(self, new_pos, arena):
        if abs(new_pos.x) > 9.2 or abs(new_pos.z) > 9.2:
            return True
        size_half = self.size / 2
        check_points = [
            (new_pos.x - size_half, new_pos.z - size_half),
            (new_pos.x - size_half, new_pos.z + size_half),
            (new_pos.x + size_half, new_pos.z - size_half),
            (new_pos.x + size_half, new_pos.z + size_half),
            (new_pos.x, new_pos.z)
        ]
        for px, pz in check_points:
            tile_type = arena.get_tile_at(px, pz)
            if tile_type == 1:
                return True
        return False
    def can_shoot(self):
        return self.last_shot >= self.shoot_cooldown
    def shoot(self, player_pos):
        # Shoot towards player with some inaccuracy based on type
        if self.can_shoot():
            self.last_shot = 0
            direction = (player_pos - self.position).normalize()
            spread = 0.08 if self.enemy_type == "sniper" else 0.15
            direction.x += (random.random() - 0.5) * spread
            direction.z += (random.random() - 0.5) * spread
            direction = direction.normalize()
            speed = 0.12 if self.enemy_type == "boss" else 0.08
            return EnhancedBullet(self.position + Vector3(0, 0.3, 0), direction, speed, False)
        return None
    def take_damage(self):
        self.health -= 1
        if self.health <= 0:
            self.active = False
    def draw_cylinder_manually(self, radius, height, slices):
        # Draw a cylinder 
        glBegin(GL_TRIANGLES)
        for i in range(slices):
            angle1 = 2.0 * math.pi * i / slices
            angle2 = 2.0 * math.pi * (i + 1) / slices
            x1 = radius * math.cos(angle1)
            z1 = radius * math.sin(angle1)
            x2 = radius * math.cos(angle2)
            z2 = radius * math.sin(angle2)
            glVertex3f(0, height/2, 0)
            glVertex3f(x1, height/2, z1)
            glVertex3f(x2, height/2, z2)
            glVertex3f(0, -height/2, 0)
            glVertex3f(x2, -height/2, z2)
            glVertex3f(x1, -height/2, z1)
        glEnd()
        glBegin(GL_QUADS)
        for i in range(slices):
            angle1 = 2.0 * math.pi * i / slices
            angle2 = 2.0 * math.pi * (i + 1) / slices
            x1 = radius * math.cos(angle1)
            z1 = radius * math.sin(angle1)
            x2 = radius * math.cos(angle2)
            z2 = radius * math.sin(angle2)
            glVertex3f(x1, -height/2, z1)
            glVertex3f(x2, -height/2, z2)
            glVertex3f(x2, height/2, z2)
            glVertex3f(x1, height/2, z1)
        glEnd()
    def draw(self):
        if not self.active:
            return
        glPushMatrix()
        glTranslatef(self.position.x, self.position.y, self.position.z)
        glRotatef(self.rotation_y, 0, 1, 0)
        if self.enemy_type == "hunter":# Hunter glows more intensely as alert level rises
            alert_factor = min(1.0, self.alert_level / 60.0)
            glColor3f(1.0, 1.0 - alert_factor * 0.7, 1.0 - alert_factor)
            glutSolidSphere(self.size/2, 20, 20)
        elif self.enemy_type == "sniper":# Sniper has a cube body with a cylinder neck
            glColor3f(0.9, 0.1, 0.9)
            glutSolidCube(self.size)
            glColor3f(0.2, 0.2, 0.2)
            glTranslatef(0, 0, self.size/2)
            glRotatef(90, 1, 0, 0)
            self.draw_cylinder_manually(0.12, 1.0, 10)
        elif self.enemy_type == "boss":# Boss pulses in size
            pulse = 1.0 + 0.2 * math.sin(time.time() * 2.0)
            glColor3f(0.7, 0.0, 0.7)
            glutSolidSphere(self.size * pulse, 25, 25)
            self.draw_health_bar()
        glPopMatrix()
    def draw_health_bar(self):
        glPushMatrix()  
        glLoadIdentity()
        glTranslatef(self.position.x, self.position.y + self.size + 1.5, self.position.z)
        health_ratio = self.health / self.max_health
        glColor3f(0.1, 0.1, 0.1)
        glBegin(GL_QUADS)
        glVertex3f(-1.2, 0, 0)
        glVertex3f(1.2, 0, 0)
        glVertex3f(1.2, 0.3, 0)
        glVertex3f(-1.2, 0.3, 0)
        glEnd()
        if health_ratio > 0.6:  # Health bar color changes
            glColor3f(0.2, 0.9, 0.2)
        elif health_ratio > 0.3:
            glColor3f(0.9, 0.9, 0.2)
        else:
            glColor3f(0.9, 0.2, 0.2)
        glBegin(GL_QUADS)
        glVertex3f(-1.2, 0, 0)
        glVertex3f(-1.2 + 2.4*health_ratio, 0, 0)
        glVertex3f(-1.2 + 2.4*health_ratio, 0.3, 0)
        glVertex3f(-1.2, 0.3, 0)
        glEnd()
        glPopMatrix()
class Collectible(GameObject):# Crystals and Power Cores
    def __init__(self, position, item_type="crystal"):
        super().__init__(position, 0.4)
        self.item_type = item_type
        self.rotation = 0
        self.bob_time = 0
        self.glow_time = 0
    def update(self):# Rotate and bob up/down
        self.rotation += 2.5
        self.bob_time += 0.12
        self.glow_time += 0.08
    def draw_octahedron_manually(self):
        glBegin(GL_TRIANGLES)
        glVertex3f(0, 1, 0); glVertex3f(-1, 0, 1); glVertex3f(1, 0, 1)
        glVertex3f(0, 1, 0); glVertex3f(1, 0, 1); glVertex3f(1, 0, -1)
        glVertex3f(0, 1, 0); glVertex3f(1, 0, -1); glVertex3f(-1, 0, -1)
        glVertex3f(0, 1, 0); glVertex3f(-1, 0, -1); glVertex3f(-1, 0, 1)
        glVertex3f(0, -1, 0); glVertex3f(1, 0, 1); glVertex3f(-1, 0, 1)
        glVertex3f(0, -1, 0); glVertex3f(1, 0, -1); glVertex3f(1, 0, 1)
        glVertex3f(0, -1, 0); glVertex3f(-1, 0, -1); glVertex3f(1, 0, -1)
        glVertex3f(0, -1, 0); glVertex3f(-1, 0, 1); glVertex3f(-1, 0, -1)
        glEnd()
    def draw(self):# Draw with glow and bobbing effect
        if not self.active:
            return
        glPushMatrix()
        bob_height = math.sin(self.bob_time) * 0.25
        glow_intensity = 0.8 + 0.2 * math.sin(self.glow_time * 2)# Glow pulsates
        glTranslatef(self.position.x, self.position.y + 0.6 + bob_height, self.position.z)
        glRotatef(self.rotation, 0, 1, 0)
        glRotatef(self.rotation * 0.5, 1, 0, 0)
        if self.item_type == "crystal":
            glColor3f(0.2 * glow_intensity, 1.0 * glow_intensity, 1.0 * glow_intensity)
        elif self.item_type == "power_core":
            glColor3f(1.0 * glow_intensity, 0.8 * glow_intensity, 0.2 * glow_intensity)
        glScalef(self.size, self.size, self.size)
        self.draw_octahedron_manually()
        glColor3f(0.5 * glow_intensity, 1.0 * glow_intensity, 1.0 * glow_intensity)
        glScalef(1.3, 1.3, 1.3)
        self.draw_octahedron_manually()
        glPopMatrix()
class PowerUp(GameObject):# Speed Boost, Shield, Rapid Fire
    def __init__(self, position, power_type):
        super().__init__(position, 0.5)
        self.power_type = power_type
        self.rotation = 0
        self.bob_time = 0
        self.pulse_time = 0
    def update(self):
        self.rotation += 1.8
        self.bob_time += 0.1
        self.pulse_time += 0.15
    def draw_torus_manually(self, inner_radius, outer_radius, sides, rings):
        for i in range(rings):
            glBegin(GL_QUADS)
            for j in range(sides):
                for k in range(2):
                    s = (i + k) % rings
                    t = j
                    angle1 = s * 2.0 * math.pi / rings
                    angle2 = t * 2.0 * math.pi / sides
                    cos1, sin1 = math.cos(angle1), math.sin(angle1)
                    cos2, sin2 = math.cos(angle2), math.sin(angle2)
                    r = outer_radius + inner_radius * cos2
                    x = cos1 * r
                    y = sin1 * r
                    z = inner_radius * sin2
                    t_next = (j + 1) % sides
                    angle2_next = t_next * 2.0 * math.pi / sides
                    cos2_next, sin2_next = math.cos(angle2_next), math.sin(angle2_next)
                    r_next = outer_radius + inner_radius * cos2_next
                    x_next = cos1 * r_next
                    y_next = sin1 * r_next
                    z_next = inner_radius * sin2_next
                    if k == 0:
                        glVertex3f(x, y, z)
                        glVertex3f(x_next, y_next, z_next)
                    else:
                        s_next = (i + 1) % rings
                        angle1_next = s_next * 2.0 * math.pi / rings
                        cos1_next, sin1_next = math.cos(angle1_next), math.sin(angle1_next)
                        r_next2 = outer_radius + inner_radius * cos2_next
                        x_next2 = cos1_next * r_next2
                        y_next2 = sin1_next * r_next2
                        z_next2 = inner_radius * sin2_next
                        r2 = outer_radius + inner_radius * cos2
                        x2 = cos1_next * r2
                        y2 = sin1_next * r2
                        z2 = inner_radius * sin2
                        glVertex3f(x_next2, y_next2, z_next2)
                        glVertex3f(x2, y2, z2)
            glEnd()
    def draw(self):# Draw with rotation, bobbing, and pulsing
        if not self.active:
            return
        glPushMatrix()
        bob_height = math.sin(self.bob_time) * 0.2
        pulse = 1.0 + 0.15 * math.sin(self.pulse_time * 3)
        glTranslatef(self.position.x, self.position.y + 0.4 + bob_height, self.position.z)
        glRotatef(self.rotation, 1, 1, 0)
        if self.power_type == "speed":
            glColor3f(0.0, 1.0 * pulse, 0.2)
        elif self.power_type == "shield":
            glColor3f(0.0, 0.6 * pulse, 1.0)
        elif self.power_type == "rapid_fire":
            glColor3f(1.0 * pulse, 0.6, 0.0)
        self.draw_torus_manually(self.size * 0.3, self.size * 0.7, 8, 16)
        if self.power_type == "speed":
            glColor3f(0.0 * pulse, 1.0 * pulse, 0.2 * pulse)
        elif self.power_type == "shield":
            glColor3f(0.0 * pulse, 0.6 * pulse, 1.0 * pulse)
        elif self.power_type == "rapid_fire":
            glColor3f(1.0 * pulse, 0.6 * pulse, 0.0 * pulse)
        self.draw_torus_manually(self.size * 0.4, self.size * 0.8, 8, 16)
        glPopMatrix()
class EnhancedPlayer(GameObject):
    def __init__(self, game_ref):
        super().__init__(Vector3(0, 1.0, 0), 0.7)
        self.game = game_ref
        self.velocity = Vector3()
        self.health = 100
        self.max_health = 100
        self.energy = 100
        self.max_energy = 100
        self.rotation_y = 0
        self.acceleration = Vector3()
        self.max_speed = 0.15
        self.ground_friction = FRICTION
        self.air_friction = AIR_FRICTION
        self.on_ground = True
        self.jump_velocity = 0
        self.speed_boost = 0
        self.shield_time = 0
        self.rapid_fire_time = 0
        self.damage_cooldown = 0
        self.shots_fired = 0
        self.last_shot_time = 0
        self.shoot_cooldown = 0
        self.bbox_offsets = {
            'min_x': -PLAYER_WIDTH_HALF,
            'max_x': PLAYER_WIDTH_HALF,
            'min_y': 0,
            'max_y': PLAYER_HEIGHT,
            'min_z': -PLAYER_WIDTH_HALF,
            'max_z': PLAYER_WIDTH_HALF
        }
    def get_bounding_box(self):# Get world-space bounding box for collision detection
        return {
            'min_x': self.position.x + self.bbox_offsets['min_x'],
            'max_x': self.position.x + self.bbox_offsets['max_x'],
            'min_y': self.position.y + self.bbox_offsets['min_y'],
            'max_y': self.position.y + self.bbox_offsets['max_y'],
            'min_z': self.position.z + self.bbox_offsets['min_z'],
            'max_z': self.position.z + self.bbox_offsets['max_z']
        }
    def check_collision(self, new_pos, arena):# Check collision at new position
        if abs(new_pos.x) > 9.3 or abs(new_pos.z) > 9.3:
            return True
        bbox = self.bbox_offsets
        
        check_points = [
            (new_pos.x + bbox['min_x'], new_pos.z + bbox['min_z']),
            (new_pos.x + bbox['min_x'], new_pos.z + bbox['max_z']),
            (new_pos.x + bbox['max_x'], new_pos.z + bbox['min_z']),
            (new_pos.x + bbox['max_x'], new_pos.z + bbox['max_z']),
            (new_pos.x, new_pos.z)
        ]
        # Check tiles at bounding box corners and center
        for px, pz in check_points:
            tile_type = arena.get_tile_at(px, pz)
            if tile_type == 1:
                return True
        return False
    def reset(self):# Reset player state
        self.position = Vector3(0, 1.0, 0)
        self.velocity = Vector3()
        self.acceleration = Vector3()
        self.health = 100
        self.energy = 100
        self.rotation_y = 0
        self.speed_boost = 0
        self.shield_time = 0
        self.rapid_fire_time = 0
        self.jump_velocity = 0
        self.on_ground = True
        self.damage_cooldown = 0
        self.shots_fired = 0
        self.shoot_cooldown = 0
    def update(self, arena):# Update player physics and state
        if not self.on_ground:
            self.jump_velocity += GRAVITY
            if self.jump_velocity < MAX_FALL_SPEED:
                self.jump_velocity = MAX_FALL_SPEED
            self.position.y += self.jump_velocity
            if self.position.y <= 1.0:
                self.position.y = 1.0
                self.jump_velocity = 0
                self.on_ground = True
        friction = self.ground_friction if self.on_ground else self.air_friction
        self.velocity.x *= friction
        self.velocity.z *= friction
        self.velocity = self.velocity + self.acceleration
        self.acceleration = Vector3()
        horizontal_speed = math.sqrt(self.velocity.x**2 + self.velocity.z**2)
        current_max_speed = self.max_speed
        if self.speed_boost > 0:
            current_max_speed *= 1.8
        if horizontal_speed > current_max_speed:
            scale = current_max_speed / horizontal_speed
            self.velocity.x *= scale
            self.velocity.z *= scale
        new_pos = self.position + self.velocity
        if abs(new_pos.x) > 9.3:
            new_pos.x = 9.3 if new_pos.x > 0 else -9.3
            self.velocity.x = 0
        if abs(new_pos.z) > 9.3:
            new_pos.z = 9.3 if new_pos.z > 0 else -9.3
            self.velocity.z = 0
        if not self.check_collision(new_pos, arena):
            self.position = new_pos
        else:
            slide_x = Vector3(new_pos.x, self.position.y, self.position.z)
            slide_z = Vector3(self.position.x, self.position.y, new_pos.z)
            if not self.check_collision(slide_x, arena):
                self.position.x = new_pos.x
                self.velocity.z = 0
            elif not self.check_collision(slide_z, arena):
                self.position.z = new_pos.z
                self.velocity.x = 0
            else:
                self.velocity.x = 0
                self.velocity.z = 0
        if self.speed_boost > 0: self.speed_boost -= 1
        if self.shield_time > 0: self.shield_time -= 1
        if self.rapid_fire_time > 0: self.rapid_fire_time -= 1
        if self.damage_cooldown > 0: self.damage_cooldown -= 1
        if self.shoot_cooldown > 0: self.shoot_cooldown -= 1
        tile_type = arena.get_tile_at(self.position.x, self.position.z)
        if tile_type == 2 and self.damage_cooldown <= 0:
            self.take_damage(4)
            self.damage_cooldown = 80
        if self.energy < self.max_energy:
            self.energy += 0.3
    def move_camera_relative(self, input_dir):# Move based on camera orientation
        base_speed = MOVE_SPEED
        if self.speed_boost > 0:
            base_speed *= 1.8
        camera_yaw = math.radians(self.game.camera_angle_y)
        forward = Vector3(math.sin(camera_yaw), 0, math.cos(camera_yaw))
        right = Vector3(math.cos(camera_yaw), 0, -math.sin(camera_yaw))
        move_vector = forward * input_dir.z + right * input_dir.x
        if move_vector.length() > 0:
            move_vector = move_vector.normalize()
            self.acceleration = self.acceleration + move_vector * base_speed
            if move_vector.length() > 0.1:
                self.rotation_y = math.degrees(math.atan2(move_vector.x, move_vector.z))
    def jump(self):# Jump if on ground and enough energy
        if self.on_ground and self.energy >= 15:
            self.jump_velocity = JUMP_SPEED
            self.on_ground = False
            self.energy -= 15
    def take_damage(self, damage=8):# Take damage if not shielded
        if self.shield_time <= 0:
            self.health -= damage
            if self.health < 0:
                self.health = 0
    def use_power_up(self, power_type):# Activate power-up if enough energy
        if self.energy >= 25:
            self.energy -= 25
            if power_type == "speed":
                self.speed_boost = 500
            elif power_type == "shield":
                self.shield_time = 800
            elif power_type == "rapid_fire":
                self.rapid_fire_time = 300
    def get_aim_direction(self):# Get shooting direction based on camera or player orientation
        if self.game.camera_mode == 0:# First-person mode
            cos_y = math.cos(math.radians(self.game.camera_angle_y))
            sin_y = math.sin(math.radians(self.game.camera_angle_y))
            cos_x = math.cos(math.radians(self.game.camera_angle_x))
            sin_x = math.sin(math.radians(self.game.camera_angle_x))
            return Vector3(-sin_y * cos_x, -sin_x, -cos_y * cos_x)
        else:# upper view mode
            cos_y = math.cos(math.radians(self.rotation_y))
            sin_y = math.sin(math.radians(self.rotation_y))
            return Vector3(sin_y, 0, cos_y)
    def shoot(self):# Shoot bullet with spread and cooldown
        cooldown_time = 4 if self.rapid_fire_time > 0 else 10
        if self.shoot_cooldown > 0:
            return []
        current_time = time.time()
        if current_time - self.last_shot_time > 1.2:
            self.shots_fired = 0
        bullets = []
        spread = 0.02
        base_direction = self.get_aim_direction()
        spread_x = (random.random() - 0.5) * spread
        spread_y = (random.random() - 0.5) * spread * 0.6
        spread_z = (random.random() - 0.5) * spread
        final_direction = Vector3(
            base_direction.x + spread_x,
            base_direction.y + spread_y,
            base_direction.z + spread_z
        ).normalize()
        gun_barrel_offset = base_direction * 0.8
        start_position = self.position + Vector3(0, 0.4, 0) + gun_barrel_offset
        bullet = EnhancedBullet(start_position, final_direction, 0.5, True)
        self.shots_fired += 1
        self.last_shot_time = current_time
        self.shoot_cooldown = cooldown_time
        return bullets
    def draw_cylinder_manually(self, radius, height, slices):# Draw a cylinder
        glBegin(GL_TRIANGLES)
        for i in range(slices):
            angle1 = 2.0 * math.pi * i / slices
            angle2 = 2.0 * math.pi * (i + 1) / slices
            x1 = radius * math.cos(angle1)
            z1 = radius * math.sin(angle1)
            x2 = radius * math.cos(angle2)
            z2 = radius * math.sin(angle2)
            glVertex3f(0, height/2, 0)
            glVertex3f(x1, height/2, z1)
            glVertex3f(x2, height/2, z2)
            glVertex3f(0, -height/2, 0)
            glVertex3f(x2, -height/2, z2)
            glVertex3f(x1, -height/2, z1)
        glEnd()
        glBegin(GL_QUADS)
        for i in range(slices):# Draw side quads
            angle1 = 2.0 * math.pi * i / slices
            angle2 = 2.0 * math.pi * (i + 1) / slices
            x1 = radius * math.cos(angle1)
            z1 = radius * math.sin(angle1)
            x2 = radius * math.cos(angle2)
            z2 = radius * math.sin(angle2)
            glVertex3f(x1, -height/2, z1)
            glVertex3f(x2, -height/2, z2)
            glVertex3f(x2, height/2, z2)
            glVertex3f(x1, height/2, z1)
        glEnd()
    def draw(self):# Draw player with effects based on state
        glPushMatrix()
        glTranslatef(self.position.x, self.position.y, self.position.z)
        glRotatef(self.rotation_y, 0, 1, 0)
        if self.shield_time > 0:
            pulse = 1.0 + 0.3 * math.sin(time.time() * 5)
            glColor3f(0.0, 0.4 * pulse, 1.0 * pulse)
            glutSolidSphere(self.size * pulse, 20, 20)
        if self.damage_cooldown > 0:
            flash = 1.0 - (self.damage_cooldown / 80.0)
            glColor3f(1.0, flash, flash)
        else:
            if self.speed_boost > 0:
                glow = 0.8 + 0.2 * math.sin(time.time() * 8)
                glColor3f(0.2, 1.0 * glow, 0.2)
            else:
                glColor3f(0.0, 0.9, 0.0)
        glutSolidCube(self.size * 0.7)
        glColor3f(0.0, 0.9, 0.0)
        glTranslatef(0, self.size * 0.4, 0)
        glutSolidSphere(self.size * 0.3, 15, 15)
        glTranslatef(0, -self.size * 0.5, self.size * 0.4)
        glRotatef(90, 1, 0, 0)
        glColor3f(0.2, 0.2, 0.2)
        self.draw_cylinder_manually(self.size * 0.1, self.size * 0.6, 12)
        glPopMatrix()
class Arena:
    def __init__(self):
        self.size = 22
        self.tile_states = []
        self.tile_heights = []
        self.init_tiles()
    def init_tiles(self):
        self.tile_states = []
        self.tile_heights = []
        for x in range(-self.size//2, self.size//2):
            row_states = []
            row_heights = []
            for z in range(-self.size//2, self.size//2):
                state = 0
                height = 0
                if abs(x) < 4 and abs(z) < 4:
                    state = 0
                else:
                    rand = random.random()
                    if rand < 0.15:
                        state = 1
                        height = random.uniform(1.5, 3.0)
                    elif rand < 0.20:
                        state = 2
                row_states.append(state)
                row_heights.append(height)
            self.tile_states.append(row_states)
            self.tile_heights.append(row_heights)
    def update(self):# Animate tile heights for elevated tiles
        for x in range(len(self.tile_states)):
            for z in range(len(self.tile_states[0])):
                if self.tile_states[x][z] == 1:
                    base_height = 1.5 + (x + z) % 3 * 0.5
                    self.tile_heights[x][z] = base_height + math.sin(time.time() * 0.8 + x + z) * 0.15
    def get_tile_at(self, world_x, world_z):# Get tile type at world coordinates
        tile_x = int(world_x + self.size//2)
        tile_z = int(world_z + self.size//2)
        if 0 <= tile_x < self.size and 0 <= tile_z < self.size:
            return self.tile_states[tile_x][tile_z]
        return 0
    def get_tile_height(self, world_x, world_z):# Get tile height at world coordinates
        tile_x = int(world_x + self.size//2)
        tile_z = int(world_z + self.size//2)
        if 0 <= tile_x < self.size and 0 <= tile_z < self.size:
            return self.tile_heights[tile_x][tile_z]
        return 0
    def draw(self):# Draw arena tiles and walls
        for x in range(-self.size//2, self.size//2):
            for z in range(-self.size//2, self.size//2):
                tile_x = x + self.size//2
                tile_z = z + self.size//2
                state = self.tile_states[tile_x][tile_z]
                height = self.tile_heights[tile_x][tile_z]
                glPushMatrix()
                glTranslatef(x, height/2, z)
                if state == 2:
                    lava_intensity = 0.9 + 0.3 * math.sin(time.time() * 3 + x + z)
                    glColor3f(1.0, lava_intensity * 0.4, 0.0)
                    glColor3f(1.0 * lava_intensity, 0.6, 0.0)
                    glScalef(1.2, max(height, 0.1) + 0.3, 1.2)
                    glutSolidCube(1)
                    glScalef(1/1.2, 1/(max(height, 0.1) + 0.3), 1/1.2)
                    glColor3f(1.0, lava_intensity * 0.4, 0.0)
                elif state == 1:
                    glColor3f(0.3, 0.3, 0.7)
                else:
                    if (x + z) % 2 == 0:
                        glColor3f(0.8, 0.8, 0.8)
                    else:
                        glColor3f(0.6, 0.6, 0.6)
                glScalef(1, max(height, 0.1), 1)
                glutSolidCube(1)
                glPopMatrix()
        glColor3f(0.15, 0.15, 0.4)
        wall_height = 6
        for i in range(4):
            glPushMatrix()
            if i == 0:
                glTranslatef(0, wall_height/2, -self.size//2 - 0.5)
                glScalef(self.size + 1, wall_height, 1)
            elif i == 1:
                glTranslatef(0, wall_height/2, self.size//2 + 0.5)
                glScalef(self.size + 1, wall_height, 1)
            elif i == 2:
                glTranslatef(-self.size//2 - 0.5, wall_height/2, 0)
                glScalef(1, wall_height, self.size + 1)
            else:
                glTranslatef(self.size//2 + 0.5, wall_height/2, 0)
                glScalef(1, wall_height, self.size + 1)
            glutSolidCube(1)
            glPopMatrix()
class EnhancedGame:
    def __init__(self):
        self.player = EnhancedPlayer(self)
        self.enemies = []
        self.bullets = []
        self.enemy_bullets = []
        self.collectibles = []
        self.power_ups = []
        self.arena = Arena()
        self.score = 0
        self.high_score = 0
        self.game_over = False
        self.victory = False
        self.wave = 1
        self.enemies_spawned = 0
        self.boss_active = False
        self.camera_mode = 0
        self.camera_angle_x = 0
        self.camera_angle_y = 0
        self.target_angle_x = 0
        self.target_angle_y = 0
        self.camera_smoothing = 0.12
        self.day_night_cycle = 0
        self.fog_enabled = True
        self.keys = set()
        self.special_keys = set()
        self.mouse_buttons = set()
        self.reset_game()
    def reset_game(self):# Reset game state for new game
        self.player.reset()
        self.enemies = []
        self.bullets = []
        self.enemy_bullets = []
        self.collectibles = []
        self.power_ups = []
        if self.score > self.high_score:
            self.high_score = self.score
        self.score = 0
        self.game_over = False
        self.victory = False
        self.wave = 1
        self.enemies_spawned = 0
        self.boss_active = False
        self.camera_mode = 0
        self.camera_angle_x = 0
        self.camera_angle_y = 0
        self.target_angle_x = 0
        self.target_angle_y = 0
        self.day_night_cycle = 0
        self.arena.init_tiles()
        self.spawn_collectibles(5)
        self.spawn_enemies(4)
    def spawn_collectibles(self, count):# Spawn crystals and power cores
        for _ in range(count):
            attempts = 0
            while attempts < 40:
                pos = Vector3(
                    random.uniform(-9, 9),
                    0.8,
                    random.uniform(-9, 9)
                )
                tile_type = self.arena.get_tile_at(pos.x, pos.z)
                if tile_type == 0:
                    item_type = "power_core" if random.random() < 0.3 else "crystal"
                    self.collectibles.append(Collectible(pos, item_type))
                    break
                attempts += 1
    def spawn_enemies(self, count):# Spawn hunters and snipers
        for _ in range(count):
            attempts = 0
            while attempts < 40:
                pos = Vector3(
                    random.uniform(-8.5, 8.5),
                    1.0,
                    random.uniform(-8.5, 8.5)
                )
                tile_type = self.arena.get_tile_at(pos.x, pos.z)
                if ((pos - self.player.position).length() > 6 and tile_type == 0):
                    enemy_type = random.choices(
                        ["hunter", "sniper"],
                        weights=[0.75, 0.25]
                    )[0]
                    self.enemies.append(Enemy(pos, enemy_type))
                    break
                attempts += 1
        self.enemies_spawned += count
    def spawn_boss(self):# Spawn a boss enemy
        if not self.boss_active:
            attempts = 0
            while attempts < 40:
                pos = Vector3(
                    random.uniform(-7, 7),
                    1.5,
                    random.uniform(-7, 7)
                )
                tile_type = self.arena.get_tile_at(pos.x, pos.z)
                if ((pos - self.player.position).length() > 8 and tile_type == 0):
                    self.enemies.append(Enemy(pos, "boss"))
                    self.boss_active = True
                    break
                attempts += 1
    def spawn_power_up(self):
        if random.random() < 0.7:
            attempts = 0
            while attempts < 25:
                pos = Vector3(
                    random.uniform(-8, 8),
                    0.8,
                    random.uniform(-8, 8)
                )
                tile_type = self.arena.get_tile_at(pos.x, pos.z)
                if tile_type == 0:
                    power_type = random.choice(["speed", "shield", "rapid_fire"])
                    self.power_ups.append(PowerUp(pos, power_type))
                    break
                attempts += 1
    def check_collisions(self):# Check all collisions between entities
        for enemy in self.enemies:
            if (enemy.active and 
                (enemy.position - self.player.position).length() < 1.4 and
                self.player.damage_cooldown <= 0):
                damage = 8 if enemy.enemy_type == "boss" else 5
                self.player.take_damage(damage)
                self.player.damage_cooldown = 100
        for bullet in self.enemy_bullets:
            if (bullet.active and 
                (bullet.position - self.player.position).length() < 1.0):
                self.player.take_damage(6)
                bullet.active = False
        for bullet in self.bullets:
            if not bullet.active:
                continue
            for enemy in self.enemies:
                if (enemy.active and 
                    (bullet.position - enemy.position).length() < 1.3):
                    enemy.take_damage()
                    bullet.active = False
                    if not enemy.active:
                        if enemy.enemy_type == "boss":
                            self.score += 50
                            self.boss_active = False
                        else:
                            self.score += 10
                        self.spawn_power_up()
                    break
        for collectible in self.collectibles:# Collect crystals and power cores
            if (collectible.active and 
                (collectible.position - self.player.position).length() < 1.3):
                collectible.active = False
                if collectible.item_type == "power_core":
                    self.score += 8
                else:
                    self.score += 5
        for power_up in self.power_ups:# Collect power-ups
            if (power_up.active and 
                (power_up.position - self.player.position).length() < 1.3):
                self.player.use_power_up(power_up.power_type)
                power_up.active = False
    def update(self):# Update game state each frame
        if self.game_over or self.victory:
            return
        self.day_night_cycle += 0.08
        self.camera_angle_x += (self.target_angle_x - self.camera_angle_x) * self.camera_smoothing
        self.camera_angle_y += (self.target_angle_y - self.camera_angle_y) * self.camera_smoothing
        angle_diff = self.target_angle_y - self.camera_angle_y
        if angle_diff > 180:
            self.target_angle_y -= 360
        elif angle_diff < -180:
            self.target_angle_y += 360
        self.player.update(self.arena)
        for enemy in self.enemies:
            enemy.update(self.player.position, self.arena)
            if enemy.enemy_type in ["sniper", "boss"]:
                bullet = enemy.shoot(self.player.position)
                if bullet:
                    bullet.arena = self.arena
                    self.enemy_bullets.append(bullet)
        for bullet in self.bullets:
            bullet.update()
        for bullet in self.enemy_bullets:
            bullet.update()
        for collectible in self.collectibles:
            collectible.update()
        for power_up in self.power_ups:
            power_up.update()
        self.arena.update()
        self.bullets = [b for b in self.bullets if b.active]
        self.enemy_bullets = [b for b in self.enemy_bullets if b.active]
        self.enemies = [e for e in self.enemies if e.active]
        self.collectibles = [c for c in self.collectibles if c.active]
        self.power_ups = [p for p in self.power_ups if p.active]
        self.check_collisions()
        if self.score >= 100 and not self.boss_active and self.score % 100 == 0:
            self.spawn_boss()
        enemy_target = min(3 + self.score // 25, 12)
        if len(self.enemies) < enemy_target and not self.boss_active:
            self.spawn_enemies(1)
        if len(self.collectibles) < 3:
            self.spawn_collectibles(2)
        if self.player.health <= 0:
            self.game_over = True
        elif self.score >= 300:
            self.victory = True
    def handle_input(self):# Handle user input for movement and actions
        move_dir = Vector3()
        if ord('w') in self.keys or ord('W') in self.keys:
            move_dir.z -= 1
        if ord('s') in self.keys or ord('S') in self.keys:
            move_dir.z += 1
        if ord('a') in self.keys or ord('A') in self.keys:
            move_dir.x -= 1
        if ord('d') in self.keys or ord('D') in self.keys:
            move_dir.x += 1
        if move_dir.length() > 0:
            self.player.move_camera_relative(move_dir.normalize())
        camera_speed = 1.0
        if GLUT_KEY_DOWN in self.special_keys:
            self.target_angle_x = min(85, self.target_angle_x + camera_speed)
        if GLUT_KEY_UP in self.special_keys:
            self.target_angle_x = max(-85, self.target_angle_x - camera_speed)
        if GLUT_KEY_RIGHT in self.special_keys:
            self.target_angle_y -= camera_speed
        if GLUT_KEY_LEFT in self.special_keys:
            self.target_angle_y += camera_speed
        if GLUT_LEFT_BUTTON in self.mouse_buttons:
            bullets = self.player.shoot()
            if bullets:
                for bullet in bullets:
                    bullet.arena = self.arena
                self.bullets.extend(bullets)
    def setup_camera(self):# Setup OpenGL camera based on mode
        glLoadIdentity()
        if self.camera_mode == 0:# First-person mode
            eye_height = 0.5
            cam_x = self.player.position.x
            cam_y = self.player.position.y + eye_height
            cam_z = self.player.position.z
            look_x = cam_x - math.sin(math.radians(self.camera_angle_y)) * math.cos(math.radians(self.camera_angle_x))
            look_y = cam_y - math.sin(math.radians(self.camera_angle_x))
            look_z = cam_z - math.cos(math.radians(self.camera_angle_y)) * math.cos(math.radians(self.camera_angle_x))
            gluLookAt(cam_x, cam_y, cam_z, look_x, look_y, look_z, 0, 1, 0)
        elif self.camera_mode == 1:# Upper view mode
            height = 25
            max_height_nearby = 0
            for x_offset in range(-4, 5):
                for z_offset in range(-4, 5):
                    check_x = self.player.position.x + x_offset
                    check_z = self.player.position.z + z_offset
                    tile_height = self.arena.get_tile_height(check_x, check_z)
                    max_height_nearby = max(max_height_nearby, tile_height)
            height = max(height, max_height_nearby + 12)
            gluLookAt(self.player.position.x, height, self.player.position.z,
                     self.player.position.x, 0, self.player.position.z,
                     0, 0, -1)
    def draw_enhanced_hud(self):
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        glOrtho(0, WINDOW_WIDTH, WINDOW_HEIGHT, 0, -1, 1)
        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()
        glDisable(GL_DEPTH_TEST)
        bar_width = 250
        bar_height = 25
        glColor3f(0.1, 0.1, 0.1)
        glBegin(GL_QUADS)
        glVertex3f(15, 15, 0)
        glVertex3f(15 + bar_width, 15, 0)
        glVertex3f(15 + bar_width, 15 + bar_height, 0)
        glVertex3f(15, 15 + bar_height, 0)
        glEnd()
        health_ratio = self.player.health / self.player.max_health
        if health_ratio > 0.7:
            glColor3f(0.0, 0.9, 0.0)
        elif health_ratio > 0.4:
            glColor3f(0.9, 0.9, 0.0)
        else:
            glColor3f(0.9, 0.0, 0.0)
        glBegin(GL_QUADS)
        health_width = health_ratio * bar_width
        glVertex3f(15, 15, 0)
        glVertex3f(15 + health_width, 15, 0)
        glVertex3f(15 + health_width, 15 + bar_height, 0)
        glVertex3f(15, 15 + bar_height, 0)
        glEnd()
        glColor3f(0.1, 0.1, 0.1)
        glBegin(GL_QUADS)
        glVertex3f(15, 50, 0)
        glVertex3f(15 + bar_width, 50, 0)
        glVertex3f(15 + bar_width, 50 + bar_height, 0)
        glVertex3f(15, 50 + bar_height, 0)
        glEnd()
        glColor3f(0.0, 0.4, 0.9)
        glBegin(GL_QUADS)
        energy_width = (self.player.energy / self.player.max_energy) * bar_width# Draw energy bar
        glVertex3f(15, 50, 0)
        glVertex3f(15 + energy_width, 50, 0)
        glVertex3f(15 + energy_width, 50 + bar_height, 0)
        glVertex3f(15, 50 + bar_height, 0)
        glEnd()
        glColor3f(1.0, 1.0, 1.0)
        glRasterPos(15, 95)  
        score_text = f"SCORE: {self.score}"
        for char in score_text:# Draw score and high score
            glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18, ord(char))
        glColor3f(1.0, 0.8, 0.0)
        glRasterPos(15, 115)
        high_score_text = f"HIGH SCORE: {self.high_score}"
        for char in high_score_text:
            glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18, ord(char))
        y_offset = 135
        if self.player.speed_boost > 0:
            glColor3f(0.0, 1.0, 0.2)
            glRasterPos(15, y_offset)
            speed_text = f"SPEED BOOST: {self.player.speed_boost//60 + 1}s"
            for char in speed_text:
                glutBitmapCharacter(GLUT_BITMAP_HELVETICA_12, ord(char))
            y_offset += 20
        if self.player.shield_time > 0:
            glColor3f(0.0, 0.6, 1.0)
            glRasterPos(15, y_offset)
            shield_text = f"SHIELD: {self.player.shield_time//60 + 1}s"
            for char in shield_text:
                glutBitmapCharacter(GLUT_BITMAP_HELVETICA_12, ord(char))
            y_offset += 20
        if self.player.rapid_fire_time > 0:
            glColor3f(1.0, 0.6, 0.0)
            glRasterPos(15, y_offset)
            rapid_text = f"RAPID FIRE: {self.player.rapid_fire_time//60 + 1}s"
            for char in rapid_text:
                glutBitmapCharacter(GLUT_BITMAP_HELVETICA_12, ord(char))
        if self.camera_mode == 0:
            center_x, center_y = WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2
            spread = 10
            if self.player.velocity.length() > 0.02:
                spread += int(self.player.velocity.length() * 120)
            glColor3f(0.0, 1.0, 0.2)
            glLineWidth(3.0)
            glBegin(GL_LINES)
            glVertex3f(center_x - spread - 12, center_y, 0)
            glVertex3f(center_x - spread, center_y, 0)
            glVertex3f(center_x + spread, center_y, 0)
            glVertex3f(center_x + spread + 12, center_y, 0)
            glVertex3f(center_x, center_y - spread - 12, 0)
            glVertex3f(center_x, center_y - spread, 0)
            glVertex3f(center_x, center_y + spread, 0)
            glVertex3f(center_x, center_y + spread + 12, 0)
            glEnd()
            glLineWidth(1.0)
        if self.game_over:
            glColor3f(0.0, 0.0, 0.0)
            glBegin(GL_QUADS)
            glVertex3f(0, 0, 0)
            glVertex3f(WINDOW_WIDTH, 0, 0)
            glVertex3f(WINDOW_WIDTH, WINDOW_HEIGHT, 0)
            glVertex3f(0, WINDOW_HEIGHT, 0)
            glEnd()
            glColor3f(1.0, 0.2, 0.2)
            glRasterPos(WINDOW_WIDTH//2 - 80, WINDOW_HEIGHT//2 - 30)
            game_over_text = "GAME OVER"
            for char in game_over_text:
                glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18, ord(char))
            glColor3f(1.0, 1.0, 1.0)
            glRasterPos(WINDOW_WIDTH//2 - 100, WINDOW_HEIGHT//2 + 10)
            restart_text = "Press R to Restart"
            for char in restart_text:
                glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18, ord(char))
        elif self.victory:
            glColor3f(0.0, 0.5, 0.0)
            glBegin(GL_QUADS)
            glVertex3f(0, 0, 0)
            glVertex3f(WINDOW_WIDTH, 0, 0)
            glVertex3f(WINDOW_WIDTH, WINDOW_HEIGHT, 0)
            glVertex3f(0, WINDOW_HEIGHT, 0)
            glEnd()
            glColor3f(1.0, 1.0, 0.0)
            glRasterPos(WINDOW_WIDTH//2 - 70, WINDOW_HEIGHT//2 - 30)
            victory_text = "VICTORY!"
            for char in victory_text:
                glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18, ord(char))
            glColor3f(1.0, 1.0, 1.0)
            glRasterPos(WINDOW_WIDTH//2 - 120, WINDOW_HEIGHT//2 + 10)
            champion_text = "You are the Champion!"
            for char in champion_text:
                glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18, ord(char))
        glEnable(GL_DEPTH_TEST)
        glPopMatrix()
        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)
    def draw(self):# Render the entire scene
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        day_factor = (math.sin(self.day_night_cycle) + 1) / 2
        bg_r = 0.08 + 0.6 * day_factor
        bg_g = 0.12 + 0.7 * day_factor
        bg_b = 0.25 + 0.7 * day_factor
        glClearColor(bg_r, bg_g, bg_b, 1.0)
        self.setup_camera()
        glEnable(GL_COLOR_MATERIAL)
        light_intensity = 0.7 + 0.5 * day_factor
        glColor3f(light_intensity, light_intensity * 0.95, light_intensity * 0.85)
        self.arena.draw()
        if not self.game_over and self.camera_mode == 1:
            self.player.draw()
        for enemy in self.enemies:
            enemy.draw()
        for bullet in self.bullets:
            bullet.draw()
        for bullet in self.enemy_bullets:
            bullet.draw()
        for collectible in self.collectibles:
            collectible.draw()
        for power_up in self.power_ups:
            power_up.draw()
        self.draw_enhanced_hud()
        glutSwapBuffers()
enhanced_game = None
def init_opengl():# Initialize OpenGL settings
    glEnable(GL_DEPTH_TEST)
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(75, WINDOW_WIDTH/WINDOW_HEIGHT, 0.1, 120.0)
    glMatrixMode(GL_MODELVIEW)
def display():
    if enhanced_game:
        enhanced_game.draw()
def update(value):
    if enhanced_game:
        enhanced_game.handle_input()
        enhanced_game.update()
    glutPostRedisplay()
    glutTimerFunc(16, update, 0)
def keyboard(key, x, y):# Handle key press events
    if enhanced_game:
        enhanced_game.keys.add(ord(key))
        if key == b'x' or key == b'X':
            bullets = enhanced_game.player.shoot()
            if bullets:
                for bullet in bullets:
                    bullet.arena = enhanced_game.arena
                enhanced_game.bullets.extend(bullets)
        elif key == b'f' or key == b'F':
            enhanced_game.fog_enabled = not enhanced_game.fog_enabled
        elif key == b' ':
            enhanced_game.player.jump()
        elif key == b'r' or key == b'R':
            enhanced_game.reset_game()
        elif key == b'c' or key == b'C':
            enhanced_game.camera_mode = (enhanced_game.camera_mode + 1) % 2
        elif key == b'\x1b':
            import sys
            sys.exit()
def keyboard_up(key, x, y):# Handle key release events
    if enhanced_game:
        enhanced_game.keys.discard(ord(key))
def special_keys(key, x, y):# Handle special key press events
    if enhanced_game:
        enhanced_game.special_keys.add(key)
def special_keys_up(key, x, y):# Handle special key release events
    if enhanced_game:
        enhanced_game.special_keys.discard(key)
def mouse_button(button, state, x, y):# Handle mouse button events
    if enhanced_game:
        if state == GLUT_DOWN:
            enhanced_game.mouse_buttons.add(button)
            if button == GLUT_LEFT_BUTTON and enhanced_game.camera_mode == 0:
                bullets = enhanced_game.player.shoot()
                if bullets:
                    for bullet in bullets:
                        bullet.arena = enhanced_game.arena
                    enhanced_game.bullets.extend(bullets)
        else:
            enhanced_game.mouse_buttons.discard(button)
def reshape(width, height):# Handle window resize events
    global WINDOW_WIDTH, WINDOW_HEIGHT
    WINDOW_WIDTH = width
    WINDOW_HEIGHT = height
    glViewport(0, 0, width, height)
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(75, width/height, 0.1, 120.0)
    glMatrixMode(GL_MODELVIEW)
def main():
    global enhanced_game
    glutInit()
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH)
    glutInitWindowSize(WINDOW_WIDTH, WINDOW_HEIGHT)
    glutInitWindowPosition(150, 100)
    glutCreateWindow(b"Enhanced Arena Shooter - COMPLIANT VERSION")
    init_opengl()
    enhanced_game = EnhancedGame()
    glutDisplayFunc(display)
    glutKeyboardFunc(keyboard)
    try:
        glutKeyboardUpFunc(keyboard_up)
        glutSpecialUpFunc(special_keys_up)
    except:
        pass
    glutSpecialFunc(special_keys)
    glutMouseFunc(mouse_button)
    glutReshapeFunc(reshape)
    glutTimerFunc(16, update, 0)
    glutMainLoop()
if __name__ == "__main__":
    main()
