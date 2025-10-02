import requests

base_url = "http://localhost:8000"

endpoints = [
    "/api/auth/superadmin/login",
    "/api/auth/employee/login",
    "/auth/superadmin/login",
    "/auth/employee/login"
]

for endpoint in endpoints:
    try:
        response = requests.get(f"{base_url}{endpoint}")
        print(f"{endpoint}: {response.status_code}")
    except Exception as e:
        print(f"{endpoint}: Error - {e}")