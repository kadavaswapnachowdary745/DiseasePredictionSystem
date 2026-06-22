import json
from db import query_db

class Disease:
    @staticmethod
    def get_by_name(name):
        """
        Retrieves details of a disease from the database by its name.
        Returns a dictionary with deserialized lists for causes, symptoms, and precautions.
        """
        row = query_db(
            "SELECT name, description, causes, symptoms, precautions, recommended_doctor "
            "FROM disease_info "
            "WHERE name = ?",
            (name,),
            one=True
        )
        
        if not row:
            return None
            
        record = dict(row)
        
        # Deserialize JSON arrays to standard python lists
        try:
            record['causes'] = json.loads(record['causes'])
        except (json.JSONDecodeError, TypeError):
            record['causes'] = []
            
        try:
            record['symptoms'] = json.loads(record['symptoms'])
        except (json.JSONDecodeError, TypeError):
            record['symptoms'] = []
            
        try:
            record['precautions'] = json.loads(record['precautions'])
        except (json.JSONDecodeError, TypeError):
            record['precautions'] = []
            
        return record
