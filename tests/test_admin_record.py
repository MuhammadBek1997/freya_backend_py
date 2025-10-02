#!/usr/bin/env python3
"""
Test script: Check if admin record was created automatically
"""

import requests

def test_admin_login():
    """Test if the auto-created admin record can login"""
    base_url = "http://localhost:8000"
    
    # Try to login with auto-generated credentials
    # Username should be "zolushka" (employee name)
    # Password should be "12345678" (default password)
    
    admin_login_data = {
        "username": "zolushka",
        "password": "12345678"
    }
    
    print("=== Test Auto-Created Admin Login ===")
    response = requests.post(f"{base_url}/api/auth/admin/login", json=admin_login_data)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
    
    if response.status_code == 200:
        print(f"✅ Avtomatik yaratilgan admin record bilan login muvaffaqiyatli!")
        
        # Get admin profile
        token = response.json().get("token")
        headers = {"Authorization": f"Bearer {token}"}
        
        profile_response = requests.get(f"{base_url}/api/auth/admin/profile", headers=headers)
        print(f"\n=== Admin Profile ===")
        print(f"Profile status: {profile_response.status_code}")
        print(f"Profile: {profile_response.text}")
        
        return True
    else:
        print(f"❌ Avtomatik yaratilgan admin record bilan login muvaffaqiyatsiz!")
        return False

def test_employee_login():
    """Test if employee can still login as employee"""
    base_url = "http://localhost:8000"
    
    # Try employee login
    employee_login_data = {
        "username": "zolushka",
        "password": "12345678"
    }
    
    print(f"\n=== Test Employee Login ===")
    response = requests.post(f"{base_url}/api/auth/employee/login", json=employee_login_data)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
    
    if response.status_code == 200:
        print(f"✅ Employee login ham ishlayapti!")
        return True
    else:
        print(f"❌ Employee login ishlamayapti!")
        return False

def main():
    print("=== Auto-Created Admin Record Test ===\n")
    
    # Test admin login
    admin_success = test_admin_login()
    
    # Test employee login
    employee_success = test_employee_login()
    
    print(f"\n=== Test Natijalari ===")
    print(f"Admin login: {'✅' if admin_success else '❌'}")
    print(f"Employee login: {'✅' if employee_success else '❌'}")
    
    if admin_success:
        print(f"\n🎉 Admin record avtomatik yaratish to'liq ishlayapti!")
        print(f"Employee uchun admin record yaratildi va login qilish mumkin!")
    else:
        print(f"\n❌ Admin record yaratishda muammo bor!")

if __name__ == "__main__":
    main()