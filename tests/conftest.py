"""
Pytest configuration and shared fixtures.
"""

import pytest
import tempfile
import os
from datetime import date, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import get_db, Base
from app.models import User, Transaction, TransactionStatus, TransactionType


@pytest.fixture(scope="session")
def test_db():
    """Create test database for the session."""
    # Create temporary database
    db_fd, db_path = tempfile.mkstemp()
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    
    Base.metadata.create_all(bind=engine)
    
    yield engine
    
    # Cleanup
    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture(scope="function")
def db_session(test_db):
    """Create database session for each test."""
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_db)
    
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="function")
def sample_users(db_session):
    """Create sample users for testing."""
    users = []
    for i in range(5):
        user = User(
            first_name=f"Test{i}",
            last_name=f"User{i}",
            email=f"test{i}@example.com"
        )
        users.append(user)
    
    db_session.add_all(users)
    db_session.commit()
    
    # Refresh to get IDs
    for user in users:
        db_session.refresh(user)
    
    yield users
    
    # Cleanup
    for user in users:
        db_session.delete(user)
    db_session.commit()


@pytest.fixture(scope="function")
def sample_transactions(db_session, sample_users):
    """Create sample transactions for testing."""
    transactions = []
    base_date = date.today() - timedelta(days=30)
    
    for i in range(50):
        transaction = Transaction(
            user_id=sample_users[i % len(sample_users)].id,
            amount=50.0 + (i % 100),
            status=TransactionStatus.SUCCESSFUL if i % 4 != 0 else TransactionStatus.FAILED,
            type=TransactionType.PAYMENT if i % 2 == 0 else TransactionType.INVOICE,
            transaction_date=base_date + timedelta(days=i % 30)
        )
        transactions.append(transaction)
    
    db_session.add_all(transactions)
    db_session.commit()
    
    # Refresh to get IDs
    for transaction in transactions:
        db_session.refresh(transaction)
    
    yield transactions
    
    # Cleanup
    for transaction in transactions:
        db_session.delete(transaction)
    db_session.commit()


@pytest.fixture(scope="function")
def sample_csv_file():
    """Create sample CSV file for testing."""
    csv_data = "user_id;country\n1;Germany\n2;France\n3;United States\n4;Canada\n5;Japan\n"
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        f.write(csv_data)
        temp_csv_path = f.name
    
    yield temp_csv_path
    
    # Cleanup
    try:
        os.unlink(temp_csv_path)
    except:
        pass


@pytest.fixture
def mock_date_today():
    """Mock today's date for consistent testing."""
    fixed_date = date(2024, 1, 15)
    
    import app.routers.reports
    import app.routers.country_reports
    
    with patch.object(app.routers.reports.date, 'today', return_value=fixed_date):
        with patch.object(app.routers.country_reports.date, 'today', return_value=fixed_date):
            yield fixed_date
