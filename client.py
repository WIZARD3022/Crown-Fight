import pygame
import socket
import json
import threading
import sys
import os

# Initialize pygame
pygame.init()

# Screen dimensions
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
pygame.display.set_caption("Multiplayer Game Client")

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

class GameClient:
    def __init__(self, server_host='localhost', server_port=5555):
        self.server_host = server_host
        self.server_port = server_port
        self.socket = None
        self.connected = False
        self.current_user = None
        self.current_room = None
        self.available_rooms = []
        
        # Game states
        self.STATE_MAIN = "main"
        self.STATE_SIGN_IN = "sign_in"
        self.STATE_SIGN_UP = "sign_up"
        self.STATE_LOBBY = "lobby"
        self.STATE_CREATE_ROOM = "create_room"
        self.STATE_JOIN_ROOM = "join_room"
        self.STATE_ROOM = "room"
        self.STATE_QUIZ = "quiz"
        self.STATE_ROLE_SELECTION = "role_selection"
        self.STATE_CHARACTER_SELECTION = "character_selection"
        self.STATE_GAME = "game"
        
        self.current_state = self.STATE_MAIN
        
        # Quiz variables
        self.current_question = 0
        self.user_answers = []
        self.user_role = None
        self.selected_character = None
        
        # Character images mapping
        self.CHARACTER_IMAGES = {
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
        
        # Quiz questions
        self.QUESTIONS = [
            {
                "question": "In a dangerous forest, a beast blocks your path. What's your instinctive approach?",
                "options": [
                    "A) Charge head-on with brute force, relying on raw strength.",
                    "B) Protect allies and take the beast's hits while they strike back.",
                    "C) Stay hidden, strike quickly, and retreat before it notices.",
                    "D) Attack from a distance, taking advantage of range.",
                    "E) Distract it with music, spells, or concoctions to support allies.",
                    "F) Study its weaknesses, call upon nature, spirits, or elements for aid."
                ]
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
                ]
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
                ]
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
                ]
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
                ]
            }
        ]
        
        # UI elements
        self.setup_ui_elements()
        
        # Message system
        self.message_text = ""
        self.message_color = TEXT_COLOR
        self.message_timer = 0
        
    def setup_ui_elements(self):
        """Initialize UI elements"""
        # Input boxes
        self.signup_username = InputBox(WIDTH//2 - 150, 200, 300, 40, 'Username')
        self.signup_email = InputBox(WIDTH//2 - 150, 260, 300, 40, 'Email')
        self.signup_password = InputBox(WIDTH//2 - 150, 320, 300, 40, 'Password', True)
        self.signup_confirm = InputBox(WIDTH//2 - 150, 380, 300, 40, 'Confirm Password', True)
        
        self.signin_username = InputBox(WIDTH//2 - 150, 200, 300, 40, 'Username or Email')
        self.signin_password = InputBox(WIDTH//2 - 150, 260, 300, 40, 'Password', True)
        
        self.room_id_input = InputBox(WIDTH//2 - 150, 250, 300, 40, 'Enter Room ID')
        
        # Buttons
        self.sign_in_btn = Button(WIDTH//2 - 150, HEIGHT - 300, 140, 50, "Sign In")
        self.sign_up_btn = Button(WIDTH//2 + 10, HEIGHT - 300, 140, 50, "Sign Up")
        self.submit_btn = Button(WIDTH//2 - 75, HEIGHT - 150, 150, 50, "Submit")
        self.back_btn = Button(WIDTH//2 - 75, HEIGHT - 80, 150, 40, "Back")
        
        self.create_room_btn = Button(WIDTH//2 - 150, HEIGHT - 200, 140, 50, "Create Room")
        self.join_room_btn = Button(WIDTH//2 + 10, HEIGHT - 200, 140, 50, "Join Room")
        self.my_room_btn = Button(WIDTH//2 - 75, HEIGHT - 130, 150, 50, "My Room")
        self.continue_game_btn = Button(WIDTH//2 - 75, HEIGHT - 70, 150, 40, "Continue Game")
        self.logout_btn = Button(WIDTH//2 - 75, HEIGHT - 20, 150, 40, "Logout")
        
        self.join_with_id_btn = Button(WIDTH//2 - 150, HEIGHT - 150, 140, 50, "Join with ID")
        self.refresh_rooms_btn = Button(WIDTH//2 + 10, HEIGHT - 150, 140, 50, "Refresh Rooms")
        
        self.start_game_btn = Button(WIDTH//2 - 150, HEIGHT - 150, 140, 50, "Start Game")
        self.leave_room_btn = Button(WIDTH//2 + 10, HEIGHT - 150, 140, 50, "Leave Room")
        
        self.next_question_btn = Button(WIDTH//2 - 75, HEIGHT - 80, 150, 40, "Next Question")
        self.submit_quiz_btn = Button(WIDTH//2 - 75, HEIGHT - 80, 150, 40, "Submit Quiz")
        
        self.select_character_btn = Button(WIDTH//2 - 75, HEIGHT - 80, 150, 40, "Select Character")
        self.lock_character_btn = Button(WIDTH//2 - 75, HEIGHT - 80, 150, 40, "Lock Character")
        
        # Room buttons list
        self.room_buttons = []
        
        # Quiz option buttons
        self.option_buttons = []
        
        # Character selection buttons
        self.character_buttons = []

    def connect_to_server(self):
        """Connect to the game server"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.server_host, self.server_port))
            self.connected = True
            
            # Start listening for server messages
            listener_thread = threading.Thread(target=self.listen_to_server)
            listener_thread.daemon = True
            listener_thread.start()
            
            print("✅ Connected to game server")
            return True
            
        except Exception as e:
            print(f"❌ Failed to connect to server: {e}")
            self.show_message(f"Failed to connect to server: {e}", ERROR_COLOR)
            return False

    def listen_to_server(self):
        """Listen for messages from the server"""
        while self.connected:
            try:
                data = self.socket.recv(4096).decode('utf-8')
                if not data:
                    break
                    
                messages = data.split('}{')
                for i, msg in enumerate(messages):
                    if i > 0:
                        msg = '{' + msg
                    if i < len(messages) - 1:
                        msg = msg + '}'
                        
                    try:
                        message = json.loads(msg)
                        self.handle_server_message(message)
                    except json.JSONDecodeError:
                        print(f"❌ Invalid JSON received: {msg}")
                        
            except Exception as e:
                print(f"❌ Error receiving from server: {e}")
                break
                
        self.connected = False
        self.show_message("Disconnected from server", ERROR_COLOR)

    def handle_server_message(self, message):
        """Handle messages from the server"""
        action = message.get('action')
        status = message.get('status')
        data = message.get('data', {})
        msg_text = message.get('message', '')
        
        print(f"📨 Received {action} from server")
        
        if status == 'error':
            self.show_message(msg_text, ERROR_COLOR)
            return
            
        if action == 'sign_up_response':
            self.show_message(msg_text, SUCCESS_COLOR)
            self.current_state = self.STATE_MAIN
            
        elif action == 'sign_in_response':
            self.current_user = data
            self.show_message(msg_text, SUCCESS_COLOR)
            self.current_state = self.STATE_LOBBY
            
        elif action == 'create_room_response':
            self.current_room = data['room_data']
            self.show_message(msg_text, SUCCESS_COLOR)
            self.current_state = self.STATE_ROOM
            
        elif action == 'join_room_response':
            self.current_room = data['room_data']
            self.show_message(msg_text, SUCCESS_COLOR)
            self.current_state = self.STATE_ROOM
            
        elif action == 'get_rooms_response':
            self.available_rooms = data['rooms']
            self.create_room_buttons()
            
        elif action == 'start_game_response':
            self.show_message(msg_text, SUCCESS_COLOR)
            self.initialize_quiz()
            self.current_state = self.STATE_QUIZ
            
        elif action == 'submit_answer_response':
            self.show_message(msg_text, SUCCESS_COLOR)
            
        elif action == 'role_assigned':
            self.user_role = data['role']
            self.show_message(msg_text, SUCCESS_COLOR)
            self.create_character_buttons()
            self.current_state = self.STATE_CHARACTER_SELECTION
            
        elif action == 'select_character_response':
            self.selected_character = data['character']
            self.show_message(msg_text, SUCCESS_COLOR)
            
        elif action == 'lock_character_response':
            self.show_message(msg_text, SUCCESS_COLOR)
            self.current_state = self.STATE_GAME
            
        elif action == 'leave_room_response':
            self.current_room = None
            self.show_message(msg_text, SUCCESS_COLOR)
            self.current_state = self.STATE_LOBBY
            
        elif action == 'room_status_response':
            self.current_room = data['room_data']
            
        elif action == 'room_updated':
            self.current_room = data['room_data']
            
        elif action == 'rooms_updated':
            self.available_rooms = data['rooms']
            self.create_room_buttons()

    def send_to_server(self, action, data=None):
        """Send message to server"""
        if not self.connected:
            self.show_message("Not connected to server", ERROR_COLOR)
            return
            
        message = {
            'action': action,
            'data': data or {}
        }
        
        try:
            self.socket.send(json.dumps(message).encode('utf-8'))
        except Exception as e:
            print(f"❌ Error sending to server: {e}")
            self.show_message("Failed to send message to server", ERROR_COLOR)

    # UI Helper Methods
    def show_message(self, text, color=TEXT_COLOR, duration=300):
        """Show temporary message"""
        self.message_text = text
        self.message_color = color
        self.message_timer = duration

    def create_room_buttons(self):
        """Create buttons for available rooms"""
        self.room_buttons = []
        
        for i, room in enumerate(self.available_rooms):
            y_pos = 150 + (i * 80)
            if y_pos < HEIGHT - 200:
                self.room_buttons.append(RoomButton(WIDTH//2 - 200, y_pos, 400, 70, room))

    def create_option_buttons(self):
        """Create buttons for quiz options"""
        self.option_buttons = []
        
        if self.current_question < len(self.QUESTIONS):
            question_data = self.QUESTIONS[self.current_question]
            
            for i, option in enumerate(question_data["options"]):
                y_pos = 200 + (i * 70)
                if y_pos < HEIGHT - 150:
                    option_key = option[0]  # Get A, B, C, etc.
                    self.option_buttons.append(OptionButton(WIDTH//2 - 300, y_pos, 600, 60, option, option_key))

    def create_character_buttons(self):
        """Create buttons for character selection"""
        self.character_buttons = []
        
        if self.user_role in self.CHARACTER_IMAGES:
            character_list = self.CHARACTER_IMAGES[self.user_role]
            
            for i, char_data in enumerate(character_list):
                row = i // 2
                col = i % 2
                x_pos = WIDTH//2 - 200 + (col * 220)
                y_pos = 200 + (row * 180)
                
                self.character_buttons.append(CharacterButton(x_pos, y_pos, 180, 160, char_data))

    def initialize_quiz(self):
        """Initialize quiz variables"""
        self.current_question = 0
        self.user_answers = []
        self.user_role = None
        self.selected_character = None
        self.create_option_buttons()

    # Game State Methods
    def handle_sign_up(self):
        """Handle user registration"""
        username = self.signup_username.text
        email = self.signup_email.text
        password = self.signup_password.text
        confirm_password = self.signup_confirm.text
        
        self.send_to_server('sign_up', {
            'username': username,
            'email': email,
            'password': password,
            'confirm_password': confirm_password
        })

    def handle_sign_in(self):
        """Handle user login"""
        username = self.signin_username.text
        password = self.signin_password.text
        
        self.send_to_server('sign_in', {
            'username': username,
            'password': password
        })

    def handle_create_room(self):
        """Handle room creation"""
        self.send_to_server('create_room')

    def handle_join_room(self, room_id):
        """Handle joining a room"""
        self.send_to_server('join_room', {'room_id': room_id})

    def handle_start_game(self):
        """Handle starting the game"""
        self.send_to_server('start_game')

    def handle_submit_answer(self, question_index, answer):
        """Handle quiz answer submission"""
        self.send_to_server('submit_answer', {
            'question_index': question_index,
            'answer': answer
        })

    def handle_select_character(self, character):
        """Handle character selection"""
        self.send_to_server('select_character', {
            'character': character
        })

    def handle_lock_character(self):
        """Handle character locking"""
        self.send_to_server('lock_character')

    def handle_leave_room(self):
        """Handle leaving room"""
        self.send_to_server('leave_room')

    def handle_get_rooms(self):
        """Request room list from server"""
        self.send_to_server('get_rooms')

    def handle_get_room_status(self):
        """Request room status from server"""
        self.send_to_server('get_room_status')

    def run(self):
        """Main game loop"""
        if not self.connect_to_server():
            return
            
        clock = pygame.time.Clock()
        running = True
        
        while running:
            current_width, current_height = screen.get_size()
            mouse_pos = pygame.mouse.get_pos()
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                    self.connected = False
                    if self.socket:
                        self.socket.close()
                
                self.handle_events(event, mouse_pos)
            
            self.update_hover_states(mouse_pos)
            self.update_message_timer()
            self.draw_ui(current_width, current_height)
            
            pygame.display.flip()
            clock.tick(60)

    def handle_events(self, event, mouse_pos):
        """Handle pygame events"""
        # Handle input based on current state
        if self.current_state == self.STATE_SIGN_UP:
            self.signup_username.handle_event(event)
            self.signup_email.handle_event(event)
            self.signup_password.handle_event(event)
            self.signup_confirm.handle_event(event)
            
        elif self.current_state == self.STATE_SIGN_IN:
            self.signin_username.handle_event(event)
            self.signin_password.handle_event(event)
            
        elif self.current_state == self.STATE_JOIN_ROOM:
            self.room_id_input.handle_event(event)
            
        elif self.current_state == self.STATE_QUIZ:
            for option_btn in self.option_buttons:
                if option_btn.is_clicked(mouse_pos, event):
                    # Deselect all other options
                    for btn in self.option_buttons:
                        if btn != option_btn:
                            btn.is_selected = False
                    
                    # Submit answer and auto-advance
                    self.handle_submit_answer(self.current_question, option_btn.option_key)
                    
                    if self.current_question < len(self.QUESTIONS) - 1:
                        self.current_question += 1
                        self.create_option_buttons()
                    else:
                        # All questions answered, wait for role assignment from server
                        pass
        
        elif self.current_state == self.STATE_CHARACTER_SELECTION:
            for char_btn in self.character_buttons:
                if char_btn.is_clicked(mouse_pos, event):
                    # Deselect all other characters
                    for btn in self.character_buttons:
                        if btn != char_btn:
                            btn.is_selected = False
                    self.selected_character = char_btn.character_data['name']
                    self.handle_select_character(self.selected_character)
        
        # Handle button clicks
        self.handle_button_clicks(event, mouse_pos)

    def handle_button_clicks(self, event, mouse_pos):
        """Handle button click events"""
        if self.sign_in_btn.is_clicked(mouse_pos, event):
            self.current_state = self.STATE_SIGN_IN
            self.show_message("")
            
        elif self.sign_up_btn.is_clicked(mouse_pos, event):
            self.current_state = self.STATE_SIGN_UP
            self.show_message("")
            
        elif self.submit_btn.is_clicked(mouse_pos, event):
            if self.current_state == self.STATE_SIGN_UP:
                self.handle_sign_up()
            elif self.current_state == self.STATE_SIGN_IN:
                self.handle_sign_in()
        
        elif self.back_btn.is_clicked(mouse_pos, event):
            if self.current_state in [self.STATE_SIGN_IN, self.STATE_SIGN_UP]:
                self.current_state = self.STATE_MAIN
            elif self.current_state in [self.STATE_CREATE_ROOM, self.STATE_JOIN_ROOM]:
                self.current_state = self.STATE_LOBBY
            elif self.current_state == self.STATE_QUIZ:
                if self.current_question > 0:
                    self.current_question -= 1
                    self.create_option_buttons()
            elif self.current_state == self.STATE_CHARACTER_SELECTION:
                self.current_state = self.STATE_ROOM
            self.show_message("")
        
        elif self.create_room_btn.is_clicked(mouse_pos, event):
            self.handle_create_room()
        
        elif self.join_room_btn.is_clicked(mouse_pos, event):
            self.current_state = self.STATE_JOIN_ROOM
            self.handle_get_rooms()
            self.show_message("")
        
        elif self.my_room_btn.is_clicked(mouse_pos, event) and self.current_user and self.current_user.get('last_room'):
            self.handle_join_room(self.current_user['last_room'])
        
        elif self.continue_game_btn.is_clicked(mouse_pos, event) and self.current_user and self.current_user.get('last_room'):
            self.handle_join_room(self.current_user['last_room'])
        
        elif self.logout_btn.is_clicked(mouse_pos, event):
            self.current_user = None
            self.current_room = None
            self.current_state = self.STATE_MAIN
            self.show_message("Logged out successfully")
        
        elif self.join_with_id_btn.is_clicked(mouse_pos, event):
            if self.room_id_input.text:
                self.handle_join_room(self.room_id_input.text)
            else:
                self.show_message("Please enter a room ID", ERROR_COLOR)
        
        elif self.refresh_rooms_btn.is_clicked(mouse_pos, event):
            self.handle_get_rooms()
            self.show_message("Rooms refreshed")
        
        elif self.start_game_btn.is_clicked(mouse_pos, event):
            self.handle_start_game()
        
        elif self.leave_room_btn.is_clicked(mouse_pos, event):
            self.handle_leave_room()
        
        elif self.select_character_btn.is_clicked(mouse_pos, event):
            if self.selected_character:
                self.current_state = self.STATE_GAME
            else:
                self.show_message("Please select a character", ERROR_COLOR)
        
        elif self.lock_character_btn.is_clicked(mouse_pos, event):
            if self.selected_character:
                self.handle_lock_character()
            else:
                self.show_message("Please select a character", ERROR_COLOR)
        
        # Room button clicks
        for room_btn in self.room_buttons:
            if room_btn.is_clicked(mouse_pos, event):
                self.handle_join_room(room_btn.room_data['room_id'])

    def update_hover_states(self, mouse_pos):
        """Update hover states for all interactive elements"""
        buttons = [
            self.sign_in_btn, self.sign_up_btn, self.submit_btn, self.back_btn,
            self.create_room_btn, self.join_room_btn, self.my_room_btn, self.continue_game_btn, self.logout_btn,
            self.join_with_id_btn, self.refresh_rooms_btn, self.start_game_btn, self.leave_room_btn,
            self.next_question_btn, self.submit_quiz_btn, self.select_character_btn, self.lock_character_btn
        ]
        
        for btn in buttons:
            btn.check_hover(mouse_pos)
        
        for room_btn in self.room_buttons:
            room_btn.check_hover(mouse_pos)
        
        for option_btn in self.option_buttons:
            option_btn.check_hover(mouse_pos)
        
        for char_btn in self.character_buttons:
            char_btn.check_hover(mouse_pos)

    def update_message_timer(self):
        """Update message display timer"""
        if self.message_timer > 0:
            self.message_timer -= 1

    def draw_ui(self, width, height):
        """Draw the UI based on current state"""
        screen.fill((40, 44, 52))  # Dark background
        
        if self.current_state == self.STATE_MAIN:
            self.draw_main_menu(width, height)
        elif self.current_state == self.STATE_SIGN_UP:
            self.draw_sign_up_form(width, height)
        elif self.current_state == self.STATE_SIGN_IN:
            self.draw_sign_in_form(width, height)
        elif self.current_state == self.STATE_LOBBY:
            self.draw_lobby(width, height)
        elif self.current_state == self.STATE_JOIN_ROOM:
            self.draw_join_room(width, height)
        elif self.current_state == self.STATE_ROOM:
            self.draw_room(width, height)
        elif self.current_state == self.STATE_QUIZ:
            self.draw_quiz(width, height)
        elif self.current_state == self.STATE_CHARACTER_SELECTION:
            self.draw_character_selection(width, height)
        elif self.current_state == self.STATE_GAME:
            self.draw_game(width, height)
        
        # Draw message if any
        if self.message_text and self.message_timer > 0:
            msg_surf = small_font.render(self.message_text, True, self.message_color)
            screen.blit(msg_surf, (width//2 - msg_surf.get_width()//2, height - 200))
        
        # Draw connection status
        status_text = "Connected" if self.connected else "Disconnected"
        status_color = SUCCESS_COLOR if self.connected else ERROR_COLOR
        status_surf = tiny_font.render(f"Server: {status_text}", True, status_color)
        screen.blit(status_surf, (10, height - 30))

    def draw_main_menu(self, width, height):
        """Draw main menu"""
        title = font.render("Multiplayer Game", True, TEXT_COLOR)
        screen.blit(title, (width//2 - title.get_width()//2, 100))
        
        self.sign_in_btn.draw(screen)
        self.sign_up_btn.draw(screen)

    def draw_sign_up_form(self, width, height):
        """Draw sign up form"""
        title = font.render("Create Account", True, TEXT_COLOR)
        screen.blit(title, (width//2 - title.get_width()//2, 100))
        
        self.signup_username.draw(screen)
        self.signup_email.draw(screen)
        self.signup_password.draw(screen)
        self.signup_confirm.draw(screen)
        
        self.submit_btn.draw(screen)
        self.back_btn.draw(screen)

    def draw_sign_in_form(self, width, height):
        """Draw sign in form"""
        title = font.render("Sign In", True, TEXT_COLOR)
        screen.blit(title, (width//2 - title.get_width()//2, 100))
        
        self.signin_username.draw(screen)
        self.signin_password.draw(screen)
        
        self.submit_btn.draw(screen)
        self.back_btn.draw(screen)

    def draw_lobby(self, width, height):
        """Draw lobby"""
        welcome_text = font.render(f"Welcome, {self.current_user['username']}!", True, TEXT_COLOR)
        screen.blit(welcome_text, (width//2 - welcome_text.get_width()//2, 100))
        
        instruction = small_font.render("Choose an option below:", True, TEXT_COLOR)
        screen.blit(instruction, (width//2 - instruction.get_width()//2, 160))
        
        self.create_room_btn.draw(screen)
        self.join_room_btn.draw(screen)
        
        # Show My Room button if user has a last room
        if self.current_user and self.current_user.get('last_room'):
            self.my_room_btn.draw(screen)
            room_info = tiny_font.render(f"Your room: {self.current_user.get('last_room')}", True, SUCCESS_COLOR)
            screen.blit(room_info, (width//2 - room_info.get_width()//2, height - 180))
        
        # Show Continue Game button if user has a character
        if self.current_user and self.current_user.get('character'):
            self.continue_game_btn.draw(screen)
            continue_info = tiny_font.render(f"Continue as {self.current_user.get('character')}", True, SUCCESS_COLOR)
            screen.blit(continue_info, (width//2 - continue_info.get_width()//2, height - 130))
        
        self.logout_btn.draw(screen)

    def draw_join_room(self, width, height):
        """Draw join room interface"""
        title = font.render("Join a Room", True, TEXT_COLOR)
        screen.blit(title, (width//2 - title.get_width()//2, 80))
        
        # Room ID input
        room_id_label = small_font.render("Enter Room ID:", True, TEXT_COLOR)
        screen.blit(room_id_label, (width//2 - 150, 220))
        self.room_id_input.draw(screen)
        self.join_with_id_btn.draw(screen)
        
        # Available rooms
        rooms_label = small_font.render("Available Rooms:", True, TEXT_COLOR)
        screen.blit(rooms_label, (width//2 - rooms_label.get_width()//2, 320))
        
        for room_btn in self.room_buttons:
            room_btn.draw(screen)
        
        self.refresh_rooms_btn.draw(screen)
        self.back_btn.draw(screen)

    def draw_room(self, width, height):
        """Draw room interface"""
        if not self.current_room:
            return
            
        title = font.render(f"Room: {self.current_room['room_id']}", True, TEXT_COLOR)
        screen.blit(title, (width//2 - title.get_width()//2, 80))
        
        # Room creator
        creator_text = small_font.render(f"Created by: {self.current_room['creator']}", True, TEXT_COLOR)
        screen.blit(creator_text, (width//2 - creator_text.get_width()//2, 130))
        
        # Players list
        players_label = small_font.render("Players:", True, TEXT_COLOR)
        screen.blit(players_label, (width//2 - 200, 180))
        
        player_characters = self.current_room.get('player_characters', {})
        character_locked = self.current_room.get('character_locked', {})
        
        for i, player in enumerate(self.current_room.get('players', [])):
            character = player_characters.get(player, "Not selected")
            lock_status = "🔒" if character_locked.get(player, False) else "🔓"
            player_text = small_font.render(f"{i+1}. {player} - {character} {lock_status}", True, TEXT_COLOR)
            screen.blit(player_text, (width//2 - 180, 220 + i * 40))
        
        # Show start button only for room creator
        if self.current_room['creator'] == self.current_user['username'] and not self.current_room.get('game_started', False):
            self.start_game_btn.draw(screen)
        
        self.leave_room_btn.draw(screen)
        
        # Show game status
        if self.current_room.get('game_started', False):
            status_text = small_font.render("Game in progress...", True, SUCCESS_COLOR)
            screen.blit(status_text, (width//2 - status_text.get_width()//2, height - 200))

    def draw_quiz(self, width, height):
        """Draw quiz interface"""
        if self.current_question < len(self.QUESTIONS):
            question_data = self.QUESTIONS[self.current_question]
            
            # Question number
            q_num_text = font.render(f"Question {self.current_question + 1} of {len(self.QUESTIONS)}", True, TEXT_COLOR)
            screen.blit(q_num_text, (width//2 - q_num_text.get_width()//2, 80))
            
            # Question text (wrapped)
            question_lines = []
            words = question_data["question"].split(' ')
            current_line = []
            
            for word in words:
                test_line = ' '.join(current_line + [word])
                test_width = question_font.size(test_line)[0]
                if test_width < width - 100:
                    current_line.append(word)
                else:
                    question_lines.append(' '.join(current_line))
                    current_line = [word]
            if current_line:
                question_lines.append(' '.join(current_line))
            
            for i, line in enumerate(question_lines):
                q_text = question_font.render(line, True, TEXT_COLOR)
                screen.blit(q_text, (width//2 - q_text.get_width()//2, 130 + i * 30))
            
            # Draw option buttons
            for option_btn in self.option_buttons:
                option_btn.draw(screen)
            
            # Auto-advance notification
            auto_text = tiny_font.render("Select an option to automatically continue", True, (150, 150, 150))
            screen.blit(auto_text, (width//2 - auto_text.get_width()//2, height - 120))
            
            self.back_btn.draw(screen)

    def draw_character_selection(self, width, height):
        """Draw character selection interface"""
        title = font.render("Choose Your Character", True, TEXT_COLOR)
        screen.blit(title, (width//2 - title.get_width()//2, 80))
        
        role_text = small_font.render(f"Your Role: {self.user_role}", True, SUCCESS_COLOR)
        screen.blit(role_text, (width//2 - role_text.get_width()//2, 130))
        
        instruction = small_font.render("Select your character from the options below:", True, TEXT_COLOR)
        screen.blit(instruction, (width//2 - instruction.get_width()//2, 160))
        
        # Draw character buttons
        for char_btn in self.character_buttons:
            char_btn.draw(screen)
        
        self.lock_character_btn.draw(screen)
        
        if self.selected_character:
            selected_text = small_font.render(f"Selected: {self.selected_character}", True, SUCCESS_COLOR)
            screen.blit(selected_text, (width//2 - selected_text.get_width()//2, height - 120))
        
        self.back_btn.draw(screen)

    def draw_game(self, width, height):
        """Draw game interface"""
        title = font.render("Game Started!", True, TEXT_COLOR)
        screen.blit(title, (width//2 - title.get_width()//2, 80))
        
        # Show character info
        if self.selected_character:
            char_text = font.render(f"Your Character: {self.selected_character}", True, SUCCESS_COLOR)
            screen.blit(char_text, (width//2 - char_text.get_width()//2, 150))
            
            role_text = small_font.render(f"Your Role: {self.user_role}", True, TEXT_COLOR)
            screen.blit(role_text, (width//2 - role_text.get_width()//2, 200))
        
        # Show other players in the room
        if self.current_room:
            players_label = small_font.render("Players in your room:", True, TEXT_COLOR)
            screen.blit(players_label, (width//2 - players_label.get_width()//2, 250))
            
            player_characters = self.current_room.get('player_characters', {})
            character_locked = self.current_room.get('character_locked', {})
            y_offset = 300
            
            for i, player in enumerate(self.current_room.get('players', [])):
                if player != self.current_user['username']:
                    character = player_characters.get(player, "Choosing character...")
                    lock_status = " (Locked)" if character_locked.get(player, False) else " (Choosing)"
                    player_text = small_font.render(f"{player}: {character}{lock_status}", True, TEXT_COLOR)
                    screen.blit(player_text, (width//2 - player_text.get_width()//2, y_offset))
                    y_offset += 40
            
            # Show waiting message if not all players have locked characters
            locked_count = sum(1 for player in self.current_room.get('players', []) 
                             if character_locked.get(player, False))
            total_players = len(self.current_room.get('players', []))
            
            if locked_count < total_players:
                wait_text = small_font.render(f"Waiting for {total_players - locked_count} player(s) to lock characters...", 
                                            True, WARNING_COLOR)
                screen.blit(wait_text, (width//2 - wait_text.get_width()//2, y_offset + 20))

# UI Element Classes (same as before, but included for completeness)
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

if __name__ == "__main__":
    client = GameClient()
    client.run()