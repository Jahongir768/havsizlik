#!/usr/bin/env python3
"""
Foydalanuvchi urinishlarini qayta tiklash uchun script
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import SessionLocal, User
from datetime import datetime

def reset_user_attempts(username=None):
    """Foydalanuvchi urinishlarini qayta tiklash"""
    db = SessionLocal()
    
    try:
        if username:
            # Reset specific user
            user = db.query(User).filter_by(username=username).first()
            if not user:
                print(f"❌ User {username} not found")
                return
            
            user.failed_attempts = 0
            user.is_blocked = False
            user.blocked_until = None
            user.last_attempt = None
            
            db.commit()
            print(f"✅ Reset attempts for user: {username}")
        else:
            # Reset all users
            users = db.query(User).all()
            reset_count = 0
            
            for user in users:
                if user.failed_attempts > 0 or user.is_blocked:
                    user.failed_attempts = 0
                    user.is_blocked = False
                    user.blocked_until = None
                    user.last_attempt = None
                    reset_count += 1
            
            db.commit()
            print(f"✅ Reset attempts for {reset_count} users")
            
    except Exception as e:
        print(f"❌ Error resetting attempts: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        username = sys.argv[1]
        reset_user_attempts(username)
    else:
        print("Reset all users? (y/N): ", end="")
        confirm = input().lower()
        if confirm == 'y':
            reset_user_attempts()
        else:
            print("Operation cancelled")
