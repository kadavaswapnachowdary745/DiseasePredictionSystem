import json
from db import query_db, insert_db

class Prediction:
    @staticmethod
    def create(user_id, symptoms, predicted_disease, confidence, prediction_type='General'):
        """
        Saves a new disease prediction entry in the database.
        - symptoms: a list or dict of input symptoms/attributes
        - predicted_disease: string name of the diagnosed disease
        - confidence: float representing prediction confidence or probability
        - prediction_type: 'General' or 'Specialized'
        """
        symptoms_str = json.dumps(symptoms) if isinstance(symptoms, (list, dict)) else str(symptoms)
        prediction_id = insert_db(
            "INSERT INTO predictions (user_id, symptoms, predicted_disease, confidence, prediction_type) VALUES (?, ?, ?, ?, ?)",
            (user_id, symptoms_str, predicted_disease, confidence, prediction_type)
        )
        return prediction_id

    @staticmethod
    def get_history_by_user(user_id):
        """
        Fetches the complete prediction history for a user ID,
        ordered from newest to oldest.
        """
        rows = query_db(
            "SELECT id, symptoms, predicted_disease, confidence, prediction_type, created_at "
            "FROM predictions "
            "WHERE user_id = ? "
            "ORDER BY created_at DESC",
            (user_id,)
        )
        
        history = []
        for row in rows:
            record = dict(row)
            try:
                record['symptoms'] = json.loads(record['symptoms'])
            except (json.JSONDecodeError, TypeError):
                pass
            if 'prediction_type' not in record or not record['prediction_type']:
                record['prediction_type'] = 'General'
            history.append(record)
            
        return history

    @staticmethod
    def get_by_id(prediction_id):
        """Retrieves a single prediction entry by its ID."""
        row = query_db(
            "SELECT id, user_id, symptoms, predicted_disease, confidence, prediction_type, created_at "
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
            pass
        if 'prediction_type' not in record or not record['prediction_type']:
            record['prediction_type'] = 'General'
            
        return record

