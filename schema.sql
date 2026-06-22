-- Enable Foreign Key constraints
PRAGMA foreign_keys = ON;

-- Users Table
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Predictions Table
CREATE TABLE IF NOT EXISTS predictions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    symptoms TEXT NOT NULL,          -- JSON serialized list of symptoms
    predicted_disease TEXT NOT NULL,
    confidence REAL NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);

-- Disease Info Table
CREATE TABLE IF NOT EXISTS disease_info (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    description TEXT NOT NULL,
    causes TEXT NOT NULL,            -- JSON serialized list of causes
    symptoms TEXT NOT NULL,          -- JSON serialized list of typical symptoms
    precautions TEXT NOT NULL,       -- JSON serialized list of precautions
    diet_recommendations TEXT NOT NULL, -- JSON serialized list of diet recommendations
    lifestyle_changes TEXT NOT NULL,    -- JSON serialized list of lifestyle changes
    recommended_doctor TEXT NOT NULL
);

-- Chat History Table
CREATE TABLE IF NOT EXISTS chat_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    sender TEXT NOT NULL,            -- 'user' or 'bot'
    message TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);


