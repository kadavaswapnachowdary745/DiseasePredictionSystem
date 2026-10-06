import logging
from flask import Blueprint, request, jsonify, session
from models.chat import ChatHistory
from services.chat_service import (
    generate_chat_response,
    clean_input,
    FAQS,
    DISEASE_KEYS,
    MEDICAL_DISCLAIMER
)

logger = logging.getLogger('flask.app')
chat_bp = Blueprint('chat', __name__, url_prefix='/api/chat')


@chat_bp.route('/message', methods=['POST'])
def send_message():
    """
    Receives user message. Returns the matched response.
    Saves the user query and the bot response in SQLite.
    """
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Not authenticated.'}), 401

    data = request.get_json() or {}
    message_text = data.get('message', '').strip()

    if not message_text:
        return jsonify({'error': 'Message cannot be empty.'}), 400

    response_text, is_emergency = generate_chat_response(user_id, message_text)

    # Save to database
    ChatHistory.create_message(user_id, 'user', message_text)
    ChatHistory.create_message(user_id, 'bot', response_text)

    return jsonify({
        'message': response_text,
        'is_emergency': is_emergency
    }), 200

@chat_bp.route('/history', methods=['GET'])
def get_chat_history():
    """Retrieves chat history for the logged-in user."""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Not authenticated.'}), 401

    try:
        history = ChatHistory.get_history_by_user(user_id)
        return jsonify({'history': history}), 200
    except Exception as e:
        return jsonify({'error': f"Failed to retrieve chat history: {str(e)}"}), 500

@chat_bp.route('/clear', methods=['POST'])
def clear_chat_history():
    """Clears all chat logs for the logged-in user."""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Not authenticated.'}), 401

    try:
        ChatHistory.clear_history(user_id)
        return jsonify({'message': 'Chat history successfully cleared.'}), 200
    except Exception as e:
        return jsonify({'error': f"Failed to clear chat history: {str(e)}"}), 500
