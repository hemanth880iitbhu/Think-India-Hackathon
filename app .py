from flask import Flask, request, jsonify, render_template, redirect, url_for, session
from database import get_db, init_db
from ai_pipeline import (
    extract_and_analyse, summarise_and_insights,
    soap_dict_to_text, patient_friendly_summary,
    rule_based_insight, summarise_chat_transcript,
)
import json
import os
import re
from datetime import datetime

from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import uuid
from flask_socketio import SocketIO, emit, join_room, leave_room, rooms


load_dotenv()


app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET", "apex-health-2026")
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    SESSION_COOKIE_SECURE=os.getenv('SESSION_COOKIE_SECURE', '0') == '1',
    TEMPLATES_AUTO_RELOAD=os.getenv('TEMPLATES_AUTO_RELOAD', '1') == '1',
)
app.jinja_env.auto_reload = app.config['TEMPLATES_AUTO_RELOAD']
if os.getenv('FLASK_ENV') == 'production' and app.secret_key == 'apex-health-2026':
    raise RuntimeError('FLASK_SECRET must be set in production')

UPLOAD_FOLDER = os.path.join(app.static_folder, 'lab_reports')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
ALLOWED_REPORT_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'webp'}

SUPPORTED_LANGUAGES = {
    "en": "English",
    "hi": "Hindi",
    "ta": "Tamil",
    "te": "Telugu",
    "bn": "Bengali",
    "mr": "Marathi",
}

TRANSLATIONS = {
    "en": {
        "pipeline_active": "7-Stage AI Pipeline Active",
        "hero_title_line1": "Unified Lifetime Medical",
        "hero_title_line2": "Intelligence for India.",
        "hero_subtitle": "Structuring fragmented telemedicine data into continuous, longitudinal patient stories across providers and languages.",
        "stage_entity": "ENTITY",
        "stage_entity_desc": "Symptoms, Meds, Dx",
        "stage_soap": "SOAP",
        "stage_soap_desc": "Clinical Structuring",
        "stage_labs": "LABS",
        "stage_labs_desc": "Vitals & Values",
        "stage_delta": "DELTA",
        "stage_delta_desc": "Cross-Visit Changes",
        "stage_drugs": "DRUGS",
        "stage_drugs_desc": "Interaction Checks",
        "stage_trends": "TRENDS",
        "stage_trends_desc": "Pattern Detection",
        "stage_risk": "RISK",
        "stage_risk_desc": "Actionable Flags",
        "new_patient": "+ NEW PATIENT",
        "active_records": "Active Longitudinal Records",
        "registered": "Registered",
        "age": "Age",
        "blood": "Blood",
        "status": "Status",
        "active": "ACTIVE",
        "deceased": "DECEASED",
        "mark_deceased": "MARK DECEASED",
        "mark_active": "MARK ACTIVE",
        "add_visit": "ADD VISIT",
        "view_history": "VIEW HISTORY",
        "new_patient_enrollment": "New Patient Enrollment",
        "language": "Language",
        "patient_registration": "Patient Registration",
        "full_name": "Full Name",
        "gender": "Gender",
        "contact_number": "Contact Number",
        "known_allergies": "Known Allergies",
        "initialize_record": "INITIALIZE LIFETIME RECORD",
        "register_subtitle": "Create a longitudinal medical record profile.",
        "select": "Select...",
        "unknown": "Unknown",
        "male": "Male",
        "female": "Female",
        "other": "Other",
        "years": "Years",
        "doctor_terminal": "Doctor Terminal",
        "exit_dashboard": "Exit to Dashboard",
        "visit_date": "Visit Date",
        "provider_details": "Provider Details",
        "clinical_notes": "Clinical Observation Terminal",
        "start_voice": "START VOICE INPUT",
        "recording": "RECORDING... CLICK TO SAVE",
        "voice_ready": "VOICE ENGINE READY",
        "process_ai": "Process with AI Intelligence",
        "lifetime_visits": "Lifetime Visits",
        "assistive_notice": "Assistive AI Notice",
        "assistive_text": "This system utilizes AI to highlight longitudinal trends for assistive purposes only. It does not replace professional clinical judgment.",
        "notes_placeholder": "Type clinical notes or use the Microphone...",
        "words": "WORDS",
        "threshold": "Threshold",
        "active_context": "Active Context",
        "lifetime_summary": "Lifetime Summary",
        "analysis_pending": "Analysis pending first visit.",
        "prior_risk_alerts": "Prior Risk Alerts",
        "historical_snapshots": "Historical Snapshots",
        "patient_dashboard": "Patient Dashboard",
        "health_score": "Health Score",
        "ai_lifetime_summary": "AI Lifetime Summary",
        "symptom_persistence": "Symptom Persistence",
        "medical_timeline": "Medical Timeline",
        "clinical_soap": "Clinical SOAP",
        "ai_insight": "AI Automated Insight",
        "visit": "Visit",
        "abdm_verified": "ABDM Verified",
        "awaiting_first_visit": "Awaiting AI analysis of first visit...",
        "soap_in_progress": "Clinical SOAP structuring in progress...",
        "translated_summary": "Patient-Friendly AI Summary",
        "translation_notice": "AI Translation Notice",
        "translation_text": "This summary has been simplified and translated by AI for easier understanding. It is an assistive tool, not a diagnostic one. Please refer to your doctor for exact medical advice.",
        "return_dashboard": "RETURN TO DASHBOARD",
        "login_title": "Welcome to Apex Health",
        "login_subtitle": "Secure login for patients and doctors across India.",
        "login_as": "Login As",
        "patient": "Patient",
        "doctor": "Doctor",
        "abha_label": "14-digit ABHA Number",
        "abha_placeholder": "Enter 14-digit ABHA Number",
        "abha_help": "Use your ABHA number as registered in ABDM records.",
        "hpr_label": "HPR ID",
        "hpr_placeholder": "Enter HPR ID",
        "hpr_help": "Enter your Health Professional Registry ID.",
        "password": "Password",
        "password_placeholder": "Enter password",
        "login_with_otp": "Login",
        "otp_note": "By continuing, you agree to secure OTP verification.",
        "signup_now": "Sign Up",
        "signup_cta": "Create Account",
        "no_account": "New here?",
    },
    "hi": {
        "pipeline_active": "7-स्टेज AI पाइपलाइन सक्रिय",
        "hero_title_line1": "एकीकृत लाइफटाइम मेडिकल",
        "hero_title_line2": "इंटेलिजेंस भारत के लिए",
        "hero_subtitle": "टेलीमेडिसिन डेटा को लगातार, दीर्घकालिक मरीज कहानी में बदलना।",
        "stage_entity": "एंटिटी",
        "stage_entity_desc": "लक्षण, दवा, निदान",
        "stage_soap": "SOAP",
        "stage_soap_desc": "क्लिनिकल संरचना",
        "stage_labs": "लैब्स",
        "stage_labs_desc": "वाइटल्स और वैल्यू",
        "stage_delta": "डेल्टा",
        "stage_delta_desc": "विज़िट तुलना",
        "stage_drugs": "दवाएं",
        "stage_drugs_desc": "इंटरैक्शन जांच",
        "stage_trends": "ट्रेंड्स",
        "stage_trends_desc": "पैटर्न पहचान",
        "stage_risk": "रिस्क",
        "stage_risk_desc": "कार्य योग्य अलर्ट",
        "new_patient": "+ नया मरीज",
        "active_records": "सक्रिय दीर्घकालिक रिकॉर्ड",
        "registered": "पंजीकृत",
        "age": "आयु",
        "blood": "ब्लड ग्रुप",
        "status": "स्थिति",
        "active": "सक्रिय",
        "add_visit": "नई विज़िट",
        "view_history": "इतिहास देखें",
        "new_patient_enrollment": "नया मरीज पंजीकरण",
        "language": "भाषा",
        "patient_registration": "मरीज पंजीकरण",
        "full_name": "पूरा नाम",
        "gender": "लिंग",
        "contact_number": "संपर्क नंबर",
        "known_allergies": "ज्ञात एलर्जी",
        "initialize_record": "लाइफटाइम रिकॉर्ड शुरू करें",
        "register_subtitle": "दीर्घकालिक मेडिकल रिकॉर्ड प्रोफाइल बनाएं।",
        "select": "चुनें...",
        "unknown": "अज्ञात",
        "male": "पुरुष",
        "female": "महिला",
        "other": "अन्य",
        "years": "वर्ष",
        "doctor_terminal": "डॉक्टर टर्मिनल",
        "exit_dashboard": "डैशबोर्ड पर लौटें",
        "visit_date": "विज़िट की तारीख",
        "provider_details": "प्रदाता विवरण",
        "clinical_notes": "क्लिनिकल ऑब्जर्वेशन",
        "start_voice": "वॉइस इनपुट शुरू करें",
        "recording": "रिकॉर्डिंग... सहेजने के लिए क्लिक करें",
        "voice_ready": "वॉइस इंजन तैयार",
        "process_ai": "AI से प्रोसेस करें",
        "lifetime_visits": "कुल विज़िट",
        "assistive_notice": "AI सहायक सूचना",
        "assistive_text": "यह सिस्टम केवल सहायक उद्देश्य से AI का उपयोग करता है। यह डॉक्टर के निर्णय का विकल्प नहीं है।",
        "notes_placeholder": "क्लिनिकल नोट्स लिखें या माइक्रोफोन का उपयोग करें...",
        "words": "शब्द",
        "threshold": "न्यूनतम सीमा",
        "active_context": "सक्रिय संदर्भ",
        "lifetime_summary": "लाइफटाइम सारांश",
        "analysis_pending": "पहली विज़िट के बाद विश्लेषण उपलब्ध होगा।",
        "prior_risk_alerts": "पिछले जोखिम अलर्ट",
        "historical_snapshots": "ऐतिहासिक झलक",
        "patient_dashboard": "मरीज डैशबोर्ड",
        "health_score": "हेल्थ स्कोर",
        "ai_lifetime_summary": "AI लाइफटाइम सारांश",
        "symptom_persistence": "लक्षण स्थिरता",
        "medical_timeline": "मेडिकल टाइमलाइन",
        "clinical_soap": "क्लिनिकल SOAP",
        "ai_insight": "AI मेडिकल इनसाइट",
        "visit": "विज़िट",
        "abdm_verified": "ABDM सत्यापित",
        "awaiting_first_visit": "पहली विज़िट के AI विश्लेषण की प्रतीक्षा...",
        "soap_in_progress": "क्लिनिकल SOAP तैयारी जारी है...",
        "translated_summary": "मरीज के लिए सरल AI सारांश",
        "translation_notice": "AI अनुवाद सूचना",
        "translation_text": "यह सारांश AI द्वारा सरल भाषा में अनुवादित है। यह केवल सहायक है, निदान का विकल्प नहीं। सही सलाह के लिए डॉक्टर से संपर्क करें।",
        "return_dashboard": "डैशबोर्ड पर वापस जाएं",
        "login_title": "एपेक्स हेल्थ में आपका स्वागत है",
        "login_subtitle": "भारत में मरीजों और डॉक्टरों के लिए सुरक्षित लॉगिन।",
        "login_as": "किस रूप में लॉगिन",
        "patient": "मरीज",
        "doctor": "डॉक्टर",
        "abha_label": "14-अंकीय ABHA नंबर",
        "abha_placeholder": "14-अंकीय ABHA नंबर दर्ज करें",
        "abha_help": "ABDM रिकॉर्ड में पंजीकृत अपना ABHA नंबर दर्ज करें।",
        "hpr_label": "HPR ID",
        "hpr_placeholder": "HPR ID दर्ज करें",
        "hpr_help": "अपना Health Professional Registry ID दर्ज करें।",
        "password": "पासवर्ड",
        "password_placeholder": "पासवर्ड दर्ज करें",
        "login_with_otp": "लॉगिन",
        "otp_note": "आगे बढ़कर आप सुरक्षित OTP सत्यापन से सहमत हैं।",
        "signup_now": "साइन अप",
        "signup_cta": "अकाउंट बनाएं",
        "no_account": "नए यूज़र?",
    },
    "ta": {
        "pipeline_active": "7-நிலை AI पाइப்லைன் செயலில்",
        "hero_title_line1": "ஒருங்கிணைந்த வாழ்நாள் மருத்துவ",
        "hero_title_line2": "நுண்ணறிவு இந்தியாவிற்கு",
        "hero_subtitle": "சிதறிய டெலிமெடிசின் தரவை தொடர்ச்சியான நோயாளர் வரலாறாக மாற்றுகிறது.",
        "stage_entity": "என்டிட்டி",
        "stage_entity_desc": "அறிகுறிகள், மருந்து, நோயறிதல்",
        "stage_soap": "SOAP",
        "stage_soap_desc": "மருத்துவ கட்டமைப்பு",
        "stage_labs": "லேப்ஸ்",
        "stage_labs_desc": "வைத்தியக் குறியீடுகள்",
        "stage_delta": "டெல்டா",
        "stage_delta_desc": "விஜிட் ஒப்பீடு",
        "stage_drugs": "மருந்துகள்",
        "stage_drugs_desc": "தொடர்பு சரிபார்ப்பு",
        "stage_trends": "போக்குகள்",
        "stage_trends_desc": "முறையியல் கண்டறிதல்",
        "stage_risk": "அபாயம்",
        "stage_risk_desc": "செயல்படுத்தக்கூடிய எச்சரிக்கைகள்",
        "language": "மொழி",
        "new_patient": "+ புதிய நோயாளர்",
        "active_records": "செயலில் உள்ள மருத்துவ பதிவுகள்",
        "registered": "பதிவுசெய்யப்பட்டது",
        "age": "வயது",
        "blood": "இரத்த வகை",
        "status": "நிலை",
        "active": "செயலில்",
        "add_visit": "புதிய விஜிட்",
        "view_history": "வரலாறு",
        "new_patient_enrollment": "புதிய நோயாளர் பதிவு",
        "patient_registration": "நோயாளர் பதிவு",
        "full_name": "முழு பெயர்",
        "gender": "பாலினம்",
        "contact_number": "தொடர்பு எண்",
        "known_allergies": "அலர்ஜிகள்",
        "initialize_record": "வாழ்நாள் பதிவை தொடங்கு",
        "register_subtitle": "நீண்டகால மருத்துவ சுயவிவரத்தை உருவாக்கவும்.",
        "select": "தேர்வு செய்க...",
        "unknown": "தெரியாது",
        "male": "ஆண்",
        "female": "பெண்",
        "other": "மற்றவை",
        "years": "ஆண்டுகள்",
        "exit_dashboard": "டாஷ்போர்டுக்கு திரும்பு",
        "doctor_terminal": "மருத்துவர் டெர்மினல்",
        "visit_date": "விஜிட் தேதி",
        "provider_details": "மருத்துவமனை விவரம்",
        "clinical_notes": "கிளினிக்கல் குறிப்புகள்",
        "start_voice": "வாய்ஸ் தொடங்கு",
        "recording": "பதிவு நடக்கிறது... சேமிக்க கிளிக் செய்க",
        "voice_ready": "வாய்ஸ் என்ஜின் தயார்",
        "process_ai": "AI மூலம் செயலாக்கு",
        "lifetime_visits": "மொத்த விஜிட்கள்",
        "assistive_notice": "AI உதவி குறிப்பு",
        "assistive_text": "இந்த அமைப்பு உதவிக்காக மட்டுமே. மருத்துவர் தீர்மானத்திற்கு மாற்றாகாது.",
        "notes_placeholder": "குறிப்புகளை தட்டச்சு செய்க அல்லது மைக்ரோஃபோன் பயன்படுத்தவும்...",
        "words": "சொற்கள்",
        "threshold": "குறைந்தபட்சம்",
        "active_context": "செயலில் உள்ள சூழல்",
        "lifetime_summary": "வாழ்நாள் சுருக்கம்",
        "analysis_pending": "முதல் விஜிட்டுக்குப் பின் பகுப்பாய்வு வரும்.",
        "prior_risk_alerts": "முன்னைய அபாய எச்சரிக்கைகள்",
        "historical_snapshots": "வரலாற்றுச் சுருக்கம்",
        "health_score": "ஆரோக்கிய மதிப்பெண்",
        "patient_dashboard": "நோயாளர் டாஷ்போர்டு",
        "ai_lifetime_summary": "AI வாழ்நாள் சுருக்கம்",
        "symptom_persistence": "அறிகுறி தொடர்ச்சி",
        "medical_timeline": "மருத்துவ காலவரிசை",
        "clinical_soap": "கிளினிக்கல் SOAP",
        "ai_insight": "AI கருத்து",
        "visit": "விஜிட்",
        "abdm_verified": "ABDM சரிபார்ப்பு",
        "awaiting_first_visit": "முதல் விஜிட் AI பகுப்பாய்வுக்காக காத்திருக்கிறது...",
        "soap_in_progress": "SOAP உருவாக்கம் நடைபெறுகிறது...",
        "translated_summary": "நோயாளிக்கான எளிய AI சுருக்கம்",
        "translation_notice": "AI மொழிபெயர்ப்பு குறிப்பு",
        "translation_text": "இந்த சுருக்கம் AI மூலம் எளிமைப்படுத்தப்பட்டது. இது உதவி கருவி மட்டும்.",
        "return_dashboard": "டாஷ்போர்டுக்கு திரும்பு",
        "login_title": "Apex Health-க்கு வரவேற்கிறோம்",
        "login_subtitle": "இந்தியாவில் நோயாளி மற்றும் மருத்துவர் பாதுகாப்பான நுழைவு.",
        "login_as": "உள்நுழைவு வகை",
        "patient": "நோயாளர்",
        "doctor": "மருத்துவர்",
        "abha_label": "14 இலக்க ABHA எண்",
        "abha_placeholder": "14 இலக்க ABHA எண்ணை உள்ளிடவும்",
        "abha_help": "ABDM பதிவில் உள்ள ABHA எண்ணை பயன்படுத்தவும்.",
        "hpr_label": "HPR ஐடி",
        "hpr_placeholder": "HPR ஐடியை உள்ளிடவும்",
        "hpr_help": "உங்கள் Health Professional Registry ID-ஐ உள்ளிடவும்.",
        "password": "கடவுச்சொல்",
        "password_placeholder": "கடவுச்சொல் உள்ளிடவும்",
        "login_with_otp": "உள்நுழையவும்",
        "otp_note": "தொடர்வதன் மூலம் பாதுகாப்பான OTP சரிபார்ப்பை ஏற்கிறீர்கள்.",
    },
    "te": {
        "pipeline_active": "7-దశల AI పైప్‌లైన్ సక్రియం",
        "hero_title_line1": "ఏకీకృత జీవితకాల వైద్య",
        "hero_title_line2": "ఇంటెలిజెన్స్ భారతదేశానికి",
        "hero_subtitle": "విభిన్న టెలిమెడిసిన్ డేటాను నిరంతర రోగి చరిత్రగా మార్చుతుంది.",
        "stage_entity": "ఎంటిటీ",
        "stage_entity_desc": "లక్షణాలు, మందులు, నిర్ధారణ",
        "stage_soap": "SOAP",
        "stage_soap_desc": "క్లినికల్ నిర్మాణం",
        "stage_labs": "ల్యాబ్స్",
        "stage_labs_desc": "వైటల్స్ & విలువలు",
        "stage_delta": "డెల్టా",
        "stage_delta_desc": "విజిట్ పోలిక",
        "stage_drugs": "మందులు",
        "stage_drugs_desc": "ఇంటరాక్షన్ తనిఖీలు",
        "stage_trends": "ట్రెండ్స్",
        "stage_trends_desc": "ప్యాటర్న్ గుర్తింపు",
        "stage_risk": "రిస్క్",
        "stage_risk_desc": "చర్యలు తీసుకునే అలర్ట్స్",
        "language": "భాష",
        "new_patient": "+ కొత్త రోగి",
        "active_records": "సక్రియ రికార్డులు",
        "registered": "నమోదైనవి",
        "age": "వయసు",
        "blood": "రక్త గ్రూప్",
        "status": "స్థితి",
        "active": "సక్రియం",
        "add_visit": "కొత్త విజిట్",
        "view_history": "చరిత్ర చూడండి",
        "new_patient_enrollment": "కొత్త రోగి నమోదు",
        "patient_registration": "రోగి నమోదు",
        "full_name": "పూర్తి పేరు",
        "gender": "లింగం",
        "contact_number": "సంప్రదింపు నంబర్",
        "known_allergies": "తెలిసిన అలెర్జీలు",
        "initialize_record": "లైఫ్‌టైమ్ రికార్డ్ ప్రారంభించు",
        "register_subtitle": "దీర్ఘకాలిక వైద్య ప్రొఫైల్ సృష్టించండి.",
        "select": "ఎంచుకోండి...",
        "unknown": "తెలియదు",
        "male": "పురుషుడు",
        "female": "స్త్రీ",
        "other": "ఇతర",
        "years": "సంవత్సరాలు",
        "exit_dashboard": "డాష్‌బోర్డ్‌కు వెళ్ళు",
        "doctor_terminal": "డాక్టర్ టెర్మినల్",
        "visit_date": "విజిట్ తేదీ",
        "provider_details": "ప్రదాత వివరాలు",
        "clinical_notes": "క్లినికల్ నోట్స్",
        "start_voice": "వాయిస్ ప్రారంభించు",
        "recording": "రికార్డింగ్... సేవ్ చేయడానికి క్లిక్ చేయండి",
        "voice_ready": "వాయిస్ ఇంజిన్ సిద్ధం",
        "process_ai": "AI తో ప్రాసెస్ చేయండి",
        "lifetime_visits": "మొత్తం విజిట్లు",
        "assistive_notice": "AI సహాయక గమనిక",
        "assistive_text": "ఇది సహాయక సాధనం మాత్రమే; వైద్యుని నిర్ణయానికి బదులు కాదు.",
        "notes_placeholder": "నోట్స్ టైప్ చేయండి లేదా మైక్రోఫోన్ ఉపయోగించండి...",
        "words": "పదాలు",
        "threshold": "కనిష్ఠ పరిమితి",
        "active_context": "సక్రియ సందర్భం",
        "lifetime_summary": "లైఫ్‌టైమ్ సారాంశం",
        "analysis_pending": "మొదటి విజిట్ తర్వాత విశ్లేషణ అందుబాటులో ఉంటుంది.",
        "prior_risk_alerts": "మునుపటి రిస్క్ అలర్ట్స్",
        "historical_snapshots": "చారిత్రక సంగ్రహాలు",
        "health_score": "హెల్త్ స్కోర్",
        "patient_dashboard": "రోగి డాష్‌బోర్డ్",
        "ai_lifetime_summary": "AI లైఫ్‌టైమ్ సారాంశం",
        "symptom_persistence": "లక్షణ స్థిరత్వం",
        "medical_timeline": "మెడికల్ టైమ్‌లైన్",
        "clinical_soap": "క్లినికల్ SOAP",
        "ai_insight": "AI అవగాహన",
        "visit": "విజిట్",
        "abdm_verified": "ABDM ధృవీకరించబడింది",
        "awaiting_first_visit": "మొదటి విజిట్ AI విశ్లేషణ కోసం వేచి ఉంది...",
        "soap_in_progress": "SOAP నిర్మాణం కొనసాగుతోంది...",
        "translated_summary": "రోగికి సులభమైన AI సారాంశం",
        "translation_notice": "AI అనువాద గమనిక",
        "translation_text": "ఈ సారాంశం AI ద్వారా సులభంగా అనువదించబడింది. ఇది సహాయక సాధనం మాత్రమే.",
        "return_dashboard": "డాష్‌బోర్డ్‌కి తిరుగు",
        "login_title": "Apex Health కు స్వాగతం",
        "login_subtitle": "భారతదేశంలోని రోగులు మరియు డాక్టర్ల కోసం సురక్షిత లాగిన్.",
        "login_as": "లాగిన్ విధానం",
        "patient": "రోగి",
        "doctor": "డాక్టర్",
        "abha_label": "14 అంకెల ABHA నంబర్",
        "abha_placeholder": "14 అంకెల ABHA నంబర్ నమోదు చేయండి",
        "abha_help": "ABDM రికార్డుల్లో ఉన్న ABHA నంబర్ ఉపయోగించండి.",
        "hpr_label": "HPR ఐడి",
        "hpr_placeholder": "HPR ఐడి నమోదు చేయండి",
        "hpr_help": "మీ Health Professional Registry ID నమోదు చేయండి.",
        "password": "పాస్‌వర్డ్",
        "password_placeholder": "పాస్‌వర్డ్ నమోదు చేయండి",
        "login_with_otp": "లాగిన్",
        "otp_note": "కొనసాగడం ద్వారా సురక్షిత OTP ధృవీకరణకు మీరు అంగీకరిస్తారు.",
    },
    "bn": {
        "pipeline_active": "7-ধাপ AI পাইপলাইন সক্রিয়",
        "hero_title_line1": "একীভূত লাইফটাইম মেডিক্যাল",
        "hero_title_line2": "ইন্টেলিজেন্স ভারতের জন্য",
        "hero_subtitle": "ছড়িয়ে থাকা টেলিমেডিসিন ডেটাকে ধারাবাহিক রোগী ইতিহাসে রূপ দেয়।",
        "stage_entity": "এন্টিটি",
        "stage_entity_desc": "লক্ষণ, ওষুধ, রোগ নির্ণয়",
        "stage_soap": "SOAP",
        "stage_soap_desc": "ক্লিনিক্যাল গঠন",
        "stage_labs": "ল্যাবস",
        "stage_labs_desc": "ভাইটালস ও মান",
        "stage_delta": "ডেল্টা",
        "stage_delta_desc": "ভিজিট তুলনা",
        "stage_drugs": "ওষুধ",
        "stage_drugs_desc": "ইন্টারঅ্যাকশন পরীক্ষা",
        "stage_trends": "ট্রেন্ডস",
        "stage_trends_desc": "প্যাটার্ন শনাক্তকরণ",
        "stage_risk": "ঝুঁকি",
        "stage_risk_desc": "কার্যকর সতর্কতা",
        "language": "ভাষা",
        "new_patient": "+ নতুন রোগী",
        "active_records": "সক্রিয় রেকর্ড",
        "registered": "নিবন্ধিত",
        "age": "বয়স",
        "blood": "রক্তের গ্রুপ",
        "status": "অবস্থা",
        "active": "সক্রিয়",
        "add_visit": "নতুন ভিজিট",
        "view_history": "ইতিহাস দেখুন",
        "new_patient_enrollment": "নতুন রোগী নিবন্ধন",
        "patient_registration": "রোগী নিবন্ধন",
        "full_name": "পূর্ণ নাম",
        "gender": "লিঙ্গ",
        "contact_number": "যোগাযোগ নম্বর",
        "known_allergies": "অ্যালার্জি",
        "initialize_record": "লাইফটাইম রেকর্ড শুরু করুন",
        "register_subtitle": "দীর্ঘমেয়াদি চিকিৎসা প্রোফাইল তৈরি করুন।",
        "select": "নির্বাচন করুন...",
        "unknown": "অজানা",
        "male": "পুরুষ",
        "female": "মহিলা",
        "other": "অন্যান্য",
        "years": "বছর",
        "exit_dashboard": "ড্যাশবোর্ডে ফিরুন",
        "doctor_terminal": "ডাক্তার টার্মিনাল",
        "visit_date": "ভিজিট তারিখ",
        "provider_details": "প্রদানকারীর বিবরণ",
        "clinical_notes": "ক্লিনিক্যাল নোট",
        "start_voice": "ভয়েস শুরু করুন",
        "recording": "রেকর্ডিং... সংরক্ষণে ক্লিক করুন",
        "voice_ready": "ভয়েস ইঞ্জিন প্রস্তুত",
        "process_ai": "AI দিয়ে প্রসেস করুন",
        "lifetime_visits": "মোট ভিজিট",
        "assistive_notice": "AI সহায়ক নোটিশ",
        "assistive_text": "এটি শুধুমাত্র সহায়ক টুল; চিকিৎসকের সিদ্ধান্তের বিকল্প নয়।",
        "notes_placeholder": "ক্লিনিক্যাল নোট লিখুন বা মাইক্রোফোন ব্যবহার করুন...",
        "words": "শব্দ",
        "threshold": "সীমা",
        "active_context": "সক্রিয় প্রসঙ্গ",
        "lifetime_summary": "লাইফটাইম সারাংশ",
        "analysis_pending": "প্রথম ভিজিটের পর বিশ্লেষণ উপলব্ধ হবে।",
        "prior_risk_alerts": "পূর্বের ঝুঁকি সতর্কতা",
        "historical_snapshots": "ঐতিহাসিক স্ন্যাপশট",
        "health_score": "হেলথ স্কোর",
        "patient_dashboard": "রোগী ড্যাশবোর্ড",
        "ai_lifetime_summary": "AI লাইফটাইম সারাংশ",
        "symptom_persistence": "উপসর্গ স্থায়িত্ব",
        "medical_timeline": "মেডিকেল টাইমলাইন",
        "clinical_soap": "ক্লিনিক্যাল SOAP",
        "ai_insight": "AI ইনসাইট",
        "visit": "ভিজিট",
        "abdm_verified": "ABDM যাচাইকৃত",
        "awaiting_first_visit": "প্রথম ভিজিটের AI বিশ্লেষণের অপেক্ষায়...",
        "soap_in_progress": "SOAP প্রস্তুত হচ্ছে...",
        "translated_summary": "রোগীর জন্য সহজ AI সারাংশ",
        "translation_notice": "AI অনুবাদ নোটিশ",
        "translation_text": "এই সারাংশ AI দ্বারা সহজ ভাষায় অনুবাদ করা হয়েছে। এটি সহায়ক টুল মাত্র।",
        "return_dashboard": "ড্যাশবোর্ডে ফিরে যান",
        "login_title": "Apex Health-এ স্বাগতম",
        "login_subtitle": "ভারতের রোগী ও ডাক্তারের জন্য নিরাপদ লগইন।",
        "login_as": "লগইন ধরন",
        "patient": "রোগী",
        "doctor": "ডাক্তার",
        "abha_label": "14-সংখ্যার ABHA নম্বর",
        "abha_placeholder": "14-সংখ্যার ABHA নম্বর লিখুন",
        "abha_help": "ABDM রেকর্ডে থাকা ABHA নম্বর ব্যবহার করুন।",
        "hpr_label": "HPR আইডি",
        "hpr_placeholder": "HPR আইডি লিখুন",
        "hpr_help": "আপনার Health Professional Registry ID লিখুন।",
        "password": "পাসওয়ার্ড",
        "password_placeholder": "পাসওয়ার্ড লিখুন",
        "login_with_otp": "লগইন",
        "otp_note": "চালিয়ে গেলে আপনি নিরাপদ OTP যাচাইকরণে সম্মত হচ্ছেন।",
    },
    "mr": {
        "pipeline_active": "7-टप्पे AI पाइपलाइन सक्रिय",
        "hero_title_line1": "एकत्रित लाइफटाइम वैद्यकीय",
        "hero_title_line2": "इंटेलिजन्स भारतासाठी",
        "hero_subtitle": "विखुरलेला टेलीमेडिसिन डेटा सतत रुग्ण इतिहासात रूपांतरित करतो.",
        "stage_entity": "एंटिटी",
        "stage_entity_desc": "लक्षणे, औषधे, निदान",
        "stage_soap": "SOAP",
        "stage_soap_desc": "क्लिनिकल संरचना",
        "stage_labs": "लॅब्स",
        "stage_labs_desc": "वाइटल्स आणि मूल्ये",
        "stage_delta": "डेल्टा",
        "stage_delta_desc": "भेट तुलना",
        "stage_drugs": "औषधे",
        "stage_drugs_desc": "परस्परसंवाद तपासणी",
        "stage_trends": "ट्रेंड्स",
        "stage_trends_desc": "पॅटर्न शोध",
        "stage_risk": "जोखीम",
        "stage_risk_desc": "कार्यक्षम अलर्ट",
        "language": "भाषा",
        "new_patient": "+ नवीन रुग्ण",
        "active_records": "सक्रिय नोंदी",
        "registered": "नोंदणीकृत",
        "age": "वय",
        "blood": "रक्तगट",
        "status": "स्थिती",
        "active": "सक्रिय",
        "add_visit": "नवी भेट",
        "view_history": "इतिहास पहा",
        "new_patient_enrollment": "नवीन रुग्ण नोंदणी",
        "patient_registration": "रुग्ण नोंदणी",
        "full_name": "पूर्ण नाव",
        "gender": "लिंग",
        "contact_number": "संपर्क क्रमांक",
        "known_allergies": "ज्ञात ऍलर्जी",
        "initialize_record": "लाईफटाइम रेकॉर्ड सुरू करा",
        "register_subtitle": "दीर्घकालीन वैद्यकीय प्रोफाइल तयार करा.",
        "select": "निवडा...",
        "unknown": "अज्ञात",
        "male": "पुरुष",
        "female": "महिला",
        "other": "इतर",
        "years": "वर्षे",
        "exit_dashboard": "डॅशबोर्डवर परत जा",
        "doctor_terminal": "डॉक्टर टर्मिनल",
        "visit_date": "भेट दिनांक",
        "provider_details": "प्रदाता तपशील",
        "clinical_notes": "क्लिनिकल नोंदी",
        "start_voice": "व्हॉइस सुरू करा",
        "recording": "रेकॉर्डिंग... जतन करण्यासाठी क्लिक करा",
        "voice_ready": "व्हॉइस इंजिन तयार",
        "process_ai": "AI ने प्रक्रिया करा",
        "lifetime_visits": "एकूण भेटी",
        "assistive_notice": "AI सहाय्य सूचना",
        "assistive_text": "ही प्रणाली फक्त सहाय्यासाठी आहे; डॉक्टरांच्या निर्णयाचा पर्याय नाही.",
        "notes_placeholder": "क्लिनिकल नोंदी टाइप करा किंवा मायक्रोफोन वापरा...",
        "words": "शब्द",
        "threshold": "किमान मर्यादा",
        "active_context": "सक्रिय संदर्भ",
        "lifetime_summary": "लाइफटाइम सारांश",
        "analysis_pending": "पहिल्या भेटीनंतर विश्लेषण उपलब्ध होईल.",
        "prior_risk_alerts": "मागील जोखीम सूचना",
        "historical_snapshots": "ऐतिहासिक झलक",
        "health_score": "हेल्थ स्कोर",
        "patient_dashboard": "रुग्ण डॅशबोर्ड",
        "ai_lifetime_summary": "AI लाइफटाइम सारांश",
        "symptom_persistence": "लक्षण सातत्य",
        "medical_timeline": "वैद्यकीय टाइमलाइन",
        "clinical_soap": "क्लिनिकल SOAP",
        "ai_insight": "AI इनसाइट",
        "visit": "भेट",
        "abdm_verified": "ABDM पडताळलेले",
        "awaiting_first_visit": "पहिल्या भेटीच्या AI विश्लेषणाची प्रतीक्षा...",
        "soap_in_progress": "SOAP संरचना सुरू आहे...",
        "translated_summary": "रुग्णासाठी सोपा AI सारांश",
        "translation_notice": "AI भाषांतर सूचना",
        "translation_text": "हा सारांश AI ने सोप्या भाषेत दिला आहे. हे सहाय्यक साधन आहे.",
        "return_dashboard": "डॅशबोर्डवर परत जा",
        "login_title": "Apex Health मध्ये आपले स्वागत आहे",
        "login_subtitle": "भारतभर रुग्ण आणि डॉक्टरांसाठी सुरक्षित लॉगिन.",
        "login_as": "लॉगिन प्रकार",
        "patient": "रुग्ण",
        "doctor": "डॉक्टर",
        "abha_label": "14-अंकी ABHA क्रमांक",
        "abha_placeholder": "14-अंकी ABHA क्रमांक टाका",
        "abha_help": "ABDM नोंदीतील ABHA क्रमांक वापरा.",
        "hpr_label": "HPR आयडी",
        "hpr_placeholder": "HPR आयडी टाका",
        "hpr_help": "आपला Health Professional Registry ID टाका.",
        "password": "पासवर्ड",
        "password_placeholder": "पासवर्ड टाका",
        "login_with_otp": "लॉगिन करा",
        "otp_note": "पुढे गेल्यावर आपण सुरक्षित OTP पडताळणीस संमती देता.",
    },
}


def get_current_lang():
    lang = (session.get("lang") or "en").lower()
    return lang if lang in SUPPORTED_LANGUAGES else "en"


def tr(key):
    lang = get_current_lang()
    lang_table = TRANSLATIONS.get(lang, TRANSLATIONS["en"])
    return lang_table.get(key, TRANSLATIONS["en"].get(key, key))


def normalize_indian_mobile(raw_value):
    raw_value = (raw_value or '').strip()
    if not raw_value:
        return ''

    digits = re.sub(r'\D', '', raw_value)
    if digits.startswith('91') and len(digits) == 12:
        digits = digits[2:]

    if re.fullmatch(r'[6-9]\d{9}', digits):
        return digits
    return None


def allowed_report_file(filename):
    if not filename or '.' not in filename:
        return False
    return filename.rsplit('.', 1)[1].lower() in ALLOWED_REPORT_EXTENSIONS


@app.context_processor
def inject_i18n_context():
    return {
        "t": tr,
        "current_lang": get_current_lang(),
        "supported_languages": SUPPORTED_LANGUAGES,
    }


@app.route('/set-language', methods=['POST'])
def set_language():
    selected = (request.form.get('lang') or 'en').lower()
    session['lang'] = selected if selected in SUPPORTED_LANGUAGES else 'en'
    next_url = request.form.get('next') or request.referrer or url_for('login_page')
    if not isinstance(next_url, str) or not next_url.startswith('/'):
        next_url = url_for('login_page')
    return redirect(next_url)


@app.template_filter('from_json')
def from_json_filter(value):
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return []
    return value or []


def safe_json_load(value, default):
    if value is None:
        return default
    if isinstance(value, (dict, list)):
        return value
    if isinstance(value, str) and not value.strip():
        return default
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError, ValueError):
        return default


def is_local_request():
    remote = (request.remote_addr or '').strip().lower()
    host = (request.host.split(':', 1)[0].strip().lower() if request.host else '')
    return remote in ('127.0.0.1', '::1') and host in ('127.0.0.1', 'localhost')



@app.route('/')
def home():
    return redirect(url_for('login_page'))


@app.route('/dashboard')
def index():
    if session.get('user_role') == 'patient' and session.get('patient_id'):
        return redirect(url_for('patient_view', patient_id=session['patient_id']))
    if session.get('user_role') != 'doctor':
        return redirect(url_for('login_page'))

    abha_error_code = (request.args.get('abha_error') or '').strip().lower()
    abha_lookup_error = ''
    if abha_error_code == 'invalid_format':
        abha_lookup_error = 'ABHA ID must be exactly 14 digits.'
    elif abha_error_code == 'not_found':
        abha_lookup_error = 'No patient found for this ABHA ID.'

    conn = get_db()
    patient_rows = conn.execute('SELECT * FROM patients ORDER BY id').fetchall()
    patients = []
    for row in patient_rows:
        patient = dict(row)
        status = (str(patient.get('patient_status') or 'active')).strip().lower()
        if status not in ('active', 'deceased'):
            status = 'active'
        patient['patient_status'] = status
        patients.append(patient)
    logged_doctor = None
    if session.get('user_role') == 'doctor' and session.get('doctor_id'):
        logged_doctor = conn.execute(
            'SELECT id, name, hpr_id, hospital_name FROM doctors WHERE id=?',
            (session['doctor_id'],)
        ).fetchone()
    conn.close()
    return render_template(
        'index.html',
        patients=patients,
        logged_doctor=logged_doctor,
        abha_lookup_error=abha_lookup_error,
    )


@app.route('/login')
def login_page():
    selected_role = (request.args.get('role') or 'patient').lower()
    if selected_role not in ('patient', 'doctor'):
        selected_role = 'patient'
    return render_template('login.html', login_error="", selected_role=selected_role)


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login_page'))


@app.route('/signup')
def signup_page():
    selected_role = (request.args.get('role') or 'patient').lower()
    if selected_role not in ('patient', 'doctor'):
        selected_role = 'patient'
    return redirect(url_for('register', role=selected_role))


@app.route('/doctor/profile', methods=['GET', 'POST'])
def doctor_profile():
    if session.get('user_role') != 'doctor' or not session.get('doctor_id'):
        return redirect(url_for('login_page'))

    doctor_id = session['doctor_id']
    profile_error = ''
    profile_success = ''

    conn = get_db()
    if request.method == 'POST':
        name = (request.form.get('name') or '').strip()
        hospital_name = (request.form.get('hospital_name') or '').strip() or 'Apex City Clinic'
        specialization = (request.form.get('specialization') or '').strip()
        contact = normalize_indian_mobile(request.form.get('contact'))

        if not name:
            profile_error = 'Doctor name is required.'
        elif contact is None:
            profile_error = 'Contact number must be a valid Indian mobile number (10 digits, optional +91).'
        else:
            conn.execute(
                '''UPDATE doctors
                   SET name=?, hospital_name=?, specialization=?, contact=?
                   WHERE id=?''',
                (name, hospital_name, specialization, contact, doctor_id)
            )
            conn.commit()
            profile_success = 'Profile updated successfully.'
            session['doctor_name'] = name
            session['doctor_hospital'] = hospital_name

    doctor = conn.execute(
        'SELECT id, name, hpr_id, hospital_name, specialization, contact FROM doctors WHERE id=?',
        (doctor_id,)
    ).fetchone()
    conn.close()

    if not doctor:
        return redirect(url_for('login_page'))

    return render_template(
        'doctor_profile.html',
        doctor=doctor,
        profile_error=profile_error,
        profile_success=profile_success,
    )


@app.route('/settings', methods=['GET', 'POST'])
def settings_page():
    role = session.get('user_role')
    if role not in ('patient', 'doctor'):
        return redirect(url_for('login_page'))

    back_url = '/login'
    if role == 'doctor':
        back_url = '/dashboard'
    elif role == 'patient' and session.get('patient_id'):
        back_url = url_for('patient_view', patient_id=session['patient_id'])

    conn = get_db()
    user = None
    identifier_label = ''
    identifier_value = ''

    if role == 'patient' and session.get('patient_id'):
        user = conn.execute(
            'SELECT id, name, abha_id, password_hash FROM patients WHERE id=?',
            (session['patient_id'],)
        ).fetchone()
        identifier_label = 'ABHA ID'
        identifier_value = user['abha_id'] if user else ''
    elif role == 'doctor' and session.get('doctor_id'):
        user = conn.execute(
            'SELECT id, name, hpr_id, password_hash FROM doctors WHERE id=?',
            (session['doctor_id'],)
        ).fetchone()
        identifier_label = 'HPR ID'
        identifier_value = user['hpr_id'] if user else ''

    if not user:
        conn.close()
        return redirect(url_for('login_page'))

    settings_error = ''
    settings_success = ''

    if request.method == 'POST':
        current_password = request.form.get('current_password') or ''
        new_password = request.form.get('new_password') or ''
        confirm_password = request.form.get('confirm_password') or ''

        if not current_password or not new_password or not confirm_password:
            settings_error = 'All password fields are required.'
        elif not check_password_hash(user['password_hash'] or '', current_password):
            settings_error = 'Current password is incorrect.'
        elif len(new_password) < 6:
            settings_error = 'New password must be at least 6 characters.'
        elif new_password != confirm_password:
            settings_error = 'New password and confirm password do not match.'
        else:
            table_name = 'patients' if role == 'patient' else 'doctors'
            conn.execute(
                f'UPDATE {table_name} SET password_hash=? WHERE id=?',
                (generate_password_hash(new_password), user['id'])
            )
            conn.commit()
            settings_success = 'Password updated successfully.'

    conn.close()
    return render_template(
        'settings.html',
        user_role=role,
        user_name=user['name'],
        identifier_label=identifier_label,
        identifier_value=identifier_value,
        settings_error=settings_error,
        settings_success=settings_success,
        back_url=back_url,
    )


@app.route('/upload_lab_report/<int:patient_id>', methods=['POST'])
def upload_lab_report(patient_id):
    if session.get('user_role') != 'doctor' or not session.get('doctor_id'):
        return redirect(url_for('login_page'))

    conn = get_db()
    patient = conn.execute('SELECT id FROM patients WHERE id=?', (patient_id,)).fetchone()
    doctor = conn.execute('SELECT name, hpr_id FROM doctors WHERE id=?', (session['doctor_id'],)).fetchone()

    if not patient or not doctor:
        conn.close()
        return redirect(url_for('doctor_profile'))

    report_file = request.files.get('report_file')
    report_title = (request.form.get('report_title') or 'Lab Report').strip() or 'Lab Report'
    report_type = (request.form.get('report_type') or '').strip()
    consultation_id_raw = (request.form.get('consultation_id') or '').strip()
    consultation_id = int(consultation_id_raw) if consultation_id_raw.isdigit() else None

    if consultation_id is not None:
        consultation = conn.execute(
            'SELECT id FROM consultations WHERE id=? AND patient_id=?',
            (consultation_id, patient_id)
        ).fetchone()
        if not consultation:
            conn.close()
            return redirect(url_for('doctor_view', patient_id=patient_id, upload_error='invalid_consultation'))

    if not report_file or not report_file.filename:
        conn.close()
        return redirect(url_for('doctor_view', patient_id=patient_id, upload_error='missing_file'))

    if not allowed_report_file(report_file.filename):
        conn.close()
        return redirect(url_for('doctor_view', patient_id=patient_id, upload_error='invalid_file'))

    original_name = secure_filename(report_file.filename)
    file_ext = original_name.rsplit('.', 1)[1].lower()
    stored_name = f"{uuid.uuid4().hex}_{original_name}"
    stored_path = os.path.join(UPLOAD_FOLDER, stored_name)

    ext_to_mime = {
        'pdf': 'application/pdf',
        'png': 'image/png',
        'jpg': 'image/jpeg',
        'jpeg': 'image/jpeg',
        'webp': 'image/webp',
    }

    try:
        report_file.save(stored_path)
        conn.execute(
            '''INSERT INTO lab_reports
               (patient_id, consultation_id, report_title, report_type, file_name, file_path, mime_type,
                uploaded_by_doctor_name, uploaded_by_doctor_hpr_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (
                patient_id,
                consultation_id,
                report_title,
                report_type,
                original_name,
                f"lab_reports/{stored_name}",
                ext_to_mime.get(file_ext, 'application/octet-stream'),
                doctor['name'],
                doctor['hpr_id'],
            )
        )
        conn.commit()
    except Exception:
        conn.rollback()
        if os.path.exists(stored_path):
            os.remove(stored_path)
        return redirect(url_for('doctor_view', patient_id=patient_id, upload_error='save_failed'))
    finally:
        conn.close()

    return redirect(url_for('doctor_view', patient_id=patient_id, upload_success='1'))


@app.route('/login', methods=['POST'])
def login_submit():
    role = (request.form.get('role') or 'patient').lower()
    identity = (request.form.get('identity') or '').strip()
    password = request.form.get('password') or ''

    if role not in ('patient', 'doctor'):
        role = 'patient'

    if role == 'patient':
        if not re.fullmatch(r'\d{14}', identity):
            return render_template('login.html', login_error='ABHA ID must be exactly 14 digits.', selected_role='patient')
        if not password:
            return render_template('login.html', login_error='Password is required for patient login.', selected_role='patient')

        conn = get_db()
        patient = conn.execute(
            'SELECT id, password_hash FROM patients WHERE abha_id=?',
            (identity,)
        ).fetchone()
        conn.close()

        if not patient or not check_password_hash(patient['password_hash'] or '', password):
            return render_template('login.html', login_error='Invalid ABHA ID or password.', selected_role='patient')

        session['logged_in'] = True
        session['user_role'] = 'patient'
        session['patient_id'] = patient['id']
        return redirect(url_for('patient_view', patient_id=patient['id']))

    if not identity:
        return render_template('login.html', login_error='HPR ID is required for doctor login.', selected_role='doctor')
    if not password:
        return render_template('login.html', login_error='Password is required for doctor login.', selected_role='doctor')

    conn = get_db()
    doctor = conn.execute(
        'SELECT id, name, hospital_name, password_hash FROM doctors WHERE hpr_id=?',
        (identity,)
    ).fetchone()
    conn.close()

    if not doctor or not check_password_hash(doctor['password_hash'] or '', password):
        return render_template('login.html', login_error='Invalid HPR ID or password.', selected_role='doctor')

    session['logged_in'] = True
    session['user_role'] = 'doctor'
    session['doctor_id'] = doctor['id']
    session['doctor_name'] = doctor['name']
    session['doctor_hospital'] = doctor['hospital_name'] or 'Apex City Clinic'
    return redirect(url_for('index'))



@app.route('/register', methods=['GET', 'POST'])
def register():
    selected_role = (request.args.get('role') or 'patient').lower()
    if selected_role not in ('patient', 'doctor'):
        selected_role = 'patient'
    lock_role = request.args.get('role') in ('patient', 'doctor')

    if request.method == 'POST':
        role = (request.form.get('role') or 'patient').lower()
        if lock_role:
            role = selected_role
        if role not in ('patient', 'doctor'):
            role = 'patient'

        password = request.form.get('password') or ''

        if len(password) < 6:
            return render_template(
                'register.html',
                register_error='Password must be at least 6 characters.',
                selected_role=role,
                lock_role=lock_role,
            )

        if role == 'doctor':
            name = (request.form.get('name') or '').strip()
            hpr_id = (request.form.get('hpr_id') or '').strip()
            hospital_name = (request.form.get('hospital_name') or '').strip() or 'Apex City Clinic'
            specialization = (request.form.get('specialization') or '').strip()
            contact = normalize_indian_mobile(request.form.get('contact'))

            if not name:
                return render_template(
                    'register.html',
                    register_error='Doctor name is required.',
                    selected_role='doctor',
                    lock_role=lock_role,
                )
            if not re.fullmatch(r'[A-Za-z0-9-]{5,30}', hpr_id):
                return render_template(
                    'register.html',
                    register_error='HPR ID must be 5-30 characters (letters, numbers, hyphen).',
                    selected_role='doctor',
                    lock_role=lock_role,
                )
            if contact is None:
                return render_template(
                    'register.html',
                    register_error='Contact number must be a valid Indian mobile number (10 digits, optional +91).',
                    selected_role='doctor',
                    lock_role=lock_role,
                )

            conn = get_db()
            c = conn.cursor()
            exists = c.execute('SELECT id FROM doctors WHERE hpr_id=?', (hpr_id,)).fetchone()
            if exists:
                conn.close()
                return render_template(
                    'register.html',
                    register_error='This HPR ID is already registered.',
                    selected_role='doctor',
                    lock_role=lock_role,
                )

            c.execute(
                     '''INSERT INTO doctors (name,hpr_id,hospital_name,specialization,contact,password_hash)
                         VALUES (?,?,?,?,?,?)''',
                     (name, hpr_id, hospital_name, specialization, contact, generate_password_hash(password))
            )
            conn.commit()
            conn.close()
            return redirect(url_for('login_page', role='doctor'))

        abha_id = (request.form.get('abha_id') or '').strip()
        name = (request.form.get('name') or '').strip()
        age = (request.form.get('age') or '').strip()
        gender = (request.form.get('gender') or '').strip()

        if not name:
            return render_template(
                'register.html',
                register_error='Patient name is required.',
                selected_role='patient',
                lock_role=lock_role,
            )
        if not age.isdigit():
            return render_template(
                'register.html',
                register_error='Patient age is required and must be a number.',
                selected_role='patient',
                lock_role=lock_role,
            )
        if not gender:
            return render_template(
                'register.html',
                register_error='Patient gender is required.',
                selected_role='patient',
                lock_role=lock_role,
            )
        if not re.fullmatch(r'\d{14}', abha_id):
            return render_template(
                'register.html',
                register_error='ABHA ID must be exactly 14 digits.',
                selected_role='patient',
                lock_role=lock_role,
            )

        patient_contact = normalize_indian_mobile(request.form.get('contact'))
        if patient_contact is None:
            return render_template(
                'register.html',
                register_error='Contact number must be a valid Indian mobile number (10 digits, optional +91).',
                selected_role='patient',
                lock_role=lock_role,
            )

        patient_email = (request.form.get('email') or '').strip().lower()
        if patient_email and not re.fullmatch(r'[^@\s]+@[^@\s]+\.[^@\s]+', patient_email):
            return render_template(
                'register.html',
                register_error='Please enter a valid email address.',
                selected_role='patient',
                lock_role=lock_role,
            )

        conn = get_db()
        c = conn.cursor()
        exists = c.execute('SELECT id FROM patients WHERE abha_id=?', (abha_id,)).fetchone()
        if exists:
            conn.close()
            return render_template(
                'register.html',
                register_error='This ABHA ID is already registered.',
                selected_role='patient',
                lock_role=lock_role,
            )

        c.execute(
            'INSERT INTO patients (name,age,gender,blood_group,allergies,contact,email,abha_id,password_hash) VALUES (?,?,?,?,?,?,?,?,?)',
            (
                name,
                age,
                gender,
                request.form.get('blood_group', 'Unknown'),
                request.form.get('allergies', 'None'),
                patient_contact,
                patient_email,
                abha_id,
                generate_password_hash(password),
            )
        )
        pid = c.lastrowid
        c.execute('INSERT INTO lifetime_records (patient_id) VALUES (?)', (pid,))
        conn.commit()
        conn.close()
        return redirect(url_for('patient_view', patient_id=pid))
    return render_template(
        'register.html',
        register_error='',
        selected_role=selected_role,
        lock_role=lock_role,
    )



@app.route('/doctor/open-by-abha', methods=['POST'])
def doctor_open_by_abha():
    if session.get('user_role') != 'doctor':
        return redirect(url_for('login_page'))

    abha_id = (request.form.get('abha_id') or '').strip()
    target = (request.form.get('target') or 'doctor').lower()
    next_url = (request.form.get('next_url') or '').strip()
    if not next_url.startswith('/doctor/') and next_url != '/dashboard':
        next_url = '/dashboard'

    def redirect_with_abha_error(error_code):
        sep = '&' if '?' in next_url else '?'
        return redirect(f"{next_url}{sep}abha_error={error_code}")

    if not re.fullmatch(r'\d{14}', abha_id):
        return redirect_with_abha_error('invalid_format')

    conn = get_db()
    patient = conn.execute('SELECT id FROM patients WHERE abha_id=?', (abha_id,)).fetchone()
    conn.close()

    if not patient:
        return redirect_with_abha_error('not_found')

    if target == 'patient':
        return redirect(url_for('patient_view', patient_id=patient['id']))

    return redirect(url_for('doctor_view', patient_id=patient['id']))


@app.route('/doctor/<int:patient_id>')
def doctor_view(patient_id):
    if session.get('user_role') != 'doctor' or not session.get('doctor_id'):
        return redirect(url_for('login_page'))

    abha_error_code = (request.args.get('abha_error') or '').strip().lower()
    abha_lookup_error = ''
    upload_error = (request.args.get('upload_error') or '').strip().lower()
    upload_success = (request.args.get('upload_success') or '').strip() == '1'
    status_notice = (request.args.get('status_notice') or '').strip().lower()
    if abha_error_code == 'invalid_format':
        abha_lookup_error = 'ABHA ID must be exactly 14 digits.'
    elif abha_error_code == 'not_found':
        abha_lookup_error = 'No patient found for this ABHA ID.'
    upload_error_message = ''
    if upload_error == 'missing_file':
        upload_error_message = 'Please choose a lab report file to upload.'
    elif upload_error == 'invalid_file':
        upload_error_message = 'Unsupported file type. Upload PDF, PNG, JPG, JPEG, or WEBP.'
    status_update_message = ''
    if status_notice == 'updated':
        status_update_message = 'Patient status updated successfully.'
    elif status_notice == 'invalid':
        status_update_message = 'Invalid patient status update request.'

    conn = get_db()
    patient_row = conn.execute('SELECT * FROM patients WHERE id=?', (patient_id,)).fetchone()
    logged_doctor = None
    if session.get('user_role') == 'doctor' and session.get('doctor_id'):
        logged_doctor = conn.execute(
            'SELECT id, name, hpr_id, hospital_name FROM doctors WHERE id=?',
            (session['doctor_id'],)
        ).fetchone()
    history = conn.execute(
        'SELECT * FROM consultations WHERE patient_id=? ORDER BY id DESC LIMIT 5', (patient_id,)
    ).fetchall()
    lab_reports = conn.execute(
        'SELECT * FROM lab_reports WHERE patient_id=? ORDER BY id DESC', (patient_id,)
    ).fetchall()
    lifetime = conn.execute('SELECT * FROM lifetime_records WHERE patient_id=?', (patient_id,)).fetchone()
    conn.close()

    if not patient_row:
        return redirect(url_for('doctor_profile'))

    patient = dict(patient_row)
    patient.setdefault('contact', '')
    patient.setdefault('email', '')
    patient.setdefault('abha_id', '')
    patient.setdefault('allergies', 'None')
    patient_status = (str(patient.get('patient_status') or 'active')).strip().lower()
    if patient_status not in ('active', 'deceased'):
        patient_status = 'active'
    patient['patient_status'] = patient_status

    return render_template(
        'doctor.html',
        patient=patient,
        history=history,
        lab_reports=lab_reports,
        lifetime=dict(lifetime) if lifetime else {},
        logged_doctor=logged_doctor,
        abha_lookup_error=abha_lookup_error,
        upload_error_message=upload_error_message,
        upload_success=upload_success,
        status_update_message=status_update_message,
    )


@app.route('/doctor/patient/<int:patient_id>/status', methods=['POST'])
def doctor_update_patient_status(patient_id):
    if session.get('user_role') != 'doctor' or not session.get('doctor_id'):
        return redirect(url_for('login_page'))

    new_status = (request.form.get('patient_status') or '').strip().lower()
    if new_status not in ('active', 'deceased'):
        return redirect(url_for('doctor_view', patient_id=patient_id, status_notice='invalid'))

    conn = get_db()
    try:
        patient = conn.execute('SELECT id FROM patients WHERE id=?', (patient_id,)).fetchone()
        if not patient:
            return redirect(url_for('doctor_profile'))
        conn.execute('UPDATE patients SET patient_status=? WHERE id=?', (new_status, patient_id))
        conn.commit()
    finally:
        conn.close()

    return redirect(url_for('doctor_view', patient_id=patient_id, status_notice='updated'))


@app.route('/api/chat-summary', methods=['POST'])
def api_chat_summary():
    if session.get('user_role') != 'doctor' or not session.get('doctor_id'):
        return jsonify({"error": "unauthorized"}), 403

    payload = request.get_json(silent=True) or {}
    chat_transcript = (payload.get('chat_transcript') or '').strip()
    if not chat_transcript:
        return jsonify({
            "summary": "",
            "patient_points": [],
            "doctor_actions": [],
            "red_flags": [],
        })

    result = summarise_chat_transcript(chat_transcript)
    return jsonify(result)



@app.route('/submit_note', methods=['POST'])
def submit_note():
    if session.get('user_role') != 'doctor' or not session.get('doctor_id'):
        return redirect(url_for('login_page'))

    patient_id_raw = (request.form.get('patient_id') or '').strip()
    doctor_notes = (request.form.get('doctor_notes') or '').strip()
    chat_transcript = (request.form.get('chat_transcript') or '').strip()
    chat_summary_hint = (request.form.get('chat_summary') or '').strip()

    if not patient_id_raw.isdigit() or (not doctor_notes and not chat_transcript):
        return redirect(url_for('doctor_profile'))

    patient_id = int(patient_id_raw)
    visit_date   = datetime.now().strftime('%d %b %Y, %I:%M %p')
    hospital     = (request.form.get('hospital_name') or 'Apex City Clinic').strip()
    doctor_name  = (request.form.get('doctor_name') or 'Dr. Sharma').strip()
    doctor_hpr_id = (request.form.get('doctor_hpr_id') or '').strip()

    conn = get_db()
    try:
        patient_exists = conn.execute(
            'SELECT id, name, age, gender, blood_group, allergies, contact, abha_id, password_hash FROM patients WHERE id=?',
            (patient_id,)
        ).fetchone()
        if not patient_exists:
            return redirect(url_for('doctor_profile'))

        if session.get('user_role') == 'doctor' and session.get('doctor_id'):
            logged_doctor = conn.execute(
                'SELECT name, hpr_id, hospital_name FROM doctors WHERE id=?',
                (session['doctor_id'],)
            ).fetchone()
            if logged_doctor:
                doctor_name = logged_doctor['name'] or doctor_name
                doctor_hpr_id = logged_doctor['hpr_id'] or doctor_hpr_id
                hospital = logged_doctor['hospital_name'] or hospital

        chat_summary_payload = {
            "summary": "",
            "patient_points": [],
            "doctor_actions": [],
            "red_flags": [],
        }

        chat_summary_text = chat_summary_hint
        if not chat_summary_text and chat_transcript:
            chat_summary_payload = summarise_chat_transcript(chat_transcript)
            chat_summary_text = str(chat_summary_payload.get('summary') or '').strip()

        patient_points = chat_summary_payload.get('patient_points') if isinstance(chat_summary_payload.get('patient_points'), list) else []
        doctor_actions = chat_summary_payload.get('doctor_actions') if isinstance(chat_summary_payload.get('doctor_actions'), list) else []
        red_flags_from_chat = chat_summary_payload.get('red_flags') if isinstance(chat_summary_payload.get('red_flags'), list) else []

        note_parts = []
        if doctor_notes:
            note_parts.append(doctor_notes)
        if chat_summary_text:
            note_parts.append(f"Live chat summary: {chat_summary_text}")
        if patient_points:
            note_parts.append("Patient-reported in chat: " + "; ".join(patient_points[:5]))
        if doctor_actions:
            note_parts.append("Doctor actions in chat: " + "; ".join(doctor_actions[:5]))
        if red_flags_from_chat:
            note_parts.append("Chat red flags: " + "; ".join(red_flags_from_chat[:5]))

        doctor_notes = "\n\n".join(note_parts).strip()
        if not doctor_notes and chat_transcript:
            doctor_notes = chat_transcript[:500]

        duplicate = conn.execute(
            '''SELECT id FROM consultations
               WHERE patient_id=? AND doctor_notes=? AND doctor_hpr_id=?
                 AND created_at >= datetime('now','-20 seconds')
               ORDER BY id DESC LIMIT 1''',
            (patient_id, doctor_notes, doctor_hpr_id)
        ).fetchone()
        if duplicate:
            return redirect(url_for('patient_view', patient_id=patient_id))

        prev = conn.execute(
            'SELECT doctor_notes FROM consultations WHERE patient_id=? ORDER BY id DESC LIMIT 1',
            (patient_id,)
        ).fetchone()
        previous_notes = prev['doctor_notes'] if prev else ""

        analysis = extract_and_analyse(doctor_notes, previous_notes)
        entities = analysis.get('entities', {})
        soap_dict = analysis.get('soap', {})
        drug_interactions = analysis.get('drug_interactions', [])
        visit_delta = analysis.get('visit_delta', {})
        soap_text = soap_dict_to_text(soap_dict)

        clinical_summary = analysis.get('clinical_summary', 'Pending clinical review.')
        insight = {
            "assessment": clinical_summary,
            "recommendation": ["Continue plan outlined in SOAP notes."],
            "red_flags": []
        }
        ai_summary = json.dumps(insight)

        conn.execute(
            '''INSERT INTO consultations
               (patient_id,visit_date,doctor_notes,ai_summary,soap_note,entities,
                    hospital_name,doctor_name,doctor_hpr_id,drug_interactions,visit_delta,
                    chat_transcript,chat_summary)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)''',
            (patient_id, visit_date, doctor_notes, ai_summary, soap_text,
                json.dumps(entities), hospital, doctor_name, doctor_hpr_id,
               json.dumps(drug_interactions), json.dumps(visit_delta),
               chat_transcript, chat_summary_text)
        )
        conn.commit()

        all_cons = [dict(c) for c in conn.execute('SELECT * FROM consultations WHERE patient_id=? ORDER BY id', (patient_id,)).fetchall()]
        all_entities = [safe_json_load(c.get('entities'), {}) for c in all_cons]
        patient_info = dict(patient_exists)

        lifetime = conn.execute('SELECT * FROM lifetime_records WHERE patient_id=?', (patient_id,)).fetchone()
        existing_summary = lifetime['cumulative_summary'] if lifetime else ''

        insights = summarise_and_insights(existing_summary, soap_text, visit_date, all_cons, patient_info, all_entities)

        conn.execute('INSERT OR IGNORE INTO lifetime_records (patient_id) VALUES (?)', (patient_id,))
        conn.execute(
            '''UPDATE lifetime_records SET
               cumulative_summary=?, pattern_data=?, risk_flags=?,
               health_score=?, health_trend=?, medication_timeline=?,
               last_updated=CURRENT_TIMESTAMP
               WHERE patient_id=?''',
            (insights.get('cumulative_summary', ''), json.dumps(insights.get('patterns', {})),
             json.dumps(insights.get('risk_flags', [])), insights.get('health_score', 5),
             insights.get('health_trend', 'stable'), json.dumps(insights.get('medication_timeline', [])),
             patient_id)
        )
        conn.commit()
    finally:
        conn.close()

    return redirect(url_for('patient_view', patient_id=patient_id))



@app.route('/patient/<int:patient_id>')
def patient_view(patient_id):
    if session.get('user_role') == 'patient' and session.get('patient_id') not in (None, patient_id):
        return redirect(url_for('patient_view', patient_id=session['patient_id']))
    if session.get('user_role') not in ('patient', 'doctor'):
        return redirect(url_for('login_page'))

    conn = get_db()
    patient_row = conn.execute('SELECT * FROM patients WHERE id=?', (patient_id,)).fetchone()
    history  = conn.execute('SELECT * FROM consultations WHERE patient_id=? ORDER BY id DESC', (patient_id,)).fetchall()
    lab_reports = conn.execute('SELECT * FROM lab_reports WHERE patient_id=? ORDER BY id DESC', (patient_id,)).fetchall()
    lifetime = conn.execute('SELECT * FROM lifetime_records WHERE patient_id=?', (patient_id,)).fetchone()

    if not patient_row:
        conn.close()
        if session.get('user_role') == 'doctor':
            return redirect(url_for('doctor_profile'))
        return redirect(url_for('login_page'))

    patient = dict(patient_row)
    patient.setdefault('contact', '')
    patient.setdefault('email', '')
    patient.setdefault('abha_id', '')
    patient.setdefault('allergies', 'None')
    patient_status = (str(patient.get('patient_status') or 'active')).strip().lower()
    if patient_status not in ('active', 'deceased'):
        patient_status = 'active'
    patient['patient_status'] = patient_status

    history_parsed = []
    for v in history:
        row = dict(v)
        row['entities_parsed']          = safe_json_load(row.get('entities'), {})
        row['visit_delta_parsed']       = safe_json_load(row.get('visit_delta'), {})
        row['drug_interactions_parsed'] = safe_json_load(row.get('drug_interactions'), [])

        ai_raw = (row.get('ai_summary') or '').strip()
        try:
            parsed = json.loads(ai_raw)
            row['insight_parsed'] = (
                parsed if isinstance(parsed, dict) and 'assessment' in parsed else None
            )
        except (json.JSONDecodeError, ValueError):
            row['insight_parsed'] = None
        history_parsed.append(row)

    pattern_data = safe_json_load(lifetime['pattern_data'], {}) if lifetime else {}
    if not isinstance(pattern_data, dict):
        pattern_data = {}
    risk_flags = safe_json_load(lifetime['risk_flags'], []) if lifetime else []
    if not isinstance(risk_flags, list):
        risk_flags = []
    med_timeline = safe_json_load(lifetime['medication_timeline'], []) if lifetime else []
    if not isinstance(med_timeline, list):
        med_timeline = []

    doctors = []
    if session.get('user_role') == 'patient':
        doctor_rows = conn.execute(
            'SELECT id, name, hpr_id, hospital_name, specialization, contact FROM doctors ORDER BY name'
        ).fetchall()
        doctors = [dict(row) for row in doctor_rows]

    conn.close()
    recurring = pattern_data.get('recurring_symptoms', {})
    if not isinstance(recurring, dict):
        recurring = {}
    chart_labels  = json.dumps(list(recurring.keys()))
    chart_values  = json.dumps(list(recurring.values()))
    cumulative_summary = lifetime['cumulative_summary'] if lifetime else ''

    selected_lang = get_current_lang()
    if cumulative_summary and selected_lang != 'en':
        cumulative_summary = patient_friendly_summary(cumulative_summary, language=selected_lang)

    return render_template('patient.html',
        patient=patient, history=history_parsed,
        lab_reports=lab_reports,
        cumulative_summary=cumulative_summary,
        pattern_data=pattern_data, risk_flags=risk_flags,
        health_score=lifetime['health_score'] if lifetime else 5,
        health_trend=lifetime['health_trend'] if lifetime else 'stable',
        medication_timeline=med_timeline,
        chart_labels=chart_labels, chart_values=chart_values,
        total_visits=len(history_parsed),
        doctors=doctors)



@app.route('/patient/<int:patient_id>/translate/<lang_code>')
def translate_summary(patient_id, lang_code):
    if session.get('user_role') == 'patient' and session.get('patient_id') not in (None, patient_id):
        return redirect(url_for('patient_view', patient_id=session['patient_id']))
    if session.get('user_role') not in ('patient', 'doctor'):
        return redirect(url_for('login_page'))

    conn = get_db()
    lifetime = conn.execute('SELECT cumulative_summary FROM lifetime_records WHERE patient_id=?', (patient_id,)).fetchone()
    patient  = conn.execute('SELECT id, name, age, abha_id FROM patients WHERE id=?', (patient_id,)).fetchone()
    conn.close()

    if not patient:
        if session.get('user_role') == 'doctor':
            return redirect(url_for('doctor_profile'))
        return redirect(url_for('login_page'))

    active_lang = get_current_lang() if lang_code == 'current' else lang_code
    summary    = lifetime['cumulative_summary'] if lifetime else "No history."
    translated = patient_friendly_summary(summary, language=active_lang)

    return render_template('translated_summary.html', patient=patient, hindi_summary=translated, lang_code=active_lang)



@app.route('/add_consultation', methods=['POST'])
def add_consultation_api():
    if session.get('user_role') != 'doctor' and not is_local_request():
        return jsonify({"status": "unauthorized"}), 403

    data = request.get_json(silent=True) or {}
    patient_id_raw = data.get('patient_id')
    visit_date = (data.get('visit_date') or '').strip()
    doctor_notes = (data.get('doctor_notes') or '').strip()

    try:
        patient_id = int(patient_id_raw)
    except (TypeError, ValueError):
        return jsonify({"status": "invalid patient_id"}), 400

    if not visit_date or not doctor_notes:
        return jsonify({"status": "visit_date and doctor_notes are required"}), 400

    conn = get_db()
    try:
        patient = conn.execute('SELECT id FROM patients WHERE id=?', (patient_id,)).fetchone()
        if not patient:
            return jsonify({"status": "patient not found"}), 404

        analysis = extract_and_analyse(doctor_notes, "")
        entities = analysis.get('entities', {})
        soap_text = soap_dict_to_text(analysis.get('soap', {}))
        drug_interactions = analysis.get('drug_interactions', [])
        visit_delta = analysis.get('visit_delta', {})
        clinical_summary = analysis.get('clinical_summary', 'Pending clinical review.')
        imported_insight = {
            "assessment": clinical_summary,
            "recommendation": ["Continue plan outlined in SOAP notes."],
            "red_flags": []
        }
        conn.execute(
               '''INSERT INTO consultations
                  (patient_id,visit_date,doctor_notes,ai_summary,soap_note,entities,drug_interactions,visit_delta,
                   hospital_name,doctor_name,doctor_hpr_id)
                  VALUES (?,?,?,?,?,?,?,?,?,?,?)''',
            (patient_id, visit_date, doctor_notes, json.dumps(imported_insight),
             soap_text, json.dumps(entities), json.dumps(drug_interactions), json.dumps(visit_delta),
             data.get('hospital_name'), data.get('doctor_name'), data.get('doctor_hpr_id', ''))
        )
        conn.commit()
    finally:
        conn.close()
    return jsonify({"status": "success"})


@app.route('/reanalyse/<int:patient_id>', methods=['GET', 'POST'])
def reanalyse(patient_id):
    if session.get('user_role') == 'doctor':
        if request.method != 'POST':
            return jsonify({"status": "method not allowed"}), 405
    elif not is_local_request():
        return jsonify({"status": "unauthorized"}), 403

    conn = get_db()
    try:
        history = conn.execute('SELECT * FROM consultations WHERE patient_id=? ORDER BY id', (patient_id,)).fetchall()
        patient_row = conn.execute('SELECT * FROM patients WHERE id=?', (patient_id,)).fetchone()
        if not patient_row:
            return jsonify({"status": "patient not found"}), 404

        conn.execute('INSERT OR IGNORE INTO lifetime_records (patient_id) VALUES (?)', (patient_id,))

        existing_summary = ""
        for visit in history:
            analysis = extract_and_analyse(visit['doctor_notes'], "")
            soap_text = soap_dict_to_text(analysis.get('soap', {}))
            entities_r = analysis.get('entities', {})
            clinical_summary_r = analysis.get('clinical_summary', '')
            ai_summary_r = json.dumps({
                "assessment": clinical_summary_r or 'Pending clinical review.',
                "recommendation": ["Continue plan outlined in SOAP notes."],
                "red_flags": []
            })

            conn.execute(
                'UPDATE consultations SET entities=?, soap_note=?, ai_summary=? WHERE id=?',
                (json.dumps(analysis.get('entities')), soap_text, ai_summary_r, visit['id'])
            )

            all_cons = [dict(c) for c in conn.execute('SELECT * FROM consultations WHERE patient_id=? ORDER BY id', (patient_id,)).fetchall()]
            patient_info = dict(patient_row)
            all_entities = [safe_json_load(c.get('entities'), {}) for c in all_cons]

            insights = summarise_and_insights(existing_summary, soap_text, visit['visit_date'], all_cons, patient_info, all_entities)
            existing_summary = insights.get('cumulative_summary', '')

            conn.execute(
                '''UPDATE lifetime_records SET cumulative_summary=?, pattern_data=?, risk_flags=?,
                   health_score=?, health_trend=? WHERE patient_id=?''',
                (existing_summary, json.dumps(insights.get('patterns', {})),
                 json.dumps(insights.get('risk_flags', [])),
                 insights.get('health_score', 5), insights.get('health_trend', 'stable'), patient_id)
            )

            conn.commit()

        return jsonify({"status": "reanalysis complete"})
    except Exception as exc:
        conn.rollback()
        return jsonify({"status": "reanalysis failed", "error": str(exc)}), 500
    finally:
        conn.close()


# ============================================================================
# REAL-TIME LIVE CHAT WEBSOCKET HANDLERS (SOCKET.IO)
# ============================================================================

# Global tracking: room_id format = f"consultation_{patient_id}_{doctor_id}"
live_consultations = {}  # {room_id: {doctor: {...}, patient: {...}, messages: []}}

@socketio.on('connect')
def handle_connect():
    """Client connects to WebSocket server"""
    pass

@socketio.on('disconnect')
def handle_disconnect():
    """Client disconnects - clean up consultation room if needed"""
    pass

@socketio.on('join_consultation')
def handle_join_consultation(data):
    """
    Doctor or Patient joins a consultation room
    data = {
        patient_id: int,
        user_role: 'doctor' or 'patient',
        user_id: doctor_id or patient_id
    }
    """
    try:
        patient_id = data.get('patient_id')
        doctor_id = data.get('doctor_id')
        user_role = data.get('user_role')
        user_id = data.get('user_id')
        user_name = data.get('user_name') or ''
        
        if not all([patient_id, doctor_id, user_role, user_id]):
            emit('error', {'message': 'Missing required fields'})
            return
        
        # Generate room ID using both patient and doctor
        room_id = f"consultation_{patient_id}_{doctor_id}"
        
        # Join the room
        join_room(room_id)
        
        # Initialize room if first user
        if room_id not in live_consultations:
            live_consultations[room_id] = {
                'doctor': None,
                'patient': None,
                'messages': [],
                'created_at': datetime.now().isoformat()
            }
        
        # Track user in room
        if user_role == 'doctor':
            live_consultations[room_id]['doctor'] = {
                'id': user_id,
                'sid': request.sid,
                'name': user_name or session.get('doctor_name', 'Dr. Unknown')
            }
        elif user_role == 'patient':
            live_consultations[room_id]['patient'] = {
                'id': user_id,
                'sid': request.sid,
                'name': user_name
            }
        
        # Notify both users that someone joined
        emit('user_joined', {
            'user_role': user_role,
            'timestamp': datetime.now().strftime('%I:%M %p'),
            'room_id': room_id
        }, room=room_id)
        
        # Send current message history to the joining user
        emit('message_history', {
            'messages': live_consultations[room_id]['messages']
        })
        
    except Exception as e:
        emit('error', {'message': f'Failed to join: {str(e)}'})

@socketio.on('send_message')
def handle_send_message(data):
    """
    Doctor or Patient sends a message in real-time
    data = {
        patient_id: int,
        doctor_id: int,
        message: str,
        user_role: 'doctor' or 'patient',
        user_name: str
    }
    """
    try:
        patient_id = data.get('patient_id')
        doctor_id = data.get('doctor_id')
        message_text = (data.get('message') or '').strip()
        user_role = data.get('user_role', 'doctor')
        user_name = data.get('user_name', 'Unknown')
        
        if not patient_id or not doctor_id or not message_text:
            emit('error', {'message': 'Empty message or missing patient/doctor ID'})
            return
        
        room_id = f"consultation_{patient_id}_{doctor_id}"
        timestamp = datetime.now().strftime('%I:%M %p')
        
        # Create message object
        msg_obj = {
            'role': user_role,
            'text': message_text,
            'time': timestamp,
            'user_name': user_name,
            'timestamp_iso': datetime.now().isoformat()
        }
        
        # Store message in room
        if room_id in live_consultations:
            live_consultations[room_id]['messages'].append(msg_obj)
        
        # Broadcast message to BOTH users in the room
        emit('new_message', msg_obj, room=room_id)
        
    except Exception as e:
        emit('error', {'message': f'Failed to send message: {str(e)}'})

@socketio.on('end_consultation')
def handle_end_consultation(data):
    """
    Doctor ends consultation and signals readiness to finalize
    data = {
        patient_id: int,
        doctor_id: int,
        generate_summary: bool
    }
    """
    try:
        patient_id = data.get('patient_id')
        doctor_id = data.get('doctor_id')
        generate_summary = data.get('generate_summary', True)
        
        if not patient_id or not doctor_id:
            emit('error', {'message': 'Missing patient or doctor ID'})
            return
        
        room_id = f"consultation_{patient_id}_{doctor_id}"
        
        if room_id not in live_consultations:
            emit('error', {'message': 'Consultation room not found'})
            return
        
        # Get all messages
        messages = live_consultations[room_id]['messages']
        
        # Build transcript
        transcript = "\n".join([
            f"{msg['role'].capitalize()} ({msg['time']}): {msg['text']}"
            for msg in messages
        ])
        
        # Return transcript to clients
        emit('consultation_ended', {
            'transcript': transcript,
            'message_count': len(messages),
            'should_summarize': generate_summary
        }, room=room_id)
        
    except Exception as e:
        emit('error', {'message': f'Failed to end consultation: {str(e)}'})

@socketio.on('typing')
def handle_typing(data):
    """
    Broadcast typing indicator
    data = {
        patient_id: int,
        doctor_id: int,
        user_name: str,
        is_typing: bool
    }
    """
    try:
        patient_id = data.get('patient_id')
        doctor_id = data.get('doctor_id')
        user_name = data.get('user_name', 'User')
        is_typing = data.get('is_typing', True)
        
        if not patient_id or not doctor_id:
            emit('error', {'message': 'Missing patient or doctor ID'})
            return
        
        room_id = f"consultation_{patient_id}_{doctor_id}"
        
        if is_typing:
            emit('user_typing', {
                'user_name': user_name,
                'is_typing': True
            }, room=room_id, skip_sid=request.sid)  # Don't send to typing user
        else:
            emit('user_typing', {
                'user_name': user_name,
                'is_typing': False
            }, room=room_id, skip_sid=request.sid)
            
    except Exception as e:
        emit('error', {'message': f'Typing update failed: {str(e)}'})

@socketio.on('leave_consultation')
def handle_leave_consultation(data):
    """
    User leaves the consultation room
    data = {
        patient_id: int,
        doctor_id: int,
        user_role: 'doctor' or 'patient'
    }
    """
    try:
        patient_id = data.get('patient_id')
        doctor_id = data.get('doctor_id')
        user_role = data.get('user_role', 'doctor')
        
        if not patient_id or not doctor_id:
            emit('error', {'message': 'Missing patient or doctor ID'})
            return
        
        room_id = f"consultation_{patient_id}_{doctor_id}"
        
        leave_room(room_id)
        
        emit('user_left', {
            'user_role': user_role,
            'timestamp': datetime.now().strftime('%I:%M %p')
        }, room=room_id)
        
        # Clean up room if empty
        if room_id in live_consultations:
            consultation = live_consultations[room_id]
            if (not consultation['doctor'] or consultation['doctor']['sid'] == request.sid) and \
               (not consultation['patient'] or consultation['patient']['sid'] == request.sid):
                # Both users have left
                del live_consultations[room_id]
                
    except Exception as e:
        emit('error', {'message': f'Failed to leave: {str(e)}'})


if __name__ == '__main__':
    init_db()
    debug_mode = os.getenv('FLASK_DEBUG', '0') == '1'
    port = int(os.getenv('PORT', '5000'))
    print("🚀 ApexHealth Server starting with real-time chat via Socket.IO...")
    socketio.run(app, debug=debug_mode, port=port, host='0.0.0.0', allow_unsafe_werkzeug=True)