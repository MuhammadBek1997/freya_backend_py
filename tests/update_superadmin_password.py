import psycopg2
import os
from dotenv import load_dotenv
import bcrypt

load_dotenv()

def update_superadmin_password():
    """Superadmin parolini yangilash"""
    try:
        database_url = os.getenv("DATABASE_URL")
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        
        # Yangi parol
        new_password = "superadmin123"
        
        # Parolni hash qilish (bcrypt bilan)
        password_bytes = new_password.encode('utf-8')
        salt = bcrypt.gensalt()
        hashed_password = bcrypt.hashpw(password_bytes, salt)
        
        print(f"New password: {new_password}")
        print(f"Hashed password: {hashed_password.decode('utf-8')}")
        
        # Superadmin parolini yangilash
        cursor.execute("""
            UPDATE admins 
            SET password_hash = %s 
            WHERE username = 'superadmin' AND role = 'superadmin'
        """, (hashed_password.decode('utf-8'),))
        
        affected_rows = cursor.rowcount
        conn.commit()
        
        if affected_rows > 0:
            print(f"✅ Superadmin paroli muvaffaqiyatli yangilandi ({affected_rows} rows affected)")
        else:
            print("❌ Superadmin topilmadi yoki yangilanmadi")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Database error: {e}")

if __name__ == "__main__":
    update_superadmin_password()