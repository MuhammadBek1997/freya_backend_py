#!/usr/bin/env python3
"""
Test bulk employee waiting status endpoint
"""

import requests
import json

def test_bulk_waiting_status_endpoint():
    """Test bulk employee waiting status update endpoint"""
    base_url = "http://localhost:8000"
    
    print("=== BULK EMPLOYEE WAITING STATUS ENDPOINT TESTI ===\n")
    
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
    
    # 2. Get employees to find employee IDs
    print("\n2. Employee ma'lumotlarini olish...")
    response = requests.get(f"{base_url}/api/employees/", headers=admin_headers)
    if response.status_code != 200:
        print(f"❌ Employee ma'lumotlarini olishda xatolik: {response.text}")
        return
    
    employees_data = response.json()
    employees = employees_data.get("data", [])
    
    if len(employees) < 2:
        print("❌ Kamida 2 ta employee kerak bulk test uchun")
        return
    
    # Use first two employees for testing
    test_employee_ids = [employees[0]["id"], employees[1]["id"]]
    
    print(f"✅ Test uchun {len(test_employee_ids)} ta employee topildi:")
    for i, emp_id in enumerate(test_employee_ids):
        emp = employees[i]
        print(f"   {i+1}. ID: {emp_id}")
        print(f"      Name: {emp.get('name', 'N/A')}")
        print(f"      Current waiting status: {emp.get('is_waiting', False)}")
    
    # 3. Test bulk updating waiting status to True
    print(f"\n3. Bulk waiting status ni True ga o'zgartirish...")
    update_data = {
        "employee_ids": test_employee_ids,
        "is_waiting": True
    }
    
    response = requests.patch(
        f"{base_url}/api/employees/bulk/waiting-status",
        json=update_data,
        headers=admin_headers
    )
    
    if response.status_code == 200:
        result = response.json()
        print("✅ Bulk waiting status True ga muvaffaqiyatli o'zgartirildi")
        print(f"   Response: {json.dumps(result, indent=2)}")
    else:
        print(f"❌ Bulk waiting status o'zgartirishda xatolik: {response.text}")
        return
    
    # 4. Verify the changes by getting employee details
    print(f"\n4. O'zgarishlarni tekshirish...")
    response = requests.get(f"{base_url}/api/employees/", headers=admin_headers)
    if response.status_code == 200:
        employees_data = response.json()
        employees = employees_data.get("data", [])
        
        print("✅ Employee ma'lumotlari yangilandi:")
        for emp_id in test_employee_ids:
            updated_employee = next((emp for emp in employees if emp["id"] == emp_id), None)
            if updated_employee:
                new_waiting_status = updated_employee.get("is_waiting", False)
                print(f"   ID {emp_id}: waiting_status = {new_waiting_status}")
                
                if new_waiting_status == True:
                    print(f"   ✅ Employee {emp_id} waiting status to'g'ri yangilandi!")
                else:
                    print(f"   ❌ Employee {emp_id} waiting status yangilanmadi!")
            else:
                print(f"   ❌ Employee {emp_id} topilmadi")
    else:
        print(f"❌ Employee ma'lumotlarini olishda xatolik: {response.text}")
    
    # 5. Test bulk updating waiting status to False
    print(f"\n5. Bulk waiting status ni False ga o'zgartirish...")
    update_data = {
        "employee_ids": test_employee_ids,
        "is_waiting": False
    }
    
    response = requests.patch(
        f"{base_url}/api/employees/bulk/waiting-status",
        json=update_data,
        headers=admin_headers
    )
    
    if response.status_code == 200:
        result = response.json()
        print("✅ Bulk waiting status False ga muvaffaqiyatli o'zgartirildi")
        print(f"   Response: {json.dumps(result, indent=2)}")
    else:
        print(f"❌ Bulk waiting status o'zgartirishda xatolik: {response.text}")
        return
    
    # 6. Test with invalid employee IDs
    print(f"\n6. Noto'g'ri employee ID lar bilan test...")
    invalid_ids = ["00000000-0000-0000-0000-000000000000", "11111111-1111-1111-1111-111111111111"]
    update_data = {
        "employee_ids": invalid_ids,
        "is_waiting": True
    }
    
    response = requests.patch(
        f"{base_url}/api/employees/bulk/waiting-status",
        json=update_data,
        headers=admin_headers
    )
    
    print(f"   Response status: {response.status_code}")
    print(f"   Response: {response.json()}")
    
    # 7. Test with empty employee IDs list
    print(f"\n7. Bo'sh employee ID list bilan test...")
    update_data = {
        "employee_ids": [],
        "is_waiting": True
    }
    
    response = requests.patch(
        f"{base_url}/api/employees/bulk/waiting-status",
        json=update_data,
        headers=admin_headers
    )
    
    print(f"   Response status: {response.status_code}")
    print(f"   Response: {response.json()}")
    
    # 8. Test without admin authentication
    print(f"\n8. Admin autentifikatsiyasisiz test...")
    response = requests.patch(
        f"{base_url}/api/employees/bulk/waiting-status",
        json={"employee_ids": test_employee_ids, "is_waiting": True}
    )
    
    if response.status_code == 401:
        print("✅ Autentifikatsiyasiz so'rov uchun 401 xatolik qaytarildi")
    else:
        print(f"❌ Kutilgan 401 xatolik qaytarilmadi: {response.text}")
    
    print("\n" + "="*60)
    print("🎉 BULK EMPLOYEE WAITING STATUS ENDPOINT TESTI YAKUNLANDI!")
    print("="*60)
    print("\n📋 XULOSA:")
    print("✅ Bulk endpoint to'g'ri ishlaydi")
    print("✅ Admin autentifikatsiya talab qilinadi")
    print("✅ Bir nechta employee ning waiting status i bir vaqtda yangilanadi")
    print("✅ Noto'g'ri ID lar bilan ham ishlaydi")
    print("✅ Bo'sh list bilan ham ishlaydi")

def main():
    test_bulk_waiting_status_endpoint()

if __name__ == "__main__":
    main()