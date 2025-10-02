#!/usr/bin/env python3
"""
Fix admin role directly in database
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import Session
from app.database import get_db
from app.models.admin import Admin
from app.models.employee import Employee

def fix_admin_role():
    """Fix admin role in database"""
    db = next(get_db())
    
    try:
        # Find employee
        employee = db.query(Employee).filter(Employee.name == "zolushka").first()
        if not employee:
            print("❌ Employee 'zolushka' not found")
            return False
        
        print(f"✅ Employee found: {employee.name} (ID: {employee.id})")
        
        # Find admin record
        admin = db.query(Admin).filter(Admin.id == employee.id).first()
        if not admin:
            print("❌ Admin record not found")
            return False
        
        print(f"✅ Admin record found: {admin.username} (Role: {admin.role})")
        
        # Update admin role
        admin.role = "admin"
        db.commit()
        
        print(f"✅ Admin role updated to: {admin.role}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
        return False
    finally:
        db.close()

def test_admin_login():
    """Test admin login after role fix"""
    import requests
    
    base_url = "http://localhost:8000"
    admin_login_data = {
        "username": "zolushka",
        "password": "12345678"
    }
    
    print(f"\n=== Test Admin Login ===")
    response = requests.post(f"{base_url}/api/auth/admin/login", json=admin_login_data)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
    
    if response.status_code == 200:
        token = response.json().get("token")
        headers = {"Authorization": f"Bearer {token}"}
        
        # Check user data in response
        user_data = response.json().get("user", {})
        role = user_data.get("role")
        print(f"Token role: {role}")
        
        # Try to access admin profile
        profile_response = requests.get(f"{base_url}/api/auth/admin/profile", headers=headers)
        print(f"\nAdmin profile status: {profile_response.status_code}")
        print(f"Admin profile: {profile_response.text}")
        
        if profile_response.status_code == 200:
            print(f"🎉 Admin role fix muvaffaqiyatli!")
            return True
        else:
            print(f"❌ Admin profile access failed!")
            return False
    else:
        print(f"❌ Admin login failed!")
        return False

def main():
    print("=== Fix Admin Role in Database ===\n")
    
    # Fix admin role
    db_success = fix_admin_role()
    
    if db_success:
        # Test admin login
        login_success = test_admin_login()
        
        if login_success:
            print(f"\n🎉 Admin role fix va test muvaffaqiyatli!")
        else:
            print(f"\n❌ Admin login test muvaffaqiyatsiz!")
    else:
        print(f"\n❌ Database da admin role fix muvaffaqiyatsiz!")

if __name__ == "__main__":
    main()