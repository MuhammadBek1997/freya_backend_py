import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

# Database connection
try:
    database_url = os.getenv("DATABASE_URL")
    conn = psycopg2.connect(database_url)
    cursor = conn.cursor()
    
    print("=== Employee Comments Table Structure ===")
    cursor.execute("""
        SELECT column_name, data_type, is_nullable 
        FROM information_schema.columns 
        WHERE table_name = 'employee_comments'
        ORDER BY ordinal_position;
    """)
    
    columns = cursor.fetchall()
    for column in columns:
        print(f"{column[0]}: {column[1]} ({'NULL' if column[2] == 'YES' else 'NOT NULL'})")
    
    print("\n=== Employee Comments Records ===")
    cursor.execute("SELECT COUNT(*) FROM employee_comments")
    count = cursor.fetchone()[0]
    print(f"Total comments: {count}")
    
    if count > 0:
        cursor.execute("SELECT * FROM employee_comments LIMIT 3")
        comments = cursor.fetchall()
        print("\nFirst 3 comments:")
        for comment in comments:
            print(comment)
    
    cursor.close()
    conn.close()
    
except Exception as e:
    print(f"Database error: {e}")