import os
import json
import numpy as np
import pandas as pd

# Set random seed for reproducibility
np.random.seed(42)

# Define the symptoms (42 in total)
SYMPTOMS = [
    'fever', 'cough', 'runny_nose', 'sore_throat', 'body_ache', 'fatigue', 'headache',
    'shortness_of_breath', 'loss_of_taste', 'loss_of_smell', 'high_blood_pressure',
    'dizziness', 'increased_thirst', 'frequent_urination', 'unexplained_weight_loss',
    'wheezing', 'chest_tightness', 'nausea', 'vomiting', 'diarrhea', 'abdominal_pain',
    'chills', 'skin_rash', 'itching', 'joint_pain', 'muscle_weakness', 'loss_of_appetite',
    'yellowing_of_skin', 'yellowing_of_eyes', 'dark_urine', 'sweating', 'constipation',
    'burning_urination', 'pelvic_pain', 'sneezing', 'watery_eyes', 'heartburn',
    'difficulty_swallowing', 'neck_pain', 'stiff_neck', 'confusion', 'sensitivity_to_light'
]

# Define 20 diseases and their symptom probability profiles
# High probability (e.g., 0.7 - 0.95) for primary symptoms, low probability (0.01 - 0.05) for noise
DISEASE_PROFILES = {
    'Influenza (Flu)': {
        'fever': 0.90, 'cough': 0.85, 'runny_nose': 0.70, 'sore_throat': 0.75,
        'body_ache': 0.90, 'fatigue': 0.85, 'headache': 0.75, 'chills': 0.80, 'sweating': 0.60
    },
    'Common Cold': {
        'runny_nose': 0.90, 'sneezing': 0.95, 'sore_throat': 0.85, 'cough': 0.60,
        'watery_eyes': 0.75, 'fatigue': 0.40, 'headache': 0.30
    },
    'Covid-19': {
        'fever': 0.85, 'cough': 0.80, 'sore_throat': 0.65, 'fatigue': 0.80,
        'body_ache': 0.70, 'headache': 0.65, 'shortness_of_breath': 0.70,
        'loss_of_taste': 0.75, 'loss_of_smell': 0.75
    },
    'Diabetes': {
        'increased_thirst': 0.90, 'frequent_urination': 0.90,
        'unexplained_weight_loss': 0.75, 'fatigue': 0.70, 'muscle_weakness': 0.50
    },
    'Hypertension': {
        'high_blood_pressure': 0.95, 'headache': 0.50, 'dizziness': 0.60, 'fatigue': 0.40
    },
    'Asthma': {
        'shortness_of_breath': 0.90, 'wheezing': 0.95, 'chest_tightness': 0.85, 'cough': 0.60
    },
    'Migraine': {
        'headache': 0.95, 'nausea': 0.75, 'sensitivity_to_light': 0.90,
        'vomiting': 0.50, 'dizziness': 0.40, 'neck_pain': 0.40
    },
    'Malaria': {
        'fever': 0.95, 'chills': 0.90, 'sweating': 0.80, 'headache': 0.75,
        'body_ache': 0.70, 'nausea': 0.60, 'vomiting': 0.50, 'diarrhea': 0.30
    },
    'Dengue': {
        'fever': 0.95, 'headache': 0.85, 'body_ache': 0.90, 'joint_pain': 0.90,
        'skin_rash': 0.75, 'fatigue': 0.80, 'loss_of_appetite': 0.70, 'nausea': 0.60
    },
    'Typhoid': {
        'fever': 0.95, 'headache': 0.75, 'abdominal_pain': 0.80, 'diarrhea': 0.50,
        'constipation': 0.40, 'fatigue': 0.80, 'loss_of_appetite': 0.75
    },
    'Chickenpox': {
        'fever': 0.80, 'fatigue': 0.75, 'loss_of_appetite': 0.65, 'headache': 0.60,
        'skin_rash': 0.95, 'itching': 0.95
    },
    'Tuberculosis': {
        'cough': 0.95, 'fatigue': 0.80, 'unexplained_weight_loss': 0.85,
        'fever': 0.70, 'sweating': 0.75, 'loss_of_appetite': 0.70, 'shortness_of_breath': 0.60
    },
    'Pneumonia': {
        'fever': 0.90, 'chills': 0.80, 'cough': 0.90, 'shortness_of_breath': 0.85,
        'chest_tightness': 0.75, 'fatigue': 0.75, 'sweating': 0.60
    },
    'Gastroenteritis': {
        'nausea': 0.85, 'vomiting': 0.85, 'diarrhea': 0.90, 'abdominal_pain': 0.85,
        'fever': 0.40, 'body_ache': 0.30, 'loss_of_appetite': 0.70
    },
    'Urinary Tract Infection (UTI)': {
        'burning_urination': 0.95, 'frequent_urination': 0.90, 'pelvic_pain': 0.75,
        'fever': 0.40, 'dark_urine': 0.60
    },
    'Allergy': {
        'sneezing': 0.85, 'runny_nose': 0.80, 'watery_eyes': 0.85, 'itching': 0.75, 'skin_rash': 0.50
    },
    'GERD (Acid Reflux)': {
        'heartburn': 0.95, 'difficulty_swallowing': 0.60, 'nausea': 0.50,
        'chest_tightness': 0.40, 'abdominal_pain': 0.50
    },
    'Arthritis': {
        'joint_pain': 0.95, 'body_ache': 0.60, 'muscle_weakness': 0.50, 'fatigue': 0.50
    },
    'Hepatitis': {
        'yellowing_of_skin': 0.90, 'yellowing_of_eyes': 0.90, 'dark_urine': 0.85,
        'abdominal_pain': 0.70, 'nausea': 0.65, 'vomiting': 0.55, 'loss_of_appetite': 0.75,
        'fatigue': 0.75, 'fever': 0.50
    },
    'Jaundice': {
        'yellowing_of_skin': 0.95, 'yellowing_of_eyes': 0.95, 'dark_urine': 0.85,
        'fatigue': 0.70, 'abdominal_pain': 0.50, 'fever': 0.40
    }
}

def generate_dataset(samples_per_disease=80):
    print("Generating synthetic disease-symptoms dataset...")
    data = []
    
    # Check that we have exactly 20 diseases
    diseases = list(DISEASE_PROFILES.keys())
    print(f"Number of diseases: {len(diseases)}")
    print(f"Number of symptoms: {len(SYMPTOMS)}")
    
    for disease in diseases:
        profile = DISEASE_PROFILES[disease]
        for _ in range(samples_per_disease):
            row = {}
            for symptom in SYMPTOMS:
                # Get the probability of having this symptom for this disease
                prob = profile.get(symptom, 0.02) # baseline 2% chance of noise symptoms
                
                # Determine presence (1) or absence (0) of symptom based on probability
                row[symptom] = np.random.choice([1, 0], p=[prob, 1 - prob])
            row['disease'] = disease
            data.append(row)
            
    df = pd.DataFrame(data)
    
    # Shuffle dataset
    df = df.sample(frac=1).reset_index(drop=True)
    
    # Ensure data directory exists
    os.makedirs('data', exist_ok=True)
    
    # Save CSV
    csv_path = 'data/disease_symptoms.csv'
    df.to_csv(csv_path, index=False)
    print(f"Dataset successfully saved to {csv_path} with {len(df)} samples.")
    
if __name__ == '__main__':
    generate_dataset()
