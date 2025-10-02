import requests
import json

base_url = "http://localhost:8000"

def test_employee_login():
    """Employee login testini"""
    print("=== Employee Login Testi ===")
    
    login_data = {
        "username": "test_employee",
        "password": "testpassword123"
    }
    
    response = requests.post(f"{base_url}/api/auth/employee/login", json=login_data)
    
    print(f"Response status: {response.status_code}")
    print(f"Response: {response.text}")
    
    if response.status_code == 200:
        result = response.json()
        print("✅ Employee login muvaffaqiyatli")
        print(f"Token: {result.get('token', 'N/A')[:50]}...")
        print(f"User info: {result.get('user', {})}")
        return result.get('token')
    else:
        print("❌ Employee login xatolik")
        return None

if __name__ == "__main__":
    test_employee_login()