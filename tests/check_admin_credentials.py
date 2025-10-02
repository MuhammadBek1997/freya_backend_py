import requests
import json

base_url = "http://localhost:8000/api"

def test_admin_credentials():
    print("=== Admin Ma'lumotlarini Tekshirish ===\n")
    
    # Test different admin credentials
    credentials = [
        {"username": "superadmin", "password": "superadmin123"},
        {"username": "admin", "password": "admin123"},
        {"username": "superadmin", "password": "admin123"},
        {"username": "admin", "password": "superadmin123"}
    ]
    
    for i, cred in enumerate(credentials, 1):
        print(f"{i}. Username: {cred['username']}, Password: {cred['password']}")
        
        response = requests.post(f"{base_url}/auth/admin/login", json=cred)
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            print(f"   ✅ Muvaffaqiyat! Token: {response.json().get('token', 'N/A')[:50]}...")
            break
        else:
            print(f"   ❌ Xatolik: {response.text}")
        print()
    
    # Check if there are any admins in the database
    print("\n" + "="*50)
    print("Admin ma'lumotlarini database dan tekshirish...")
    
    # Try to get all users to see if there are any admins
    response = requests.get(f"{base_url}/users/")
    if response.status_code == 200:
        users = response.json().get("data", [])
        print(f"Jami foydalanuvchilar: {len(users)}")
        
        admins = [user for user in users if user.get("role") in ["admin", "superadmin"]]
        print(f"Admin foydalanuvchilar: {len(admins)}")
        
        for admin in admins:
            print(f"  - {admin.get('username', 'N/A')} ({admin.get('role', 'N/A')})")
    else:
        print(f"Foydalanuvchilarni olishda xatolik: {response.text}")

if __name__ == "__main__":
    test_admin_credentials()