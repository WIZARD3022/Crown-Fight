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
BACKGROUND = (40, 44, 52)
BUTTON_COLOR = (86, 98, 246)
BUTTON_HOVER = (108, 119, 252)
BUTTON_TEXT = (255, 255, 255)
TEXT_COLOR = (220, 220, 220)

# Font
font = pygame.font.SysFont("Arial", 32)
small_font = pygame.font.SysFont("Arial", 24)

# Create a sample image (in a real game, you would load your own image)
# For demonstration, we'll create a placeholder image
# Load your image (make sure the path is correct)
try:
    image_surface = pygame.image.load("Data\Images\Front.jpg")
    # Scale the image if needed
    image_surface = pygame.transform.scale(image_surface, (400, 300))
except:
    # Fallback to placeholder if image loading fails
    image_surface = pygame.Surface((400, 300))
    image_surface.fill((50, 120, 200))
    text = small_font.render("Image Not Found", True, (255, 255, 255))
    text_rect = text.get_rect(center=(200, 150))
    image_surface.blit(text, text_rect)

# image_surface = pygame.Surface((400, 300))
# image_surface.fill((50, 120, 200))
# pygame.draw.rect(image_surface, (30, 80, 160), (10, 10, 380, 280), 5)
# text = small_font.render("Game Image", True, (255, 255, 255))
# text_rect = text.get_rect(center=(200, 150))
# image_surface.blit(text, text_rect)

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
    screen.fill(BACKGROUND)
    
    # Draw title
    title = font.render("My Awesome Game", True, TEXT_COLOR)
    screen.blit(title, (WIDTH//2 - title.get_width()//2, 40))
    
    # Draw image
    screen.blit(image_surface, (WIDTH//2 - image_surface.get_width()//2, 120))
    
    # Draw buttons
    button1.draw(screen)
    button2.draw(screen)
    
    # Draw footer text
    footer = small_font.render("Click the buttons to interact with the game", True, (150, 150, 150))
    screen.blit(footer, (WIDTH//2 - footer.get_width()//2, HEIGHT - 50))
    
    pygame.display.flip()
    clock.tick(60)

pygame.quit()
sys.exit()