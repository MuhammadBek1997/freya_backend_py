#!/usr/bin/env python3
"""
Reset admin record for employee
"""

import requests

def reset_admin_record():
    """Delete existing admin record and create new post to trigger recreation"""
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
    
    # Get employee
    print(f"\n=== Get Employee ===")
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
    
    employees_data = employees_response.json()
    employees = employees_data.get("data", []) if employees_data.get("success") else employees_data.get("employees", [])
    if not employees:
        print("❌ No employees found")
        print(f"Response: {employees_response.text}")
        return
    
    employee = employees[0]
    employee_id = employee["id"]
    employee_name = employee["name"]
    
    print(f"✅ Employee: {employee_name} (ID: {employee_id})")
    
    # Create another post to trigger admin record creation with new role
    print(f"\n=== Create New Post ===")
    post_data = {
        "title": "Test Admin Role Fix",
        "description": "Bu post admin role ni to'g'rilash uchun yaratilgan"
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
        
        # Now try to login with admin credentials
        print(f"\n=== Test Admin Login After Fix ===")
        admin_login_data = {
            "username": employee_name.lower().replace(" ", "_"),
            "password": "12345678"
        }
        
        admin_response = requests.post(f"{base_url}/api/auth/admin/login", json=admin_login_data)
        print(f"Admin login status: {admin_response.status_code}")
        print(f"Admin login response: {admin_response.text}")
        
        if admin_response.status_code == 200:
            admin_token = admin_response.json().get("token")
            admin_headers = {"Authorization": f"Bearer {admin_token}"}
            
            # Check the role in token
            user_data = admin_response.json().get("user", {})
            role = user_data.get("role")
            print(f"Token role: {role}")
            
            # Try to access admin profile
            profile_response = requests.get(f"{base_url}/api/auth/admin/profile", headers=admin_headers)
            print(f"\nAdmin profile status: {profile_response.status_code}")
            print(f"Admin profile: {profile_response.text}")
            
            if profile_response.status_code == 200:
                print(f"🎉 Admin role fix muvaffaqiyatli!")
                return True
            else:
                print(f"❌ Admin profile access still failed!")
                return False
        else:
            print(f"❌ Admin login failed!")
            return False
    else:
        print(f"❌ Post creation failed!")
        return False

def main():
    print("=== Reset Admin Record Test ===\n")
    success = reset_admin_record()
    
    if success:
        print(f"\n🎉 Admin record reset va role fix muvaffaqiyatli!")
    else:
        print(f"\n❌ Admin record reset da muammo bor!")

if __name__ == "__main__":
    main()