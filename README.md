# Disease Prediction System Using Machine Learning

A complete Python-based medical AI mini-project that generates a clinical dataset, trains a Random Forest Classifier to identify 20 diseases from 42 symptoms, and exposes a production-ready Flask REST API with SQLite database integration, session-based authentication, password hashing, and user prediction history logs.

---

## 📁 Project Folder Structure

```
mini_project/
├── data/
│   └── disease_symptoms.csv       # Synthetic dataset (1,600 samples, 42 symptoms, 20 diseases)
├── models/
│   ├── disease_model.pkl          # Trained Random Forest model (joblib)
│   ├── symptoms.json              # Symptom features list defining columns order
│   ├── user.py                 # User database query model (password hashing)
│   └── prediction.py           # Prediction database logger model
├── controllers/
│   ├── auth.py                 # User authentication routing blueprint
│   └── prediction.py           # ML prediction & history routing blueprint
├── app.py                      # Main Flask server entrypoint (CORS, error handers)
├── config.py                   # Global configuration for SQLite DB and Secret Key
├── db.py                       # SQLite connection pooling and initialization logic
├── schema.sql                  # SQLite database table definitions DDL
├── generate_dataset.py            # Dataset generator script
├── train_model.py                 # ML training and evaluation script
├── verify_backend.py              # Automated test client script (uses Flask TestClient)
├── requirements.txt               # Python library dependencies
└── README.md                      # Project documentation (this file)
```

---

## 📄 File Explanations

### 1. `requirements.txt`
Declares the third-party Python packages:
- `scikit-learn` & `pandas` & `numpy`: Machine Learning and data manipulation tools.
- `joblib`: Serializes the Scikit-learn model object to disk.
- `Flask` & `Flask-Cors` & `werkzeug`: Web framework, Cross-Origin Request configuration, and secure password hashing algorithms.

### 2. `generate_dataset.py`
Generates a realistic clinical dataset of 1,600 samples covering **20 diseases** and **42 symptoms** based on localized symptom probability distributions with added noise (2%). Saves output to `data/disease_symptoms.csv`.

### 3. `train_model.py`
Builds and evaluates the machine learning model:
- Implements stratified train-test splits (80-20).
- Fits a `RandomForestClassifier` (100 decision trees) achieving **95% accuracy**.
- Saves model to `models/disease_model.pkl` and mapping headers to `models/symptoms.json`.

### 4. Database Layer (`schema.sql`, `db.py`, `config.py`)
- `schema.sql`: Standard DDL defining the SQLite schema:
  - **`users` Table**: `id`, `username` (unique), `email` (unique), `password_hash`, `created_at`.
  - **`predictions` Table**: `id`, `user_id` (foreign key), `symptoms` (JSON list), `predicted_disease`, `confidence`, `created_at`.
- `db.py`: Connects to SQLite and populates database tables upon app startup.

### 5. MVC Models (`models/user.py`, `models/prediction.py`)
Encapsulates SQLite interactions:
- `user.py`: Creates user profiles with hashed passwords using Werkzeug `generate_password_hash` and checks passwords with `check_password_hash`.
- `prediction.py`: Stores predictions and queries database logs sorted chronologically.

### 6. MVC Controllers (`controllers/auth.py`, `controllers/prediction.py`)
API endpoints structuring system inputs and outputs:
- `auth.py`: Controls routes `/api/auth/register`, `/api/auth/login`, `/api/auth/logout`, and `/api/auth/me`.
- `prediction.py`:
  - `/api/predict` (POST): Accepts JSON list of symptoms, computes predictions using the trained model, and logs outputs to database if session is active.
  - `/api/predictions/history` (GET): Fetches user history records.

---

## ⚡ API Endpoints reference

| Method | Endpoint | Description | Auth Required | Payload / Response |
| :--- | :--- | :--- | :---: | :--- |
| **POST** | `/api/auth/register` | Register a new user profile | No | `{ "username": "doc", "email": "doc@hosp.com", "password": "password123" }` |
| **POST** | `/api/auth/login` | Authenticate user and start session | No | `{ "username": "doc", "password": "password123" }` |
| **POST** | `/api/auth/logout` | End active session | No | `{}` |
| **GET** | `/api/auth/me` | Fetch active user credentials | Yes | Returns user metadata |
| **POST** | `/api/predict` | Get ML disease classification | No | Send `{ "symptoms": ["cough", "fever"] }` |
| **GET** | `/api/predictions/history` | Retrieve prediction history | Yes | Returns list of user's predictions |

---

## 🚀 How to Run

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Generate Dataset and Train Model**:
   ```bash
   python3 generate_dataset.py
   python3 train_model.py
   ```

3. **Verify API Endpoints**:
   ```bash
   python3 verify_backend.py
   ```

4. **Launch Flask Server**:
   ```bash
   python3 app.py
   ```
   The server will start running on `http://localhost:5000`.
