#!/usr/bin/env python3
"""
Test script for automatic admin record creation when employee posts
"""

import requests
import json
import psycopg2
from psycopg2.extras import RealDictCursor
import uuid

# Database connection
def get_db_connection():
    return psycopg2.connect(
        host="localhost",
        database="freya_db",
        user="postgres",
        password="1234",
        cursor_factory=RealDictCursor
    )

def create_test_employee():
    """Create a new employee without admin record"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Generate unique employee data
    employee_id = str(uuid.uuid4())
    employee_name = f"Test Employee {employee_id[:8]}"
    
    try:
        # Insert employee into employees table
        cursor.execute("""
            INSERT INTO employees (id, name, phone, salon_id, created_at, updated_at)
            VALUES (%s, %s, %s, %s, NOW(), NOW())
        """, (
            employee_id,
            employee_name,
            "+998901234567",
            "83fc0c1a-b3d1-44dd-9b43-d2b9608042c7"  # Default salon ID
        ))
        
        conn.commit()
        print(f"✅ Employee yaratildi: {employee_name} (ID: {employee_id})")
        
        # Check if admin record exists (should not exist)
        cursor.execute("SELECT * FROM admins WHERE id = %s", (employee_id,))
        admin_record = cursor.fetchone()
        
        if admin_record:
            print(f"❌ Admin record allaqachon mavjud: {admin_record}")
        else:
            print(f"✅ Admin record yo'q (kutilganidek)")
        
        return employee_id, employee_name
        
    except Exception as e:
        print(f"❌ Employee yaratishda xatolik: {e}")
        conn.rollback()
        return None, None
    finally:
        cursor.close()
        conn.close()

def test_post_creation(employee_id, employee_name):
    """Test post creation which should auto-create admin record"""
    base_url = "http://localhost:8000"
    
    # First, try to login as admin to get token for creating post
    admin_login_data = {
        "username": "superadmin",
        "password": "superadmin123"
    }
    
    print(f"\n=== Admin Login ===")
    response = requests.post(f"{base_url}/api/auth/admin/login", json=admin_login_data)
    print(f"Login status: {response.status_code}")
    
    if response.status_code != 200:
        print(f"❌ Admin login failed: {response.text}")
        return False
    
    admin_token = response.json().get("token")
    print(f"✅ Admin token olingan")
    
    # Now try to create post for the employee (this should auto-create admin record)
    post_data = {
        "title": f"Auto-created admin test post for {employee_name}",
        "description": f"Bu post {employee_name} uchun admin record avtomatik yaratish testida yaratilgan"
    }
    
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    print(f"\n=== Post Creation Test ===")
    response = requests.post(
        f"{base_url}/api/employee/{employee_id}/posts",
        json=post_data,
        headers=headers
    )
    
    print(f"Post creation status: {response.status_code}")
    print(f"Response: {response.text}")
    
    if response.status_code == 200:
        print(f"✅ Post muvaffaqiyatli yaratildi")
        return True
    else:
        print(f"❌ Post yaratishda xatolik")
        return False

def check_admin_record_created(employee_id, employee_name):
    """Check if admin record was automatically created"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT * FROM admins WHERE id = %s", (employee_id,))
        admin_record = cursor.fetchone()
        
        if admin_record:
            print(f"\n✅ Admin record avtomatik yaratildi:")
            print(f"   ID: {admin_record['id']}")
            print(f"   Username: {admin_record['username']}")
            print(f"   Email: {admin_record['email']}")
            print(f"   Role: {admin_record['role']}")
            print(f"   Full Name: {admin_record['full_name']}")
            return True
        else:
            print(f"\n❌ Admin record yaratilmagan")
            return False
            
    except Exception as e:
        print(f"❌ Admin record tekshirishda xatolik: {e}")
        return False
    finally:
        cursor.close()
        conn.close()

def cleanup_test_data(employee_id):
    """Clean up test data"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Delete posts
        cursor.execute("DELETE FROM employee_posts WHERE employee_id = %s", (employee_id,))
        # Delete admin record
        cursor.execute("DELETE FROM admins WHERE id = %s", (employee_id,))
        # Delete employee
        cursor.execute("DELETE FROM employees WHERE id = %s", (employee_id,))
        
        conn.commit()
        print(f"\n🧹 Test ma'lumotlari tozalandi")
        
    except Exception as e:
        print(f"❌ Tozalashda xatolik: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

def main():
    print("=== Auto Admin Record Creation Test ===\n")
    
    # Step 1: Create test employee without admin record
    employee_id, employee_name = create_test_employee()
    if not employee_id:
        return
    
    try:
        # Step 2: Test post creation (should auto-create admin record)
        post_success = test_post_creation(employee_id, employee_name)
        
        # Step 3: Check if admin record was created
        admin_created = check_admin_record_created(employee_id, employee_name)
        
        # Results
        print(f"\n=== Test Natijalari ===")
        print(f"Employee yaratildi: ✅")
        print(f"Post yaratildi: {'✅' if post_success else '❌'}")
        print(f"Admin record avtomatik yaratildi: {'✅' if admin_created else '❌'}")
        
        if post_success and admin_created:
            print(f"\n🎉 Test muvaffaqiyatli! Admin record avtomatik yaratish ishlayapti!")
        else:
            print(f"\n❌ Test muvaffaqiyatsiz!")
            
    finally:
        # Cleanup
        cleanup_test_data(employee_id)

if __name__ == "__main__":
    main()