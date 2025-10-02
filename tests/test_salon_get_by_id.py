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

def test_get_salon_by_id():
    print("=== Salon ID bo'yicha Salon Olish Testini ===\n")
    
    # Get admin token
    token = get_admin_token()
    if not token:
        print("Admin token olinmadi!")
        return
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # First, get all salons to find an existing salon ID
    print("1. Mavjud salonlarni olish...")
    response = requests.get(f"{base_url}/salons/")
    
    if response.status_code == 200:
        salons_data = response.json()
        salons = salons_data.get("salons", [])
        
        if not salons:
            print("❌ Hech qanday salon topilmadi! Avval salon yarating.")
            return
        
        salon_id = salons[0]["id"]
        print(f"✅ Test uchun salon ID: {salon_id}")
        
        # Test 2: Get salon by ID
        print(f"\n2. Salon ID bo'yicha salon olish: {salon_id}")
        response = requests.get(f"{base_url}/salons/{salon_id}")
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            salon_data = response.json()
            print("✅ Salon muvaffaqiyatli olindi!")
            print(f"Salon nomi: {salon_data.get('salon_name', 'N/A')}")
            print(f"Salon telefoni: {salon_data.get('salon_phone', 'N/A')}")
            print(f"Salon ID: {salon_data.get('id', 'N/A')}")
        else:
            print("❌ Salon olishda xatolik!")
            print(f"Response: {response.text}")
        
        # Test 3: Get non-existing salon
        print(f"\n3. Mavjud bo'lmagan salon ID bilan test...")
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = requests.get(f"{base_url}/salons/{fake_id}")
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 404:
            print("✅ Mavjud bo'lmagan salon uchun kutilgan xatolik!")
        else:
            print("❌ Mavjud bo'lmagan salon uchun kutilmagan natija!")
            print(f"Response: {response.text}")
        
        # Test 4: Get salon with invalid ID format
        print(f"\n4. Noto'g'ri ID format bilan test...")
        invalid_id = "invalid-id-format"
        response = requests.get(f"{base_url}/salons/{invalid_id}")
        
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
        
    else:
        print(f"❌ Salonlarni olishda xatolik: {response.text}")
    
    print("\n" + "="*50)
    print("Test yakunlandi!")

if __name__ == "__main__":
    test_get_salon_by_id()