import psycopg2
import bcrypt
import uuid
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database connection from DATABASE_URL
database_url = os.getenv("DATABASE_URL")
conn = psycopg2.connect(database_url)
cur = conn.cursor()

# Test employee ma'lumotlari
employee_username = "test_employee"
employee_password = "testpassword123"
employee_email = "test_employee@example.com"
employee_full_name = "Test Employee"

# Password hash qilish
password_hash = bcrypt.hashpw(employee_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

# Admin record yaratish
admin_id = str(uuid.uuid4())

insert_query = """
INSERT INTO admins (id, username, email, full_name, password_hash, role, is_active, created_at, updated_at)
VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
"""

cur.execute(insert_query, (
    admin_id,
    employee_username,
    employee_email,
    employee_full_name,
    password_hash,
    'employee',
    True
))

conn.commit()
print(f"✅ Employee admin record yaratildi: {admin_id}")

# Cleanup
cur.close()
conn.close()