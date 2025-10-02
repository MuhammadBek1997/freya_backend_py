#!/usr/bin/env python3
"""
Debug admin profile endpoint
"""

import requests
import json

def debug_admin_profile():
    """Debug admin profile endpoint"""
    base_url = "http://localhost:8000"
    
    # Login as admin
    admin_login_data = {
        "username": "zolushka",
        "password": "12345678"
    }
    
    print("=== Admin Login ===")
    response = requests.post(f"{base_url}/api/auth/admin/login", json=admin_login_data)
    print(f"Status: {response.status_code}")
    
    if response.status_code != 200:
        print("❌ Admin login failed!")
        print(f"Response: {response.text}")
        return
    
    response_data = response.json()
    token = response_data.get("token")
    user_data = response_data.get("user", {})
    
    print(f"✅ Admin login successful!")
    print(f"User data: {json.dumps(user_data, indent=2)}")
    print(f"Token: {token[:50]}...")
    
    # Try admin profile
    headers = {"Authorization": f"Bearer {token}"}
    
    print(f"\n=== Admin Profile Request ===")
    try:
        profile_response = requests.get(f"{base_url}/api/auth/admin/profile", headers=headers)
        print(f"Status: {profile_response.status_code}")
        print(f"Headers: {dict(profile_response.headers)}")
        print(f"Response: {profile_response.text}")
        
        if profile_response.status_code == 200:
            print(f"✅ Admin profile successful!")
            profile_data = profile_response.json()
            print(f"Profile data: {json.dumps(profile_data, indent=2)}")
        else:
            print(f"❌ Admin profile failed!")
            
    except Exception as e:
        print(f"❌ Request error: {e}")
    
    # Also try with superadmin for comparison
    print(f"\n=== Superadmin Login for Comparison ===")
    superadmin_data = {
        "username": "superadmin",
        "password": "superadmin123"
    }
    
    super_response = requests.post(f"{base_url}/api/auth/superadmin/login", json=superadmin_data)
    print(f"Superadmin login status: {super_response.status_code}")
    
    if super_response.status_code == 200:
        super_token = super_response.json().get("token")
        super_headers = {"Authorization": f"Bearer {super_token}"}
        
        super_profile_response = requests.get(f"{base_url}/api/auth/admin/profile", headers=super_headers)
        print(f"Superadmin profile status: {super_profile_response.status_code}")
        print(f"Superadmin profile response: {super_profile_response.text}")

def main():
    print("=== Debug Admin Profile ===\n")
    debug_admin_profile()

if __name__ == "__main__":
    main()