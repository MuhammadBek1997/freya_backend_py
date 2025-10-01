import requests
import json

base_url = "http://localhost:8000/api"

def test_all_employee_endpoints():
    print("=== Barcha Employee Endpointlarini Test Qilish ===\n")
    
    # 1. GET /api/employees/
    print("1. GET /api/employees/ - Barcha employeelar")
    response = requests.get(f"{base_url}/employees/")
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Muvaffaqiyat! {len(data['data'])} ta employee topildi")
        employee_id = data['data'][0]['id'] if data['data'] else None
        salon_id = data['data'][0]['salon_id'] if data['data'] else None
    else:
        print(f"❌ Xatolik: {response.text}")
        return
    
    print("\n" + "="*50 + "\n")
    
    # 2. GET /api/employees/salon/{salon_id}
    if salon_id:
        print(f"2. GET /api/employees/salon/{salon_id} - Salon bo'yicha employeelar")
        response = requests.get(f"{base_url}/employees/salon/{salon_id}")
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Muvaffaqiyat! {len(data['data'])} ta employee topildi")
        else:
            print(f"❌ Xatolik: {response.text}")
    else:
        print("2. Salon ID topilmadi, test o'tkazilmadi")
    
    print("\n" + "="*50 + "\n")
    
    # 3. GET /api/employees/{employee_id}
    if employee_id:
        print(f"3. GET /api/employees/{employee_id} - Bitta employee")
        response = requests.get(f"{base_url}/employees/{employee_id}")
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            data = result['data']
            print(f"✅ Muvaffaqiyat! Employee: {data['name']} {data['surname']}")
            print(f"   Username: {data.get('username', 'N/A')}")
            print(f"   Rating: {data.get('rating', 'N/A')}")
            print(f"   Salon: {data.get('salon_name', 'N/A')}")
        else:
            print(f"❌ Xatolik: {response.text}")
    else:
        print("3. Employee ID topilmadi, test o'tkazilmadi")
    
    print("\n" + "="*50 + "\n")
    
    # 4. PUT /api/employees/{employee_id} - Username bilan yangilash
    if employee_id:
        print(f"4. PUT /api/employees/{employee_id} - Username bilan yangilash")
        
        # Get admin token
        login_data = {
            "username": "superadmin",
            "password": "superadmin123"
        }
        
        response = requests.post(f"{base_url}/auth/admin/login", json=login_data)
        if response.status_code == 200:
            token = response.json()["token"]
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
            
            update_data = {
                "username": f"test_user_{employee_id[:8]}"
            }
            
            response = requests.put(
                f"{base_url}/employees/{employee_id}",
                json=update_data,
                headers=headers
            )
            
            print(f"Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Muvaffaqiyat! {data['message']}")
            else:
                print(f"❌ Xatolik: {response.text}")
        else:
            print("❌ Admin login xatoligi")
    else:
        print("4. Employee ID topilmadi, test o'tkazilmadi")
    
    print("\n" + "="*50 + "\n")
    print("Barcha testlar yakunlandi!")

if __name__ == "__main__":
    test_all_employee_endpoints()