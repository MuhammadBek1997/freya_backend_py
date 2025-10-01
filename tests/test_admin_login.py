import requests
import json

base_url = "http://localhost:8000/api"

def test_admin_login():
    print("=== Admin Login Test ===")
    
    login_data = {
        "username": "superadmin",
        "password": "superadmin123"
    }
    
    response = requests.post(f"{base_url}/auth/admin/login", json=login_data)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"Response keys: {list(data.keys())}")

if __name__ == "__main__":
    test_admin_login()