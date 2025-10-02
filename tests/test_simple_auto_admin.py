#!/usr/bin/env python3
"""
Simple test for automatic admin record creation using known employee
"""

import requests
import json

def test_auto_admin_creation():
    """Test automatic admin record creation with known employee"""
    base_url = "http://localhost:8000"
    
    print("=== Auto Admin Record Creation Test ===\n")
    
    # Use known employee ID (we'll create a new test employee)
    test_employee_id = "639ea749-59a1-4f40-a919-34a47f40f5dd"  # Zolushka's ID
    test_employee_name = "zolushka"
    
    # Step 1: Login as admin to get token
    admin_login_data = {
        "username": "superadmin",
        "password": "superadmin123"
    }
    
    print("=== Admin Login ===")
    response = requests.post(f"{base_url}/api/auth/admin/login", json=admin_login_data)
    print(f"Login status: {response.status_code}")
    
    if response.status_code != 200:
        print(f"❌ Admin login failed: {response.text}")
        return False
    
    admin_token = response.json().get("token")
    print(f"✅ Admin token olingan")
    
    # Step 2: Check if employee exists
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    print(f"\n=== Employee Check ===")
    response = requests.get(f"{base_url}/api/employee/{test_employee_id}", headers=headers)
    print(f"Employee check status: {response.status_code}")
    
    if response.status_code != 200:
        print(f"❌ Employee topilmadi: {response.text}")
        return False
    
    employee_data = response.json().get("data", {})
    print(f"✅ Employee topildi: {employee_data.get('name', 'Unknown')}")
    
    # Step 3: Try to create post for this employee (this should trigger auto admin creation if needed)
    post_data = {
        "title": f"Auto Admin Test Post for {test_employee_name}",
        "description": f"Bu post {test_employee_name} uchun admin record avtomatik yaratish testida yaratilgan"
    }
    
    print(f"\n=== Post Creation Test ===")
    response = requests.post(
        f"{base_url}/api/employee/{test_employee_id}/posts",
        json=post_data,
        headers=headers
    )
    
    print(f"Post creation status: {response.status_code}")
    print(f"Response: {response.text}")
    
    if response.status_code == 200:
        print(f"✅ Post muvaffaqiyatli yaratildi!")
        response_data = response.json()
        if "data" in response_data:
            post_id = response_data["data"].get("id")
            print(f"Post ID: {post_id}")
        return True
    else:
        print(f"❌ Post yaratishda xatolik")
        # Print more details about the error
        try:
            error_data = response.json()
            print(f"Error details: {error_data}")
        except:
            pass
        return False

def test_with_new_employee():
    """Test with a completely new employee ID"""
    base_url = "http://localhost:8000"
    
    print("\n=== Test with New Employee ID ===")
    
    # Use a new UUID that doesn't exist
    import uuid
    new_employee_id = str(uuid.uuid4())
    
    # Login as admin
    admin_login_data = {
        "username": "superadmin", 
        "password": "superadmin123"
    }
    
    response = requests.post(f"{base_url}/api/auth/admin/login", json=admin_login_data)
    if response.status_code != 200:
        print(f"❌ Admin login failed")
        return False
    
    admin_token = response.json().get("token")
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    # Try to create post for non-existent employee
    post_data = {
        "title": "Test Post for Non-existent Employee",
        "description": "This should fail because employee doesn't exist"
    }
    
    print(f"Testing with non-existent employee ID: {new_employee_id}")
    response = requests.post(
        f"{base_url}/api/employee/{new_employee_id}/posts",
        json=post_data,
        headers=headers
    )
    
    print(f"Post creation status: {response.status_code}")
    print(f"Response: {response.text}")
    
    if response.status_code == 404:
        print(f"✅ To'g'ri: Employee topilmadi (kutilganidek)")
        return True
    else:
        print(f"❌ Kutilmagan natija")
        return False

def main():
    # Test 1: With existing employee
    success1 = test_auto_admin_creation()
    
    # Test 2: With non-existent employee (should fail properly)
    success2 = test_with_new_employee()
    
    print(f"\n=== Test Natijalari ===")
    print(f"Mavjud employee bilan test: {'✅' if success1 else '❌'}")
    print(f"Mavjud bo'lmagan employee bilan test: {'✅' if success2 else '❌'}")
    
    if success1:
        print(f"🎉 Admin record avtomatik yaratish ishlayapti!")
    else:
        print(f"❌ Admin record avtomatik yaratishda muammo bor!")

if __name__ == "__main__":
    main()