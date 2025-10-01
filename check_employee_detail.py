import requests
import json

base_url = "http://localhost:8000/api"

def check_employee_detail():
    print("=== Employee Detail Response Strukturasi ===\n")
    
    # Get first employee
    response = requests.get(f"{base_url}/employees/")
    if response.status_code == 200:
        employees = response.json()["data"]
        if employees:
            employee_id = employees[0]["id"]
            print(f"Employee ID: {employee_id}")
            
            # Get employee detail
            response = requests.get(f"{base_url}/employees/{employee_id}")
            if response.status_code == 200:
                data = response.json()
                print(f"Status: {response.status_code}")
                print("Response keys:", list(data.keys()))
                print("\nResponse data:")
                print(json.dumps(data, indent=2, ensure_ascii=False))
            else:
                print(f"Xatolik: {response.text}")
        else:
            print("Employee topilmadi")
    else:
        print(f"Employeelarni olishda xatolik: {response.text}")

if __name__ == "__main__":
    check_employee_detail()