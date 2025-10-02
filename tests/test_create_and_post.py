#!/usr/bin/env python3
"""
Test script: Test auto admin record creation with correct endpoints
"""

import requests
import json

def test_direct_post_creation():
    """Test post creation directly with a known employee ID"""
    base_url = "http://localhost:8000"
    
    # Login as admin first
    admin_login_data = {
        "username": "superadmin",
        "password": "superadmin123"
    }
    
    print("=== Admin Login ===")
    response = requests.post(f"{base_url}/api/auth/admin/login", json=admin_login_data)
    if response.status_code != 200:
        print(f"❌ Admin login failed: {response.text}")
        return False
    
    admin_token = response.json().get("token")
    headers = {"Authorization": f"Bearer {admin_token}"}
    print(f"✅ Admin token olingan")
    
    # Use a test employee ID (we'll create one manually if needed)
    # Let's use a new UUID for testing
    import uuid
    test_employee_id = str(uuid.uuid4())
    
    print(f"\n=== Test Employee ID: {test_employee_id} ===")
    
    # Try to create post for this employee ID
    # This should fail with "Employee not found" first
    post_data = {
        "title": "Auto Admin Test Post",
        "description": "Bu post admin record avtomatik yaratish testida yaratilgan"
    }
    
    print(f"\n=== Post Creation Test (should fail first) ===")
    response = requests.post(
        f"{base_url}/api/employee/{test_employee_id}/posts",
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

def test_with_existing_employee():
    """Test with an employee that we know exists"""
    base_url = "http://localhost:8000"
    
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
    
    # Let's try to get salon info first to see if API is working
    print(f"\n=== Test API Connectivity ===")
    response = requests.get(f"{base_url}/api/salon/", headers=headers)
    print(f"Salon list status: {response.status_code}")
    
    if response.status_code == 200:
        print(f"✅ API ishlayapti")
        salons = response.json().get("data", [])
        print(f"Salon count: {len(salons)}")
        
        if salons:
            salon = salons[0]
            salon_id = salon.get("id")
            print(f"Test salon ID: {salon_id}")
            
            # Now try to get employees for this salon
            print(f"\n=== Get Employees for Salon ===")
            response = requests.get(f"{base_url}/api/employee/salon/{salon_id}", headers=headers)
            print(f"Employees status: {response.status_code}")
            print(f"Response: {response.text}")
            
            if response.status_code == 200:
                employees = response.json().get("data", [])
                print(f"✅ {len(employees)} ta employee topildi")
                
                if employees:
                    employee = employees[0]
                    employee_id = employee.get("id")
                    employee_name = employee.get("name")
                    
                    print(f"Test employee: {employee_name} (ID: {employee_id})")
                    
                    # Test post creation
                    post_data = {
                        "title": f"Auto Admin Test Post for {employee_name}",
                        "description": "Bu post admin record avtomatik yaratish testida yaratilgan"
                    }
                    
                    print(f"\n=== Post Creation Test ===")
                    response = requests.post(
                        f"{base_url}/api/employee/{employee_id}/posts",
                        json=post_data,
                        headers=headers
                    )
                    
                    print(f"Post creation status: {response.status_code}")
                    print(f"Response: {response.text}")
                    
                    if response.status_code == 200:
                        print(f"✅ Post muvaffaqiyatli yaratildi!")
                        return True
                    else:
                        print(f"❌ Post yaratishda xatolik")
                        return False
                else:
                    print(f"❌ Employee lar yo'q")
                    return False
            else:
                print(f"❌ Employee larni olishda xatolik")
                return False
        else:
            print(f"❌ Salon lar yo'q")
            return False
    else:
        print(f"❌ API ishlamayapti: {response.text}")
        return False

def main():
    print("=== Auto Admin Record Creation Test ===\n")
    
    # Test 1: Direct post creation with non-existent employee
    print("Test 1: Non-existent employee")
    test1_success = test_direct_post_creation()
    
    # Test 2: With existing employee
    print("\nTest 2: Existing employee")
    test2_success = test_with_existing_employee()
    
    print(f"\n=== Test Natijalari ===")
    print(f"Non-existent employee test: {'✅' if test1_success else '❌'}")
    print(f"Existing employee test: {'✅' if test2_success else '❌'}")
    
    if test2_success:
        print(f"\n🎉 Admin record avtomatik yaratish ishlayapti!")
    else:
        print(f"\n❌ Admin record avtomatik yaratishda muammo bor!")

if __name__ == "__main__":
    main()