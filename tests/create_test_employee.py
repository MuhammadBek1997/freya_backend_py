import requests
import json

base_url = "http://localhost:8000/api"

def get_admin_token():
    """Admin token olish"""
    admin_data = {
        "username": "superadmin",
        "password": "superadmin123"
    }
    
    response = requests.post(f"{base_url}/auth/superadmin/login", json=admin_data)
    
    if response.status_code == 200:
        return response.json().get("token")
    else:
        print(f"Admin login xatoligi: {response.text}")
        return None

def get_first_salon_id(admin_token):
    """Birinchi salon ID sini olish"""
    headers = {"Authorization": f"Bearer {admin_token}"}
    response = requests.get(f"{base_url}/admin/salons", headers=headers)
    
    if response.status_code == 200:
        salons_data = response.json()
        # Response list bo'lsa
        if isinstance(salons_data, list) and salons_data:
            return salons_data[0]["id"]
        # Response object bo'lsa
        elif isinstance(salons_data, dict):
            salons = salons_data.get("data", [])
            if salons:
                return salons[0]["id"]
    
    print(f"Salon topilmadi: {response.text}")
    return None

def create_test_employee():
    """Test uchun employee yaratish"""
    print("=== Test Employee Yaratish ===")
    
    # Admin token olish
    admin_token = get_admin_token()
    if not admin_token:
        print("❌ Admin token olinmadi")
        return
    
    # Salon ID olish
    salon_id = get_first_salon_id(admin_token)
    if not salon_id:
        print("❌ Salon topilmadi")
        return
    
    # Employee ma'lumotlari
    employee_data = {
        "salon_id": salon_id,
        "employee_name": "Test Employee",
        "employee_phone": "+998901111111",
        "employee_email": "test_employee@example.com",
        "role": "employee",
        "username": "test_employee",
        "profession": "test_profession",
        "employee_password": "testpassword123"
    }
    
    headers = {"Authorization": f"Bearer {admin_token}"}
    response = requests.post(f"{base_url}/employees", json=employee_data, headers=headers)
    
    if response.status_code == 200:
        print("✅ Test employee muvaffaqiyatli yaratildi")
        result = response.json()
        print(f"Employee ID: {result['data']['id']}")
        print(f"Username: {result['data']['username']}")
        print(f"Password: testpassword123")
        return result['data']['id']
    else:
        print(f"❌ Employee yaratishda xatolik: {response.status_code}")
        print(f"Response: {response.text}")
        return None

if __name__ == "__main__":
    create_test_employee()