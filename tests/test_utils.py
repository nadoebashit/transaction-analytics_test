"""
Tests for utility functions and modules.
"""

import pytest
import tempfile
import os
import pandas as pd
from datetime import date, timedelta

from app.utils.data_loader import load_user_countries
from app.utils.analytics import TransactionAnalytics


class TestDataLoader:
    """Test class for data loader utilities."""
    
    def test_load_user_countries_success(self):
        """Test successful loading of user countries CSV."""
        # Create temporary CSV file
        csv_data = "user_id;country\n1;Germany\n2;France\n3;United States\n"
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(csv_data)
            temp_csv_path = f.name
        
        try:
            result = load_user_countries(temp_csv_path)
            
            assert isinstance(result, dict)
            assert len(result) == 3
            assert result[1] == "Germany"
            assert result[2] == "France"
            assert result[3] == "United States"
            
        finally:
            os.unlink(temp_csv_path)
    
    def test_load_user_countries_empty_file(self):
        """Test loading empty CSV file."""
        # Create empty CSV file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("")
            temp_csv_path = f.name
        
        try:
            result = load_user_countries(temp_csv_path)
            assert result == {}
            
        finally:
            os.unlink(temp_csv_path)
    
    def test_load_user_countries_invalid_file(self):
        """Test loading non-existent CSV file."""
        result = load_user_countries("non_existent_file.csv")
        assert result == {}
    
    def test_load_user_countries_malformed_csv(self):
        """Test loading malformed CSV file."""
        # Create malformed CSV file
        csv_data = "invalid,csv,format\nno,semicolon,separators"
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(csv_data)
            temp_csv_path = f.name
        
        try:
            result = load_user_countries(temp_csv_path)
            # Should return empty dict on error
            assert result == {}
            
        finally:
            os.unlink(temp_csv_path)


class TestTransactionAnalytics:
    """Test class for transaction analytics utilities."""
    
    @pytest.fixture
    def mock_db_session(self):
        """Mock database session for testing."""
        class MockQuery:
            def __init__(self, data=None):
                self.data = data or []
                self.filters = []
                self.group_by_fields = []
            
            def filter(self, *args):
                self.filters.extend(args)
                return self
            
            def group_by(self, *args):
                self.group_by_fields.extend(args)
                return self
            
            def order_by(self, *args):
                return self
            
            def limit(self, limit):
                return self
            
            def all(self):
                # Return mock data based on filters
                if any('successful' in str(f) for f in self.filters):
                    return [
                        MockResult(100, 5000.0, 50.0, 10.0, 100.0),
                        MockResult(50, 2500.0, 50.0, 20.0, 80.0)
                    ]
                return []
            
            def first(self):
                results = self.all()
                return results[0] if results else MockResult(0, 0.0, 0.0, 0.0, 0.0)
        
        class MockResult:
            def __init__(self, count, total, avg, min_amt, max_amt):
                self.total_count = count
                self.total_amount = total
                self.avg_amount = avg
                self.min_amount = min_amt
                self.max_amount = max_amt
                self.successful_count = count
                self.successful_amount = total
                self.successful_avg = avg
                self.failed_count = 0
                self.failed_amount = 0.0
        
        class MockSession:
            def query(self, *args):
                return MockQuery()
        
        return MockSession()
    
    def test_analytics_initialization(self, mock_db_session):
        """Test TransactionAnalytics initialization."""
        analytics = TransactionAnalytics(mock_db_session)
        assert analytics.db == mock_db_session
    
    def test_get_comprehensive_metrics_structure(self, mock_db_session):
        """Test structure of comprehensive metrics."""
        analytics = TransactionAnalytics(mock_db_session)
        
        start_date = date.today() - timedelta(days=30)
        end_date = date.today()
        
        metrics = analytics.get_comprehensive_metrics(start_date, end_date)
        
        # Check required fields
        required_fields = [
            'total_transactions', 'total_amount', 'average_amount',
            'minimum_amount', 'maximum_amount', 'successful_transactions',
            'successful_amount', 'failed_transactions', 'success_rate',
            'type_breakdown'
        ]
        
        for field in required_fields:
            assert field in metrics
        
        # Check type breakdown structure
        type_breakdown = metrics['type_breakdown']
        assert 'payment' in type_breakdown
        assert 'invoice' in type_breakdown
        assert 'count' in type_breakdown['payment']
        assert 'amount' in type_breakdown['payment']
    
    def test_get_daily_trends_structure(self, mock_db_session):
        """Test structure of daily trends."""
        analytics = TransactionAnalytics(mock_db_session)
        
        start_date = date.today() - timedelta(days=30)
        end_date = date.today()
        
        trends = analytics.get_daily_trends(start_date, end_date)
        
        assert isinstance(trends, list)
        
        if trends:
            first_day = trends[0]
            required_fields = [
                'date', 'transaction_count', 'total_amount',
                'average_amount', 'amount_change_percent', 'count_change_percent'
            ]
            
            for field in required_fields:
                assert field in first_day
    
    def test_get_monthly_comparison_structure(self, mock_db_session):
        """Test structure of monthly comparison."""
        analytics = TransactionAnalytics(mock_db_session)
        
        start_date = date.today() - timedelta(days=90)
        end_date = date.today()
        
        monthly = analytics.get_monthly_comparison(start_date, end_date)
        
        assert isinstance(monthly, list)
        
        if monthly:
            first_month = monthly[0]
            required_fields = [
                'period', 'year', 'month', 'transaction_count',
                'total_amount', 'average_amount'
            ]
            
            for field in required_fields:
                assert field in first_month
    
    def test_get_top_transactions_structure(self, mock_db_session):
        """Test structure of top transactions."""
        analytics = TransactionAnalytics(mock_db_session)
        
        start_date = date.today() - timedelta(days=30)
        end_date = date.today()
        
        top_transactions = analytics.get_top_transactions(start_date, end_date, 5)
        
        assert isinstance(top_transactions, list)
        assert len(top_transactions) <= 5
        
        if top_transactions:
            first_transaction = top_transactions[0]
            required_fields = [
                'transaction_id', 'user_id', 'amount', 'status',
                'type', 'transaction_date'
            ]
            
            for field in required_fields:
                assert field in first_transaction


class TestAnalyticsEdgeCases:
    """Test edge cases for analytics functions."""
    
    @pytest.fixture
    def empty_db_session(self):
        """Mock empty database session."""
        class MockEmptyQuery:
            def filter(self, *args):
                return self
            
            def group_by(self, *args):
                return self
            
            def order_by(self, *args):
                return self
            
            def limit(self, limit):
                return self
            
            def all(self):
                return []
            
            def first(self):
                return MockEmptyResult()
        
        class MockEmptyResult:
            def __init__(self):
                self.total_count = 0
                self.total_amount = 0.0
                self.avg_amount = 0.0
                self.min_amount = 0.0
                self.max_amount = 0.0
                self.successful_count = 0
                self.successful_amount = 0.0
                self.successful_avg = 0.0
                self.failed_count = 0
                self.failed_amount = 0.0
        
        class MockEmptySession:
            def query(self, *args):
                return MockEmptyQuery()
        
        return MockEmptySession()
    
    def test_empty_data_handling(self, empty_db_session):
        """Test analytics with empty data."""
        analytics = TransactionAnalytics(empty_db_session)
        
        start_date = date.today() - timedelta(days=30)
        end_date = date.today()
        
        metrics = analytics.get_comprehensive_metrics(start_date, end_date)
        
        # Should return zero values
        assert metrics['total_transactions'] == 0
        assert metrics['total_amount'] == 0.0
        assert metrics['success_rate'] == 0.0
        
        # Type breakdown should be empty but present
        assert 'payment' in metrics['type_breakdown']
        assert 'invoice' in metrics['type_breakdown']
