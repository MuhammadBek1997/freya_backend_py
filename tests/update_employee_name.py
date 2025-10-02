import psycopg2
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database connection from DATABASE_URL
database_url = os.getenv("DATABASE_URL")
conn = psycopg2.connect(database_url)
cur = conn.cursor()

# Employee ID va yangi name
employee_id = "676193c7-c9f1-410e-88e4-4d5b737455c3"
new_name = "test_employee"  # Admin username bilan mos kelishi kerak

# Employee name ni yangilash
update_query = """
UPDATE employees 
SET name = %s, updated_at = NOW()
WHERE id = %s
"""

cur.execute(update_query, (new_name, employee_id))
conn.commit()

print(f"✅ Employee name yangilandi: {new_name}")

# Tekshirish
cur.execute("SELECT id, name, email FROM employees WHERE id = %s", (employee_id,))
result = cur.fetchone()
print(f"Employee ma'lumotlari: ID={result[0]}, Name={result[1]}, Email={result[2]}")

# Cleanup
cur.close()
conn.close()