import re
import json
import os
import time
from dotenv import load_dotenv
from litellm import completion
import litellm

load_dotenv()



PROVIDER_CONFIGS = [
    {
        "name": "github",
        "model": "github/gpt-4o-mini",
        "api_key_envs": ["GITHUB_API_KEY", "GITHUB_API_KEY_BACKUP"],
        "priority": 1,
    },
    {
        "name": "gemini",
        "model": "gemini/gemini-2.0-flash",
        "api_key_env": "GEMINI_API_KEY",
        "priority": 2,
    },
    {
        "name": "groq",
        "model": "groq/llama-3.3-70b-versatile",
        "api_key_env": "GROQ_API_KEY",
        "priority": 3,
    }
]





_SYMPTOM_PATTERNS = {
    'abdominal_pain': [
        r'abdominal pain', r'stomach pain', r'पेट.{0,10}दर्द',
        r'epigastric', r'upper abdominal', r'belly ache',
    ],
    'nausea': [r'nausea', r'nauseous', r'जी मिचला', r'मतली'],
    'vomiting': [r'vomit', r'उल्टी', r'emesis'],
    'fever': [r'\bfever\b', r'\bबुखार\b', r'pyrexia'],
    'headache': [r'headache', r'सिरदर्द', r'head ache'],
    'chest_pain': [r'chest pain', r'सीने में दर्द', r'chest tightness', r'angina'],
    'breathlessness': [r'breathless', r'dyspnea', r'सांस.{0,10}तकलीफ', r'shortness of breath'],
    'diarrhea': [r'diarrhea', r'diarrhoea', r'दस्त', r'loose stools'],
    'cough': [r'\bcough\b', r'खांसी'],
    'tenderness': [
        r'tenderness', r'\btender\b', r'pain on palpation',
        r'छूने पर दर्द', r'दर्द बढ़', r'tenderness present',
    ],
}

_NO_FEVER_PATTERNS = [
    r'no fever', r'afebrile', r'बुखार नहीं', r'fever absent',
    r'no temperature', r'apyrexial',
]

_ANTACID_PATTERNS = [
    r'antacid', r'omeprazole', r'pantoprazole', r'ranitidine',
    r'rabeprazole', r'esomeprazole', r'proton pump',
]

_GI_TERMS = [
    r'gastritis', r'gastric', r'peptic', r'dyspepsia', r'acidity', r'gerd',
]

_RED_FLAG_RULES = [
    (r'chest pain|सीने में दर्द|chest tightness|angina',
     'Chest pain — cardiac/pulmonary cause must be excluded'),
    (r'breathless|dyspnea|सांस.{0,10}तकलीफ|shortness of breath',
     'Breathlessness detected'),
    (r'blood in stool|bloody stool|haematochezia|मल में खून',
     'Blood in stool'),
    (r'haematemesis|blood.{0,8}vomit|खून की उल्टी',
     'Haematemesis (blood in vomit)'),
    (r'unconscious|unresponsive|बेहोश|syncope|faint',
     'Altered consciousness'),
    (r'rebound tenderness|rigid abdomen|board.?like|पेट कड़ा',
     'Peritoneal signs — surgical emergency possible'),
    (r'seizure|convulsion|दौरा',
     'Seizure activity'),
    (r'jaundice|पीलिया',
     'Jaundice — hepatic/biliary evaluation needed'),
]


def _match_any(patterns, text):
    """Return True if any pattern matches (case-insensitive)."""
    return any(re.search(p, text, re.IGNORECASE) for p in patterns)


def rule_based_insight(doctor_notes, entities=None, clinical_summary=""):
    """
    Deterministic rule-based clinical insight generator.

    Parses Hindi/English mixed clinical notes and returns a structured dict:
        {
            "assessment":     str,
            "risk_level":     "Low" | "Medium" | "High",
            "red_flags":      list[str],
            "recommendation": list[str],
            "rationale":      str,
        }

    Safe fallback is returned when note text is absent or too short to parse.
    Never emits placeholder strings ("See SOAP note", "Imported", etc.).
    """
    if not doctor_notes or not str(doctor_notes).strip():
        return {
            "assessment": "Insufficient data to generate insight.",
            "risk_level": "Low",
            "red_flags": [],
            "recommendation": ["Add clinical notes to enable automated insight."],
            "rationale": "No note text provided.",
        }

    if entities is None:
        entities = {}

    note_l = doctor_notes.lower()


    detected = {k: _match_any(v, note_l) for k, v in _SYMPTOM_PATTERNS.items()}
    no_fever  = _match_any(_NO_FEVER_PATTERNS, note_l)
    has_fever = detected['fever'] and not no_fever
    has_antacid = _match_any(_ANTACID_PATTERNS, note_l)
    has_gi = _match_any(_GI_TERMS, note_l) or has_antacid


    bp_m = re.search(r'bp[\s:]*(\d{2,3})\s*/\s*(\d{2,3})', note_l)
    bp_sys = int(bp_m.group(1)) if bp_m else None
    bp_dia = int(bp_m.group(2)) if bp_m else None


    pulse_m = re.search(r'pulse[\s:]*(\d{2,3})', note_l)
    pulse = int(pulse_m.group(1)) if pulse_m else None


    red_flags = []
    for pattern, flag_text in _RED_FLAG_RULES:
        if re.search(pattern, note_l, re.IGNORECASE):
            red_flags.append(flag_text)

    if bp_sys is not None:
        bp_str = f"{bp_sys}/{bp_dia}" if bp_dia is not None else str(bp_sys)
        if bp_sys >= 160 or (bp_dia is not None and bp_dia >= 100):
            red_flags.append(f"Elevated BP ({bp_str}) — hypertensive range")
        elif bp_sys < 90:
            red_flags.append(f"Low BP ({bp_str}) — hypotension")

    if pulse is not None and (pulse > 120 or pulse < 50):
        red_flags.append(f"Abnormal pulse ({pulse}/min)")


    if red_flags:
        risk_level = "High"
    elif has_fever and detected['abdominal_pain']:
        risk_level = "Medium"
    elif detected['abdominal_pain'] and detected['tenderness']:
        risk_level = "Medium"
    elif detected['vomiting'] or has_fever:
        risk_level = "Medium"
    else:
        risk_level = "Low"


    symptoms_list  = [s for s in (entities.get('symptoms') or []) if s]
    diagnoses_list = [d for d in (entities.get('diagnoses') or []) if d]

    _bad_summaries = {"Manual review of notes recommended.", ""}
    if clinical_summary and clinical_summary not in _bad_summaries:
        assessment = clinical_summary
    elif diagnoses_list:
        assessment = f"Probable: {', '.join(diagnoses_list[:2])}."
        if symptoms_list:
            assessment += f" Presenting with {', '.join(symptoms_list[:3])}."
    elif detected['abdominal_pain'] and (detected['nausea'] or has_antacid or has_gi):
        assessment = "Acute gastritis / dyspepsia suspected."
        if no_fever:
            assessment += " Afebrile with stable vitals suggests non-infectious GI cause."
        if detected['tenderness']:
            assessment += " Tenderness on palpation noted."
    elif detected['chest_pain']:
        assessment = "Chest pain — cardiac and pulmonary causes must be excluded urgently."
    elif detected['breathlessness']:
        assessment = "Breathlessness — evaluate for respiratory or cardiac etiology."
    elif symptoms_list:
        assessment = f"Presenting complaints: {', '.join(symptoms_list[:3])}."
    else:
        assessment = (
            "No specific diagnosis determinable from available data — "
            "manual clinical review recommended."
        )


    recommendation = []
    if risk_level == "High":
        recommendation.append("Urgent clinical review — consider immediate escalation.")
        if detected['chest_pain']:
            recommendation.append("ECG and troponin indicated.")
        elif detected['abdominal_pain'] and detected['tenderness']:
            recommendation.append(
                "Surgical consultation if rebound tenderness or rigidity present."
            )
    else:
        if detected['abdominal_pain']:
            recommendation.append("Monitor for worsening pain, fever, or vomiting.")
            if detected['tenderness']:
                recommendation.append(
                    "Follow-up in 24–48 h if tenderness persists or worsens."
                )
            if has_antacid:
                recommendation.append("Continue prescribed antacid; reassess in 3–5 days.")
        if has_fever:
            recommendation.append(
                "Monitor temperature; investigate infectious source if fever persists > 48 h."
            )
        if not recommendation:
            recommendation.append("Follow up as clinically indicated.")


    rationale_parts = []
    if no_fever:
        rationale_parts.append("afebrile")
    if bp_sys and 90 <= bp_sys <= 140:
        bp_str = f"{bp_sys}/{bp_dia}" if bp_dia is not None else str(bp_sys)
        rationale_parts.append(f"BP {bp_str} (stable)")
    if pulse and 50 <= pulse <= 100:
        rationale_parts.append(f"pulse {pulse}/min (normal range)")
    if detected['tenderness']:
        rationale_parts.append("tenderness on palpation")

    rationale = (
        "Basis: " + ", ".join(rationale_parts) + "."
        if rationale_parts
        else "Based on available clinical data in note."
    )

    return {
        "assessment": assessment,
        "risk_level": risk_level,
        "red_flags": red_flags,
        "recommendation": recommendation,
        "rationale": rationale,
    }


def _get_available_providers():
    """Get list of available providers based on API keys."""
    available = []
    for config in sorted(PROVIDER_CONFIGS, key=lambda x: x["priority"]):
        key_envs = config.get("api_key_envs")
        if isinstance(key_envs, list) and key_envs:
            for idx, env_name in enumerate(key_envs, start=1):
                if os.getenv(env_name):
                    provider_copy = dict(config)
                    provider_copy["api_key_env"] = env_name
                    provider_copy["key_slot"] = idx
                    available.append(provider_copy)
            continue

        api_key_env = config.get("api_key_env")
        if api_key_env and os.getenv(api_key_env):
            provider_copy = dict(config)
            provider_copy["key_slot"] = 1
            available.append(provider_copy)
    return available


def _call(prompt, expect_json=True, max_tokens=1024, temperature=0.2):
    """
    Call LLM with automatic provider fallback.
    Tries providers in priority order until one succeeds.
    """
    available_providers = _get_available_providers()

    if not available_providers:
        print("[AI] No API keys found. Set at least one: GITHUB_API_KEY, GITHUB_API_KEY_BACKUP, GEMINI_API_KEY, or GROQ_API_KEY")
        return "AI_ERROR"

    last_error = None

    for provider_config in available_providers:
        provider_name = provider_config["name"]
        model = provider_config["model"]
        api_key = os.getenv(provider_config["api_key_env"])
        key_slot = provider_config.get("key_slot", 1)
        provider_label = f"{provider_name} (key {key_slot})"


        for attempt in range(2):
            try:

                kwargs = {
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                    "timeout": 45,
                    "api_key": api_key,
                }


                if provider_name == "openrouter":

                    if "extra_headers" in provider_config:
                        kwargs["extra_headers"] = provider_config["extra_headers"]


                response = completion(**kwargs)


                choices = getattr(response, 'choices', None) or []
                if not choices:
                    raise ValueError("Empty LLM response choices")

                message = getattr(choices[0], 'message', None)
                content = getattr(message, 'content', None)
                if not isinstance(content, str) or not content.strip():
                    raise ValueError("Empty LLM response content")

                print(f"[AI] ✓ Successfully used provider: {provider_label}")
                return content

            except Exception as e:
                last_error = e
                error_msg = str(e).lower()


                is_quota_exceeded = any(x in error_msg for x in [
                    "quota", "billing", "resource_exhausted"
                ])
                if provider_name == "gemini" and is_quota_exceeded:
                    print(f"[AI] {provider_label} quota exhausted, skipping retry and falling back...")
                    break


                is_retryable = any(x in error_msg for x in [
                    "rate limit", "429", "503", "502", "500", "timeout", "connection"
                ])

                if is_retryable and attempt < 1:
                    print(f"[AI] {provider_label} temporary error, retrying in 5s.... ({attempt + 1}/2)")
                    time.sleep(5)
                    continue
                else:
                    print(f"[AI] {provider_label} failed: {str(e)[:100]}")
                    break


    print(f"[AI] All providers failed. Last error: {last_error}")
    return "AI_ERROR"


def _parse_json(text):
    """Parse JSON from LLM response, handling various formats."""
    if not text or text.startswith("AI_ERROR"):
        return None

    text = text.strip()


    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.IGNORECASE | re.MULTILINE)


    text = re.sub(r",\s*([}\]])", r"\1", text)

    try:
        return json.loads(text)
    except Exception:
        pass


    start_positions = [i for i, ch in enumerate(text) if ch == "{"]
    for start in start_positions:
        depth = 0
        for idx in range(start, len(text)):
            ch = text[idx]
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    candidate = text[start:idx + 1]
                    try:
                        return json.loads(candidate)
                    except Exception:
                        break

    print("[AI] JSON parse failed: could not find a valid JSON object")
    print(f"[AI] Raw text (first 200 chars): {text[:200]}")
    return None


def _build_fallback_summary(doctor_notes):
    """Generate a concise clinical-style summary when AI output is unavailable."""
    note = re.sub(r"\s+", " ", (doctor_notes or "").strip())
    if not note:
        return "Clinical details captured; manual review recommended."
    if len(note) > 160:
        note = note[:160].rstrip() + "..."
    return note[0].upper() + note[1:] if note else "Clinical details captured; manual review recommended."


def summarise_chat_transcript(chat_transcript):
    """Summarize doctor-patient chat into a structured clinical snapshot."""
    transcript = re.sub(r"\s+", " ", (chat_transcript or "").strip())
    if not transcript:
        return {
            "summary": "No live consultation chat was recorded.",
            "patient_points": [],
            "doctor_actions": [],
            "red_flags": [],
        }

    prompt = (
        "You are a clinical documentation assistant. "
        "Summarize this doctor-patient chat into concise medical notes. "
        "Return ONLY valid JSON (no markdown): "
        '{"summary":"",'
        '"patient_points":[""],'
        '"doctor_actions":[""],'
        '"red_flags":[""]}'
        "\n\n"
        "Rules:\n"
        "1) summary must be 1-2 short clinical sentences.\n"
        "2) patient_points should contain patient-reported symptoms/history only.\n"
        "3) doctor_actions should contain doctor advice/investigation/plan only.\n"
        "4) red_flags should only include urgent warning signs if clearly present.\n"
        "5) Do not invent facts.\n\n"
        "CHAT TRANSCRIPT:\n" + transcript
    )

    parsed = _parse_json(_call(prompt, max_tokens=900))

    fallback_summary = _build_fallback_summary(transcript)
    fallback = {
        "summary": fallback_summary,
        "patient_points": [],
        "doctor_actions": [],
        "red_flags": [],
    }

    if not isinstance(parsed, dict):
        return fallback

    summary = str(parsed.get("summary") or "").strip()
    if not summary:
        summary = fallback_summary

    patient_points = parsed.get("patient_points")
    if not isinstance(patient_points, list):
        patient_points = []
    patient_points = [str(item).strip() for item in patient_points if str(item).strip()][:5]

    doctor_actions = parsed.get("doctor_actions")
    if not isinstance(doctor_actions, list):
        doctor_actions = []
    doctor_actions = [str(item).strip() for item in doctor_actions if str(item).strip()][:5]

    red_flags = parsed.get("red_flags")
    if not isinstance(red_flags, list):
        red_flags = []
    red_flags = [str(item).strip() for item in red_flags if str(item).strip()][:5]

    return {
        "summary": summary,
        "patient_points": patient_points,
        "doctor_actions": doctor_actions,
        "red_flags": red_flags,
    }


def extract_and_analyse(doctor_notes, previous_notes=""):
    """Extract structured medical data from clinical notes."""
    if previous_notes:
        delta_instruction = (
            f"\nPREVIOUS VISIT:\n{previous_notes}\n\n"
            "Compare current vs previous for 'visit_delta': improved, worsened, new_findings, resolved."
        )
    else:
        delta_instruction = "\nFirst visit. Keep visit_delta empty []."

    prompt = (
        "You are a Senior Medical AI. Analyze this clinical note (Hindi/English/Mixed).\n\n"
        "CLINICAL NOTE:\n" + doctor_notes + "\n" + delta_instruction + "\n\n"
        "CRITICAL: For the 'clinical_summary' field, you MUST write a 1-sentence medical assessment "
        "summarizing the patient's condition and status. NEVER write 'See SOAP note' or refer the reader "
        "elsewhere. Write the actual clinical insight directly.\n\n"
        "Return ONLY valid JSON, no extra text, no markdown fences:\n"
        '{"clinical_summary":"Acute epigastric pain with nausea; normal vitals suggest stable Gastritis.",'
        '"entities":{"symptoms":[],"diagnoses":[],"medications":[{"name":"","dose":"","frequency":""}],'
        '"vitals":{"bp":null,"temperature":null,"spo2":null,"weight":null,"pulse":null},'
        '"lab_results":{"hba1c":null,"fasting_sugar":null,"creatinine":null,"ldl":null},"follow_up":""},'
        '"soap":{"subjective":"","objective":"","assessment":"","plan":""},'
        '"drug_interactions":[],"visit_delta":{"improved":[],"worsened":[],"new_findings":[],"resolved":[]}}'
    )

    parsed = _parse_json(_call(prompt, max_tokens=1500))


    fallback_summary = _build_fallback_summary(doctor_notes)
    fallback = {
        "clinical_summary": fallback_summary,
        "entities": {
            "symptoms": [], "diagnoses": [], "medications": [],
            "vitals": {}, "lab_results": {}, "follow_up": ""
        },
        "soap": {"subjective": doctor_notes[:150], "objective": "", "assessment": "", "plan": ""},
        "drug_interactions": [],
        "visit_delta": {"improved": [], "worsened": [], "new_findings": [], "resolved": []}
    }

    if not isinstance(parsed, dict):
        return fallback


    model_summary = str(parsed.get("clinical_summary", "")).strip()
    note_norm = re.sub(r"\s+", " ", (doctor_notes or "").strip()).lower()
    summary_norm = re.sub(r"\s+", " ", model_summary).lower()
    if not model_summary or summary_norm == note_norm:
        parsed["clinical_summary"] = fallback["clinical_summary"]

    entities_raw = parsed.get("entities") if isinstance(parsed.get("entities"), dict) else {}
    parsed["entities"] = {
        "symptoms": entities_raw.get("symptoms") if isinstance(entities_raw.get("symptoms"), list) else [],
        "diagnoses": entities_raw.get("diagnoses") if isinstance(entities_raw.get("diagnoses"), list) else [],
        "medications": entities_raw.get("medications") if isinstance(entities_raw.get("medications"), list) else [],
        "vitals": entities_raw.get("vitals") if isinstance(entities_raw.get("vitals"), dict) else {},
        "lab_results": entities_raw.get("lab_results") if isinstance(entities_raw.get("lab_results"), dict) else {},
        "follow_up": str(entities_raw.get("follow_up") or "")
    }

    soap_raw = parsed.get("soap") if isinstance(parsed.get("soap"), dict) else {}
    parsed["soap"] = {
        "subjective": str(soap_raw.get("subjective") or ""),
        "objective": str(soap_raw.get("objective") or ""),
        "assessment": str(soap_raw.get("assessment") or ""),
        "plan": str(soap_raw.get("plan") or "")
    }

    visit_delta_raw = parsed.get("visit_delta") if isinstance(parsed.get("visit_delta"), dict) else {}
    parsed["visit_delta"] = {
        "improved": visit_delta_raw.get("improved") if isinstance(visit_delta_raw.get("improved"), list) else [],
        "worsened": visit_delta_raw.get("worsened") if isinstance(visit_delta_raw.get("worsened"), list) else [],
        "new_findings": visit_delta_raw.get("new_findings") if isinstance(visit_delta_raw.get("new_findings"), list) else [],
        "resolved": visit_delta_raw.get("resolved") if isinstance(visit_delta_raw.get("resolved"), list) else []
    }

    parsed["drug_interactions"] = parsed.get("drug_interactions") if isinstance(parsed.get("drug_interactions"), list) else []


    for k in fallback:
        if k not in parsed:
            parsed[k] = fallback[k]
    return parsed


def summarise_and_insights(existing_summary, soap_text, visit_date, all_consultations, patient_info, all_entities):
    """Generate longitudinal patient summary and insights."""
    recent = all_consultations[-5:]
    history_summary = "\n".join([
        f"Date: {c.get('visit_date')} | Notes: {c.get('doctor_notes', '')[:100]}..."
        for c in recent
    ])

    prompt = (
        "You are a senior clinical longitudinal reviewer for ABDM telemedicine records.\n"
        f"PATIENT INFO: {patient_info.get('name')}, Age {patient_info.get('age')}\n"
        f"LATEST SOAP:\n{soap_text}\n"
        f"HISTORY CONTEXT:\n{history_summary}\n\n"
        "STRICT RULES:\n"
        "1) cumulative_summary must be exactly 2-3 sentences.\n"
        "2) It must summarize the full longitudinal trajectory across visits (progression, current status, and key risk direction).\n"
        "3) Use clinically precise but concise language.\n"
        "4) Do not mention that you are an AI.\n\n"
        "Return ONLY valid JSON, no extra text, no markdown fences:\n"
        '{"cumulative_summary":"Narrative paragraph.",'
        '"patterns":{"recurring_symptoms":{},"patterns":[],"trends":[],"likely_condition":""},'
        '"risk_flags":[],"health_score":5,"health_trend":"stable",'
        '"medication_timeline":[{"drug":"","started":"","stopped":null,"reason":""}]}'
    )

    parsed = _parse_json(_call(prompt, max_tokens=1500))

    if isinstance(parsed, dict):
        cumulative_summary = parsed.get("cumulative_summary")
        if not isinstance(cumulative_summary, str) or not cumulative_summary.strip():
            latest_soap_text = (soap_text or "").strip()
            if existing_summary:
                cumulative_summary = existing_summary
            elif latest_soap_text:
                cumulative_summary = f"Latest ({visit_date}): {latest_soap_text}"
            else:
                cumulative_summary = ""
        parsed["cumulative_summary"] = cumulative_summary

        patterns_raw = parsed.get("patterns") if isinstance(parsed.get("patterns"), dict) else {}
        recurring_raw = patterns_raw.get("recurring_symptoms") if isinstance(patterns_raw.get("recurring_symptoms"), dict) else {}
        parsed["patterns"] = {
            "recurring_symptoms": recurring_raw,
            "patterns": patterns_raw.get("patterns") if isinstance(patterns_raw.get("patterns"), list) else [],
            "trends": patterns_raw.get("trends") if isinstance(patterns_raw.get("trends"), list) else [],
            "likely_condition": str(patterns_raw.get("likely_condition") or "unknown")
        }

        parsed["risk_flags"] = parsed.get("risk_flags") if isinstance(parsed.get("risk_flags"), list) else []
        parsed["medication_timeline"] = (
            parsed.get("medication_timeline") if isinstance(parsed.get("medication_timeline"), list) else []
        )


        try:
            parsed["health_score"] = max(1, min(10, int(parsed.get("health_score", 5))))
        except (ValueError, TypeError):
            parsed["health_score"] = 5


        trend = str(parsed.get("health_trend", "")).strip().lower()
        if trend == "declining":
            trend = "worsening"
        if trend not in ("improving", "stable", "worsening"):
            trend = "stable"
        parsed["health_trend"] = trend

        return parsed


    latest_assessment = ""
    soap_lines = (soap_text or "").splitlines()
    for line in soap_lines:
        if line.strip().upper().startswith("ASSESSMENT:"):
            latest_assessment = line.split(":", 1)[-1].strip()
            break

    fallback_summary = existing_summary or ""
    if latest_assessment:
        update_line = f"Latest ({visit_date}): {latest_assessment}"
        fallback_summary = f"{fallback_summary}\n{update_line}".strip() if fallback_summary else update_line
    elif not fallback_summary:
        compact = re.sub(r"\s+", " ", (soap_text or "").strip())
        if compact:
            fallback_summary = f"Latest ({visit_date}): {compact[:220]}"

    return {
        "cumulative_summary": fallback_summary,
        "patterns": {"recurring_symptoms": {}, "patterns": [], "trends": [], "likely_condition": "unknown"},
        "risk_flags": [],
        "health_score": 5,
        "health_trend": "stable",
        "medication_timeline": []
    }


def patient_friendly_summary(lifetime_summary, language="english"):
    """Generate patient-friendly summary in local language."""
    if not lifetime_summary:
        return "विवरण उपलब्ध नहीं है।" if language.lower() == "hi" else "No medical history recorded."

    lang_map = {
        "hi": "Hindi", "ta": "Tamil", "te": "Telugu",
        "bn": "Bengali", "mr": "Marathi"
    }
    target_lang = lang_map.get(language.lower(), "English")

    prompt = (
        f"Rewrite this medical summary in very simple {target_lang} for a patient in rural India. "
        "Max 150 words. No jargon. Return only the translated text.\n\n" + lifetime_summary
    )

    result = _call(prompt, expect_json=False, max_tokens=512)
    return result if not result.startswith("AI_ERROR") else lifetime_summary


def soap_dict_to_text(soap):
    """Convert SOAP dictionary to formatted text."""
    if not soap or isinstance(soap, str):
        return str(soap) if soap else ""
    return (
        f"SUBJECTIVE: {soap.get('subjective', '')}\n"
        f"OBJECTIVE:  {soap.get('objective', '')}\n"
        f"ASSESSMENT: {soap.get('assessment', '')}\n"
        f"PLAN:       {soap.get('plan', '')}"
    )


def translate_summary(text, lang="Hindi"):
    """Translate summary to specified language."""
    prompt = (
        f"Translate this medical summary into simple, patient-friendly {lang}. "
        f"Keep it under 100 words. No jargon: {text}"
    )
    return _call(prompt, expect_json=False, max_tokens=512)



def test_providers():
    """Test all configured providers and show which are available."""
    print("\n=== Testing LLM Providers ===\n")
    available = _get_available_providers()

    if not available:
        print("❌ No providers available. Please set API keys in .env file:")
        for config in PROVIDER_CONFIGS:
            print(f"   - {config['api_key_env']}")
        return

    print("✓ Available providers:")
    for config in available:
        print(f"   {config['priority']}. {config['name']} - {config['model']} ({config.get('api_key_env', 'n/a')})")

    print("\n🧪 Testing with simple prompt...\n")
    result = _call("Say 'Hello from AI' in one short sentence.", expect_json=False, max_tokens=50)

    if not result.startswith("AI_ERROR"):
        print(f"✓ Success! Response: {result}")
    else:
        print("❌ All providers failed")

    print("\n" + "="*40 + "\n")


if __name__ == "__main__":

    test_providers()