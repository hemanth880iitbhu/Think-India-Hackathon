"""
time_machine.py — The ApexHealth Master Demo Initializer
Usage:
  1. Ensure app.py is running in another terminal.
  2. Run 'python time_machine.py' to seed the data and trigger AI analysis.
"""

import requests
import time
import sys


CYAN = '\033[96m'
GREEN = '\033[92m'
YELLOW = '\033[93m'
RED = '\033[91m'
BOLD = '\033[1m'
MAGENTA = '\033[95m'
RESET = '\033[0m'

BASE_URL = 'http://127.0.0.1:5000'





histories = {


    1: [
        {
            "visit_date": "12 Aug 2025",
            "hospital_name": "Rural Health Center",
            "doctor_name": "Dr. Gupta",
            "doctor_notes": "Patient presents with extreme fatigue and frequent thirst. Weight 74kg. BP 138/88. Fasting blood sugar 155 mg/dL. HbA1c 7.2%. Diagnosed with Type 2 Diabetes. Started Metformin 500mg OD. Advised sugar monitoring."
        },
        {
            "visit_date": "05 Nov 2025",
            "hospital_name": "District Clinic",
            "doctor_name": "Dr. Sharma",
            "doctor_notes": "Follow-up. Fatigue persists. Patient reports new, frequent headaches. BP elevated at 165/100. Fasting sugar 178 mg/dL. Assessment: Uncontrolled hypertension and diabetes. Increase Metformin to 500mg BD. Added Telmisartan 40mg for BP control."
        },
        {
            "visit_date": "20 Feb 2026",
            "hospital_name": "Apex City Cardiology",
            "doctor_name": "Dr. Reddy",
            "doctor_notes": "URGENT. Patient reports chest tightness and shortness of breath. Headaches are severe. BP 180/110. SpO2 94%. Fasting sugar 195. High risk of cardiac event. ICU admission recommended. Started Aspirin 75mg and Atorvastatin 40mg."
        }
    ],



    2: [
        {
            "visit_date": "01 Mar 2026",
            "hospital_name": "City Care",
            "doctor_name": "Dr. Ali",
            "doctor_notes": "High fever (103F) and severe throat pain. Tonsils inflamed with exudate. Diagnosed with acute bacterial tonsillitis. Prescribed Amoxicillin 500mg TDS for 7 days."
        },
        {
            "visit_date": "03 Mar 2026",
            "hospital_name": "City Care",
            "doctor_name": "Dr. Ali",
            "doctor_notes": "EMERGENCY. Patient returned with severe hives and wheezing after taking Amoxicillin. Acute allergic reaction. STOPPED Amoxicillin. Switched to Azithromycin 500mg OD. Documented Penicillin allergy."
        }
    ]
}

def print_status(text, delay=0.015):
    for char in text:
        sys.stdout.write(char)
        sys.stdout.flush()
        time.sleep(delay)
    print()

def run_time_machine():
    print(f"\n{CYAN}{BOLD}╔════════════════════════════════════════════════════════╗{RESET}")
    print(f"{CYAN}{BOLD}║   APEX-HEALTH : SYNTHETIC INTELLIGENCE INITIALIZER     ║{RESET}")
    print(f"{CYAN}{BOLD}╚════════════════════════════════════════════════════════╝{RESET}\n")

    print_status(f"{YELLOW}[*] Establishing connection to local server...{RESET}")
    time.sleep(0.5)


    print_status(f"\n{BOLD}{MAGENTA}▶ PHASE 1: INJECTING HISTORICAL CLINICAL NARRATIVES{RESET}")
    for patient_id, visits in histories.items():
        for i, visit in enumerate(visits):
            visit['patient_id'] = patient_id
            try:
                requests.post(f"{BASE_URL}/add_consultation", json=visit)
                print(f"  {GREEN}✔{RESET} Patient {patient_id} | Visit {i+1} [{visit['visit_date']}] -> Injected")
            except Exception as e:
                print(f"  {RED}✘ Connection Failed. Is app.py running?{RESET}")
                return
            time.sleep(3)


    print_status(f"\n{BOLD}{MAGENTA}▶ PHASE 2: EXECUTING 7-STAGE AI PIEPELINE{RESET}")
    print(f"{YELLOW}  [!] Triggering longitudinal analysis and pattern detection...{RESET}\n")

    for patient_id in histories.keys():
        sys.stdout.write(f"  {CYAN}⚙{RESET} Processing lifetime record for Patient {patient_id} ")
        sys.stdout.flush()

        for _ in range(5):
            time.sleep(0.3)
            sys.stdout.write(".")
            sys.stdout.flush()

        try:
            resp = requests.get(f"{BASE_URL}/reanalyse/{patient_id}", timeout=180)
            if resp.status_code == 200:
                print(f" {GREEN}[COMPLETE]{RESET}")
            else:
                print(f" {RED}[FAILED]{RESET}")
        except Exception:
            print(f" {RED}[TIMEOUT]{RESET}")

    print(f"\n{GREEN}{BOLD}════════════════════════════════════════════════════════════{RESET}")
    print(f"{GREEN}{BOLD} ✅ SYSTEM INITIALIZED FOR DEMO                              {RESET}")
    print(f"{GREEN}{BOLD}════════════════════════════════════════════════════════════{RESET}")
    print(f"{CYAN}Ready for presentation at:{RESET}")
    print(f" 🌟 Chronic Trajectory: {BOLD}http://127.0.0.1:5000/patient/1{RESET}")
    print(f" 🛡️  Allergy Management: {BOLD}http://127.0.0.1:5000/patient/2{RESET}\n")

if __name__ == "__main__":
    run_time_machine()