import pygame
import sys
import os

# Initialize pygame
pygame.init()

# Screen dimensions
WIDTH, HEIGHT = 800, 600
# Create resizable window
screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
pygame.display.set_caption("Game Interface - Press F11 for Fullscreen")

# Colors
BUTTON_COLOR = (86, 98, 246)
BUTTON_HOVER = (108, 119, 252)
BUTTON_TEXT = (255, 255, 255)
TEXT_COLOR = (220, 220, 220)

# Font
font = pygame.font.SysFont("Arial", 32)
small_font = pygame.font.SysFont("Arial", 24)

# Load background image
def load_background_image(width, height):
    try:
        background_image = pygame.image.load("Data\\Images\\Front.jpg")
        # Scale the image to fit the current window dimensions
        background_image = pygame.transform.scale(background_image, (width, height))
        return background_image, True
    except:
        # Fallback to solid color if image loading fails
        background_image = pygame.Surface((width, height))
        background_image.fill((40, 44, 52))
        return background_image, False

# Create initial background
background_image, image_loaded = load_background_image(WIDTH, HEIGHT)

# Create overlay function
def create_overlay(width, height):
    overlay = pygame.Surface((width, height), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 128))  # Black with 50% transparency
    return overlay

overlay = create_overlay(WIDTH, HEIGHT)

# Button class
class Button:
    def __init__(self, x, y, width, height, text):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.is_hovered = False
        self.original_pos = (x, y, width, height)
        
    def update_position(self, screen_width, screen_height):
        # Update button position based on screen size
        self.rect.x = screen_width // 2 - 150
        self.rect.y = screen_height - 120
        
    def draw(self, surface):
        color = BUTTON_HOVER if self.is_hovered else BUTTON_COLOR
        pygame.draw.rect(surface, color, self.rect, border_radius=12)
        pygame.draw.rect(surface, (255, 255, 255), self.rect, 2, border_radius=12)
        
        text_surf = font.render(self.text, True, BUTTON_TEXT)
        text_rect = text_surf.get_rect(center=self.rect.center)
        surface.blit(text_surf, text_rect)
        
    def check_hover(self, pos):
        self.is_hovered = self.rect.collidepoint(pos)
        
    def is_clicked(self, pos, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            return self.rect.collidepoint(pos)
        return False

# Create buttons
button1 = Button(WIDTH//2 - 150, HEIGHT - 350, 140, 50, "Sign In")
button2 = Button(WIDTH//2 + 10, HEIGHT - 350, 140, 50, "Sign Up")

# Control buttons for window management
class ControlButton:
    def __init__(self, x, y, width, height, text, color):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.color = color
        self.is_hovered = False
        
    def draw(self, surface):
        color = (min(self.color[0] + 30, 255), 
                 min(self.color[1] + 30, 255), 
                 min(self.color[2] + 30, 255)) if self.is_hovered else self.color
        pygame.draw.rect(surface, color, self.rect, border_radius=6)
        
        text_surf = small_font.render(self.text, True, (255, 255, 255))
        text_rect = text_surf.get_rect(center=self.rect.center)
        surface.blit(text_surf, text_rect)
        
    def check_hover(self, pos):
        self.is_hovered = self.rect.collidepoint(pos)
        
    def is_clicked(self, pos, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            return self.rect.collidepoint(pos)
        return False

# Create control buttons
minimize_btn = ControlButton(WIDTH - 80, 10, 30, 25, "_", (100, 100, 100))
maximize_btn = ControlButton(WIDTH - 45, 10, 30, 25, "□", (100, 100, 100))
close_btn = ControlButton(WIDTH - 15, 10, 25, 25, "x", (200, 60, 60))

# Window state
is_fullscreen = False
original_size = (WIDTH, HEIGHT)

# Main game loop
clock = pygame.time.Clock()
running = True

while running:
    current_width, current_height = screen.get_size()
    mouse_pos = pygame.mouse.get_pos()
    
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
            
        # Handle window resize
        if event.type == pygame.VIDEORESIZE:
            if not is_fullscreen:
                WIDTH, HEIGHT = event.size
                screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
                background_image, image_loaded = load_background_image(WIDTH, HEIGHT)
                overlay = create_overlay(WIDTH, HEIGHT)
                # Update button positions
                button1.update_position(WIDTH, HEIGHT)
                button2.rect.x = WIDTH//2 + 10
                button2.rect.y = HEIGHT - 120
                # Update control buttons position
                minimize_btn.rect.x = WIDTH - 80
                maximize_btn.rect.x = WIDTH - 45
                close_btn.rect.x = WIDTH - 15
            
        # Check for button clicks
        if button1.is_clicked(mouse_pos, event):
            print("Start Game button clicked!")
            
        if button2.is_clicked(mouse_pos, event):
            print("Settings button clicked!")
            
        # Check for control button clicks
        if minimize_btn.is_clicked(mouse_pos, event):
            pygame.display.iconify()  # Minimize window
            
        if maximize_btn.is_clicked(mouse_pos, event):
            if not is_fullscreen:
                # Go to fullscreen
                screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
                is_fullscreen = True
            else:
                # Return to windowed mode
                screen = pygame.display.set_mode(original_size, pygame.RESIZABLE)
                is_fullscreen = False
            # Update background for new size
            current_width, current_height = screen.get_size()
            background_image, image_loaded = load_background_image(current_width, current_height)
            overlay = create_overlay(current_width, current_height)
            
        if close_btn.is_clicked(mouse_pos, event):
            running = False
            
        # Keyboard shortcuts
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_F11:
                if not is_fullscreen:
                    # Go to fullscreen
                    screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
                    is_fullscreen = True
                else:
                    # Return to windowed mode
                    screen = pygame.display.set_mode(original_size, pygame.RESIZABLE)
                    is_fullscreen = False
                # Update background for new size
                current_width, current_height = screen.get_size()
                background_image, image_loaded = load_background_image(current_width, current_height)
                overlay = create_overlay(current_width, current_height)
                
            if event.key == pygame.K_ESCAPE and is_fullscreen:
                # Exit fullscreen with ESC
                screen = pygame.display.set_mode(original_size, pygame.RESIZABLE)
                is_fullscreen = False
                current_width, current_height = screen.get_size()
                background_image, image_loaded = load_background_image(current_width, current_height)
                overlay = create_overlay(current_width, current_height)
    
    # Update button hover states
    button1.check_hover(mouse_pos)
    button2.check_hover(mouse_pos)
    minimize_btn.check_hover(mouse_pos)
    maximize_btn.check_hover(mouse_pos)
    close_btn.check_hover(mouse_pos)
    
    # Draw everything
    # Draw background image
    screen.blit(background_image, (0, 0))
    
    # Draw semi-transparent overlay for better text readability
    screen.blit(overlay, (0, 0))
    
    # Draw main buttons
    button1.draw(screen)
    button2.draw(screen)
    
    # Draw control buttons (only in windowed mode or if specified)
    if not is_fullscreen:
        minimize_btn.draw(screen)
        maximize_btn.draw(screen)
        close_btn.draw(screen)
    
    pygame.display.flip()
    clock.tick(60)

pygame.quit()
sys.exit()