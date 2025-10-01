import requests
import json

# API base URL
BASE_URL = "http://localhost:8000"

def test_employee_endpoints():
    print("=== Employee Endpointlarini Test Qilish ===\n")
    
    # 1. Barcha employeelarni olish
    print("1. GET /api/employees/ - Barcha employeelarni olish")
    try:
        response = requests.get(f"{BASE_URL}/api/employees/")
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Success: {data.get('success')}")
            print(f"Employeelar soni: {len(data.get('data', []))}")
            if data.get('data'):
                print(f"Birinchi employee: {data['data'][0].get('name', 'N/A')}")
        else:
            print(f"Xatolik: {response.text}")
    except Exception as e:
        print(f"Xatolik: {e}")
    
    print("\n" + "="*50 + "\n")
    
    # 2. Salon bo'yicha employeelarni olish
    salon_id = "a8be0e5f-d78f-4574-a383-2bf23f80f1b0"  # Test salon ID
    print(f"2. GET /api/employees/salon/{salon_id} - Salon bo'yicha employeelarni olish")
    try:
        response = requests.get(f"{BASE_URL}/api/employees/salon/{salon_id}")
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Success: {data.get('success')}")
            print(f"Salon employeelari soni: {len(data.get('data', []))}")
            if data.get('data'):
                for emp in data['data'][:3]:  # Faqat birinchi 3 ta ko'rsatish
                    print(f"  - {emp.get('name', 'N/A')} ({emp.get('role', 'N/A')})")
        else:
            print(f"Xatolik: {response.text}")
    except Exception as e:
        print(f"Xatolik: {e}")
    
    print("\n" + "="*50 + "\n")
    
    # 3. Birinchi employeeni olish (agar mavjud bo'lsa)
    print("3. Birinchi employeeni ID bo'yicha olish")
    try:
        # Avval barcha employeelarni olib, birinchisining ID sini olish
        all_employees_response = requests.get(f"{BASE_URL}/api/employees/")
        if all_employees_response.status_code == 200:
            all_data = all_employees_response.json()
            if all_data.get('data'):
                first_employee_id = all_data['data'][0]['id']
                print(f"Employee ID: {first_employee_id}")
                
                # Endi shu employee haqida batafsil ma'lumot olish
                response = requests.get(f"{BASE_URL}/api/employees/{first_employee_id}")
                print(f"Status: {response.status_code}")
                if response.status_code == 200:
                    data = response.json()
                    print(f"Success: {data.get('success')}")
                    employee_data = data.get('data', {})
                    print(f"Employee nomi: {employee_data.get('name', 'N/A')}")
                    print(f"Role: {employee_data.get('role', 'N/A')}")
                    print(f"Profession: {employee_data.get('profession', 'N/A')}")
                    print(f"Username: {employee_data.get('username', 'N/A')}")
                    print(f"Phone: {employee_data.get('phone', 'N/A')}")
                    print(f"Email: {employee_data.get('email', 'N/A')}")
                    print(f"Rating: {employee_data.get('rating', 'N/A')}")
                else:
                    print(f"Xatolik: {response.text}")
            else:
                print("Hech qanday employee topilmadi")
        else:
            print("Employeelarni olishda xatolik")
    except Exception as e:
        print(f"Xatolik: {e}")
    
    print("\n" + "="*50 + "\n")
    print("Test yakunlandi!")

if __name__ == "__main__":
    test_employee_endpoints()