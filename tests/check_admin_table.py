#!/usr/bin/env python3
"""
Check if admin record exists in Admin table
"""

import requests

def check_admin_table():
    """Check admin table via API"""
    base_url = "http://localhost:8000"
    
    # Login as superadmin first
    superadmin_data = {
        "username": "superadmin",
        "password": "superadmin123"
    }
    
    print("=== Superadmin Login ===")
    response = requests.post(f"{base_url}/api/auth/superadmin/login", json=superadmin_data)
    print(f"Status: {response.status_code}")
    
    if response.status_code != 200:
        print("❌ Superadmin login failed!")
        return
    
    token = response.json().get("token")
    headers = {"Authorization": f"Bearer {token}"}
    
    # Try to get admin list or check if we can access admin endpoints
    print(f"\n=== Check Admin Endpoints ===")
    
    # Check if we can access admin profile with superadmin token
    profile_response = requests.get(f"{base_url}/api/auth/admin/profile", headers=headers)
    print(f"Admin profile with superadmin token: {profile_response.status_code}")
    print(f"Response: {profile_response.text}")
    
    # Now try to login with the auto-created admin
    print(f"\n=== Test Auto-Created Admin Login ===")
    admin_login_data = {
        "username": "zolushka",
        "password": "12345678"
    }
    
    admin_response = requests.post(f"{base_url}/api/auth/admin/login", json=admin_login_data)
    print(f"Admin login status: {admin_response.status_code}")
    print(f"Admin login response: {admin_response.text}")
    
    if admin_response.status_code == 200:
        admin_token = admin_response.json().get("token")
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Try to access admin profile with admin token
        admin_profile_response = requests.get(f"{base_url}/api/auth/admin/profile", headers=admin_headers)
        print(f"\nAdmin profile with admin token: {admin_profile_response.status_code}")
        print(f"Response: {admin_profile_response.text}")

def main():
    print("=== Admin Table Check ===\n")
    check_admin_table()

if __name__ == "__main__":
    main()