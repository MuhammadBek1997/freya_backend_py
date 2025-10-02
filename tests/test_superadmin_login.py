import requests
import json

base_url = "http://localhost:8000/api"

def test_superadmin_login():
    """Superadmin login testlari"""
    print("=== Superadmin Login Test ===")
    
    # Turli parollarni sinab ko'rish
    passwords = [
        "superadmin123",
        "superadmin",
        "admin123",
        "password",
        "123456",
        "password123"
    ]
    
    for password in passwords:
        print(f"\nTesting password: {password}")
        
        admin_data = {
            "username": "superadmin",
            "password": password
        }
        
        try:
            response = requests.post(f"{base_url}/auth/superadmin/login", json=admin_data)
            
            if response.status_code == 200:
                print(f"✅ SUCCESS! Password: {password}")
                result = response.json()
                print(f"Token: {result.get('token', 'No token')[:50]}...")
                return password
            else:
                print(f"❌ Failed: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"❌ Error: {e}")
    
    print("\n❌ Hech qaysi parol ishlamadi")
    return None

if __name__ == "__main__":
    test_superadmin_login()