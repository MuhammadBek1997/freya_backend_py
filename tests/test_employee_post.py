import requests
import json

base_url = "http://localhost:8000"

def get_admin_token():
    """Admin token olish"""
    admin_data = {
        "username": "superadmin",
        "password": "superadmin123"
    }
    
    response = requests.post(f"{base_url}/api/auth/superadmin/login", json=admin_data)
    
    if response.status_code == 200:
        return response.json().get("token")
    else:
        print(f"Admin login xatoligi: {response.text}")
        return None

def get_employee_token():
    """Employee token olish (test uchun)"""
    # Mavjud employee ma'lumotlari
    employee_data = {
        "username": "test_employee",  # Mavjud employee username
        "password": "testpassword123"  # Default password
    }
    
    # Employee login endpoint
    response = requests.post(f"{base_url}/api/auth/employee/login", json=employee_data)
    
    if response.status_code == 200:
        return response.json().get("token")
    else:
        print(f"Employee login xatoligi: {response.text}")
        return None

def get_employee_info():
    """Employee ma'lumotlarini olish"""
    # Bu yerda mavjud employee ID sini qo'yish kerak
    return "676193c7-c9f1-410e-88e4-4d5b737455c3"  # Test employee ID

def test_add_post_with_admin():
    """Admin bilan post qo'shish testi"""
    print("=== Admin bilan post qo'shish testi ===")
    
    admin_token = get_admin_token()
    if not admin_token:
        print("❌ Admin token olinmadi")
        return
    
    employee_id = get_employee_info()
    if not employee_id:
        print("❌ Employee topilmadi")
        return
    
    print(f"Employee ID: {employee_id}")
    
    post_data = {
        "title": "Test Post by Admin",
        "description": "Bu admin tomonidan yaratilgan test post",
        "media": []
    }
    
    headers = {"Authorization": f"Bearer {admin_token}"}
    response = requests.post(f"{base_url}/api/employees/{employee_id}/posts", json=post_data, headers=headers)
    
    print(f"Response status: {response.status_code}")
    print(f"Response: {response.text}")
    
    if response.status_code == 200:
        print("✅ Admin post qo'shish muvaffaqiyatli")
    else:
        print("❌ Admin post qo'shishda xatolik")

def test_add_post_with_employee():
    """Employee bilan post qo'shish testi"""
    print("=== Employee bilan post qo'shish testi ===")
    
    employee_token = get_employee_token()
    if not employee_token:
        print("❌ Employee token olinmadi")
        return
    
    employee_id = get_employee_info()
    if not employee_id:
        print("❌ Employee topilmadi")
        return
    
    print(f"Employee ID: {employee_id}")
    
    post_data = {
        "title": "Test Post by Employee",
        "description": "Bu employee tomonidan yaratilgan test post",
        "media": []
    }
    
    headers = {"Authorization": f"Bearer {employee_token}"}
    response = requests.post(f"{base_url}/api/employees/{employee_id}/posts", json=post_data, headers=headers)
    
    print(f"Response status: {response.status_code}")
    print(f"Response: {response.text}")
    
    if response.status_code == 200:
        print("✅ Employee post qo'shish muvaffaqiyatli")
    else:
        print("❌ Employee post qo'shishda xatolik")





def test_employee_post():
    print("=== Employee Post Qo'shish Testini ===")
    
    # Test 1: Admin bilan post qo'shish
    print("\n1. Admin bilan post qo'shish...")
    test_add_post_with_admin()
    
    # Test 2: Employee o'zi bilan post qo'shish
    print("\n2. Employee o'zi bilan post qo'shish...")
    test_add_post_with_employee()
    
    print("\n" + "="*50)
    print("Test yakunlandi!")

if __name__ == "__main__":
    test_employee_post()