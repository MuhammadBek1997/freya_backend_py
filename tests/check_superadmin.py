#!/usr/bin/env python3
"""
Script to delete existing superadmin and create a new one
"""
from app.database import get_db
from app.models import Admin
from app.auth import JWTUtils

def main():
    # Get database session
    db = next(get_db())

    # Find and delete existing superadmin
    existing_superadmin = db.query(Admin).filter(
        Admin.username == 'superadmin'
    ).first()
    
    if existing_superadmin:
        print(f"Found existing superadmin: {existing_superadmin.id}")
        print(f"  Username: {existing_superadmin.username}")
        print(f"  Role: {existing_superadmin.role}")
        print(f"  Email: {existing_superadmin.email}")
        print(f"Deleting existing superadmin...")
        
        db.delete(existing_superadmin)
        db.commit()
        print("Existing superadmin deleted successfully!")
    else:
        print("No existing superadmin found.")

    # Create new superadmin with correct configuration
    print("\nCreating new superadmin...")
    
    # Use the same password hashing method as JWT utils
    password_hash = JWTUtils.hash_password('superadmin123')
    
    new_superadmin = Admin(
        salon_id=None,  # Superadmin doesn't belong to any salon
        username='superadmin',
        email='superadmin@freya.com',
        password_hash=password_hash,
        full_name='Super Administrator',
        phone='+998901234567',
        is_active=True,
        role='superadmin'  # Use 'superadmin' role as expected by auth endpoint
    )
    
    db.add(new_superadmin)
    db.commit()
    
    print("New superadmin created successfully!")
    print(f"  ID: {new_superadmin.id}")
    print(f"  Username: {new_superadmin.username}")
    print(f"  Password: superadmin123")
    print(f"  Role: {new_superadmin.role}")
    print(f"  Email: {new_superadmin.email}")
    print(f"  Password Hash: {new_superadmin.password_hash}")
    
    # Test password verification
    is_valid = JWTUtils.verify_password('superadmin123', new_superadmin.password_hash)
    print(f"  Password verification test: {is_valid}")

    db.close()

if __name__ == "__main__":
    main()