#!/usr/bin/env python3
"""
Test foydalanuvchilarini yaratish uchun script
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import SessionLocal, User
from datetime import datetime

def create_test_users():
    """Test foydalanuvchilarini yaratish"""
    db = SessionLocal()
    
    test_users = [
        {
            "username": "test1",
            "password": "test123",
            "telegram_id": None,
            "is_admin": False
        },
        {
            "username": "test2", 
            "password": "test456",
            "telegram_id": None,
            "is_admin": False
        },
        {
            "username": "manager",
            "password": "manager123",
            "telegram_id": None,
            "is_admin": True
        }
    ]
    
    try:
        for user_data in test_users:
            # Check if user already exists
            existing_user = db.query(User).filter_by(username=user_data["username"]).first()
            if existing_user:
                print(f"⚠️  User {user_data['username']} already exists, skipping...")
                continue
            
            # Create new user
            new_user = User(**user_data)
            db.add(new_user)
            print(f"✅ Created user: {user_data['username']}")
        
        db.commit()
        print("\n🎉 Test users created successfully!")
        
        # Display all users
        print("\n👥 All users in database:")
        users = db.query(User).all()
        for user in users:
            status = "👑 Admin" if user.is_admin else "👤 User"
            blocked = "🚫 Blocked" if user.is_blocked else "✅ Active"
            print(f"  {status} | {user.username} | {blocked}")
            
    except Exception as e:
        print(f"❌ Error creating test users: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    create_test_users()
