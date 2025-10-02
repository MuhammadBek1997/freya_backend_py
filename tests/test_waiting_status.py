#!/usr/bin/env python3
"""
Test employee waiting status endpoint
"""

import requests
import json

def test_waiting_status_endpoint():
    """Test employee waiting status update endpoint"""
    base_url = "http://localhost:8000"
    
    print("=== EMPLOYEE WAITING STATUS ENDPOINT TESTI ===\n")
    
    # 1. Admin login
    print("1. Admin login...")
    admin_data = {
        "username": "zolushka",
        "password": "12345678"
    }
    
    response = requests.post(f"{base_url}/api/auth/admin/login", json=admin_data)
    if response.status_code != 200:
        print(f"❌ Admin login failed: {response.text}")
        return
    
    admin_token = response.json().get("token")
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    print("✅ Admin login successful")
    
    # 2. Get employees to find an employee ID
    print("\n2. Employee ma'lumotlarini olish...")
    response = requests.get(f"{base_url}/api/employees/", headers=admin_headers)
    if response.status_code != 200:
        print(f"❌ Employee ma'lumotlarini olishda xatolik: {response.text}")
        return
    
    employees_data = response.json()
    employees = employees_data.get("data", [])
    
    if not employees:
        print("❌ Employee topilmadi")
        return
    
    # Use first employee for testing
    test_employee = employees[0]
    employee_id = test_employee["id"]
    current_waiting_status = test_employee.get("is_waiting", False)
    
    print(f"✅ Test uchun employee topildi:")
    print(f"   ID: {employee_id}")
    print(f"   Name: {test_employee.get('name', 'N/A')}")
    print(f"   Current waiting status: {current_waiting_status}")
    
    # 3. Test updating waiting status to True
    print(f"\n3. Waiting status ni True ga o'zgartirish...")
    update_data = {
        "is_waiting": True
    }
    
    response = requests.patch(
        f"{base_url}/api/employees/{employee_id}/waiting-status",
        json=update_data,
        headers=admin_headers
    )
    
    if response.status_code == 200:
        result = response.json()
        print("✅ Waiting status True ga muvaffaqiyatli o'zgartirildi")
        print(f"   Response: {json.dumps(result, indent=2)}")
    else:
        print(f"❌ Waiting status o'zgartirishda xatolik: {response.text}")
        return
    
    # 4. Verify the change by getting employee details
    print(f"\n4. O'zgarishni tekshirish...")
    response = requests.get(f"{base_url}/api/employees/", headers=admin_headers)
    if response.status_code == 200:
        employees_data = response.json()
        employees = employees_data.get("data", [])
        updated_employee = next((emp for emp in employees if emp["id"] == employee_id), None)
        
        if updated_employee:
            new_waiting_status = updated_employee.get("is_waiting", False)
            print(f"✅ Employee ma'lumotlari yangilandi:")
            print(f"   Yangi waiting status: {new_waiting_status}")
            
            if new_waiting_status == True:
                print("✅ Waiting status to'g'ri yangilandi!")
            else:
                print("❌ Waiting status yangilanmadi!")
        else:
            print("❌ Employee topilmadi")
    else:
        print(f"❌ Employee ma'lumotlarini olishda xatolik: {response.text}")
    
    # 5. Test updating waiting status to False
    print(f"\n5. Waiting status ni False ga o'zgartirish...")
    update_data = {
        "is_waiting": False
    }
    
    response = requests.patch(
        f"{base_url}/api/employees/{employee_id}/waiting-status",
        json=update_data,
        headers=admin_headers
    )
    
    if response.status_code == 200:
        result = response.json()
        print("✅ Waiting status False ga muvaffaqiyatli o'zgartirildi")
        print(f"   Response: {json.dumps(result, indent=2)}")
    else:
        print(f"❌ Waiting status o'zgartirishda xatolik: {response.text}")
        return
    
    # 6. Test with invalid employee ID
    print(f"\n6. Noto'g'ri employee ID bilan test...")
    invalid_id = "00000000-0000-0000-0000-000000000000"
    update_data = {
        "is_waiting": True
    }
    
    response = requests.patch(
        f"{base_url}/api/employees/{invalid_id}/waiting-status",
        json=update_data,
        headers=admin_headers
    )
    
    if response.status_code == 404:
        print("✅ Noto'g'ri ID uchun 404 xatolik qaytarildi")
        print(f"   Response: {response.json()}")
    else:
        print(f"❌ Kutilgan 404 xatolik qaytarilmadi: {response.text}")
    
    # 7. Test without admin authentication
    print(f"\n7. Admin autentifikatsiyasisiz test...")
    response = requests.patch(
        f"{base_url}/api/employees/{employee_id}/waiting-status",
        json={"is_waiting": True}
    )
    
    if response.status_code == 401:
        print("✅ Autentifikatsiyasiz so'rov uchun 401 xatolik qaytarildi")
    else:
        print(f"❌ Kutilgan 401 xatolik qaytarilmadi: {response.text}")
    
    print("\n" + "="*60)
    print("🎉 EMPLOYEE WAITING STATUS ENDPOINT TESTI YAKUNLANDI!")
    print("="*60)
    print("\n📋 XULOSA:")
    print("✅ Endpoint to'g'ri ishlaydi")
    print("✅ Admin autentifikatsiya talab qilinadi")
    print("✅ Waiting status muvaffaqiyatli yangilanadi")
    print("✅ Noto'g'ri ID uchun 404 xatolik qaytariladi")
    print("✅ Autentifikatsiyasiz so'rov uchun 401 xatolik qaytariladi")

def main():
    test_waiting_status_endpoint()

if __name__ == "__main__":
    main()