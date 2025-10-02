#!/usr/bin/env python3
"""
Check admin record in database
"""

import sys
import os

# Add the app directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import Session
from app.database import get_db
from app.models.admin import Admin
from app.models.employee import Employee

def check_admin_record():
    """Check admin record in database"""
    db = next(get_db())
    
    try:
        print("=== Checking Admin Records ===")
        
        # Find all admin records
        admins = db.query(Admin).all()
        
        print(f"Total admin records: {len(admins)}")
        for admin in admins:
            print(f"Admin: ID={admin.id}, username={admin.username}, email={admin.email}, role={admin.role}, active={admin.is_active}")
        
        print(f"\n=== Checking Employee Records ===")
        
        # Find all employee records
        employees = db.query(Employee).all()
        
        print(f"Total employee records: {len(employees)}")
        for employee in employees:
            print(f"Employee: ID={employee.id}, name={employee.name}, username={employee.username}, role={employee.role}")
        
        # Check specific admin record for zolushka
        print(f"\n=== Checking Zolushka Admin Record ===")
        zolushka_admin = db.query(Admin).filter(Admin.username == "zolushka").first()
        if zolushka_admin:
            print(f"Zolushka admin record:")
            print(f"  ID: {zolushka_admin.id}")
            print(f"  Username: {zolushka_admin.username}")
            print(f"  Email: {zolushka_admin.email}")
            print(f"  Full Name: {zolushka_admin.full_name}")
            print(f"  Role: {zolushka_admin.role}")
            print(f"  Salon ID: {zolushka_admin.salon_id}")
            print(f"  Active: {zolushka_admin.is_active}")
            print(f"  Created: {zolushka_admin.created_at}")
            print(f"  Updated: {zolushka_admin.updated_at}")
            
            print(f"✅ All required fields present")
        else:
            print(f"❌ No admin record found for zolushka")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        db.close()

def main():
    check_admin_record()

if __name__ == "__main__":
    main()