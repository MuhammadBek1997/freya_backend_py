import psycopg2
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database connection from DATABASE_URL
database_url = os.getenv("DATABASE_URL")
conn = psycopg2.connect(database_url)
cur = conn.cursor()

# Employee ID
employee_id = "676193c7-c9f1-410e-88e4-4d5b737455c3"

# Admin record ni employee ID bilan yangilash
update_query = """
UPDATE admins 
SET id = %s, updated_at = NOW()
WHERE username = 'test_employee' AND role = 'employee'
"""

cur.execute(update_query, (employee_id,))
conn.commit()

print(f"✅ Admin record ID yangilandi: {employee_id}")

# Tekshirish
cur.execute("SELECT id, username, role FROM admins WHERE id = %s", (employee_id,))
result = cur.fetchone()
if result:
    print(f"Admin record: ID={result[0]}, Username={result[1]}, Role={result[2]}")
else:
    print("❌ Admin record topilmadi")

# Cleanup
cur.close()
conn.close()