import requests
import json

# Test employee update endpoint with admin authentication
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

def test_employee_update():
    print("=== Employee Update Endpointini Test Qilish ===\n")
    
    # Get admin token
    print("0. Admin token olish...")
    token = get_admin_token()
    if not token:
        print("Admin token olinmadi!")
        return
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    print("Admin token muvaffaqiyatli olindi!")
    
    print("\n" + "="*50 + "\n")
    
    # First get an employee to update
    print("1. Birinchi employeeni olish...")
    response = requests.get(f"{base_url}/employees/")
    if response.status_code == 200:
        employees = response.json()["data"]
        if employees:
            employee_id = employees[0]["id"]
            current_username = employees[0]["username"]
            current_name = employees[0]["name"]
            print(f"Employee ID: {employee_id}")
            print(f"Joriy username: {current_username}")
            print(f"Joriy ism: {current_name}")
        else:
            print("Employeelar topilmadi!")
            return
    else:
        print(f"Employeelarni olishda xatolik: {response.status_code}")
        return
    
    print("\n" + "="*50 + "\n")
    
    # Test 1: Update with new username
    print("2. Username bilan yangilash...")
    update_data = {
        "name": "Yangilangan Ism",
        "surname": "Yangilangan Familiya", 
        "username": "yangi_username_test",
        "profession": "Yangilangan Kasb"
    }
    
    response = requests.put(
        f"{base_url}/employees/{employee_id}",
        json=update_data,
        headers=headers
    )
    
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"Success: {result['success']}")
        print(f"Message: {result['message']}")
    else:
        print(f"Xatolik: {response.text}")
    
    print("\n" + "="*50 + "\n")
    
    # Test 2: Try to update with existing username
    print("3. Mavjud username bilan yangilash (xatolik bo'lishi kerak)...")
    
    # Get another employee's username
    if len(employees) > 1:
        existing_username = employees[1]["username"]
        if existing_username:
            print(f"Mavjud username: {existing_username}")
            
            update_data = {
                "username": existing_username
            }
            
            response = requests.put(
                f"{base_url}/employees/{employee_id}",
                json=update_data,
                headers=headers
            )
            
            print(f"Status: {response.status_code}")
            if response.status_code == 400:
                result = response.json()
                print(f"Kutilgan xatolik: {result['detail']}")
            else:
                print(f"Kutilmagan natija: {response.text}")
        else:
            print("Ikkinchi employee username yo'q")
    else:
        print("Ikkinchi employee topilmadi, test o'tkazib yuborildi")
    
    print("\n" + "="*50 + "\n")
    
    # Test 3: Verify the update
    print("4. Yangilanishni tekshirish...")
    response = requests.get(f"{base_url}/employees/{employee_id}")
    if response.status_code == 200:
        employee = response.json()["data"]
        print(f"Yangilangan ism: {employee['name']}")
        print(f"Yangilangan familiya: {employee['surname']}")
        print(f"Yangilangan username: {employee['username']}")
        print(f"Yangilangan kasb: {employee['profession']}")
    else:
        print(f"Employee ma'lumotlarini olishda xatolik: {response.status_code}")
    
    print("\n" + "="*50 + "\n")
    
    # Test 4: Update only username
    print("5. Faqat username yangilash...")
    update_data = {
        "username": "faqat_username_test"
    }
    
    response = requests.put(
        f"{base_url}/employees/{employee_id}",
        json=update_data,
        headers=headers
    )
    
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"Success: {result['success']}")
        print(f"Message: {result['message']}")
        
        # Verify username change
        response = requests.get(f"{base_url}/employees/{employee_id}")
        if response.status_code == 200:
            employee = response.json()["data"]
            print(f"Yangi username: {employee['username']}")
    else:
        print(f"Xatolik: {response.text}")
    
    print("\n" + "="*50 + "\n")
    print("Test yakunlandi!")

if __name__ == "__main__":
    test_employee_update()