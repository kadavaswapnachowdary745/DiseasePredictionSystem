import json
import os
import unittest
from app import create_app
from db import init_db, get_db_connection

class TestBackendAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Initialize database tables
        init_db()
        
    def setUp(self):
        # Create Flask app instance and client
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()
        
        # Clear database records to ensure tests are isolated
        conn = get_db_connection()
        conn.execute("DELETE FROM predictions")
        conn.execute("DELETE FROM users")
        conn.commit()
        conn.close()

    def test_full_flow(self):
        print("\n--- Running Backend Integration Tests ---")
        
        # 1. Test registration
        register_payload = {
            'username': 'testdoctor',
            'email': 'doctor@hospital.com',
            'password': 'securepassword123'
        }
        res = self.client.post('/api/auth/register', json=register_payload)
        print(f"Register status: {res.status_code}, data: {res.get_json()}")
        self.assertEqual(res.status_code, 201)
        self.assertIn('user_id', res.get_json())
        
        # 2. Test duplicate registration (should fail)
        res_dup = self.client.post('/api/auth/register', json=register_payload)
        print(f"Duplicate register check status: {res_dup.status_code}, error message: {res_dup.get_json().get('error')}")
        self.assertEqual(res_dup.status_code, 400)
        
        # 3. Test login
        login_payload = {
            'username': 'testdoctor',
            'password': 'securepassword123'
        }
        res_login = self.client.post('/api/auth/login', json=login_payload)
        print(f"Login status: {res_login.status_code}, data: {res_login.get_json()}")
        self.assertEqual(res_login.status_code, 200)
        self.assertIn('user', res_login.get_json())
        
        # 4. Test authenticated profile retrieval (GET /api/auth/me)
        res_me = self.client.get('/api/auth/me')
        print(f"Get Me profile status: {res_me.status_code}, username: {res_me.get_json().get('user', {}).get('username')}")
        self.assertEqual(res_me.status_code, 200)
        
        # 5. Test ML prediction (while logged in)
        # Fever, Cough, Body Ache, Fatigue, Chills should trigger Influenza (Flu) or Covid-19
        predict_payload = {
            'symptoms': ['fever', 'cough', 'body_ache', 'fatigue', 'chills']
        }
        res_predict = self.client.post('/api/predict', json=predict_payload)
        data_predict = res_predict.get_json()
        print(f"Predict status: {res_predict.status_code}, output disease: {data_predict.get('disease')} (confidence: {data_predict.get('confidence')}), saved_to_history: {data_predict.get('saved_to_history')}")
        self.assertEqual(res_predict.status_code, 200)
        self.assertEqual(data_predict.get('saved_to_history'), True)
        self.assertIn(data_predict.get('disease'), ['Influenza (Flu)', 'Covid-19'])
        
        # Verify the presence of disease details fetched from database
        self.assertIn('disease_details', data_predict)
        details = data_predict.get('disease_details')
        self.assertIsNotNone(details)
        self.assertEqual(details['name'], data_predict['disease'])
        self.assertIn('description', details)
        self.assertIn('recommended_doctor', details)
        self.assertIsInstance(details['causes'], list)
        self.assertIsInstance(details['precautions'], list)
        print(f"Verified DB-sourced details in API: Description={details['description'][:40]}..., Doctor={details['recommended_doctor']}")

        # Verify PDF report generation (GET /api/predictions/<id>/pdf)
        prediction_id = data_predict.get('prediction_id')
        self.assertIsNotNone(prediction_id)
        
        res_pdf = self.client.get(f'/api/predictions/{prediction_id}/pdf')
        print(f"PDF download status: {res_pdf.status_code}, content type: {res_pdf.content_type}, size: {len(res_pdf.data)} bytes")
        self.assertEqual(res_pdf.status_code, 200)
        self.assertEqual(res_pdf.content_type, 'application/pdf')
        self.assertTrue(len(res_pdf.data) > 0)
        
        # 6. Test prediction history retrieval
        res_history = self.client.get('/api/predictions/history')
        data_history = res_history.get_json()
        print(f"Get History status: {res_history.status_code}, records found: {len(data_history.get('history', []))}")
        self.assertEqual(res_history.status_code, 200)
        self.assertEqual(len(data_history.get('history', [])), 1)
        self.assertIn(data_history['history'][0]['predicted_disease'], ['Influenza (Flu)', 'Covid-19'])

        
        # 7. Test logout
        res_logout = self.client.post('/api/auth/logout')
        print(f"Logout status: {res_logout.status_code}, message: {res_logout.get_json().get('message')}")
        self.assertEqual(res_logout.status_code, 200)
        
        # 8. Test history retrieval after logout (should fail)
        res_history_anon = self.client.get('/api/predictions/history')
        print(f"Anonymous history check status: {res_history_anon.status_code}, error message: {res_history_anon.get_json().get('error')}")
        self.assertEqual(res_history_anon.status_code, 401)
        
        print("------------------------------------------\n")

if __name__ == '__main__':
    unittest.main()
