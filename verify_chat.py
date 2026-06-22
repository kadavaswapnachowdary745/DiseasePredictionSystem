import json
import os
import unittest
from app import create_app
from db import init_db, get_db_connection
from models.chat import ChatHistory
from models.prediction import Prediction
from controllers.chat import MEDICAL_DISCLAIMER

class TestChatbotAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Initialize database tables (seeds updated profiles)
        init_db()
        
    def setUp(self):
        # Create Flask app instance and client
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()
        
        # Clear database tables to ensure tests are isolated
        conn = get_db_connection()
        conn.execute("DELETE FROM chat_history")
        conn.execute("DELETE FROM predictions")
        conn.execute("DELETE FROM users")
        conn.commit()
        conn.close()

        # Seed a test user for auth sessions
        self.register_and_login()

    def register_and_login(self):
        # Register test member
        register_payload = {
            'username': 'chatpatient',
            'email': 'patient@chat.com',
            'password': 'securepassword'
        }
        self.client.post('/api/auth/register', json=register_payload)
        
        # Login to start session
        login_payload = {
            'username': 'chatpatient',
            'password': 'securepassword'
        }
        res = self.client.post('/api/auth/login', json=login_payload)
        self.user_data = res.get_json()['user']

    def test_database_model_operations(self):
        print("\n--- Test 1: ChatHistory DB Model Operations ---")
        user_id = self.user_data['id']
        
        # Write user and bot message logs
        msg_id1 = ChatHistory.create_message(user_id, 'user', "Hello Assistant")
        msg_id2 = ChatHistory.create_message(user_id, 'bot', "Hello! How can I help you?")
        
        self.assertIsNotNone(msg_id1)
        self.assertIsNotNone(msg_id2)
        
        # Fetch history
        history = ChatHistory.get_history_by_user(user_id)
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0]['sender'], 'user')
        self.assertEqual(history[0]['message'], "Hello Assistant")
        self.assertEqual(history[1]['sender'], 'bot')
        self.assertEqual(history[1]['message'], "Hello! How can I help you?")
        print("Successfully verified saving and retrieving chat history in DB.")

        # Clear history
        ChatHistory.clear_history(user_id)
        history_after = ChatHistory.get_history_by_user(user_id)
        self.assertEqual(len(history_after), 0)
        print("Successfully verified clearing chat history in DB.")

    def test_emergency_warning_response(self):
        print("\n--- Test 2: Chatbot Emergency Detection Warning ---")
        # Post a message containing emergency symptoms: chest pain
        payload = {'message': "I am experiencing severe chest pain and dizziness"}
        res = self.client.post('/api/chat/message', json=payload)
        data = res.get_json()
        
        self.assertEqual(res.status_code, 200)
        self.assertTrue(data['is_emergency'])
        self.assertIn("EMERGENCY WARNING", data['message'])
        self.assertIn("chest pain", data['message'])
        print("Verified chatbot emergency warning for 'chest pain'.")

        # Post a message containing loss of consciousness
        payload2 = {'message': "Someone passed out and has loss of consciousness"}
        res2 = self.client.post('/api/chat/message', json=payload2)
        data2 = res2.get_json()
        
        self.assertEqual(res2.status_code, 200)
        self.assertTrue(data2['is_emergency'])
        self.assertIn("EMERGENCY WARNING", data2['message'])
        print("Verified chatbot emergency warning for 'loss of consciousness'.")

    def test_greeting_and_faqs(self):
        print("\n--- Test 3: Chatbot Greetings and FAQs ---")
        # Greetings
        res = self.client.post('/api/chat/message', json={'message': "Hi there!"})
        data = res.get_json()
        self.assertEqual(res.status_code, 200)
        self.assertIn("AI Health Assistant", data['message'])
        print("Verified greeting intent match.")

        # FAQ: Boost immune system
        res_faq = self.client.post('/api/chat/message', json={'message': "How do I boost my immune system?"})
        data_faq = res_faq.get_json()
        self.assertEqual(res_faq.status_code, 200)
        self.assertIn("To help support and boost your immune system", data_faq['message'])
        self.assertIn("Diet", data_faq['message'])
        print("Verified immune system FAQ match.")

        # FAQ: Daily water intake
        res_faq2 = self.client.post('/api/chat/message', json={'message': "how much water should I drink daily?"})
        data_faq2 = res_faq2.get_json()
        self.assertEqual(res_faq2.status_code, 200)
        self.assertIn("8 to 10 glasses", data_faq2['message'])
        print("Verified water intake FAQ match.")

    def test_specific_disease_queries(self):
        print("\n--- Test 4: Specific Disease Detail Matches ---")
        # Ask about Diabetes general description
        res = self.client.post('/api/chat/message', json={'message': "Tell me about Diabetes"})
        data = res.get_json()
        self.assertEqual(res.status_code, 200)
        self.assertIn("Diabetes", data['message'])
        self.assertIn("Description", data['message'])
        self.assertIn("Diet Recommendations", data['message'])
        self.assertIn("Lifestyle Changes", data['message'])
        print("Verified specific disease query match for Diabetes.")

        # Ask about precautions for Jaundice
        res_prec = self.client.post('/api/chat/message', json={'message': "What are the precautions for jaundice?"})
        data_prec = res_prec.get_json()
        self.assertEqual(res_prec.status_code, 200)
        self.assertIn("precautions for **Jaundice**", data_prec['message'])
        self.assertIn("Avoid fatty, fried, and heavy foods", data_prec['message'])
        print("Verified specific disease precautions sub-intent for Jaundice.")

        # Ask about diet for Covid-19
        res_diet = self.client.post('/api/chat/message', json={'message': "what diet recommendations are for covid-19?"})
        data_diet = res_diet.get_json()
        self.assertEqual(res_diet.status_code, 200)
        self.assertIn("Diet recommendations for **Covid-19**", data_diet['message'])
        self.assertIn("High-protein foods", data_diet['message'])
        print("Verified specific disease diet sub-intent for Covid-19.")

    def test_prediction_context_explanations(self):
        print("\n--- Test 5: Prediction Context Explanations ---")
        
        # 1. Check message before any prediction runs
        res = self.client.post('/api/chat/message', json={'message': "Explain my latest prediction"})
        data = res.get_json()
        self.assertEqual(res.status_code, 200)
        self.assertIn("You do not have any prediction history", data['message'])
        print("Verified no-prediction-history case.")

        # 2. Seed a prediction (e.g. Diabetes)
        Prediction.create(
            user_id=self.user_data['id'],
            symptoms=['increased_thirst', 'frequent_urination', 'fatigue'],
            predicted_disease='Diabetes',
            confidence=0.92
        )

        # 3. Check explanation query now
        res_explain = self.client.post('/api/chat/message', json={'message': "Explain my prediction"})
        data_explain = res_explain.get_json()
        self.assertEqual(res_explain.status_code, 200)
        self.assertIn("Your latest prediction was **Diabetes**", data_explain['message'])
        self.assertIn("Description", data_explain['message'])
        self.assertIn("Diet Recommendations", data_explain['message'])
        print("Verified contextual explanation of latest prediction.")

        # 4. Check precautions query for latest prediction
        res_prec = self.client.post('/api/chat/message', json={'message': "Suggest precautions for my predicted disease"})
        data_prec = res_prec.get_json()
        self.assertEqual(res_prec.status_code, 200)
        self.assertIn("precautions", data_prec['message'].lower())
        self.assertIn("diabetes", data_prec['message'].lower())
        print("Verified contextual precautions query for latest prediction.")

    def test_chat_history_endpoints(self):
        print("\n--- Test 6: Chat History API Endpoints ---")
        user_id = self.user_data['id']
        
        # Post messages
        self.client.post('/api/chat/message', json={'message': "Hello bot!"})
        self.client.post('/api/chat/message', json={'message': "Tell me about Migraine"})

        # GET history log
        res = self.client.get('/api/chat/history')
        data = res.get_json()
        self.assertEqual(res.status_code, 200)
        # There should be 4 messages in log: 2 users, 2 bots
        self.assertEqual(len(data['history']), 4)
        self.assertEqual(data['history'][0]['sender'], 'user')
        self.assertEqual(data['history'][0]['message'], "Hello bot!")
        self.assertEqual(data['history'][2]['sender'], 'user')
        self.assertEqual(data['history'][2]['message'], "Tell me about Migraine")
        print("Verified fetching chat history via HTTP GET.")

        # POST clear log
        res_clear = self.client.post('/api/chat/clear')
        self.assertEqual(res_clear.status_code, 200)
        
        res_after = self.client.get('/api/chat/history')
        self.assertEqual(len(res_after.get_json()['history']), 0)
        print("Verified clearing chat history via HTTP POST.")

if __name__ == '__main__':
    unittest.main()
