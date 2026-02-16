#!/usr/bin/env python3
"""
Script to seed the database with mock data for testing.

Creates:
- 100+ users with realistic data
- 10,000+ transactions distributed over the last 2 years
- Balanced status and type distributions
"""

import random
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List

from faker import Faker
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.models import User, Transaction, TransactionType, TransactionStatus

# Initialize Faker
fake = Faker()

# Database setup
engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(bind=engine)


def create_mock_users(count: int = 100) -> List[User]:
    """Create mock users with realistic data."""
    users = []
    
    for i in range(1, count + 1):
        user = User(
            first_name=fake.first_name(),
            last_name=fake.last_name(),
            email=fake.email(),
            is_active=random.choice([True, True, True, False])  # 75% active
        )
        users.append(user)
    
    return users


def create_mock_transactions(users: List[User], count: int = 10000) -> List[Transaction]:
    """Create mock transactions distributed over the last 2 years."""
    transactions = []
    
    # Calculate date range (last 2 years)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=730)  # 2 years
    
    # Status and type distributions
    statuses = [TransactionStatus.SUCCESSFUL, TransactionStatus.FAILED]
    types = [TransactionType.PAYMENT, TransactionType.INVOICE]
    
    # Weighted distributions (70% successful, 60% payment)
    status_weights = [0.7, 0.3]
    type_weights = [0.6, 0.4]
    
    for i in range(count):
        # Random user
        user = random.choice(users)
        
        # Random date within range
        days_offset = random.randint(0, 730)
        transaction_date = start_date + timedelta(days=days_offset)
        
        # Random amount (1 to 1000)
        amount = Decimal(str(round(random.uniform(1.0, 1000.0), 2)))
        
        # Weighted random status and type
        status = random.choices(statuses, weights=status_weights)[0]
        trans_type = random.choices(types, weights=type_weights)[0]
        
        transaction = Transaction(
            user_id=user.id,
            amount=amount,
            status=status,
            type=trans_type,
            transaction_date=transaction_date
        )
        transactions.append(transaction)
    
    return transactions


def seed_database():
    """Main function to seed the database."""
    print("Starting database seeding...")
    
    # Create session
    db = SessionLocal()
    
    try:
        # Clear existing data
        print("Clearing existing data...")
        db.query(Transaction).delete()
        db.query(User).delete()
        db.commit()
        
        # Create users
        print("Creating users...")
        users = create_mock_users(120)  # Create 120 users
        db.add_all(users)
        db.commit()
        
        # Refresh to get IDs
        for user in users:
            db.refresh(user)
        
        print(f"Created {len(users)} users")
        
        # Create transactions
        print("Creating transactions...")
        transactions = create_mock_transactions(users, 12000)  # Create 12,000 transactions
        db.add_all(transactions)
        db.commit()
        
        print(f"Created {len(transactions)} transactions")
        
        # Print some statistics
        successful_count = len([t for t in transactions if t.status == TransactionStatus.SUCCESSFUL])
        failed_count = len([t for t in transactions if t.status == TransactionStatus.FAILED])
        payment_count = len([t for t in transactions if t.type == TransactionType.PAYMENT])
        invoice_count = len([t for t in transactions if t.type == TransactionType.INVOICE])
        
        print("\n=== Database Statistics ===")
        print(f"Total Users: {len(users)}")
        print(f"Total Transactions: {len(transactions)}")
        print(f"Successful Transactions: {successful_count} ({successful_count/len(transactions)*100:.1f}%)")
        print(f"Failed Transactions: {failed_count} ({failed_count/len(transactions)*100:.1f}%)")
        print(f"Payment Transactions: {payment_count} ({payment_count/len(transactions)*100:.1f}%)")
        print(f"Invoice Transactions: {invoice_count} ({invoice_count/len(transactions)*100:.1f}%)")
        
        # Date range
        dates = [t.transaction_date for t in transactions]
        print(f"Date Range: {min(dates).date()} to {max(dates).date()}")
        
        # Amount range
        amounts = [float(t.amount) for t in transactions]
        print(f"Amount Range: ${min(amounts):.2f} to ${max(amounts):.2f}")
        print(f"Average Amount: ${sum(amounts)/len(amounts):.2f}")
        
        print("\nDatabase seeding completed successfully!")
        
    except Exception as e:
        print(f"Error during seeding: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
