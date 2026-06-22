from db import query_db, insert_db
from werkzeug.security import generate_password_hash, check_password_hash

class User:
    @staticmethod
    def create(username, email, password):
        """
        Creates a new user record in the database with a hashed password.
        Returns the user ID on success.
        """
        password_hash = generate_password_hash(password)
        # Note: Database constraints (UNIQUE) will naturally raise an sqlite3.IntegrityError
        # if the username or email is already taken.
        user_id = insert_db(
            "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
            (username, email, password_hash)
        )
        return user_id

    @staticmethod
    def get_by_username(username):
        """Retrieves a user dictionary by their username, including their password hash."""
        row = query_db("SELECT * FROM users WHERE username = ?", (username,), one=True)
        return dict(row) if row else None

    @staticmethod
    def get_by_email(email):
        """Retrieves a user dictionary by their email."""
        row = query_db("SELECT * FROM users WHERE email = ?", (email,), one=True)
        return dict(row) if row else None

    @staticmethod
    def get_by_id(user_id):
        """Retrieves a user's details (excluding password hash) by their ID."""
        row = query_db("SELECT id, username, email, created_at FROM users WHERE id = ?", (user_id,), one=True)
        return dict(row) if row else None

    @staticmethod
    def verify_password(password_hash, password):
        """Verifies a plain-text password against the stored password hash."""
        return check_password_hash(password_hash, password)
