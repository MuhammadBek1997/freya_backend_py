#!/usr/bin/env python3
"""
Test script to verify all models work correctly with the database
"""
import sys
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add the app directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.config import settings
from app.models import *

def test_database_connection():
    """Test basic database connection"""
    try:
        engine = create_engine(settings.database_url)
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            print("✓ Database connection successful")
            return True
    except Exception as e:
        print(f"✗ Database connection failed: {e}")
        return False

def test_model_imports():
    """Test that all models can be imported without errors"""
    try:
        models_to_test = [
            BaseModel, Admin, User, Salon, Employee, EmployeeComment, 
            EmployeePost, PostMedia, EmployeePostLimit, Schedule, Message,
            PaymentCard, Notification, UserSession, Analytics, SalonTopHistory,
            Service, Payment, Appointment, UserChat, TempRegistration, Post,
            EmployeeTranslation, SalonTranslation
        ]
        
        for model in models_to_test:
            print(f"✓ {model.__name__} imported successfully")
        
        print(f"✓ All {len(models_to_test)} models imported successfully")
        return True
    except Exception as e:
        print(f"✗ Model import failed: {e}")
        return False

def test_model_table_mapping():
    """Test that models map to correct database tables"""
    try:
        engine = create_engine(settings.database_url)
        
        # Test key models and their table names
        model_table_mapping = {
            User: 'users',
            Admin: 'admins', 
            Salon: 'salons',
            Employee: 'employees',
            Appointment: 'appointments',
            UserChat: 'user_chats',
            TempRegistration: 'temp_registrations',
            Post: 'posts',
            Message: 'messages'
        }
        
        for model, expected_table in model_table_mapping.items():
            actual_table = model.__tablename__
            if actual_table == expected_table:
                print(f"✓ {model.__name__} maps to table '{actual_table}'")
            else:
                print(f"✗ {model.__name__} maps to '{actual_table}', expected '{expected_table}'")
                return False
        
        print("✓ All model-table mappings are correct")
        return True
    except Exception as e:
        print(f"✗ Model table mapping test failed: {e}")
        return False

def test_model_relationships():
    """Test that model relationships are properly defined"""
    try:
        # Test some key relationships
        relationships_to_test = [
            (User, 'appointments'),
            (User, 'user_chats'),
            (Admin, 'salon'),
            (Salon, 'employees'),
            (Salon, 'appointments'),
            (Employee, 'appointments'),
            (Employee, 'user_chats'),
            (UserChat, 'user'),
            (UserChat, 'salon'),
            (UserChat, 'employee'),
            (Appointment, 'user'),
            (Appointment, 'salon'),
            (Appointment, 'employee')
        ]
        
        for model, relationship_name in relationships_to_test:
            if hasattr(model, relationship_name):
                print(f"✓ {model.__name__}.{relationship_name} relationship exists")
            else:
                print(f"✗ {model.__name__}.{relationship_name} relationship missing")
                return False
        
        print("✓ All tested relationships are properly defined")
        return True
    except Exception as e:
        print(f"✗ Relationship test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("Testing Freya Backend Models")
    print("=" * 40)
    
    tests = [
        ("Database Connection", test_database_connection),
        ("Model Imports", test_model_imports),
        ("Model Table Mapping", test_model_table_mapping),
        ("Model Relationships", test_model_relationships)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{test_name}:")
        print("-" * len(test_name))
        if test_func():
            passed += 1
        else:
            print(f"Test '{test_name}' failed!")
    
    print("\n" + "=" * 40)
    print(f"Tests passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 All tests passed! Models are working correctly.")
        return True
    else:
        print("❌ Some tests failed. Please check the errors above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)