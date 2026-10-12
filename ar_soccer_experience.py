import numpy as np
import cv2
import cv2.aruco as aruco
import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *
import os
import sys
import math
import time
import random

# Constants for the soccer field
FIELD_WIDTH = 105.0
FIELD_LENGTH = 68.0

# Dictionary for ArUco markers
ARUCO_DICT = aruco.Dictionary_get(aruco.DICT_4X4_50)
ARUCO_PARAMS = aruco.DetectorParameters_create()

class ARSoccerExperience:
    def __init__(self):
        # Initialize Pygame and OpenGL
        pygame.init()
        # Set up display with OpenGL support
        self.width, self.height = 1920, 1080  # Higher resolution
        self.display = pygame.display.set_mode(
            (self.width, self.height), 
            DOUBLEBUF | OPENGL | pygame.RESIZABLE | pygame.FULLSCREEN
        )
        pygame.display.set_caption("Soccer AR Experience")
        
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
        
        # Perspective settings
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(45, (self.width / self.height), 0.1, 200.0)
        
        # Modelview
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        
        # Camera setup
        self.camera_index = 0
        self.cap = None
        self.init_camera()
        
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
        
        # Animation
        self.animation_time = 0
        self.running = True
        self.clock = pygame.time.Clock()
        
        # AR mode flag
        self.ar_mode = True
        
        # Game state
        self.game_time = 0
        self.score = [0, 0]  # Team 1, Team 2
        
        # Effects
        self.effects = []
        
        # Print modern instructions
        print("\n⚽ Soccer AR Experience Controls:")
        print("  A: Toggle AR mode")
        print("  C: Change camera view")
        print("  Arrow keys: Rotate view")
        print("  +/-: Zoom in/out")
        print("  Space: Kick ball")
        print("  ESC: Exit")
        print("\n🎯 Place ArUco marker (ID: 0) in front of the camera to track the field.")
    
    def init_camera(self):
        """Initialize the webcam"""
        if self.cap is not None:
            self.cap.release()
        
        try:
            self.cap = cv2.VideoCapture(self.camera_index)
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
            
            # Check if camera opened successfully
            if not self.cap.isOpened():
                print("Error: Could not open camera.")
                self.cap = None
                self.ar_mode = False
        except Exception as e:
            print(f"Error initializing camera: {e}")
            self.cap = None
            self.ar_mode = False
    
    def create_field_texture(self):
        """Create a more detailed soccer field texture"""
        tex_width, tex_height = 1024, 1024  # Higher resolution texture
        
        # Create empty array
        texture = np.zeros((tex_height, tex_width, 3), dtype=np.uint8)
        
        # Field color (modern green)
        texture[:, :] = (0, 120, 0)
        
        # Draw field lines (white)
        line_color = (255, 255, 255)
        line_width = 8
        
        # Field outline
        margin = 50
        cv2.rectangle(texture, 
                    (margin, margin), 
                    (tex_width - margin, tex_height - margin), 
                    line_color, line_width)
        
        # Center line
        cv2.line(texture, 
                (tex_width // 2, margin), 
                (tex_width // 2, tex_height - margin), 
                line_color, line_width)
        
        # Center circle
        center = (tex_width // 2, tex_height // 2)
        radius = min(tex_width, tex_height) // 8
        cv2.circle(texture, center, radius, line_color, line_width)
        
        # Center dot
        cv2.circle(texture, center, 8, line_color, -1)
        
        # Penalty areas
        penalty_width = tex_width // 4
        penalty_height = tex_height // 6
        
        # Left penalty area
        cv2.rectangle(texture, 
                    (margin, tex_height // 2 - penalty_height // 2), 
                    (margin + penalty_width, tex_height // 2 + penalty_height // 2), 
                    line_color, line_width)
        
        # Right penalty area
        cv2.rectangle(texture, 
                    (tex_width - margin - penalty_width, tex_height // 2 - penalty_height // 2), 
                    (tex_width - margin, tex_height // 2 + penalty_height // 2), 
                    line_color, line_width)
        
        # Add grass pattern
        for _ in range(1000):
            x = random.randint(0, tex_width-1)
            y = random.randint(0, tex_height-1)
            cv2.circle(texture, (x, y), 1, (0, 100, 0), -1)
        
        # Convert to RGB for OpenGL
        texture = cv2.cvtColor(texture, cv2.COLOR_BGR2RGB)
        
        # Create OpenGL texture
        texture_id = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, texture_id)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR_MIPMAP_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, tex_width, tex_height, 0, GL_RGB, GL_UNSIGNED_BYTE, texture)
        glGenerateMipmap(GL_TEXTURE_2D)
        
        return texture_id
    
    def detect_markers(self, frame):
        """Detect ArUco markers in the camera frame"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        corners, ids, rejected = aruco.detectMarkers(gray, ARUCO_DICT, parameters=ARUCO_PARAMS)
        
        if ids is not None and 0 in ids:
            # Find the index of marker ID 0
            idx = np.where(ids == 0)[0][0]
            
            # Get the corners of the marker
            marker_corners = corners[idx][0]
            
            # Calculate transformation matrix
            return self.get_transformation_matrix(marker_corners)
        
        return None
    
    def get_transformation_matrix(self, corners):
        """Calculate transformation matrix from marker corners"""
        # Marker size in OpenGL units
        marker_size = 10.0
        
        # 3D points of the marker in marker coordinate system
        marker_points = np.array([
            [-marker_size/2, 0, marker_size/2],
            [marker_size/2, 0, marker_size/2],
            [marker_size/2, 0, -marker_size/2],
            [-marker_size/2, 0, -marker_size/2]
        ])
        
        # 2D points in image
        image_points = np.array([
            [corners[0][0], corners[0][1]],
            [corners[1][0], corners[1][1]],
            [corners[2][0], corners[2][1]],
            [corners[3][0], corners[3][1]]
        ], dtype=np.float32)
        
        # Camera matrix (approximate values, should be calibrated properly in a real app)
        camera_matrix = np.array([
            [self.width, 0, self.width/2],
            [0, self.width, self.height/2],
            [0, 0, 1]
        ], dtype=np.float32)
        
        # Distortion coefficients (assume no distortion)
        dist_coeffs = np.zeros((4, 1), dtype=np.float32)
        
        # Solve PnP
        _, rvec, tvec = cv2.solvePnP(
            marker_points, image_points, camera_matrix, dist_coeffs
        )
        
        # Convert rotation vector to rotation matrix
        rot_mat, _ = cv2.Rodrigues(rvec)
        
        # Create 4x4 transformation matrix
        transform = np.eye(4, dtype=np.float32)
        transform[:3, :3] = rot_mat
        transform[:3, 3] = tvec.flatten()
        
        return transform
    
    def draw_soccer_field(self):
        """Draw a 3D soccer field"""
        # Enable texture
        glEnable(GL_TEXTURE_2D)
        glBindTexture(GL_TEXTURE_2D, self.field_texture)
        
        # Material properties
        glMaterialfv(GL_FRONT, GL_AMBIENT, (0.2, 0.5, 0.2, 1.0))
        glMaterialfv(GL_FRONT, GL_DIFFUSE, (0.4, 0.8, 0.4, 1.0))
        glMaterialfv(GL_FRONT, GL_SPECULAR, (0.0, 0.0, 0.0, 1.0))
        glMaterialf(GL_FRONT, GL_SHININESS, 0.0)
        
        # Draw field quad
        glBegin(GL_QUADS)
        # Set normal pointing up
        glNormal3f(0, 1, 0)
        
        # Draw field with texture coordinates
        glTexCoord2f(0, 0)
        glVertex3f(-FIELD_WIDTH/2, 0.0, -FIELD_LENGTH/2)
        
        glTexCoord2f(1, 0)
        glVertex3f(FIELD_WIDTH/2, 0.0, -FIELD_LENGTH/2)
        
        glTexCoord2f(1, 1)
        glVertex3f(FIELD_WIDTH/2, 0.0, FIELD_LENGTH/2)
        
        glTexCoord2f(0, 1)
        glVertex3f(-FIELD_WIDTH/2, 0.0, FIELD_LENGTH/2)
        glEnd()
        
        # Disable texture
        glDisable(GL_TEXTURE_2D)
    
    def draw_player(self, x, y, jersey_color):
        """Draw a more detailed player model"""
        glPushMatrix()
        glTranslatef(x, 0, y)
        
        # Player body
        glColor3f(*jersey_color)
        glMaterialfv(GL_FRONT, GL_AMBIENT, (*jersey_color, 1.0))
        glMaterialfv(GL_FRONT, GL_DIFFUSE, (*jersey_color, 1.0))
        
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
    
    def render_scene(self, transform=None):
        """Render the complete scene"""
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        
        if transform is not None:
            glLoadMatrixf(transform.T)
        else:
            glLoadIdentity()
            gluLookAt(0, 5, 10, 0, 0, 0, 0, 1, 0)
        
        # Draw field
        self.draw_soccer_field()
        
        # Draw players
        for pos in self.player_positions:
            self.draw_player(*pos)
        
        # Draw ball
        self.draw_ball()
        
        # Draw effects
        self.draw_effects()
        
        # Update animation
        self.animation_time += 0.016
        self.game_time += 0.016
        
        # Update ball physics
        self.update_ball_physics()
        
        pygame.display.flip()
    
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
    
    def handle_events(self):
        """Handle user input events"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                elif event.key == pygame.K_a:
                    self.ar_mode = not self.ar_mode
                elif event.key == pygame.K_c:
                    self.camera_index = (self.camera_index + 1) % 3
                    self.init_camera()
                elif event.key == pygame.K_SPACE:
                    # Kick ball
                    self.ball_vel = [
                        random.uniform(-0.5, 0.5),
                        random.uniform(0.2, 0.5),
                        random.uniform(-0.5, 0.5)
                    ]
        
        # Handle continuous key presses
        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT]:
            glRotatef(1, 0, 1, 0)
        if keys[pygame.K_RIGHT]:
            glRotatef(-1, 0, 1, 0)
        if keys[pygame.K_UP]:
            glRotatef(1, 1, 0, 0)
        if keys[pygame.K_DOWN]:
            glRotatef(-1, 1, 0, 0)
        if keys[pygame.K_PLUS] or keys[pygame.K_EQUALS]:
            glScalef(1.01, 1.01, 1.01)
        if keys[pygame.K_MINUS]:
            glScalef(0.99, 0.99, 0.99)
    
    def run(self):
        """Main game loop"""
        while self.running:
            self.handle_events()
            
            if self.ar_mode and self.cap is not None:
                ret, frame = self.cap.read()
                if ret:
                    transform = self.detect_markers(frame)
                    self.render_scene(transform)
            else:
                self.render_scene()
            
            self.clock.tick(60)
        
        if self.cap is not None:
            self.cap.release()
        pygame.quit()

if __name__ == "__main__":
    app = ARSoccerExperience()
    app.run() 