#!/usr/bin/env python3
"""
Debug JWT token and admin profile
"""

import requests
import json
import jwt
import sys
import os

# Add the app directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.config import settings

def debug_jwt_and_profile():
    """Debug JWT token and admin profile"""
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
    
    # Decode JWT token
    print(f"\n=== JWT Token Analysis ===")
    try:
        # Decode without verification first to see the payload
        decoded_payload = jwt.decode(token, options={"verify_signature": False})
        print(f"Token payload: {json.dumps(decoded_payload, indent=2)}")
        
        # Try to decode with verification
        try:
            verified_payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
            print(f"✅ Token verification successful!")
            print(f"Verified payload: {json.dumps(verified_payload, indent=2)}")
        except Exception as verify_error:
            print(f"❌ Token verification failed: {verify_error}")
            
    except Exception as decode_error:
        print(f"❌ Token decode failed: {decode_error}")
    
    # Try admin profile with detailed error handling
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

def main():
    print("=== Debug JWT Token and Admin Profile ===\n")
    debug_jwt_and_profile()

if __name__ == "__main__":
    main()