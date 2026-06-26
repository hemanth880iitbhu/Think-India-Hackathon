# Live Chat - Practical Code Example

## SCENARIO: Doctor Records Fever Consultation

### STEP 1: Doctor Opens Patient (Meena Devi)
**Browser loads:** `/doctor_view?patient_id=1`

```
DOCTOR'S SCREEN
┌─────────────────────────────────────────────┐
│ Patient: Meena Devi (52F, ABHA: 1000...01) │
├─────────────────────────────────────────────┤
│                                             │
│ Live Consultation Chat                      │
│ ├─ [Chat Input Box]                         │
│ ├─ [Send] [Summarize to Notes]             │
│ └─ 0 messages                               │
│                                             │
│ Clinical Notes:                             │
│ [Text Area - empty]                         │
│                                             │
│ [Process with AI]                           │
└─────────────────────────────────────────────┘

JavaScript State:
chatMessages = []  // Empty array
```

---

### STEP 2: Doctor Sends Message #1

**Doctor types:** "Patient reports high fever since yesterday"

```javascript
// In browser console (for illustration):
console.log(chatMessages)
// Output: []

// Doctor clicks "Send":
addMessage('doctor', 'Patient reports high fever since yesterday')

// Now:
chatMessages = [
  {
    role: 'doctor',
    text: 'Patient reports high fever since yesterday',
    time: '2:45 PM'
  }
]
```

**UI Updates:**
```
┌─────────────────────────────────┐
│ 1 message                       │
├─────────────────────────────────┤
│ 👨‍⚕️ Doctor • 2:45 PM             │
│ Patient reports high fever      │
│ since yesterday                 │
└─────────────────────────────────┘
Input: [cleared]
Status: "New message added. Click Summarize to Notes."
```

---

### STEP 3: Doctor Simulates Patient Response

**Doctor changes dropdown to "Patient"**
**Doctor types:** "Yes, temp is 102°F"

```javascript
// Doctor clicks dropdown → role changes to 'patient'
// Doctor clicks "Send":

chatMessages = [
  {
    role: 'doctor',
    text: 'Patient reports high fever since yesterday',
    time: '2:45 PM'
  },
  {
    role: 'patient',
    text: 'Yes, temp is 102°F',
    time: '2:46 PM'
  }
]
```

**UI Updates:**
```
┌─────────────────────────────────┐
│ 2 messages                      │
├─────────────────────────────────┤
│ 👨‍⚕️ Doctor • 2:45 PM             │
│ Patient reports high fever      │
│ since yesterday                 │
│                                 │
│ 👩 Patient • 2:46 PM            │
│ Yes, temp is 102°F              │
└─────────────────────────────────┘
```

---

### STEP 4: Doctor Adds Diagnosis

**Doctor switches back to "Doctor"**
**Doctor types:** "Likely viral. Start Paracetamol 500mg, rest, fluids"

```javascript
chatMessages = [
  {role: 'doctor', text: 'Patient reports high fever since yesterday', time: '2:45 PM'},
  {role: 'patient', text: 'Yes, temp is 102°F', time: '2:46 PM'},
  {role: 'doctor', text: 'Likely viral. Start Paracetamol 500mg, rest, fluids', time: '2:47 PM'}
]
```

**UI Shows all 3 messages**

---

### STEP 5: Doctor Clicks "Summarize to Notes"

**Behind scenes:**
```javascript
// Build transcript function runs:
function buildTranscript() {
  return chatMessages
    .map((msg) => `${msg.role === 'doctor' ? 'Doctor' : 'Patient'} (${msg.time}): ${msg.text}`)
    .join('\n')
}

// Result:
const transcript = `Doctor (2:45 PM): Patient reports high fever since yesterday
Patient (2:46 PM): Yes, temp is 102°F
Doctor (2:47 PM): Likely viral. Start Paracetamol 500mg, rest, fluids`
```

**JavaScript makes fetch request:**
```javascript
fetch('/api/chat-summary', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    chat_transcript: transcript
  })
})
```

**Sent to backend:**
```
POST /api/chat-summary
{
  "chat_transcript": "Doctor (2:45 PM): Patient reports high fever since yesterday\nPatient (2:46 PM): Yes, temp is 102°F\nDoctor (2:47 PM): Likely viral. Start Paracetamol 500mg, rest, fluids"
}
```

**Backend processes** (`/api/chat-summary` endpoint in app.py):
```python
from ai_pipeline import summarise_chat_transcript

@app.route('/api/chat-summary', methods=['POST'])
def api_chat_summary():
    payload = request.get_json()
    chat_transcript = payload.get('chat_transcript')
    
    # Call AI
    result = summarise_chat_transcript(chat_transcript)
    
    return jsonify(result)
    # Returns:
    # {
    #   "summary": "Patient with acute viral fever (102°F), started on Paracetamol 500mg with supportive care",
    #   "patient_points": ["high fever", "102°F temp", "since yesterday"],
    #   "doctor_actions": ["Paracetamol 500mg", "rest", "fluids"],
    #   "red_flags": []
    # }
```

**Browser inserts into Clinical Notes:**
```
Before:
[Text Area empty]

After:
Live chat summary: Patient with acute viral fever (102°F), started on Paracetamol 500mg with supportive care
Patient-reported in chat: high fever; 102°F temp; since yesterday
Doctor actions in chat: Paracetamol 500mg; rest; fluids
Chat red flags: (none)
```

**Also stores in hidden fields:**
```javascript
// For form submission
chatTranscriptInput.value = `Doctor (2:45 PM): Patient reports high fever since yesterday\nPatient (2:46 PM): Yes, temp is 102°F\nDoctor (2:47 PM): Likely viral. Start Paracetamol 500mg, rest, fluids`

chatSummaryInput.value = `Patient with acute viral fever (102°F), started on Paracetamol 500mg with supportive care`
```

**UI Status updates:**
```
Status: "AI chat summary inserted into clinical notes."
Button text: "Summarize to Notes" (re-enabled)
```

---

### STEP 6: Doctor Clicks "Process with AI" Button

**Form submission:**
```javascript
// Submits with all fields
mainForm.submit()
```

**HTTP POST to `/submit_note`:**
```
POST /submit_note
Content-Type: application/x-www-form-urlencoded

patient_id=1
&doctor_notes=Live chat summary: Patient with acute viral fever (102°F), started on Paracetamol 500mg with supportive care
Patient-reported in chat: high fever; 102°F temp; since yesterday
Doctor actions in chat: Paracetamol 500mg; rest; fluids
Chat red flags: (none)
&chat_transcript=Doctor (2:45 PM): Patient reports high fever since yesterday
Patient (2:46 PM): Yes, temp is 102°F
Doctor (2:47 PM): Likely viral. Start Paracetamol 500mg, rest, fluids
&chat_summary=Patient with acute viral fever (102°F), started on Paracetamol 500mg with supportive care
&hospital_name=Apex City Clinic
&doctor_name=Dr. Sharma
&doctor_hpr_id=HPR-XYZ
```

**Backend processes** (`/submit_note` in app.py):
```python
@app.route('/submit_note', methods=['POST'])
def submit_note():
    # 1. Validate
    patient_id = 1
    doctor_notes = request.form['doctor_notes']
    chat_transcript = request.form['chat_transcript']  # ← SAVED!
    chat_summary = request.form['chat_summary']       # ← SAVED!
    
    # 2. Run 7-stage AI pipeline
    result = extract_and_analyse(doctor_notes, previous_notes)
    # ... runs through all 7 stages ...
    
    # 3. Save to database
    conn.execute('''
        INSERT INTO consultations (
            patient_id, 
            visit_date, 
            doctor_notes, 
            chat_transcript,
            chat_summary,
            ai_summary, 
            soap_note, 
            entities, 
            drug_interactions, 
            visit_delta, 
            hospital_name, 
            doctor_name, 
            doctor_hpr_id
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        1,  # patient_id
        '08 Apr 2026, 2:47 PM',  # visit_date
        doctor_notes,
        chat_transcript,  # ← Database saves this!
        chat_summary,     # ← Database saves this!
        ai_summary,       # ← 7-stage output
        soap_note,
        entities_json,
        drug_interactions_json,
        visit_delta_json,
        'Apex City Clinic',
        'Dr. Sharma',
        'HPR-XYZ'
    ))
    conn.commit()
```

**Database now contains:**
```sql
SELECT * FROM consultations WHERE patient_id=1 ORDER BY visit_date DESC LIMIT 1;

-- Result:
id: 123
patient_id: 1
visit_date: '08 Apr 2026, 2:47 PM'
doctor_notes: 'Live chat summary: Patient with acute viral fever...'
chat_transcript: 'Doctor (2:45 PM): Patient reports high fever since yesterday\nPatient (2:46 PM): Yes, temp is 102°F\nDoctor (2:47 PM): Likely viral. Start Paracetamol 500mg, rest, fluids'  ← PERMANENT!
chat_summary: 'Patient with acute viral fever (102°F), started on Paracetamol 500mg with supportive care'
ai_summary: '[7-stage pipeline output with delta analysis, risk flags, etc.]'
soap_note: '[structured clinical format]'
entities: '[extracted symptoms, findings, medications]'
...
```

---

### STEP 7: Patient Views Consultation (Later)

**Patient logs in:** `/patient`
```
SELECT * FROM consultations WHERE patient_id=1;
```

**Patient sees visit:**
```
┌────────────────────────────────────────────┐
│ Visit: 08 Apr 2026, 2:47 PM               │
│ Doctor: Dr. Sharma (HPR-XYZ)               │
│ Hospital: Apex City Clinic                 │
├────────────────────────────────────────────┤
│ 📋 Live Consultation Chat                  │
│                                            │
│ Patient with acute viral fever (102°F),   │
│ started on Paracetamol 500mg with         │
│ supportive care                            │
│                                            │
│ [Show Transcript ▼]                        │
│                                            │
│ Doctor (2:45 PM): Patient reports high    │
│ fever since yesterday                     │
│ Patient (2:46 PM): Yes, temp is 102°F    │
│ Doctor (2:47 PM): Likely viral. Start    │
│ Paracetamol 500mg, rest, fluids           │
│                                            │
├────────────────────────────────────────────┤
│ (Patient cannot edit/reply)                │
└────────────────────────────────────────────┘
```

**Rendered from template** (patient.html):
```html
{% set chat_summary = visit.get('chat_summary')|trim %}
{% set chat_transcript = visit.get('chat_transcript')|trim %}

<div class="chat-capture">
  <div class="chat-capture-head">Live Consultation Chat</div>
  <div class="chat-capture-summary">
    {{ chat_summary or 'No summary' }}
  </div>
  
  <details class="chat-transcript">
    <summary>Transcript</summary>
    <div class="chat-transcript-body">
      {{ chat_transcript }}
    </div>
  </details>
</div>
```

---

## 📊 Data Lifecycle Summary

```
TIMELINE VISUALIZATION:

2:45 PM  Doctor types → chatMessages[0]
         ├─ Memory only ✅
         └─ UI display ✅

2:46 PM  Patient msg → chatMessages[1]
         ├─ Memory only ✅
         └─ UI display ✅

2:47 PM  Doctor diagnosis → chatMessages[2]
         ├─ Memory only ✅
         └─ UI display ✅

[Doctor clicks Summarize]

2:48 PM  Build transcript → /api/chat-summary
         ├─ Sent to AI ✅
         ├─ Processed ✅
         └─ Summary returned ✅

[Doctor clicks Process]

2:49 PM  Form submission → /submit_note
         ├─ chat_transcript saved to DB ✅✅✅
         ├─ chat_summary saved to DB ✅✅✅
         ├─ 7-stage pipeline runs ✅
         └─ Entire consultation stored ✅

[PERSISTENT - never lost]

Next Day: Patient login
         └─ Reads from consultations table
         └─ Shows chat_summary + chat_transcript
         └─ Read-only view
```

---

## ⚠️ CRITICAL POINTS

### Messages Lost Without "Process with AI"
If doctor closes browser without clicking "Process with AI":
- ❌ chatMessages array discarded
- ❌ All conversation lost
- ❌ Database has no record

### This Is NOT Real-Time Chat
- Doctor types BOTH sides (simulating)
- No actual patient app/interface
- Patient receives messages AFTER consultation ends
- Good for: Recording workflow
- Bad for: Live telemedicine video

### Data Integrity
- ✅ Once in database = permanent
- ✅ Accessible to patient forever
- ✅ Included in lifetime records analysis
- ✅ Used by 7-stage AI pipeline

---

## 🔍 WHERE TO FIND THIS CODE

1. **Chat UI rendering** → [templates/doctor.html](templates/doctor.html#L202-L230)
2. **JavaScript message handling** → [templates/doctor.html](templates/doctor.html#L345-L475)
3. **Transcript building** → [templates/doctor.html](templates/doctor.html#L346)
4. **AI summarization API** → [app.py](app.py#L1315-L1330)
5. **Form submission** → [app.py](app.py#L1336-L1410)
6. **Database storage** → [database.py](database.py#L87-110)
7. **Patient view rendering** → [templates/patient.html](templates/patient.html#L217-L226)
