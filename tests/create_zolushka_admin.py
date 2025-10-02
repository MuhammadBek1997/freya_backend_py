import psycopg2
import bcrypt
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database connection from DATABASE_URL
database_url = os.getenv("DATABASE_URL")
conn = psycopg2.connect(database_url)
cur = conn.cursor()

print("=== Zolushka uchun Admin Record Yaratish ===\n")

# Employee ma'lumotlarini olish
employee_id = "639ea749-59a1-4f40-a919-34a47f40f5dd"
username = "zolushka"
password = "12345678"
salon_id = "83fc0c1a-b3d1-44dd-9b43-d2b9608042c7"

# Password ni hash qilish
hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

# Admin record yaratish
try:
    insert_query = """
    INSERT INTO admins (id, username, email, password_hash, role, salon_id, is_active, created_at, updated_at)
    VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
    """
    
    cur.execute(insert_query, (
        employee_id,  # Employee ID bilan bir xil qilish
        username,
        f"{username}@example.com",  # Email qo'shish
        hashed_password,
        'employee',
        salon_id,
        True
    ))
    
    conn.commit()
    print(f"✅ Zolushka uchun admin record yaratildi:")
    print(f"  ID: {employee_id}")
    print(f"  Username: {username}")
    print(f"  Role: employee")
    print(f"  Salon ID: {salon_id}")
    
    # Tekshirish
    cur.execute("SELECT id, username, role FROM admins WHERE id = %s", (employee_id,))
    result = cur.fetchone()
    if result:
        print(f"\n✅ Tekshirish: Admin record topildi")
        print(f"  ID: {result[0]}")
        print(f"  Username: {result[1]}")
        print(f"  Role: {result[2]}")
    else:
        print("❌ Admin record topilmadi")
        
except Exception as e:
    print(f"❌ Xatolik: {e}")
    conn.rollback()

# Cleanup
cur.close()
conn.close()