#!/usr/bin/env python3
"""
Test script: Create post for second employee to test admin record creation
"""

import requests

def test_new_admin_creation():
    """Test admin record creation for second employee"""
    base_url = "http://localhost:8000"
    
    # Login as superadmin
    admin_login_data = {
        "username": "superadmin",
        "password": "superadmin123"
    }
    
    print("=== Superadmin Login ===")
    response = requests.post(f"{base_url}/api/auth/superadmin/login", json=admin_login_data)
    print(f"Status: {response.status_code}")
    
    if response.status_code != 200:
        print("❌ Superadmin login failed!")
        return
    
    token = response.json().get("token")
    headers = {"Authorization": f"Bearer {token}"}
    
    # Get employees
    print(f"\n=== Get Employees ===")
    salon_response = requests.get(f"{base_url}/api/salons/", headers=headers)
    if salon_response.status_code != 200:
        print("❌ Failed to get salons")
        return
    
    salons = salon_response.json().get("salons", [])
    if not salons:
        print("❌ No salons found")
        return
    
    salon_id = salons[0]["id"]
    employees_response = requests.get(f"{base_url}/api/employees/salon/{salon_id}", headers=headers)
    
    if employees_response.status_code != 200:
        print("❌ Failed to get employees")
        return
    
    employees = employees_response.json().get("employees", [])
    if len(employees) < 2:
        print("❌ Need at least 2 employees for test")
        return
    
    # Use second employee (xolida)
    second_employee = employees[1]
    employee_id = second_employee["id"]
    employee_name = second_employee["name"]
    
    print(f"✅ Using second employee: {employee_name} (ID: {employee_id})")
    
    # Create post for second employee
    print(f"\n=== Create Post for Second Employee ===")
    post_data = {
        "title": "Test Admin Creation for Second Employee",
        "description": "Bu ikkinchi employee uchun admin record yaratish testi"
    }
    
    post_response = requests.post(
        f"{base_url}/api/employees/{employee_id}/posts",
        json=post_data,
        headers=headers
    )
    
    print(f"Post creation status: {post_response.status_code}")
    print(f"Post response: {post_response.text}")
    
    if post_response.status_code == 200:
        print(f"✅ Post created successfully!")
        
        # Now try to login with the new admin record
        print(f"\n=== Test New Admin Login ===")
        new_admin_login_data = {
            "username": employee_name.lower().replace(" ", "_"),
            "password": "12345678"
        }
        
        admin_response = requests.post(f"{base_url}/api/auth/admin/login", json=new_admin_login_data)
        print(f"Admin login status: {admin_response.status_code}")
        print(f"Admin login response: {admin_response.text}")
        
        if admin_response.status_code == 200:
            admin_token = admin_response.json().get("token")
            admin_headers = {"Authorization": f"Bearer {admin_token}"}
            
            # Try to access admin profile
            profile_response = requests.get(f"{base_url}/api/auth/admin/profile", headers=admin_headers)
            print(f"\nAdmin profile status: {profile_response.status_code}")
            print(f"Admin profile: {profile_response.text}")
            
            if profile_response.status_code == 200:
                print(f"🎉 Admin record yaratish va login muvaffaqiyatli!")
                return True
            else:
                print(f"❌ Admin profile access failed!")
                return False
        else:
            print(f"❌ Admin login failed!")
            return False
    else:
        print(f"❌ Post creation failed!")
        return False

def main():
    print("=== New Admin Creation Test ===\n")
    success = test_new_admin_creation()
    
    if success:
        print(f"\n🎉 Yangi admin record yaratish to'liq ishlayapti!")
    else:
        print(f"\n❌ Admin record yaratishda muammo bor!")

if __name__ == "__main__":
    main()