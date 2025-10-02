#!/usr/bin/env python3
import requests

# Login as admin
admin_login_data = {
    "username": "superadmin",
    "password": "superadmin123"
}

response = requests.post("http://localhost:8000/api/auth/admin/login", json=admin_login_data)
if response.status_code != 200:
    print(f"❌ Admin login failed: {response.text}")
    exit(1)

admin_token = response.json().get("token")
headers = {"Authorization": f"Bearer {admin_token}"}
print(f"✅ Admin token olingan")

# Test salon endpoint
print(f"\n=== Test Salon Endpoint ===")
response = requests.get("http://localhost:8000/api/salons/", headers=headers)
print(f"Status: {response.status_code}")
print(f"Response: {response.text}")

if response.status_code == 200:
    response_data = response.json()
    salons = response_data.get("salons", [])
    print(f"✅ {len(salons)} ta salon topildi")
    
    if salons:
        salon = salons[0]
        salon_id = salon.get("id")
        print(f"Test salon ID: {salon_id}")
        
        # Test employee endpoint for this salon
        print(f"\n=== Test Employee Endpoint ===")
        response = requests.get(f"http://localhost:8000/api/employees/salon/{salon_id}", headers=headers)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            employees = response.json().get("data", [])
            print(f"✅ {len(employees)} ta employee topildi")
            
            if employees:
                employee = employees[0]
                employee_id = employee.get("id")
                employee_name = employee.get("name")
                print(f"Test employee: {employee_name} (ID: {employee_id})")
                
                # Test post creation for this employee
                post_data = {
                    "title": "Test Auto Admin Creation",
                    "description": "Bu post admin record avtomatik yaratish testida yaratilgan"
                }
                
                print(f"\n=== Test Post Creation ===")
                response = requests.post(
                    f"http://localhost:8000/api/employees/{employee_id}/posts",
                    json=post_data,
                    headers=headers
                )
                print(f"Status: {response.status_code}")
                print(f"Response: {response.text}")
                
                if response.status_code == 200:
                    print(f"✅ Post muvaffaqiyatli yaratildi!")
                    print(f"🎉 Admin record avtomatik yaratish ishlayapti!")
                else:
                    print(f"❌ Post yaratishda xatolik")
            else:
                print(f"❌ Employee lar yo'q")
        else:
            print(f"❌ Employee endpoint ishlamayapti")
    else:
        print(f"❌ Salon lar yo'q")
else:
    print(f"❌ Salon endpoint ishlamayapti")