import pygame
import sys
import os
import re
from datetime import datetime
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, DuplicateKeyError
import bcrypt
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Initialize pygame
pygame.init()

# Screen dimensions
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
pygame.display.set_caption("Game Authentication System - MongoDB")

# Colors
BUTTON_COLOR = (86, 98, 246)
BUTTON_HOVER = (108, 119, 252)
BUTTON_TEXT = (255, 255, 255)
TEXT_COLOR = (220, 220, 220)
INPUT_COLOR = (50, 50, 50)
INPUT_BORDER = (100, 100, 100)
ERROR_COLOR = (255, 50, 50)
SUCCESS_COLOR = (50, 255, 50)
WARNING_COLOR = (255, 165, 0)

# Font
font = pygame.font.SysFont("Arial", 32)
small_font = pygame.font.SysFont("Arial", 24)
tiny_font = pygame.font.SysFont("Arial", 18)

# Get configuration from environment variables
MONGODB_URI = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/')
DATABASE_NAME = os.getenv('DATABASE_NAME', 'game_auth')
SECRET_KEY = os.getenv('SECRET_KEY', 'fallback_secret_key')
DEBUG_MODE = os.getenv('DEBUG_MODE', 'False').lower() == 'true'

print(f"Connecting to MongoDB: {MONGODB_URI}")
print(f"Database: {DATABASE_NAME}")

# Safe print function for Windows console
def safe_print(message):
    """Print messages safely without Unicode emojis for Windows compatibility"""
    try:
        print(message)
    except UnicodeEncodeError:
        # Replace Unicode characters with ASCII equivalents
        safe_message = message.encode('ascii', 'replace').decode('ascii')
        print(safe_message)

# MongoDB Configuration
class MongoDB:
    def __init__(self, connection_string=MONGODB_URI, db_name=DATABASE_NAME):
        self.client = None
        self.db = None
        self.users_collection = None
        self.connection_string = connection_string
        self.db_name = db_name
        self.connect()
    
    def connect(self):
        try:
            safe_print("Attempting to connect to MongoDB...")
            self.client = MongoClient(self.connection_string, serverSelectionTimeoutMS=10000)
            
            # Test connection with longer timeout
            self.client.server_info()
            self.db = self.client[self.db_name]
            self.users_collection = self.db.users
            safe_print("SUCCESS: Connected to MongoDB!")
            
            # Create unique indexes
            self.users_collection.create_index("username", unique=True)
            self.users_collection.create_index("email", unique=True)
            safe_print("Database indexes created successfully.")
            
        except ConnectionFailure as e:
            safe_print(f"ERROR: Could not connect to MongoDB: {e}")
            safe_print("Please check your connection string and ensure MongoDB is running.")
            self.client = None
        except Exception as e:
            safe_print(f"ERROR: Unexpected error: {e}")
            self.client = None
    
    def is_connected(self):
        try:
            if self.client:
                self.client.server_info()
                return True
        except:
            return False
        return False
    
    def insert_user(self, user_data):
        if not self.is_connected():
            return False, "Database connection failed"
        
        try:
            result = self.users_collection.insert_one(user_data)
            safe_print(f"User created successfully with ID: {result.inserted_id}")
            return True, "Account created successfully!"
        except DuplicateKeyError as e:
            field = "username" if "username" in str(e) else "email"
            safe_print(f"Duplicate key error: {field} already exists")
            return False, f"{field.capitalize()} already exists"
        except Exception as e:
            safe_print(f"Database insertion error: {e}")
            return False, f"Database error: {str(e)}"
    
    def find_user(self, query):
        if not self.is_connected():
            return None
        return self.users_collection.find_one(query)
    
    def get_user_count(self):
        if not self.is_connected():
            return 0
        return self.users_collection.count_documents({})

# Initialize MongoDB
mongo_db = MongoDB()

# Password hashing with bcrypt
def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

def verify_password(password, hashed):
    if isinstance(hashed, str):
        hashed = hashed.encode('utf-8')
    return bcrypt.checkpw(password.encode('utf-8'), hashed)

# Input Box class
class InputBox:
    def __init__(self, x, y, width, height, placeholder='', is_password=False):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = ''
        self.placeholder = placeholder
        self.active = False
        self.is_password = is_password
        self.color = INPUT_COLOR
        self.border_color = INPUT_BORDER
        
    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            self.active = self.rect.collidepoint(event.pos)
            self.border_color = (150, 150, 255) if self.active else INPUT_BORDER
            
        if event.type == pygame.KEYDOWN and self.active:
            if event.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
            elif event.key == pygame.K_RETURN:
                return True
            else:
                self.text += event.unicode
        return False
        
    def draw(self, surface):
        pygame.draw.rect(surface, self.color, self.rect, border_radius=8)
        pygame.draw.rect(surface, self.border_color, self.rect, 2, border_radius=8)
        
        display_text = self.text
        if self.is_password and self.text:
            display_text = '*' * len(self.text)
        elif not self.text and not self.active:
            display_text = self.placeholder
            
        text_surf = small_font.render(display_text, True, TEXT_COLOR)
        text_rect = text_surf.get_rect(midleft=(self.rect.x + 10, self.rect.centery))
        surface.blit(text_surf, text_rect)

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
        
        text_surf = small_font.render(self.text, True, BUTTON_TEXT)
        text_rect = text_surf.get_rect(center=self.rect.center)
        surface.blit(text_surf, text_rect)
        
    def check_hover(self, pos):
        self.is_hovered = self.rect.collidepoint(pos)
        
    def is_clicked(self, pos, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            return self.rect.collidepoint(pos)
        return False

# Authentication functions
def validate_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_password(password):
    return len(password) >= 6

def sign_up(username, email, password, confirm_password):
    if not username or not email or not password:
        return False, "All fields are required"
    
    if not validate_email(email):
        return False, "Invalid email format"
    
    if not validate_password(password):
        return False, "Password must be at least 6 characters"
    
    if password != confirm_password:
        return False, "Passwords do not match"
    
    # Create user document
    user_data = {
        "username": username,
        "email": email,
        "password_hash": hash_password(password),
        "created_at": datetime.utcnow(),
        "last_login": None
    }
    
    return mongo_db.insert_user(user_data)

def sign_in(username, password):
    if not username or not password:
        return False, "All fields are required"
    
    # Find user by username or email
    query = {
        "$or": [
            {"username": username},
            {"email": username}
        ]
    }
    
    user = mongo_db.find_user(query)
    
    if user and verify_password(password, user["password_hash"]):
        # Update last login
        if mongo_db.is_connected():
            try:
                mongo_db.users_collection.update_one(
                    {"_id": user["_id"]},
                    {"$set": {"last_login": datetime.utcnow()}}
                )
                safe_print(f"User {user['username']} logged in successfully")
            except Exception as e:
                safe_print(f"Warning: Could not update last login: {e}")
        return True, f"Welcome back, {user['username']}!"
    else:
        safe_print(f"Failed login attempt for: {username}")
        return False, "Invalid username/email or password"

# Load background image
def load_background_image(width, height):
    try:
        background_image = pygame.image.load("Data\\Images\\Front.jpg")
        background_image = pygame.transform.scale(background_image, (width, height))
        return background_image, True
    except:
        background_image = pygame.Surface((width, height))
        background_image.fill((40, 44, 52))
        return background_image, False

# Create overlay
def create_overlay(width, height):
    overlay = pygame.Surface((width, height), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 180))
    return overlay

# Initialize components
background_image, image_loaded = load_background_image(WIDTH, HEIGHT)
overlay = create_overlay(WIDTH, HEIGHT)

# Game states
STATE_MAIN = "main"
STATE_SIGN_IN = "sign_in"
STATE_SIGN_UP = "sign_up"
current_state = STATE_MAIN

# Input boxes for sign up
signup_username = InputBox(WIDTH//2 - 150, 200, 300, 40, 'Username')
signup_email = InputBox(WIDTH//2 - 150, 260, 300, 40, 'Email')
signup_password = InputBox(WIDTH//2 - 150, 320, 300, 40, 'Password', True)
signup_confirm = InputBox(WIDTH//2 - 150, 380, 300, 40, 'Confirm Password', True)

# Input boxes for sign in
signin_username = InputBox(WIDTH//2 - 150, 200, 300, 40, 'Username or Email')
signin_password = InputBox(WIDTH//2 - 150, 260, 300, 40, 'Password', True)

# Buttons
sign_in_btn = Button(WIDTH//2 - 150, HEIGHT - 300, 140, 50, "Sign In")
sign_up_btn = Button(WIDTH//2 + 10, HEIGHT - 300, 140, 50, "Sign Up")
submit_btn = Button(WIDTH//2 - 75, HEIGHT - 150, 150, 50, "Submit")
back_btn = Button(WIDTH//2 - 75, HEIGHT - 80, 150, 40, "Back")

# Message variables
message_text = ""
message_color = TEXT_COLOR
message_timer = 0

def show_message(text, color=TEXT_COLOR, duration=300):
    global message_text, message_color, message_timer
    message_text = text
    message_color = color
    message_timer = duration

# Main game loop
clock = pygame.time.Clock()
running = True

while running:
    current_width, current_height = screen.get_size()
    mouse_pos = pygame.mouse.get_pos()
    
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        
        # Handle input based on current state
        if current_state == STATE_SIGN_UP:
            if signup_username.handle_event(event):
                pass
            if signup_email.handle_event(event):
                pass
            if signup_password.handle_event(event):
                pass
            if signup_confirm.handle_event(event):
                # Submit on Enter key
                success, message = sign_up(
                    signup_username.text, 
                    signup_email.text, 
                    signup_password.text, 
                    signup_confirm.text
                )
                show_message(message, SUCCESS_COLOR if success else ERROR_COLOR)
                if success:
                    current_state = STATE_MAIN
                    # Clear inputs
                    signup_username.text = signup_email.text = signup_password.text = signup_confirm.text = ""
                    
        elif current_state == STATE_SIGN_IN:
            if signin_username.handle_event(event):
                pass
            if signin_password.handle_event(event):
                # Submit on Enter key
                success, message = sign_in(signin_username.text, signin_password.text)
                show_message(message, SUCCESS_COLOR if success else ERROR_COLOR)
                if success:
                    current_state = STATE_MAIN
                    # Clear inputs
                    signin_username.text = signin_password.text = ""
        
        # Check for button clicks
        if sign_in_btn.is_clicked(mouse_pos, event):
            current_state = STATE_SIGN_IN
            show_message("")  # Clear any previous messages
            
        if sign_up_btn.is_clicked(mouse_pos, event):
            current_state = STATE_SIGN_UP
            show_message("")  # Clear any previous messages
            
        if submit_btn.is_clicked(mouse_pos, event):
            if current_state == STATE_SIGN_UP:
                success, message = sign_up(
                    signup_username.text, 
                    signup_email.text, 
                    signup_password.text, 
                    signup_confirm.text
                )
                show_message(message, SUCCESS_COLOR if success else ERROR_COLOR)
                if success:
                    current_state = STATE_MAIN
                    signup_username.text = signup_email.text = signup_password.text = signup_confirm.text = ""
                    
            elif current_state == STATE_SIGN_IN:
                success, message = sign_in(signin_username.text, signin_password.text)
                show_message(message, SUCCESS_COLOR if success else ERROR_COLOR)
                if success:
                    current_state = STATE_MAIN
                    signin_username.text = signin_password.text = ""
        
        if back_btn.is_clicked(mouse_pos, event):
            current_state = STATE_MAIN
            show_message("")  # Clear any previous messages
    
    # Update hover states
    sign_in_btn.check_hover(mouse_pos)
    sign_up_btn.check_hover(mouse_pos)
    submit_btn.check_hover(mouse_pos)
    back_btn.check_hover(mouse_pos)
    
    # Update message timer
    if message_timer > 0:
        message_timer -= 1
    
    # Draw everything
    screen.blit(background_image, (0, 0))
    screen.blit(overlay, (0, 0))
    
    if current_state == STATE_MAIN:
        # Draw main menu
        title = font.render("Welcome to Game", True, TEXT_COLOR)
        screen.blit(title, (current_width//2 - title.get_width()//2, 100))
        
        sign_in_btn.draw(screen)
        sign_up_btn.draw(screen)
        
    elif current_state == STATE_SIGN_UP:
        # Draw sign up form
        title = font.render("Create Account", True, TEXT_COLOR)
        screen.blit(title, (current_width//2 - title.get_width()//2, 100))
        
        signup_username.draw(screen)
        signup_email.draw(screen)
        signup_password.draw(screen)
        signup_confirm.draw(screen)
        
        submit_btn.draw(screen)
        back_btn.draw(screen)
        
    elif current_state == STATE_SIGN_IN:
        # Draw sign in form
        title = font.render("Sign In", True, TEXT_COLOR)
        screen.blit(title, (current_width//2 - title.get_width()//2, 100))
        
        signin_username.draw(screen)
        signin_password.draw(screen)
        
        submit_btn.draw(screen)
        back_btn.draw(screen)
    
    # Draw message if any
    if message_text and message_timer > 0:
        msg_surf = small_font.render(message_text, True, message_color)
        screen.blit(msg_surf, (current_width//2 - msg_surf.get_width()//2, current_height - 200))
    
    # Draw database status and user count
    db_status = "MongoDB: Connected" if mongo_db.is_connected() else "MongoDB: Disconnected"
    status_color = SUCCESS_COLOR if mongo_db.is_connected() else ERROR_COLOR
    
    status_text = tiny_font.render(db_status, True, status_color)
    screen.blit(status_text, (10, current_height - 50))
    
    if mongo_db.is_connected():
        user_count = mongo_db.get_user_count()
        count_text = tiny_font.render(f"Total Users: {user_count}", True, (150, 150, 150))
        screen.blit(count_text, (10, current_height - 30))
    else:
        # Show connection help message
        help_text = tiny_font.render("Check .env file and MongoDB connection", True, WARNING_COLOR)
        screen.blit(help_text, (10, current_height - 30))
    
    pygame.display.flip()
    clock.tick(60)

# Close MongoDB connection when exiting
if mongo_db.client:
    mongo_db.client.close()
    safe_print("MongoDB connection closed.")

pygame.quit()
sys.exit()