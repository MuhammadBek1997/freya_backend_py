import requests
import json

base_url = "http://localhost:8000/api"

def get_admin_token():
    """Get admin token for authentication"""
    login_data = {
        "username": "superadmin",
        "password": "superadmin123"
    }
    
    response = requests.post(f"{base_url}/auth/admin/login", json=login_data)
    if response.status_code == 200:
        return response.json()["token"]
    else:
        print(f"Admin login xatoligi: {response.text}")
        return None

def test_username_conflict():
    print("=== Username Konflikti Testi ===\n")
    
    # Get admin token
    token = get_admin_token()
    if not token:
        print("Admin token olinmadi!")
        return
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # Get all employees
    response = requests.get(f"{base_url}/employees/")
    if response.status_code != 200:
        print("Employeelarni olishda xatolik!")
        return
    
    employees = response.json()["data"]
    if len(employees) < 2:
        print("Kamida 2 ta employee kerak!")
        return
    
    employee1_id = employees[0]["id"]
    employee2_id = employees[1]["id"]
    
    print(f"Employee 1 ID: {employee1_id}")
    print(f"Employee 2 ID: {employee2_id}")
    
    # Set unique username for employee 2
    print("\n1. Employee 2 ga unique username berish...")
    update_data = {
        "username": "unique_test_username"
    }
    
    response = requests.put(
        f"{base_url}/employees/{employee2_id}",
        json=update_data,
        headers=headers
    )
    
    if response.status_code == 200:
        print("Employee 2 username muvaffaqiyatli o'rnatildi!")
    else:
        print(f"Xatolik: {response.text}")
        return
    
    print("\n" + "="*50 + "\n")
    
    # Try to set employee 1's username to the same as employee 2
    print("2. Employee 1 ga Employee 2 ning username ini berish (xatolik bo'lishi kerak)...")
    update_data = {
        "username": "unique_test_username"
    }
    
    response = requests.put(
        f"{base_url}/employees/{employee1_id}",
        json=update_data,
        headers=headers
    )
    
    print(f"Status: {response.status_code}")
    if response.status_code == 400:
        result = response.json()
        print(f"✅ Kutilgan xatolik: {result['detail']}")
    else:
        print(f"❌ Kutilmagan natija: {response.text}")
    
    print("\n" + "="*50 + "\n")
    print("Test yakunlandi!")

if __name__ == "__main__":
    test_username_conflict()