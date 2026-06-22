import os
import json
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, classification_report
import joblib

def train_disease_predictor():
    csv_path = 'data/disease_symptoms.csv'
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Dataset not found at {csv_path}. Please run generate_dataset.py first.")
        
    print(f"Loading dataset from {csv_path}...")
    df = pd.read_csv(csv_path)
    
    # Split features (symptoms) and labels (diseases)
    # The last column is 'disease', and all other columns are features (symptoms)
    X = df.drop(columns=['disease'])
    y = df['disease']
    
    # Save the symptom names (features) to models/symptoms.json for future deployment mapping
    symptoms_list = list(X.columns)
    os.makedirs('models', exist_ok=True)
    with open('models/symptoms.json', 'w') as f:
        json.dump(symptoms_list, f, indent=4)
    print("Saved symptom feature list to models/symptoms.json")
    
    # Split into train and test sets (80% train, 20% test)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42, stratify=y
    )
    print(f"Train size: {X_train.shape[0]}, Test size: {X_test.shape[0]}")
    
    # Initialize Random Forest Classifier
    # n_estimators=100 is standard and works exceptionally well for binary feature sets
    print("Training Random Forest Classifier...")
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)
    
    # Make predictions on test set
    y_pred = model.predict(X_test)
    
    # Calculate evaluation metrics
    accuracy = accuracy_score(y_test, y_pred)
    precision = precision_score(y_test, y_pred, average='weighted')
    recall = recall_score(y_test, y_pred, average='weighted')
    f1 = f1_score(y_test, y_pred, average='weighted')
    
    # Print results
    print("\n" + "="*40)
    print("MODEL EVALUATION RESULTS")
    print("="*40)
    print(f"Accuracy:  {accuracy:.4f}")
    print(f"Precision: {precision:.4f} (Weighted)")
    print(f"Recall:    {recall:.4f} (Weighted)")
    print(f"F1 Score:  {f1:.4f} (Weighted)")
    print("="*40)
    
    print("\nDetailed Classification Report:")
    print(classification_report(y_test, y_pred))
    
    # Save the trained model
    model_path = 'models/disease_model.pkl'
    joblib.dump(model, model_path)
    print(f"Trained model saved to {model_path}")
    
    # Verification test with dummy symptom profile (e.g., Flu-like symptoms)
    print("\nPerforming quick verification test...")
    # Creating a sample where 'fever', 'cough', 'body_ache', 'fatigue', and 'chills' are present (1), others are 0
    sample_input = pd.DataFrame(0, index=[0], columns=symptoms_list)
    sample_symptoms = ['fever', 'cough', 'body_ache', 'fatigue', 'chills']
    for sym in sample_symptoms:
        if sym in sample_input.columns:
            sample_input.loc[0, sym] = 1
            
    predicted_disease = model.predict(sample_input)[0]
    probabilities = model.predict_proba(sample_input)[0]
    class_index = np.where(model.classes_ == predicted_disease)[0][0]
    confidence = probabilities[class_index]
    
    print(f"Input Symptoms: {sample_symptoms}")
    print(f"Predicted Disease: {predicted_disease} (Confidence: {confidence:.2%})")

if __name__ == '__main__':
    train_disease_predictor()
