"""
Advanced tests for the enhanced reports API endpoints.
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
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_advanced.db"
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
def setup_advanced_test_data():
    """Setup comprehensive test data for advanced testing."""
    # Create tables
    Base.metadata.create_all(bind=engine)
    
    db = TestingSessionLocal()
    
    try:
        # Create test users
        users = []
        for i in range(10):
            user = User(
                first_name=f"Advanced{i}",
                last_name=f"User{i}",
                email=f"advanced{i}@example.com"
            )
            users.append(user)
        
        db.add_all(users)
        db.commit()
        
        # Refresh to get IDs
        for user in users:
            db.refresh(user)
        
        # Create diverse test transactions over 3 months
        base_date = date.today() - timedelta(days=90)
        transactions = []
        
        for i in range(500):
            # Vary dates across 3 months
            days_offset = i % 90
            transaction_date = base_date + timedelta(days=days_offset)
            
            # Create varied amounts
            if i % 10 == 0:
                amount = 1000.0  # High value transactions
            elif i % 5 == 0:
                amount = 500.0   # Medium value
            else:
                amount = float(10 + (i % 100))  # Regular transactions
            
            # Balanced status distribution
            status = TransactionStatus.SUCCESSFUL if i % 3 != 0 else TransactionStatus.FAILED
            
            # Balanced type distribution
            trans_type = TransactionType.PAYMENT if i % 2 == 0 else TransactionType.INVOICE
            
            transaction = Transaction(
                user_id=users[i % len(users)].id,
                amount=amount,
                status=status,
                type=trans_type,
                transaction_date=transaction_date
            )
            transactions.append(transaction)
        
        db.add_all(transactions)
        db.commit()
        
        yield
        
    finally:
        # Cleanup
        db.close()
        Base.metadata.drop_all(bind=engine)


class TestAdvancedReportsAPI:
    """Test class for advanced reports API features."""
    
    def test_report_with_all_features(self, setup_advanced_test_data):
        """Test report endpoint with all advanced features enabled."""
        response = client.get("/report/?include_avg=true&include_min=true&include_max=true&include_daily_shift=true&include_monthly_comparison=true&include_top_transactions=true")
        assert response.status_code == 200
        
        data = response.json()
        
        # Check basic structure
        assert "period" in data
        assert "filters" in data
        assert "metrics" in data
        
        # Check advanced metrics
        metrics = data["metrics"]
        assert "success_rate" in metrics
        assert "successful_transactions" in metrics
        assert "failed_transactions" in metrics
        assert "type_breakdown" in metrics
        assert "average_amount" in metrics
        assert "minimum_amount" in metrics
        assert "maximum_amount" in metrics
        
        # Check type breakdown structure
        type_breakdown = metrics["type_breakdown"]
        assert "payment" in type_breakdown
        assert "invoice" in type_breakdown
        assert "count" in type_breakdown["payment"]
        assert "amount" in type_breakdown["payment"]
        
        # Check daily breakdown
        assert "daily_breakdown" in data
        daily_data = data["daily_breakdown"]
        assert isinstance(daily_data, list)
        
        if daily_data:
            first_day = daily_data[0]
            assert "date" in first_day
            assert "transaction_count" in first_day
            assert "total_amount" in first_day
            assert "average_amount" in first_day
            assert "amount_change_percent" in first_day
            assert "count_change_percent" in first_day
        
        # Check monthly comparison
        assert "monthly_comparison" in data
        monthly_data = data["monthly_comparison"]
        assert isinstance(monthly_data, list)
        
        if monthly_data:
            first_month = monthly_data[0]
            assert "period" in first_month
            assert "year" in first_month
            assert "month" in first_month
            assert "transaction_count" in first_month
            assert "total_amount" in first_month
            assert "average_amount" in first_month
        
        # Check top transactions
        assert "top_transactions" in data
        top_transactions = data["top_transactions"]
        assert isinstance(top_transactions, list)
        assert len(top_transactions) <= 10  # Should be limited to 10
        
        if top_transactions:
            first_transaction = top_transactions[0]
            assert "transaction_id" in first_transaction
            assert "user_id" in first_transaction
            assert "amount" in first_transaction
            assert "status" in first_transaction
            assert "type" in first_transaction
            assert "transaction_date" in first_transaction
            
            # Check that transactions are sorted by amount (descending)
            if len(top_transactions) > 1:
                assert top_transactions[0]["amount"] >= top_transactions[1]["amount"]
    
    def test_summary_endpoint(self, setup_advanced_test_data):
        """Test the summary endpoint."""
        response = client.get("/report/summary?days=30")
        assert response.status_code == 200
        
        data = response.json()
        
        # Check structure
        assert "period" in data
        assert "summary" in data
        
        # Check period info
        period = data["period"]
        assert "start_date" in period
        assert "end_date" in period
        assert period["days"] == 30
        
        # Check summary metrics
        summary = data["summary"]
        assert "total_transactions" in summary
        assert "total_amount" in summary
        assert "success_rate" in summary
        assert "average_amount" in summary
        
        # Validate data types
        assert isinstance(summary["total_transactions"], int)
        assert isinstance(summary["total_amount"], (int, float))
        assert isinstance(summary["success_rate"], (int, float))
        assert isinstance(summary["average_amount"], (int, float))
    
    def test_summary_endpoint_custom_days(self, setup_advanced_test_data):
        """Test summary endpoint with custom day range."""
        response = client.get("/report/summary?days=7")
        assert response.status_code == 200
        
        data = response.json()
        assert data["period"]["days"] == 7
    
    def test_summary_endpoint_invalid_days(self, setup_advanced_test_data):
        """Test summary endpoint with invalid day range."""
        # Test days too small
        response = client.get("/report/summary?days=0")
        assert response.status_code == 422  # Validation error
        
        # Test days too large
        response = client.get("/report/summary?days=400")
        assert response.status_code == 422  # Validation error
    
    def test_report_performance_optimization(self, setup_advanced_test_data):
        """Test that the optimized queries work correctly."""
        start_date = (date.today() - timedelta(days=30)).isoformat()
        end_date = date.today().isoformat()
        
        response = client.get(f"/report/?start_date={start_date}&end_date={end_date}&include_avg=true&include_min=true&include_max=true")
        assert response.status_code == 200
        
        data = response.json()
        metrics = data["metrics"]
        
        # Verify all metrics are calculated correctly
        assert metrics["total_transactions"] > 0
        assert metrics["total_amount"] > 0
        assert metrics["average_amount"] > 0
        assert metrics["minimum_amount"] > 0
        assert metrics["maximum_amount"] > 0
        
        # Verify logical consistency
        assert metrics["minimum_amount"] <= metrics["average_amount"] <= metrics["maximum_amount"]
        assert metrics["successful_transactions"] + metrics["failed_transactions"] == metrics["total_transactions"]
    
    def test_report_with_specific_filters(self, setup_advanced_test_data):
        """Test report endpoint with specific status and type filters."""
        response = client.get("/report/?status=successful&type=payment&include_daily_shift=true")
        assert response.status_code == 200
        
        data = response.json()
        
        # Check filters are applied
        assert data["filters"]["status"] == "successful"
        assert data["filters"]["type"] == "payment"
        
        # Check that only successful transactions are counted
        metrics = data["metrics"]
        assert metrics["successful_transactions"] == metrics["total_transactions"]
        assert metrics["failed_transactions"] == 0
    
    def test_report_date_range_validation(self, setup_advanced_test_data):
        """Test date range validation."""
        start_date = date.today().isoformat()
        end_date = (date.today() - timedelta(days=1)).isoformat()
        
        response = client.get(f"/report/?start_date={start_date}&end_date={end_date}")
        assert response.status_code == 400
        
        data = response.json()
        assert "Start date cannot be after end date" in data["detail"]
    
    def test_report_empty_result_handling(self, setup_advanced_test_data):
        """Test handling of empty results."""
        # Use a date range far in the future
        future_date = (date.today() + timedelta(days=365)).isoformat()
        future_date_end = (date.today() + timedelta(days=366)).isoformat()
        
        response = client.get(f"/report/?start_date={future_date}&end_date={future_date_end}")
        assert response.status_code == 200
        
        data = response.json()
        metrics = data["metrics"]
        
        # Should return zero values for empty result
        assert metrics["total_transactions"] == 0
        assert metrics["total_amount"] == 0
        assert metrics["success_rate"] == 0
