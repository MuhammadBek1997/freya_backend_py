import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

# Database connection
try:
    database_url = os.getenv("DATABASE_URL")
    conn = psycopg2.connect(database_url)
    cursor = conn.cursor()
    
    print("=== Checking if post_media table exists ===")
    cursor.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_name = 'post_media'
        );
    """)
    
    exists = cursor.fetchone()[0]
    print(f"post_media table exists: {exists}")
    
    if exists:
        print("\n=== Post Media Table Structure ===")
        cursor.execute("""
            SELECT column_name, data_type, is_nullable 
            FROM information_schema.columns 
            WHERE table_name = 'post_media'
            ORDER BY ordinal_position;
        """)
        
        columns = cursor.fetchall()
        for column in columns:
            print(f"{column[0]}: {column[1]} ({'NULL' if column[2] == 'YES' else 'NOT NULL'})")
    else:
        print("post_media table does not exist!")
        
        # Check what tables exist
        print("\n=== Available tables ===")
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name;
        """)
        
        tables = cursor.fetchall()
        for table in tables:
            print(table[0])
    
    cursor.close()
    conn.close()
    
except Exception as e:
    print(f"Database error: {e}")