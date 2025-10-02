import psycopg2
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database connection from DATABASE_URL
database_url = os.getenv("DATABASE_URL")
conn = psycopg2.connect(database_url)
cur = conn.cursor()

print("=== Zolushka Employee Tekshiruvi ===\n")

# 1. Employee table da zolushka ni qidirish
print("1. Employee table da 'zolushka' ni qidirish...")
cur.execute("""
    SELECT id, name, username, email, phone, role, profession, salon_id, is_active 
    FROM employees 
    WHERE username = %s OR name ILIKE %s
""", ("zolushka", "%zolushka%"))

employees = cur.fetchall()
if employees:
    print(f"✅ {len(employees)} ta employee topildi:")
    for emp in employees:
        print(f"  ID: {emp[0]}")
        print(f"  Name: {emp[1]}")
        print(f"  Username: {emp[2]}")
        print(f"  Email: {emp[3]}")
        print(f"  Phone: {emp[4]}")
        print(f"  Role: {emp[5]}")
        print(f"  Profession: {emp[6]}")
        print(f"  Salon ID: {emp[7]}")
        print(f"  Active: {emp[8]}")
        print("-" * 40)
        
        employee_id = emp[0]
        employee_username = emp[2]
        
        # 2. Admin table da shu employee uchun record tekshirish
        print(f"2. Admin table da '{employee_username}' uchun record tekshirish...")
        cur.execute("""
            SELECT id, username, role, salon_id, is_active 
            FROM admins 
            WHERE username = %s AND role = 'employee'
        """, (employee_username,))
        
        admin_record = cur.fetchone()
        if admin_record:
            print(f"✅ Admin record topildi:")
            print(f"  Admin ID: {admin_record[0]}")
            print(f"  Username: {admin_record[1]}")
            print(f"  Role: {admin_record[2]}")
            print(f"  Salon ID: {admin_record[3]}")
            print(f"  Active: {admin_record[4]}")
            
            # ID lar mos kelishini tekshirish
            if str(admin_record[0]) == str(employee_id):
                print("✅ Admin ID va Employee ID mos keladi")
            else:
                print(f"❌ Admin ID ({admin_record[0]}) va Employee ID ({employee_id}) mos kelmaydi")
        else:
            print(f"❌ Admin record topilmadi")
            
else:
    print("❌ 'zolushka' employee topilmadi")

# Cleanup
cur.close()
conn.close()