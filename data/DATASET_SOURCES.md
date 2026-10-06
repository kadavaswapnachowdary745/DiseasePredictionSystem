# PrediHealth — Specialized Disease Dataset Sources

This document describes the legitimate public machine learning datasets used for the **Specialized Disease Prediction** module in PrediHealth.

---

## 1. Breast Cancer Diagnostic Dataset
- **Disease**: Breast Cancer
- **Original Source**: UCI Machine Learning Repository / scikit-learn (`load_breast_cancer`)
- **File**: `data/breast_cancer.csv`
- **Records**: 569 instances
- **Features**: 30 numerical features (cell nucleus characteristics derived from digitized FNA images including radius, texture, perimeter, area, smoothness, compactness, concavity, concave points, symmetry, fractal dimension).
- **Target Column**: `diagnosis` (1 = Benign [357], 0 = Malignant [212]).
- **Missing Values**: 0 missing values.
- **Preprocessing**: StandardScaler normalization.

---

## 2. Heart Disease Dataset
- **Disease**: Heart Disease
- **Original Source**: UCI Machine Learning Repository (Cleveland Heart Disease Database)
- **File**: `data/heart_disease.csv`
- **Records**: 303 instances
- **Features**: 13 clinical parameters (`age`, `sex`, `cp` [chest pain type], `trestbps` [resting blood pressure], `chol` [serum cholesterol], `fbs` [fasting blood sugar], `restecg`, `thalach` [max heart rate], `exang` [exercise induced angina], `oldpeak` [ST depression], `slope`, `ca` [number of major vessels], `thal`).
- **Target Column**: `target` (1 = Heart Disease Present [139], 0 = No Heart Disease [164]).
- **Missing Values**: Median imputation for missing values in `ca` and `thal`.
- **Preprocessing**: Imputation & StandardScaler normalization.

---

## 3. Chronic Kidney Disease Dataset
- **Disease**: Chronic Kidney Disease (CKD)
- **Original Source**: UCI Machine Learning Repository / OpenML Dataset ID 42972
- **File**: `data/kidney_disease.csv`
- **Records**: 400 instances
- **Features**: 25 attributes (11 numerical: `age`, `bp`, `bgr`, `bu`, `sc`, `sod`, `pot`, `hemo`, `pcv`, `wc`, `rc`; 14 categorical/binary: `sg`, `al`, `su`, `rbc`, `pc`, `pcc`, `ba`, `htn`, `dm`, `cad`, `appet`, `pe`, `ane`).
- **Target Column**: `classification` (`ckd` [250], `notckd` [150]).
- **Missing Values**: Median imputation for numerical features, most-frequent mode imputation for categorical attributes.
- **Preprocessing**: Imputation, LabelEncoding for categorical attributes, StandardScaler normalization.

---

## 4. Indian Liver Patient Dataset (ILPD)
- **Disease**: Liver Disease
- **Original Source**: UCI Machine Learning Repository (Indian Liver Patient Dataset)
- **File**: `data/liver_disease.csv`
- **Records**: 583 instances
- **Features**: 10 clinical parameters (`age`, `gender`, `total_bilirubin`, `direct_bilirubin`, `alkaline_phosphotase`, `alamine_aminotransferase`, `aspartate_aminotransferase`, `total_proteins`, `albumin`, `albumin_and_globulin_ratio`).
- **Target Column**: `target` (1 = Liver Disease Present [416], 0 = No Liver Disease [167]).
- **Missing Values**: Median imputation for missing `albumin_and_globulin_ratio` values.
- **Preprocessing**: Gender OneHotEncoding/OrdinalEncoding, Imputation, StandardScaler normalization.

---

## 5. Healthcare Stroke Prediction Dataset
- **Disease**: Stroke
- **Original Source**: Kaggle Healthcare Stroke Prediction Dataset (Fedesoriano)
- **File**: `data/stroke.csv`
- **Records**: 5,110 instances
- **Features**: 10 clinical and demographic attributes (`gender`, `age`, `hypertension`, `heart_disease`, `ever_married`, `work_type`, `Residence_type`, `avg_glucose_level`, `bmi`, `smoking_status`).
- **Target Column**: `stroke` (1 = Stroke Event [249], 0 = No Stroke [4,861]).
- **Missing Values**: Median imputation for missing `bmi` values (201 missing rows).
- **Preprocessing**: Median Imputation, OneHotEncoding for categorical variables, SMOTE / class weighting, StandardScaler normalization.

---

## 6. Survey Lung Cancer Dataset
- **Disease**: Lung Cancer
- **Original Source**: Kaggle Survey Lung Cancer Dataset
- **File**: `data/lung_cancer.csv`
- **Records**: 309 instances
- **Features**: 15 survey risk factors (`GENDER`, `AGE`, `SMOKING`, `YELLOW_FINGERS`, `ANXIETY`, `PEER_PRESSURE`, `CHRONIC DISEASE`, `FATIGUE`, `ALLERGY`, `WHEEZING`, `ALCOHOL CONSUMING`, `COUGHING`, `SHORTNESS OF BREATH`, `SWALLOWING DIFFICULTY`, `CHEST PAIN`).
- **Target Column**: `LUNG_CANCER` (YES [270], NO [39]).
- **Missing Values**: 0 missing values.
- **Preprocessing**: Gender encoding (M/F -> 1/0), Target encoding (YES/NO -> 1/0), StandardScaler normalization.
