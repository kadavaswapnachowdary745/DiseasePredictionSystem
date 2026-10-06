import re
import logging
from models.disease import Disease
from models.prediction import Prediction

logger = logging.getLogger('predihealth.chat')

# Disclaimer text to be appended to all chatbot responses
MEDICAL_DISCLAIMER = (
    "\n\n*Disclaimer: I am an AI Health Assistant, not a doctor. This information is for educational purposes "
    "and is not a replacement for professional medical advice, diagnosis, or treatment. Always consult a qualified "
    "healthcare provider for medical concerns.*"
)

# Common Health FAQs
FAQS = {
    r"boost.*immune|immune.*system": (
        "To help support and boost your immune system:\n"
        "• **Diet:** Focus on a nutrient-rich diet with plenty of fruits, vegetables, lean proteins, and healthy fats.\n"
        "• **Sleep:** Prioritize getting 7-9 hours of quality sleep per night.\n"
        "• **Exercise:** Engage in regular, moderate-intensity physical activity (like brisk walking).\n"
        "• **Hydration:** Drink plenty of water throughout the day.\n"
        "• **Stress:** Practice stress-management techniques such as mindfulness, yoga, or deep breathing exercises.\n"
        "• **Supplements:** Consider speaking with a doctor about Vitamin D, Vitamin C, and Zinc if your levels are low."
    ),
    r"what.*do.*fever|have.*fever|treat.*fever|high.*fever": (
        "If you are experiencing a fever:\n"
        "• **Hydration:** Drink plenty of fluids (water, herbal teas, or clear broths) to prevent dehydration.\n"
        "• **Rest:** Get ample bed rest to help your body fight the infection.\n"
        "• **Cooling:** Wear light, breathable clothing and use a light blanket. You can apply a cool, damp cloth to your forehead.\n"
        "• **Medication:** Over-the-counter fever reducers like Paracetamol (Acetaminophen) or Ibuprofen can help, but ensure you follow dosage instructions carefully.\n"
        "• **When to see a doctor:** Seek immediate medical care if the fever exceeds 103°F (39.4°C), lasts more than 3 days, or is accompanied by severe headache, stiff neck, shortness of breath, or confusion."
    ),
    r"how.*much.*water|drink.*water.*daily|daily.*water.*intake": (
        "Hydration needs vary by individual, activity level, and climate, but a good general rule of thumb is:\n"
        "• **General Guide:** Aim for about 8 to 10 glasses (approximately 2 to 2.5 liters) of water daily.\n"
        "• **Check Hydration:** Monitor your urine color; it should ideally be pale yellow or clear.\n"
        "• **Increase Intake:** Drink more water if you are exercising, in hot weather, or recovering from an illness (like fever, vomiting, or diarrhea)."
    ),
    r"difference.*cold.*flu|difference.*flu.*cold|cold.*vs.*flu|flu.*vs.*cold": (
        "While the common cold and influenza (flu) are both contagious respiratory viruses, they have distinct differences:\n"
        "• **Onset:** Flu symptoms hit suddenly and intensely, whereas cold symptoms build up gradually.\n"
        "• **Fever & Chills:** High fever and severe chills are very common with the flu but rare with a common cold.\n"
        "• **Body Aches & Fatigue:** Severe muscle aches, headaches, and extreme exhaustion are classic signs of the flu. A cold usually causes mild fatigue at most.\n"
        "• **Nose & Throat:** Runny/stuffy nose and sore throat are common in both, but typically more prominent in a cold."
    ),
    r"importance.*sleep|why.*sleep|benefit.*sleep": (
        "Quality sleep is a foundation of good health. It is essential because:\n"
        "• **Immune Support:** Your immune system releases cytokines during sleep, which help fight infections.\n"
        "• **Physical Healing:** Sleep triggers tissue growth and repair, cardiovascular health maintenance, and hormone regulation.\n"
        "• **Brain Health:** It helps consolidate memories, improve concentration, and regulate mood.\n"
        "• **Recommendations:** Adults should aim for 7 to 9 hours of uninterrupted sleep each night."
    ),
    r"manage.*stress|stress.*relief|reduce.*stress": (
        "To manage and reduce stress levels:\n"
        "• **Mindfulness & Meditation:** Try deep breathing exercises or guided meditation for 5-10 minutes daily.\n"
        "• **Physical Activity:** Regular exercise releases endorphins, which are natural mood lifters.\n"
        "• **Healthy Structure:** Break tasks into small steps, maintain a regular sleep pattern, and limit caffeine/alcohol.\n"
        "• **Social Connection:** Share your feelings with trusted friends, family, or a professional counselor."
    ),
    r"prevent.*heart|reduce.*risk.*heart|heart.*disease.*risk|heart.*health.*tip": (
        "To protect your cardiovascular system and reduce the risk of Heart Disease:\n"
        "• **Diet:** Follow a heart-healthy DASH or Mediterranean diet low in saturated fats and sodium.\n"
        "• **Exercise:** Aim for at least 150 minutes of moderate aerobic activity (e.g., brisk walking) per week.\n"
        "• **Smoking:** Avoid all tobacco products and limit alcohol consumption.\n"
        "• **Monitoring:** Keep blood pressure, blood glucose, and LDL cholesterol within target ranges."
    ),
    r"prevent.*kidney|kidney.*precaution|kidney.*health": (
        "To protect kidney health and prevent Chronic Kidney Disease:\n"
        "• **Blood Pressure & Sugar:** Strictly manage high blood pressure and diabetes.\n"
        "• **Hydration:** Drink sufficient water throughout the day.\n"
        "• **Medications:** Avoid unnecessary or long-term overuse of NSAID pain relievers (like ibuprofen).\n"
        "• **Diet:** Keep sodium intake moderate and maintain a balanced, nutrient-rich diet."
    )
}

# Supported diseases mapping (20 General Symptom-based + 6 Specialized Modules)
DISEASE_KEYS = {
    'influenza (flu)': 'Influenza (Flu)', 'flu': 'Influenza (Flu)', 'influenza': 'Influenza (Flu)',
    'common cold': 'Common Cold', 'cold': 'Common Cold',
    'covid-19': 'Covid-19', 'covid': 'Covid-19', 'corona': 'Covid-19',
    'diabetes': 'Diabetes',
    'hypertension': 'Hypertension', 'high blood pressure': 'Hypertension',
    'asthma': 'Asthma',
    'migraine': 'Migraine',
    'malaria': 'Malaria',
    'dengue': 'Dengue',
    'typhoid': 'Typhoid',
    'chickenpox': 'Chickenpox',
    'tuberculosis': 'Tuberculosis', 'tb': 'Tuberculosis',
    'pneumonia': 'Pneumonia',
    'gastroenteritis': 'Gastroenteritis', 'stomach flu': 'Gastroenteritis',
    'urinary tract infection (uti)': 'Urinary Tract Infection (UTI)', 'uti': 'Urinary Tract Infection (UTI)',
    'allergy': 'Allergy', 'allergies': 'Allergy',
    'gerd (acid reflux)': 'GERD (Acid Reflux)', 'gerd': 'GERD (Acid Reflux)', 'acid reflux': 'GERD (Acid Reflux)',
    'arthritis': 'Arthritis', 'joint pain disease': 'Arthritis',
    'hepatitis': 'Hepatitis',
    'jaundice': 'Jaundice',
    
    # Specialized Disease Modules
    'heart disease': 'Heart Disease', 'cardiovascular disease': 'Heart Disease', 'heart attack': 'Heart Disease',
    'chronic kidney disease': 'Chronic Kidney Disease', 'kidney disease': 'Chronic Kidney Disease', 'ckd': 'Chronic Kidney Disease',
    'breast cancer': 'Breast Cancer',
    'liver disease': 'Liver Disease', 'hepatic disease': 'Liver Disease',
    'stroke': 'Stroke', 'brain stroke': 'Stroke',
    'lung cancer': 'Lung Cancer'
}

def clean_input(text):
    """Lowercases and cleans up extra whitespaces/punctuation."""
    return re.sub(r'[^\w\s\-\(\)]', '', text.lower().strip())

def generate_chat_response(user_id, message_text):
    """
    Core response generation engine for chatbot queries.
    Returns a tuple: (response_text, is_emergency).
    """
    try:
        message_text = str(message_text).strip() if message_text else ""
        if not message_text:
            return "Please enter a message.", False

        # 1. EMERGENCY CHECK
        emergency_pattern = r"\b(chest\s*pain|difficulty\s*(in\s*)?breathing|shortness\s*of\s*breath|severe\s*bleeding|loss\s*of\s*consciousness|unconscious|passed\s*out)\b"
        if re.search(emergency_pattern, message_text.lower()):
            response_text = (
                "⚠️ **EMERGENCY WARNING:** You have described symptoms (such as chest pain, breathing difficulty, "
                "severe bleeding, or loss of consciousness) that may indicate a **critical, life-threatening medical emergency**.\n\n"
                "Please **seek immediate professional medical attention**:\n"
                "• Call your local emergency services (e.g., 911, 999, 112) immediately.\n"
                "• Go to the nearest emergency room (ER) or hospital.\n\n"
                "**Do not delay seeking help.** This AI chatbot is not an emergency response tool."
            )
            return response_text, True

        # Clean query for intent routing
        cleaned = clean_input(message_text)

        # 2. GREETINGS & INTRO
        greetings = [r"\bhello\b", r"\bhi\b", r"\bhey\b", r"\bwho\s*are\s*you\b", r"\bwhat\s*is\s*your\s*name\b", r"\bhelp\b"]
        if any(re.search(g, cleaned) for g in greetings):
            response_text = (
                "Hello! I am your AI Health Assistant for **PrediHealth**. I am here to help you understand medical conditions, "
                "suggest diets, precautions, lifestyle adjustments, recommend doctor specialties, or answer common health FAQs.\n\n"
                "How can I help you today? You can ask me:\n"
                "• *'Explain my latest prediction'* or *'Diet for my prediction'*\n"
                "• *'What are the symptoms of Diabetes?'*\n"
                "• *'Precautions for Dengue or Stroke'*\n"
                "• *'How can I reduce my risk of Heart Disease?'*\n"
                "• *'How can I boost my immune system?'*"
            )
            return response_text + MEDICAL_DISCLAIMER, False

        # 3. COMMON FAQS MATCHING
        for faq_pattern, faq_answer in FAQS.items():
            if re.search(faq_pattern, cleaned):
                return faq_answer + MEDICAL_DISCLAIMER, False

        # 4. USER'S LATEST PREDICTION CONTEXT QUERY
        prediction_context = r"\b(explain\s+my\s+(prediction|result|diagnosis|disease)|my\s+(latest|last|current)\s+(prediction|result|diagnosis)|what\s+does\s+my\s+prediction\s+mean|diet\s+for\s+my\s+prediction|precautions?\s+for\s+my\s+predicted?\s*disease|suggest\s+precautions\s+for\s+my\s+predicted\s+disease)\b|\bexplain\s+my\s+prediction\b"
        if re.search(prediction_context, cleaned):
            history = Prediction.get_history_by_user(user_id) if user_id else []
            if not history:
                response_text = (
                    "You do not have any prediction history logged in your active account yet. "
                    "Please go to the **General Prediction** or **Specialized Diagnosis** tab, check your health inputs, and generate a prediction first!"
                )
                return response_text + MEDICAL_DISCLAIMER, False

            latest = history[0]
            raw_disease = latest['predicted_disease']
            
            # Clean disease name if it contains sub-labels (e.g. "Heart Disease: Lower Risk / No Disease" -> "Heart Disease")
            disease_name = raw_disease.split(':')[0].strip() if ':' in raw_disease else raw_disease.strip()
            
            # Fallback matching if name varies slightly
            disease_details = Disease.get_by_name(disease_name)
            if not disease_details:
                for key_term, db_term in DISEASE_KEYS.items():
                    if key_term in disease_name.lower():
                        disease_details = Disease.get_by_name(db_term)
                        disease_name = db_term
                        break

            if not disease_details:
                response_text = (
                    f"Your latest logged prediction outcome was **{raw_disease}** (Confidence: {latest['confidence']*100:.1f}%).\n\n"
                    f"Please consult a qualified healthcare provider for detailed guidance regarding this prediction."
                )
                return response_text + MEDICAL_DISCLAIMER, False

            # Sub-intents for latest prediction
            if "precaution" in cleaned or "prevent" in cleaned:
                precs = "\n".join([f"• {p}" for p in disease_details['precautions']])
                response_text = f"Based on your latest prediction of **{disease_name}**, here are the recommended precautions:\n\n{precs}"
            elif "diet" in cleaned or "food" in cleaned or "eat" in cleaned:
                diets = "\n".join([f"• {d}" for d in disease_details['diet_recommendations']])
                response_text = f"For **{disease_name}**, the following diet recommendations are suggested:\n\n{diets}"
            elif "lifestyle" in cleaned or "habit" in cleaned or "change" in cleaned:
                lifestyles = "\n".join([f"• {l}" for l in disease_details['lifestyle_changes']])
                response_text = f"Managing **{disease_name}** typically involves these lifestyle modifications:\n\n{lifestyles}"
            elif "doctor" in cleaned or "specialist" in cleaned or "specialty" in cleaned:
                response_text = f"For **{disease_name}**, it is recommended to see a **{disease_details['recommended_doctor']}**."
            elif "cause" in cleaned or "why" in cleaned:
                causes = "\n".join([f"• {c}" for c in disease_details['causes']])
                response_text = f"Here are the typical causes or risk factors associated with **{disease_name}**:\n\n{causes}"
            else:
                # Default detailed explanation of prediction
                precs = "\n".join([f"• {p}" for p in disease_details['precautions']])
                diets = "\n".join([f"• {d}" for d in disease_details['diet_recommendations']])
                lifestyles = "\n".join([f"• {l}" for l in disease_details['lifestyle_changes']])
                
                response_text = (
                    f"Your latest prediction was **{disease_name}** (Confidence: {latest['confidence']*100:.1f}%).\n\n"
                    f"**Description:** {disease_details['description']}\n\n"
                    f"**Recommended Doctor:** {disease_details['recommended_doctor']}\n\n"
                    f"**Diet Recommendations:**\n{diets}\n\n"
                    f"**Lifestyle Changes:**\n{lifestyles}\n\n"
                    f"**Precautions:**\n{precs}"
                )

            return response_text + MEDICAL_DISCLAIMER, False

        # 5. SPECIFIC DISEASE QUERY MATCHING
        matched_disease_db_name = None
        for keyword, db_name in DISEASE_KEYS.items():
            # Match using word boundaries for keywords
            if re.search(r'\b' + re.escape(keyword) + r'\b', cleaned):
                matched_disease_db_name = db_name
                break

        if matched_disease_db_name:
            disease_details = Disease.get_by_name(matched_disease_db_name)
            if disease_details:
                # Sub-intents for specific disease
                if "precaution" in cleaned or "prevent" in cleaned:
                    precs = "\n".join([f"• {p}" for p in disease_details['precautions']])
                    response_text = f"Here are the precautions for **{matched_disease_db_name}**:\n\n{precs}"
                elif "diet" in cleaned or "food" in cleaned or "eat" in cleaned:
                    diets = "\n".join([f"• {d}" for d in disease_details['diet_recommendations']])
                    response_text = f"Diet recommendations for **{matched_disease_db_name}**:\n\n{diets}"
                elif "lifestyle" in cleaned or "habit" in cleaned or "change" in cleaned:
                    lifestyles = "\n".join([f"• {l}" for l in disease_details['lifestyle_changes']])
                    response_text = f"Lifestyle recommendations to manage **{matched_disease_db_name}**:\n\n{lifestyles}"
                elif "doctor" in cleaned or "specialist" in cleaned or "specialty" in cleaned:
                    response_text = f"For **{matched_disease_db_name}**, you should consult a **{disease_details['recommended_doctor']}**."
                elif "cause" in cleaned or "why" in cleaned:
                    causes = "\n".join([f"• {c}" for c in disease_details['causes']])
                    response_text = f"Typical causes and risk factors for **{matched_disease_db_name}**:\n\n{causes}"
                elif "symptom" in cleaned or "sign" in cleaned:
                    sympts = "\n".join([f"• {s.replace('_', ' ').capitalize()}" for s in disease_details['symptoms']])
                    response_text = f"Typical symptoms of **{matched_disease_db_name}** include:\n\n{sympts}"
                else:
                    # Default explanation of the specific disease
                    precs = "\n".join([f"• {p}" for p in disease_details['precautions']])
                    diets = "\n".join([f"• {d}" for d in disease_details['diet_recommendations']])
                    lifestyles = "\n".join([f"• {l}" for l in disease_details['lifestyle_changes']])
                    causes = "\n".join([f"• {c}" for c in disease_details['causes']])
                    
                    response_text = (
                        f"### **{matched_disease_db_name}**\n\n"
                        f"**Description:** {disease_details['description']}\n\n"
                        f"**Typical Causes & Risk Factors:**\n{causes}\n\n"
                        f"**Recommended Specialist:** {disease_details['recommended_doctor']}\n\n"
                        f"**Diet Recommendations:**\n{diets}\n\n"
                        f"**Lifestyle Changes:**\n{lifestyles}\n\n"
                        f"**Required Precautions:**\n{precs}"
                    )

                return response_text + MEDICAL_DISCLAIMER, False

        # 6. FALLBACK
        fallback_response = (
            "I'm sorry, I couldn't find a direct match for your specific medical question. You can ask me about:\n"
            "• Explaining your latest prediction (e.g., *'Explain my diagnosis'*, *'Diet for my prediction'*)\n"
            "• Explaining any condition (e.g., *'Symptoms of Diabetes'*, *'What is Heart Disease?'*, *'Precautions for Dengue'*, *'What is Breast Cancer?'*)\n"
            "• General health FAQs (e.g., *'How to manage stress?'*, *'How much water to drink?'*, *'What to do for fever?'*)\n\n"
            "Could you please rephrase your query?"
        )
        return fallback_response + MEDICAL_DISCLAIMER, False

    except Exception as e:
        logger.error(f"Error generating chat response: {e}", exc_info=True)
        return "Sorry, I'm temporarily unable to process your request. Please try again." + MEDICAL_DISCLAIMER, False
