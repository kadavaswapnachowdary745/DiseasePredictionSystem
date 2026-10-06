import os
import json
import joblib
import pandas as pd
import numpy as np

from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, OrdinalEncoder, LabelEncoder
from sklearn.impute import SimpleImputer
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score

# Classifiers
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.tree import DecisionTreeClassifier
from sklearn.neighbors import KNeighborsClassifier
from xgboost import XGBClassifier

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / 'data'
MODEL_DIR = BASE_DIR / 'models' / 'specialized'
MODEL_DIR.mkdir(parents=True, exist_ok=True)

# Definition of 6 Specialized Disease Configurations
DISEASE_CONFIGS = {
    'heart_disease': {
        'display_name': 'Heart Disease',
        'file': DATA_DIR / 'heart_disease.csv',
        'target_col': 'target',
        'target_names': {0: 'Lower Risk / No Disease', 1: 'Higher Risk / Disease Present'},
        'numeric_features': ['age', 'trestbps', 'chol', 'thalach', 'oldpeak'],
        'categorical_features': ['sex', 'cp', 'fbs', 'restecg', 'exang', 'slope', 'ca', 'thal']
    },
    'kidney_disease': {
        'display_name': 'Chronic Kidney Disease',
        'file': DATA_DIR / 'kidney_disease.csv',
        'target_col': 'classification',
        'target_names': {0: 'Not CKD / Lower Risk', 1: 'CKD Present / Higher Risk'},
        'numeric_features': ['age', 'bp', 'bgr', 'bu', 'sc', 'sod', 'pot', 'hemo', 'pcv', 'wc', 'rc'],
        'categorical_features': ['sg', 'al', 'su', 'rbc', 'pc', 'pcc', 'ba', 'htn', 'dm', 'cad', 'appet', 'pe', 'ane']
    },
    'breast_cancer': {
        'display_name': 'Breast Cancer',
        'file': DATA_DIR / 'breast_cancer.csv',
        'target_col': 'diagnosis',
        'target_names': {0: 'Malignant (Higher Risk)', 1: 'Benign (Lower Risk)'},
        'numeric_features': [
            'mean radius', 'mean texture', 'mean perimeter', 'mean area', 'mean smoothness',
            'mean compactness', 'mean concavity', 'mean concave points', 'mean symmetry', 'mean fractal dimension',
            'radius error', 'texture error', 'perimeter error', 'area error', 'smoothness error',
            'compactness error', 'concavity error', 'concave points error', 'symmetry error', 'fractal dimension error',
            'worst radius', 'worst texture', 'worst perimeter', 'worst area', 'worst smoothness',
            'worst compactness', 'worst concavity', 'worst concave points', 'worst symmetry', 'worst fractal dimension'
        ],
        'categorical_features': []
    },
    'liver_disease': {
        'display_name': 'Liver Disease',
        'file': DATA_DIR / 'liver_disease.csv',
        'target_col': 'target',
        'target_names': {0: 'Lower Risk / No Disease', 1: 'Higher Risk / Disease Present'},
        'numeric_features': [
            'age', 'total_bilirubin', 'direct_bilirubin', 'alkaline_phosphotase',
            'alamine_aminotransferase', 'aspartate_aminotransferase', 'total_proteins',
            'albumin', 'albumin_and_globulin_ratio'
        ],
        'categorical_features': ['gender']
    },
    'stroke': {
        'display_name': 'Stroke',
        'file': DATA_DIR / 'stroke.csv',
        'target_col': 'stroke',
        'target_names': {0: 'Lower Risk / No Stroke', 1: 'Higher Risk / Stroke Event'},
        'numeric_features': ['age', 'hypertension', 'heart_disease', 'avg_glucose_level', 'bmi'],
        'categorical_features': ['gender', 'ever_married', 'work_type', 'Residence_type', 'smoking_status']
    },
    'lung_cancer': {
        'display_name': 'Lung Cancer',
        'file': DATA_DIR / 'lung_cancer.csv',
        'target_col': 'LUNG_CANCER',
        'target_names': {0: 'Lower Risk / Negative', 1: 'Higher Risk / Positive'},
        'numeric_features': ['AGE'],
        'categorical_features': [
            'GENDER', 'SMOKING', 'YELLOW_FINGERS', 'ANXIETY', 'PEER_PRESSURE',
            'CHRONIC DISEASE', 'FATIGUE', 'ALLERGY', 'WHEEZING', 'ALCOHOL CONSUMING',
            'COUGHING', 'SHORTNESS OF BREATH', 'SWALLOWING DIFFICULTY', 'CHEST PAIN'
        ]
    }
}

def load_and_clean_data(disease_key, config):
    df = pd.read_csv(config['file'])
    
    # Specific cleaning per dataset
    if disease_key == 'kidney_disease':
        # Drop ID if present
        if 'id' in df.columns:
            df = df.drop(columns=['id'])
        # Map target 'ckd' -> 1, 'notckd' -> 0
        def map_ckd(val):
            s = str(val).lower().strip().replace("'", "").replace('"', '').replace('\t', '')
            if 'notckd' in s:
                return 0
            elif 'ckd' in s:
                return 1
            return 0
        df['classification'] = df['classification'].apply(map_ckd)
        # Convert numeric string columns like pcv, wc, rc to numeric
        for num_col in config['numeric_features']:
            if num_col in df.columns:
                df[num_col] = pd.to_numeric(df[num_col].astype(str).str.replace('\t', '').str.replace('?', ''), errors='coerce')
    elif disease_key == 'lung_cancer':
        # Target YES -> 1, NO -> 0
        df['LUNG_CANCER'] = df['LUNG_CANCER'].astype(str).str.strip().map({'YES': 1, 'NO': 0, '2': 1, '1': 0})

    # Drop target column for X
    target_col = config['target_col']
    y = df[target_col]
    X = df.drop(columns=[target_col])
    
    # Ensure target is 0-indexed integer (0 and 1)
    if y.dtype == 'object' or not np.issubdtype(y.dtype, np.integer):
        le = LabelEncoder()
        y = le.fit_transform(y.astype(str))
    else:
        y = y.astype(int)

    # Ensure features exist
    all_feats = config['numeric_features'] + config['categorical_features']
    X = X[all_feats]
    
    return X, y

def build_preprocessor(numeric_features, categorical_features):
    num_transformer = Pipeline(steps=[
        ('imputer', SimpleImputer(strategy='median')),
        ('scaler', StandardScaler())
    ])
    
    if categorical_features:
        cat_transformer = Pipeline(steps=[
            ('imputer', SimpleImputer(strategy='most_frequent')),
            ('encoder', OrdinalEncoder(handle_unknown='use_encoded_value', unknown_value=-1))
        ])
        preprocessor = ColumnTransformer(transformers=[
            ('num', num_transformer, numeric_features),
            ('cat', cat_transformer, categorical_features)
        ])
    else:
        preprocessor = ColumnTransformer(transformers=[
            ('num', num_transformer, numeric_features)
        ])
        
    return preprocessor

def get_classifiers():
    return {
        'Random Forest': RandomForestClassifier(n_estimators=100, random_state=42),
        'XGBoost': XGBClassifier(n_estimators=100, random_state=42, eval_metric='logloss'),
        'Decision Tree': DecisionTreeClassifier(random_state=42),
        'K-Nearest Neighbors': KNeighborsClassifier(n_neighbors=5),
        'Gradient Boosting': GradientBoostingClassifier(n_estimators=100, random_state=42)
    }

def train_and_evaluate_all():
    metadata = {}
    print("=" * 70)
    print("PREDIHEALTH — SPECIALIZED MULTI-DISEASE MODEL TRAINING PIPELINE")
    print("=" * 70)
    
    for d_key, cfg in DISEASE_CONFIGS.items():
        print(f"\n---> Processing Specialized Disease: {cfg['display_name']} ({d_key})")
        X, y = load_and_clean_data(d_key, cfg)
        
        # Train / Test Split (80 / 20 stratified)
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.20, random_state=42, stratify=y
        )
        
        preprocessor = build_preprocessor(cfg['numeric_features'], cfg['categorical_features'])
        
        classifiers = get_classifiers()
        eval_results = []
        best_model_name = None
        best_f1 = -1.0
        best_pipeline = None
        
        for name, clf in classifiers.items():
            pipeline = Pipeline(steps=[
                ('preprocessor', preprocessor),
                ('classifier', clf)
            ])
            
            # Fit strictly on train set (no data leakage)
            pipeline.fit(X_train, y_train)
            
            # Evaluate on test set
            y_pred = pipeline.predict(X_test)
            
            acc = float(accuracy_score(y_test, y_pred))
            prec = float(precision_score(y_test, y_pred, average='weighted', zero_division=0))
            rec = float(recall_score(y_test, y_pred, average='weighted', zero_division=0))
            f1 = float(f1_score(y_test, y_pred, average='weighted', zero_division=0))
            
            res_entry = {
                'algorithm': name,
                'accuracy': round(acc, 4),
                'precision': round(prec, 4),
                'recall': round(rec, 4),
                'f1_score': round(f1, 4)
            }
            eval_results.append(res_entry)
            print(f"   [{name:<20}] Acc: {acc*100:.2f}% | Prec: {prec*100:.2f}% | Rec: {rec*100:.2f}% | F1: {f1*100:.2f}%")
            
            # Select best model based primarily on F1 Score, then Accuracy
            if f1 > best_f1:
                best_f1 = f1
                best_model_name = name
                best_pipeline = pipeline
                
        # Save best model pipeline
        model_filename = f"{d_key}_model.pkl"
        model_path = MODEL_DIR / model_filename
        joblib.dump(best_pipeline, model_path)
        print(f"   ★ BEST MODEL SELECTED: {best_model_name} (F1 Score: {best_f1*100:.2f}%) saved to '{model_path}'")
        
        # Calculate feature importances if available on best model classifier
        clf_obj = best_pipeline.named_steps['classifier']
        feat_importances = {}
        all_feature_names = cfg['numeric_features'] + cfg['categorical_features']
        
        if hasattr(clf_obj, 'feature_importances_'):
            imps = clf_obj.feature_importances_
            for feat, imp in zip(all_feature_names, imps):
                feat_importances[feat] = round(float(imp), 4)
                
        metadata[d_key] = {
            'display_name': cfg['display_name'],
            'model_file': model_filename,
            'dataset_records': len(X),
            'feature_count': len(all_feature_names),
            'feature_names': all_feature_names,
            'numeric_features': cfg['numeric_features'],
            'categorical_features': cfg['categorical_features'],
            'target_names': cfg['target_names'],
            'selected_algorithm': best_model_name,
            'best_f1_score': round(best_f1, 4),
            'evaluation_comparison': eval_results,
            'feature_importances': feat_importances
        }
        
    # Save specialized metadata JSON
    meta_path = MODEL_DIR / 'specialized_metadata.json'
    with open(meta_path, 'w') as f:
        json.dump(metadata, f, indent=2)
        
    print("\n" + "=" * 70)
    print(f"SUMMARY: All 6 specialized models successfully trained and metadata saved to '{meta_path}'!")
    print("=" * 70)

if __name__ == '__main__':
    train_and_evaluate_all()
