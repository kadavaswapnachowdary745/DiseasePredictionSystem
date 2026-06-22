import os
from flask import Flask, jsonify, render_template, redirect, url_for, session
from flask_cors import CORS
from config import Config
from db import init_db, close_db
from controllers.auth import auth_bp
from controllers.prediction import predict_bp

def create_app():
    """Application factory to configure and return the Flask application."""
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Configure CORS. Allow credentials (cookies) to persist sessions from a frontend client.
    CORS(app, supports_credentials=True)
    
    # Register DB connection cleanup teardown hook
    app.teardown_appcontext(close_db)
    
    # Register controllers (Blueprints)
    app.register_blueprint(auth_bp)
    app.register_blueprint(predict_bp)
    
    # UI Navigation Routes
    @app.route('/')
    def index():
        return redirect(url_for('dashboard'))

    @app.route('/login')
    def login():
        # If user is already authenticated, redirect them to dashboard
        if 'user_id' in session:
            return redirect(url_for('dashboard'))
        return render_template('login.html')

    @app.route('/register')
    def register():
        # If user is already authenticated, redirect them to dashboard
        if 'user_id' in session:
            return redirect(url_for('dashboard'))
        return render_template('register.html')

    @app.route('/dashboard')
    def dashboard():
        # If user is not authenticated, redirect to login
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return render_template('dashboard.html')

        
    # Error handling overrides to return clean JSON messages
    @app.errorhandler(400)
    def bad_request(error):
        return jsonify({'error': 'Bad request. Please verify inputs.'}), 400

    @app.errorhandler(401)
    def unauthorized(error):
        return jsonify({'error': 'Authentication required.'}), 401

    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'error': 'The requested route or resource was not found.'}), 404

    @app.errorhandler(500)
    def server_error(error):
        return jsonify({'error': 'Internal server error occurred.'}), 500
        
    @app.errorhandler(Exception)
    def unhandled_exception(e):
        # Fallback handler for raw exceptions
        return jsonify({'error': f'Unhandled system error: {str(e)}'}), 500

    return app

if __name__ == '__main__':
    # Initialize SQLite database (runs schema.sql commands to build tables if missing)
    print("Checking database status...")
    init_db()
    
    app = create_app()
    print("Starting Flask application server...")
    port = int(os.environ.get('PORT', 5001))
    app.run(host='0.0.0.0', port=port, debug=True)

