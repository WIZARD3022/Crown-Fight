import pygame
import sys
import os
import re
import random
import string
from datetime import datetime
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, DuplicateKeyError
import bcrypt
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Initialize pygame and mixer for audio
pygame.init()
pygame.mixer.init()

# Screen dimensions
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
pygame.display.set_caption("Game Lobby System")

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
ROOM_COLOR = (70, 130, 180)
ROOM_HOVER = (100, 160, 210)
OPTION_COLOR = (60, 60, 80)
OPTION_HOVER = (80, 80, 100)
OPTION_SELECTED = (100, 150, 200)

# Font
font = pygame.font.SysFont("Arial", 32)
small_font = pygame.font.SysFont("Arial", 24)
tiny_font = pygame.font.SysFont("Arial", 18)
question_font = pygame.font.SysFont("Arial", 20)

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
        self.rooms_collection = None
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
            self.rooms_collection = self.db.rooms
            safe_print("SUCCESS: Connected to MongoDB!")
            
            # Create unique indexes
            self.users_collection.create_index("username", unique=True)
            self.users_collection.create_index("email", unique=True)
            self.rooms_collection.create_index("room_id", unique=True)
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
    
    # Room management methods
    def create_room(self, room_data):
        if not self.is_connected():
            return False, "Database connection failed"
        
        try:
            result = self.rooms_collection.insert_one(room_data)
            safe_print(f"Room created successfully with ID: {result.inserted_id}")
            return True, "Room created successfully!"
        except DuplicateKeyError:
            return False, "Room ID already exists"
        except Exception as e:
            safe_print(f"Room creation error: {e}")
            return False, f"Database error: {str(e)}"
    
    def get_room(self, room_id):
        if not self.is_connected():
            return None
        return self.rooms_collection.find_one({"room_id": room_id})
    
    def get_all_rooms(self):
        if not self.is_connected():
            return []
        return list(self.rooms_collection.find({"is_active": True}))
    
    def update_room(self, room_id, update_data):
        if not self.is_connected():
            return False
        try:
            result = self.rooms_collection.update_one(
                {"room_id": room_id}, 
                {"$set": update_data}
            )
            return result.modified_count > 0
        except Exception as e:
            safe_print(f"Room update error: {e}")
            return False
    
    def delete_room(self, room_id):
        if not self.is_connected():
            return False
        try:
            result = self.rooms_collection.delete_one({"room_id": room_id})
            return result.deleted_count > 0
        except Exception as e:
            safe_print(f"Room deletion error: {e}")
            return False
    
    def update_user_role(self, username, role, character):
        if not self.is_connected():
            return False
        try:
            result = self.users_collection.update_one(
                {"username": username},
                {"$set": {"role": role, "character": character, "last_played": datetime.utcnow()}}
            )
            return result.modified_count > 0
        except Exception as e:
            safe_print(f"User role update error: {e}")
            return False
    
    def get_user_last_room(self, username):
        """Get the last room the user was in"""
        if not self.is_connected():
            return None
        
        # Find rooms where the user is a player and the game hasn't finished
        room = self.rooms_collection.find_one({
            "players": username,
            "is_active": True
        })
        
        return room
    
    def update_player_character_in_room(self, room_id, username, character):
        """Update a player's character in the room"""
        if not self.is_connected():
            return False
        try:
            result = self.rooms_collection.update_one(
                {"room_id": room_id},
                {"$set": {f"player_characters.{username}": character}}
            )
            return result.modified_count > 0
        except Exception as e:
            safe_print(f"Room character update error: {e}")
            return False

# Initialize MongoDB
mongo_db = MongoDB()

# Password hashing with bcrypt
def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

def verify_password(password, hashed):
    if isinstance(hashed, str):
        hashed = hashed.encode('utf-8')
    return bcrypt.checkpw(password.encode('utf-8'), hashed)

# Room ID generation
def generate_room_id():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

# Quiz Questions
QUESTIONS = [
    {
        "question": "In a dangerous forest, a beast blocks your path. What's your instinctive approach?",
        "options": [
            "A) Charge head-on with brute force, relying on raw strength.",
            "B) Protect allies and take the beast's hits while they strike back.",
            "C) Stay hidden, strike quickly, and retreat before it notices.",
            "D) Attack from a distance, taking advantage of range.",
            "E) Distract it with music, spells, or concoctions to support allies.",
            "F) Study its weaknesses, call upon nature, spirits, or elements for aid."
        ],
        "video": "Data/video/q1.mp4"
    },
    {
        "question": "In a group adventure, how do you see your ideal role?",
        "options": [
            "A) The one who deals devastating damage up close.",
            "B) The shield that stands between danger and allies.",
            "C) The unseen force, moving in shadows, striking when least expected.",
            "D) The sniper or tactician, eliminating threats from afar.",
            "E) The heart of the group, keeping morale and health strong.",
            "F) The strategist who bends nature, spirits, or dimensions to their will."
        ],
        "video": "Data/video/q2.mp4"
    },
    {
        "question": "Imagine you've found an ancient, mysterious artifact. What do you do first?",
        "options": [
            "A) Test its strength directly in combat.",
            "B) Secure it safely so no harm comes to others.",
            "C) Study it silently, waiting for the right time to use it.",
            "D) Analyze how it can help from a distance—maybe as a weapon.",
            "E) See if it can heal, buff, or inspire allies.",
            "F) Research deeply into its magical properties, perhaps unlocking hidden powers."
        ],
        "video": "Data/video/q3.mp4"
    },
    {
        "question": "How do you prefer to overcome challenges in life (or battle)?",
        "options": [
            "A) With raw power and relentless offense.",
            "B) By taking hits others cannot and enduring longer.",
            "C) By being unpredictable, swift, and elusive.",
            "D) Through precision, planning, and keeping distance.",
            "E) By uplifting and empowering others.",
            "F) With knowledge, rituals, and commanding forces beyond yourself."
        ],
        "video": "Data/video/q4.mp4"
    },
    {
        "question": "Which statement resonates most with your philosophy?",
        "options": [
            "A) 'Strength and fury carve the path to victory.'",
            "B) 'Protection and duty keep everyone alive.'",
            "C) 'Speed and cunning win fights before they even start.'",
            "D) 'A well-placed strike can change the entire battle.'",
            "E) 'Together we thrive, divided we fall.'",
            "F) 'The world is full of hidden forces—master them, and you master destiny.'"
        ],
        "video": "Data/video/q5.mp4"
    }
]

# Role mapping
ROLE_MAPPING = {
    'A': 'Barbarian / Monk (Melee DPS)',
    'B': 'Fighter/Knight (Tank)',
    'C': 'Rogue / Scout-Ranger (Stealth/Agile)',
    'D': 'Gunman / Ranger (Ranged Physical)',
    'E': 'Bard / Priest / Alchemist (Support/Healing)',
    'F': 'Wizard / Druids / Necromancer / Elementalist / Summoner / Sorcerer / Warlock (Magical Combatants)'
}

# Character images mapping
CHARACTER_IMAGES = {
    'Barbarian / Monk (Melee DPS)': [
        {'name': 'Barbarian', 'path': 'Data/character/logo/barbarian.png'},
        {'name': 'Monk', 'path': 'Data/character/logo/monk.png'}
    ],
    'Fighter/Knight (Tank)': [
        {'name': 'Fighter', 'path': 'Data/character/logo/fighter.png'},
        {'name': 'Knight', 'path': 'Data/character/logo/knight.png'},
    ],
    'Rogue / Scout-Ranger (Stealth/Agile)': [
        {'name': 'Rogue', 'path': 'Data/character/logo/rogue.png'},
        {'name': 'Ranger', 'path': 'Data/character/logo/ranger.png'},
    ],
    'Gunman / Ranger (Ranged Physical)': [
        {'name': 'Gunman', 'path': 'Data/character/logo/gunman.png'},
        {'name': 'Archer', 'path': 'Data/character/logo/archer.png'}
    ],
    'Bard / Priest / Alchemist (Support/Healing)': [
        {'name': 'Bard', 'path': 'Data/character/logo/bard.png'},
        {'name': 'Priest', 'path': 'Data/character/logo/priest.png'},
        {'name': 'Alchemist', 'path': 'Data/character/logo/alchemist.png'}
    ],
    'Wizard / Druids / Necromancer / Elementalist / Summoner / Sorcerer / Warlock (Magical Combatants)': [
        {'name': 'Wizard', 'path': 'Data/character/logo/wizard.png'},
        {'name': 'Druid', 'path': 'Data/character/logo/druid.png'},
        {'name': 'Necromancer', 'path': 'Data/character/logo/necromancer.png'}
    ]
}

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

# Option Button class for quiz
class OptionButton:
    def __init__(self, x, y, width, height, text, option_key):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.option_key = option_key
        self.is_hovered = False
        self.is_selected = False
        
    def draw(self, surface):
        if self.is_selected:
            color = OPTION_SELECTED
        else:
            color = OPTION_HOVER if self.is_hovered else OPTION_COLOR
            
        pygame.draw.rect(surface, color, self.rect, border_radius=8)
        pygame.draw.rect(surface, (255, 255, 255), self.rect, 2, border_radius=8)
        
        # Wrap text if needed
        words = self.text.split(' ')
        lines = []
        current_line = []
        
        for word in words:
            test_line = ' '.join(current_line + [word])
            test_width = question_font.size(test_line)[0]
            if test_width < self.rect.width - 20:
                current_line.append(word)
            else:
                lines.append(' '.join(current_line))
                current_line = [word]
        if current_line:
            lines.append(' '.join(current_line))
        
        # Draw text lines
        for i, line in enumerate(lines):
            text_surf = question_font.render(line, True, TEXT_COLOR)
            text_rect = text_surf.get_rect(midleft=(self.rect.x + 10, self.rect.y + 15 + i * 25))
            surface.blit(text_surf, text_rect)
        
    def check_hover(self, pos):
        self.is_hovered = self.rect.collidepoint(pos)
        
    def is_clicked(self, pos, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(pos):
                self.is_selected = True
                return True
        return False

# Character Selection Button
class CharacterButton:
    def __init__(self, x, y, width, height, character_data):
        self.rect = pygame.Rect(x, y, width, height)
        self.character_data = character_data
        self.is_hovered = False
        self.is_selected = False
        
        # Load image or create placeholder
        try:
            self.image = pygame.image.load(character_data['path'])
            self.image = pygame.transform.scale(self.image, (width - 20, height - 60))
        except:
            # Create placeholder if image not found
            self.image = pygame.Surface((width - 20, height - 60))
            self.image.fill((100, 100, 100))
            text = tiny_font.render(character_data['name'], True, TEXT_COLOR)
            text_rect = text.get_rect(center=(self.image.get_width()//2, self.image.get_height()//2))
            self.image.blit(text, text_rect)
        
    def draw(self, surface):
        if self.is_selected:
            border_color = OPTION_SELECTED
        else:
            border_color = OPTION_HOVER if self.is_hovered else OPTION_COLOR
            
        pygame.draw.rect(surface, border_color, self.rect, border_radius=8)
        pygame.draw.rect(surface, (255, 255, 255), self.rect, 2, border_radius=8)
        
        # Draw image
        surface.blit(self.image, (self.rect.x + 10, self.rect.y + 10))
        
        # Draw character name
        name_text = tiny_font.render(self.character_data['name'], True, TEXT_COLOR)
        name_rect = name_text.get_rect(center=(self.rect.centerx, self.rect.y + self.rect.height - 25))
        surface.blit(name_text, name_rect)
        
    def check_hover(self, pos):
        self.is_hovered = self.rect.collidepoint(pos)
        
    def is_clicked(self, pos, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(pos):
                self.is_selected = True
                return True
        return False

# Room Button class
class RoomButton:
    def __init__(self, x, y, width, height, room_data):
        self.rect = pygame.Rect(x, y, width, height)
        self.room_data = room_data
        self.is_hovered = False
        
    def draw(self, surface):
        color = ROOM_HOVER if self.is_hovered else ROOM_COLOR
        pygame.draw.rect(surface, color, self.rect, border_radius=8)
        pygame.draw.rect(surface, (255, 255, 255), self.rect, 2, border_radius=8)
        
        # Room ID
        room_id_text = small_font.render(f"Room: {self.room_data['room_id']}", True, BUTTON_TEXT)
        surface.blit(room_id_text, (self.rect.x + 10, self.rect.y + 10))
        
        # Creator
        creator_text = tiny_font.render(f"Creator: {self.room_data['creator']}", True, BUTTON_TEXT)
        surface.blit(creator_text, (self.rect.x + 10, self.rect.y + 40))
        
        # Players count
        players_text = tiny_font.render(f"Players: {len(self.room_data.get('players', []))}/4", True, BUTTON_TEXT)
        surface.blit(players_text, (self.rect.x + self.rect.width - 100, self.rect.y + 40))
        
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
        "last_login": None,
        "last_room": None
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
        return True, user
    else:
        safe_print(f"Failed login attempt for: {username}")
        return False, "Invalid username/email or password"

# Room functions
def create_room(creator_username):
    room_id = generate_room_id()
    room_data = {
        "room_id": room_id,
        "creator": creator_username,
        "players": [creator_username],
        "player_characters": {},
        "is_active": True,
        "created_at": datetime.utcnow(),
        "max_players": 4,
        "game_started": False,
        "game_finished": False
    }
    
    success, message = mongo_db.create_room(room_data)
    if success:
        # Update user's last room
        mongo_db.users_collection.update_one(
            {"username": creator_username},
            {"$set": {"last_room": room_id}}
        )
        return True, room_id, message
    else:
        return False, None, message

def join_room(room_id, username):
    room = mongo_db.get_room(room_id)
    if not room:
        return False, "Room not found"
    
    if not room.get("is_active", True):
        return False, "Room is not active"
    
    if username in room.get("players", []):
        return False, "You are already in this room"
    
    if len(room.get("players", [])) >= room.get("max_players", 4):
        return False, "Room is full"
    
    # Add player to room
    update_data = {"players": room.get("players", []) + [username]}
    if mongo_db.update_room(room_id, update_data):
        # Update user's last room
        mongo_db.users_collection.update_one(
            {"username": username},
            {"$set": {"last_room": room_id}}
        )
        return True, f"Joined room {room_id}"
    else:
        return False, "Failed to join room"

# Quiz functions
def calculate_role(answers):
    # Count occurrences of each option
    option_count = {'A': 0, 'B': 0, 'C': 0, 'D': 0, 'E': 0, 'F': 0}
    for answer in answers:
        option_count[answer] += 1
    
    # Find the option with maximum count
    max_option = max(option_count, key=option_count.get)
    max_count = option_count[max_option]
    
    # Check for ties
    tied_options = [opt for opt, count in option_count.items() if count == max_count]
    
    if len(tied_options) > 1:
        # If tie, choose the first one in order A-F
        chosen_option = tied_options[0]
    else:
        chosen_option = max_option
    
    return ROLE_MAPPING[chosen_option]

# Video playback function using Pygame movie (for MPEG-1 videos)
def play_video(video_path):
    try:
        # For MP4 files, we'll use a placeholder since Pygame doesn't natively support MP4
        # In a real implementation, you might need to use a different library or convert videos
        print(f"Attempting to play video: {video_path}")
        
        # Play a sound or show a message instead of actual video
        try:
            # Try to play a beep sound as placeholder
            beep_sound = pygame.mixer.Sound(buffer=bytes([128] * 44100))  # 1 second of silence
            beep_sound.play()
        except:
            pass
            
        return True
    except Exception as e:
        print(f"Video playback error: {e}")
        return False

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
STATE_LOBBY = "lobby"
STATE_CREATE_ROOM = "create_room"
STATE_JOIN_ROOM = "join_room"
STATE_ROOM = "room"
STATE_QUIZ = "quiz"
STATE_ROLE_SELECTION = "role_selection"
STATE_GAME = "game"
STATE_VIDEO = "video"
STATE_CHARACTER_CONFIRM = "character_confirm"
current_state = STATE_MAIN

# Current user and room
current_user = None
current_room = None
available_rooms = []
room_buttons = []

# Quiz variables
current_question = 0
user_answers = []
option_buttons = []
quiz_completed = False

# Role selection variables
user_role = None
character_buttons = []
selected_character = None
selected_character_data = None

# Video playback variables
current_video = None
video_playing = False
video_start_time = 0
video_duration = 5000  # 5 seconds for demo

# My Room variables
my_room_available = False

# Input boxes for sign up
signup_username = InputBox(WIDTH//2 - 150, 200, 300, 40, 'Username')
signup_email = InputBox(WIDTH//2 - 150, 260, 300, 40, 'Email')
signup_password = InputBox(WIDTH//2 - 150, 320, 300, 40, 'Password', True)
signup_confirm = InputBox(WIDTH//2 - 150, 380, 300, 40, 'Confirm Password', True)

# Input boxes for sign in
signin_username = InputBox(WIDTH//2 - 150, 200, 300, 40, 'Username or Email')
signin_password = InputBox(WIDTH//2 - 150, 260, 300, 40, 'Password', True)

# Room ID input
room_id_input = InputBox(WIDTH//2 - 150, 250, 300, 40, 'Enter Room ID')

# Buttons
sign_in_btn = Button(WIDTH//2 - 150, HEIGHT - 300, 140, 50, "Sign In")
sign_up_btn = Button(WIDTH//2 + 10, HEIGHT - 300, 140, 50, "Sign Up")
submit_btn = Button(WIDTH//2 - 75, HEIGHT - 150, 150, 50, "Submit")
back_btn = Button(WIDTH//2 - 75, HEIGHT - 80, 150, 40, "Back")

# Lobby buttons
create_room_btn = Button(WIDTH//2 - 150, HEIGHT - 200, 140, 50, "Create Room")
join_room_btn = Button(WIDTH//2 + 10, HEIGHT - 200, 140, 50, "Join Room")
my_room_btn = Button(WIDTH//2 - 75, HEIGHT - 130, 150, 50, "My Room")
continue_game_btn = Button(WIDTH//2 - 75, HEIGHT - 70, 150, 40, "Continue Game")
logout_btn = Button(WIDTH//2 - 75, HEIGHT - 20, 150, 40, "Logout")

# Room buttons
join_with_id_btn = Button(WIDTH//2 - 150, HEIGHT - 150, 140, 50, "Join with ID")
refresh_rooms_btn = Button(WIDTH//2 + 10, HEIGHT - 150, 140, 50, "Refresh Rooms")

# Room management buttons
start_game_btn = Button(WIDTH//2 - 150, HEIGHT - 150, 140, 50, "Start Game")
leave_room_btn = Button(WIDTH//2 + 10, HEIGHT - 150, 140, 50, "Leave Room")

# Quiz buttons
next_question_btn = Button(WIDTH//2 - 75, HEIGHT - 80, 150, 40, "Next Question")
submit_quiz_btn = Button(WIDTH//2 - 75, HEIGHT - 80, 150, 40, "Submit Quiz")

# Character selection buttons
select_character_btn = Button(WIDTH//2 - 75, HEIGHT - 80, 150, 40, "Select Character")
confirm_character_btn = Button(WIDTH//2 - 75, HEIGHT - 80, 150, 40, "Confirm Character")

# Video buttons
skip_video_btn = Button(WIDTH//2 - 75, HEIGHT - 80, 150, 40, "Skip Video")

# Message variables
message_text = ""
message_color = TEXT_COLOR
message_timer = 0

def show_message(text, color=TEXT_COLOR, duration=300):
    global message_text, message_color, message_timer
    message_text = text
    message_color = color
    message_timer = duration

def refresh_rooms():
    global available_rooms, room_buttons
    available_rooms = mongo_db.get_all_rooms()
    room_buttons = []
    
    for i, room in enumerate(available_rooms):
        y_pos = 150 + (i * 80)
        if y_pos < HEIGHT - 200:  # Don't go beyond screen
            room_buttons.append(RoomButton(WIDTH//2 - 200, y_pos, 400, 70, room))

def initialize_quiz():
    global current_question, user_answers, option_buttons, quiz_completed, current_video, video_playing, video_start_time
    current_question = 0
    user_answers = []
    option_buttons = []
    quiz_completed = False
    current_video = None
    video_playing = False
    video_start_time = 0
    start_video_playback()

def start_video_playback():
    global current_video, video_playing, video_start_time
    if current_question < len(QUESTIONS):
        current_video = QUESTIONS[current_question]["video"]
        video_playing = True
        video_start_time = pygame.time.get_ticks()
        
        # Try to play the video (placeholder implementation)
        play_video(current_video)
        
        create_option_buttons()

def create_option_buttons():
    global option_buttons
    option_buttons = []
    
    if current_question < len(QUESTIONS):
        question_data = QUESTIONS[current_question]
        
        for i, option in enumerate(question_data["options"]):
            y_pos = 200 + (i * 70)
            if y_pos < HEIGHT - 150:
                option_key = option[0]  # Get A, B, C, etc.
                option_buttons.append(OptionButton(WIDTH//2 - 300, y_pos, 600, 60, option, option_key))

def create_character_buttons(role):
    global character_buttons
    character_buttons = []
    
    character_list = CHARACTER_IMAGES.get(role, [])
    
    for i, char_data in enumerate(character_list):
        row = i // 2
        col = i % 2
        x_pos = WIDTH//2 - 200 + (col * 220)
        y_pos = 200 + (row * 180)
        
        character_buttons.append(CharacterButton(x_pos, y_pos, 180, 160, char_data))

def check_my_room_availability():
    global my_room_available
    if current_user and 'last_room' in current_user and current_user['last_room']:
        room = mongo_db.get_room(current_user['last_room'])
        if room and room.get('is_active', True) and current_user['username'] in room.get('players', []):
            my_room_available = True
            return True
    my_room_available = False
    return False

# Main game loop
clock = pygame.time.Clock()
running = True

while running:
    current_width, current_height = screen.get_size()
    mouse_pos = pygame.mouse.get_pos()
    current_time = pygame.time.get_ticks()
    
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
                success, result = sign_in(signin_username.text, signin_password.text)
                if success:
                    current_user = result
                    check_my_room_availability()
                    current_state = STATE_LOBBY
                    show_message(f"Welcome, {current_user['username']}!", SUCCESS_COLOR)
                    # Clear inputs
                    signin_username.text = signin_password.text = ""
                else:
                    show_message(result, ERROR_COLOR)
        
        elif current_state == STATE_JOIN_ROOM:
            if room_id_input.handle_event(event):
                # Join room on Enter key
                success, message = join_room(room_id_input.text, current_user['username'])
                show_message(message, SUCCESS_COLOR if success else ERROR_COLOR)
                if success:
                    current_room = mongo_db.get_room(room_id_input.text)
                    current_state = STATE_ROOM
                    room_id_input.text = ""
            
            # Check room button clicks
            for room_btn in room_buttons:
                if room_btn.is_clicked(mouse_pos, event):
                    success, message = join_room(room_btn.room_data['room_id'], current_user['username'])
                    show_message(message, SUCCESS_COLOR if success else ERROR_COLOR)
                    if success:
                        current_room = room_btn.room_data
                        current_state = STATE_ROOM
        
        elif current_state == STATE_QUIZ:
            # Handle option selection - AUTO ADVANCE when option is selected
            for option_btn in option_buttons:
                if option_btn.is_clicked(mouse_pos, event):
                    # Deselect all other options
                    for btn in option_buttons:
                        if btn != option_btn:
                            btn.is_selected = False
                    # Record the answer
                    if current_question < len(user_answers):
                        user_answers[current_question] = option_btn.option_key
                    else:
                        user_answers.append(option_btn.option_key)
                    
                    # AUTO ADVANCE to next question after a short delay
                    pygame.time.delay(500)  # 0.5 second delay
                    
                    if current_question < len(QUESTIONS) - 1:
                        current_question += 1
                        start_video_playback()
                        current_state = STATE_VIDEO
                    else:
                        # All questions answered
                        quiz_completed = True
                        user_role = calculate_role(user_answers)
                        create_character_buttons(user_role)
                        current_state = STATE_ROLE_SELECTION
                        show_message(f"Your role is: {user_role}. Now choose your character!")
        
        elif current_state == STATE_ROLE_SELECTION:
            # Handle character selection
            for char_btn in character_buttons:
                if char_btn.is_clicked(mouse_pos, event):
                    # Deselect all other characters
                    for btn in character_buttons:
                        if btn != char_btn:
                            btn.is_selected = False
                    selected_character = char_btn.character_data['name']
                    selected_character_data = char_btn.character_data
        
        elif current_state == STATE_VIDEO:
            # Handle video skip
            if skip_video_btn.is_clicked(mouse_pos, event):
                video_playing = False
                current_state = STATE_QUIZ
        
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
                success, result = sign_in(signin_username.text, signin_password.text)
                if success:
                    current_user = result
                    check_my_room_availability()
                    current_state = STATE_LOBBY
                    show_message(f"Welcome, {current_user['username']}!", SUCCESS_COLOR)
                    signin_username.text = signin_password.text = ""
                else:
                    show_message(result, ERROR_COLOR)
        
        if back_btn.is_clicked(mouse_pos, event):
            if current_state in [STATE_SIGN_IN, STATE_SIGN_UP]:
                current_state = STATE_MAIN
            elif current_state in [STATE_CREATE_ROOM, STATE_JOIN_ROOM]:
                current_state = STATE_LOBBY
            elif current_state == STATE_QUIZ:
                # Go back to previous question
                if current_question > 0:
                    current_question -= 1
                    start_video_playback()
                    current_state = STATE_VIDEO
                    # Restore previous selection
                    if current_question < len(user_answers):
                        for btn in option_buttons:
                            btn.is_selected = (btn.option_key == user_answers[current_question])
            elif current_state == STATE_VIDEO:
                if current_question > 0:
                    current_question -= 1
                    start_video_playback()
                else:
                    current_state = STATE_ROOM
            elif current_state == STATE_ROLE_SELECTION:
                current_state = STATE_QUIZ
                current_question = len(QUESTIONS) - 1
                create_option_buttons()
            elif current_state == STATE_CHARACTER_CONFIRM:
                current_state = STATE_ROLE_SELECTION
            show_message("")  # Clear any previous messages
        
        if create_room_btn.is_clicked(mouse_pos, event):
            success, room_id, message = create_room(current_user['username'])
            show_message(message, SUCCESS_COLOR if success else ERROR_COLOR)
            if success:
                current_room = mongo_db.get_room(room_id)
                current_state = STATE_ROOM
        
        if join_room_btn.is_clicked(mouse_pos, event):
            current_state = STATE_JOIN_ROOM
            refresh_rooms()
            show_message("")  # Clear any previous messages
        
        if my_room_btn.is_clicked(mouse_pos, event) and my_room_available:
            if current_user and 'last_room' in current_user:
                room = mongo_db.get_room(current_user['last_room'])
                if room and room.get('is_active', True):
                    # Check if user is still in the room
                    if current_user['username'] in room.get('players', []):
                        current_room = room
                        current_state = STATE_ROOM
                        show_message(f"Rejoined your room: {room['room_id']}")
                    else:
                        # Try to rejoin the room
                        success, message = join_room(current_user['last_room'], current_user['username'])
                        if success:
                            current_room = mongo_db.get_room(current_user['last_room'])
                            current_state = STATE_ROOM
                            show_message(message, SUCCESS_COLOR)
                        else:
                            show_message("Could not rejoin your previous room", ERROR_COLOR)
                else:
                    show_message("Your previous room is no longer available", ERROR_COLOR)
        
        if continue_game_btn.is_clicked(mouse_pos, event):
            if current_user and 'last_room' in current_user:
                room = mongo_db.get_room(current_user['last_room'])
                if room and room.get('is_active', True) and room.get('game_started', False):
                    # Check if user has already completed character selection
                    user_data = mongo_db.find_user({"username": current_user['username']})
                    if user_data and user_data.get('character'):
                        # User has a character, continue to game
                        current_room = room
                        user_role = user_data.get('role')
                        selected_character = user_data.get('character')
                        current_state = STATE_GAME
                        show_message(f"Welcome back to your game! Role: {user_role}, Character: {selected_character}")
                    else:
                        # User needs to complete character selection
                        current_room = room
                        if room.get('game_started', False):
                            # Initialize quiz to continue where they left off
                            initialize_quiz()
                            current_state = STATE_VIDEO
                        else:
                            current_state = STATE_ROOM
                        show_message("Continuing your game...")
                else:
                    show_message("No active game to continue", ERROR_COLOR)
            else:
                show_message("No previous game found", ERROR_COLOR)
        
        if logout_btn.is_clicked(mouse_pos, event):
            current_state = STATE_MAIN
            current_user = None
            show_message("Logged out successfully")
        
        if join_with_id_btn.is_clicked(mouse_pos, event):
            if room_id_input.text:
                success, message = join_room(room_id_input.text, current_user['username'])
                show_message(message, SUCCESS_COLOR if success else ERROR_COLOR)
                if success:
                    current_room = mongo_db.get_room(room_id_input.text)
                    current_state = STATE_ROOM
                    room_id_input.text = ""
            else:
                show_message("Please enter a room ID", ERROR_COLOR)
        
        if refresh_rooms_btn.is_clicked(mouse_pos, event):
            refresh_rooms()
            show_message("Rooms refreshed")
        
        if start_game_btn.is_clicked(mouse_pos, event):
            if current_room and current_room['creator'] == current_user['username']:
                # Start the game for all players in the room
                mongo_db.update_room(current_room['room_id'], {'game_started': True})
                initialize_quiz()
                current_state = STATE_VIDEO
                show_message("Game started! Answer the questions to determine your role.")
        
        if leave_room_btn.is_clicked(mouse_pos, event):
            if current_room:
                # Remove player from room
                if current_user['username'] in current_room.get('players', []):
                    new_players = [p for p in current_room['players'] if p != current_user['username']]
                    mongo_db.update_room(current_room['room_id'], {'players': new_players})
                    
                    # If room is empty, delete it
                    if not new_players:
                        mongo_db.delete_room(current_room['room_id'])
                
                current_room = None
                current_state = STATE_LOBBY
                show_message("Left the room")
        
        if select_character_btn.is_clicked(mouse_pos, event):
            if selected_character:
                current_state = STATE_CHARACTER_CONFIRM
            else:
                show_message("Please select a character", ERROR_COLOR)
        
        if confirm_character_btn.is_clicked(mouse_pos, event):
            if selected_character:
                # Save role and character to database
                if mongo_db.update_user_role(current_user['username'], user_role, selected_character):
                    # Also update the room with the player's character
                    if current_room:
                        mongo_db.update_player_character_in_room(current_room['room_id'], current_user['username'], selected_character)
                    
                    show_message(f"Character {selected_character} selected! Your role is {selected_character}.", SUCCESS_COLOR)
                    current_state = STATE_GAME
                else:
                    show_message("Failed to save character selection", ERROR_COLOR)
            else:
                show_message("Please select a character", ERROR_COLOR)
    
    # Update hover states
    sign_in_btn.check_hover(mouse_pos)
    sign_up_btn.check_hover(mouse_pos)
    submit_btn.check_hover(mouse_pos)
    back_btn.check_hover(mouse_pos)
    create_room_btn.check_hover(mouse_pos)
    join_room_btn.check_hover(mouse_pos)
    my_room_btn.check_hover(mouse_pos)
    continue_game_btn.check_hover(mouse_pos)
    logout_btn.check_hover(mouse_pos)
    join_with_id_btn.check_hover(mouse_pos)
    refresh_rooms_btn.check_hover(mouse_pos)
    start_game_btn.check_hover(mouse_pos)
    leave_room_btn.check_hover(mouse_pos)
    next_question_btn.check_hover(mouse_pos)
    submit_quiz_btn.check_hover(mouse_pos)
    select_character_btn.check_hover(mouse_pos)
    confirm_character_btn.check_hover(mouse_pos)
    skip_video_btn.check_hover(mouse_pos)
    
    for room_btn in room_buttons:
        room_btn.check_hover(mouse_pos)
    
    for option_btn in option_buttons:
        option_btn.check_hover(mouse_pos)
    
    for char_btn in character_buttons:
        char_btn.check_hover(mouse_pos)
    
    # Update message timer
    if message_timer > 0:
        message_timer -= 1
    
    # Refresh room data if in room
    if current_state == STATE_ROOM and current_room:
        updated_room = mongo_db.get_room(current_room['room_id'])
        if updated_room:
            current_room = updated_room
            
            # Auto-start quiz if game started
            if updated_room.get('game_started', False) and current_state not in [STATE_QUIZ, STATE_VIDEO, STATE_ROLE_SELECTION, STATE_CHARACTER_CONFIRM, STATE_GAME]:
                initialize_quiz()
                current_state = STATE_VIDEO
    
    # Handle video playback
    if current_state == STATE_VIDEO and video_playing:
        # Check if video has finished playing
        if current_time - video_start_time >= video_duration:
            video_playing = False
            current_state = STATE_QUIZ
    
    # Check My Room availability
    if current_state == STATE_LOBBY:
        check_my_room_availability()
    
    # Draw everything
    screen.blit(background_image, (0, 0))
    screen.blit(overlay, (0, 0))
    
    if current_state == STATE_MAIN:
        # Draw main menu
        title = font.render("Welcome to Game Lobby", True, TEXT_COLOR)
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
    
    elif current_state == STATE_LOBBY:
        # Draw lobby
        welcome_text = font.render(f"Welcome, {current_user['username']}!", True, TEXT_COLOR)
        screen.blit(welcome_text, (current_width//2 - welcome_text.get_width()//2, 100))
        
        instruction = small_font.render("Choose an option below:", True, TEXT_COLOR)
        screen.blit(instruction, (current_width//2 - instruction.get_width()//2, 160))
        
        create_room_btn.draw(screen)
        join_room_btn.draw(screen)
        
        # Show My Room button if available
        if my_room_available:
            my_room_btn.draw(screen)
            room_info = tiny_font.render(f"Your room: {current_user.get('last_room', 'Unknown')}", True, SUCCESS_COLOR)
            screen.blit(room_info, (current_width//2 - room_info.get_width()//2, HEIGHT - 180))
        else:
            no_room_text = tiny_font.render("No active room to rejoin", True, WARNING_COLOR)
            screen.blit(no_room_text, (current_width//2 - no_room_text.get_width()//2, HEIGHT - 180))
        
        # Show Continue Game button if user has a character
        user_data = mongo_db.find_user({"username": current_user['username']})
        if user_data and user_data.get('character'):
            continue_game_btn.draw(screen)
            continue_info = tiny_font.render(f"Continue as {user_data.get('character')}", True, SUCCESS_COLOR)
            screen.blit(continue_info, (current_width//2 - continue_info.get_width()//2, HEIGHT - 130))
        
        logout_btn.draw(screen)
    
    elif current_state == STATE_JOIN_ROOM:
        # Draw join room interface
        title = font.render("Join a Room", True, TEXT_COLOR)
        screen.blit(title, (current_width//2 - title.get_width()//2, 80))
        
        # Room ID input
        room_id_label = small_font.render("Enter Room ID:", True, TEXT_COLOR)
        screen.blit(room_id_label, (current_width//2 - 150, 220))
        room_id_input.draw(screen)
        join_with_id_btn.draw(screen)
        
        # Available rooms
        rooms_label = small_font.render("Available Rooms:", True, TEXT_COLOR)
        screen.blit(rooms_label, (current_width//2 - rooms_label.get_width()//2, 320))
        
        for room_btn in room_buttons:
            room_btn.draw(screen)
        
        refresh_rooms_btn.draw(screen)
        back_btn.draw(screen)
    
    elif current_state == STATE_ROOM:
        # Draw room interface
        title = font.render(f"Room: {current_room['room_id']}", True, TEXT_COLOR)
        screen.blit(title, (current_width//2 - title.get_width()//2, 80))
        
        # Room creator
        creator_text = small_font.render(f"Created by: {current_room['creator']}", True, TEXT_COLOR)
        screen.blit(creator_text, (current_width//2 - creator_text.get_width()//2, 130))
        
        # Players list
        players_label = small_font.render("Players:", True, TEXT_COLOR)
        screen.blit(players_label, (current_width//2 - 200, 180))
        
        player_characters = current_room.get('player_characters', {})
        
        for i, player in enumerate(current_room.get('players', [])):
            character = player_characters.get(player, "Not selected")
            player_text = small_font.render(f"{i+1}. {player} - {character}", True, TEXT_COLOR)
            screen.blit(player_text, (current_width//2 - 180, 220 + i * 40))
        
        # Show start button only for room creator
        if current_room['creator'] == current_user['username'] and not current_room.get('game_started', False):
            start_game_btn.draw(screen)
        
        leave_room_btn.draw(screen)
        
        # Show game status
        if current_room.get('game_started', False):
            status_text = small_font.render("Game in progress...", True, SUCCESS_COLOR)
            screen.blit(status_text, (current_width//2 - status_text.get_width()//2, HEIGHT - 200))
    
    elif current_state == STATE_VIDEO:
        # Draw video playback interface
        title = font.render(f"Question {current_question + 1} of {len(QUESTIONS)}", True, TEXT_COLOR)
        screen.blit(title, (current_width//2 - title.get_width()//2, 80))
        
        # Video placeholder
        video_rect = pygame.Rect(current_width//2 - 200, 150, 400, 300)
        pygame.draw.rect(screen, (30, 30, 30), video_rect)
        pygame.draw.rect(screen, (100, 100, 100), video_rect, 2)
        
        video_text = small_font.render("Video Playing...", True, TEXT_COLOR)
        screen.blit(video_text, (current_width//2 - video_text.get_width()//2, 160))
        
        # Show video progress
        if video_playing:
            progress = min(1.0, (current_time - video_start_time) / video_duration)
            progress_width = int(360 * progress)
            progress_rect = pygame.Rect(current_width//2 - 180, 470, progress_width, 20)
            pygame.draw.rect(screen, SUCCESS_COLOR, progress_rect)
            pygame.draw.rect(screen, (200, 200, 200), (current_width//2 - 180, 470, 360, 20), 2)
        
        skip_video_btn.draw(screen)
        
        # Auto-advance notification
        auto_text = tiny_font.render("Video will auto-advance to question when finished", True, (150, 150, 150))
        screen.blit(auto_text, (current_width//2 - auto_text.get_width()//2, HEIGHT - 120))
    
    elif current_state == STATE_QUIZ:
        # Draw quiz interface
        if current_question < len(QUESTIONS):
            question_data = QUESTIONS[current_question]
            
            # Question number
            q_num_text = font.render(f"Question {current_question + 1} of {len(QUESTIONS)}", True, TEXT_COLOR)
            screen.blit(q_num_text, (current_width//2 - q_num_text.get_width()//2, 80))
            
            # Question text (wrapped)
            question_lines = []
            words = question_data["question"].split(' ')
            current_line = []
            
            for word in words:
                test_line = ' '.join(current_line + [word])
                test_width = question_font.size(test_line)[0]
                if test_width < current_width - 100:
                    current_line.append(word)
                else:
                    question_lines.append(' '.join(current_line))
                    current_line = [word]
            if current_line:
                question_lines.append(' '.join(current_line))
            
            for i, line in enumerate(question_lines):
                q_text = question_font.render(line, True, TEXT_COLOR)
                screen.blit(q_text, (current_width//2 - q_text.get_width()//2, 130 + i * 30))
            
            # Draw option buttons
            for option_btn in option_buttons:
                option_btn.draw(screen)
            
            # Auto-advance notification
            auto_text = tiny_font.render("Select an option to automatically continue", True, (150, 150, 150))
            screen.blit(auto_text, (current_width//2 - auto_text.get_width()//2, HEIGHT - 120))
            
            back_btn.draw(screen)
    
    elif current_state == STATE_ROLE_SELECTION:
        # Draw role selection interface
        title = font.render("Choose Your Character", True, TEXT_COLOR)
        screen.blit(title, (current_width//2 - title.get_width()//2, 80))
        
        role_text = small_font.render(f"Your Role: {user_role}", True, SUCCESS_COLOR)
        screen.blit(role_text, (current_width//2 - role_text.get_width()//2, 130))
        
        instruction = small_font.render("Select your character from the options below:", True, TEXT_COLOR)
        screen.blit(instruction, (current_width//2 - instruction.get_width()//2, 160))
        
        # Draw character buttons
        for char_btn in character_buttons:
            char_btn.draw(screen)
        
        select_character_btn.draw(screen)
        
        if selected_character:
            selected_text = small_font.render(f"Selected: {selected_character}", True, SUCCESS_COLOR)
            screen.blit(selected_text, (current_width//2 - selected_text.get_width()//2, current_height - 120))
        
        back_btn.draw(screen)
    
    elif current_state == STATE_CHARACTER_CONFIRM:
        # Draw character confirmation interface
        title = font.render("Confirm Your Character", True, TEXT_COLOR)
        screen.blit(title, (current_width//2 - title.get_width()//2, 80))
        
        # Show selected character image and name
        if selected_character_data:
            try:
                char_img = pygame.image.load(selected_character_data['path'])
                char_img = pygame.transform.scale(char_img, (200, 200))
                screen.blit(char_img, (current_width//2 - 100, 150))
            except:
                # Placeholder if image not found
                placeholder = pygame.Surface((200, 200))
                placeholder.fill((100, 100, 100))
                screen.blit(placeholder, (current_width//2 - 100, 150))
        
        confirm_text = font.render(f"Your Role: {selected_character}", True, SUCCESS_COLOR)
        screen.blit(confirm_text, (current_width//2 - confirm_text.get_width()//2, 370))
        
        instruction = small_font.render("This will be your character for the game. Confirm your choice?", True, TEXT_COLOR)
        screen.blit(instruction, (current_width//2 - instruction.get_width()//2, 420))
        
        confirm_character_btn.draw(screen)
        back_btn.draw(screen)
    
    elif current_state == STATE_GAME:
        # Draw game interface
        title = font.render("Game Started!", True, TEXT_COLOR)
        screen.blit(title, (current_width//2 - title.get_width()//2, 80))
        
        # Show character image and role
        if selected_character_data:
            try:
                char_img = pygame.image.load(selected_character_data['path'])
                char_img = pygame.transform.scale(char_img, (200, 200))
                screen.blit(char_img, (current_width//2 - 100, 150))
            except:
                # Placeholder if image not found
                placeholder = pygame.Surface((200, 200))
                placeholder.fill((100, 100, 100))
                placeholder_text = small_font.render(selected_character, True, TEXT_COLOR)
                text_rect = placeholder_text.get_rect(center=(100, 100))
                placeholder.blit(placeholder_text, text_rect)
                screen.blit(placeholder, (current_width//2 - 100, 150))
        
        role_text = font.render(f"Your Role: {selected_character}", True, SUCCESS_COLOR)
        screen.blit(role_text, (current_width//2 - role_text.get_width()//2, 370))
        
        # Show other players in the room
        if current_room:
            players_label = small_font.render("Players in your room:", True, TEXT_COLOR)
            screen.blit(players_label, (current_width//2 - players_label.get_width()//2, 420))
            
            player_characters = current_room.get('player_characters', {})
            y_offset = 460
            
            for i, player in enumerate(current_room.get('players', [])):
                if player != current_user['username']:
                    character = player_characters.get(player, "Choosing character...")
                    player_text = small_font.render(f"{player}: {character}", True, TEXT_COLOR)
                    screen.blit(player_text, (current_width//2 - player_text.get_width()//2, y_offset))
                    y_offset += 40
            
            # Show waiting message if not all players have characters
            if len(player_characters) < len(current_room.get('players', [])):
                wait_text = small_font.render("Waiting for other players to choose characters...", True, WARNING_COLOR)
                screen.blit(wait_text, (current_width//2 - wait_text.get_width()//2, y_offset + 20))
    
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