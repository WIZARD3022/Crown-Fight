import socket
import threading
import json
import os
import re
import random
import string
from datetime import datetime
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, DuplicateKeyError
import bcrypt
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class GameServer:
    def __init__(self, host='0.0.0.0', port=os.getenv('PORT')):
        self.host = host
        self.port = port
        self.server = None
        self.clients = {}
        self.rooms = {}
        self.setup_database()
        
    def setup_database(self):
        """Initialize MongoDB connection"""
        try:
            self.mongo_client = MongoClient(os.getenv('MONGODB_URI', 'mongodb://localhost:27017/'))
            self.db = self.mongo_client[os.getenv('DATABASE_NAME', 'game_auth')]
            self.users_collection = self.db.users
            self.rooms_collection = self.db.rooms
            
            # Create indexes
            self.users_collection.create_index("username", unique=True)
            self.users_collection.create_index("email", unique=True)
            self.rooms_collection.create_index("room_id", unique=True)
            
            print("✅ Database connected successfully")
        except Exception as e:
            print(f"❌ Database connection failed: {e}")
            exit(1)

    def start_server(self):
        """Start the game server"""
        try:
            self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server.bind((self.host, self.port))
            self.server.listen(5)
            print(f"🎮 Game server started on {self.host}:{self.port}")
            
            while True:
                client_socket, address = self.server.accept()
                print(f"🔗 New connection from {address}")
                
                client_handler = threading.Thread(
                    target=self.handle_client,
                    args=(client_socket, address)
                )
                client_handler.daemon = True
                client_handler.start()
                
        except Exception as e:
            print(f"❌ Server error: {e}")
        finally:
            if self.server:
                self.server.close()

    def handle_client(self, client_socket, address):
        """Handle individual client connections"""
        client_id = f"{address[0]}:{address[1]}"
        self.clients[client_id] = {
            'socket': client_socket,
            'username': None,
            'room_id': None,
            'character_locked': False
        }
        
        try:
            while True:
                data = client_socket.recv(4096).decode('utf-8')
                if not data:
                    break
                    
                try:
                    message = json.loads(data)
                    self.process_message(client_id, message)
                except json.JSONDecodeError:
                    self.send_error(client_socket, "Invalid JSON format")
                    
        except Exception as e:
            print(f"❌ Client {client_id} error: {e}")
        finally:
            self.disconnect_client(client_id)

    def process_message(self, client_id, message):
        """Process incoming messages from clients"""
        action = message.get('action')
        data = message.get('data', {})
        
        print(f"📨 Received {action} from {client_id}")
        
        handler_map = {
            'sign_up': self.handle_sign_up,
            'sign_in': self.handle_sign_in,
            'create_room': self.handle_create_room,
            'join_room': self.handle_join_room,
            'get_rooms': self.handle_get_rooms,
            'start_game': self.handle_start_game,
            'submit_answer': self.handle_submit_answer,
            'select_character': self.handle_select_character,
            'lock_character': self.handle_lock_character,
            'leave_room': self.handle_leave_room,
            'get_room_status': self.handle_get_room_status
        }
        
        handler = handler_map.get(action)
        if handler:
            handler(client_id, data)
        else:
            self.send_error(self.clients[client_id]['socket'], f"Unknown action: {action}")

    # Authentication Handlers
    def handle_sign_up(self, client_id, data):
        """Handle user registration"""
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')
        confirm_password = data.get('confirm_password')
        
        if not all([username, email, password, confirm_password]):
            self.send_error(self.clients[client_id]['socket'], "All fields are required")
            return
            
        if password != confirm_password:
            self.send_error(self.clients[client_id]['socket'], "Passwords do not match")
            return
            
        if not self.validate_email(email):
            self.send_error(self.clients[client_id]['socket'], "Invalid email format")
            return
            
        if len(password) < 6:
            self.send_error(self.clients[client_id]['socket'], "Password must be at least 6 characters")
            return
            
        try:
            # Check if username or email already exists
            if self.users_collection.find_one({"$or": [{"username": username}, {"email": email}]}):
                self.send_error(self.clients[client_id]['socket'], "Username or email already exists")
                return
                
            # Create user
            user_data = {
                "username": username,
                "email": email,
                "password_hash": bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()),
                "created_at": datetime.utcnow(),
                "last_login": None,
                "last_room": None
            }
            
            result = self.users_collection.insert_one(user_data)
            
            response = {
                'action': 'sign_up_response',
                'status': 'success',
                'message': 'Account created successfully!'
            }
            self.send_message(self.clients[client_id]['socket'], response)
            
        except Exception as e:
            self.send_error(self.clients[client_id]['socket'], f"Registration failed: {str(e)}")

    def handle_sign_in(self, client_id, data):
        """Handle user login"""
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            self.send_error(self.clients[client_id]['socket'], "All fields are required")
            return
            
        try:
            # Find user by username or email
            user = self.users_collection.find_one({
                "$or": [
                    {"username": username},
                    {"email": username}
                ]
            })
            
            if user and bcrypt.checkpw(password.encode('utf-8'), user["password_hash"]):
                # Update last login
                self.users_collection.update_one(
                    {"_id": user["_id"]},
                    {"$set": {"last_login": datetime.utcnow()}}
                )
                
                # Store user info in client data
                self.clients[client_id]['username'] = user['username']
                
                response = {
                    'action': 'sign_in_response',
                    'status': 'success',
                    'data': {
                        'username': user['username'],
                        'email': user['email'],
                        'last_room': user.get('last_room')
                    },
                    'message': f"Welcome back, {user['username']}!"
                }
                self.send_message(self.clients[client_id]['socket'], response)
            else:
                self.send_error(self.clients[client_id]['socket'], "Invalid username/email or password")
                
        except Exception as e:
            self.send_error(self.clients[client_id]['socket'], f"Login failed: {str(e)}")

    # Room Management Handlers
    def handle_create_room(self, client_id, data):
        """Handle room creation"""
        username = self.clients[client_id].get('username')
        if not username:
            self.send_error(self.clients[client_id]['socket'], "You must be logged in to create a room")
            return
            
        room_id = self.generate_room_id()
        room_data = {
            "room_id": room_id,
            "creator": username,
            "players": [username],
            "player_characters": {},
            "player_answers": {},
            "player_roles": {},
            "character_locked": {},
            "is_active": True,
            "created_at": datetime.utcnow(),
            "max_players": 4,
            "game_started": False,
            "game_finished": False,
            "current_question": 0
        }
        
        try:
            # Save to database
            self.rooms_collection.insert_one(room_data)
            
            # Update user's last room
            self.users_collection.update_one(
                {"username": username},
                {"$set": {"last_room": room_id}}
            )
            
            # Store in memory
            self.rooms[room_id] = room_data
            self.clients[client_id]['room_id'] = room_id
            
            response = {
                'action': 'create_room_response',
                'status': 'success',
                'data': {
                    'room_id': room_id,
                    'room_data': room_data
                },
                'message': f"Room {room_id} created successfully!"
            }
            self.send_message(self.clients[client_id]['socket'], response)
            
            # Notify all clients about room list update
            self.broadcast_room_list()
            
        except Exception as e:
            self.send_error(self.clients[client_id]['socket'], f"Room creation failed: {str(e)}")

    def handle_join_room(self, client_id, data):
        """Handle joining a room"""
        username = self.clients[client_id].get('username')
        room_id = data.get('room_id')
        
        if not username:
            self.send_error(self.clients[client_id]['socket'], "You must be logged in to join a room")
            return
            
        if not room_id:
            self.send_error(self.clients[client_id]['socket'], "Room ID is required")
            return
            
        try:
            # Get room from database
            room = self.rooms_collection.find_one({"room_id": room_id})
            if not room:
                self.send_error(self.clients[client_id]['socket'], "Room not found")
                return
                
            if not room.get('is_active', True):
                self.send_error(self.clients[client_id]['socket'], "Room is not active")
                return
                
            if username in room.get('players', []):
                self.send_error(self.clients[client_id]['socket'], "You are already in this room")
                return
                
            if len(room.get('players', [])) >= room.get('max_players', 4):
                self.send_error(self.clients[client_id]['socket'], "Room is full")
                return
                
            # Add player to room
            updated_players = room.get('players', []) + [username]
            self.rooms_collection.update_one(
                {"room_id": room_id},
                {"$set": {"players": updated_players}}
            )
            
            # Update user's last room
            self.users_collection.update_one(
                {"username": username},
                {"$set": {"last_room": room_id}}
            )
            
            # Update in-memory data
            if room_id in self.rooms:
                self.rooms[room_id]['players'] = updated_players
            else:
                self.rooms[room_id] = room
                self.rooms[room_id]['players'] = updated_players
                
            self.clients[client_id]['room_id'] = room_id
            
            response = {
                'action': 'join_room_response',
                'status': 'success',
                'data': {
                    'room_id': room_id,
                    'room_data': self.rooms[room_id]
                },
                'message': f"Joined room {room_id} successfully!"
            }
            self.send_message(self.clients[client_id]['socket'], response)
            
            # Notify all clients in the room
            self.broadcast_room_update(room_id)
            self.broadcast_room_list()
            
        except Exception as e:
            self.send_error(self.clients[client_id]['socket'], f"Failed to join room: {str(e)}")

    def handle_get_rooms(self, client_id, data):
        """Handle request for room list"""
        try:
            rooms = list(self.rooms_collection.find({"is_active": True}))
            
            response = {
                'action': 'get_rooms_response',
                'status': 'success',
                'data': {
                    'rooms': rooms
                }
            }
            self.send_message(self.clients[client_id]['socket'], response)
            
        except Exception as e:
            self.send_error(self.clients[client_id]['socket'], f"Failed to get rooms: {str(e)}")

    def handle_start_game(self, client_id, data):
        """Handle starting the game in a room"""
        username = self.clients[client_id].get('username')
        room_id = self.clients[client_id].get('room_id')
        
        if not username or not room_id:
            self.send_error(self.clients[client_id]['socket'], "You must be in a room to start the game")
            return
            
        try:
            room = self.rooms_collection.find_one({"room_id": room_id})
            if not room:
                self.send_error(self.clients[client_id]['socket'], "Room not found")
                return
                
            if room['creator'] != username:
                self.send_error(self.clients[client_id]['socket'], "Only the room creator can start the game")
                return
                
            # Start the game
            self.rooms_collection.update_one(
                {"room_id": room_id},
                {"$set": {"game_started": True, "current_question": 0}}
            )
            
            # Update in-memory data
            if room_id in self.rooms:
                self.rooms[room_id]['game_started'] = True
                self.rooms[room_id]['current_question'] = 0
            
            response = {
                'action': 'start_game_response',
                'status': 'success',
                'message': "Game started! All players will now begin the quiz."
            }
            self.send_message(self.clients[client_id]['socket'], response)
            
            # Notify all players in the room
            self.broadcast_room_update(room_id)
            
        except Exception as e:
            self.send_error(self.clients[client_id]['socket'], f"Failed to start game: {str(e)}")

    # Gameplay Handlers
    def handle_submit_answer(self, client_id, data):
        """Handle quiz answer submission"""
        username = self.clients[client_id].get('username')
        room_id = self.clients[client_id].get('room_id')
        question_index = data.get('question_index')
        answer = data.get('answer')
        
        if not all([username, room_id, question_index is not None, answer]):
            self.send_error(self.clients[client_id]['socket'], "Missing answer data")
            return
            
        try:
            room = self.rooms_collection.find_one({"room_id": room_id})
            if not room:
                self.send_error(self.clients[client_id]['socket'], "Room not found")
                return
                
            # Store answer
            player_answers = room.get('player_answers', {})
            if username not in player_answers:
                player_answers[username] = []
                
            # Ensure we have enough slots
            while len(player_answers[username]) <= question_index:
                player_answers[username].append(None)
                
            player_answers[username][question_index] = answer
            
            self.rooms_collection.update_one(
                {"room_id": room_id},
                {"$set": {"player_answers": player_answers}}
            )
            
            # Update in-memory data
            if room_id in self.rooms:
                self.rooms[room_id]['player_answers'] = player_answers
            
            response = {
                'action': 'submit_answer_response',
                'status': 'success',
                'message': "Answer submitted successfully!"
            }
            self.send_message(self.clients[client_id]['socket'], response)
            
            # Check if all questions answered and calculate role
            if len(player_answers[username]) == 5 and all(player_answers[username]):
                role = self.calculate_role(player_answers[username])
                
                # Store role
                player_roles = room.get('player_roles', {})
                player_roles[username] = role
                
                self.rooms_collection.update_one(
                    {"room_id": room_id},
                    {"$set": {"player_roles": player_roles}}
                )
                
                if room_id in self.rooms:
                    self.rooms[room_id]['player_roles'] = player_roles
                
                # Send role to player
                role_response = {
                    'action': 'role_assigned',
                    'status': 'success',
                    'data': {
                        'role': role
                    },
                    'message': f"Your role is: {role}"
                }
                self.send_message(self.clients[client_id]['socket'], role_response)
                
        except Exception as e:
            self.send_error(self.clients[client_id]['socket'], f"Failed to submit answer: {str(e)}")

    def handle_select_character(self, client_id, data):
        """Handle character selection"""
        username = self.clients[client_id].get('username')
        room_id = self.clients[client_id].get('room_id')
        character = data.get('character')
        
        if not all([username, room_id, character]):
            self.send_error(self.clients[client_id]['socket'], "Missing character data")
            return
            
        try:
            room = self.rooms_collection.find_one({"room_id": room_id})
            if not room:
                self.send_error(self.clients[client_id]['socket'], "Room not found")
                return
                
            # Check if character is already locked by another player
            player_characters = room.get('player_characters', {})
            if character in player_characters.values():
                self.send_error(self.clients[client_id]['socket'], "This character is already taken")
                return
                
            # Check if player already has a locked character
            character_locked = room.get('character_locked', {})
            if character_locked.get(username, False):
                self.send_error(self.clients[client_id]['socket'], "Your character is already locked and cannot be changed")
                return
                
            # Assign character
            player_characters[username] = character
            
            self.rooms_collection.update_one(
                {"room_id": room_id},
                {"$set": {"player_characters": player_characters}}
            )
            
            # Update in-memory data
            if room_id in self.rooms:
                self.rooms[room_id]['player_characters'] = player_characters
            
            response = {
                'action': 'select_character_response',
                'status': 'success',
                'data': {
                    'character': character
                },
                'message': f"Character {character} selected!"
            }
            self.send_message(self.clients[client_id]['socket'], response)
            
            # Update user's character in their profile
            self.users_collection.update_one(
                {"username": username},
                {"$set": {"character": character}}
            )
            
            # Notify all players in the room
            self.broadcast_room_update(room_id)
            
        except Exception as e:
            self.send_error(self.clients[client_id]['socket'], f"Failed to select character: {str(e)}")

    def handle_lock_character(self, client_id, data):
        """Handle character locking - once locked, cannot be changed"""
        username = self.clients[client_id].get('username')
        room_id = self.clients[client_id].get('room_id')
        
        if not all([username, room_id]):
            self.send_error(self.clients[client_id]['socket'], "Missing data for character lock")
            return
            
        try:
            room = self.rooms_collection.find_one({"room_id": room_id})
            if not room:
                self.send_error(self.clients[client_id]['socket'], "Room not found")
                return
                
            # Check if player has selected a character
            player_characters = room.get('player_characters', {})
            if username not in player_characters:
                self.send_error(self.clients[client_id]['socket'], "You must select a character before locking it")
                return
                
            # Lock character
            character_locked = room.get('character_locked', {})
            character_locked[username] = True
            
            self.rooms_collection.update_one(
                {"room_id": room_id},
                {"$set": {"character_locked": character_locked}}
            )
            
            # Update in-memory data
            if room_id in self.rooms:
                self.rooms[room_id]['character_locked'] = character_locked
            
            # Update client state
            self.clients[client_id]['character_locked'] = True
            
            response = {
                'action': 'lock_character_response',
                'status': 'success',
                'message': "Character locked! You cannot change it now."
            }
            self.send_message(self.clients[client_id]['socket'], response)
            
            # Notify all players in the room
            self.broadcast_room_update(room_id)
            
        except Exception as e:
            self.send_error(self.clients[client_id]['socket'], f"Failed to lock character: {str(e)}")

    def handle_leave_room(self, client_id, data):
        """Handle leaving a room"""
        username = self.clients[client_id].get('username')
        room_id = self.clients[client_id].get('room_id')
        
        if not username or not room_id:
            self.send_error(self.clients[client_id]['socket'], "Not in a room")
            return
            
        try:
            room = self.rooms_collection.find_one({"room_id": room_id})
            if not room:
                self.send_error(self.clients[client_id]['socket'], "Room not found")
                return
                
            # Remove player from room
            players = room.get('players', [])
            if username in players:
                players.remove(username)
                
            # Remove player's character and lock status
            player_characters = room.get('player_characters', {})
            if username in player_characters:
                del player_characters[username]
                
            character_locked = room.get('character_locked', {})
            if username in character_locked:
                del character_locked[username]
                
            # If room is empty, delete it
            if not players:
                self.rooms_collection.delete_one({"room_id": room_id})
                if room_id in self.rooms:
                    del self.rooms[room_id]
            else:
                # Update room
                self.rooms_collection.update_one(
                    {"room_id": room_id},
                    {"$set": {
                        "players": players,
                        "player_characters": player_characters,
                        "character_locked": character_locked
                    }}
                )
                
                # Update in-memory data
                if room_id in self.rooms:
                    self.rooms[room_id]['players'] = players
                    self.rooms[room_id]['player_characters'] = player_characters
                    self.rooms[room_id]['character_locked'] = character_locked
            
            # Clear client's room
            self.clients[client_id]['room_id'] = None
            self.clients[client_id]['character_locked'] = False
            
            response = {
                'action': 'leave_room_response',
                'status': 'success',
                'message': "Left the room successfully"
            }
            self.send_message(self.clients[client_id]['socket'], response)
            
            # Notify remaining players
            if players:
                self.broadcast_room_update(room_id)
            self.broadcast_room_list()
            
        except Exception as e:
            self.send_error(self.clients[client_id]['socket'], f"Failed to leave room: {str(e)}")

    def handle_get_room_status(self, client_id, data):
        """Handle request for room status"""
        room_id = self.clients[client_id].get('room_id')
        
        if not room_id:
            self.send_error(self.clients[client_id]['socket'], "Not in a room")
            return
            
        try:
            room = self.rooms_collection.find_one({"room_id": room_id})
            if not room:
                self.send_error(self.clients[client_id]['socket'], "Room not found")
                return
                
            response = {
                'action': 'room_status_response',
                'status': 'success',
                'data': {
                    'room_data': room
                }
            }
            self.send_message(self.clients[client_id]['socket'], response)
            
        except Exception as e:
            self.send_error(self.clients[client_id]['socket'], f"Failed to get room status: {str(e)}")

    # Utility Methods
    def validate_email(self, email):
        """Validate email format"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None

    def generate_room_id(self):
        """Generate unique room ID"""
        return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

    def calculate_role(self, answers):
        """Calculate role based on answers"""
        role_mapping = {
            'A': 'Barbarian / Monk (Melee DPS)',
            'B': 'Fighter/Knight (Tank)',
            'C': 'Rogue / Scout-Ranger (Stealth/Agile)',
            'D': 'Gunman / Ranger (Ranged Physical)',
            'E': 'Bard / Priest / Alchemist (Support/Healing)',
            'F': 'Wizard / Druids / Necromancer / Elementalist / Summoner / Sorcerer / Warlock (Magical Combatants)'
        }
        
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
        
        return role_mapping[chosen_option]

    def broadcast_room_update(self, room_id):
        """Broadcast room update to all players in the room"""
        try:
            room = self.rooms_collection.find_one({"room_id": room_id})
            if not room:
                return
                
            message = {
                'action': 'room_updated',
                'data': {
                    'room_data': room
                }
            }
            
            for client_id, client_data in self.clients.items():
                if client_data.get('room_id') == room_id:
                    self.send_message(client_data['socket'], message)
                    
        except Exception as e:
            print(f"❌ Error broadcasting room update: {e}")

    def broadcast_room_list(self):
        """Broadcast updated room list to all clients"""
        try:
            rooms = list(self.rooms_collection.find({"is_active": True}))
            
            message = {
                'action': 'rooms_updated',
                'data': {
                    'rooms': rooms
                }
            }
            
            for client_data in self.clients.values():
                self.send_message(client_data['socket'], message)
                
        except Exception as e:
            print(f"❌ Error broadcasting room list: {e}")

    def send_message(self, socket, message):
        """Send message to client"""
        try:
            socket.send(json.dumps(message).encode('utf-8'))
        except Exception as e:
            print(f"❌ Error sending message: {e}")

    def send_error(self, socket, error_message):
        """Send error message to client"""
        error_response = {
            'action': 'error',
            'status': 'error',
            'message': error_message
        }
        self.send_message(socket, error_response)

    def disconnect_client(self, client_id):
        """Handle client disconnection"""
        if client_id in self.clients:
            client_data = self.clients[client_id]
            
            # Leave room if in one
            room_id = client_data.get('room_id')
            if room_id:
                self.handle_leave_room(client_id, {})
                
            # Close socket
            try:
                client_data['socket'].close()
            except:
                pass
                
            # Remove from clients
            del self.clients[client_id]
            print(f"🔌 Client {client_id} disconnected")

if __name__ == "__main__":
    server = GameServer()
    server.start_server()