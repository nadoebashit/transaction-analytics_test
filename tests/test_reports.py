"""
Tests for the reports API endpoints.
"""

import pytest
from datetime import date, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import get_db, Base
from app.models import User, Transaction, TransactionStatus, TransactionType

# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """Override database dependency for testing."""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

# Create test client
client = TestClient(app)


@pytest.fixture(scope="function")
def setup_test_data():
    """Setup test data for each test."""
    # Create tables
    Base.metadata.create_all(bind=engine)
    
    db = TestingSessionLocal()
    
    try:
        # Create test users
        users = []
        for i in range(5):
            user = User(
                first_name=f"Test{i}",
                last_name=f"User{i}",
                email=f"test{i}@example.com"
            )
            users.append(user)
        
        db.add_all(users)
        db.commit()
        
        # Refresh to get IDs
        for user in users:
            db.refresh(user)
        
        # Create test transactions
        base_date = date.today() - timedelta(days=30)
        transactions = []
        
        for i in range(100):
            transaction = Transaction(
                user_id=users[i % len(users)].id,
                amount=100.0 + i,
                status=TransactionStatus.SUCCESSFUL if i % 4 != 0 else TransactionStatus.FAILED,
                type=TransactionType.PAYMENT if i % 3 != 0 else TransactionType.INVOICE,
                transaction_date=base_date + timedelta(days=i % 30)
            )
            transactions.append(transaction)
        
        db.add_all(transactions)
        db.commit()
        
        yield
        
    finally:
        # Cleanup
        db.close()
        Base.metadata.drop_all(bind=engine)


class TestReportsAPI:
    """Test class for reports API."""
    
    def test_root_endpoint(self):
        """Test root endpoint."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Transaction Analytics API"
        assert "version" in data
        assert data["docs"] == "/docs"
    
    def test_health_endpoint(self):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
    
    def test_report_basic(self, setup_test_data):
        """Test basic report endpoint."""
        response = client.get("/report/")
        assert response.status_code == 200
        
        data = response.json()
        assert "period" in data
        assert "filters" in data
        assert "metrics" in data
        
        # Check metrics structure
        metrics = data["metrics"]
        assert "total_transactions" in metrics
        assert "total_amount" in metrics
        assert metrics["total_transactions"] > 0
    
    def test_report_with_date_filter(self, setup_test_data):
        """Test report endpoint with date filters."""
        start_date = (date.today() - timedelta(days=10)).isoformat()
        end_date = date.today().isoformat()
        
        response = client.get(f"/report/?start_date={start_date}&end_date={end_date}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["period"]["start_date"] == start_date
        assert data["period"]["end_date"] == end_date
    
    def test_report_with_status_filter(self, setup_test_data):
        """Test report endpoint with status filter."""
        response = client.get("/report/?status=successful")
        assert response.status_code == 200
        
        data = response.json()
        assert data["filters"]["status"] == "successful"
    
    def test_report_with_type_filter(self, setup_test_data):
        """Test report endpoint with type filter."""
        response = client.get("/report/?type=payment")
        assert response.status_code == 200
        
        data = response.json()
        assert data["filters"]["type"] == "payment"
    
    def test_report_with_avg_min_max(self, setup_test_data):
        """Test report endpoint with avg, min, max included."""
        response = client.get("/report/?include_avg=true&include_min=true&include_max=true")
        assert response.status_code == 200
        
        data = response.json()
        metrics = data["metrics"]
        assert "average_amount" in metrics
        assert "minimum_amount" in metrics
        assert "maximum_amount" in metrics
    
    def test_report_with_daily_shift(self, setup_test_data):
        """Test report endpoint with daily breakdown."""
        response = client.get("/report/?include_daily_shift=true")
        assert response.status_code == 200
        
        data = response.json()
        assert "daily_breakdown" in data
        
        daily_data = data["daily_breakdown"]
        assert isinstance(daily_data, list)
        
        if daily_data:
            # Check structure of daily data
            first_day = daily_data[0]
            assert "date" in first_day
            assert "transaction_count" in first_day
            assert "total_amount" in first_day
            assert "percent_change" in first_day
    
    def test_invalid_date_format(self, setup_test_data):
        """Test report endpoint with invalid date format."""
        response = client.get("/report/?start_date=invalid-date")
        assert response.status_code == 400
        
        data = response.json()
        assert "Invalid date format" in data["detail"]
    
    def test_invalid_status(self, setup_test_data):
        """Test report endpoint with invalid status."""
        response = client.get("/report/?status=invalid")
        assert response.status_code == 400
        
        data = response.json()
        assert "Invalid status" in data["detail"]
    
    def test_invalid_type(self, setup_test_data):
        """Test report endpoint with invalid type."""
        response = client.get("/report/?type=invalid")
        assert response.status_code == 400
        
        data = response.json()
        assert "Invalid type" in data["detail"]
    
    def test_start_date_after_end_date(self, setup_test_data):
        """Test report endpoint with start date after end date."""
        start_date = date.today().isoformat()
        end_date = (date.today() - timedelta(days=1)).isoformat()
        
        response = client.get(f"/report/?start_date={start_date}&end_date={end_date}")
        assert response.status_code == 400
        
        data = response.json()
        assert "Start date cannot be after end date" in data["detail"]
