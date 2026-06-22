import json
from db import query_db, insert_db

class Prediction:
    @staticmethod
    def create(user_id, symptoms, predicted_disease, confidence):
        """
        Saves a new disease prediction entry in the database.
        - symptoms: a list of symptom strings (e.g., ['fever', 'cough'])
        - predicted_disease: string name of the diagnosed disease
        - confidence: float representing prediction confidence
        """
        symptoms_str = json.dumps(symptoms)
        prediction_id = insert_db(
            "INSERT INTO predictions (user_id, symptoms, predicted_disease, confidence) VALUES (?, ?, ?, ?)",
            (user_id, symptoms_str, predicted_disease, confidence)
        )
        return prediction_id

    @staticmethod
    def get_history_by_user(user_id):
        """
        Fetches the complete prediction history for a user ID,
        ordered from newest to oldest.
        """
        rows = query_db(
            "SELECT id, symptoms, predicted_disease, confidence, created_at "
            "FROM predictions "
            "WHERE user_id = ? "
            "ORDER BY created_at DESC",
            (user_id,)
        )
        
        history = []
        for row in rows:
            record = dict(row)
            try:
                # Deserialize the JSON string of symptoms back to a list
                record['symptoms'] = json.loads(record['symptoms'])
            except (json.JSONDecodeError, TypeError):
                # Fallback in case of parse error
                record['symptoms'] = []
            history.append(record)
            
        return history

    @staticmethod
    def get_by_id(prediction_id):
        """Retrieves a single prediction entry by its ID."""
        row = query_db(
            "SELECT id, user_id, symptoms, predicted_disease, confidence, created_at "
            "FROM predictions "
            "WHERE id = ?",
            (prediction_id,),
            one=True
        )
        if not row:
            return None
            
        record = dict(row)
        try:
            record['symptoms'] = json.loads(record['symptoms'])
        except (json.JSONDecodeError, TypeError):
            record['symptoms'] = []
            
        return record

