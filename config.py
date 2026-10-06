import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    # A standard secret key for signing session cookies. In production, this would be set as an environment variable.
    SECRET_KEY = os.environ.get('SECRET_KEY', 'disease_prediction_super_secret_key_12345')

    # Stable absolute SQLite path for persistent app data.
    DATABASE_PATH = os.path.join(BASE_DIR, 'database.db')
