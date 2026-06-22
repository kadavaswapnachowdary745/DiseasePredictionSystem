import os

class Config:
    # A standard secret key for signing session cookies. In production, this would be set as an environment variable.
    SECRET_KEY = os.environ.get('SECRET_KEY', 'disease_prediction_super_secret_key_12345')
    
    # Path to the SQLite database
    DATABASE_PATH = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'database.db')
