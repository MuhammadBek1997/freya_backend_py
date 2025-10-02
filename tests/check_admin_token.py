import requests
import jwt
import json

base_url = "http://localhost:8000"

def get_admin_token():
    """Admin token olish"""
    login_data = {
        "username": "superadmin",
        "password": "superadmin123"
    }
    
    response = requests.post(f"{base_url}/api/auth/superadmin/login", json=login_data)
    print(f"Admin login status: {response.status_code}")
    print(f"Admin login response: {response.text}")
    
    if response.status_code == 200:
        response_data = response.json()
        # Token ni topish
        if "access_token" in response_data:
            return response_data["access_token"]
        elif "token" in response_data:
            return response_data["token"]
        elif "data" in response_data and "token" in response_data["data"]:
            return response_data["data"]["token"]
        else:
            print("Token topilmadi!")
            return None
    return None

# Admin token olish
admin_token = get_admin_token()
if admin_token:
    print(f"Admin token: {admin_token[:50]}...")
    
    # Token ni decode qilish (secret key siz)
    try:
        # JWT ni decode qilmasdan payload ni ko'rish
        import base64
        parts = admin_token.split('.')
        if len(parts) >= 2:
            # Payload qismini decode qilish
            payload = parts[1]
            # Padding qo'shish
            payload += '=' * (4 - len(payload) % 4)
            decoded = base64.b64decode(payload)
            payload_data = json.loads(decoded)
            print("Admin token payload:")
            print(json.dumps(payload_data, indent=2))
    except Exception as e:
        print(f"Token decode xatolik: {e}")
else:
    print("❌ Admin token olinmadi")