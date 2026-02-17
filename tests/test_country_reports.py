"""
Tests for the country-based reports API endpoints.
"""

import pytest
from datetime import date, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import pandas as pd
import tempfile
import os

from app.main import app
from app.database import get_db, Base
from app.models import User, Transaction, TransactionStatus, TransactionType

# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_country.db"
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
def setup_country_test_data():
    """Setup test data for country reports testing."""
    # Create tables
    Base.metadata.create_all(bind=engine)
    
    db = TestingSessionLocal()
    
    try:
        # Create test users
        users = []
        for i in range(20):
            user = User(
                first_name=f"Country{i}",
                last_name=f"User{i}",
                email=f"country{i}@example.com"
            )
            users.append(user)
        
        db.add_all(users)
        db.commit()
        
        # Refresh to get IDs
        for user in users:
            db.refresh(user)
        
        # Create test transactions
        base_date = date.today() - timedelta(days=60)
        transactions = []
        
        for i in range(200):
            transaction = Transaction(
                user_id=users[i % len(users)].id,
                amount=50.0 + (i % 200),
                status=TransactionStatus.SUCCESSFUL if i % 4 != 0 else TransactionStatus.FAILED,
                type=TransactionType.PAYMENT if i % 2 == 0 else TransactionType.INVOICE,
                transaction_date=base_date + timedelta(days=i % 60)
            )
            transactions.append(transaction)
        
        db.add_all(transactions)
        db.commit()
        
        # Create temporary CSV file with user-country mapping
        csv_data = "user_id;country\n"
        country_mapping = [
            "Germany", "Canada", "France", "United States", "India",
            "Brazil", "Japan", "Australia", "Poland", "United Kingdom",
            "Italy", "Spain", "Netherlands", "Sweden", "Mexico",
            "Argentina", "South Korea", "Thailand", "Malaysia", "Singapore"
        ]
        
        for i, user in enumerate(users):
            csv_data += f"{user.id};{country_mapping[i % len(country_mapping)]}\n"
        
        # Write to temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(csv_data)
            temp_csv_path = f.name
        
        # Update the data_loader to use our temp file
        import app.utils.data_loader
        original_load = app.utils.data_loader.load_user_countries
        
        def mock_load_user_countries(csv_path):
            """Mock loader that uses our temp file."""
            try:
                df = pd.read_csv(temp_csv_path, sep=';')
                user_countries = dict(zip(df['user_id'], df['country']))
                return user_countries
            except Exception:
                return {}
        
        app.utils.data_loader.load_user_countries = mock_load_user_countries
        
        yield temp_csv_path
        
    finally:
        # Cleanup
        db.close()
        Base.metadata.drop_all(bind=engine)
        
        # Restore original function
        import app.utils.data_loader
        app.utils.data_loader.load_user_countries = original_load
        
        # Clean up temp file
        if 'temp_csv_path' in locals():
            try:
                os.unlink(temp_csv_path)
            except:
                pass


class TestCountryReportsAPI:
    """Test class for country reports API."""
    
    def test_country_report_basic(self, setup_country_test_data):
        """Test basic country report endpoint."""
        response = client.get("/report/by-country")
        assert response.status_code == 200
        
        data = response.json()
        
        # Check basic structure
        assert "period" in data
        assert "filters" in data
        assert "countries" in data
        assert "summary" in data
        
        # Check filters
        filters = data["filters"]
        assert filters["status"] == "successful"
        assert filters["type"] == "all"
        assert filters["sort_by"] == "total"
        assert filters["top_n"] == 10
        
        # Check countries structure
        countries = data["countries"]
        assert isinstance(countries, list)
        
        if countries:
            first_country = countries[0]
            assert "country" in first_country
            assert "transaction_count" in first_country
            assert "total_amount" in first_country
            assert "average_amount" in first_country
            assert "unique_users" in first_country
            
            # Check data types
            assert isinstance(first_country["transaction_count"], int)
            assert isinstance(first_country["total_amount"], (int, float))
            assert isinstance(first_country["average_amount"], (int, float))
            assert isinstance(first_country["unique_users"], int)
        
        # Check summary
        summary = data["summary"]
        assert "total_countries" in summary
        assert "total_transactions" in summary
        assert "total_amount" in summary
        assert "average_per_country" in summary
        assert "top_performer" in summary
    
    def test_country_report_with_date_filter(self, setup_country_test_data):
        """Test country report with date filters."""
        start_date = (date.today() - timedelta(days=30)).isoformat()
        end_date = date.today().isoformat()
        
        response = client.get(f"/report/by-country?start_date={start_date}&end_date={end_date}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["period"]["start_date"] == start_date
        assert data["period"]["end_date"] == end_date
    
    def test_country_report_sort_by_count(self, setup_country_test_data):
        """Test country report sorted by transaction count."""
        response = client.get("/report/by-country?sort_by=count")
        assert response.status_code == 200
        
        data = response.json()
        countries = data["countries"]
        
        # Check that countries are sorted by count (descending)
        if len(countries) > 1:
            for i in range(len(countries) - 1):
                assert countries[i]["transaction_count"] >= countries[i + 1]["transaction_count"]
    
    def test_country_report_sort_by_total(self, setup_country_test_data):
        """Test country report sorted by total amount."""
        response = client.get("/report/by-country?sort_by=total")
        assert response.status_code == 200
        
        data = response.json()
        countries = data["countries"]
        
        # Check that countries are sorted by total amount (descending)
        if len(countries) > 1:
            for i in range(len(countries) - 1):
                assert countries[i]["total_amount"] >= countries[i + 1]["total_amount"]
    
    def test_country_report_sort_by_avg(self, setup_country_test_data):
        """Test country report sorted by average amount."""
        response = client.get("/report/by-country?sort_by=avg")
        assert response.status_code == 200
        
        data = response.json()
        countries = data["countries"]
        
        # Check that countries are sorted by average amount (descending)
        if len(countries) > 1:
            for i in range(len(countries) - 1):
                assert countries[i]["average_amount"] >= countries[i + 1]["average_amount"]
    
    def test_country_report_top_n_filter(self, setup_country_test_data):
        """Test country report with top_n filter."""
        response = client.get("/report/by-country?top_n=5")
        assert response.status_code == 200
        
        data = response.json()
        countries = data["countries"]
        
        # Should return at most 5 countries
        assert len(countries) <= 5
    
    def test_country_report_status_filter(self, setup_country_test_data):
        """Test country report with status filter."""
        response = client.get("/report/by-country?status=all")
        assert response.status_code == 200
        
        data = response.json()
        assert data["filters"]["status"] == "all"
    
    def test_country_report_type_filter(self, setup_country_test_data):
        """Test country report with type filter."""
        response = client.get("/report/by-country?type=payment")
        assert response.status_code == 200
        
        data = response.json()
        assert data["filters"]["type"] == "payment"
    
    def test_country_report_invalid_sort_by(self, setup_country_test_data):
        """Test country report with invalid sort_by parameter."""
        response = client.get("/report/by-country?sort_by=invalid")
        assert response.status_code == 400
        
        data = response.json()
        assert "Invalid sort_by" in data["detail"]
    
    def test_country_report_invalid_status(self, setup_country_test_data):
        """Test country report with invalid status parameter."""
        response = client.get("/report/by-country?status=invalid")
        assert response.status_code == 400
        
        data = response.json()
        assert "Invalid status" in data["detail"]
    
    def test_country_report_invalid_type(self, setup_country_test_data):
        """Test country report with invalid type parameter."""
        response = client.get("/report/by-country?type=invalid")
        assert response.status_code == 400
        
        data = response.json()
        assert "Invalid type" in data["detail"]
    
    def test_country_report_invalid_top_n(self, setup_country_test_data):
        """Test country report with invalid top_n parameter."""
        # Test top_n too small
        response = client.get("/report/by-country?top_n=0")
        assert response.status_code == 422  # Validation error
        
        # Test top_n too large
        response = client.get("/report/by-country?top_n=101")
        assert response.status_code == 422  # Validation error
    
    def test_country_report_date_validation(self, setup_country_test_data):
        """Test date range validation."""
        start_date = date.today().isoformat()
        end_date = (date.today() - timedelta(days=1)).isoformat()
        
        response = client.get(f"/report/by-country?start_date={start_date}&end_date={end_date}")
        assert response.status_code == 400
        
        data = response.json()
        assert "Start date cannot be after end date" in data["detail"]
    
    def test_country_report_empty_data(self, setup_country_test_data):
        """Test country report with empty transaction data."""
        # Use a date range far in the future
        future_date = (date.today() + timedelta(days=365)).isoformat()
        future_date_end = (date.today() + timedelta(days=366)).isoformat()
        
        response = client.get(f"/report/by-country?start_date={future_date}&end_date={future_date_end}")
        assert response.status_code == 200
        
        data = response.json()
        
        # Should return empty results
        assert data["countries"] == []
        assert data["summary"]["total_countries"] == 0
        assert data["summary"]["total_transactions"] == 0
        assert data["summary"]["total_amount"] == 0.0
    
    def test_country_report_csv_loading_error(self, setup_country_test_data):
        """Test country report when CSV loading fails."""
        import app.utils.data_loader
        
        # Mock the loader to return empty dict
        def mock_empty_loader(csv_path):
            return {}
        
        original_load = app.utils.data_loader.load_user_countries
        app.utils.data_loader.load_user_countries = mock_empty_loader
        
        try:
            response = client.get("/report/by-country")
            assert response.status_code == 500
            
            data = response.json()
            assert "Could not load user-country data" in data["detail"]
        finally:
            # Restore original function
            app.utils.data_loader.load_user_countries = original_load
