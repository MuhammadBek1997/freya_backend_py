import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

# Database connection
try:
    database_url = os.getenv("DATABASE_URL")
    conn = psycopg2.connect(database_url)
    cursor = conn.cursor()
    
    print("=== Employee Table Structure ===")
    cursor.execute("""
        SELECT column_name, data_type, is_nullable 
        FROM information_schema.columns 
        WHERE table_name = 'employees'
        ORDER BY ordinal_position;
    """)
    
    columns = cursor.fetchall()
    for col in columns:
        print(f"{col[0]}: {col[1]} ({'NULL' if col[2] == 'YES' else 'NOT NULL'})")
    
    print("\n=== Employee Records ===")
    cursor.execute("SELECT COUNT(*) FROM employees;")
    count = cursor.fetchone()[0]
    print(f"Total employees: {count}")
    
    if count > 0:
        cursor.execute("""
            SELECT id, name, surname, username, role, profession, phone, email, is_active 
            FROM employees 
            LIMIT 5;
        """)
        employees = cursor.fetchall()
        
        print("\nFirst 5 employees:")
        for emp in employees:
            print(f"ID: {emp[0]}")
            print(f"Name: {emp[1]} {emp[2] or ''}")
            print(f"Username: {emp[3]}")
            print(f"Role: {emp[4]}")
            print(f"Profession: {emp[5]}")
            print(f"Phone: {emp[6]}")
            print(f"Email: {emp[7]}")
            print(f"Active: {emp[8]}")
            print("-" * 40)
    
    cursor.close()
    conn.close()
    
except Exception as e:
    print(f"Database error: {e}")