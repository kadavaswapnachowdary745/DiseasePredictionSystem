import logging
import sqlite3
from flask import Blueprint, request, jsonify, session
from models.user import User

logger = logging.getLogger('flask.app')
auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

@auth_bp.route('/register', methods=['POST'])
def register():
    """
    Registers a new user.
    Expects JSON: { "username": "...", "email": "...", "password": "..." }
    """
    data = request.get_json() or {}
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    
    # Input validation
    if not username or not email or not password:
        logger.warning("Registration attempt rejected: missing credentials fields.")
        return jsonify({'error': 'Username, email, and password are required.'}), 400
        
    username = username.strip()
    email = email.strip().lower()
    
    if len(username) < 3:
        logger.warning(f"Registration attempt rejected: username '{username}' too short.")
        return jsonify({'error': 'Username must be at least 3 characters long.'}), 400
    if len(password) < 6:
        logger.warning("Registration attempt rejected: password too short.")
        return jsonify({'error': 'Password must be at least 6 characters long.'}), 400
        
    try:
        logger.info(f"Checking credentials uniqueness for username: {username}, email: {email}")
        # Check uniqueness manually to give clean error responses
        if User.get_by_username(username):
            logger.warning(f"Registration duplicate: Username '{username}' already taken.")
            return jsonify({'error': 'Username is already taken.'}), 400
        if User.get_by_email(email):
            logger.warning(f"Registration duplicate: Email '{email}' already registered.")
            return jsonify({'error': 'Email is already registered.'}), 400
            
        # Create user
        user_id = User.create(username, email, password)
        logger.info(f"User '{username}' registered successfully. Assigned ID: {user_id}")
        return jsonify({
            'message': 'Registration successful.',
            'user_id': user_id
        }), 201
        
    except sqlite3.IntegrityError:
        logger.warning(f"Integrity check failed: duplicate username or email exists in DB during registration attempt of {username}.")
        return jsonify({'error': 'Username or email already exists.'}), 400
    except Exception as e:
        logger.error(f"Exception during registration process: {str(e)}")
        return jsonify({'error': f'Registration failed: {str(e)}'}), 500

@auth_bp.route('/login', methods=['POST'])
def login():
    """
    Authenticates an existing user and starts a session.
    Expects JSON: { "username": "...", "password": "..." }
    """
    data = request.get_json() or {}
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        logger.warning("Login attempt rejected: missing username or password fields.")
        return jsonify({'error': 'Username and password are required.'}), 400
        
    username = username.strip()
    logger.info(f"Processing login credentials check for: {username}")
    
    user = User.get_by_username(username)
    if not user or not User.verify_password(user['password_hash'], password):
        logger.warning(f"Failed login attempt: invalid credentials for username: {username}")
        return jsonify({'error': 'Invalid username or password.'}), 401
        
    # Clear any existing session and store credentials
    session.clear()
    session['user_id'] = user['id']
    session['username'] = user['username']
    
    logger.info(f"Session started: User '{username}' authenticated successfully.")
    return jsonify({
        'message': 'Login successful.',
        'user': {
            'id': user['id'],
            'username': user['username'],
            'email': user['email']
        }
    }), 200

@auth_bp.route('/logout', methods=['POST'])
def logout():
    """Ends the user's session."""
    user_id = session.get('user_id')
    username = session.get('username')
    logger.info(f"Ending session: User '{username}' (ID: {user_id}) requested logout.")
    session.clear()
    return jsonify({'message': 'Logged out successfully.'}), 200

@auth_bp.route('/me', methods=['GET'])
def get_me():
    """Returns details of the currently authenticated user based on session."""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Not authenticated.'}), 401
        
    user = User.get_by_id(user_id)
    if not user:
        session.clear()
        return jsonify({'error': 'Invalid session.'}), 401
        
    return jsonify({'user': user}), 200
