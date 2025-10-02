import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

# Database connection
try:
    database_url = os.getenv("DATABASE_URL")
    conn = psycopg2.connect(database_url)
    cursor = conn.cursor()
    
    print("=== Admin Table Structure ===")
    cursor.execute("""
        SELECT column_name, data_type, is_nullable 
        FROM information_schema.columns 
        WHERE table_name = 'admins'
        ORDER BY ordinal_position;
    """)
    
    columns = cursor.fetchall()
    for col in columns:
        print(f"{col[0]}: {col[1]} ({'NULL' if col[2] == 'YES' else 'NOT NULL'})")
    
    print("\n=== Admin Records ===")
    cursor.execute("SELECT COUNT(*) FROM admins;")
    count = cursor.fetchone()[0]
    print(f"Total admins: {count}")
    
    if count > 0:
        cursor.execute("""
            SELECT id, username, email, full_name, role, is_active, password_hash 
            FROM admins 
            LIMIT 5;
        """)
        admins = cursor.fetchall()
        
        print("\nFirst 5 admins:")
        for admin in admins:
            print(f"ID: {admin[0]}")
            print(f"Username: {admin[1]}")
            print(f"Email: {admin[2]}")
            print(f"Full Name: {admin[3]}")
            print(f"Role: {admin[4]}")
            print(f"Active: {admin[5]}")
            print(f"Password Hash: {admin[6][:50]}...")
            print("-" * 40)
    
    cursor.close()
    conn.close()
    
except Exception as e:
    print(f"Database error: {e}")