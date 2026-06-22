import sqlite3
import os
import json
from flask import g, current_app
from config import Config

# Complete clinical profile data for all 20 diseases predicted by our machine learning model
DISEASE_SEEDS = [
    {
        'name': 'Influenza (Flu)',
        'description': 'A highly contagious viral infection of the respiratory tract causing fever, severe aching, and fatigue.',
        'causes': ['Influenza viruses (Type A, B, or C)', 'Inhalation of airborne respiratory droplets', 'Contact with contaminated objects'],
        'symptoms': ['fever', 'cough', 'runny_nose', 'sore_throat', 'body_ache', 'fatigue', 'headache', 'chills', 'sweating'],
        'precautions': ['Get annual flu vaccine', 'Wash hands frequently with soap', 'Cover mouth when coughing or sneezing', 'Isolate to protect others'],
        'recommended_doctor': 'General Physician'
    },
    {
        'name': 'Common Cold',
        'description': 'A mild viral infection of the nose, sinuses, and throat causing runny nose, sore throat, and sneezing.',
        'causes': ['Rhinoviruses or Coronaviruses', 'Airborne transmission of respiratory droplets', 'Direct hand-to-hand contact with infected individuals'],
        'symptoms': ['runny_nose', 'sneezing', 'sore_throat', 'cough', 'watery_eyes', 'fatigue', 'headache'],
        'precautions': ['Wash hands frequently', 'Avoid touching eyes, nose, and mouth', 'Clean surfaces regularly', 'Stay warm and hydrated'],
        'recommended_doctor': 'General Physician'
    },
    {
        'name': 'Covid-19',
        'description': 'An infectious respiratory disease caused by the SARS-CoV-2 virus, ranging from mild symptoms to severe respiratory distress.',
        'causes': ['SARS-CoV-2 virus', 'Respiratory droplets from coughs/sneezes', 'Close physical proximity with infected patients'],
        'symptoms': ['fever', 'cough', 'sore_throat', 'fatigue', 'body_ache', 'headache', 'shortness_of_breath', 'loss_of_taste', 'loss_of_smell'],
        'precautions': ['Wear face masks in public', 'Get vaccinated and booster shots', 'Maintain physical distancing (6 feet)', 'Monitor oxygen saturation levels'],
        'recommended_doctor': 'Pulmonologist / Infectious Disease Specialist'
    },
    {
        'name': 'Diabetes',
        'description': 'A chronic metabolic disorder characterized by high blood glucose levels resulting from defects in insulin secretion or action.',
        'causes': ['Genetic predisposition', 'Lack of physical exercise and sedentary lifestyle', 'Autoimmune destruction of pancreatic beta cells'],
        'symptoms': ['increased_thirst', 'frequent_urination', 'unexplained_weight_loss', 'fatigue', 'muscle_weakness'],
        'precautions': ['Adopt a low-sugar, fiber-rich diet', 'Exercise regularly (30 minutes daily)', 'Monitor blood glucose levels', 'Adhere to prescribed medication or insulin therapy'],
        'recommended_doctor': 'Endocrinologist'
    },
    {
        'name': 'Hypertension',
        'description': 'A long-term medical condition where the blood pressure in the arteries is persistently elevated, increasing cardiovascular risks.',
        'causes': ['High dietary salt intake', 'Lack of exercise and obesity', 'Chronic stress and genetic factors'],
        'symptoms': ['high_blood_pressure', 'headache', 'dizziness', 'fatigue'],
        'precautions': ['Reduce dietary sodium intake', 'Manage daily stress levels', 'Maintain a healthy weight', 'Take prescribed antihypertensive medications daily'],
        'recommended_doctor': 'Cardiologist'
    },
    {
        'name': 'Asthma',
        'description': 'A chronic condition characterized by inflammation and narrowing of the airways, causing breathing difficulties.',
        'causes': ['Allergen exposure (dust, pollen, pet dander)', 'Air pollution and tobacco smoke', 'Physical exertion or cold air'],
        'symptoms': ['shortness_of_breath', 'wheezing', 'chest_tightness', 'cough'],
        'precautions': ['Identify and avoid asthma triggers', 'Always carry a rescue inhaler', 'Discuss a long-term controller plan with a doctor', 'Monitor breathing with a peak flow meter'],
        'recommended_doctor': 'Pulmonologist / Allergist'
    },
    {
        'name': 'Migraine',
        'description': 'A neurological condition characterized by intense, debilitating headaches, often accompanied by sensory disturbances.',
        'causes': ['Hormonal fluctuations', 'Environmental triggers (bright lights, strong smells)', 'Stress or sleep deprivation'],
        'symptoms': ['headache', 'nausea', 'sensitivity_to_light', 'vomiting', 'dizziness', 'neck_pain'],
        'precautions': ['Rest in a dark, quiet room during attacks', 'Maintain a consistent sleep schedule', 'Stay hydrated and eat at regular times', 'Keep a headache diary to identify triggers'],
        'recommended_doctor': 'Neurologist'
    },
    {
        'name': 'Malaria',
        'description': 'A life-threatening blood disease transmitted by the bite of the female Anopheles mosquito, causing cyclic fever and chills.',
        'causes': ['Plasmodium parasites', 'Bite of an infected female Anopheles mosquito', 'Rarely via blood transfusions'],
        'symptoms': ['fever', 'chills', 'sweating', 'headache', 'body_ache', 'nausea', 'vomiting', 'diarrhea'],
        'precautions': ['Use mosquito nets treated with insecticide', 'Apply mosquito repellent creams', 'Drain standing water around residential areas', 'Take preventive antimalarial pills when traveling to endemic zones'],
        'recommended_doctor': 'General Physician / Infectious Disease Specialist'
    },
    {
        'name': 'Dengue',
        'description': 'A mosquito-borne viral disease causing severe flu-like symptoms and potentially life-threatening hemorrhagic fever.',
        'causes': ['Dengue virus (DENV-1, -2, -3, or -4)', 'Bite of an infected Aedes aegypti mosquito'],
        'symptoms': ['fever', 'headache', 'body_ache', 'joint_pain', 'skin_rash', 'fatigue', 'loss_of_appetite', 'nausea'],
        'precautions': ['Use mosquito repellents and wear long-sleeved clothes', 'Do NOT take Aspirin or Ibuprofen (only Paracetamol) to prevent bleeding', 'Keep body hydrated with fluids', 'Ensure no stagnant water collects near the home'],
        'recommended_doctor': 'General Physician'
    },
    {
        'name': 'Typhoid',
        'description': 'A systemic bacterial infection caused by Salmonella Typhi, characterized by prolonged high fever, headache, and abdominal symptoms.',
        'causes': ['Salmonella typhi bacteria', 'Consumption of contaminated food or water', 'Poor sanitation and hygiene practices'],
        'symptoms': ['fever', 'headache', 'abdominal_pain', 'diarrhea', 'constipation', 'fatigue', 'loss_of_appetite'],
        'precautions': ['Drink only boiled or bottled mineral water', 'Wash hands before eating or cooking', 'Eat hot, thoroughly cooked foods', 'Get vaccinated against Typhoid'],
        'recommended_doctor': 'General Physician / Gastroenterologist'
    },
    {
        'name': 'Chickenpox',
        'description': 'A highly contagious viral infection causing an itchy, blister-like skin rash and mild fever.',
        'causes': ['Varicella-zoster virus (VZV)', 'Direct contact with blisters of an infected person', 'Inhalation of respiratory droplets from coughing/sneezing'],
        'symptoms': ['fever', 'fatigue', 'loss_of_appetite', 'headache', 'skin_rash', 'itching'],
        'precautions': ['Get vaccinated (Varicella vaccine)', 'Avoid close contact with active cases', 'Maintain isolation to prevent spread', 'Apply calamine lotion to soothe itching'],
        'recommended_doctor': 'General Physician / Dermatologist'
    },
    {
        'name': 'Tuberculosis',
        'description': 'A serious infectious bacterial disease that mainly affects the lungs, requiring long-term antibiotic combinations.',
        'causes': ['Mycobacterium tuberculosis bacteria', 'Inhalation of microscopic airborne droplets from active tuberculosis patients'],
        'symptoms': ['cough', 'fatigue', 'unexplained_weight_loss', 'fever', 'sweating', 'loss_of_appetite', 'shortness_of_breath'],
        'precautions': ['Strictly complete the 6-9 month antibiotic course (DOTS)', 'Avoid close contact with active pulmonary patients', 'Ensure good room ventilation', 'Wear masks around vulnerable individuals'],
        'recommended_doctor': 'Pulmonologist / Infectious Disease Specialist'
    },
    {
        'name': 'Pneumonia',
        'description': 'An inflammatory condition of the lung alveoli, which fill with pus or fluid, causing cough and breathing problems.',
        'causes': ['Bacterial (Streptococcus pneumoniae) or viral infections', 'Aspiration of foreign matter', 'Weakened immune system'],
        'symptoms': ['fever', 'chills', 'cough', 'shortness_of_breath', 'chest_tightness', 'fatigue', 'sweating'],
        'precautions': ['Get the pneumococcal and annual flu vaccines', 'Avoid smoking and excessive alcohol', 'Wash hands regularly', 'Allow adequate recovery time after respiratory infections'],
        'recommended_doctor': 'Pulmonologist / General Physician'
    },
    {
        'name': 'Gastroenteritis',
        'description': 'Inflammation of the stomach and intestines (stomach flu), typically resulting in vomiting and watery diarrhea.',
        'causes': ['Rotavirus or Norovirus infections', 'Bacterial toxins in contaminated food', 'Poor personal hygiene'],
        'symptoms': ['nausea', 'vomiting', 'diarrhea', 'abdominal_pain', 'fever', 'body_ache', 'loss_of_appetite'],
        'precautions': ['Drink Oral Rehydration Salts (ORS) to prevent dehydration', 'Wash hands thoroughly with soap', 'Avoid eating raw or street foods', 'Avoid sharing utensils with sick individuals'],
        'recommended_doctor': 'Gastroenterologist'
    },
    {
        'name': 'Urinary Tract Infection (UTI)',
        'description': 'An infection in any part of the urinary system, most commonly involving the bladder and urethra.',
        'causes': ['Escherichia coli (E. coli) bacteria', 'Poor hygiene practices', 'Incomplete bladder emptying'],
        'symptoms': ['burning_urination', 'frequent_urination', 'pelvic_pain', 'fever', 'dark_urine'],
        'precautions': ['Drink plenty of water daily', 'Avoid delaying urination when needed', 'Maintain good personal hygiene', 'Consult a doctor for appropriate antibiotics'],
        'recommended_doctor': 'Urologist / General Physician'
    },
    {
        'name': 'Allergy',
        'description': 'A hypersensitive reaction of the immune system to typically harmless environmental substances like pollen, dust, or food.',
        'causes': ['Allergen exposure (pollen, dust mites, mold spores)', 'Genetic predisposition'],
        'symptoms': ['sneezing', 'runny_nose', 'watery_eyes', 'itching', 'skin_rash'],
        'precautions': ['Avoid known allergen triggers', 'Take antihistamine medications as prescribed', 'Keep indoor spaces clean and vacuumed', 'Use air purifiers with HEPA filters'],
        'recommended_doctor': 'Allergist / Immunologist'
    },
    {
        'name': 'GERD (Acid Reflux)',
        'description': 'A digestive disorder where acidic stomach contents flow back into the esophagus, causing irritation and heartburn.',
        'causes': ['Weakness of the lower esophageal sphincter (LES)', 'Obesity and smoking', 'Consuming fatty, spicy, or acidic foods'],
        'symptoms': ['heartburn', 'difficulty_swallowing', 'nausea', 'chest_tightness', 'abdominal_pain'],
        'precautions': ['Avoid lying down for 2-3 hours after eating', 'Eat smaller, frequent meals', 'Elevate the head of your bed', 'Limit spicy, fatty, or caffeinated foods'],
        'recommended_doctor': 'Gastroenterologist'
    },
    {
        'name': 'Arthritis',
        'description': 'Joint inflammation characterized by pain, swelling, stiffness, and reduced range of joint motion.',
        'causes': ['Age-related wear and tear (Osteoarthritis)', 'Autoimmune joint destruction (Rheumatoid arthritis)', 'Uric acid accumulation (Gout)'],
        'symptoms': ['joint_pain', 'body_ache', 'muscle_weakness', 'fatigue'],
        'precautions': ['Engage in low-impact exercises (swimming, yoga)', 'Maintain a healthy body weight to reduce joint pressure', 'Apply hot or cold packs to relieve pain', 'Consult a rheumatologist for therapy options'],
        'recommended_doctor': 'Rheumatologist / Orthopedician'
    },
    {
        'name': 'Hepatitis',
        'description': 'Inflammation of the liver tissue, most commonly caused by a viral infection, leading to jaundice and liver fatigue.',
        'causes': ['Hepatitis viruses (A, B, C, D, or E)', 'Excessive alcohol consumption', 'Exposure to toxic chemicals'],
        'symptoms': ['yellowing_of_skin', 'yellowing_of_eyes', 'dark_urine', 'abdominal_pain', 'nausea', 'vomiting', 'loss_of_appetite', 'fatigue', 'fever'],
        'precautions': ['Get vaccinated (Hepatitis A and B)', 'Avoid sharing needles, razors, or toothbrushes', 'Limit alcohol consumption', 'Practice safe sex and wash hands before eating'],
        'recommended_doctor': 'Hepatologist / Gastroenterologist'
    },
    {
        'name': 'Jaundice',
        'description': 'A clinical state resulting in yellowing of the skin and eyes, caused by high levels of bilirubin in the blood.',
        'causes': ['Liver inflammation or disease', 'Obstruction of the bile duct (gallstones)', 'Rapid destruction of red blood cells'],
        'symptoms': ['yellowing_of_skin', 'yellowing_of_eyes', 'dark_urine', 'fatigue', 'abdominal_pain', 'fever'],
        'precautions': ['Avoid fatty, fried, and heavy foods', 'Drink plenty of boiled water', 'Get adequate physical rest', 'Consult a doctor immediately to diagnose the underlying liver issue'],
        'recommended_doctor': 'Gastroenterologist / Hepatologist'
    }
]

def get_db_connection():
    """
    Establish database connection. If running in a Flask request context,
    reuse the connection stored in Flask's 'g' object. Otherwise, return a new connection.
    """
    try:
        if current_app:
            if 'db' not in g:
                g.db = sqlite3.connect(
                    current_app.config['DATABASE_PATH']
                )
                g.db.row_factory = sqlite3.Row
                g.db.execute("PRAGMA foreign_keys = ON;")
            return g.db
    except RuntimeError:
        pass
        
    conn = sqlite3.connect(Config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def close_db(e=None):
    """Close the database connection for the current Flask request context."""
    db = g.pop('db', None)
    if db is not None:
        db.close()

def seed_disease_data(db):
    """Programmatically populates the disease_info table if it is currently empty."""
    cursor = db.cursor()
    cursor.execute("SELECT COUNT(*) FROM disease_info")
    count = cursor.fetchone()[0]
    
    if count == 0:
        print("Seeding database with clinical disease data...")
        for disease in DISEASE_SEEDS:
            cursor.execute(
                "INSERT INTO disease_info (name, description, causes, symptoms, precautions, recommended_doctor) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    disease['name'],
                    disease['description'],
                    json.dumps(disease['causes']),
                    json.dumps(disease['symptoms']),
                    json.dumps(disease['precautions']),
                    disease['recommended_doctor']
                )
            )
        db.commit()
        print(f"Seeded {len(DISEASE_SEEDS)} diseases successfully.")
    else:
        print(f"Database already contains {count} disease profiles. Seeding skipped.")

def init_db():
    """Initialize database tables using schema.sql DDL script and seed data."""
    db = get_db_connection()
    schema_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'schema.sql')
    
    with open(schema_path, 'r') as f:
        db.executescript(f.read())
        
    db.commit()
    
    # Call the seed function
    seed_disease_data(db)
    
    db.close()
    print("Database initialization and seeding completed.")

def query_db(query, args=(), one=False):
    """Helper function to query the database."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(query, args)
    rv = cur.fetchall()
    cur.close()
    
    try:
        if not current_app:
            conn.commit()
            conn.close()
    except RuntimeError:
        conn.commit()
        conn.close()
        
    return (rv[0] if rv else None) if one else rv

def insert_db(query, args=()):
    """Helper function to perform inserts/updates."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(query, args)
    last_id = cur.lastrowid
    
    try:
        if current_app:
            conn.commit()
        else:
            conn.commit()
            conn.close()
    except RuntimeError:
        conn.commit()
        conn.close()
        
    cur.close()
    return last_id
