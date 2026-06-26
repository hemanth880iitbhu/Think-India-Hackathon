import sqlite3

def reset_data():
    conn = sqlite3.connect('apex_health.db')
    cursor = conn.cursor()


    cursor.execute("DELETE FROM consultations")


    cursor.execute("DELETE FROM sqlite_sequence WHERE name='consultations'")

    conn.commit()
    conn.close()
    print("🧹 Database Cleared. Ready for the Winning Demo.")

if __name__ == "__main__":
    reset_data()