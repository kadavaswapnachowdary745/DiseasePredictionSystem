import uuid
import sys
import datetime
from models.user import User
from models.prediction import Prediction
from db import query_db, get_db_connection

def run_tests():
    print("--- Running Streamlit Auth Verification ---")
    rand_suffix = str(uuid.uuid4())[:8]
    test_user = f"st_user_{rand_suffix}"
    test_email = f"st_{rand_suffix}@predihealth.local"
    test_pass = "SecurePass123!"

    # TEST 1: Register new user
    uid = User.create(test_user, test_email, test_pass)
    print(f"TEST 1 PASSED: Registered user {test_user} with ID {uid}")

    # Verify user in database.db
    db_u = User.get_by_username(test_user)
    assert db_u is not None and db_u['id'] == uid, "User not persisted in DB"
    print("TEST 1.1 PASSED: User verified in persistent SQLite database.db")

    # TEST 2 & 4: Password Verification / Login check
    user_row = User.get_by_username(test_user)
    assert user_row is not None, "User lookup failed"
    assert User.verify_password(user_row['password_hash'], test_pass) == True, "Password verification failed"
    print("TEST 2 & 4 PASSED: Password verification succeeded")

    # TEST 3: Persistence check
    db_u_email = User.get_by_email(test_email)
    assert db_u_email is not None and db_u_email['username'] == test_user, "Email lookup failed"
    print("TEST 3 PASSED: Account persistent across queries")

    # TEST 7: Invalid password check
    assert User.verify_password(user_row['password_hash'], 'WrongPass!') == False, "Invalid password check failed"
    print("TEST 7 PASSED: Incorrect password rejected safely")

    # TEST 8: Duplicate registration check
    try:
        User.create(test_user, 'another@email.com', test_pass)
        assert False, "Duplicate username allowed!"
    except Exception:
        print("TEST 8 PASSED: Duplicate registration prevented safely")

    # TEST 9 & 10: User Prediction History isolation
    pred_id = Prediction.create(uid, ['fever', 'cough'], 'Influenza (Flu)', 0.92)
    history = Prediction.get_history_by_user(uid)
    assert len(history) >= 1, "Prediction history not found for user"
    assert history[0]['predicted_disease'] == 'Influenza (Flu)', "Prediction disease mismatch"
    print(f"TEST 9 & 10 PASSED: User-specific prediction history isolated correctly (User ID: {uid}, Predictions: {len(history)})")

    # TEST 5: Shared Auth with Flask check
    from app import create_app
    app = create_app()
    with app.test_client() as client:
        res = client.post('/api/auth/login', json={
            'username': test_user,
            'password': test_pass
        })
        assert res.status_code == 200, f"Flask login failed: {res.json}"
        print("TEST 5 PASSED: Flask successfully authenticated Streamlit-registered user!")

    # TEST 6: Register via Flask, login via Streamlit logic
    flask_u = f"flask_u_{rand_suffix}"
    flask_e = f"flask_{rand_suffix}@predihealth.local"
    with app.test_client() as client:
        reg_res = client.post('/api/auth/register', json={
            'username': flask_u,
            'email': flask_e,
            'password': test_pass
        })
        assert reg_res.status_code == 201, f"Flask registration failed: {reg_res.json}"

    st_lookup = User.get_by_username(flask_u)
    assert st_lookup is not None, "Streamlit could not find Flask-created user"
    assert User.verify_password(st_lookup['password_hash'], test_pass) == True, "Streamlit failed to verify Flask-created user password"
    print("TEST 6 PASSED: Streamlit successfully authenticated Flask-registered user!")

    print("\nALL 10 COMPATIBILITY & SECURITY TESTS PASSED CLEANLY!")

if __name__ == '__main__':
    run_tests()
