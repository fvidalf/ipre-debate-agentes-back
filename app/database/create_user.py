
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

from sqlmodel import Session, create_engine, SQLModel
from app.models import User
from app.auth import hash_password


def create_database_engine():
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("ERROR: DATABASE_URL not found in environment variables")
        print("Please set DATABASE_URL in your .env file")
        sys.exit(1)
    
    return create_engine(database_url)


def create_user():
    print("=== Create New User ===")
    
    email = input("Email: ").strip()
    if not email:
        print("Email is required")
        return
    
    password = input("Password: ").strip()
    if not password:
        print("Password is required")
        return
    
    print(f"\nCreating user with email: {email}")
    confirm = input("Continue? (y/N): ").strip().lower()
    if confirm != 'y':
        print("Cancelled")
        return
    
    engine = create_database_engine()
    SQLModel.metadata.create_all(engine)
    
    with Session(engine) as session:
        from sqlmodel import select
        existing_user = session.exec(select(User).where(User.email == email)).first()
        if existing_user:
            print(f"ERROR: User with email {email} already exists")
            return
        
        hashed_password = hash_password(password)
        new_user = User(
            email=email,
            password_hash=hashed_password,
            is_active=True
        )
        
        session.add(new_user)
        session.commit()
        session.refresh(new_user)
        
        print(f"✅ User created successfully!")
        print(f"   ID: {new_user.id}")
        print(f"   Email: {new_user.email}")
        print(f"   Created: {new_user.created_at}")


def list_users():
    print("=== All Users ===")
    
    engine = create_database_engine()
    
    with Session(engine) as session:
        from sqlmodel import select
        users = session.exec(select(User)).all()
        
        if not users:
            print("No users found")
            return
        
        for user in users:
            status = "active" if user.is_active else "inactive"
            last_login = user.last_login_at.strftime("%Y-%m-%d %H:%M") if user.last_login_at else "never"
            print(f"  {user.email} ({status}) - Last login: {last_login}")


def main():
    while True:
        print("\n=== User Management ===")
        print("1. Create user")
        print("2. List users")
        print("3. Exit")
        
        choice = input("\nChoice: ").strip()
        
        if choice == "1":
            create_user()
        elif choice == "2":
            list_users()
        elif choice == "3":
            print("Goodbye!")
            break
        else:
            print("Invalid choice")


if __name__ == "__main__":
    main()