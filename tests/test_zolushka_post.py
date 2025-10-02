import requests
import json

base_url = "http://localhost:8000"

def test_zolushka_login():
    """Zolushka employee login testi"""
    print("=== Zolushka Employee Login Testi ===")
    
    login_data = {
        "username": "zolushka",
        "password": "12345678"
    }
    
    response = requests.post(f"{base_url}/api/auth/employee/login", json=login_data)
    print(f"Login status: {response.status_code}")
    print(f"Login response: {response.text}")
    
    if response.status_code == 200:
        response_data = response.json()
        if "token" in response_data:
            print("✅ Zolushka login muvaffaqiyatli")
            return response_data["token"]
        else:
            print("❌ Token topilmadi")
            return None
    else:
        print("❌ Login xatolik")
        return None

def test_zolushka_post(token):
    """Zolushka bilan post qo'shish testi"""
    print("\n=== Zolushka Post Qo'shish Testi ===")
    
    if not token:
        print("❌ Token yo'q, test bajarib bo'lmaydi")
        return
    
    employee_id = "639ea749-59a1-4f40-a919-34a47f40f5dd"  # Zolushka ID
    
    post_data = {
        "title": "Zolushka ning Test Posti",
        "description": "Bu Zolushka tomonidan yaratilgan test post",
        "media": []
    }
    
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.post(f"{base_url}/api/employees/{employee_id}/posts", json=post_data, headers=headers)
    
    print(f"Post qo'shish status: {response.status_code}")
    print(f"Post qo'shish response: {response.text}")
    
    if response.status_code == 200:
        print("✅ Zolushka post qo'shish muvaffaqiyatli")
        response_data = response.json()
        if "data" in response_data:
            post_info = response_data["data"]
            print(f"Post ID: {post_info.get('id')}")
            print(f"Post Title: {post_info.get('title')}")
            if "limits" in post_info:
                limits = post_info["limits"]
                print(f"Free posts used: {limits.get('free_posts_used')}")
                print(f"Remaining free posts: {limits.get('remaining_free_posts')}")
    else:
        print("❌ Post qo'shishda xatolik")

def main():
    print("=== Zolushka Employee Test ===\n")
    
    # 1. Login test
    token = test_zolushka_login()
    
    # 2. Post qo'shish test
    test_zolushka_post(token)
    
    print("\n" + "="*50)
    print("Test yakunlandi!")

if __name__ == "__main__":
    main()