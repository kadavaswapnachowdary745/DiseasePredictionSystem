import json
import joblib
import pandas as pd
import numpy as np
from pathlib import Path
from db import init_db
from models.prediction import Prediction

BASE_DIR = Path(__file__).resolve().parent
SPECIALIZED_DIR = BASE_DIR / 'models' / 'specialized'
SPECIALIZED_META_PATH = SPECIALIZED_DIR / 'specialized_metadata.json'

def test_specialized_system():
    print("=== Testing Specialized Multi-Disease Prediction System ===")
    
    # 1. Initialize Database
    init_db()
    print("✓ SQLite database initialized successfully.")

    # 2. Check metadata
    assert SPECIALIZED_META_PATH.exists(), "Metadata file missing!"
    with open(SPECIALIZED_META_PATH, 'r') as f:
        meta = json.load(f)
    
    diseases = ["heart_disease", "kidney_disease", "breast_cancer", "liver_disease", "stroke", "lung_cancer"]
    for d in diseases:
        assert d in meta, f"Disease {d} missing in metadata!"
        print(f"✓ Metadata verified for: {meta[d]['display_name']} ({meta[d]['selected_algorithm']} - F1: {meta[d]['best_f1_score']*100:.1f}%)")

    # 3. Test each model inference
    sample_inputs = {
        "heart_disease": {
            "age": 55, "trestbps": 130, "chol": 240, "thalach": 150, "oldpeak": 1.0,
            "sex": 1, "cp": 0, "fbs": 0, "restecg": 0, "exang": 0, "slope": 1, "ca": 0, "thal": 2
        },
        "kidney_disease": {
            "age": 48, "bp": 80, "bgr": 121, "bu": 36, "sc": 1.2, "sod": 138, "pot": 4.4, "hemo": 12.5,
            "pcv": 39, "wc": 7800, "rc": 4.7, "sg": 1.020, "al": 0, "su": 0, "rbc": "normal", "pc": "normal",
            "pcc": "notpresent", "ba": "notpresent", "htn": "no", "dm": "no", "cad": "no", "appet": "good",
            "pe": "no", "ane": "no"
        },
        "breast_cancer": {
            "mean radius": 13.5, "mean texture": 17.8, "mean perimeter": 87.0, "mean area": 565.0,
            "mean smoothness": 0.096, "mean compactness": 0.104, "mean concavity": 0.088, "mean concave points": 0.048,
            "mean symmetry": 0.181, "mean fractal dimension": 0.062, "radius error": 0.40, "texture error": 1.21,
            "perimeter error": 2.86, "area error": 40.3, "smoothness error": 0.007, "compactness error": 0.025,
            "concavity error": 0.031, "concave points error": 0.011, "symmetry error": 0.020,
            "fractal dimension error": 0.0037, "worst radius": 16.2, "worst texture": 25.6,
            "worst perimeter": 107.0, "worst area": 880.0, "worst smoothness": 0.132, "worst compactness": 0.254,
            "worst concavity": 0.272, "worst concave points": 0.114, "worst symmetry": 0.290,
            "worst fractal dimension": 0.083
        },
        "liver_disease": {
            "age": 45, "total_bilirubin": 1.0, "direct_bilirubin": 0.3, "alkaline_phosphotase": 198,
            "alamine_aminotransferase": 35, "aspartate_aminotransferase": 42, "total_proteins": 6.5,
            "albumin": 3.2, "albumin_and_globulin_ratio": 0.95, "gender": "Male"
        },
        "stroke": {
            "age": 62, "hypertension": 0, "heart_disease": 0, "avg_glucose_level": 106.0, "bmi": 28.8,
            "gender": "Male", "ever_married": "Yes", "work_type": "Private", "Residence_type": "Urban",
            "smoking_status": "never smoked"
        },
        "lung_cancer": {
            "AGE": 60, "GENDER": "M", "SMOKING": 2, "YELLOW_FINGERS": 1, "ANXIETY": 1, "PEER_PRESSURE": 1,
            "CHRONIC DISEASE": 1, "FATIGUE": 2, "ALLERGY": 1, "WHEEZING": 1, "ALCOHOL CONSUMING": 1,
            "COUGHING": 2, "SHORTNESS OF BREATH": 2, "SWALLOWING DIFFICULTY": 1, "CHEST PAIN": 1
        }
    }

    for d_key, d_info in meta.items():
        m_path = SPECIALIZED_DIR / d_info['model_file']
        assert m_path.exists(), f"Model file {m_path} missing!"
        model = joblib.load(m_path)
        
        sample = sample_inputs[d_key]
        input_df = pd.DataFrame([sample])[d_info['feature_names']]
        pred = model.predict(input_df)[0]
        prob = model.predict_proba(input_df)[0] if hasattr(model, 'predict_proba') else [1.0]
        
        pred_str = str(pred)
        label_text = d_info['target_names'].get(pred_str, f"Class {pred_str}")
        print(f"✓ Inference successful for {d_info['display_name']}: Output='{label_text}', Max Probability={np.max(prob)*100:.1f}%")

    # 4. Test database creation of Specialized Prediction
    from models.user import User
    test_user = User.get_by_username("test_user_spec")
    if not test_user:
        test_uid = User.create("test_user_spec", "test_user_spec@example.com", "password123")
    else:
        test_uid = test_user['id']

    pred_id = Prediction.create(
        user_id=test_uid,
        symptoms=sample_inputs['heart_disease'],
        predicted_disease="Heart Disease: Lower Risk / No Disease",
        confidence=0.918,
        prediction_type='Specialized'
    )
    assert pred_id is not None, "Failed to log specialized prediction to database!"
    print(f"✓ Database logging verified for specialized prediction (Record ID: #{pred_id}).")

    # 5. Verify prediction history retrieval
    history = Prediction.get_history_by_user(test_uid)
    assert len(history) > 0, "No prediction history found!"
    print(f"✓ Prediction history query returned {len(history)} entries.")

    print("\n🎉 ALL SPECIALIZED SYSTEM TESTS PASSED SUCCESSFULLY!")

if __name__ == '__main__':
    test_specialized_system()
