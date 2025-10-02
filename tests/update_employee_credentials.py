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

# Employee ID va credentials
employee_id = "676193c7-c9f1-410e-88e4-4d5b737455c3"
username = "test_employee"
password = "testpassword123"

# Password hash qilish
password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

# Employee credentials ni yangilash
update_query = """
UPDATE employees 
SET username = %s, employee_password = %s, updated_at = NOW()
WHERE id = %s
"""

cur.execute(update_query, (username, password_hash, employee_id))
conn.commit()

print(f"✅ Employee credentials yangilandi:")
print(f"   Username: {username}")
print(f"   Password: {password}")

# Tekshirish
cur.execute("SELECT id, name, username, email FROM employees WHERE id = %s", (employee_id,))
result = cur.fetchone()
print(f"Employee ma'lumotlari: ID={result[0]}, Name={result[1]}, Username={result[2]}, Email={result[3]}")

# Cleanup
cur.close()
conn.close()