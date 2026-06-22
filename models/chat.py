from db import query_db, insert_db

class ChatHistory:
    @staticmethod
    def create_message(user_id, sender, message):
        """
        Saves a new chat message entry.
        - user_id: integer ID of the user
        - sender: string 'user' or 'bot'
        - message: string message content
        """
        message_id = insert_db(
            "INSERT INTO chat_history (user_id, sender, message) VALUES (?, ?, ?)",
            (user_id, sender, message)
        )
        return message_id

    @staticmethod
    def get_history_by_user(user_id, limit=50):
        """
        Fetches the chat history log for a specific user ID,
        ordered chronologically (oldest to newest) to display in the chat window.
        """
        rows = query_db(
            "SELECT id, sender, message, created_at "
            "FROM chat_history "
            "WHERE user_id = ? "
            "ORDER BY created_at ASC, id ASC "
            "LIMIT ?",
            (user_id, limit)
        )
        
        history = []
        for row in rows:
            history.append(dict(row))
            
        return history

    @staticmethod
    def clear_history(user_id):
        """Deletes all chat messages for a specific user ID."""
        insert_db(
            "DELETE FROM chat_history WHERE user_id = ?",
            (user_id,)
        )
        return True
