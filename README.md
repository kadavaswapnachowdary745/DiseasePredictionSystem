# PrediHealth — Streamlit-Based Multi-Disease Prediction System for Early Disease Detection Using Machine Learning

PrediHealth is a complete, multi-disease prediction platform that combines **General Symptom-Based Prediction** across 20 diseases with **Specialized Disease Diagnosis** across 6 clinical conditions (**Heart Disease, Chronic Kidney Disease, Breast Cancer, Liver Disease, Stroke, and Lung Cancer**).

The system features a dual architecture supporting both a **Flask REST API Web Application** and a **Streamlit Multi-Page Machine Learning Interface**, integrated with a persistent SQLite database, Explainable AI (XAI), session authentication, and ReportLab PDF clinical report generation.

---

## 🏗️ System Architecture

```
                    PREDIHEALTH PLATFORM
                             |
             ┌───────────────┴───────────────┐
             |                               |
      GENERAL PREDICTION              SPECIALIZED DIAGNOSIS
             |                               |
      Existing Model (Random Forest)    Six Disease Models
             |                               |
      20 Diseases                    ┌───────┼───────┐
                                     |       |       |
                                   Heart   Kidney  Breast
                                     |       |       |
                                   Liver   Stroke  Lung Cancer
```

### 1. General Symptom-Based Prediction (20 Diseases)
- **Model**: Trained `RandomForestClassifier` (100 estimators, `models/disease_model.pkl`)
- **Features**: 42 clinical symptoms (`models/symptoms.json`)
- **Dataset**: `data/disease_symptoms.csv` (1,600 samples)
- **Capabilities**: Multi-symptom pattern matching, top-3 class probabilities, Explainable AI (XAI) feature contribution analysis, PDF report download.

### 2. Specialized Disease Diagnosis (6 Diseases)
Each specialized disease is trained on dedicated public datasets, evaluating **5 algorithms** (Random Forest, XGBoost, Decision Tree, K-Nearest Neighbors, Gradient Boosting) to select the optimal model pipeline (`models/specialized/`):

1. **Heart Disease**: Cleveland Dataset (13 clinical parameters, **Random Forest** selected, F1: 91.82%)
2. **Chronic Kidney Disease (CKD)**: UCI CKD Dataset (24 parameters, **Random Forest** selected, F1: 100.00%)
3. **Breast Cancer**: Wisconsin Diagnostic FNA Dataset (30 parameters, **Random Forest** selected, F1: 95.60%)
4. **Liver Disease**: Indian Liver Patient Dataset (10 parameters, **Random Forest** selected, F1: 69.64%)
5. **Stroke**: Healthcare Stroke Dataset (10 parameters, **XGBoost** selected, F1: 93.12%)
6. **Lung Cancer**: Survey Lung Cancer Dataset (15 survey parameters, **Decision Tree** selected, F1: 93.85%)

---

## 📁 Folder Structure

```
DiseasePredictionSystem/
├── data/
│   ├── disease_symptoms.csv       # General 20-disease symptoms dataset (1,600 samples, 42 symptoms)
│   ├── heart_disease.csv          # Heart Disease dataset (303 samples, 13 features)
│   ├── kidney_disease.csv         # Chronic Kidney Disease dataset (400 samples, 24 features)
│   ├── breast_cancer.csv          # Breast Cancer dataset (569 samples, 30 features)
│   ├── liver_disease.csv          # Indian Liver Patient dataset (583 samples, 10 features)
│   ├── stroke.csv                 # Healthcare Stroke dataset (5,110 samples, 10 features)
│   ├── lung_cancer.csv            # Survey Lung Cancer dataset (309 samples, 15 features)
│   └── DATASET_SOURCES.md         # Documented origins, preprocessing, and features of datasets
├── models/
│   ├── disease_model.pkl          # Serialized 20-disease Random Forest model
│   ├── symptoms.json              # 42 general symptom features definition
│   ├── specialized/               # Serialized specialized models & benchmark metadata
│   │   ├── heart_disease_model.pkl
│   │   ├── kidney_disease_model.pkl
│   │   ├── breast_cancer_model.pkl
│   │   ├── liver_disease_model.pkl
│   │   ├── stroke_model.pkl
│   │   ├── lung_cancer_model.pkl
│   │   └── specialized_metadata.json
│   ├── user.py                    # User authentication database model
│   └── prediction.py              # Prediction history database model
├── controllers/
│   ├── auth.py                    # Flask authentication blueprint
│   ├── chat.py                    # Health Assistant chatbot engine
│   └── prediction.py              # Flask ML prediction & PDF generator blueprint
├── static/                        # CSS/JS web assets for Flask
├── templates/                     # Jinja2 HTML templates for Flask
├── app.py                         # Main Flask server entrypoint (Port 5000)
├── streamlit_app.py               # Streamlit Multi-Page Web Application
├── train_model.py                 # General 20-disease Random Forest training script
├── train_specialized_models.py    # Specialized models training & benchmarking pipeline
├── config.py                      # Database path & configuration
├── db.py                          # SQLite database connection & migrations
├── schema.sql                     # Database DDL schema definition
├── requirements.txt               # Required Python packages
└── README.md                      # Project documentation (this file)
```

---

## 📊 Benchmark Results — Specialized Disease Models

| Disease | Best Selected Algorithm | Accuracy | Precision | Recall | F1 Score |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **Heart Disease** | Random Forest | 91.80% | 92.27% | 91.80% | **91.82%** |
| **Chronic Kidney Disease** | Random Forest | 100.00% | 100.00% | 100.00% | **100.00%** |
| **Breast Cancer** | Random Forest | 95.61% | 95.61% | 95.61% | **95.60%** |
| **Liver Disease** | Random Forest | 72.65% | 69.89% | 72.65% | **69.64%** |
| **Stroke** | XGBoost | 94.91% | 92.53% | 94.91% | **93.12%** |
| **Lung Cancer** | Decision Tree | 93.55% | 94.45% | 93.55% | **93.85%** |

---

## 🚀 How to Run the Project

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Retrain Machine Learning Models (Optional)
- Train General 20-disease model:
  ```bash
  python3 train_model.py
  ```
- Train and benchmark 6 Specialized Disease models:
  ```bash
  python3 train_specialized_models.py
  ```

### 3. Launch Streamlit Application
```bash
streamlit run streamlit_app.py
```
Access Streamlit UI at: `http://localhost:8501`

### 4. Launch Flask Web Application
```bash
python3 app.py
```
Access Flask Web App at: `http://localhost:5000`

---

## ⚠️ Academic Medical Disclaimer
This system is intended for educational and research demonstration purposes only. Machine learning predictions are not a medical diagnosis and should not replace professional medical evaluation. Always consult a qualified healthcare professional for medical concerns.
