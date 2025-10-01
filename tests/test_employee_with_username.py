import requests
import json

# API base URL
BASE_URL = "http://localhost:8000"

# Admin login credentials
admin_credentials = {
    "username": "superadmin",
    "password": "superadmin123"
}

# Login as admin
print("Admin sifatida login qilish...")
login_response = requests.post(f"{BASE_URL}/api/admin/login", json=admin_credentials)
print(f"Login status: {login_response.status_code}")

if login_response.status_code == 200:
    login_data = login_response.json()
    print(f"Login response: {login_data}")
    
    # Get token
    token = login_data.get("token")
    if token:
        print(f"Token olindi: {token[:20]}...")
        
        # Headers with token
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        # Employee data with username and profession
        employee_data = {
            "salon_id": "a8be0e5f-d78f-4574-a383-2bf23f80f1b0",
            "employee_name": "Test Employee",
            "employee_phone": "+998901234567",
            "employee_email": "test.employee@example.com",
            "role": "stylist",
            "employee_password": "password123",
            "username": "testemployee",
            "profession": "Hair Stylist"
        }
        
        # Create employee
        print("\nEmployee yaratish...")
        create_response = requests.post(
            f"{BASE_URL}/api/employees/",
            json=employee_data,
            headers=headers
        )
        
        print(f"Employee yaratish status: {create_response.status_code}")
        print(f"Response: {create_response.text}")
        
        if create_response.status_code == 200:
            response_data = create_response.json()
            print("\nEmployee muvaffaqiyatli yaratildi!")
            print(f"Employee ma'lumotlari: {json.dumps(response_data, indent=2, ensure_ascii=False)}")
        else:
            print(f"Employee yaratishda xatolik: {create_response.text}")
    else:
        print("Token topilmadi!")
else:
    print(f"Login xatolik: {login_response.text}")