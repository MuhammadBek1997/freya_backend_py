import requests
import json

base_url = "http://localhost:8000/api"

def get_admin_token():
    """Admin token olish"""
    admin_data = {
        "username": "superadmin",
        "password": "superadminpassword"
    }
    
    response = requests.post(f"{base_url}/auth/admin/login", json=admin_data)
    
    if response.status_code == 200:
        return response.json().get("token")
    else:
        print(f"Admin login xatoligi: {response.text}")
        return None

def test_salon_create():
    print("=== Salon Yaratish Endpointini Test Qilish ===\n")
    
    # Get admin token
    token = get_admin_token()
    if not token:
        print("Admin token olinmadi!")
        return
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # Test 1: Minimal salon data
    print("1. Minimal ma'lumotlar bilan salon yaratish...")
    salon_data = {
        "salon_name": "Test Salon",
        "salon_phone": "+998901234567"
    }
    
    response = requests.post(f"{base_url}/salons/", json=salon_data, headers=headers)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
    
    if response.status_code == 201:
        print("✅ Minimal salon muvaffaqiyatli yaratildi!")
    else:
        print("❌ Minimal salon yaratishda xatolik!")
    
    print("\n" + "="*50 + "\n")
    
    # Test 2: Full salon data
    print("2. To'liq ma'lumotlar bilan salon yaratish...")
    full_salon_data = {
        "salon_name": "Professional Beauty Center",
        "salon_phone": "+998901234568",
        "salon_instagram": "@professional_beauty",
        "salon_rating": 4.5,
        "salon_description": "Professional beauty salon",
        "salon_types": [
            {"type": "Beauty Salon", "selected": True},
            {"type": "Massage", "selected": True}
        ],
        "private_salon": False,
        "location": {
            "latitude": 41.2995,
            "longitude": 69.2401
        },
        "salon_comfort": [
            {"name": "parking", "isActive": True},
            {"name": "cafee", "isActive": False}
        ],
        "is_private": False,
        "description_uz": "Professional go'zallik saloni",
        "description_ru": "Профессиональный салон красоты",
        "description_en": "Professional beauty salon",
        "address_uz": "Toshkent shahar",
        "address_ru": "Город Ташкент",
        "address_en": "Tashkent city"
    }
    
    response = requests.post(f"{base_url}/salons/", json=full_salon_data, headers=headers)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
    
    if response.status_code == 201:
        print("✅ To'liq salon muvaffaqiyatli yaratildi!")
    else:
        print("❌ To'liq salon yaratishda xatolik!")
    
    print("\n" + "="*50 + "\n")
    
    # Test 3: Invalid data (empty salon_name)
    print("3. Noto'g'ri ma'lumotlar bilan salon yaratish (bo'sh salon_name)...")
    invalid_data = {
        "salon_name": "",
        "salon_phone": "+998901234569"
    }
    
    response = requests.post(f"{base_url}/salons/", json=invalid_data, headers=headers)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
    
    if response.status_code == 400:
        print("✅ Bo'sh salon_name uchun kutilgan xatolik!")
    else:
        print("❌ Bo'sh salon_name uchun kutilmagan natija!")
    
    print("\n" + "="*50 + "\n")
    
    # Test 4: Without authentication
    print("4. Autentifikatsiyasiz salon yaratish...")
    response = requests.post(f"{base_url}/salons/", json=salon_data)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
    
    if response.status_code == 401 or response.status_code == 403:
        print("✅ Autentifikatsiyasiz uchun kutilgan xatolik!")
    else:
        print("❌ Autentifikatsiyasiz uchun kutilmagan natija!")
    
    print("\n" + "="*50 + "\n")
    print("Test yakunlandi!")

if __name__ == "__main__":
    test_salon_create()