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
        'diet_recommendations': ['Warm broths and chicken soup', 'Herbal teas with honey', 'Vitamin C-rich fruits (oranges, strawberries)', 'Stay highly hydrated with plenty of water'],
        'lifestyle_changes': ['Get plenty of bed rest', 'Avoid intense physical activities', 'Use a humidifier to soothe airways', 'Wash bedding and clothes frequently to prevent reinfection'],
        'recommended_doctor': 'General Physician'
    },
    {
        'name': 'Common Cold',
        'description': 'A mild viral infection of the nose, sinuses, and throat causing runny nose, sore throat, and sneezing.',
        'causes': ['Rhinoviruses or Coronaviruses', 'Airborne transmission of respiratory droplets', 'Direct hand-to-hand contact with infected individuals'],
        'symptoms': ['runny_nose', 'sneezing', 'sore_throat', 'cough', 'watery_eyes', 'fatigue', 'headache'],
        'precautions': ['Wash hands frequently', 'Avoid touching eyes, nose, and mouth', 'Clean surfaces regularly', 'Stay warm and hydrated'],
        'diet_recommendations': ['Citrus fruits and juices', 'Garlic and ginger teas', 'Warm chicken broth', 'Foods rich in zinc (spinach, pumpkin seeds)'],
        'lifestyle_changes': ['Get adequate sleep and rest', 'Gargle with warm salt water', 'Avoid cold environments', 'Avoid exposure to smoke and air pollutants'],
        'recommended_doctor': 'General Physician'
    },
    {
        'name': 'Covid-19',
        'description': 'An infectious respiratory disease caused by the SARS-CoV-2 virus, ranging from mild symptoms to severe respiratory distress.',
        'causes': ['SARS-CoV-2 virus', 'Respiratory droplets from coughs/sneezes', 'Close physical proximity with infected patients'],
        'symptoms': ['fever', 'cough', 'sore_throat', 'fatigue', 'body_ache', 'headache', 'shortness_of_breath', 'loss_of_taste', 'loss_of_smell'],
        'precautions': ['Wear face masks in public', 'Get vaccinated and booster shots', 'Maintain physical distancing (6 feet)', 'Monitor oxygen saturation levels'],
        'diet_recommendations': ['High-protein foods (eggs, legumes, lean meat)', 'Fresh fruits and vegetables', 'Plenty of warm fluids', 'Stay hydrated with water and electrolyte solutions'],
        'lifestyle_changes': ['Strictly isolate from others', 'Monitor oxygen saturation levels and temperature daily', 'Practice breathing exercises', 'Ensure adequate ventilation in your isolation room'],
        'recommended_doctor': 'Pulmonologist / Infectious Disease Specialist'
    },
    {
        'name': 'Diabetes',
        'description': 'A chronic metabolic disorder characterized by high blood glucose levels resulting from defects in insulin secretion or action.',
        'causes': ['Genetic predisposition', 'Lack of physical exercise and sedentary lifestyle', 'Autoimmune destruction of pancreatic beta cells'],
        'symptoms': ['increased_thirst', 'frequent_urination', 'unexplained_weight_loss', 'fatigue', 'muscle_weakness'],
        'precautions': ['Adopt a low-sugar, fiber-rich diet', 'Exercise regularly (30 minutes daily)', 'Monitor blood glucose levels', 'Adhere to prescribed medication or insulin therapy'],
        'diet_recommendations': ['Whole grains (oats, brown rice)', 'Leafy green vegetables (spinach, kale)', 'Lean proteins and nuts', 'Avoid sugary drinks and refined carbohydrates'],
        'lifestyle_changes': ['Engage in at least 30 minutes of daily physical exercise', 'Monitor blood glucose levels regularly', 'Maintain a healthy body weight', 'Prioritize stress management and adequate sleep'],
        'recommended_doctor': 'Endocrinologist'
    },
    {
        'name': 'Hypertension',
        'description': 'A long-term medical condition where the blood pressure in the arteries is persistently elevated, increasing cardiovascular risks.',
        'causes': ['High dietary salt intake', 'Lack of exercise and obesity', 'Chronic stress and genetic factors'],
        'symptoms': ['high_blood_pressure', 'headache', 'dizziness', 'fatigue'],
        'precautions': ['Reduce dietary sodium intake', 'Manage daily stress levels', 'Maintain a healthy weight', 'Take prescribed antihypertensive medications daily'],
        'diet_recommendations': ['Low-sodium meals (DASH diet)', 'Potassium-rich foods (bananas, spinach)', 'Whole grains and lean poultry', 'Avoid fatty, fried, or highly processed foods'],
        'lifestyle_changes': ['Incorporate 30 minutes of aerobic exercise daily', 'Practice relaxation techniques like meditation or yoga', 'Limit alcohol consumption', 'Avoid smoking and tobacco products'],
        'recommended_doctor': 'Cardiologist'
    },
    {
        'name': 'Asthma',
        'description': 'A chronic condition characterized by inflammation and narrowing of the airways, causing breathing difficulties.',
        'causes': ['Allergen exposure (dust, pollen, pet dander)', 'Air pollution and tobacco smoke', 'Physical exertion or cold air'],
        'symptoms': ['shortness_of_breath', 'wheezing', 'chest_tightness', 'cough'],
        'precautions': ['Identify and avoid asthma triggers', 'Always carry a rescue inhaler', 'Discuss a long-term controller plan with a doctor', 'Monitor breathing with a peak flow meter'],
        'diet_recommendations': ['Magnesium-rich foods (spinach, pumpkin seeds)', 'Omega-3 fatty acid foods (fish, flaxseeds)', 'Apples and carrots', 'Avoid food preservatives containing sulfites'],
        'lifestyle_changes': ['Avoid known allergen and dust triggers', 'Use indoor air purifiers and wash bedding weekly', 'Perform light breathing exercises', 'Avoid cold drafts and strenuous outdoor activity when air quality is poor'],
        'recommended_doctor': 'Pulmonologist / Allergist'
    },
    {
        'name': 'Migraine',
        'description': 'A neurological condition characterized by intense, debilitating headaches, often accompanied by sensory disturbances.',
        'causes': ['Hormonal fluctuations', 'Environmental triggers (bright lights, strong smells)', 'Stress or sleep deprivation'],
        'symptoms': ['headache', 'nausea', 'sensitivity_to_light', 'vomiting', 'dizziness', 'neck_pain'],
        'precautions': ['Rest in a dark, quiet room during attacks', 'Maintain a consistent sleep schedule', 'Stay hydrated and eat at regular times', 'Keep a headache diary to identify triggers'],
        'diet_recommendations': ['Magnesium-rich foods (almonds, spinach)', 'Ginger and chamomile teas', 'Maintain consistent meal times', 'Avoid triggers: caffeine, aged cheese, artificial sweeteners, processed meats'],
        'lifestyle_changes': ['Maintain a strict, consistent sleep schedule', 'Practice daily stress-relief techniques', 'Avoid sudden exposure to bright or flickering lights', 'Keep a detailed headache diary to track symptoms'],
        'recommended_doctor': 'Neurologist'
    },
    {
        'name': 'Malaria',
        'description': 'A life-threatening blood disease transmitted by the bite of the female Anopheles mosquito, causing cyclic fever and chills.',
        'causes': ['Plasmodium parasites', 'Bite of an infected female Anopheles mosquito', 'Rarely via blood transfusions'],
        'symptoms': ['fever', 'chills', 'sweating', 'headache', 'body_ache', 'nausea', 'vomiting', 'diarrhea'],
        'precautions': ['Use mosquito nets treated with insecticide', 'Apply mosquito repellent creams', 'Drain standing water around residential areas', 'Take preventive antimalarial pills when traveling to endemic zones'],
        'diet_recommendations': ['Easily digestible soft foods (mashed foods, soups)', 'High-calorie liquid diets', 'Fresh coconut water', 'Boiled vegetables', 'Avoid oily or heavily spiced dishes'],
        'lifestyle_changes': ['Rest in a clean, mosquito-free environment', 'Wear protective long-sleeved clothing', 'Maintain strict personal hygiene', 'Avoid heavy physical exertion during recovery'],
        'recommended_doctor': 'General Physician / Infectious Disease Specialist'
    },
    {
        'name': 'Dengue',
        'description': 'A mosquito-borne viral disease causing severe flu-like symptoms and potentially life-threatening hemorrhagic fever.',
        'causes': ['Dengue virus (DENV-1, -2, -3, or -4)', 'Bite of an infected Aedes aegypti mosquito'],
        'symptoms': ['fever', 'headache', 'body_ache', 'joint_pain', 'skin_rash', 'fatigue', 'loss_of_appetite', 'nausea'],
        'precautions': ['Use mosquito repellents and wear long-sleeved clothes', 'Do NOT take Aspirin or Ibuprofen (only Paracetamol) to prevent bleeding', 'Keep body hydrated with fluids', 'Ensure no stagnant water collects near the home'],
        'diet_recommendations': ['Stay highly hydrated with ORS, coconut water, and fresh juices', 'Papaya leaf extract (helps support platelet counts)', 'Light vegetable soups', 'Avoid dark-colored foods (to help detect gastrointestinal bleeding)'],
        'lifestyle_changes': ['Ensure complete bed rest', 'Avoid contact sports or strenuous activities to prevent injury and bleeding', 'Sleep under insecticide-treated mosquito nets', 'Keep residential areas clear of standing water'],
        'recommended_doctor': 'General Physician'
    },
    {
        'name': 'Typhoid',
        'description': 'A systemic bacterial infection caused by Salmonella Typhi, characterized by prolonged high fever, headache, and abdominal symptoms.',
        'causes': ['Salmonella typhi bacteria', 'Consumption of contaminated food or water', 'Poor sanitation and hygiene practices'],
        'symptoms': ['fever', 'headache', 'abdominal_pain', 'diarrhea', 'constipation', 'fatigue', 'loss_of_appetite'],
        'precautions': ['Drink only boiled or bottled mineral water', 'Wash hands before eating or cooking', 'Eat hot, thoroughly cooked foods', 'Get vaccinated against Typhoid'],
        'diet_recommendations': ['High-calorie soft foods (mashed potatoes, porridge)', 'Ripe bananas and applesauce', 'Boiled water and ORS fluids', 'Low-fiber foods to protect intestines', 'Avoid raw fruits and vegetables'],
        'lifestyle_changes': ['Strictly wash hands with soap before handling food', 'Get plenty of bed rest to conserve energy', 'Isolate personal dining utensils', 'Maintain strict personal and sanitation hygiene'],
        'recommended_doctor': 'General Physician / Gastroenterologist'
    },
    {
        'name': 'Chickenpox',
        'description': 'A highly contagious viral infection causing an itchy, blister-like skin rash and mild fever.',
        'causes': ['Varicella-zoster virus (VZV)', 'Direct contact with blisters of an infected person', 'Inhalation of respiratory droplets from coughing/sneezing'],
        'symptoms': ['fever', 'fatigue', 'loss_of_appetite', 'headache', 'skin_rash', 'itching'],
        'precautions': ['Get vaccinated (Varicella vaccine)', 'Avoid close contact with active cases', 'Maintain isolation to prevent spread', 'Apply calamine lotion to soothe itching'],
        'diet_recommendations': ['Soft, bland, non-acidic foods (yogurt, oatmeal, mashed potatoes)', 'Cold fluids to soothe mouth sores', 'Avoid spicy, salty, or acidic foods that irritate mouth sores'],
        'lifestyle_changes': ['Keep skin clean, cool, and dry', 'Take cool baths with baking soda or colloidal oatmeal to relieve itching', 'Avoid scratching the rash to prevent scarring (wear soft mittens)', 'Isolate to protect others'],
        'recommended_doctor': 'General Physician / Dermatologist'
    },
    {
        'name': 'Tuberculosis',
        'description': 'A serious infectious bacterial disease that mainly affects the lungs, requiring long-term antibiotic combinations.',
        'causes': ['Mycobacterium tuberculosis bacteria', 'Inhalation of microscopic airborne droplets from active tuberculosis patients'],
        'symptoms': ['cough', 'fatigue', 'unexplained_weight_loss', 'fever', 'sweating', 'loss_of_appetite', 'shortness_of_breath'],
        'precautions': ['Strictly complete the 6-9 month antibiotic course (DOTS)', 'Avoid close contact with active pulmonary patients', 'Ensure good room ventilation', 'Wear masks around vulnerable individuals'],
        'diet_recommendations': ['Nutrient-dense foods', 'High-protein foods (eggs, milk, fish, legumes)', 'Leafy green vegetables', 'Bananas and whole grains', 'Avoid alcohol and tobacco completely'],
        'lifestyle_changes': ['Ensure ample rest and fresh air', 'Cover mouth and nose when coughing or sneezing', 'Ensure room ventilation by keeping windows open', 'Strictly adhere to the DOTS medication schedule', 'Wear face masks in public'],
        'recommended_doctor': 'Pulmonologist / Infectious Disease Specialist'
    },
    {
        'name': 'Pneumonia',
        'description': 'An inflammatory condition of the lung alveoli, which fill with pus or fluid, causing cough and breathing problems.',
        'causes': ['Bacterial (Streptococcus pneumoniae) or viral infections', 'Aspiration of foreign matter', 'Weakened immune system'],
        'symptoms': ['fever', 'chills', 'cough', 'shortness_of_breath', 'chest_tightness', 'fatigue', 'sweating'],
        'precautions': ['Get the pneumococcal and annual flu vaccines', 'Avoid smoking and excessive alcohol', 'Wash hands regularly', 'Allow adequate recovery time after respiratory infections'],
        'diet_recommendations': ['Warm broths and clear vegetable soups', 'Citrus fruits for Vitamin C boost', 'Ginger and turmeric herbal teas', 'Drink plenty of water to help thin and loosen mucus'],
        'lifestyle_changes': ['Rest in an inclined position to make breathing easier', 'Avoid all exposure to tobacco smoke or cold drafts', 'Use a cool-mist humidifier in your room', 'Perform light deep-breathing exercises as tolerated'],
        'recommended_doctor': 'Pulmonologist / General Physician'
    },
    {
        'name': 'Gastroenteritis',
        'description': 'Inflammation of the stomach and intestines (stomach flu), typically resulting in vomiting and watery diarrhea.',
        'causes': ['Rotavirus or Norovirus infections', 'Bacterial toxins in contaminated food', 'Poor personal hygiene'],
        'symptoms': ['nausea', 'vomiting', 'diarrhea', 'abdominal_pain', 'fever', 'body_ache', 'loss_of_appetite'],
        'precautions': ['Drink Oral Rehydration Salts (ORS) to prevent dehydration', 'Wash hands thoroughly with soap', 'Avoid eating raw or street foods', 'Avoid sharing utensils with sick individuals'],
        'diet_recommendations': ['BRAT diet (Bananas, Rice, Applesauce, Toast)', 'ORS solutions and clear broths', 'Plain crackers or oatmeal', 'Avoid dairy, caffeine, alcohol, nicotine, and spicy or fatty foods'],
        'lifestyle_changes': ['Wash hands thoroughly with soap and water frequently', 'Disinfect toilets, handles, and kitchen surfaces', 'Allow plenty of physical rest', 'Sip fluids slowly in small, frequent amounts'],
        'recommended_doctor': 'Gastroenterologist'
    },
    {
        'name': 'Urinary Tract Infection (UTI)',
        'description': 'An infection in any part of the urinary system, most commonly involving the bladder and urethra.',
        'causes': ['Escherichia coli (E. coli) bacteria', 'Poor hygiene practices', 'Incomplete bladder emptying'],
        'symptoms': ['burning_urination', 'frequent_urination', 'pelvic_pain', 'fever', 'dark_urine'],
        'precautions': ['Drink plenty of water daily', 'Avoid delaying urination when needed', 'Maintain good personal hygiene', 'Consult a doctor for appropriate antibiotics'],
        'diet_recommendations': ['Unsweetened cranberry juice', 'Drink plenty of water (8-10 glasses daily)', 'Vitamin C-rich fruits', 'Avoid caffeine, alcohol, and carbonated beverages'],
        'lifestyle_changes': ['Maintain clean personal hygiene practices', 'Urinate as soon as the urge arises (do not hold it)', 'Empty the bladder before and after sexual activity', 'Wear loose-fitting, breathable cotton underwear'],
        'recommended_doctor': 'Urologist / General Physician'
    },
    {
        'name': 'Allergy',
        'description': 'A hypersensitive reaction of the immune system to typically harmless environmental substances like pollen, dust, or food.',
        'causes': ['Allergen exposure (pollen, dust mites, mold spores)', 'Genetic predisposition'],
        'symptoms': ['sneezing', 'runny_nose', 'watery_eyes', 'itching', 'skin_rash'],
        'precautions': ['Avoid known allergen triggers', 'Take antihistamine medications as prescribed', 'Keep indoor spaces clean and vacuumed', 'Use air purifiers with HEPA filters'],
        'diet_recommendations': ['Anti-inflammatory foods (ginger, turmeric, berries)', 'Local organic honey (helps build tolerance to local pollen)', 'Vitamin C-rich foods', 'Avoid known food allergen triggers'],
        'lifestyle_changes': ['Keep windows closed during high pollen seasons', 'Vacuum and clean dust mites from bedding and carpets regularly', 'Wash clothes after spending time outdoors', 'Use HEPA air purifiers inside home'],
        'recommended_doctor': 'Allergist / Immunologist'
    },
    {
        'name': 'GERD (Acid Reflux)',
        'description': 'A digestive disorder where acidic stomach contents flow back into the esophagus, causing irritation and heartburn.',
        'causes': ['Weakness of the lower esophageal sphincter (LES)', 'Obesity and smoking', 'Consuming fatty, spicy, or acidic foods'],
        'symptoms': ['heartburn', 'difficulty_swallowing', 'nausea', 'chest_tightness', 'abdominal_pain'],
        'precautions': ['Avoid lying down for 2-3 hours after eating', 'Eat smaller, frequent meals', 'Elevate the head of your bed', 'Limit spicy, fatty, or caffeinated foods'],
        'diet_recommendations': ['Non-citrus fruits (melons, bananas, apples)', 'Oatmeal and whole grain bread', 'Ginger tea or chamomile tea', 'Lean meats (chicken, fish) cooked without oils', 'Avoid chocolate, caffeine, tomatoes, and peppermint'],
        'lifestyle_changes': ['Do not lie down for at least 2-3 hours after eating a meal', 'Eat smaller, more frequent meals rather than large portions', 'Elevate the head of your bed by 6 inches', 'Maintain a healthy weight and avoid tight clothing around the abdomen'],
        'recommended_doctor': 'Gastroenterologist'
    },
    {
        'name': 'Arthritis',
        'description': 'Joint inflammation characterized by pain, swelling, stiffness, and reduced range of joint motion.',
        'causes': ['Age-related wear and tear (Osteoarthritis)', 'Autoimmune joint destruction (Rheumatoid arthritis)', 'Uric acid accumulation (Gout)'],
        'symptoms': ['joint_pain', 'body_ache', 'muscle_weakness', 'fatigue'],
        'precautions': ['Engage in low-impact exercises (swimming, yoga)', 'Maintain a healthy body weight to reduce joint pressure', 'Apply hot or cold packs to relieve pain', 'Consult a rheumatologist for therapy options'],
        'diet_recommendations': ['Anti-inflammatory Mediterranean diet', 'Omega-3 rich fish (salmon, sardines)', 'Extra virgin olive oil', 'Walnuts and colorful berries', 'Avoid processed sugars and red meat'],
        'lifestyle_changes': ['Perform regular low-impact activities like swimming or walking', 'Practice joint protection techniques (use larger joints for lifting)', 'Apply warm heat pads for stiffness or cold ice packs for acute swelling', 'Maintain a healthy weight to ease stress on knees and hips'],
        'recommended_doctor': 'Rheumatologist / Orthopedician'
    },
    {
        'name': 'Hepatitis',
        'description': 'Inflammation of the liver tissue, most commonly caused by a viral infection, leading to jaundice and liver fatigue.',
        'causes': ['Hepatitis viruses (A, B, C, D, or E)', 'Excessive alcohol consumption', 'Exposure to toxic chemicals'],
        'symptoms': ['yellowing_of_skin', 'yellowing_of_eyes', 'dark_urine', 'abdominal_pain', 'nausea', 'vomiting', 'loss_of_appetite', 'fatigue', 'fever'],
        'precautions': ['Get vaccinated (Hepatitis A and B)', 'Avoid sharing needles, razors, or toothbrushes', 'Limit alcohol consumption', 'Practice safe sex and wash hands before eating'],
        'diet_recommendations': ['Low-fat, high-carbohydrate meals', 'Fresh fruits and vegetable juices', 'Whole grains (oats, barley)', 'Lean proteins in moderation', 'Strictly avoid alcohol and processed, fatty foods'],
        'lifestyle_changes': ['Ensure complete physical rest to aid liver healing', 'Avoid self-medicating or taking unnecessary drugs/supplements (protects liver)', 'Practice strict hand washing and personal hygiene', 'Monitor liver enzymes periodically'],
        'recommended_doctor': 'Hepatologist / Gastroenterologist'
    },
    {
        'name': 'Jaundice',
        'description': 'A clinical state resulting in yellowing of the skin and eyes, caused by high levels of bilirubin in the blood.',
        'causes': ['Liver inflammation or disease', 'Obstruction of the bile duct (gallstones)', 'Rapid destruction of red blood cells'],
        'symptoms': ['yellowing_of_skin', 'yellowing_of_eyes', 'dark_urine', 'fatigue', 'abdominal_pain', 'fever'],
        'precautions': ['Avoid fatty, fried, and heavy foods', 'Drink plenty of boiled water', 'Get adequate physical rest', 'Consult a doctor immediately to diagnose the underlying liver issue'],
        'diet_recommendations': ['Mainly liquid or semi-liquid foods to start', 'Fresh coconut water and sugarcane juice', 'Boiled vegetables without oil', 'Ripe bananas and papayas', 'Avoid oily, fried, spicy, or heavy dairy items'],
        'lifestyle_changes': ['Get absolute bed rest and avoid physical exertion', 'Keep hydrated with safe, boiled drinking water', 'Strictly avoid alcohol or liver-taxing substances', 'Consult a doctor to treat the root cause of high bilirubin levels'],
        'recommended_doctor': 'Gastroenterologist / Hepatologist'
    },
    {
        'name': 'Heart Disease',
        'description': 'A broad term for conditions affecting the heart structure and blood vessels, including coronary artery disease, heart failure, and arrhythmias.',
        'causes': ['High blood pressure (hypertension)', 'Elevated LDL cholesterol', 'Smoking and tobacco use', 'Sedentary lifestyle and obesity', 'Diabetes and genetic factors'],
        'symptoms': ['chest_pain', 'shortness_of_breath', 'dizziness', 'fatigue', 'irregular_heartbeat', 'swelling_in_legs'],
        'precautions': ['Adopt a heart-healthy low-sodium, low-fat diet', 'Engage in 150 minutes of moderate exercise per week', 'Avoid smoking and limit alcohol intake', 'Monitor blood pressure and cholesterol levels regularly'],
        'diet_recommendations': ['DASH and Mediterranean diet patterns', 'Omega-3 fatty acid rich foods (salmon, flaxseeds, walnuts)', 'Whole grains (oats, brown rice)', 'Fresh fruits and leafy green vegetables', 'Limit saturated fats, trans fats, and processed sodium'],
        'lifestyle_changes': ['Maintain 30 minutes of daily physical exercise', 'Practice stress management techniques like meditation', 'Maintain a healthy Body Mass Index (BMI)', 'Schedule regular cardiovascular checkups'],
        'recommended_doctor': 'Cardiologist'
    },
    {
        'name': 'Chronic Kidney Disease',
        'description': 'A gradual loss of kidney function over time, impairing the body\'s ability to filter waste products and excess fluids from the blood.',
        'causes': ['Uncontrolled High Blood Pressure (Hypertension)', 'Diabetes (Diabetic Nephropathy)', 'Glomerulonephritis', 'Long-term overuse of NSAID painkillers'],
        'symptoms': ['fatigue', 'swelling_in_feet_or_ankles', 'frequent_urination', 'nausea', 'loss_of_appetite', 'shortness_of_breath'],
        'precautions': ['Keep blood pressure and blood sugar strictly controlled', 'Limit daily sodium and protein intake as directed by a nephrologist', 'Stay adequately hydrated but follow fluid guidelines', 'Avoid unnecessary NSAID pain relievers'],
        'diet_recommendations': ['Low-sodium and low-potassium foods', 'Controlled protein intake (lean poultry, egg whites)', 'Apples, berries, and cabbage', 'Avoid high-phosphorus processed foods and dark sodas'],
        'lifestyle_changes': ['Monitor blood pressure daily', 'Avoid smoking and alcohol completely', 'Perform light physical exercise as tolerated', 'Get regular kidney function tests (serum creatinine, eGFR)'],
        'recommended_doctor': 'Nephrologist'
    },
    {
        'name': 'Breast Cancer',
        'description': 'A disease in which malignant cells form in the tissues of the breast, most commonly starting in the ducts or lobules.',
        'causes': ['Genetic mutations (BRCA1, BRCA2 genes)', 'Hormonal factors and advancing age', 'Family history of breast or ovarian cancer', 'Obesity and alcohol consumption'],
        'symptoms': ['painless_breast_lump', 'skin_changes_or_dimpling', 'nipple_discharge_or_inversion', 'breast_pain_or_swelling', 'swollen_lymph_nodes'],
        'precautions': ['Perform monthly self-breast examinations', 'Undergo regular mammogram screenings', 'Maintain a healthy weight and stay active', 'Limit alcohol consumption'],
        'diet_recommendations': ['Antioxidant-rich berries and cruciferous vegetables (broccoli, kale)', 'Whole grains and legumes', 'Green tea and flaxseeds', 'Avoid processed meats and excessive saturated fats'],
        'lifestyle_changes': ['Schedule routine clinical breast examinations', 'Engage in regular physical exercise', 'Maintain a healthy weight post-menopause', 'Discuss genetic risk factors with a specialist'],
        'recommended_doctor': 'Oncologist / Breast Specialist'
    },
    {
        'name': 'Liver Disease',
        'description': 'Damage to liver tissue that impairs its ability to filter toxins, produce bile, and assist metabolic functions.',
        'causes': ['Excessive alcohol consumption', 'Non-alcoholic fatty liver disease (NAFLD) linked to obesity/diabetes', 'Viral hepatitis (B, C)', 'Exposure to toxins or heavy drug use'],
        'symptoms': ['yellowing_of_skin', 'yellowing_of_eyes', 'abdominal_pain_and_swelling', 'dark_urine', 'chronic_fatigue', 'nausea', 'loss_of_appetite'],
        'precautions': ['Abstain completely from alcohol', 'Get vaccinated against Hepatitis A and B', 'Maintain a healthy body weight', 'Avoid self-medication and liver-toxic substances'],
        'diet_recommendations': ['Low-fat, plant-based nutrient-dense foods', 'Whole grains (oats, quinoa)', 'Fresh green leafy vegetables', 'Coffee in moderation (protective for liver health)', 'Avoid fried, sugary, and processed foods'],
        'lifestyle_changes': ['Maintain strict alcohol abstinence', 'Exercise regularly to reduce liver fat', 'Undergo regular liver enzyme tests (ALT, AST)', 'Maintain good personal sanitation'],
        'recommended_doctor': 'Hepatologist / Gastroenterologist'
    },
    {
        'name': 'Stroke',
        'description': 'A medical emergency occurring when blood supply to a part of the brain is interrupted, depriving brain tissue of oxygen and nutrients.',
        'causes': ['High blood pressure (Hypertension)', 'Smoking and elevated cholesterol', 'Diabetes and cardiovascular disease', 'Atrial fibrillation'],
        'symptoms': ['sudden_numbness_or_weakness', 'facial_droop', 'arm_weakness', 'speech_difficulty', 'sudden_confusion', 'severe_headache', 'dizziness'],
        'precautions': ['Strictly control high blood pressure', 'Stop smoking immediately', 'Manage blood sugar and cholesterol levels', 'Remember FAST: Face droop, Arm weakness, Speech difficulty, Time to call emergency'],
        'diet_recommendations': ['Plant-focused DASH or Mediterranean diet', 'Potassium-rich foods (bananas, spinach, sweet potatoes)', 'Fiber-rich oats and legumes', 'Avoid high-sodium, fried, and trans-fat foods'],
        'lifestyle_changes': ['Engage in daily aerobic exercise', 'Eliminate tobacco use', 'Limit alcohol intake', 'Take prescribed blood pressure or anticoagulant medications reliably'],
        'recommended_doctor': 'Neurologist / Vascular Surgeon'
    },
    {
        'name': 'Lung Cancer',
        'description': 'A type of cancer that begins in the lungs, strongly linked to inhaled carcinogens, especially tobacco smoke.',
        'causes': ['Tobacco smoking (primary or passive exposure)', 'Radon gas exposure', 'Occupational exposure to asbestos or chemicals', 'Air pollution and genetic factors'],
        'symptoms': ['persistent_cough', 'coughing_up_blood', 'chest_pain', 'shortness_of_breath', 'hoarseness', 'unexplained_weight_loss', 'wheezing'],
        'precautions': ['Avoid all forms of smoking and secondhand smoke', 'Test home environment for radon gas', 'Wear protective equipment if working with industrial hazards', 'Maintain an active lifestyle'],
        'diet_recommendations': ['Antioxidant-rich fruits and vegetables (berries, carrots, apples)', 'Cruciferous vegetables (broccoli, cabbage)', 'Green tea', 'Avoid processed and high-fat foods'],
        'lifestyle_changes': ['Seek smoking cessation support programs', 'Improve indoor ventilation and air quality', 'Get annual low-dose CT screening if high-risk long-term smoker', 'Perform light respiratory exercises'],
        'recommended_doctor': 'Pulmonologist / Thoracic Oncologist'
    }
]

HEALTH_TIPS_SEEDS = [
    # Nutrition general tips
    {'category': 'Nutrition', 'tip': 'Eat a colorful plate. Try to include 3-5 different colored vegetables and fruits in your meals daily to get a variety of vitamins and antioxidants.', 'disease_context': None},
    {'category': 'Nutrition', 'tip': 'Cut back on processed sugars. Opt for whole foods like raw nuts, fruits, and whole grains to keep energy levels stable throughout the day.', 'disease_context': None},
    {'category': 'Nutrition', 'tip': 'Stay hydrated. Drink at least 8-10 glasses of water daily. Hydration is vital for healthy digestion, circulation, and skin.', 'disease_context': None},
    {'category': 'Nutrition', 'tip': 'Include healthy fats in your diet, such as avocados, extra virgin olive oil, and walnuts. They support brain health and hormone regulation.', 'disease_context': None},
    
    # Exercise general tips
    {'category': 'Exercise', 'tip': 'Aim for 150 minutes of moderate aerobic activity weekly. A simple 30-minute brisk walk, five days a week, dramatically improves heart health.', 'disease_context': None},
    {'category': 'Exercise', 'tip': 'Incorporate strength training at least twice a week. Lifting weights or doing bodyweight exercises helps preserve bone density and muscle mass.', 'disease_context': None},
    {'category': 'Exercise', 'tip': 'Avoid prolonged sitting. Stand up, stretch, or walk around for 2 minutes every hour to improve blood circulation and reduce spinal pressure.', 'disease_context': None},
    {'category': 'Exercise', 'tip': 'Listen to your body. Warm up before exercising and cool down afterward to prevent muscle strains and injury.', 'disease_context': None},
    
    # Sleep general tips
    {'category': 'Sleep', 'tip': 'Aim for 7-9 hours of quality sleep per night. Sleep is essential for muscle recovery, brain health, and keeping your immune system strong.', 'disease_context': None},
    {'category': 'Sleep', 'tip': 'Set a consistent sleep schedule. Go to bed and wake up at the same time every day, even on weekends, to regulate your circadian rhythm.', 'disease_context': None},
    {'category': 'Sleep', 'tip': 'Disconnect from screens 30-60 minutes before bed. Blue light from smartphones and laptops inhibits melatonin production, making it harder to fall asleep.', 'disease_context': None},
    {'category': 'Sleep', 'tip': 'Keep your bedroom cool, dark, and quiet. A sleep-friendly environment signals your brain that it is time to wind down.', 'disease_context': None},
    
    # Disease Prevention general tips
    {'category': 'Disease Prevention', 'tip': 'Wash your hands frequently with soap and water for at least 20 seconds to prevent the spread of infectious viruses and bacteria.', 'disease_context': None},
    {'category': 'Disease Prevention', 'tip': 'Get scheduled health checkups. Early detection of blood pressure, cholesterol, or glucose anomalies is key to preventing long-term illness.', 'disease_context': None},
    {'category': 'Disease Prevention', 'tip': 'Prioritize stress management. Chronic stress raises cortisol levels, weakening the immune response. Try deep breathing or meditation.', 'disease_context': None},
    {'category': 'Disease Prevention', 'tip': 'Stay up-to-date with vaccinations. Vaccines are safe and provide the strongest protection against influenza, pneumonia, and other infections.', 'disease_context': None},

    # Disease-specific tips
    {'category': 'Disease Prevention', 'tip': 'For Influenza: Get your annual flu shot and isolate if symptoms develop. Drink warm broths to thin mucus.', 'disease_context': 'Influenza (Flu)'},
    {'category': 'Disease Prevention', 'tip': 'For Common Cold: Gargle with warm salt water to relieve sore throat. Rest is your body\'s best way to fight rhinoviruses.', 'disease_context': 'Common Cold'},
    {'category': 'Disease Prevention', 'tip': 'For Covid-19: Monitor oxygen levels with a pulse oximeter. Isolate in a well-ventilated space to protect family members.', 'disease_context': 'Covid-19'},
    {'category': 'Nutrition', 'tip': 'For Diabetes: Focus on fiber-rich, low-glycemic foods. Monitor blood sugar levels before and after meals.', 'disease_context': 'Diabetes'},
    {'category': 'Nutrition', 'tip': 'For Hypertension: Reduce sodium intake strictly to under 1,500 mg daily and adopt the low-fat DASH diet.', 'disease_context': 'Hypertension'},
    {'category': 'Disease Prevention', 'tip': 'For Asthma: Always keep a rescue inhaler in an accessible spot. Avoid strong scents, dust, and pollen triggers.', 'disease_context': 'Asthma'},
    {'category': 'Sleep', 'tip': 'For Migraine: Maintain a rigorous sleeping pattern. Sleep deprivation is one of the most common migraine triggers.', 'disease_context': 'Migraine'},
    {'category': 'Disease Prevention', 'tip': 'For Malaria: Sleep under insecticidal bed nets and drain stagnant water around your home. Seek immediate medical attention.', 'disease_context': 'Malaria'},
    {'category': 'Disease Prevention', 'tip': 'For Dengue: Stay hydrated with electrolyte fluids. Do not take NSAIDs like Aspirin or Ibuprofen, as they increase bleeding risks.', 'disease_context': 'Dengue'},
    {'category': 'Nutrition', 'tip': 'For Typhoid: Drink only boiled or bottled mineral water. Consume light, easily digestible soft foods.', 'disease_context': 'Typhoid'},
    {'category': 'Disease Prevention', 'tip': 'For Chickenpox: Take cool oatmeal baths to relieve skin itching and wear mittens to avoid scratching and scarring.', 'disease_context': 'Chickenpox'},
    {'category': 'Disease Prevention', 'tip': 'For Tuberculosis: Complete the full duration of your DOTS antibiotic course, even if you feel better. Good room ventilation is key.', 'disease_context': 'Tuberculosis'},
    {'category': 'Exercise', 'tip': 'For Pneumonia: Rest in an inclined position to make breathing easier. Avoid physical exertion until clear.', 'disease_context': 'Pneumonia'},
    {'category': 'Nutrition', 'tip': 'For Gastroenteritis: Sip Oral Rehydration Salts (ORS) slowly. Follow the BRAT diet (Bananas, Rice, Applesauce, Toast).', 'disease_context': 'Gastroenteritis'},
    {'category': 'Nutrition', 'tip': 'For UTI: Drink plenty of water and unsweetened cranberry juice to help flush bacteria out of the urinary tract.', 'disease_context': 'UTI'},
    {'category': 'Disease Prevention', 'tip': 'For Allergy: Wash your clothes and shower after spending time outdoors during high pollen seasons to remove allergens.', 'disease_context': 'Allergy'},
    {'category': 'Nutrition', 'tip': 'For GERD: Avoid lying down for 2-3 hours after eating, and avoid triggers like caffeine, chocolate, and fatty foods.', 'disease_context': 'GERD (Acid Reflux)'},
    {'category': 'Exercise', 'tip': 'For Arthritis: Keep joints moving with low-impact aerobic exercises like swimming, which eases joint stiffness without high pressure.', 'disease_context': 'Arthritis'},
    {'category': 'Nutrition', 'tip': 'For Hepatitis: Rest fully and avoid alcohol entirely. Eat a low-fat, high-carbohydrate diet to reduce liver strain.', 'disease_context': 'Hepatitis'},
    {'category': 'Nutrition', 'tip': 'For Jaundice: Rest completely and drink fresh sugarcane or coconut water. Avoid fried, heavy, or fatty dairy products.', 'disease_context': 'Jaundice'}
]

def get_db_connection():
    """
    Establish a database connection. If running in a Flask request context,
    reuse the connection stored in Flask's 'g' object. Otherwise, return a new connection.
    """
    try:
        if has_app_context():
            if 'db' not in g:
                conn = sqlite3.connect(current_app.config['DATABASE_PATH'], timeout=30.0, isolation_level=None)
                conn.row_factory = sqlite3.Row
                conn.execute("PRAGMA foreign_keys = ON;")
                conn.execute("PRAGMA busy_timeout = 30000;")
                g.db = conn
            return g.db
    except Exception:
        pass

    conn = sqlite3.connect(Config.DATABASE_PATH, timeout=30.0, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA busy_timeout = 30000;")
    return conn


def close_db(e=None):
    """Close the database connection for the current Flask request context."""
    db = g.pop('db', None)
    if db is not None:
        db.close()


def seed_disease_data(db):
    """Programmatically populates the disease_info table with missing seeds."""
    cursor = db.cursor()
    inserted_count = 0
    for disease in DISEASE_SEEDS:
        cursor.execute("SELECT COUNT(*) FROM disease_info WHERE name = ?", (disease['name'],))
        exists = cursor.fetchone()[0]
        if not exists:
            cursor.execute(
                "INSERT INTO disease_info (name, description, causes, symptoms, precautions, diet_recommendations, lifestyle_changes, recommended_doctor) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    disease['name'],
                    disease['description'],
                    json.dumps(disease['causes']),
                    json.dumps(disease['symptoms']),
                    json.dumps(disease['precautions']),
                    json.dumps(disease['diet_recommendations']),
                    json.dumps(disease['lifestyle_changes']),
                    disease['recommended_doctor']
                )
            )
            inserted_count += 1
    db.commit()
    if inserted_count > 0:
        print(f"Seeded {inserted_count} new disease profiles into database.")



def init_db():
    """Ensure the SQLite database exists and initialize its schema without deleting existing data."""
    db_path = Config.DATABASE_PATH
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    conn = sqlite3.connect(db_path, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA busy_timeout = 30000;")

    try:
        # Check if database is already initialized
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='disease_info';")
        tbl = cur.fetchone()
        if tbl:
            # Check if prediction_type column exists, add if missing
            cur.execute("PRAGMA table_info(predictions);")
            cols = [r[1] for r in cur.fetchall()]
            if 'prediction_type' not in cols:
                cur.execute("ALTER TABLE predictions ADD COLUMN prediction_type TEXT DEFAULT 'General';")
            conn.commit()
            cur.close()
            seed_disease_data(conn)
            return
        cur.close()

        schema_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'schema.sql')
        with open(schema_path, 'r', encoding='utf-8') as f:
            conn.executescript(f.read())
        conn.commit()
        seed_disease_data(conn)
        conn.commit()
        print("Database initialization and seeding completed.")
    except sqlite3.DatabaseError as exc:
        conn.rollback()
        print(f"Database initialization failed: {exc}")
        raise
    finally:
        conn.close()

from flask import g, current_app, has_app_context

def query_db(query, args=(), one=False):
    """Helper function to query the database."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(query, args)
    rv = cur.fetchall()
    cur.close()
    
    if has_app_context() and 'db' in g and g.db == conn:
        pass
    else:
        conn.commit()
        conn.close()
        
    return (rv[0] if rv else None) if one else rv

def insert_db(query, args=()):
    """Helper function to perform inserts/updates."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(query, args)
    last_id = cur.lastrowid
    cur.close()
    
    if has_app_context() and 'db' in g and g.db == conn:
        conn.commit()
    else:
        conn.commit()
        conn.close()
        
    return last_id
