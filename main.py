import pygame
import sys
import os

# Initialize pygame
pygame.init()

# Screen dimensions
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Game Interface")

# Colors
BUTTON_COLOR = (86, 98, 246)
BUTTON_HOVER = (108, 119, 252)
BUTTON_TEXT = (255, 255, 255)
TEXT_COLOR = (220, 220, 220)

# Font
font = pygame.font.SysFont("Arial", 32)
small_font = pygame.font.SysFont("Arial", 24)

# Load and scale background image to fill the entire screen
try:
    background_image = pygame.image.load("Data\\Images\\Front.jpg")
    # Scale the image to fit the screen dimensions
    background_image = pygame.transform.scale(background_image, (WIDTH, HEIGHT))
    image_loaded = True
except:
    # Fallback to solid color if image loading fails
    background_image = pygame.Surface((WIDTH, HEIGHT))
    background_image.fill((40, 44, 52))
    image_loaded = False
    print("Background image not found. Using solid color background.")

# Create a semi-transparent overlay for better button visibility
overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
overlay.fill((0, 0, 0, 128))  # Black with 50% transparency

# Button class
class Button:
    def __init__(self, x, y, width, height, text):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.is_hovered = False
        
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
button1 = Button(WIDTH//2 - 150, HEIGHT - 120, 140, 50, "Start Game")
button2 = Button(WIDTH//2 + 10, HEIGHT - 120, 140, 50, "Settings")

# Main game loop
clock = pygame.time.Clock()
running = True

while running:
    mouse_pos = pygame.mouse.get_pos()
    
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
            
        # Check for button clicks
        if button1.is_clicked(mouse_pos, event):
            print("Start Game button clicked!")
            
        if button2.is_clicked(mouse_pos, event):
            print("Settings button clicked!")
    
    # Update button hover states
    button1.check_hover(mouse_pos)
    button2.check_hover(mouse_pos)
    
    # Draw everything
    # Draw background image
    screen.blit(background_image, (0, 0))
    
    # Draw semi-transparent overlay for better text readability
    screen.blit(overlay, (0, 0))
    
    # Draw title with shadow for better visibility
    title = font.render("My Awesome Game", True, TEXT_COLOR)
    title_shadow = font.render("My Awesome Game", True, (0, 0, 0))
    
    # Draw shadow (slightly offset)
    screen.blit(title_shadow, (WIDTH//2 - title.get_width()//2 + 2, 42))
    # Draw main title
    screen.blit(title, (WIDTH//2 - title.get_width()//2, 40))
    
    # Draw buttons
    button1.draw(screen)
    button2.draw(screen)
    
    # Draw footer text with shadow
    footer = small_font.render("Click the buttons to interact with the game", True, (220, 220, 220))
    footer_shadow = small_font.render("Click the buttons to interact with the game", True, (0, 0, 0))
    
    # Draw shadow
    screen.blit(footer_shadow, (WIDTH//2 - footer.get_width()//2 + 1, HEIGHT - 49))
    # Draw main text
    screen.blit(footer, (WIDTH//2 - footer.get_width()//2, HEIGHT - 50))
    
    pygame.display.flip()
    clock.tick(60)

pygame.quit()
sys.exit()