import numpy as np
import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *
import matplotlib.pyplot as plt
from PIL import Image
import os
import sys

# Constants for the soccer field
FIELD_WIDTH = 105.0  # standard soccer field width in meters
FIELD_LENGTH = 68.0  # standard soccer field length in meters

def draw_soccer_field():
    """Draw a simple 3D soccer field"""
    glBegin(GL_QUADS)
    # Field (green)
    glColor3f(0.1, 0.5, 0.1)  # Darker green
    glVertex3f(-FIELD_WIDTH/2, 0.0, -FIELD_LENGTH/2)
    glVertex3f(FIELD_WIDTH/2, 0.0, -FIELD_LENGTH/2)
    glVertex3f(FIELD_WIDTH/2, 0.0, FIELD_LENGTH/2)
    glVertex3f(-FIELD_WIDTH/2, 0.0, FIELD_LENGTH/2)
    glEnd()
    
    # Draw field lines (white)
    glBegin(GL_LINES)
    glColor3f(1.0, 1.0, 1.0)  # White
    
    # Outline
    glVertex3f(-FIELD_WIDTH/2, 0.01, -FIELD_LENGTH/2)
    glVertex3f(FIELD_WIDTH/2, 0.01, -FIELD_LENGTH/2)
    
    glVertex3f(FIELD_WIDTH/2, 0.01, -FIELD_LENGTH/2)
    glVertex3f(FIELD_WIDTH/2, 0.01, FIELD_LENGTH/2)
    
    glVertex3f(FIELD_WIDTH/2, 0.01, FIELD_LENGTH/2)
    glVertex3f(-FIELD_WIDTH/2, 0.01, FIELD_LENGTH/2)
    
    glVertex3f(-FIELD_WIDTH/2, 0.01, FIELD_LENGTH/2)
    glVertex3f(-FIELD_WIDTH/2, 0.01, -FIELD_LENGTH/2)
    
    # Middle line
    glVertex3f(-FIELD_WIDTH/2, 0.01, 0)
    glVertex3f(FIELD_WIDTH/2, 0.01, 0)
    
    # Center circle (approximated with straight lines)
    radius = 9.15  # standard center circle radius
    segments = 24
    for i in range(segments):
        angle1 = 2 * np.pi * i / segments
        angle2 = 2 * np.pi * (i + 1) / segments
        glVertex3f(radius * np.cos(angle1), 0.01, radius * np.sin(angle1))
        glVertex3f(radius * np.cos(angle2), 0.01, radius * np.sin(angle2))
    
    glEnd()

def draw_player(x, y, jersey_color=(1.0, 0.0, 0.0)):
    """Draw a simple player representation"""
    glPushMatrix()
    glTranslatef(x, 1.0, y)  # Position player on the field (1m tall)
    
    # Body (cylinder)
    glColor3f(*jersey_color)
    quad = gluNewQuadric()
    gluCylinder(quad, 0.5, 0.5, 1.5, 20, 20)  # Player body
    
    # Head (sphere)
    glTranslatef(0, 0, 1.8)
    glColor3f(0.8, 0.6, 0.4)  # Skin color
    quad = gluNewQuadric()
    gluSphere(quad, 0.3, 20, 20)  # Player head
    
    glPopMatrix()

def main():
    # Setup paths - adjust based on where you extracted the barcelona dataset
    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(base_dir, 'barcelona', 'barcelona')
    
    if not os.path.exists(data_dir):
        print(f"Error: Data directory not found: {data_dir}")
        print("Please make sure you've downloaded and extracted the barcelona.zip file")
        sys.exit(1)
        
    # Initialize pygame and OpenGL
    pygame.init()
    display = (800, 600)
    pygame.display.set_mode(display, DOUBLEBUF | OPENGL)
    pygame.display.set_caption("Soccer On Your Tabletop - 3D Viewer")
    
    # Setup OpenGL
    glEnable(GL_DEPTH_TEST)
    glMatrixMode(GL_PROJECTION)
    gluPerspective(45, (display[0] / display[1]), 0.1, 150.0)
    
    # Set the camera position
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()
    gluLookAt(0, 50, 0,  # Eye position (high above the field)
              0, 0, 0,   # Look at center of field
              0, 0, 1)   # Up vector
    
    # Sample player positions (could be derived from the dataset in full implementation)
    player_positions = [
        (-20, 10, (1.0, 0.0, 0.0)),   # Team 1 (red)
        (-15, -5, (1.0, 0.0, 0.0)),
        (-5, 15, (1.0, 0.0, 0.0)),
        (10, 5, (1.0, 0.0, 0.0)),
        (20, -10, (1.0, 0.0, 0.0)),
        (-18, -20, (0.0, 0.0, 1.0)),  # Team 2 (blue)
        (-8, -12, (0.0, 0.0, 1.0)),
        (0, -18, (0.0, 0.0, 1.0)),
        (12, -8, (0.0, 0.0, 1.0)),
        (22, -5, (0.0, 0.0, 1.0))
    ]
    
    # Ball position
    ball_position = [0, 0]
    
    # Rotation and translation variables
    rot_x, rot_y, rot_z = 0, 0, 0
    trans_z = -5
    
    clock = pygame.time.Clock()
    
    print("Soccer 3D Viewer - Controls:")
    print("  Arrow keys: Rotate view")
    print("  W/S: Zoom in/out")
    print("  ESC: Quit")
    
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                return
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    return
        
        # Handle continuous key presses
        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT]:
            rot_y += 1
        if keys[pygame.K_RIGHT]:
            rot_y -= 1
        if keys[pygame.K_UP]:
            rot_x += 1
        if keys[pygame.K_DOWN]:
            rot_x -= 1
        if keys[pygame.K_w]:
            trans_z += 1
        if keys[pygame.K_s]:
            trans_z -= 1
        
        # Clear the screen
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        
        # Apply transformations
        glLoadIdentity()
        glTranslatef(0, 0, trans_z)
        glRotatef(rot_x, 1, 0, 0)
        glRotatef(rot_y, 0, 1, 0)
        glRotatef(rot_z, 0, 0, 1)
        
        # Draw the scene
        draw_soccer_field()
        
        # Draw players
        for pos in player_positions:
            draw_player(pos[0], pos[1], pos[2])
        
        # Draw ball (simple white sphere)
        glPushMatrix()
        glTranslatef(ball_position[0], 0.5, ball_position[1])
        glColor3f(1.0, 1.0, 1.0)  # White
        quad = gluNewQuadric()
        gluSphere(quad, 0.2, 20, 20)  # Ball
        glPopMatrix()
        
        # Update display
        pygame.display.flip()
        clock.tick(60)  # 60 FPS

if __name__ == "__main__":
    main() 