import numpy as np
import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *
import os
import sys
import math
import time
import random
import cv2

# Constants for the soccer field
FIELD_WIDTH = 105.0
FIELD_LENGTH = 68.0

class VRSoccerExperience:
    def __init__(self):
        # Initialize Pygame and OpenGL
        pygame.init()
        self.width, self.height = 1920, 1080  # Higher resolution
        self.display = pygame.display.set_mode(
            (self.width, self.height), 
            DOUBLEBUF | OPENGL | pygame.RESIZABLE | pygame.FULLSCREEN
        )
        pygame.display.set_caption("Soccer VR Experience")
        
        # OpenGL settings
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_LIGHTING)
        glEnable(GL_LIGHT0)
        glEnable(GL_LIGHT1)  # Additional light source
        glEnable(GL_COLOR_MATERIAL)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        
        # Lighting setup
        glLightfv(GL_LIGHT0, GL_POSITION, (0, 100, 100, 1))
        glLightfv(GL_LIGHT0, GL_AMBIENT, (0.2, 0.2, 0.2, 1))
        glLightfv(GL_LIGHT0, GL_DIFFUSE, (0.8, 0.8, 0.8, 1))
        glLightfv(GL_LIGHT1, GL_POSITION, (0, 100, -100, 1))
        glLightfv(GL_LIGHT1, GL_AMBIENT, (0.1, 0.1, 0.1, 1))
        glLightfv(GL_LIGHT1, GL_DIFFUSE, (0.6, 0.6, 0.6, 1))
        
        # Field texture
        self.field_texture = self.create_field_texture()
        
        # Player positions with more realistic formations
        self.player_positions = [
            # Team 1 (Red) - 4-3-3 Formation
            (-20, 10, (1.0, 0.0, 0.0)),   # Forward
            (-25, 0, (1.0, 0.0, 0.0)),    # Forward
            (-20, -10, (1.0, 0.0, 0.0)),  # Forward
            (-35, 15, (1.0, 0.0, 0.0)),   # Midfielder
            (-35, 0, (1.0, 0.0, 0.0)),    # Midfielder
            (-35, -15, (1.0, 0.0, 0.0)),  # Midfielder
            (-50, 20, (1.0, 0.0, 0.0)),   # Defender
            (-50, 10, (1.0, 0.0, 0.0)),   # Defender
            (-50, -10, (1.0, 0.0, 0.0)),  # Defender
            (-50, -20, (1.0, 0.0, 0.0)),  # Defender
            (-60, 0, (1.0, 0.0, 0.0)),    # Goalkeeper
            
            # Team 2 (Blue) - 4-3-3 Formation
            (20, 10, (0.0, 0.0, 1.0)),    # Forward
            (25, 0, (0.0, 0.0, 1.0)),     # Forward
            (20, -10, (0.0, 0.0, 1.0)),   # Forward
            (35, 15, (0.0, 0.0, 1.0)),    # Midfielder
            (35, 0, (0.0, 0.0, 1.0)),     # Midfielder
            (35, -15, (0.0, 0.0, 1.0)),   # Midfielder
            (50, 20, (0.0, 0.0, 1.0)),    # Defender
            (50, 10, (0.0, 0.0, 1.0)),    # Defender
            (50, -10, (0.0, 0.0, 1.0)),   # Defender
            (50, -20, (0.0, 0.0, 1.0)),   # Defender
            (60, 0, (0.0, 0.0, 1.0))      # Goalkeeper
        ]
        
        # Ball properties
        self.ball_pos = [0.0, 0.5, 0.0]
        self.ball_vel = [0.1, 0.0, 0.1]
        self.ball_radius = 0.2
        
        # Camera position (VR view)
        self.camera_pos = [0.0, 1.7, 0.0]  # Standing height
        self.look_dir = [0.0, 0.0, -1.0]   # Looking forward
        self.up_vector = [0.0, 1.0, 0.0]   # Up is Y-axis
        
        # Movement and rotation speeds
        self.move_speed = 0.5
        self.rot_speed = 2.0
        
        # VR settings
        self.vr_mode = True
        self.ipd = 0.064  # Interpupillary distance in meters
        
        # Game state
        self.game_time = 0
        self.score = [0, 0]  # Team 1, Team 2
        
        # Effects
        self.effects = []
        
        # Animation
        self.animation_time = 0
        self.running = True
        self.clock = pygame.time.Clock()
        
        # Print modern instructions
        print("\n⚽ Soccer VR Experience Controls:")
        print("  WASD: Move around the field")
        print("  Arrow keys: Look around")
        print("  V: Toggle VR mode (stereoscopic 3D)")
        print("  +/-: Adjust eye separation")
        print("  Space: Kick ball")
        print("  ESC: Exit")
    
    def create_field_texture(self):
        """Create a more detailed soccer field texture"""
        tex_width, tex_height = 1024, 1024  # Higher resolution texture
        
        # Create empty array
        texture = np.zeros((tex_height, tex_width, 3), dtype=np.uint8)
        
        # Field color (modern green)
        texture[:, :] = (20, 140, 20)  # Green field
        
        # White lines
        line_color = (255, 255, 255)
        line_thickness = 8
        
        # Field border
        margin = 30
        texture[margin:margin+line_thickness, margin:-margin] = line_color  # Top
        texture[-margin-line_thickness:-margin, margin:-margin] = line_color  # Bottom
        texture[margin:-margin, margin:margin+line_thickness] = line_color  # Left
        texture[margin:-margin, -margin-line_thickness:-margin] = line_color  # Right
        
        # Center line
        texture[margin:-margin, (tex_width//2)-2:(tex_width//2)+3] = line_color
        
        # Center circle
        center = (tex_width//2, tex_height//2)
        radius = tex_height//6
        for y in range(tex_height):
            for x in range(tex_width):
                dist = np.sqrt((x - center[0])**2 + (y - center[1])**2)
                if abs(dist - radius) < 2:
                    texture[y, x] = line_color
        
        # Add grass pattern
        for _ in range(1000):
            x = random.randint(0, tex_width-1)
            y = random.randint(0, tex_height-1)
            cv2.circle(texture, (x, y), 1, (0, 100, 0), -1)
        
        # Convert to RGB for OpenGL
        texture = np.flip(texture, axis=0)
        
        # Create OpenGL texture
        texture_id = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, texture_id)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR_MIPMAP_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, tex_width, tex_height, 0, GL_RGB, GL_UNSIGNED_BYTE, texture)
        glGenerateMipmap(GL_TEXTURE_2D)
        
        return texture_id
    
    def draw_field(self):
        """Draw the soccer field with improved visuals"""
        # Enable texture
        glEnable(GL_TEXTURE_2D)
        glBindTexture(GL_TEXTURE_2D, self.field_texture)
        
        # Material properties
        glMaterialfv(GL_FRONT, GL_AMBIENT, (0.2, 0.5, 0.2, 1.0))
        glMaterialfv(GL_FRONT, GL_DIFFUSE, (0.8, 0.8, 0.8, 1.0))
        
        # Draw the field quad
        glBegin(GL_QUADS)
        glNormal3f(0, 1, 0)  # Normal pointing up
        
        glTexCoord2f(0, 0)
        glVertex3f(-FIELD_WIDTH/2, 0, -FIELD_LENGTH/2)
        
        glTexCoord2f(1, 0)
        glVertex3f(FIELD_WIDTH/2, 0, -FIELD_LENGTH/2)
        
        glTexCoord2f(1, 1)
        glVertex3f(FIELD_WIDTH/2, 0, FIELD_LENGTH/2)
        
        glTexCoord2f(0, 1)
        glVertex3f(-FIELD_WIDTH/2, 0, FIELD_LENGTH/2)
        glEnd()
        
        # Disable texture
        glDisable(GL_TEXTURE_2D)
        
        # Draw goalposts
        self.draw_goalpost(-FIELD_WIDTH/2, 0, 0)
        self.draw_goalpost(FIELD_WIDTH/2, 0, 0)
    
    def draw_goalpost(self, x, y, z):
        """Draw a more detailed goalpost"""
        goal_width = 7.32  # Standard FIFA goal width
        goal_height = 2.44  # Standard FIFA goal height
        post_radius = 0.1
        
        # Material properties
        glMaterialfv(GL_FRONT, GL_AMBIENT, (0.2, 0.2, 0.2, 1.0))
        glMaterialfv(GL_FRONT, GL_DIFFUSE, (1.0, 1.0, 1.0, 1.0))
        
        # Goal orientation
        goal_depth = 1.5
        direction = 1 if x < 0 else -1
        
        quad = gluNewQuadric()
        gluQuadricNormals(quad, GLU_SMOOTH)
        
        # Left post
        glPushMatrix()
        glTranslatef(x + (direction * post_radius), y, z - goal_width/2)
        glRotatef(90, 1, 0, 0)
        gluCylinder(quad, post_radius, post_radius, goal_height, 10, 10)
        glPopMatrix()
        
        # Right post
        glPushMatrix()
        glTranslatef(x + (direction * post_radius), y, z + goal_width/2)
        glRotatef(90, 1, 0, 0)
        gluCylinder(quad, post_radius, post_radius, goal_height, 10, 10)
        glPopMatrix()
        
        # Crossbar
        glPushMatrix()
        glTranslatef(x + (direction * post_radius), y + goal_height, z - goal_width/2)
        glRotatef(90, 0, 1, 0)
        gluCylinder(quad, post_radius, post_radius, goal_width, 10, 10)
        glPopMatrix()
        
        # Draw net (semi-transparent)
        glMaterialfv(GL_FRONT, GL_AMBIENT, (0.9, 0.9, 0.9, 0.4))
        glMaterialfv(GL_FRONT, GL_DIFFUSE, (0.9, 0.9, 0.9, 0.4))
        
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        
        # Back panel
        glBegin(GL_QUADS)
        glVertex3f(x + (direction * goal_depth), y, z - goal_width/2)
        glVertex3f(x + (direction * goal_depth), y + goal_height, z - goal_width/2)
        glVertex3f(x + (direction * goal_depth), y + goal_height, z + goal_width/2)
        glVertex3f(x + (direction * goal_depth), y, z + goal_width/2)
        glEnd()
        
        # Top panel
        glBegin(GL_QUADS)
        glVertex3f(x, y + goal_height, z - goal_width/2)
        glVertex3f(x + (direction * goal_depth), y + goal_height, z - goal_width/2)
        glVertex3f(x + (direction * goal_depth), y + goal_height, z + goal_width/2)
        glVertex3f(x, y + goal_height, z + goal_width/2)
        glEnd()
        
        # Side panels
        glBegin(GL_QUADS)
        glVertex3f(x, y, z - goal_width/2)
        glVertex3f(x, y + goal_height, z - goal_width/2)
        glVertex3f(x + (direction * goal_depth), y + goal_height, z - goal_width/2)
        glVertex3f(x + (direction * goal_depth), y, z - goal_width/2)
        glEnd()
        
        glBegin(GL_QUADS)
        glVertex3f(x, y, z + goal_width/2)
        glVertex3f(x, y + goal_height, z + goal_width/2)
        glVertex3f(x + (direction * goal_depth), y + goal_height, z + goal_width/2)
        glVertex3f(x + (direction * goal_depth), y, z + goal_width/2)
        glEnd()
        
        glDisable(GL_BLEND)
    
    def draw_player(self, position):
        """Draw a more detailed player model"""
        x, z, team_color = position
        
        # Animation: make players move slightly
        x += 0.3 * math.sin(self.animation_time + x * 0.3)
        z += 0.3 * math.cos(self.animation_time + z * 0.3)
        
        glPushMatrix()
        glTranslatef(x, 0, z)
        
        # Player body
        glColor3f(*team_color)
        glMaterialfv(GL_FRONT, GL_AMBIENT, (*team_color, 1.0))
        glMaterialfv(GL_FRONT, GL_DIFFUSE, (*team_color, 1.0))
        
        # Body
        glPushMatrix()
        glTranslatef(0, 1.0, 0)
        glRotatef(90, 1, 0, 0)
        gluCylinder(gluNewQuadric(), 0.3, 0.3, 1.0, 10, 10)
        glPopMatrix()
        
        # Head
        glPushMatrix()
        glTranslatef(0, 1.8, 0)
        gluSphere(gluNewQuadric(), 0.2, 10, 10)
        glPopMatrix()
        
        # Arms
        glPushMatrix()
        glTranslatef(0, 1.5, 0)
        glRotatef(45 * math.sin(self.animation_time), 0, 1, 0)
        glRotatef(90, 0, 1, 0)
        gluCylinder(gluNewQuadric(), 0.1, 0.1, 0.5, 10, 10)
        glPopMatrix()
        
        glPushMatrix()
        glTranslatef(0, 1.5, 0)
        glRotatef(-45 * math.sin(self.animation_time), 0, 1, 0)
        glRotatef(90, 0, 1, 0)
        gluCylinder(gluNewQuadric(), 0.1, 0.1, 0.5, 10, 10)
        glPopMatrix()
        
        # Legs
        glPushMatrix()
        glTranslatef(0.2, 0.5, 0)
        glRotatef(30 * math.sin(self.animation_time), 1, 0, 0)
        glRotatef(90, 1, 0, 0)
        gluCylinder(gluNewQuadric(), 0.15, 0.15, 0.8, 10, 10)
        glPopMatrix()
        
        glPushMatrix()
        glTranslatef(-0.2, 0.5, 0)
        glRotatef(-30 * math.sin(self.animation_time), 1, 0, 0)
        glRotatef(90, 1, 0, 0)
        gluCylinder(gluNewQuadric(), 0.15, 0.15, 0.8, 10, 10)
        glPopMatrix()
        
        glPopMatrix()
    
    def draw_ball(self):
        """Draw a more detailed soccer ball"""
        glPushMatrix()
        glTranslatef(*self.ball_pos)
        
        # Ball texture
        glColor3f(1.0, 1.0, 1.0)
        glMaterialfv(GL_FRONT, GL_AMBIENT, (0.8, 0.8, 0.8, 1.0))
        glMaterialfv(GL_FRONT, GL_DIFFUSE, (0.8, 0.8, 0.8, 1.0))
        
        # Draw pentagons and hexagons to create a soccer ball pattern
        gluSphere(gluNewQuadric(), self.ball_radius, 20, 20)
        
        # Add black patches
        glColor3f(0.0, 0.0, 0.0)
        for i in range(12):
            glPushMatrix()
            glRotatef(i * 30, 0, 1, 0)
            glRotatef(i * 15, 1, 0, 0)
            gluPartialDisk(gluNewQuadric(), self.ball_radius * 0.9, self.ball_radius, 
                          5, 1, 0, 72)
            glPopMatrix()
        
        glPopMatrix()
    
    def add_effect(self, effect_type, position):
        """Add visual effects"""
        self.effects.append({
            'type': effect_type,
            'position': position.copy(),
            'time': 0,
            'max_time': 1.0
        })
    
    def draw_effects(self):
        """Draw visual effects"""
        for effect in self.effects[:]:
            if effect['time'] >= effect['max_time']:
                self.effects.remove(effect)
                continue
            
            glPushMatrix()
            glTranslatef(*effect['position'])
            
            if effect['type'] == 'goal':
                # Goal celebration effect
                alpha = 1.0 - (effect['time'] / effect['max_time'])
                glColor4f(1.0, 1.0, 0.0, alpha)
                glMaterialfv(GL_FRONT, GL_AMBIENT, (1.0, 1.0, 0.0, alpha))
                glMaterialfv(GL_FRONT, GL_DIFFUSE, (1.0, 1.0, 0.0, alpha))
                
                # Draw particles
                for _ in range(10):
                    angle = random.uniform(0, 2 * math.pi)
                    radius = random.uniform(0, effect['time'] * 2)
                    x = radius * math.cos(angle)
                    y = radius * math.sin(angle)
                    glPushMatrix()
                    glTranslatef(x, y, 0)
                    gluSphere(gluNewQuadric(), 0.1, 5, 5)
                    glPopMatrix()
            
            effect['time'] += 0.016  # Assuming 60 FPS
            glPopMatrix()
    
    def set_3d_camera(self, eye_offset=0.0):
        """Set up the camera for stereoscopic 3D"""
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        
        # Calculate aspect ratio
        aspect = self.width / (self.height / 2)
        
        # Set up perspective projection
        gluPerspective(45, aspect, 0.1, 200.0)
        
        # Set up modelview matrix
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        
        # Calculate eye position
        eye_pos = [
            self.camera_pos[0] + eye_offset,
            self.camera_pos[1],
            self.camera_pos[2]
        ]
        
        # Set up view
        gluLookAt(
            eye_pos[0], eye_pos[1], eye_pos[2],
            eye_pos[0] + self.look_dir[0],
            eye_pos[1] + self.look_dir[1],
            eye_pos[2] + self.look_dir[2],
            self.up_vector[0], self.up_vector[1], self.up_vector[2]
        )
    
    def handle_input(self):
        """Handle user input for movement and interaction"""
        keys = pygame.key.get_pressed()
        
        # Movement
        if keys[pygame.K_w]:
            self.camera_pos[0] += self.look_dir[0] * self.move_speed
            self.camera_pos[2] += self.look_dir[2] * self.move_speed
        if keys[pygame.K_s]:
            self.camera_pos[0] -= self.look_dir[0] * self.move_speed
            self.camera_pos[2] -= self.look_dir[2] * self.move_speed
        if keys[pygame.K_a]:
            # Strafe left
            self.camera_pos[0] += self.look_dir[2] * self.move_speed
            self.camera_pos[2] -= self.look_dir[0] * self.move_speed
        if keys[pygame.K_d]:
            # Strafe right
            self.camera_pos[0] -= self.look_dir[2] * self.move_speed
            self.camera_pos[2] += self.look_dir[0] * self.move_speed
        
        # Look around
        if keys[pygame.K_LEFT]:
            self.rotate_view_y(self.rot_speed)
        if keys[pygame.K_RIGHT]:
            self.rotate_view_y(-self.rot_speed)
        if keys[pygame.K_UP]:
            self.rotate_view_x(self.rot_speed)
        if keys[pygame.K_DOWN]:
            self.rotate_view_x(-self.rot_speed)
        
        # VR mode toggle
        if keys[pygame.K_v]:
            self.vr_mode = not self.vr_mode
        
        # Adjust eye separation
        if keys[pygame.K_PLUS] or keys[pygame.K_EQUALS]:
            self.ipd += 0.001
        if keys[pygame.K_MINUS]:
            self.ipd = max(0.01, self.ipd - 0.001)
        
        # Kick ball
        if keys[pygame.K_SPACE]:
            # Calculate direction to ball
            dx = self.ball_pos[0] - self.camera_pos[0]
            dz = self.ball_pos[2] - self.camera_pos[2]
            dist = math.sqrt(dx*dx + dz*dz)
            
            if dist < 5:  # Only kick if close enough
                self.ball_vel = [
                    dx/dist * 0.5,
                    0.3,
                    dz/dist * 0.5
                ]
    
    def rotate_view_y(self, angle):
        """Rotate view around Y axis"""
        # Convert angle to radians
        angle_rad = math.radians(angle)
        
        # Calculate new look direction
        new_x = self.look_dir[0] * math.cos(angle_rad) - self.look_dir[2] * math.sin(angle_rad)
        new_z = self.look_dir[0] * math.sin(angle_rad) + self.look_dir[2] * math.cos(angle_rad)
        
        self.look_dir[0] = new_x
        self.look_dir[2] = new_z
    
    def rotate_view_x(self, angle):
        """Rotate view around X axis"""
        # Convert angle to radians
        angle_rad = math.radians(angle)
        
        # Calculate new look direction
        new_y = self.look_dir[1] * math.cos(angle_rad) - self.look_dir[2] * math.sin(angle_rad)
        new_z = self.look_dir[1] * math.sin(angle_rad) + self.look_dir[2] * math.cos(angle_rad)
        
        self.look_dir[1] = new_y
        self.look_dir[2] = new_z
    
    def handle_events(self):
        """Handle pygame events"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
    
    def update_ball_physics(self):
        """Update ball physics with more realistic movement"""
        # Gravity
        self.ball_vel[1] -= 0.01
        
        # Update position
        for i in range(3):
            self.ball_pos[i] += self.ball_vel[i]
        
        # Ground collision
        if self.ball_pos[1] < self.ball_radius:
            self.ball_pos[1] = self.ball_radius
            self.ball_vel[1] = -self.ball_vel[1] * 0.8  # Bounce with energy loss
        
        # Field boundaries
        if abs(self.ball_pos[0]) > FIELD_WIDTH/2:
            self.ball_vel[0] = -self.ball_vel[0] * 0.8
            self.ball_pos[0] = np.sign(self.ball_pos[0]) * (FIELD_WIDTH/2 - 0.1)
        
        if abs(self.ball_pos[2]) > FIELD_LENGTH/2:
            self.ball_vel[2] = -self.ball_vel[2] * 0.8
            self.ball_pos[2] = np.sign(self.ball_pos[2]) * (FIELD_LENGTH/2 - 0.1)
        
        # Friction
        self.ball_vel[0] *= 0.99
        self.ball_vel[2] *= 0.99
        
        # Check for goals
        if abs(self.ball_pos[0]) > FIELD_WIDTH/2 - 1 and abs(self.ball_pos[2]) < 7.32/2:
            if self.ball_pos[0] < 0:
                self.score[1] += 1
            else:
                self.score[0] += 1
            self.add_effect('goal', self.ball_pos.copy())
            self.reset_ball()
    
    def reset_ball(self):
        """Reset ball to center"""
        self.ball_pos = [0.0, 0.5, 0.0]
        self.ball_vel = [0.1, 0.0, 0.1]
    
    def run(self):
        """Main game loop"""
        while self.running:
            self.handle_events()
            self.handle_input()
            
            # Clear the screen
            glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
            
            if self.vr_mode:
                # Left eye
                glViewport(0, 0, self.width//2, self.height)
                self.set_3d_camera(-self.ipd/2)
                self.draw_scene()
                
                # Right eye
                glViewport(self.width//2, 0, self.width//2, self.height)
                self.set_3d_camera(self.ipd/2)
                self.draw_scene()
            else:
                # Single view
                glViewport(0, 0, self.width, self.height)
                self.set_3d_camera(0)
                self.draw_scene()
            
            # Update animation
            self.animation_time += 0.016
            self.game_time += 0.016
            
            # Update ball physics
            self.update_ball_physics()
            
            pygame.display.flip()
            self.clock.tick(60)
        
        pygame.quit()
    
    def draw_scene(self):
        """Draw the complete scene"""
        # Draw field
        self.draw_field()
        
        # Draw players
        for pos in self.player_positions:
            self.draw_player(pos)
        
        # Draw ball
        self.draw_ball()
        
        # Draw effects
        self.draw_effects()

if __name__ == "__main__":
    app = VRSoccerExperience()
    app.run() 