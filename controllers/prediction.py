import os
import json
import joblib
import io
import logging
import pandas as pd
import numpy as np
from flask import Blueprint, request, jsonify, session, send_file
from models.prediction import Prediction
from models.disease import Disease
from models.user import User

# ReportLab imports for PDF generation
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

logger = logging.getLogger('flask.app')
predict_bp = Blueprint('predict', __name__, url_prefix='/api')

# Caching variables to avoid loading model/features from disk on every API call
_MODEL = None
_SYMPTOMS_LIST = None

def get_model_and_features():
    """Lazy loads the ML model and symptoms feature mapping and caches them in memory."""
    global _MODEL, _SYMPTOMS_LIST
    if _MODEL is None or _SYMPTOMS_LIST is None:
        logger.info("Initializing ML model and symptom features cache...")
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # Load features list
        features_path = os.path.join(base_dir, 'models', 'symptoms.json')
        if not os.path.exists(features_path):
            logger.error(f"Symptom features JSON not found at: {features_path}")
            raise FileNotFoundError("Symptoms JSON feature list is missing. Make sure to train the model first.")
        with open(features_path, 'r') as f:
            _SYMPTOMS_LIST = json.load(f)
        logger.info(f"Loaded {len(_SYMPTOMS_LIST)} symptom features definition.")
            
        # Load trained RandomForest classifier
        model_path = os.path.join(base_dir, 'models', 'disease_model.pkl')
        if not os.path.exists(model_path):
            logger.error(f"RandomForest disease model .pkl not found at: {model_path}")
            raise FileNotFoundError("Disease prediction model (.pkl) is missing. Make sure to train the model first.")
        _MODEL = joblib.load(model_path)
        logger.info("RandomForest disease model successfully deserialized and cached in-memory.")
        
    return _MODEL, _SYMPTOMS_LIST

@predict_bp.route('/predict', methods=['POST'])
def predict():
    """
    Performs machine learning inference based on provided symptoms.
    Saves the prediction to user history if logged in.
    Expects JSON: { "symptoms": ["cough", "fever", "body_ache"] }
    """
    data = request.get_json() or {}
    symptoms_input = data.get('symptoms')
    
    if not isinstance(symptoms_input, list):
        logger.warning("Predict request rejected: 'symptoms' field missing or not a JSON list.")
        return jsonify({'error': "Missing or invalid payload. 'symptoms' must be a JSON array of strings."}), 400
        
    logger.info(f"Received predict request with symptoms profile: {symptoms_input}")
    try:
        model, symptoms_features = get_model_and_features()
    except Exception as e:
        logger.error(f"ML dependencies lookup failure: {str(e)}")
        return jsonify({'error': f"Failed to initialize machine learning dependencies: {str(e)}"}), 500
        
    # Clean and filter symptoms
    cleaned_input = [str(s).strip().lower() for s in symptoms_input]
    
    # Map input symptoms into binary DataFrame conforming to training column sequence
    input_vector = pd.DataFrame(0, index=[0], columns=symptoms_features)
    valid_symptoms = []
    
    for sym in cleaned_input:
        if sym in input_vector.columns:
            input_vector.loc[0, sym] = 1
            valid_symptoms.append(sym)
            
    try:
        # Run inference
        predicted_class = model.predict(input_vector)[0]
        probabilities = model.predict_proba(input_vector)[0]
        
        # Extract class confidence level
        class_index = np.where(model.classes_ == predicted_class)[0][0]
        confidence = float(probabilities[class_index])
        logger.info(f"Classification completed: predicted='{predicted_class}', confidence={confidence:.4f}")
    except Exception as e:
        logger.error(f"Model classification failed: {str(e)}")
        return jsonify({'error': f"Model classification failed: {str(e)}"}), 500
        
    # Save search log if user session exists
    user_id = session.get('user_id')
    saved_to_db = False
    prediction_id = None
    if user_id:
        try:
            logger.info(f"Active session found (User ID: {user_id}). Storing prediction in database...")
            prediction_id = Prediction.create(
                user_id=user_id,
                symptoms=valid_symptoms,
                predicted_disease=predicted_class,
                confidence=confidence
            )
            saved_to_db = True
            logger.info(f"Prediction logged successfully. Record ID: {prediction_id}")
        except Exception as db_err:
            # Prediction logging failure should not crash inference endpoint execution.
            # Output warning internally but return successful prediction to client.
            logger.warning(f"Database logging warning: failed to write prediction record: {str(db_err)}")
            
    # Fetch detailed clinical profiles from SQLite database
    disease_details = Disease.get_by_name(predicted_class)
    if disease_details:
        logger.info(f"Seeded details retrieved for disease '{predicted_class}' from database.")
    else:
        logger.warning(f"No clinical explanation found for disease '{predicted_class}' inside SQLite.")
    
    return jsonify({
        'disease': predicted_class,
        'confidence': round(confidence, 4),
        'symptoms_analyzed': valid_symptoms,
        'saved_to_history': saved_to_db,
        'prediction_id': prediction_id,
        'disease_details': disease_details
    }), 200

@predict_bp.route('/predictions/history', methods=['GET'])
def get_history():
    """Retrieves prediction history for the currently logged-in user."""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Not authenticated. Please log in first.'}), 401
        
    try:
        history = Prediction.get_history_by_user(user_id)
        return jsonify({'history': history}), 200
    except Exception as e:
        return jsonify({'error': f"Failed to retrieve predictions history: {str(e)}"}), 500

@predict_bp.route('/symptoms', methods=['GET'])
def get_symptoms():
    """Exposes the list of symptom features used in the ML model."""
    try:
        _, symptoms = get_model_and_features()
        return jsonify({'symptoms': symptoms}), 200
    except Exception as e:
        return jsonify({'error': f"Failed to retrieve symptoms list: {str(e)}"}), 500

@predict_bp.route('/predictions/<int:prediction_id>/pdf', methods=['GET'])
def download_pdf(prediction_id):
    """
    Generates a secure, styled medical report PDF for a prediction ID.
    Only allows access to the owner of the prediction log.
    """
    user_id = session.get('user_id')
    if not user_id:
        logger.warning("PDF request rejected: unauthenticated session.")
        return jsonify({'error': 'Not authenticated.'}), 401

    logger.info(f"Generating PDF report for prediction ID: {prediction_id} (Requested by User ID: {user_id})")

    # Fetch prediction details
    pred = Prediction.get_by_id(prediction_id)
    if not pred:
        logger.warning(f"PDF generation failed: prediction ID {prediction_id} not found in DB.")
        return jsonify({'error': 'Prediction record not found.'}), 404

    # Security check: verify this prediction belongs to the current logged-in user
    if pred['user_id'] != user_id:
        logger.warning(f"Security Alert: User ID {user_id} attempted to download report ID {prediction_id} owned by User ID {pred['user_id']}.")
        return jsonify({'error': 'Unauthorized access to this report.'}), 403

    # Fetch user details
    user = User.get_by_id(user_id)
    if not user:
        logger.error(f"User profile lookup failed for User ID {user_id} during PDF generation.")
        return jsonify({'error': 'User profile not found.'}), 404

    # Fetch disease details from DB
    disease_details = Disease.get_by_name(pred['predicted_disease'])

    # Initialize report stream
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40
    )
    story = []

    # Styles setup
    styles = getSampleStyleSheet()

    # Custom color palette
    teal = colors.HexColor("#0f766e")
    slate = colors.HexColor("#1e293b")
    mint = colors.HexColor("#10b981")
    light_grey = colors.HexColor("#f8fafc")

    title_style = ParagraphStyle(
        'DocTitle', parent=styles['Normal'],
        fontName='Helvetica-Bold', fontSize=22, leading=26,
        textColor=teal, alignment=1, spaceAfter=20
    )

    h1_style = ParagraphStyle(
        'SectionHeader', parent=styles['Normal'],
        fontName='Helvetica-Bold', fontSize=13, leading=17,
        textColor=teal, spaceBefore=15, spaceAfter=8
    )

    body_style = ParagraphStyle(
        'Body', parent=styles['Normal'],
        fontName='Helvetica', fontSize=10, leading=14,
        textColor=slate, spaceAfter=6
    )

    body_bold_style = ParagraphStyle(
        'BodyBold', parent=body_style,
        fontName='Helvetica-Bold'
    )

    disclaimer_style = ParagraphStyle(
        'Disclaimer', parent=styles['Normal'],
        fontName='Helvetica-Oblique', fontSize=8, leading=11,
        textColor=colors.HexColor("#64748b"), alignment=1, spaceBefore=30
    )

    # Document Header
    story.append(Paragraph("PrediHealth Patient Assessment Report", title_style))
    story.append(Spacer(1, 8))

    # Patient Metadata Table
    meta_data = [
        [Paragraph("<b>Patient Name:</b>", body_style), Paragraph(user['username'], body_style),
         Paragraph("<b>Date of Report:</b>", body_style), Paragraph(pred['created_at'], body_style)],
        [Paragraph("<b>Patient Email:</b>", body_style), Paragraph(user['email'], body_style),
         Paragraph("<b>Report ID:</b>", body_style), Paragraph(f"#{pred['id']}", body_style)]
    ]
    t_meta = Table(meta_data, colWidths=[100, 160, 100, 160])
    t_meta.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), light_grey),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 10),
        ('RIGHTPADDING', (0,0), (-1,-1), 10),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
        ('INNERGRID', (0,0), (-1,-1), 0.25, colors.HexColor("#e2e8f0")),
    ]))
    story.append(t_meta)
    story.append(Spacer(1, 15))

    # Diagnosis Results Table
    story.append(Paragraph("Diagnostic Summary", h1_style))

    symptoms_str = ", ".join([s.replace('_', ' ').title() for s in pred['symptoms']])

    diag_data = [
        [Paragraph("<b>Likely Diagnosis</b>", body_bold_style), Paragraph("<b>Model Confidence</b>", body_bold_style)],
        [Paragraph(pred['predicted_disease'], ParagraphStyle('DiseaseCol', parent=body_style, fontName='Helvetica-Bold', fontSize=14, textColor=teal)),
         Paragraph(f"{pred['confidence'] * 100:.1f}%", ParagraphStyle('ConfCol', parent=body_style, fontName='Helvetica-Bold', fontSize=14, textColor=mint))],
        [Paragraph(f"<b>Symptoms Analyzed:</b> {symptoms_str}", body_style), ""]
    ]

    t_diag = Table(diag_data, colWidths=[260, 260])
    t_diag.setStyle(TableStyle([
        ('SPAN', (0,2), (1,2)),
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#e2e8f0")),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('LEFTPADDING', (0,0), (-1,-1), 12),
        ('BOX', (0,0), (-1,-1), 1, teal),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
    ]))
    story.append(t_diag)
    story.append(Spacer(1, 15))

    # Clinical Information
    if disease_details:
        story.append(Paragraph("Clinical Information & Details", h1_style))
        story.append(Paragraph(f"<b>Description:</b> {disease_details['description']}", body_style))
        story.append(Paragraph(f"<b>Recommended Specialist Type:</b> {disease_details['recommended_doctor']}", body_bold_style))
        story.append(Spacer(1, 8))

        # Causes and Precautions lists
        causes_para = "<br/>".join([f"&bull; {c}" for c in disease_details['causes']])
        precautions_para = "<br/>".join([f"&bull; {p}" for p in disease_details['precautions']])

        info_data = [
            [Paragraph("<b>Possible Causes</b>", body_bold_style), Paragraph("<b>Required Precautions</b>", body_bold_style)],
            [Paragraph(causes_para, body_style), Paragraph(precautions_para, body_style)]
        ]
        t_info = Table(info_data, colWidths=[260, 260])
        t_info.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), light_grey),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('BOTTOMPADDING', (0,0), (-1,-1), 8),
            ('TOPPADDING', (0,0), (-1,-1), 8),
            ('LEFTPADDING', (0,0), (-1,-1), 10),
            ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
            ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
        ]))
        story.append(t_info)

    story.append(Spacer(1, 15))

    # Medical Disclaimer
    disclaimer_text = (
        "<b>Medical Disclaimer:</b> This report is generated programmatically using a machine learning simulation "
        "trained on synthetic diagnostic datasets. It does not constitute actual medical advice, clinical diagnostics, "
        "or formal prescriptions. Always verify health concerns and conditions with a qualified physician or primary care provider."
    )
    story.append(Paragraph(disclaimer_text, disclaimer_style))

    # Build Document
    doc.build(story)

    pdf_size = buffer.tell()
    logger.info(f"PDF report successfully compiled for prediction ID {prediction_id}. Document size: {pdf_size} bytes.")

    buffer.seek(0)
    return send_file(
        buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f"PrediHealth_Report_{prediction_id}.pdf"
    )

