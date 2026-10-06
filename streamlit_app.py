import os
import json
import io
import datetime
import re
from pathlib import Path
import pandas as pd
import numpy as np
import joblib
import matplotlib.pyplot as plt
import streamlit as st

# ReportLab imports for PDF generation
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# Project relative paths
BASE_DIR = Path(__file__).resolve().parent
MODEL_PATH = BASE_DIR / 'models' / 'disease_model.pkl'
SYMPTOMS_PATH = BASE_DIR / 'models' / 'symptoms.json'
DATASET_PATH = BASE_DIR / 'data' / 'disease_symptoms.csv'
DB_PATH = BASE_DIR / 'database.db'

SPECIALIZED_DIR = BASE_DIR / 'models' / 'specialized'
SPECIALIZED_META_PATH = SPECIALIZED_DIR / 'specialized_metadata.json'

# Import internal models & helpers safely
try:
    from db import query_db, insert_db, init_db
    from models.disease import Disease
    from models.prediction import Prediction
    from models.user import User
    from models.chat import ChatHistory
    from controllers.prediction import explain_rf_prediction
    from services.chat_service import (
        FAQS, DISEASE_KEYS, clean_input, generate_chat_response, MEDICAL_DISCLAIMER as CHAT_MEDICAL_DISCLAIMER
    )
except Exception as imp_err:
    st.warning(f"Note on internal imports: {imp_err}")

# Ensure DB initialization
try:
    init_db()
except Exception:
    pass

# Helper to retrieve current authenticated user ID
def get_current_user_id():
    """Returns the authenticated user_id from session_state, or falls back to first DB user."""
    uid = st.session_state.get('user_id')
    if uid:
        return uid
    try:
        users = query_db("SELECT id FROM users LIMIT 1")
        if users:
            return users[0]['id']
    except Exception:
        pass
    return 1

# Chatbot Query Processor Helper with Intent Priority
def process_chat_query(user_text):
    """Processes user text using controllers/chat.py logic and returns (response_markdown, is_emergency)."""
    uid = st.session_state.get('user_id') or get_current_user_id()
    return generate_chat_response(uid, user_text)


# ==========================================
# PAGE CONFIGURATION & HIGH-CONTRAST STYLING
# ==========================================
st.set_page_config(
    page_title="PrediHealth — AI Multi-Disease Prediction System",
    page_icon="🩺",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Healthcare Styling & Matching Flask Chatbot Palette
st.markdown("""
<style>
    /* Main Background & Text Defaults */
    .stApp {
        background-color: #f8fafc;
        color: #0f172a;
        font-family: 'Inter', system-ui, -apple-system, sans-serif;
    }

    /* Sidebar High-Contrast Styling */
    section[data-testid="stSidebar"] {
        background-color: #ffffff !important;
        border-right: 1px solid #cbd5e1 !important;
    }
    
    section[data-testid="stSidebar"] p,
    section[data-testid="stSidebar"] span,
    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3,
    section[data-testid="stSidebar"] div,
    section[data-testid="stSidebar"] label {
        color: #0f172a !important;
    }

    section[data-testid="stSidebar"] .stRadio > label {
        font-weight: 700 !important;
        font-size: 0.95rem !important;
        color: #0f766e !important;
        margin-bottom: 0.5rem !important;
    }

    section[data-testid="stSidebar"] div[role="radiogroup"] label {
        background-color: #f1f5f9 !important;
        border: 1px solid #e2e8f0 !important;
        padding: 0.55rem 0.85rem !important;
        border-radius: 8px !important;
        margin-bottom: 0.4rem !important;
        font-weight: 600 !important;
        font-size: 0.95rem !important;
        transition: all 0.2s ease-in-out !important;
        cursor: pointer !important;
    }

    section[data-testid="stSidebar"] div[role="radiogroup"] label:hover {
        background-color: #e6fffa !important;
        border-color: #0f766e !important;
    }

    section[data-testid="stSidebar"] div[role="radiogroup"] label[aria-checked="true"] {
        background-color: #0f766e !important;
        border-color: #0f766e !important;
    }
    section[data-testid="stSidebar"] div[role="radiogroup"] label[aria-checked="true"] p,
    section[data-testid="stSidebar"] div[role="radiogroup"] label[aria-checked="true"] span {
        color: #ffffff !important;
        font-weight: 700 !important;
    }

    /* Main Header Banner */
    .main-header {
        background: linear-gradient(135deg, #0f766e 0%, #115e59 100%);
        padding: 1.75rem 2rem;
        border-radius: 12px;
        color: white;
        box-shadow: 0 4px 12px rgba(15, 118, 110, 0.15);
        margin-bottom: 1.75rem;
    }
    .main-header h1 {
        color: #ffffff !important;
        font-size: 2.1rem;
        font-weight: 700;
        margin: 0;
        padding-bottom: 0.25rem;
    }
    .main-header p {
        color: #ccfbf1 !important;
        font-size: 1.05rem;
        margin: 0;
    }

    /* Custom Metric Cards */
    .metric-card {
        background-color: #ffffff;
        border: 1px solid #cbd5e1;
        border-radius: 10px;
        padding: 1.25rem 1rem;
        text-align: center;
        box-shadow: 0 2px 4px rgba(0,0,0,0.03);
    }
    .metric-card-number {
        font-size: 2.2rem;
        font-weight: 800;
        color: #0f766e;
        line-height: 1.1;
        margin-bottom: 0.35rem;
    }
    .metric-card-label {
        font-size: 0.95rem;
        font-weight: 600;
        color: #334155;
        text-transform: uppercase;
        letter-spacing: 0.03em;
    }

    /* Card Containers */
    .health-card {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 1.25rem;
        margin-bottom: 1rem;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
    }
    .health-card-accent {
        border-left: 5px solid #0f766e;
    }

    /* Badges */
    .metric-badge {
        display: inline-block;
        background-color: #ccfbf1;
        color: #0f766e;
        font-weight: 700;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.85rem;
    }
    .badge-gold { background-color: #fef3c7; color: #92400e; }
    .badge-silver { background-color: #f1f5f9; color: #475569; }
    .badge-bronze { background-color: #ffedd5; color: #9a3412; }
    .badge-spec { background-color: #e0f2fe; color: #0369a1; }

    /* Medical Disclaimer Box */
    .disclaimer-box {
        background-color: #fef2f2;
        border: 1px solid #fecaca;
        border-left: 5px solid #ef4444;
        padding: 1rem 1.25rem;
        border-radius: 8px;
        color: #991b1b;
        font-size: 0.9rem;
        margin-top: 1.25rem;
        margin-bottom: 1.25rem;
        line-height: 1.45;
    }

    /* Chatbot Design System */
    .chat-header-bar {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
        border-radius: 12px 12px 0 0;
        padding: 1rem 1.25rem;
        color: #ffffff;
        display: flex;
        align-items: center;
        justify-content: space-between;
    }

    .chat-disclaimer-bar {
        background-color: #fffbeb;
        border-bottom: 1px solid #fef3c7;
        color: #b45309;
        font-size: 0.8rem;
        font-weight: 600;
        text-align: center;
        padding: 0.45rem 1rem;
    }

    /* User Message Bubble */
    .chat-bubble-user {
        background: linear-gradient(135deg, #0f766e 0%, #0d9488 100%);
        color: #ffffff !important;
        padding: 0.8rem 1.15rem;
        border-radius: 16px 16px 2px 16px;
        max-width: 78%;
        margin-left: auto;
        margin-bottom: 0.85rem;
        box-shadow: 0 2px 6px rgba(15, 118, 110, 0.2);
        font-size: 0.95rem;
        line-height: 1.45;
    }
    .chat-bubble-user * {
        color: #ffffff !important;
    }

    /* Assistant Message Bubble */
    .chat-bubble-assistant {
        background-color: #ffffff;
        color: #0f172a !important;
        border: 1px solid #cbd5e1;
        padding: 0.9rem 1.2rem;
        border-radius: 16px 16px 16px 2px;
        max-width: 85%;
        margin-right: auto;
        margin-bottom: 0.85rem;
        box-shadow: 0 2px 5px rgba(0,0,0,0.03);
        font-size: 0.95rem;
        line-height: 1.5;
    }

    /* Emergency Warning Bubble */
    .chat-bubble-emergency {
        background-color: #fef2f2 !important;
        color: #991b1b !important;
        border: 1.5px solid #f87171 !important;
        padding: 0.9rem 1.2rem;
        border-radius: 16px;
        max-width: 85%;
        margin-right: auto;
        margin-bottom: 0.85rem;
        box-shadow: 0 4px 12px rgba(239, 68, 68, 0.15);
    }

    /* ==========================================
       BUTTON & INPUT CONTRAST & ACCESSIBILITY FIX
       ========================================== */
    .stButton > button,
    .stDownloadButton > button,
    div[data-testid="stButton"] > button,
    div[data-testid="stDownloadButton"] > button,
    button[data-testid="baseButton-secondary"],
    button[data-testid="stBaseButton-secondary"],
    button[kind="secondary"] {
        background-color: #151923 !important;
        color: #ffffff !important;
        border: 1px solid #334155 !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        font-size: 0.95rem !important;
        padding: 0.55rem 1rem !important;
        transition: all 0.2s ease-in-out !important;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1) !important;
    }

    .stButton > button *,
    .stDownloadButton > button *,
    div[data-testid="stButton"] > button *,
    div[data-testid="stDownloadButton"] > button *,
    button[data-testid="baseButton-secondary"] *,
    button[data-testid="stBaseButton-secondary"] *,
    button[kind="secondary"] * {
        color: #ffffff !important;
        fill: #ffffff !important;
        opacity: 1 !important;
    }

    .stButton > button:hover,
    .stDownloadButton > button:hover,
    div[data-testid="stButton"] > button:hover,
    div[data-testid="stDownloadButton"] > button:hover,
    button[data-testid="baseButton-secondary"]:hover,
    button[data-testid="stBaseButton-secondary"]:hover,
    button[kind="secondary"]:hover {
        background-color: #0f766e !important;
        color: #ffffff !important;
        border-color: #0f766e !important;
        box-shadow: 0 4px 10px rgba(15, 118, 110, 0.3) !important;
    }

    .stButton > button[kind="primary"],
    div[data-testid="stButton"] > button[kind="primary"],
    button[data-testid="baseButton-primary"],
    button[data-testid="stBaseButton-primary"] {
        background: linear-gradient(135deg, #0f766e 0%, #0d9488 100%) !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 8px !important;
        font-weight: 700 !important;
        font-size: 1rem !important;
        padding: 0.65rem 1.2rem !important;
        box-shadow: 0 4px 10px rgba(15, 118, 110, 0.25) !important;
        transition: all 0.2s ease-in-out !important;
    }

    .stButton > button[kind="primary"] *,
    div[data-testid="stButton"] > button[kind="primary"] * {
        color: #ffffff !important;
        fill: #ffffff !important;
    }

    /* ==========================================
       SELECTBOX & INPUT CONTRAST FIX
       ========================================== */

    /* 1. Labels for all Streamlit controls */
    .stTextInput label,
    .stNumberInput label,
    .stSelectbox label,
    .stMultiSelect label,
    .stSlider label,
    .stRadio label {
        color: #0f172a !important;
        font-weight: 600 !important;
        font-size: 0.9rem !important;
    }

    /* 2. Selectbox Container & Input Box (Closed State) */
    div[data-testid="stSelectbox"] div[data-baseweb="select"],
    div[data-testid="stSelectbox"] div[data-baseweb="select"] > div,
    div[data-baseweb="select"],
    div[data-baseweb="select"] > div {
        background-color: #ffffff !important;
        color: #0f172a !important;
        border: 1px solid #cbd5e1 !important;
        border-radius: 8px !important;
    }

    /* Target all child text elements, values, spans, and SVG icons inside selectbox */
    div[data-baseweb="select"] div,
    div[data-baseweb="select"] span,
    div[data-baseweb="select"] p,
    div[data-baseweb="select"] input,
    div[data-baseweb="select"] [role="button"] {
        color: #0f172a !important;
        -webkit-text-fill-color: #0f172a !important;
        font-weight: 500 !important;
    }

    /* Selectbox Arrow Icon */
    div[data-baseweb="select"] svg {
        fill: #0f172a !important;
        color: #0f172a !important;
    }

    /* 3. Selectbox Opened Dropdown Popover Menu */
    div[data-baseweb="popover"],
    div[data-baseweb="menu"],
    ul[data-baseweb="menu"],
    ul[role="listbox"] {
        background-color: #ffffff !important;
        border: 1px solid #cbd5e1 !important;
        border-radius: 8px !important;
        box-shadow: 0 4px 14px rgba(0, 0, 0, 0.12) !important;
    }

    div[data-baseweb="popover"] li,
    div[data-baseweb="menu"] li,
    ul[data-baseweb="menu"] li,
    ul[role="listbox"] li,
    div[data-baseweb="popover"] [role="option"],
    ul[role="listbox"] [role="option"] {
        background-color: #ffffff !important;
        color: #0f172a !important;
    }

    div[data-baseweb="popover"] li *,
    div[data-baseweb="menu"] li *,
    ul[data-baseweb="menu"] li *,
    ul[role="listbox"] li *,
    div[data-baseweb="popover"] [role="option"] *,
    ul[role="listbox"] [role="option"] * {
        color: #0f172a !important;
    }

    /* Opened Dropdown Option Item Hover & Focus States */
    li[role="option"]:hover,
    li[role="option"][aria-selected="true"],
    div[role="option"]:hover,
    div[role="option"][aria-selected="true"],
    ul[role="listbox"] li:hover {
        background-color: #ccfbf1 !important;
        color: #0f766e !important;
    }

    li[role="option"]:hover *,
    li[role="option"][aria-selected="true"] *,
    div[role="option"]:hover *,
    div[role="option"][aria-selected="true"] * {
        color: #0f766e !important;
        font-weight: 600 !important;
    }

    /* 4. Number Input & Text Input Controls */
    div[data-baseweb="input"],
    div[data-baseweb="base-input"],
    .stTextInput input,
    .stNumberInput input,
    .stTextArea textarea {
        background-color: #ffffff !important;
        color: #0f172a !important;
        border: 1px solid #cbd5e1 !important;
        border-radius: 8px !important;
    }

    div[data-baseweb="input"] input,
    .stTextInput input,
    .stNumberInput input {
        background-color: #ffffff !important;
        color: #0f172a !important;
        -webkit-text-fill-color: #0f172a !important;
        font-weight: 500 !important;
    }

    /* Number Input Step Increment/Decrement Buttons */
    div[data-testid="stNumberInput"] button {
        background-color: #f1f5f9 !important;
        color: #0f172a !important;
        border: 1px solid #cbd5e1 !important;
    }
    div[data-testid="stNumberInput"] button * {
        color: #0f172a !important;
        fill: #0f172a !important;
    }
    div[data-testid="stNumberInput"] button:hover {
        background-color: #e2e8f0 !important;
    }

    /* 5. Input Placeholders */
    input::placeholder,
    textarea::placeholder,
    .stTextInput input::placeholder,
    .stNumberInput input::placeholder {
        color: #64748b !important;
        -webkit-text-fill-color: #64748b !important;
        opacity: 1 !important;
    }
</style>
""", unsafe_allow_html=True)


# ==========================================
# RESOURCE CACHING HELPERS
# ==========================================
@st.cache_resource
def load_ml_model_and_features():
    """Loads the trained RandomForest 20-disease model and symptoms definition."""
    if not MODEL_PATH.exists():
        return None, None, f"Model file missing at '{MODEL_PATH}'. Please train model first."
    if not SYMPTOMS_PATH.exists():
        return None, None, f"Symptoms definition missing at '{SYMPTOMS_PATH}'."
    
    try:
        model = joblib.load(MODEL_PATH)
        with open(SYMPTOMS_PATH, 'r') as f:
            symptoms = json.load(f)
        return model, symptoms, None
    except Exception as e:
        return None, None, f"Error loading ML artifacts: {str(e)}"

@st.cache_resource
def load_specialized_models_and_meta():
    """Loads specialized metadata and serialized model pipelines for 6 specialized diseases."""
    if not SPECIALIZED_META_PATH.exists():
        return {}, {}, f"Specialized metadata missing at '{SPECIALIZED_META_PATH}'."
    
    try:
        with open(SPECIALIZED_META_PATH, 'r') as f:
            meta = json.load(f)
        
        models = {}
        for key, info in meta.items():
            m_path = SPECIALIZED_DIR / info['model_file']
            if m_path.exists():
                models[key] = joblib.load(m_path)
            else:
                models[key] = None
        return meta, models, None
    except Exception as e:
        return {}, {}, f"Error loading specialized models: {str(e)}"

@st.cache_data
def load_dataset():
    """Loads the symptoms dataset CSV."""
    if not DATASET_PATH.exists():
        return None, f"Dataset CSV missing at '{DATASET_PATH}'."
    try:
        df = pd.read_csv(DATASET_PATH)
        return df, None
    except Exception as e:
        return None, f"Error reading dataset: {str(e)}"

# Load cached resources
model, symptoms_list, model_error = load_ml_model_and_features()
specialized_meta, specialized_models, specialized_error = load_specialized_models_and_meta()
dataset_df, dataset_error = load_dataset()


# ==========================================
# GENERAL UTILITY FUNCTIONS
# ==========================================
def format_symptom_name(sym):
    """Converts symptom snake_case to Title Case."""
    return sym.replace('_', ' ').title()

def generate_pdf_report(prediction_data, disease_details=None, is_specialized=False):
    """Generates an in-memory ReportLab PDF for download in Streamlit (supports General & Specialized)."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40
    )
    story = []
    styles = getSampleStyleSheet()

    teal = colors.HexColor("#0f766e")
    slate = colors.HexColor("#1e293b")
    mint = colors.HexColor("#10b981")
    light_grey = colors.HexColor("#f8fafc")

    title_style = ParagraphStyle(
        'DocTitle', parent=styles['Normal'],
        fontName='Helvetica-Bold', fontSize=20, leading=24,
        textColor=teal, alignment=1, spaceAfter=15
    )

    h1_style = ParagraphStyle(
        'SectionHeader', parent=styles['Normal'],
        fontName='Helvetica-Bold', fontSize=12, leading=16,
        textColor=teal, spaceBefore=12, spaceAfter=6
    )

    body_style = ParagraphStyle(
        'Body', parent=styles['Normal'],
        fontName='Helvetica', fontSize=9.5, leading=13.5,
        textColor=slate, spaceAfter=5
    )

    body_bold_style = ParagraphStyle('BodyBold', parent=body_style, fontName='Helvetica-Bold')

    disclaimer_style = ParagraphStyle(
        'Disclaimer', parent=styles['Normal'],
        fontName='Helvetica-Oblique', fontSize=8, leading=11,
        textColor=colors.HexColor("#64748b"), alignment=1, spaceBefore=20
    )

    report_title = "PrediHealth Specialized Clinical Report" if is_specialized else "PrediHealth Patient Assessment Report"
    story.append(Paragraph(report_title, title_style))
    story.append(Spacer(1, 6))

    # Meta Table
    module_text = f"Specialized Module: {prediction_data.get('disease_name', 'Specialized Disease')}" if is_specialized else "General Symptom Module"
    meta_data = [
        [Paragraph("<b>Module:</b>", body_style), Paragraph(module_text, body_style),
         Paragraph("<b>Date:</b>", body_style), Paragraph(datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), body_style)]
    ]
    t_meta = Table(meta_data, colWidths=[90, 170, 70, 190])
    t_meta.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), light_grey),
        ('PADDING', (0,0), (-1,-1), 6),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
    ]))
    story.append(t_meta)
    story.append(Spacer(1, 12))

    # Diagnosis Summary
    story.append(Paragraph("Diagnostic Summary", h1_style))
    
    if is_specialized:
        input_summary = prediction_data.get('inputs_summary', 'Parameters evaluated')
        model_name = prediction_data.get('model_used', 'Trained ML Model')
        diag_data = [
            [Paragraph("<b>Predicted Result / Class</b>", body_bold_style), Paragraph("<b>Model Probability</b>", body_bold_style)],
            [Paragraph(prediction_data['disease'], ParagraphStyle('DisCol', parent=body_style, fontName='Helvetica-Bold', fontSize=13, textColor=teal)),
             Paragraph(f"{prediction_data['confidence'] * 100:.1f}%", ParagraphStyle('ConfCol', parent=body_style, fontName='Helvetica-Bold', fontSize=13, textColor=mint))],
            [Paragraph(f"<b>Algorithm:</b> {model_name} | <b>Inputs Summary:</b> {input_summary}", body_style), ""]
        ]
    else:
        symptoms_str = ", ".join([format_symptom_name(s) for s in prediction_data.get('symptoms', [])])
        diag_data = [
            [Paragraph("<b>Likely Predicted Disease Class</b>", body_bold_style), Paragraph("<b>Model Confidence</b>", body_bold_style)],
            [Paragraph(prediction_data['disease'], ParagraphStyle('DisCol', parent=body_style, fontName='Helvetica-Bold', fontSize=13, textColor=teal)),
             Paragraph(f"{prediction_data['confidence'] * 100:.1f}%", ParagraphStyle('ConfCol', parent=body_style, fontName='Helvetica-Bold', fontSize=13, textColor=mint))],
            [Paragraph(f"<b>Symptoms Analyzed:</b> {symptoms_str}", body_style), ""]
        ]

    t_diag = Table(diag_data, colWidths=[260, 260])
    t_diag.setStyle(TableStyle([
        ('SPAN', (0,2), (1,2)),
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#e2e8f0")),
        ('PADDING', (0,0), (-1,-1), 8),
        ('BOX', (0,0), (-1,-1), 1, teal),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
    ]))
    story.append(t_diag)
    story.append(Spacer(1, 12))

    # Clinical Info if available
    if disease_details:
        story.append(Paragraph("Clinical Information", h1_style))
        story.append(Paragraph(f"<b>Description:</b> {disease_details.get('description', 'N/A')}", body_style))
        if 'recommended_doctor' in disease_details:
            story.append(Paragraph(f"<b>Recommended Specialist:</b> {disease_details['recommended_doctor']}", body_bold_style))
        story.append(Spacer(1, 6))

        if 'causes' in disease_details or 'precautions' in disease_details:
            causes_p = "<br/>".join([f"&bull; {c}" for c in disease_details.get('causes', [])])
            precs_p = "<br/>".join([f"&bull; {p}" for p in disease_details.get('precautions', [])])

            info_data = [
                [Paragraph("<b>Possible Causes / Factors</b>", body_bold_style), Paragraph("<b>Required Precautions</b>", body_bold_style)],
                [Paragraph(causes_p if causes_p else "Standard clinical factors", body_style),
                 Paragraph(precs_p if precs_p else "Consult a physician", body_style)]
            ]
            t_info = Table(info_data, colWidths=[260, 260])
            t_info.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), light_grey),
                ('VALIGN', (0,0), (-1,-1), 'TOP'),
                ('PADDING', (0,0), (-1,-1), 8),
                ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
                ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
            ]))
            story.append(t_info)

    story.append(Spacer(1, 15))
    disclaimer_text = (
        "<b>Medical Disclaimer:</b> This report is generated programmatically using a machine learning model "
        "for educational and research demonstration purposes only. It is not a medical diagnosis or treatment plan. "
        "Always consult a qualified healthcare professional for medical concerns."
    )
    story.append(Paragraph(disclaimer_text, disclaimer_style))

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()


# ==========================================
# AUTHENTICATION & SESSION STATE MANAGEMENT
# ==========================================
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "user_id" not in st.session_state:
    st.session_state.user_id = None
if "username" not in st.session_state:
    st.session_state.username = ""
if "email" not in st.session_state:
    st.session_state.email = ""
if "auth_mode" not in st.session_state:
    st.session_state.auth_mode = "login"

def render_auth_page():
    """Renders PrediHealth Authentication interface (Login / Registration)."""
    st.markdown("""
    <div style="max-width: 520px; margin: 1.5rem auto 1rem auto; text-align: center;">
        <div style="font-size: 3.5rem; line-height: 1;">🩺</div>
        <h1 style="color: #0f766e; font-weight: 800; margin-bottom: 0.2rem; font-size: 2.3rem;">PrediHealth</h1>
        <p style="color: #475569; font-weight: 600; font-size: 1.05rem;">
            AI-Powered Multi-Disease Prediction System
        </p>
    </div>
    """, unsafe_allow_html=True)

    _, col_card, _ = st.columns([1, 2.2, 1])
    with col_card:
        if st.session_state.auth_mode == "login":
            st.markdown("""
            <div class="health-card" style="border-top: 5px solid #0f766e; padding: 1.75rem 1.5rem 1rem 1.5rem; margin-bottom: 1rem;">
                <h3 style="color: #0f172a; font-weight: 700; margin-bottom: 0.3rem; text-align: center;">Welcome Back</h3>
                <p style="color: #64748b; font-size: 0.9rem; text-align: center; margin-bottom: 1.25rem;">
                    Sign in to access your predictions, symptom analytics, and specialized disease diagnostic modules.
                </p>
            </div>
            """, unsafe_allow_html=True)

            with st.form(key="login_form"):
                username_input = st.text_input("Username or Email Address", key="login_user", placeholder="Enter username or email")
                password_input = st.text_input("Password", type="password", key="login_pass", placeholder="••••••••")
                submit_login = st.form_submit_button("🔐 Sign In", use_container_width=True, type="primary")

                if submit_login:
                    u_clean = username_input.strip()
                    p_clean = password_input or ""

                    if not u_clean or not p_clean:
                        st.error("Please enter both username/email and password.")
                    else:
                        user = User.get_by_username(u_clean)
                        if not user:
                            user = User.get_by_email(u_clean.lower())

                        if user and User.verify_password(user['password_hash'], p_clean):
                            st.session_state.authenticated = True
                            st.session_state.user_id = user['id']
                            st.session_state.username = user['username']
                            st.session_state.email = user['email']
                            st.success("Login successful! Redirecting...")
                            st.rerun()
                        else:
                            st.error("Invalid username/email or password.")

            st.markdown("<div style='text-align: center; margin-top: 0.75rem;'>", unsafe_allow_html=True)
            if st.button("Don't have an account? Create Account", use_container_width=True):
                st.session_state.auth_mode = "register"
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

        else:
            st.markdown("""
            <div class="health-card" style="border-top: 5px solid #0f766e; padding: 1.75rem 1.5rem 1rem 1.5rem; margin-bottom: 1rem;">
                <h3 style="color: #0f172a; font-weight: 700; margin-bottom: 0.3rem; text-align: center;">Create Account</h3>
                <p style="color: #64748b; font-size: 0.9rem; text-align: center; margin-bottom: 1.25rem;">
                    Sign up to analyze symptoms, track diagnoses, and save history records.
                </p>
            </div>
            """, unsafe_allow_html=True)

            with st.form(key="register_form"):
                reg_username = st.text_input("Username (min 3 chars)", key="reg_user", placeholder="e.g. johndoe")
                reg_email = st.text_input("Email Address", key="reg_email", placeholder="name@example.com")
                reg_pass = st.text_input("Password (min 6 chars)", type="password", key="reg_pass", placeholder="••••••••")
                reg_confirm = st.text_input("Confirm Password", type="password", key="reg_conf", placeholder="Repeat password")

                submit_reg = st.form_submit_button("📝 Create Account", use_container_width=True, type="primary")

                if submit_reg:
                    u_val = reg_username.strip()
                    e_val = reg_email.strip().lower()
                    p_val = reg_pass or ""
                    c_val = reg_confirm or ""

                    if not u_val or not e_val or not p_val or not c_val:
                        st.error("All registration fields are required.")
                    elif len(u_val) < 3:
                        st.error("Username must be at least 3 characters long.")
                    elif not re.match(r"^[\w\.-]+@[\w\.-]+\.\w+$", e_val):
                        st.error("Please enter a valid email address.")
                    elif len(p_val) < 6:
                        st.error("Password must be at least 6 characters long.")
                    elif p_val != c_val:
                        st.error("Passwords do not match.")
                    else:
                        if User.get_by_username(u_val):
                            st.error("Username is already taken. Please choose another.")
                        elif User.get_by_email(e_val):
                            st.error("Email is already registered. Please sign in or use another email.")
                        else:
                            try:
                                uid = User.create(u_val, e_val, p_val)
                                st.success("Account created successfully! Please sign in.")
                                st.session_state.auth_mode = "login"
                                st.rerun()
                            except Exception as reg_err:
                                st.error(f"Registration failed: {reg_err}")

            st.markdown("<div style='text-align: center; margin-top: 0.75rem;'>", unsafe_allow_html=True)
            if st.button("Already have an account? Sign in here", use_container_width=True):
                st.session_state.auth_mode = "login"
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

# Guard clause: Stop script execution if unauthenticated
if not st.session_state.authenticated:
    render_auth_page()
    st.stop()


# ==========================================
# SIDEBAR NAVIGATION (PROTECTED ROUTE VIEW)
# ==========================================
with st.sidebar:
    st.markdown("""
    <div style="padding-bottom: 0.5rem;">
        <h2 style="color: #0f766e !important; margin: 0; font-size: 1.6rem; font-weight: 800;">🩺 PrediHealth</h2>
        <p style="color: #475569 !important; font-size: 0.85rem; font-weight: 600; margin-top: 0.2rem;">AI Multi-Disease Platform</p>
    </div>
    """, unsafe_allow_html=True)
    st.divider()

    # Logged-in User Profile Badge
    uname_disp = st.session_state.get('username', 'User')
    uemail_disp = st.session_state.get('email', '')
    st.markdown(f"""
    <div style="background-color: #f1f5f9; border: 1px solid #cbd5e1; border-radius: 8px; padding: 0.65rem 0.85rem; margin-bottom: 1rem;">
        <div style="font-size: 0.75rem; color: #64748b; font-weight: 700; letter-spacing: 0.04em;">SIGNED IN AS</div>
        <div style="font-size: 0.95rem; color: #0f766e; font-weight: 700; margin-top: 0.1rem;">👤 {uname_disp}</div>
        <div style="font-size: 0.8rem; color: #475569; overflow: hidden; text-overflow: ellipsis;">{uemail_disp}</div>
    </div>
    """, unsafe_allow_html=True)

    nav_choice = st.radio(
        "NAVIGATION MENU",
        options=[
            "🏠 Dashboard",
            "🩺 Symptom Prediction",
            "🔬 Specialized Diagnosis",
            "📊 Model Analytics",
            "📜 Prediction History",
            "💬 Health Assistant",
            "ℹ️ About Project"
        ],
        index=0
    )

    st.divider()

    if st.button("🚪 Logout", use_container_width=True):
        st.session_state.authenticated = False
        st.session_state.user_id = None
        st.session_state.username = ""
        st.session_state.email = ""
        st.rerun()

    st.markdown("""
    <div style="font-size: 0.8rem; color: #475569 !important; line-height: 1.4; margin-top: 0.5rem;">
        <strong style="color: #0f766e !important;">PrediHealth Multi-Disease System</strong><br/>
        26 Total Disease Modules<br/>
        • 20 General Symptom Diseases<br/>
        • 6 Specialized Clinical Models
    </div>
    """, unsafe_allow_html=True)


# ==========================================
# PAGE 1: DASHBOARD
# ==========================================
if nav_choice == "🏠 Dashboard":
    st.markdown("""
    <div class="main-header">
        <h1>PrediHealth Dashboard</h1>
        <p>Streamlit-Based Multi-Disease Prediction System for Early Disease Detection Using Machine Learning</p>
    </div>
    """, unsafe_allow_html=True)

    # Dynamic metrics calculation from models and datasets
    n_general_diseases = len(model.classes_) if model is not None else 20
    n_specialized_diseases = len(specialized_meta) if specialized_meta else 6
    n_total_diseases = n_general_diseases + n_specialized_diseases
    n_symptoms = len(symptoms_list) if symptoms_list is not None else 42

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-card-number">{n_total_diseases}</div>
            <div class="metric-card-label">Total Disease Modules</div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-card-number">{n_general_diseases}</div>
            <div class="metric-card-label">General Diseases (Symptom-Based)</div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-card-number">{n_specialized_diseases}</div>
            <div class="metric-card-label">Specialized Diseases</div>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-card-number">{n_symptoms}</div>
            <div class="metric-card-label">General Symptoms</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br/>", unsafe_allow_html=True)

    # Two-Level Architecture Cards
    st.markdown("### 🧬 Dual Diagnostic Architecture")
    c_arch1, c_arch2 = st.columns(2)

    with c_arch1:
        st.markdown("""
        <div class="health-card health-card-accent">
            <div style="display: flex; align-items: center; justify-content: space-between;">
                <h3 style="color: #0f766e; margin: 0;">🩺 General Symptom-Based Prediction</h3>
                <span class="metric-badge">20 Diseases</span>
            </div>
            <p style="color: #475569; font-size: 0.95rem; margin-top: 0.6rem;">
                Evaluates user-selected symptoms across 42 general clinical features using the trained <strong>Random Forest Model</strong> (<code>models/disease_model.pkl</code>).
            </p>
            <ul style="color: #334155; font-size: 0.88rem; padding-left: 1.2rem;">
                <li>Multi-symptom pattern matching</li>
                <li>Top-3 probabilities & model confidence</li>
                <li>Explainable AI (XAI) feature contribution analysis</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

    with c_arch2:
        st.markdown("""
        <div class="health-card" style="border-left: 5px solid #0369a1;">
            <div style="display: flex; align-items: center; justify-content: space-between;">
                <h3 style="color: #0369a1; margin: 0;">🔬 Specialized Disease Diagnosis</h3>
                <span class="metric-badge badge-spec">6 Diseases</span>
            </div>
            <p style="color: #475569; font-size: 0.95rem; margin-top: 0.6rem;">
                Dedicated clinical diagnostic modules trained on specialized public datasets, benchmarked across 5 ML algorithms (Random Forest, XGBoost, Decision Tree, KNN, Gradient Boosting).
            </p>
            <ul style="color: #334155; font-size: 0.88rem; padding-left: 1.2rem;">
                <li>❤️ Heart Disease | 🫘 Chronic Kidney Disease | 🎗️ Breast Cancer</li>
                <li>🫀 Liver Disease | 🧠 Stroke | 🫁 Lung Cancer</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    col_left, col_right = st.columns([3, 2])
    with col_left:
        st.markdown("### 📋 Supported Disease Modules")
        st.write("""
        **General Symptom Module (20 Diseases):**
        Fungal Infection, Allergy, GERD, Chronic Cholestasis, Drug Reaction, Peptic Ulcer Disease, AIDS, Diabetes, Gastroenteritis, Bronchial Asthma, Hypertension, Migraine, Cervical Spondylosis, Paralysis (Brain Hemorrhage), Jaundice, Malaria, Chicken Pox, Dengue, Typhoid, Hepatitis A.

        **Specialized Diagnostic Module (6 Diseases):**
        - ❤️ **Heart Disease**: Cleveland Dataset (13 clinical parameters)
        - 🫘 **Chronic Kidney Disease**: UCI CKD Dataset (24 parameters)
        - 🎗️ **Breast Cancer**: Wisconsin Diagnostic FNA Dataset (30 parameters)
        - 🫀 **Liver Disease**: Indian Liver Patient Dataset (10 parameters)
        - 🧠 **Stroke**: Healthcare Stroke Dataset (10 parameters)
        - 🫁 **Lung Cancer**: Survey Lung Cancer Dataset (15 parameters)
        """)

    with col_right:
        st.markdown("### 🏆 Specialized Models Benchmark Summary")
        if specialized_meta:
            for s_key, s_info in specialized_meta.items():
                st.markdown(f"""
                <div style="padding: 0.5rem 0.8rem; background: #ffffff; border: 1px solid #cbd5e1; border-radius: 8px; margin-bottom: 0.4rem;">
                    <strong>{s_info['display_name']}</strong> — Best: <span style="color: #0f766e; font-weight: 700;">{s_info['selected_algorithm']}</span> 
                    (F1: <strong style="color: #10b981;">{s_info['best_f1_score']*100:.1f}%</strong>)
                </div>
                """, unsafe_allow_html=True)

    # Medical Disclaimer Callout
    st.markdown("""
    <div class="disclaimer-box">
        <strong>⚠️ Medical Disclaimer:</strong><br/>
        This system is intended for educational and demonstration purposes only. 
        Predictions are generated by machine learning models and should not be considered a medical diagnosis. 
        Please consult a qualified healthcare professional for medical concerns.
    </div>
    """, unsafe_allow_html=True)


# ==========================================
# PAGE 2: SYMPTOM PREDICTION (GENERAL MODEL)
# ==========================================
elif nav_choice == "🩺 Symptom Prediction":
    st.markdown("""
    <div class="main-header">
        <h1>Symptom Analyzer & Disease Prediction</h1>
        <p>Select symptoms to run machine learning classification using the trained Random Forest 20-disease model</p>
    </div>
    """, unsafe_allow_html=True)

    if model_error:
        st.error(f"Cannot initialize prediction engine: {model_error}")
        st.stop()

    # Symptom formatting map
    symptom_map = {format_symptom_name(sym): sym for sym in symptoms_list}
    formatted_options = sorted(list(symptom_map.keys()))

    # Session State management for symptoms selection & prediction results
    if 'selected_formatted_symptoms' not in st.session_state:
        st.session_state.selected_formatted_symptoms = []
    if 'latest_prediction' not in st.session_state:
        st.session_state.latest_prediction = None

    st.markdown("### 🩺 Select Symptoms")

    c_select, c_actions = st.columns([3, 1])
    with c_select:
        selected_formatted = st.multiselect(
            "Search and select symptoms:",
            options=formatted_options,
            default=st.session_state.selected_formatted_symptoms,
            help="Search symptoms by typing (e.g. Fever, Headache, Cough)"
        )
        st.session_state.selected_formatted_symptoms = selected_formatted

    with c_actions:
        st.markdown("<br/>", unsafe_allow_html=True)
        if st.button("❌ Clear Selection", use_container_width=True):
            st.session_state.selected_formatted_symptoms = []
            st.session_state.latest_prediction = None
            st.rerun()

        analyze_btn = st.button("🔍 Analyze Symptoms", type="primary", use_container_width=True)

    # Convert selected formatted names back to raw snake_case symptoms
    selected_raw_symptoms = [symptom_map[fmt] for fmt in selected_formatted]
    st.info(f"**Selected Symptoms:** `{len(selected_raw_symptoms)}` symptom(s)")

    # Execute Prediction Logic
    if analyze_btn:
        if not selected_raw_symptoms:
            st.warning("Please select at least one symptom before analyzing.")
        else:
            with st.spinner("Running Random Forest prediction model..."):
                input_vector = pd.DataFrame(0, index=[0], columns=symptoms_list)
                for sym in selected_raw_symptoms:
                    if sym in input_vector.columns:
                        input_vector.loc[0, sym] = 1

                predicted_class = model.predict(input_vector)[0]
                probabilities = model.predict_proba(input_vector)[0]

                top_indices = np.argsort(probabilities)[::-1][:3]
                top_3 = []
                for idx in top_indices:
                    top_3.append({
                        'disease': model.classes_[idx],
                        'probability': float(probabilities[idx])
                    })

                main_confidence = top_3[0]['probability']

                try:
                    xai_data = explain_rf_prediction(model, input_vector, predicted_class, symptoms_list)
                except Exception:
                    xai_data = None

                disease_details = None
                try:
                    disease_details = Disease.get_by_name(predicted_class)
                except Exception:
                    pass

                saved_id = None
                try:
                    uid = st.session_state.get('user_id') or get_current_user_id()
                    saved_id = Prediction.create(
                        user_id=uid,
                        symptoms=selected_raw_symptoms,
                        predicted_disease=predicted_class,
                        confidence=main_confidence,
                        prediction_type='General'
                    )
                except Exception as db_err:
                    pass

                st.session_state.latest_prediction = {
                    'symptoms': selected_raw_symptoms,
                    'disease': predicted_class,
                    'confidence': main_confidence,
                    'top_3': top_3,
                    'xai_data': xai_data,
                    'details': disease_details,
                    'saved_id': saved_id
                }

    # Render Prediction Output if present
    pred_res = st.session_state.latest_prediction
    if pred_res:
        st.markdown("---")
        st.markdown("## 📊 Prediction Results")

        res_col1, res_col2 = st.columns([1, 1])

        with res_col1:
            st.markdown(f"""
            <div class="health-card health-card-accent">
                <span class="metric-badge">Primary Prediction</span>
                <p style="color: #64748b; font-size: 0.85rem; margin-top: 0.4rem; margin-bottom: 0.2rem;">
                    Most likely predicted disease class according to the model:
                </p>
                <h2 style="color: #0f766e; margin-top: 0.2rem; margin-bottom: 0.3rem;">{pred_res['disease']}</h2>
                <h4 style="color: #10b981; margin: 0;">Prediction Confidence: {pred_res['confidence'] * 100:.1f}%</h4>
                <p style="color: #94a3b8; font-size: 0.8rem; margin-top: 0.4rem; margin-bottom: 0;">
                    Probability derived from <code>model.predict_proba()</code>
                </p>
            </div>
            """, unsafe_allow_html=True)

        with res_col2:
            st.markdown("### 🏆 Top 3 Predictions")
            badges = [
                ('<span class="metric-badge badge-gold">1. Most Likely</span>', pred_res['top_3'][0]),
                ('<span class="metric-badge badge-silver">2. Second</span>', pred_res['top_3'][1] if len(pred_res['top_3']) > 1 else None),
                ('<span class="metric-badge badge-bronze">3. Third</span>', pred_res['top_3'][2] if len(pred_res['top_3']) > 2 else None)
            ]

            for badge_html, item in badges:
                if item:
                    st.markdown(f"""
                    <div style="display: flex; justify-content: space-between; align-items: center; padding: 0.55rem 0.85rem; background: white; border: 1px solid #cbd5e1; border-radius: 8px; margin-bottom: 0.5rem;">
                        <div>{badge_html} <strong style="margin-left: 0.5rem;">{item['disease']}</strong></div>
                        <div style="font-weight: 800; color: #0f766e;">{item['probability'] * 100:.1f}%</div>
                    </div>
                    """, unsafe_allow_html=True)

        # Download PDF Report Button
        st.markdown("#### 📄 Download Prediction Report")
        pdf_bytes = generate_pdf_report(pred_res, pred_res['details'], is_specialized=False)
        st.download_button(
            label="📄 Download Prediction Report (PDF)",
            data=pdf_bytes,
            file_name=f"PrediHealth_Report_{pred_res['disease'].replace(' ', '_')}.pdf",
            mime="application/pdf"
        )

        st.markdown("---")

        # EXPLAINABLE AI (XAI) SECTION
        st.markdown("### 🔎 Prediction Explanation")
        if pred_res['xai_data']:
            xai = pred_res['xai_data']

            st.markdown(f"**Clinical Pattern Matching:** {xai['reasoning']}")
            st.markdown(f"**Confidence Rationale:** {xai['confidence_explanation']}")

            tab_xai1, tab_xai2 = st.tabs(["Patient Symptom Contributions", "Random Forest Model Feature Importance"])

            with tab_xai1:
                pos_contribs = [x for x in xai['local_contributions'] if x['present'] == 1]
                pos_contribs.sort(key=lambda x: x['contribution'], reverse=True)

                if pos_contribs:
                    st.write("Selected symptoms contributing positively to this prediction:")
                    contrib_df = pd.DataFrame([
                        {
                            'Selected Symptom': format_symptom_name(x['symptom']),
                            'Decision Path Contribution Weight': f"{x['contribution']:.4f}"
                        } for x in pos_contribs
                    ])
                    st.table(contrib_df)
                else:
                    st.info("The combination of selected symptoms matches the clinical profile distribution.")

            with tab_xai2:
                st.caption("Random Forest Model Feature Importance (Global Gini Feature Importances from trained Random Forest)")
                top_global = xai['global_importances'][:10]
                fig, ax = plt.subplots(figsize=(8, 3.5))
                y_pos = np.arange(len(top_global))
                scores = [x['importance'] for x in top_global]
                labels = [format_symptom_name(x['symptom']) for x in top_global]

                ax.barh(y_pos, scores, align='center', color='#0f766e')
                ax.set_yticks(y_pos)
                ax.set_yticklabels(labels)
                ax.invert_yaxis()
                ax.set_xlabel('Random Forest Gini Feature Importance')
                ax.set_title('Random Forest Model Feature Importance')
                plt.tight_layout()
                st.pyplot(fig)

        st.markdown("---")

        # DISEASE INFORMATION SECTION
        st.markdown(f"### 📖 Disease Information — {pred_res['disease']}")
        details = pred_res['details']
        if details:
            col_d1, col_d2 = st.columns(2)
            with col_d1:
                st.markdown(f"**Description:** {details['description']}")
                st.markdown(f"**👨‍⚕️ Recommended Specialist:** `{details['recommended_doctor']}`")

                st.markdown("**🔍 Possible Causes:**")
                for c in details.get('causes', []):
                    st.markdown(f"• {c}")

                st.markdown("**🥗 Diet Recommendations:**")
                for d in details.get('diet_recommendations', []):
                    st.markdown(f"• {d}")

            with col_d2:
                st.markdown("**⚠️ Required Precautions:**")
                for p in details.get('precautions', []):
                    st.markdown(f"• {p}")

                st.markdown("**🏃 Recommended Lifestyle Modifications:**")
                for l in details.get('lifestyle_changes', []):
                    st.markdown(f"• {l}")
        else:
            st.info("No detailed clinical profile entry found in database for this disease.")

        st.markdown("""
        <div class="disclaimer-box">
            <strong>Medical Disclaimer:</strong> This prediction is generated by a machine learning model for educational purposes and should not be considered a medical diagnosis. Please consult a qualified healthcare professional for medical advice.
        </div>
        """, unsafe_allow_html=True)


# ==========================================
# PAGE 3: SPECIALIZED DIAGNOSIS (NEW PAGE)
# ==========================================
elif nav_choice == "🔬 Specialized Diagnosis":
    st.markdown("""
    <div class="main-header">
        <h1>Specialized Disease Diagnosis</h1>
        <p>Dedicated clinical diagnostic modules powered by disease-specific machine learning models</p>
    </div>
    """, unsafe_allow_html=True)

    if specialized_error or not specialized_meta:
        st.error(f"Cannot initialize specialized diagnosis engine: {specialized_error}")
        st.stop()

    disease_labels = {
        "heart_disease": "❤️ Heart Disease",
        "kidney_disease": "🫘 Chronic Kidney Disease",
        "breast_cancer": "🎗️ Breast Cancer",
        "liver_disease": "🫀 Liver Disease",
        "stroke": "🧠 Stroke",
        "lung_cancer": "🫁 Lung Cancer"
    }

    selected_disease_label = st.selectbox(
        "Select a Specialized Clinical Disease Module:",
        options=list(disease_labels.values()),
        index=0,
        help="Select a specialized disease to load its specific clinical input form."
    )

    # Reverse lookup key
    selected_key = [k for k, v in disease_labels.items() if v == selected_disease_label][0]
    meta = specialized_meta[selected_key]
    spec_model = specialized_models.get(selected_key)

    st.markdown(f"### {selected_disease_label}")
    st.caption(f"**Best Algorithm Selected:** {meta['selected_algorithm']} | **Dataset Records:** {meta['dataset_records']} | **Features:** {meta['feature_count']} | **Benchmark F1 Score:** {meta['best_f1_score']*100:.1f}%")

    if spec_model is None:
        st.error(f"Model file '{meta['model_file']}' could not be deserialized.")
        st.stop()

    # Form Container for current selected disease ONLY
    input_values = {}

    with st.form(key=f"form_{selected_key}"):
        st.write("**Enter Patient Clinical Parameters:**")

        if selected_key == "heart_disease":
            c1, c2, c3 = st.columns(3)
            with c1:
                input_values['age'] = st.number_input("Age (years)", min_value=1, max_value=120, value=55)
                input_values['sex'] = 1 if st.selectbox("Sex", options=["Male (1)", "Female (0)"]) == "Male (1)" else 0
                input_values['cp'] = st.selectbox("Chest Pain Type (cp)", options=[0, 1, 2, 3], format_func=lambda x: f"Type {x}: " + ["Typical Angina", "Atypical Angina", "Non-anginal Pain", "Asymptomatic"][x])
                input_values['trestbps'] = st.number_input("Resting Blood Pressure (mm Hg)", min_value=80, max_value=220, value=130)
                input_values['chol'] = st.number_input("Serum Cholesterol (mg/dl)", min_value=100, max_value=600, value=240)
            with c2:
                input_values['fbs'] = 1 if st.selectbox("Fasting Blood Sugar > 120 mg/dl", options=["No (0)", "Yes (1)"]) == "Yes (1)" else 0
                input_values['restecg'] = st.selectbox("Resting ECG Results", options=[0, 1, 2], format_func=lambda x: f"Value {x}: " + ["Normal", "ST-T Wave Abnormality", "Left Ventricular Hypertrophy"][x])
                input_values['thalach'] = st.number_input("Maximum Heart Rate Achieved", min_value=60, max_value=220, value=150)
                input_values['exang'] = 1 if st.selectbox("Exercise Induced Angina", options=["No (0)", "Yes (1)"]) == "Yes (1)" else 0
            with c3:
                input_values['oldpeak'] = st.number_input("ST Depression (oldpeak)", min_value=0.0, max_value=10.0, value=1.0, step=0.1)
                input_values['slope'] = st.selectbox("Slope of Peak Exercise ST Segment", options=[0, 1, 2], format_func=lambda x: f"Slope {x}: " + ["Upsloping", "Flat", "Downsloping"][x])
                input_values['ca'] = st.selectbox("Major Vessels Colored by Fluoroscopy (ca)", options=[0, 1, 2, 3, 4])
                input_values['thal'] = st.selectbox("Thalassemia (thal)", options=[0, 1, 2, 3], format_func=lambda x: f"Code {x}: " + ["Null/Unknown", "Normal", "Fixed Defect", "Reversable Defect"][x])

            predict_button = st.form_submit_button("❤️ Predict Heart Disease Risk", type="primary", use_container_width=True)

        elif selected_key == "kidney_disease":
            c1, c2, c3 = st.columns(3)
            with c1:
                input_values['age'] = st.number_input("Age (years)", min_value=1, max_value=120, value=48)
                input_values['bp'] = st.number_input("Blood Pressure (mm Hg)", min_value=50, max_value=180, value=80)
                input_values['bgr'] = st.number_input("Blood Glucose Random (mgs/dl)", min_value=50, max_value=500, value=121)
                input_values['bu'] = st.number_input("Blood Urea (mgs/dl)", min_value=10, max_value=400, value=36)
                input_values['sc'] = st.number_input("Serum Creatinine (mgs/dl)", min_value=0.4, max_value=20.0, value=1.2, step=0.1)
                input_values['sod'] = st.number_input("Sodium (mEq/L)", min_value=100, max_value=180, value=138)
                input_values['pot'] = st.number_input("Potassium (mEq/L)", min_value=2.0, max_value=10.0, value=4.4, step=0.1)
                input_values['hemo'] = st.number_input("Hemoglobin (gms)", min_value=3.0, max_value=20.0, value=12.5, step=0.1)

            with c2:
                input_values['pcv'] = st.number_input("Packed Cell Volume", min_value=10, max_value=60, value=39)
                input_values['wc'] = st.number_input("White Blood Cell Count", min_value=2000, max_value=30000, value=7800)
                input_values['rc'] = st.number_input("Red Blood Cell Count (millions/cmm)", min_value=2.0, max_value=8.0, value=4.7, step=0.1)
                input_values['sg'] = float(st.selectbox("Specific Gravity", options=["1.005", "1.010", "1.015", "1.020", "1.025"], index=3))
                input_values['al'] = float(st.selectbox("Albumin", options=[0, 1, 2, 3, 4, 5], index=0))
                input_values['su'] = float(st.selectbox("Sugar Level", options=[0, 1, 2, 3, 4, 5], index=0))
                input_values['rbc'] = st.selectbox("Red Blood Cells", options=["normal", "abnormal"], index=0)
                input_values['pc'] = st.selectbox("Pus Cell", options=["normal", "abnormal"], index=0)

            with c3:
                input_values['pcc'] = st.selectbox("Pus Cell Clumps", options=["notpresent", "present"], index=0)
                input_values['ba'] = st.selectbox("Bacteria", options=["notpresent", "present"], index=0)
                input_values['htn'] = st.selectbox("Hypertension", options=["no", "yes"], index=0)
                input_values['dm'] = st.selectbox("Diabetes Mellitus", options=["no", "yes"], index=0)
                input_values['cad'] = st.selectbox("Coronary Artery Disease", options=["no", "yes"], index=0)
                input_values['appet'] = st.selectbox("Appetite", options=["good", "poor"], index=0)
                input_values['pe'] = st.selectbox("Pedal Edema", options=["no", "yes"], index=0)
                input_values['ane'] = st.selectbox("Anemia", options=["no", "yes"], index=0)

            predict_button = st.form_submit_button("🫘 Predict Kidney Disease Risk", type="primary", use_container_width=True)

        elif selected_key == "breast_cancer":
            st.info("Wisconsin Diagnostic Breast Cancer dataset (30 digitized FNA image features). Defaults represent baseline benign tumor characteristics.")
            t1, t2, t3 = st.tabs(["Mean Attributes", "Standard Error Attributes", "Worst Attributes"])
            
            with t1:
                c1, c2 = st.columns(2)
                with c1:
                    input_values['mean radius'] = st.number_input("mean radius", min_value=6.0, max_value=35.0, value=13.5, step=0.1)
                    input_values['mean texture'] = st.number_input("mean texture", min_value=9.0, max_value=40.0, value=17.8, step=0.1)
                    input_values['mean perimeter'] = st.number_input("mean perimeter", min_value=40.0, max_value=200.0, value=87.0, step=0.1)
                    input_values['mean area'] = st.number_input("mean area", min_value=140.0, max_value=2500.0, value=565.0, step=1.0)
                    input_values['mean smoothness'] = st.number_input("mean smoothness", min_value=0.05, max_value=0.20, value=0.096, step=0.005, format="%.4f")
                with c2:
                    input_values['mean compactness'] = st.number_input("mean compactness", min_value=0.01, max_value=0.35, value=0.104, step=0.005, format="%.4f")
                    input_values['mean concavity'] = st.number_input("mean concavity", min_value=0.0, max_value=0.45, value=0.088, step=0.005, format="%.4f")
                    input_values['mean concave points'] = st.number_input("mean concave points", min_value=0.0, max_value=0.25, value=0.048, step=0.005, format="%.4f")
                    input_values['mean symmetry'] = st.number_input("mean symmetry", min_value=0.10, max_value=0.35, value=0.181, step=0.005, format="%.4f")
                    input_values['mean fractal dimension'] = st.number_input("mean fractal dimension", min_value=0.04, max_value=0.10, value=0.062, step=0.002, format="%.4f")

            with t2:
                c1, c2 = st.columns(2)
                with c1:
                    input_values['radius error'] = st.number_input("radius error", min_value=0.05, max_value=3.0, value=0.40, step=0.05)
                    input_values['texture error'] = st.number_input("texture error", min_value=0.3, max_value=5.0, value=1.21, step=0.05)
                    input_values['perimeter error'] = st.number_input("perimeter error", min_value=0.7, max_value=22.0, value=2.86, step=0.1)
                    input_values['area error'] = st.number_input("area error", min_value=6.0, max_value=500.0, value=40.3, step=1.0)
                    input_values['smoothness error'] = st.number_input("smoothness error", min_value=0.001, max_value=0.04, value=0.007, step=0.001, format="%.4f")
                with c2:
                    input_values['compactness error'] = st.number_input("compactness error", min_value=0.002, max_value=0.15, value=0.025, step=0.002, format="%.4f")
                    input_values['concavity error'] = st.number_input("concavity error", min_value=0.0, max_value=0.4, value=0.031, step=0.002, format="%.4f")
                    input_values['concave points error'] = st.number_input("concave points error", min_value=0.0, max_value=0.06, value=0.011, step=0.001, format="%.4f")
                    input_values['symmetry error'] = st.number_input("symmetry error", min_value=0.005, max_value=0.08, value=0.020, step=0.001, format="%.4f")
                    input_values['fractal dimension error'] = st.number_input("fractal dimension error", min_value=0.0005, max_value=0.03, value=0.0037, step=0.0005, format="%.4f")

            with t3:
                c1, c2 = st.columns(2)
                with c1:
                    input_values['worst radius'] = st.number_input("worst radius", min_value=7.0, max_value=40.0, value=16.2, step=0.1)
                    input_values['worst texture'] = st.number_input("worst texture", min_value=12.0, max_value=50.0, value=25.6, step=0.1)
                    input_values['worst perimeter'] = st.number_input("worst perimeter", min_value=50.0, max_value=260.0, value=107.0, step=0.5)
                    input_values['worst area'] = st.number_input("worst area", min_value=180.0, max_value=4250.0, value=880.0, step=5.0)
                    input_values['worst smoothness'] = st.number_input("worst smoothness", min_value=0.07, max_value=0.25, value=0.132, step=0.005, format="%.4f")
                with c2:
                    input_values['worst compactness'] = st.number_input("worst compactness", min_value=0.02, max_value=1.05, value=0.254, step=0.01, format="%.4f")
                    input_values['worst concavity'] = st.number_input("worst concavity", min_value=0.0, max_value=1.25, value=0.272, step=0.01, format="%.4f")
                    input_values['worst concave points'] = st.number_input("worst concave points", min_value=0.0, max_value=0.30, value=0.114, step=0.005, format="%.4f")
                    input_values['worst symmetry'] = st.number_input("worst symmetry", min_value=0.15, max_value=0.66, value=0.290, step=0.005, format="%.4f")
                    input_values['worst fractal dimension'] = st.number_input("worst fractal dimension", min_value=0.05, max_value=0.21, value=0.083, step=0.002, format="%.4f")

            predict_button = st.form_submit_button("🎗️ Predict Breast Cancer Risk", type="primary", use_container_width=True)

        elif selected_key == "liver_disease":
            c1, c2 = st.columns(2)
            with c1:
                input_values['age'] = st.number_input("Age (years)", min_value=1, max_value=120, value=45)
                input_values['gender'] = st.selectbox("Gender", options=["Male", "Female"], index=0)
                input_values['total_bilirubin'] = st.number_input("Total Bilirubin (mg/dL)", min_value=0.1, max_value=75.0, value=1.0, step=0.1)
                input_values['direct_bilirubin'] = st.number_input("Direct Bilirubin (mg/dL)", min_value=0.1, max_value=30.0, value=0.3, step=0.1)
                input_values['alkaline_phosphotase'] = st.number_input("Alkaline Phosphotase (IU/L)", min_value=50, max_value=2500, value=198)
            with c2:
                input_values['alamine_aminotransferase'] = st.number_input("Alamine Aminotransferase (ALT) (IU/L)", min_value=10, max_value=2000, value=35)
                input_values['aspartate_aminotransferase'] = st.number_input("Aspartate Aminotransferase (AST) (IU/L)", min_value=10, max_value=5000, value=42)
                input_values['total_proteins'] = st.number_input("Total Proteins (g/dL)", min_value=2.0, max_value=10.0, value=6.5, step=0.1)
                input_values['albumin'] = st.number_input("Albumin (g/dL)", min_value=0.9, max_value=6.0, value=3.2, step=0.1)
                input_values['albumin_and_globulin_ratio'] = st.number_input("Albumin & Globulin Ratio", min_value=0.3, max_value=3.0, value=0.95, step=0.05)

            predict_button = st.form_submit_button("🫀 Predict Liver Disease Risk", type="primary", use_container_width=True)

        elif selected_key == "stroke":
            c1, c2 = st.columns(2)
            with c1:
                input_values['age'] = st.number_input("Age (years)", min_value=1, max_value=120, value=62)
                input_values['gender'] = st.selectbox("Gender", options=["Male", "Female", "Other"], index=0)
                input_values['hypertension'] = 1 if st.selectbox("Hypertension History", options=["No (0)", "Yes (1)"]) == "Yes (1)" else 0
                input_values['heart_disease'] = 1 if st.selectbox("Heart Disease History", options=["No (0)", "Yes (1)"]) == "Yes (1)" else 0
                input_values['ever_married'] = st.selectbox("Ever Married", options=["Yes", "No"], index=0)
            with c2:
                input_values['work_type'] = st.selectbox("Work Type", options=["Private", "Self-employed", "Govt_job", "children", "Never_worked"], index=0)
                input_values['Residence_type'] = st.selectbox("Residence Type", options=["Urban", "Rural"], index=0)
                input_values['avg_glucose_level'] = st.number_input("Average Glucose Level (mg/dL)", min_value=50.0, max_value=300.0, value=106.0, step=1.0)
                input_values['bmi'] = st.number_input("Body Mass Index (BMI)", min_value=10.0, max_value=70.0, value=28.8, step=0.1)
                input_values['smoking_status'] = st.selectbox("Smoking Status", options=["formerly smoked", "never smoked", "smokes", "Unknown"], index=1)

            predict_button = st.form_submit_button("🧠 Predict Stroke Risk", type="primary", use_container_width=True)

        elif selected_key == "lung_cancer":
            c1, c2 = st.columns(2)
            with c1:
                input_values['AGE'] = st.number_input("Age (years)", min_value=15, max_value=100, value=60)
                input_values['GENDER'] = st.selectbox("Gender", options=["Male (M)", "Female (F)"], index=0)[0]
                input_values['SMOKING'] = 2 if st.selectbox("Smoking History", options=["No (1)", "Yes (2)"], index=1) == "Yes (2)" else 1
                input_values['YELLOW_FINGERS'] = 2 if st.selectbox("Yellow Fingers", options=["No (1)", "Yes (2)"]) == "Yes (2)" else 1
                input_values['ANXIETY'] = 2 if st.selectbox("Anxiety", options=["No (1)", "Yes (2)"]) == "Yes (2)" else 1
                input_values['PEER_PRESSURE'] = 2 if st.selectbox("Peer Pressure", options=["No (1)", "Yes (2)"]) == "Yes (2)" else 1
                input_values['CHRONIC DISEASE'] = 2 if st.selectbox("Chronic Disease", options=["No (1)", "Yes (2)"]) == "Yes (2)" else 1
                input_values['FATIGUE'] = 2 if st.selectbox("Fatigue", options=["No (1)", "Yes (2)"], index=1) == "Yes (2)" else 1
            with c2:
                input_values['ALLERGY'] = 2 if st.selectbox("Allergy", options=["No (1)", "Yes (2)"]) == "Yes (2)" else 1
                input_values['WHEEZING'] = 2 if st.selectbox("Wheezing", options=["No (1)", "Yes (2)"]) == "Yes (2)" else 1
                input_values['ALCOHOL CONSUMING'] = 2 if st.selectbox("Alcohol Consuming", options=["No (1)", "Yes (2)"]) == "Yes (2)" else 1
                input_values['COUGHING'] = 2 if st.selectbox("Coughing", options=["No (1)", "Yes (2)"], index=1) == "Yes (2)" else 1
                input_values['SHORTNESS OF BREATH'] = 2 if st.selectbox("Shortness of Breath", options=["No (1)", "Yes (2)"], index=1) == "Yes (2)" else 1
                input_values['SWALLOWING DIFFICULTY'] = 2 if st.selectbox("Swallowing Difficulty", options=["No (1)", "Yes (2)"]) == "Yes (2)" else 1
                input_values['CHEST PAIN'] = 2 if st.selectbox("Chest Pain", options=["No (1)", "Yes (2)"]) == "Yes (2)" else 1

            predict_button = st.form_submit_button("🫁 Predict Lung Cancer Risk", type="primary", use_container_width=True)

    # Process Specialized Prediction
    if predict_button:
        with st.spinner(f"Running {meta['selected_algorithm']} inference..."):
            # Construct DataFrame with exact column sequence
            input_df = pd.DataFrame([input_values])[meta['feature_names']]

            try:
                raw_pred = spec_model.predict(input_df)[0]
                pred_label_str = str(raw_pred)
                
                # Retrieve readable class label
                class_text = meta['target_names'].get(pred_label_str, f"Class {pred_label_str}")

                prob_val = 0.0
                if hasattr(spec_model, "predict_proba"):
                    probs = spec_model.predict_proba(input_df)[0]
                    # Index corresponding to raw_pred
                    try:
                        classes_arr = list(spec_model.classes_)
                        c_idx = classes_arr.index(raw_pred)
                        prob_val = float(probs[c_idx])
                    except Exception:
                        prob_val = float(np.max(probs))

                # Save history record
                uid = st.session_state.get('user_id') or get_current_user_id()
                saved_id = None
                try:
                    inputs_summary = f"{meta['display_name']} ({len(input_values)} parameters)"
                    saved_id = Prediction.create(
                        user_id=uid,
                        symptoms=input_values,
                        predicted_disease=f"{meta['display_name']}: {class_text}",
                        confidence=prob_val,
                        prediction_type='Specialized'
                    )
                except Exception as db_err:
                    pass

                # Store specialized result
                st.session_state.specialized_result = {
                    'disease_name': meta['display_name'],
                    'disease_key': selected_key,
                    'selected_algorithm': meta['selected_algorithm'],
                    'predicted_class_text': class_text,
                    'probability': prob_val,
                    'input_values': input_values,
                    'feature_importances': meta.get('feature_importances', {}),
                    'saved_id': saved_id
                }
            except Exception as eval_err:
                st.error(f"Prediction error: {eval_err}")

    # Render Specialized Results
    if 'specialized_result' in st.session_state and st.session_state.specialized_result and st.session_state.specialized_result.get('disease_key') == selected_key:
        res = st.session_state.specialized_result
        st.markdown("---")
        st.markdown("## 📊 Specialized Diagnosis Result")

        res_col1, res_col2 = st.columns([1, 1])

        with res_col1:
            st.markdown(f"""
            <div class="health-card health-card-accent">
                <span class="metric-badge badge-spec">{res['disease_name']} Module</span>
                <p style="color: #64748b; font-size: 0.85rem; margin-top: 0.4rem; margin-bottom: 0.2rem;">
                    Model Predicted Output:
                </p>
                <h2 style="color: #0f766e; margin-top: 0.2rem; margin-bottom: 0.3rem;">{res['predicted_class_text']}</h2>
                <h4 style="color: #10b981; margin: 0;">Model-Estimated Probability: {res['probability'] * 100:.1f}%</h4>
                <p style="color: #475569; font-size: 0.8rem; margin-top: 0.4rem; margin-bottom: 0;">
                    Algorithm Selected: <strong>{res['selected_algorithm']}</strong>
                </p>
            </div>
            """, unsafe_allow_html=True)

        with res_col2:
            st.markdown("### 📄 Clinical Report Download")
            pdf_data = {
                'disease_name': res['disease_name'],
                'disease': f"{res['disease_name']} ({res['predicted_class_text']})",
                'confidence': res['probability'],
                'inputs_summary': f"{len(res['input_values'])} clinical parameters evaluated",
                'model_used': res['selected_algorithm']
            }
            spec_pdf_bytes = generate_pdf_report(pdf_data, disease_details={'description': f'Specialized clinical model classification for {res["disease_name"]}.'}, is_specialized=True)
            st.download_button(
                label="📄 Download Specialized Diagnosis Report (PDF)",
                data=spec_pdf_bytes,
                file_name=f"PrediHealth_Specialized_{res['disease_key']}.pdf",
                mime="application/pdf"
            )

        st.markdown("---")

        # MODEL FEATURE IMPORTANCES PLOT
        st.markdown("### 🌲 Model Feature Importance")
        f_imps = res.get('feature_importances', {})
        if f_imps:
            sorted_imps = sorted(f_imps.items(), key=lambda x: x[1], reverse=True)[:10]
            top_feats = [x[0] for x in sorted_imps]
            top_scores = [x[1] for x in sorted_imps]

            fig_f, ax_f = plt.subplots(figsize=(8, 3.5))
            y_p = np.arange(len(top_feats))
            ax_f.barh(y_p, top_scores, align='center', color='#0369a1')
            ax_f.set_yticks(y_p)
            ax_f.set_yticklabels(top_feats)
            ax_f.invert_yaxis()
            ax_f.set_xlabel('Model Feature Importance')
            ax_f.set_title(f'{res["disease_name"]} — Top Feature Importances ({res["selected_algorithm"]})')
            plt.tight_layout()
            st.pyplot(fig_f)

        # Educational Information & Disclaimer
        st.markdown("### 📖 Educational Summary & Precautions")
        st.write(f"""
        - **Model Classification**: The {res['selected_algorithm']} model evaluated patient clinical parameters and estimated a **{res['probability']*100:.1f}%** probability for **{res['predicted_class_text']}**.
        - **General Precautions**: Maintain routine medical monitoring, follow recommended dietary guidelines, keep regular health appointments, and report any sudden symptom onset.
        """)

        st.markdown("""
        <div class="disclaimer-box">
            <strong>Medical Disclaimer:</strong> This system is intended for educational and research demonstration purposes only. Machine learning predictions are not a medical diagnosis and should not replace professional medical evaluation. Please consult a qualified healthcare professional for medical concerns.
        </div>
        """, unsafe_allow_html=True)


# ==========================================
# PAGE 4: MODEL ANALYTICS
# ==========================================
elif nav_choice == "📊 Model Analytics":
    st.markdown("""
    <div class="main-header">
        <h1>Model Analytics & Benchmark Comparison</h1>
        <p>Performance metrics, dataset distributions, and 5-algorithm benchmarks across specialized models</p>
    </div>
    """, unsafe_allow_html=True)

    tab_an1, tab_an2 = st.tabs(["🩺 General Symptom Model Analytics", "🔬 Specialized Models Benchmarks"])

    with tab_an1:
        if dataset_error or dataset_df is None:
            st.error(f"Cannot load dataset for analytics: {dataset_error}")
        else:
            st.markdown("### 📈 General 20-Disease Model Evaluation (Stratified 80/20 Test Split)")

            from sklearn.model_selection import train_test_split
            from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score

            X = dataset_df.drop(columns=['disease'])
            y = dataset_df['disease']

            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.20, random_state=42, stratify=y
            )

            if model is not None:
                y_pred = model.predict(X_test)
                acc = accuracy_score(y_test, y_pred)
                prec = precision_score(y_test, y_pred, average='weighted')
                rec = recall_score(y_test, y_pred, average='weighted')
                f1 = f1_score(y_test, y_pred, average='weighted')
            else:
                acc, prec, rec, f1 = 0.0, 0.0, 0.0, 0.0

            m1, m2, m3, m4 = st.columns(4)
            with m1:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-card-number">{acc * 100:.1f}%</div>
                    <div class="metric-card-label">Accuracy</div>
                </div>
                """, unsafe_allow_html=True)
            with m2:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-card-number">{prec * 100:.1f}%</div>
                    <div class="metric-card-label">Precision (Weighted)</div>
                </div>
                """, unsafe_allow_html=True)
            with m3:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-card-number">{rec * 100:.1f}%</div>
                    <div class="metric-card-label">Recall (Weighted)</div>
                </div>
                """, unsafe_allow_html=True)
            with m4:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-card-number">{f1 * 100:.1f}%</div>
                    <div class="metric-card-label">F1 Score (Weighted)</div>
                </div>
                """, unsafe_allow_html=True)

            st.markdown("<br/>", unsafe_allow_html=True)

            col_chart1, col_chart2 = st.columns(2)

            with col_chart1:
                st.markdown("### 📊 Dataset Disease Class Distribution")
                disease_counts = dataset_df['disease'].value_counts()

                fig_dist, ax_dist = plt.subplots(figsize=(6, 4.5))
                ax_dist.barh(disease_counts.index, disease_counts.values, color='#10b981')
                ax_dist.set_xlabel("Sample Count")
                ax_dist.set_ylabel("Disease Class")
                ax_dist.set_title("Records per Disease (Total: 1600)")
                ax_dist.invert_yaxis()
                plt.tight_layout()
                st.pyplot(fig_dist)

            with col_chart2:
                st.markdown("### 🌲 Random Forest Model Feature Importance")
                if model is not None and symptoms_list is not None:
                    importances = model.feature_importances_
                    feat_df = pd.DataFrame({
                        'Symptom': [format_symptom_name(s) for s in symptoms_list],
                        'Importance': importances
                    }).sort_values(by='Importance', ascending=False).head(12)

                    fig_imp, ax_imp = plt.subplots(figsize=(6, 4.5))
                    ax_imp.barh(feat_df['Symptom'], feat_df['Importance'], color='#0f766e')
                    ax_imp.set_xlabel("Gini Feature Importance")
                    ax_imp.set_title("Random Forest Model Feature Importance")
                    ax_imp.invert_yaxis()
                    plt.tight_layout()
                    st.pyplot(fig_imp)

    with tab_an2:
        st.markdown("### 🔬 Specialized Disease Models Benchmark Comparison")
        st.write("Evaluating **Random Forest, XGBoost, Decision Tree, K-Nearest Neighbors (KNN), and Gradient Boosting** across 6 specialized public datasets.")

        if not specialized_meta:
            st.warning("Specialized model metadata not available.")
        else:
            for s_key, s_info in specialized_meta.items():
                st.markdown(f"#### {s_info['display_name']}")
                st.write(f"**Records:** {s_info['dataset_records']} | **Features:** {s_info['feature_count']} | **Selected Best Model:** `{s_info['selected_algorithm']}` (F1: **{s_info['best_f1_score']*100:.2f}%**)")

                # Comparison Table
                comp_df = pd.DataFrame(s_info['evaluation_comparison'])
                comp_df['Accuracy'] = comp_df['accuracy'].map(lambda x: f"{x*100:.2f}%")
                comp_df['Precision'] = comp_df['precision'].map(lambda x: f"{x*100:.2f}%")
                comp_df['Recall'] = comp_df['recall'].map(lambda x: f"{x*100:.2f}%")
                comp_df['F1 Score'] = comp_df['f1_score'].map(lambda x: f"{x*100:.2f}%")

                display_comp = comp_df[['algorithm', 'Accuracy', 'Precision', 'Recall', 'F1 Score']].rename(columns={'algorithm': 'Algorithm'})
                st.table(display_comp)
                st.markdown("---")

            # Comparative Chart across all 6 specialized diseases
            st.markdown("### 🏆 Best Model F1 Score Across Specialized Diseases")
            spec_names = [info['display_name'] for info in specialized_meta.values()]
            spec_f1s = [info['best_f1_score']*100 for info in specialized_meta.values()]
            spec_algos = [info['selected_algorithm'] for info in specialized_meta.values()]

            fig_comp, ax_comp = plt.subplots(figsize=(9, 4))
            bars = ax_comp.bar(spec_names, spec_f1s, color='#0f766e')
            ax_comp.set_ylabel("Best F1 Score (%)")
            ax_comp.set_ylim(0, 110)
            ax_comp.set_title("Benchmark Performance Across 6 Specialized Disease Models")

            for bar, algo, f1_val in zip(bars, spec_algos, spec_f1s):
                yval = bar.get_height()
                ax_comp.text(bar.get_x() + bar.get_width()/2.0, yval + 1.5, f"{f1_val:.1f}%\n({algo})", ha='center', va='bottom', fontsize=8, fontweight='bold')

            plt.xticks(rotation=15)
            plt.tight_layout()
            st.pyplot(fig_comp)


# ==========================================
# PAGE 5: PREDICTION HISTORY
# ==========================================
elif nav_choice == "📜 Prediction History":
    st.markdown("""
    <div class="main-header">
        <h1>Prediction History</h1>
        <p>Logged diagnostic predictions retrieved from SQLite database</p>
    </div>
    """, unsafe_allow_html=True)

    try:
        uid = st.session_state.get('user_id') or get_current_user_id()
        rows = query_db(
            "SELECT id, user_id, symptoms, predicted_disease, confidence, prediction_type, created_at "
            "FROM predictions WHERE user_id = ? ORDER BY created_at DESC",
            (uid,)
        )
    except Exception as db_err:
        st.error(f"Failed to query database: {db_err}")
        rows = []

    if not rows:
        st.info("No prediction history entries found in the database yet. Run a prediction on the '🩺 Symptom Prediction' or '🔬 Specialized Diagnosis' tab!")
    else:
        history_list = []
        for r in rows:
            rec = dict(r)
            try:
                syms = json.loads(rec['symptoms'])
                if isinstance(syms, list):
                    rec['symptoms_fmt'] = ", ".join([format_symptom_name(s) for s in syms])
                elif isinstance(syms, dict):
                    rec['symptoms_fmt'] = f"Parameters ({len(syms)})"
                else:
                    rec['symptoms_fmt'] = str(syms)
            except Exception:
                rec['symptoms_fmt'] = str(rec['symptoms'])
            rec['confidence_pct'] = f"{rec['confidence'] * 100:.1f}%"
            if 'prediction_type' not in rec or not rec['prediction_type']:
                rec['prediction_type'] = 'General'
            history_list.append(rec)

        hist_df = pd.DataFrame(history_list)

        # Search and Filter
        c_f1, c_f2, c_f3 = st.columns(3)
        with c_f1:
            search_query = st.text_input("🔍 Search History:", "")
        with c_f2:
            type_filter = st.selectbox("Filter by Module Type:", ["All Types", "General", "Specialized"])
        with c_f3:
            unique_diseases = ["All Diseases"] + sorted(list(hist_df['predicted_disease'].unique()))
            disease_filter = st.selectbox("Filter by Disease:", unique_diseases)

        # Apply filtering
        filtered_df = hist_df.copy()
        if type_filter != "All Types":
            filtered_df = filtered_df[filtered_df['prediction_type'] == type_filter]
        if disease_filter != "All Diseases":
            filtered_df = filtered_df[filtered_df['predicted_disease'] == disease_filter]
        if search_query.strip():
            sq = search_query.lower()
            filtered_df = filtered_df[
                filtered_df['predicted_disease'].str.lower().str.contains(sq) |
                filtered_df['symptoms_fmt'].str.lower().str.contains(sq)
            ]

        st.markdown(f"Displaying **{len(filtered_df)}** of **{len(hist_df)}** stored history records:")

        display_df = filtered_df[['id', 'created_at', 'prediction_type', 'predicted_disease', 'confidence_pct', 'symptoms_fmt']].rename(columns={
            'id': 'ID',
            'created_at': 'Date / Time',
            'prediction_type': 'Module Type',
            'predicted_disease': 'Predicted Disease / Result',
            'confidence_pct': 'Confidence / Probability',
            'symptoms_fmt': 'Input Summary'
        })

        st.dataframe(display_df, use_container_width=True, hide_index=True)


# ==========================================
# PAGE 6: HEALTH ASSISTANT (FLASK CHATBOT MATCH)
# ==========================================
elif nav_choice == "💬 Health Assistant":
    uid = st.session_state.get('user_id') or get_current_user_id()
    if 'chat_messages' not in st.session_state:
        st.session_state.chat_messages = []
        if uid:
            try:
                db_hist = ChatHistory.get_history_by_user(uid)
                for item in db_hist:
                    st.session_state.chat_messages.append({
                        'sender': item['sender'],
                        'message': item['message'],
                        'is_emergency': 'EMERGENCY WARNING' in item['message']
                    })
            except Exception:
                pass

    if 'pending_chat_query' not in st.session_state:
        st.session_state.pending_chat_query = None

    c_head1, c_head2 = st.columns([4, 1])
    with c_head1:
        st.markdown("""
        <div class="chat-header-bar">
            <div style="display: flex; align-items: center; gap: 12px;">
                <div style="background-color: rgba(255,255,255,0.2); width: 36px; height: 36px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 1.1rem;">
                    💗
                </div>
                <div>
                    <h4 style="margin: 0; color: #ffffff !important; font-weight: 700; font-size: 1.15rem;">Health Assistant</h4>
                    <p style="margin: 0; color: #94a3b8 !important; font-size: 0.75rem;">AI Support Active — General & Specialized Knowledge</p>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    with c_head2:
        if st.button("🗑️ Clear Chat", use_container_width=True):
            st.session_state.chat_messages = []
            st.session_state.pending_chat_query = None
            if uid:
                try:
                    ChatHistory.clear_history(uid)
                except Exception:
                    pass
            st.rerun()

    st.markdown("""
    <div class="chat-disclaimer-bar">
        ⚠️ Disclaimer: Not a replacement for professional medical advice.
    </div>
    <br/>
    """, unsafe_allow_html=True)

    if st.session_state.pending_chat_query:
        user_text = st.session_state.pending_chat_query
        st.session_state.pending_chat_query = None
        reply_text, is_emerg = process_chat_query(user_text)
        st.session_state.chat_messages.append({'sender': 'user', 'message': user_text, 'is_emergency': False})
        st.session_state.chat_messages.append({'sender': 'bot', 'message': reply_text, 'is_emergency': is_emerg})
        if uid:
            try:
                ChatHistory.create_message(uid, 'user', user_text)
                ChatHistory.create_message(uid, 'bot', reply_text)
            except Exception:
                pass
        st.rerun()

    if not st.session_state.chat_messages:
        initial_bot_msg = (
            "Hello! I am your AI Health Assistant. I can assist you with understanding General Symptom-based predictions, "
            "Specialized Diseases (Heart Disease, Chronic Kidney Disease, Breast Cancer, Liver Disease, Stroke, Lung Cancer), "
            "precautions, diets, lifestyle modifications, or specialist recommendations.\n\n"
            "How can I help you today? You can ask me:\n"
            "• *'Explain my latest prediction'* or *'Diet for Diabetes'*\n"
            "• *'What are the risk factors for Heart Disease?'*\n"
            "• *'Precautions for Stroke or Kidney Disease'*\n"
            "• *'How can I boost my immune system?'*"
        )
        st.markdown(f"""
        <div style="display: flex; justify-content: flex-start; align-items: flex-start; margin-bottom: 1rem;">
            <div class="chat-bubble-assistant">
                <strong style="color: #0f766e;">🤖 Health Assistant</strong><br/>
                {initial_bot_msg}
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        for msg in st.session_state.chat_messages:
            if msg['sender'] == 'user':
                st.markdown(f"""
                <div style="display: flex; justify-content: flex-end; align-items: flex-start; margin-bottom: 0.85rem;">
                    <div class="chat-bubble-user">
                        <strong>👤 You</strong><br/>
                        {msg['message']}
                    </div>
                </div>
                """, unsafe_allow_html=True)
            else:
                bubble_class = "chat-bubble-emergency" if msg.get('is_emergency') else "chat-bubble-assistant"
                st.markdown(f"""
                <div style="display: flex; justify-content: flex-start; align-items: flex-start; margin-bottom: 0.85rem;">
                    <div class="{bubble_class}">
                        <strong style="color: #0f766e;">🤖 Health Assistant</strong><br/>
                        {msg['message']}
                    </div>
                </div>
                """, unsafe_allow_html=True)

    st.markdown("<p style='font-weight: 600; font-size: 0.85rem; color: #475569; margin-bottom: 0.4rem;'>Quick Replies:</p>", unsafe_allow_html=True)
    q_col1, q_col2, q_col3, q_col4 = st.columns(4)
    with q_col1:
        if st.button("Explain Diagnosis", key="qr_explain", use_container_width=True):
            st.session_state.pending_chat_query = "Explain my prediction"
            st.rerun()
    with q_col2:
        if st.button("Heart Health Tips", key="qr_heart", use_container_width=True):
            st.session_state.pending_chat_query = "What are healthy precautions for heart disease?"
            st.rerun()
    with q_col3:
        if st.button("Kidney Precautions", key="qr_kidney", use_container_width=True):
            st.session_state.pending_chat_query = "What precautions help prevent chronic kidney disease?"
            st.rerun()
    with q_col4:
        if st.button("Boost Immunity", key="qr_immunity", use_container_width=True):
            st.session_state.pending_chat_query = "How can I boost my immune system?"
            st.rerun()

    user_input = st.chat_input("Ask a health question...")
    if user_input:
        with st.spinner("🤖 Thinking..."):
            reply_text, is_emerg = process_chat_query(user_input)
            st.session_state.chat_messages.append({'sender': 'user', 'message': user_input, 'is_emergency': False})
            st.session_state.chat_messages.append({'sender': 'bot', 'message': reply_text, 'is_emergency': is_emerg})
            if uid:
                try:
                    ChatHistory.create_message(uid, 'user', user_input)
                    ChatHistory.create_message(uid, 'bot', reply_text)
                except Exception:
                    pass
            st.rerun()


# ==========================================
# PAGE 7: ABOUT PROJECT
# ==========================================
elif nav_choice == "ℹ️ About Project":
    st.markdown("""
    <div class="main-header">
        <h1>About Project — PrediHealth</h1>
        <p>Streamlit-Based Multi-Disease Prediction System for Early Disease Detection Using Machine Learning</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("### 📌 Project Metadata")
    st.write("""
    - **Project Title**: Streamlit-Based Multi-Disease Prediction System for Early Disease Detection Using Machine Learning
    - **Application Name**: PrediHealth
    - **Total Disease Categories**: 26 Diseases (20 General Symptom-Based + 6 Specialized Clinical Diseases)
    - **Dual Diagnostic Architecture**: General Symptom Classification + Specialized Diagnostic Modules
    """)

    st.markdown("---")

    st.markdown("### 🛠️ Technology Stack & Machine Learning Frameworks")
    col_t1, col_t2 = st.columns(2)
    with col_t1:
        st.markdown("""
        - **Programming Language**: Python 3.x
        - **Streamlit**: Multi-Page Dashboard & Clinical ML Interface
        - **Flask**: Backend REST API & Web Application
        - **Random Forest**: 20-Disease Symptom Model (`RandomForestClassifier`, 100 Estimators)
        - **XGBoost**: Extreme Gradient Boosting Classifier
        - **Decision Tree & KNN**: Non-parametric & tree-based classifiers
        """)
    with col_t2:
        st.markdown("""
        - **Gradient Boosting**: Ensemble boosting framework
        - **Joblib**: Model Deserialization & Memory Caching
        - **SQLite**: Persistent Multi-User Database (`database.db`)
        - **ReportLab**: Dynamic Clinical Assessment PDF Document Generation
        - **Matplotlib & Pandas**: Analytics, Feature Importances & Data Processing
        """)

    st.markdown("---")

    st.markdown("### 🔄 2-Level Multi-Disease System Architecture")
    st.markdown("""
    <div style="background-color: #ffffff; border: 1px solid #cbd5e1; border-radius: 10px; padding: 1.25rem; font-family: monospace; font-size: 0.92rem; line-height: 1.6; color: #0f766e;">
    &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;PREDIHEALTH PLATFORM<br/>
    &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;|<br/>
    &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;┌───────────────┴───────────────┐<br/>
    &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;|                               |<br/>
    &nbsp;&nbsp;&nbsp;&nbsp;GENERAL PREDICTION              SPECIALIZED DIAGNOSIS<br/>
    &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;|                               |<br/>
    &nbsp;&nbsp;&nbsp;&nbsp;Existing Model (models/disease_model.pkl)   Six Specialized Models<br/>
    &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;|                               |<br/>
    &nbsp;&nbsp;&nbsp;&nbsp;20 Disease Categories           ┌───────┼───────┐<br/>
    &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;|       |       |<br/>
    &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Heart   Kidney  Breast<br/>
    &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;|       |       |<br/>
    &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Liver   Stroke  Lung Cancer
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    st.markdown("""
    <div class="disclaimer-box">
        <strong>Academic Medical Disclaimer:</strong><br/>
        This project is created strictly for academic research and educational demonstration. 
        It does not provide official medical diagnoses, clinical treatments, or prescriptions. Always consult a licensed healthcare provider for personal health concerns.
    </div>
    """, unsafe_allow_html=True)
