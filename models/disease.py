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
            "SELECT name, description, causes, symptoms, precautions, diet_recommendations, lifestyle_changes, recommended_doctor "
            "FROM disease_info "
            "WHERE name = ?",
            (name,),
            one=True
        )
        
        if not row:
            return None
            
        record = dict(row)
        
        # Deserialize JSON arrays to standard python lists
        for list_field in ['causes', 'symptoms', 'precautions', 'diet_recommendations', 'lifestyle_changes']:
            try:
                record[list_field] = json.loads(record[list_field]) if record.get(list_field) else []
            except (json.JSONDecodeError, TypeError):
                record[list_field] = []
                
        return record
