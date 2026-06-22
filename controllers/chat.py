import re
import logging
from flask import Blueprint, request, jsonify, session
from models.chat import ChatHistory
from models.disease import Disease
from models.prediction import Prediction

logger = logging.getLogger('flask.app')
chat_bp = Blueprint('chat', __name__, url_prefix='/api/chat')

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
    r"what.*do.*fever|have.*fever|treat.*fever": (
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
    r"difference.*cold.*flu|cold.*vs.*flu|flu.*vs.*cold": (
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
    )
}

# Supported diseases list from db.py mapping
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
    'jaundice': 'Jaundice'
}

def clean_input(text):
    """Lowercases and cleans up extra whitespaces/punctuation."""
    return re.sub(r'[^\w\s\-\(\)]', '', text.lower().strip())

@chat_bp.route('/message', methods=['POST'])
def send_message():
    """
    Receives user message. Returns the matched response.
    Saves the user query and the bot response in SQLite.
    """
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Not authenticated.'}), 401

    data = request.get_json() or {}
    message_text = data.get('message', '').strip()

    if not message_text:
        return jsonify({'error': 'Message cannot be empty.'}), 400

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
        # Save to database
        ChatHistory.create_message(user_id, 'user', message_text)
        ChatHistory.create_message(user_id, 'bot', response_text)
        
        return jsonify({
            'message': response_text,
            'is_emergency': True
        }), 200

    # Clean query for intent routing
    cleaned = clean_input(message_text)

    # 2. GREETINGS & INTRO
    greetings = [r"\bhello\b", r"\bhi\b", r"\bhey\b", r"\bwho\s*are\s*you\b", r"\bwhat\s*is\s*your\s*name\b", r"\bhelp\b"]
    if any(re.search(g, cleaned) for g in greetings):
        response_text = (
            "Hello! I am your AI Health Assistant. I am here to help you understand medical conditions, "
            "suggest diets, precautions, lifestyle adjustments, recommend doctor specialties, or answer common FAQs.\n\n"
            "How can I help you today? You can ask me:\n"
            "• *'Explain my latest prediction'* or *'Diet for my prediction'*\n"
            "• *'What are the precautions for Diabetes?'*\n"
            "• *'Diet recommendations for Dengue'*\n"
            "• *'How can I boost my immune system?'*"
        )
        # Save and return
        ChatHistory.create_message(user_id, 'user', message_text)
        ChatHistory.create_message(user_id, 'bot', response_text + MEDICAL_DISCLAIMER)
        return jsonify({
            'message': response_text + MEDICAL_DISCLAIMER,
            'is_emergency': False
        }), 200

    # 3. USER'S LATEST PREDICTION CONTEXT QUERY
    prediction_context = r"\bmy\b.*\b(prediction|result|diagnosis|disease|symptoms)\b|\b(latest|last|current)\s+prediction\b"
    if re.search(prediction_context, cleaned):
        history = Prediction.get_history_by_user(user_id)
        if not history:
            response_text = (
                "You do not have any prediction history logged in your active account yet. "
                "Please go to the **New Prediction** analyzer tab, check your symptoms, and generate a prediction first!"
            )
            ChatHistory.create_message(user_id, 'user', message_text)
            ChatHistory.create_message(user_id, 'bot', response_text + MEDICAL_DISCLAIMER)
            return jsonify({
                'message': response_text + MEDICAL_DISCLAIMER,
                'is_emergency': False
            }), 200

        latest = history[0]
        disease_name = latest['predicted_disease']
        disease_details = Disease.get_by_name(disease_name)

        if not disease_details:
            response_text = f"Your latest prediction was for **{disease_name}**, but no clinical details were found in the database."
            ChatHistory.create_message(user_id, 'user', message_text)
            ChatHistory.create_message(user_id, 'bot', response_text + MEDICAL_DISCLAIMER)
            return jsonify({
                'message': response_text + MEDICAL_DISCLAIMER,
                'is_emergency': False
            }), 200

        # Sub-intents for latest prediction
        if "precaution" in cleaned or "prevent" in cleaned:
            precs = "\n".join([f"• {p}" for p in disease_details['precautions']])
            response_text = f"Based on your latest diagnosis of **{disease_name}**, here are the recommended precautions:\n\n{precs}"
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

        ChatHistory.create_message(user_id, 'user', message_text)
        ChatHistory.create_message(user_id, 'bot', response_text + MEDICAL_DISCLAIMER)
        return jsonify({
            'message': response_text + MEDICAL_DISCLAIMER,
            'is_emergency': False
        }), 200

    # 4. COMMON FAQS MATCHING
    for faq_pattern, faq_answer in FAQS.items():
        if re.search(faq_pattern, cleaned):
            ChatHistory.create_message(user_id, 'user', message_text)
            ChatHistory.create_message(user_id, 'bot', faq_answer + MEDICAL_DISCLAIMER)
            return jsonify({
                'message': faq_answer + MEDICAL_DISCLAIMER,
                'is_emergency': False
            }), 200

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
                    f"### **{matched_disease_db_name}**\n"
                    f"**Description:** {disease_details['description']}\n\n"
                    f"**Typical Causes:**\n{causes}\n\n"
                    f"**Doctor Specialist Specialty:** {disease_details['recommended_doctor']}\n\n"
                    f"**Diet Recommendations:**\n{diets}\n\n"
                    f"**Lifestyle Changes:**\n{lifestyles}\n\n"
                    f"**Required Precautions:**\n{precs}"
                )

            ChatHistory.create_message(user_id, 'user', message_text)
            ChatHistory.create_message(user_id, 'bot', response_text + MEDICAL_DISCLAIMER)
            return jsonify({
                'message': response_text + MEDICAL_DISCLAIMER,
                'is_emergency': False
            }), 200

    # 6. FALLBACK
    fallback_response = (
        "I'm sorry, I couldn't find matches for your specific medical question. You can ask me about:\n"
        "• Explaining your latest prediction (e.g., *'Explain my diagnosis'*, *'Diet for my prediction'*)\n"
        "• Explaining a specific disease (e.g., *'Tell me about Diabetes'*, *'Precautions for Covid-19'*, *'Diet for Jaundice'*)\n"
        "• General health FAQs (e.g., *'How to manage stress?'*, *'How much water to drink?'*)\n\n"
        "Could you please rephrase your query?"
    )
    ChatHistory.create_message(user_id, 'user', message_text)
    ChatHistory.create_message(user_id, 'bot', fallback_response + MEDICAL_DISCLAIMER)
    return jsonify({
        'message': fallback_response + MEDICAL_DISCLAIMER,
        'is_emergency': False
    }), 200

@chat_bp.route('/history', methods=['GET'])
def get_chat_history():
    """Retrieves chat history for the logged-in user."""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Not authenticated.'}), 401

    try:
        history = ChatHistory.get_history_by_user(user_id)
        return jsonify({'history': history}), 200
    except Exception as e:
        return jsonify({'error': f"Failed to retrieve chat history: {str(e)}"}), 500

@chat_bp.route('/clear', methods=['POST'])
def clear_chat_history():
    """Clears all chat logs for the logged-in user."""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Not authenticated.'}), 401

    try:
        ChatHistory.clear_history(user_id)
        return jsonify({'message': 'Chat history successfully cleared.'}), 200
    except Exception as e:
        return jsonify({'error': f"Failed to clear chat history: {str(e)}"}), 500
