import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

# Database connection
try:
    database_url = os.getenv("DATABASE_URL")
    conn = psycopg2.connect(database_url)
    cursor = conn.cursor()
    
    print("=== Users Table Structure ===")
    cursor.execute("""
        SELECT column_name, data_type, is_nullable 
        FROM information_schema.columns 
        WHERE table_name = 'users'
        ORDER BY ordinal_position;
    """)
    
    columns = cursor.fetchall()
    for column in columns:
        print(f"{column[0]}: {column[1]} ({'NULL' if column[2] == 'YES' else 'NOT NULL'})")
    
    print("\n=== Users Records ===")
    cursor.execute("SELECT COUNT(*) FROM users")
    count = cursor.fetchone()[0]
    print(f"Total users: {count}")
    
    if count > 0:
        cursor.execute("SELECT id, phone, email, full_name FROM users LIMIT 3")
        users = cursor.fetchall()
        print("\nFirst 3 users:")
        for user in users:
            print(user)
    
    cursor.close()
    conn.close()
    
except Exception as e:
    print(f"Database error: {e}")