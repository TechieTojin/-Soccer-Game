import pygame
import sys
import os
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *
import numpy as np
import math
import random
import cv2
import time

"""
Soccer AR/VR Experience
Developed by Tojin Varkey Simson and Jaiby Mariya Jospeh
A modern soccer game with AR and VR capabilities
"""

class SoccerGame:
    def __init__(self):
        # Initialize Pygame
        pygame.init()
        # Initialize display without OpenGL first
        self.width, self.height = 1280, 720  # Lower resolution
        pygame.display.set_mode((self.width, self.height), pygame.DOUBLEBUF)
        pygame.display.set_caption("Soccer AR/VR Game")
        
        # Game modes
        self.mode = "menu"  # menu, ar, vr, 2d
        self.running = True
        
        # Modern theme colors
        self.colors = {
            'background': (25, 25, 25),
            'accent': (0, 180, 80),
            'text': (255, 255, 255),
            'button': (50, 50, 50),
            'button_hover': (80, 80, 80),
            'field': (0, 120, 0),
            'lines': (255, 255, 255),
            'red': (255, 0, 0),
            'blue': (0, 0, 255),
            'ball': (255, 255, 255)
        }
        
        # Initialize fonts
        self.font_large = pygame.font.Font(None, 72)
        self.font_medium = pygame.font.Font(None, 48)
        self.font_small = pygame.font.Font(None, 36)
        
        # Game state
        self.reset_game_state()
        self.clock = pygame.time.Clock()
        
        # Initialize camera for AR mode
        try:
            self.cap = cv2.VideoCapture(0)
            if not self.cap.isOpened():
                print("Warning: No camera found. AR mode will be disabled.")
                self.ar_available = False
            else:
                self.ar_available = True
        except:
            print("Camera initialization failed. AR mode will be disabled.")
            self.ar_available = False
        
        # Print modern instructions
        print("\n⚽ Soccer AR/VR Game Controls:")
        print("  WASD: Move around the field")
        print("  Arrow keys: Look around")
        print("  Space: Kick ball")
        print("  V: Toggle VR mode")
        print("  A: Toggle AR mode")
        print("  ESC: Exit")
    
    def reset_game_state(self):
        """Initialize or reset game state"""
        self.score = [0, 0]
        self.game_time = 90  # 90-second match
        
        # Ball properties
        self.ball_pos = [self.width//2, self.height//2]
        self.ball_vel = [0, 0]
        self.ball_radius = 8
        self.ball_mass = 1.0
        
        # Players
        self.players = {
            'red': [],   # Team 1 (left)
            'blue': []   # Team 2 (right)
        }
        
        # Create players with initial positions and properties
        for i in range(11):
            # Red team (left)
            self.players['red'].append({
                'pos': [200 + (i % 4) * 100, 150 + (i // 4) * 100],
                'vel': [0, 0],
                'radius': 15,
                'mass': 1.0,
                'speed': 5.0,
                'stamina': 100.0,
                'role': self.get_player_role(i)
            })
            
            # Blue team (right)
            self.players['blue'].append({
                'pos': [self.width - 200 - (i % 4) * 100, 150 + (i // 4) * 100],
                'vel': [0, 0],
                'radius': 15,
                'mass': 1.0,
                'speed': 5.0,
                'stamina': 100.0,
                'role': self.get_player_role(i)
            })
        
        # Player control
        self.selected_team = 'red'
        self.selected_player = 0
        self.player_speed = 5
        self.ball_speed = 15
        self.friction = 0.95
        self.air_resistance = 0.99
        self.gravity = 0.2
        
        # Game physics
        self.last_update = time.time()
        self.dt = 0.016  # Target time step (60 FPS)
    
    def get_player_role(self, index):
        """Assign player roles based on position"""
        roles = {
            0: "GK",  # Goalkeeper
            1: "LB",  # Left Back
            2: "CB",  # Center Back
            3: "CB",  # Center Back
            4: "RB",  # Right Back
            5: "LM",  # Left Midfielder
            6: "CM",  # Center Midfielder
            7: "CM",  # Center Midfielder
            8: "RM",  # Right Midfielder
            9: "ST",  # Striker
            10: "ST"  # Striker
        }
        return roles.get(index, "UNK")
    
    def draw_menu(self):
        """Draw the modern main menu"""
        # Clear screen
        self.display = pygame.display.get_surface()
        self.display.fill(self.colors['background'])
        
        # Draw title
        title = self.font_large.render("Soccer AR/VR Game", True, self.colors['accent'])
        title_rect = title.get_rect(center=(self.width/2, 150))
        self.display.blit(title, title_rect)
        
        # Draw buttons
        buttons = [
            ("2D Soccer Game", self.width/2, 300),
            ("3D Field", self.width/2, 400),
            ("AR Experience", self.width/2, 500),
            ("VR Experience", self.width/2, 600)
        ]
        
        mouse_pos = pygame.mouse.get_pos()
        
        for text, x, y in buttons:
            # Check if mouse is over button
            hover = (x - 150 <= mouse_pos[0] <= x + 150 and 
                    y - 30 <= mouse_pos[1] <= y + 30)
            
            # Draw button
            color = self.colors['button_hover'] if hover else self.colors['button']
            pygame.draw.rect(self.display, color, 
                           (x - 150, y - 30, 300, 60), border_radius=10)
            
            # Draw button text
            text_surface = self.font_medium.render(text, True, self.colors['text'])
            text_rect = text_surface.get_rect(center=(x, y))
            self.display.blit(text_surface, text_rect)
            
            # Handle click
            if hover and pygame.mouse.get_pressed()[0]:
                if text == "2D Soccer Game":
                    self.mode = "2d_game"
                    self.reset_game_state()
                elif text == "3D Field":
                    self.mode = "3d_simple"
                elif text == "AR Experience":
                    if self.ar_available:
                        self.mode = "ar"
                    else:
                        self.show_message("Camera not available")
                elif text == "VR Experience":
                    self.mode = "vr_simple"
    
    def show_message(self, message, duration=2000):
        """Show a message on screen"""
        start_time = pygame.time.get_ticks()
        while pygame.time.get_ticks() - start_time < duration:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                    return
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    return
            
            self.display.fill(self.colors['background'])
            msg = self.font_medium.render(message, True, self.colors['text'])
            msg_rect = msg.get_rect(center=(self.width/2, self.height/2))
            self.display.blit(msg, msg_rect)
            pygame.display.flip()
            self.clock.tick(60)
    
    def handle_events(self):
        """Handle pygame events"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if self.mode != "menu":
                        self.mode = "menu"
                    else:
                        self.running = False
                elif self.mode == "2d_game":
                    if event.key == pygame.K_SPACE:
                        self.handle_ball_kick()
                    elif event.key == pygame.K_TAB:
                        self.selected_team = 'blue' if self.selected_team == 'red' else 'red'
                    elif pygame.K_1 <= event.key <= pygame.K_9:
                        player_num = event.key - pygame.K_1
                        if player_num < 11:
                            self.selected_player = player_num
    
    def handle_ball_kick(self):
        """Handle ball kicking with more realistic physics"""
        player = self.players[self.selected_team][self.selected_player]
        dx = self.ball_pos[0] - player['pos'][0]
        dy = self.ball_pos[1] - player['pos'][1]
        dist = math.sqrt(dx*dx + dy*dy)
        
        # Only kick if close enough
        if dist < player['radius'] + self.ball_radius + 20:
            # Calculate kick power based on player's stamina and role
            power_multiplier = 1.0
            if player['role'] in ['ST', 'CM']:
                power_multiplier = 1.2
            elif player['role'] == 'GK':
                power_multiplier = 1.5
            
            # Calculate kick direction and power
            angle = math.atan2(dy, dx)
            power = player['stamina'] / 100.0 * power_multiplier
            
            # Apply kick force
            self.ball_vel[0] = math.cos(angle) * self.ball_speed * power
            self.ball_vel[1] = math.sin(angle) * self.ball_speed * power
            
            # Add some randomness based on player's stamina
            randomness = (100 - player['stamina']) / 100.0
            self.ball_vel[0] += random.uniform(-2, 2) * randomness
            self.ball_vel[1] += random.uniform(-2, 2) * randomness
            
            # Reduce player's stamina
            player['stamina'] = max(0, player['stamina'] - 10)
    
    def update_game_state(self):
        """Update game physics and state with more realistic movement"""
        current_time = time.time()
        self.dt = min(current_time - self.last_update, 0.1)  # Cap dt to prevent large jumps
        self.last_update = current_time
        
        # Update selected player position based on keyboard input
        keys = pygame.key.get_pressed()
        player = self.players[self.selected_team][self.selected_player]
        
        # Calculate movement direction
        move_x = keys[pygame.K_RIGHT] - keys[pygame.K_LEFT]
        move_y = keys[pygame.K_DOWN] - keys[pygame.K_UP]
        
        # Normalize diagonal movement
        if move_x != 0 and move_y != 0:
            move_x *= 0.7071  # 1/sqrt(2)
            move_y *= 0.7071
        
        # Apply movement with stamina effect
        speed_multiplier = player['stamina'] / 100.0
        player['vel'][0] = move_x * self.player_speed * speed_multiplier
        player['vel'][1] = move_y * self.player_speed * speed_multiplier
        
        # Update player position
        player['pos'][0] += player['vel'][0] * self.dt * 60
        player['pos'][1] += player['vel'][1] * self.dt * 60
        
        # Keep player in bounds
        player['pos'][0] = max(0, min(self.width, player['pos'][0]))
        player['pos'][1] = max(0, min(self.height, player['pos'][1]))
        
        # Regenerate stamina when not moving
        if move_x == 0 and move_y == 0:
            player['stamina'] = min(100, player['stamina'] + 0.5)
        
        # Update ball physics
        self.update_ball_physics()
        
        # Check for goals
        self.check_goals()
        
        # Update game time
        if self.game_time > 0:
            self.game_time -= self.dt
    
    def update_ball_physics(self):
        """Update ball physics with more realistic movement"""
        # Apply gravity
        self.ball_vel[1] += self.gravity * self.dt * 60
        
        # Apply air resistance
        self.ball_vel[0] *= self.air_resistance
        self.ball_vel[1] *= self.air_resistance
        
        # Update ball position
        self.ball_pos[0] += self.ball_vel[0] * self.dt * 60
        self.ball_pos[1] += self.ball_vel[1] * self.dt * 60
        
        # Ball collision with walls
        if self.ball_pos[0] < self.ball_radius or self.ball_pos[0] > self.width - self.ball_radius:
            self.ball_vel[0] *= -0.8
            self.ball_pos[0] = max(self.ball_radius, min(self.width - self.ball_radius, self.ball_pos[0]))
        
        if self.ball_pos[1] < self.ball_radius or self.ball_pos[1] > self.height - self.ball_radius:
            self.ball_vel[1] *= -0.8
            self.ball_pos[1] = max(self.ball_radius, min(self.height - self.ball_radius, self.ball_pos[1]))
        
        # Ball collision with players
        for team in ['red', 'blue']:
            for player in self.players[team]:
                dx = self.ball_pos[0] - player['pos'][0]
                dy = self.ball_pos[1] - player['pos'][1]
                dist = math.sqrt(dx*dx + dy*dy)
                
                if dist < player['radius'] + self.ball_radius:
                    # Calculate collision response
                    normal_x = dx / dist
                    normal_y = dy / dist
                    
                    # Calculate relative velocity
                    relative_vel_x = self.ball_vel[0] - player['vel'][0]
                    relative_vel_y = self.ball_vel[1] - player['vel'][1]
                    
                    # Calculate impulse
                    impulse = 2.0 * (relative_vel_x * normal_x + relative_vel_y * normal_y)
                    impulse /= (1.0/self.ball_mass + 1.0/player['mass'])
                    
                    # Apply impulse
                    self.ball_vel[0] -= impulse * normal_x / self.ball_mass
                    self.ball_vel[1] -= impulse * normal_y / self.ball_mass
                    
                    # Move ball out of collision
                    overlap = (player['radius'] + self.ball_radius - dist) * 1.1
                    self.ball_pos[0] += normal_x * overlap
                    self.ball_pos[1] += normal_y * overlap
    
    def check_goals(self):
        """Check for goals with more realistic detection"""
        goal_height = 100
        goal_width = 20
        
        if (self.ball_pos[1] > self.height/2 - goal_height/2 and 
            self.ball_pos[1] < self.height/2 + goal_height/2):
            
            # Left goal
            if (self.ball_pos[0] < goal_width and 
                self.ball_vel[0] < 0):  # Ball must be moving towards goal
                self.score[1] += 1
                self.reset_ball()
                self.show_goal_message("Blue Team Scores!")
            
            # Right goal
            elif (self.ball_pos[0] > self.width - goal_width and 
                  self.ball_vel[0] > 0):  # Ball must be moving towards goal
                self.score[0] += 1
                self.reset_ball()
                self.show_goal_message("Red Team Scores!")
    
    def show_goal_message(self, message):
        """Show goal celebration message"""
        self.show_message(message, 1000)
    
    def reset_ball(self):
        """Reset ball to center after goal"""
        self.ball_pos = [self.width//2, self.height//2]
        self.ball_vel = [0, 0]
        
        # Reset all players to their initial positions
        for team in ['red', 'blue']:
            for i, player in enumerate(self.players[team]):
                if team == 'red':
                    player['pos'] = [200 + (i % 4) * 100, 150 + (i // 4) * 100]
                else:
                    player['pos'] = [self.width - 200 - (i % 4) * 100, 150 + (i // 4) * 100]
                player['vel'] = [0, 0]
    
    def draw_2d_game(self):
        """Draw the interactive 2D soccer game with more details"""
        self.display = pygame.display.get_surface()
        self.display.fill(self.colors['field'])
        
        # Draw field lines
        self.draw_field_lines()
        
        # Draw goals
        self.draw_goals()
        
        # Draw players
        self.draw_players()
        
        # Draw ball
        self.draw_ball()
        
        # Draw UI elements
        self.draw_ui()
        
        # Show game over message if time is up
        if self.game_time <= 0:
            self.show_game_over()
    
    def draw_field_lines(self):
        """Draw soccer field lines"""
        # Field outline
        pygame.draw.rect(self.display, self.colors['lines'], 
                        (100, 100, self.width-200, self.height-200), 2)
        
        # Center circle
        pygame.draw.circle(self.display, self.colors['lines'], 
                         (self.width//2, self.height//2), 70, 2)
        
        # Center line
        pygame.draw.line(self.display, self.colors['lines'], 
                        (self.width//2, 100), (self.width//2, self.height-100), 2)
        
        # Penalty areas
        penalty_width = 200
        penalty_height = 100
        pygame.draw.rect(self.display, self.colors['lines'], 
                        (100, self.height//2-penalty_height//2, penalty_width, penalty_height), 2)
        pygame.draw.rect(self.display, self.colors['lines'], 
                        (self.width-100-penalty_width, self.height//2-penalty_height//2, 
                         penalty_width, penalty_height), 2)
    
    def draw_goals(self):
        """Draw goals with nets"""
        goal_height = 100
        goal_width = 20
        
        # Left goal
        pygame.draw.rect(self.display, self.colors['lines'], 
                        (80, self.height//2-goal_height//2, goal_width, goal_height), 2)
        
        # Right goal
        pygame.draw.rect(self.display, self.colors['lines'], 
                        (self.width-100, self.height//2-goal_height//2, goal_width, goal_height), 2)
    
    def draw_players(self):
        """Draw players with their roles and stamina"""
        for team, color in [('red', self.colors['red']), ('blue', self.colors['blue'])]:
            for i, player in enumerate(self.players[team]):
                # Draw player
                pygame.draw.circle(self.display, color, 
                                 [int(player['pos'][0]), int(player['pos'][1])], 
                                 player['radius'])
                
                # Draw player role
                role_text = self.font_small.render(player['role'], True, self.colors['text'])
                role_rect = role_text.get_rect(center=(player['pos'][0], player['pos'][1]))
                self.display.blit(role_text, role_rect)
                
                # Draw stamina bar
                stamina_width = 30
                stamina_height = 4
                stamina_x = player['pos'][0] - stamina_width//2
                stamina_y = player['pos'][1] - player['radius'] - 8
                
                # Background
                pygame.draw.rect(self.display, (50, 50, 50), 
                               (stamina_x, stamina_y, stamina_width, stamina_height))
                
                # Stamina level
                stamina_level = int(stamina_width * player['stamina'] / 100)
                stamina_color = (0, 255, 0) if player['stamina'] > 50 else (255, 255, 0) if player['stamina'] > 25 else (255, 0, 0)
                pygame.draw.rect(self.display, stamina_color, 
                               (stamina_x, stamina_y, stamina_level, stamina_height))
                
                # Highlight selected player
                if team == self.selected_team and i == self.selected_player:
                    pygame.draw.circle(self.display, (255, 255, 0), 
                                     [int(player['pos'][0]), int(player['pos'][1])], 
                                     player['radius'] + 2, 2)
    
    def draw_ball(self):
        """Draw ball with shadow"""
        # Draw shadow
        shadow_offset = 3
        pygame.draw.circle(self.display, (0, 0, 0, 128), 
                         [int(self.ball_pos[0] + shadow_offset), 
                          int(self.ball_pos[1] + shadow_offset)], 
                         self.ball_radius)
        
        # Draw ball
        pygame.draw.circle(self.display, self.colors['ball'], 
                         [int(self.ball_pos[0]), int(self.ball_pos[1])], 
                         self.ball_radius)
    
    def draw_ui(self):
        """Draw game UI elements"""
        # Score and time
        score_text = self.font_medium.render(f"{self.score[0]} - {self.score[1]}", 
                                           True, self.colors['text'])
        time_text = self.font_medium.render(f"Time: {int(self.game_time)}s", 
                                          True, self.colors['text'])
        
        # Controls
        controls = [
            "Arrow keys: Move player",
            "Space: Kick ball",
            "Tab: Switch teams",
            "1-9: Select player",
            "ESC: Menu"
        ]
        
        # Draw score and time
        self.display.blit(score_text, (self.width//2 - 40, 20))
        self.display.blit(time_text, (self.width//2 - 60, 60))
        
        # Draw controls
        for i, control in enumerate(controls):
            control_text = self.font_small.render(control, True, self.colors['text'])
            self.display.blit(control_text, (20, self.height - 30 - i * 25))
    
    def show_game_over(self):
        """Show game over screen with more details"""
        overlay = pygame.Surface((self.width, self.height))
        overlay.set_alpha(128)
        overlay.fill((0, 0, 0))
        self.display.blit(overlay, (0, 0))
        
        # Determine winner
        if self.score[0] > self.score[1]:
            winner = "Red Team Wins!"
            winner_color = self.colors['red']
        elif self.score[1] > self.score[0]:
            winner = "Blue Team Wins!"
            winner_color = self.colors['blue']
        else:
            winner = "It's a Draw!"
            winner_color = self.colors['text']
        
        # Draw game over text
        game_over_text = self.font_large.render("Game Over!", True, self.colors['text'])
        winner_text = self.font_medium.render(winner, True, winner_color)
        score_text = self.font_medium.render(f"Final Score: {self.score[0]} - {self.score[1]}", 
                                           True, self.colors['text'])
        restart_text = self.font_small.render("Press ESC to return to menu", True, self.colors['text'])
        
        # Position and draw text
        self.display.blit(game_over_text, 
                         game_over_text.get_rect(center=(self.width//2, self.height//2-100)))
        self.display.blit(winner_text, 
                         winner_text.get_rect(center=(self.width//2, self.height//2-20)))
        self.display.blit(score_text, 
                         score_text.get_rect(center=(self.width//2, self.height//2+40)))
        self.display.blit(restart_text, 
                         restart_text.get_rect(center=(self.width//2, self.height//2+100)))
    
    def run(self):
        """Main game loop"""
        while self.running:
            self.handle_events()
            
            if self.mode == "menu":
                self.draw_menu()
            elif self.mode == "2d_game":
                if self.game_time > 0:
                    self.update_game_state()
                self.draw_2d_game()
            elif self.mode == "3d_simple":
                self.show_message("3D field visualization (without OpenGL)")
                self.mode = "menu"
            elif self.mode == "vr_simple":
                self.show_message("VR mode (without VR glasses)")
                self.mode = "menu"
            elif self.mode == "ar":
                if self.ar_available:
                    self.show_message("AR mode requires camera setup")
                else:
                    self.show_message("Camera not available")
                self.mode = "menu"
            
            pygame.display.flip()
            self.clock.tick(60)
        
        # Cleanup
        if hasattr(self, 'cap') and self.cap is not None and self.ar_available:
            self.cap.release()
        pygame.quit()

if __name__ == "__main__":
    game = SoccerGame()
    game.run() 