"""
database.py - SQLite setup for ApexHealth
Contains the get_db() and init_db() functions required by app.py
"""
import sqlite3
from werkzeug.security import generate_password_hash

DB_PATH = 'apex_health.db'

def get_db():
    """Opens a new database connection for a request."""
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('PRAGMA synchronous=NORMAL')
    conn.execute('PRAGMA busy_timeout=30000')
    conn.execute('PRAGMA foreign_keys=ON')

    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes the database schema if it doesn't exist."""
    conn = get_db()
    c = conn.cursor()


    c.execute('''CREATE TABLE IF NOT EXISTS patients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        age INTEGER,
        gender TEXT,
        blood_group TEXT DEFAULT 'Unknown',
        allergies TEXT DEFAULT 'None',
        contact TEXT DEFAULT '',
        email TEXT DEFAULT '',
        patient_status TEXT DEFAULT 'active',
        abha_id TEXT DEFAULT '',
        password_hash TEXT DEFAULT '',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')


    patient_cols = {row[1] for row in c.execute("PRAGMA table_info(patients)").fetchall()}
    if 'password_hash' not in patient_cols:
        c.execute("ALTER TABLE patients ADD COLUMN password_hash TEXT DEFAULT ''")
    if 'email' not in patient_cols:
        c.execute("ALTER TABLE patients ADD COLUMN email TEXT DEFAULT ''")
    if 'patient_status' not in patient_cols:
        c.execute("ALTER TABLE patients ADD COLUMN patient_status TEXT DEFAULT 'active'")

    c.execute(
        """CREATE UNIQUE INDEX IF NOT EXISTS idx_patients_abha_unique
           ON patients(abha_id)
           WHERE length(abha_id) = 14"""
    )


    c.execute('''CREATE TABLE IF NOT EXISTS doctors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        hpr_id TEXT NOT NULL,
        hospital_name TEXT DEFAULT 'Apex City Clinic',
        specialization TEXT DEFAULT '',
        contact TEXT DEFAULT '',
        password_hash TEXT DEFAULT '',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    doctor_cols = {row[1] for row in c.execute("PRAGMA table_info(doctors)").fetchall()}
    if 'password_hash' not in doctor_cols:
        c.execute("ALTER TABLE doctors ADD COLUMN password_hash TEXT DEFAULT ''")
    if 'hospital_name' not in doctor_cols:
        c.execute("ALTER TABLE doctors ADD COLUMN hospital_name TEXT DEFAULT 'Apex City Clinic'")
    if 'specialization' not in doctor_cols:
        c.execute("ALTER TABLE doctors ADD COLUMN specialization TEXT DEFAULT ''")
    if 'contact' not in doctor_cols:
        c.execute("ALTER TABLE doctors ADD COLUMN contact TEXT DEFAULT ''")

    c.execute(
        '''CREATE UNIQUE INDEX IF NOT EXISTS idx_doctors_hpr_unique
           ON doctors(hpr_id)'''
    )


    c.execute('''CREATE TABLE IF NOT EXISTS consultations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id INTEGER,
        visit_date TEXT,
        doctor_notes TEXT,
        ai_summary TEXT,
        soap_note TEXT,
        entities TEXT,
        drug_interactions TEXT DEFAULT '[]',
        visit_delta TEXT DEFAULT '{}',
        chat_transcript TEXT DEFAULT '',
        chat_summary TEXT DEFAULT '',
        hospital_name TEXT DEFAULT 'Apex City Clinic',
        doctor_name TEXT DEFAULT 'Dr. Sharma',
        doctor_hpr_id TEXT DEFAULT '',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (patient_id) REFERENCES patients(id)
    )''')

    consultation_cols = {row[1] for row in c.execute("PRAGMA table_info(consultations)").fetchall()}
    if 'doctor_hpr_id' not in consultation_cols:
        c.execute("ALTER TABLE consultations ADD COLUMN doctor_hpr_id TEXT DEFAULT ''")
    if 'chat_transcript' not in consultation_cols:
        c.execute("ALTER TABLE consultations ADD COLUMN chat_transcript TEXT DEFAULT ''")
    if 'chat_summary' not in consultation_cols:
        c.execute("ALTER TABLE consultations ADD COLUMN chat_summary TEXT DEFAULT ''")

    c.execute('''CREATE TABLE IF NOT EXISTS lab_reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id INTEGER NOT NULL,
        consultation_id INTEGER DEFAULT NULL,
        report_title TEXT DEFAULT 'Lab Report',
        report_type TEXT DEFAULT '',
        file_name TEXT NOT NULL,
        file_path TEXT NOT NULL,
        mime_type TEXT DEFAULT '',
        uploaded_by_doctor_name TEXT DEFAULT '',
        uploaded_by_doctor_hpr_id TEXT DEFAULT '',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (patient_id) REFERENCES patients(id),
        FOREIGN KEY (consultation_id) REFERENCES consultations(id)
    )''')

    lab_report_cols = {row[1] for row in c.execute("PRAGMA table_info(lab_reports)").fetchall()}
    if 'consultation_id' not in lab_report_cols:
        c.execute("ALTER TABLE lab_reports ADD COLUMN consultation_id INTEGER DEFAULT NULL")
    if 'report_title' not in lab_report_cols:
        c.execute("ALTER TABLE lab_reports ADD COLUMN report_title TEXT DEFAULT 'Lab Report'")
    if 'report_type' not in lab_report_cols:
        c.execute("ALTER TABLE lab_reports ADD COLUMN report_type TEXT DEFAULT ''")
    if 'file_name' not in lab_report_cols:
        c.execute("ALTER TABLE lab_reports ADD COLUMN file_name TEXT DEFAULT ''")
    if 'file_path' not in lab_report_cols:
        c.execute("ALTER TABLE lab_reports ADD COLUMN file_path TEXT DEFAULT ''")
    if 'mime_type' not in lab_report_cols:
        c.execute("ALTER TABLE lab_reports ADD COLUMN mime_type TEXT DEFAULT ''")
    if 'uploaded_by_doctor_name' not in lab_report_cols:
        c.execute("ALTER TABLE lab_reports ADD COLUMN uploaded_by_doctor_name TEXT DEFAULT ''")
    if 'uploaded_by_doctor_hpr_id' not in lab_report_cols:
        c.execute("ALTER TABLE lab_reports ADD COLUMN uploaded_by_doctor_hpr_id TEXT DEFAULT ''")


    c.execute('''CREATE TABLE IF NOT EXISTS lifetime_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id INTEGER UNIQUE,
        cumulative_summary TEXT DEFAULT '',
        condition_history TEXT DEFAULT '[]',
        medication_timeline TEXT DEFAULT '[]',
        risk_flags TEXT DEFAULT '[]',
        pattern_data TEXT DEFAULT '{}',
        health_score INTEGER DEFAULT 5,
        health_trend TEXT DEFAULT 'stable',
        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (patient_id) REFERENCES patients(id)
    )''')


    patient_count = c.execute('SELECT COUNT(*) FROM patients').fetchone()[0]
    if patient_count == 0:
        demo_patients = [
            ('Meena Devi', 52, 'Female', 'B+', 'None', '+91-9000000001', 'meena@example.com', '10000000000001', generate_password_hash('Apex@123')),
            ('Rohan Verma', 31, 'Male', 'O+', 'Penicillin', '+91-9000000002', 'rohan@example.com', '10000000000002', generate_password_hash('Apex@123')),
            ('Priya Sharma', 44, 'Female', 'A+', 'None', '+91-9000000003', 'priya@example.com', '10000000000003', generate_password_hash('Apex@123')),
        ]
        c.executemany(
            '''INSERT INTO patients
               (name, age, gender, blood_group, allergies, contact, email, abha_id, password_hash)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            demo_patients
        )
        patient_ids = [row[0] for row in c.execute('SELECT id FROM patients').fetchall()]
        c.executemany(
            'INSERT OR IGNORE INTO lifetime_records (patient_id) VALUES (?)',
            [(pid,) for pid in patient_ids]
        )

        primary_patient_id = patient_ids[0]
        demo_visits = [
            (
                primary_patient_id,
                '12 Jan 2026',
                'Dry cough with nocturnal wheeze for 5 days. Mild breathlessness on exertion. No fever.',
                'Upper airway inflammation with wheeze pattern; no current danger signs.',
                'SUBJECTIVE: Dry cough and wheeze\nOBJECTIVE: Mild bilateral wheeze\nASSESSMENT: Reactive airway episode\nPLAN: Inhaler and hydration',
                '{"symptoms": ["dry cough", "wheeze", "mild breathlessness"], "diagnoses": ["reactive airway episode"], "medications": [{"name": "Salbutamol", "dose": "2 puffs", "frequency": "SOS"}], "vitals": {"bp": "128/82", "temperature": "98.4", "spo2": "96", "weight": 67, "pulse": 88}}',
                'Apex City Clinic',
                'Dr. A. Sharma',
                'HPR-APEX-1001'
            ),
            (
                primary_patient_id,
                '03 Feb 2026',
                'Cough frequency reduced but still present at night. Reports chest tightness during cold exposure.',
                'Partial improvement with persistent triggers; requires continuation of controller therapy.',
                'SUBJECTIVE: Night cough persists\nOBJECTIVE: No acute distress\nASSESSMENT: Improving reactive airway disease\nPLAN: Continue inhaler and avoid triggers',
                '{"symptoms": ["night cough", "chest tightness"], "diagnoses": ["reactive airway disease"], "medications": [{"name": "Budesonide", "dose": "200 mcg", "frequency": "BD"}], "vitals": {"bp": "126/80", "temperature": "98.2", "spo2": "97", "weight": 67, "pulse": 84}}',
                'Apex City Clinic',
                'Dr. P. Iyer',
                'HPR-APEX-1002'
            ),
            (
                primary_patient_id,
                '21 Mar 2026',
                'Two brief wheeze episodes this month, no ER visits. Better exercise tolerance now.',
                'Overall improving respiratory trend with low but recurring symptom burden.',
                'SUBJECTIVE: Intermittent wheeze\nOBJECTIVE: Stable vitals\nASSESSMENT: Controlled but recurring airway symptoms\nPLAN: Continue maintenance inhaler and review in 4 weeks',
                '{"symptoms": ["intermittent wheeze"], "diagnoses": ["controlled reactive airway disease"], "medications": [{"name": "Budesonide", "dose": "200 mcg", "frequency": "BD"}, {"name": "Salbutamol", "dose": "2 puffs", "frequency": "PRN"}], "vitals": {"bp": "124/78", "temperature": "98.1", "spo2": "98", "weight": 66, "pulse": 80}}',
                'Apex City Clinic',
                'Dr. A. Sharma',
                'HPR-APEX-1001'
            )
        ]

        c.executemany(
            '''INSERT INTO consultations
               (patient_id, visit_date, doctor_notes, ai_summary, soap_note, entities, hospital_name, doctor_name, doctor_hpr_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            demo_visits
        )

        c.execute(
            '''UPDATE lifetime_records
               SET cumulative_summary=?,
                   pattern_data=?,
                   risk_flags=?,
                   health_score=?,
                   health_trend=?,
                   medication_timeline=?
               WHERE patient_id=?''',
            (
                'Patient demonstrates recurring airway inflammation over three visits with gradual improvement after inhaler adherence. Night-time symptoms persist intermittently, indicating a chronic trigger pattern that still needs monitoring.',
                '{"recurring_symptoms": {"wheeze": 3, "cough": 2}, "trends": ["improving exercise tolerance", "reduced episode severity"]}',
                '["Recurring wheeze across 3 visits", "Night cough persistence"]',
                7,
                'improving',
                '[{"drug": "Budesonide", "started": "03 Feb 2026", "stopped": null, "reason": "Controller therapy"}, {"drug": "Salbutamol", "started": "12 Jan 2026", "stopped": null, "reason": "Rescue inhaler"}]',
                primary_patient_id
            )
        )

    doctor_count = c.execute('SELECT COUNT(*) FROM doctors').fetchone()[0]
    if doctor_count == 0:
        c.execute(
                '''INSERT INTO doctors (name, hpr_id, hospital_name, specialization, contact, password_hash)
                    VALUES (?, ?, ?, ?, ?, ?)''',
                ('Dr. A. Sharma', 'HPR-APEX-1001', 'Apex City Clinic', 'General Medicine', '+91-9000001001', generate_password_hash('Apex@123'))
        )

    conn.commit()
    conn.close()
    print("✅ Database schema verified and ready.")


if __name__ == '__main__':
    init_db()