#!/usr/bin/env python3
"""
Test admin profile directly using database
"""

import sys
import os

# Add the app directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import Session
from app.database import get_db
from app.models.admin import Admin
from app.schemas.auth import AdminProfileResponse

def test_admin_profile_direct():
    """Test admin profile creation directly"""
    db = next(get_db())
    
    try:
        print("=== Testing Admin Profile Response Creation ===")
        
        # Get zolushka admin
        admin = db.query(Admin).filter(Admin.username == "zolushka").first()
        if not admin:
            print("❌ Admin not found")
            return
        
        print(f"✅ Admin found: {admin.username}")
        print(f"Admin details:")
        print(f"  ID: {admin.id} (type: {type(admin.id)})")
        print(f"  Username: {admin.username}")
        print(f"  Email: {admin.email}")
        print(f"  Full Name: {admin.full_name}")
        print(f"  Role: {admin.role}")
        print(f"  Salon ID: {admin.salon_id} (type: {type(admin.salon_id)})")
        print(f"  Active: {admin.is_active}")
        print(f"  Created: {admin.created_at} (type: {type(admin.created_at)})")
        print(f"  Updated: {admin.updated_at} (type: {type(admin.updated_at)})")
        
        # Try to create AdminProfileResponse
        try:
            profile_response = AdminProfileResponse(
                id=str(admin.id),
                username=admin.username,
                email=admin.email,
                full_name=admin.full_name,
                role=admin.role,
                salon_id=str(admin.salon_id) if admin.salon_id else None,
                is_active=admin.is_active,
                created_at=admin.created_at.isoformat(),
                updated_at=admin.updated_at.isoformat()
            )
            
            print(f"✅ AdminProfileResponse created successfully!")
            print(f"Response data: {profile_response.dict()}")
            
        except Exception as response_error:
            print(f"❌ AdminProfileResponse creation failed: {response_error}")
            print(f"Error type: {type(response_error)}")
            
            # Try each field individually
            print(f"\n=== Testing Individual Fields ===")
            try:
                print(f"ID conversion: {str(admin.id)}")
            except Exception as e:
                print(f"❌ ID conversion failed: {e}")
                
            try:
                print(f"Salon ID conversion: {str(admin.salon_id) if admin.salon_id else None}")
            except Exception as e:
                print(f"❌ Salon ID conversion failed: {e}")
                
            try:
                print(f"Created at conversion: {admin.created_at.isoformat()}")
            except Exception as e:
                print(f"❌ Created at conversion failed: {e}")
                
            try:
                print(f"Updated at conversion: {admin.updated_at.isoformat()}")
            except Exception as e:
                print(f"❌ Updated at conversion failed: {e}")
            
    except Exception as e:
        print(f"❌ Database error: {e}")
    finally:
        db.close()

def main():
    test_admin_profile_direct()

if __name__ == "__main__":
    main()