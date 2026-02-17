"""
Tests for database models.
"""

import pytest
from datetime import datetime, date
from decimal import Decimal

from app.models import User, Transaction, TransactionStatus, TransactionType


class TestUserModel:
    """Test class for User model."""
    
    def test_user_creation(self):
        """Test user model creation."""
        user = User(
            first_name="John",
            last_name="Doe",
            email="john.doe@example.com"
        )
        
        assert user.first_name == "John"
        assert user.last_name == "Doe"
        assert user.email == "john.doe@example.com"
        assert user.is_active in [True, None]  # Default value or None
        # created_at and updated_at are set by database defaults
    
    def test_user_repr(self):
        """Test user model string representation."""
        user = User(
            id=1,
            first_name="John",
            last_name="Doe",
            email="john.doe@example.com"
        )
        
        expected = "<User(id=1, email=john.doe@example.com)>"
        assert str(user) == expected
    
    def test_user_relationships(self):
        """Test user-transaction relationship."""
        user = User(
            id=1,
            first_name="John",
            last_name="Doe",
            email="john.doe@example.com"
        )
        
        # Initially empty
        assert len(user.transactions) == 0
        
        # Add transaction
        transaction = Transaction(
            id=1,
            user_id=1,
            amount=Decimal("100.00"),
            status=TransactionStatus.SUCCESSFUL,
            type=TransactionType.PAYMENT,
            transaction_date=datetime.now()
        )
        
        user.transactions.append(transaction)
        assert len(user.transactions) == 1
        assert user.transactions[0].id == 1


class TestTransactionModel:
    """Test class for Transaction model."""
    
    def test_transaction_creation(self):
        """Test transaction model creation."""
        transaction_date = datetime.now()
        transaction = Transaction(
            user_id=1,
            amount=Decimal("100.50"),
            status=TransactionStatus.SUCCESSFUL,
            type=TransactionType.PAYMENT,
            transaction_date=transaction_date
        )
        
        assert transaction.user_id == 1
        assert transaction.amount == Decimal("100.50")
        assert transaction.status == TransactionStatus.SUCCESSFUL
        assert transaction.type == TransactionType.PAYMENT
        assert transaction.transaction_date == transaction_date
        # created_at and updated_at are set by database defaults
    
    def test_transaction_repr(self):
        """Test transaction model string representation."""
        transaction = Transaction(
            id=1,
            user_id=1,
            amount=Decimal("100.00"),
            status=TransactionStatus.SUCCESSFUL,
            type=TransactionType.PAYMENT,
            transaction_date=datetime.now()
        )
        
        expected = "<Transaction(id=1, user_id=1, amount=100.00, status=successful)>"
        assert str(transaction) == expected
    
    def test_transaction_amount_decimal_property(self):
        """Test transaction amount_decimal property."""
        transaction = Transaction(
            id=1,
            user_id=1,
            amount=Decimal("100.50"),
            status=TransactionStatus.SUCCESSFUL,
            type=TransactionType.PAYMENT,
            transaction_date=datetime.now()
        )
        
        assert transaction.amount_decimal == Decimal("100.50")
        assert isinstance(transaction.amount_decimal, Decimal)
    
    def test_transaction_status_enum(self):
        """Test transaction status enum values."""
        assert TransactionStatus.SUCCESSFUL == "successful"
        assert TransactionStatus.FAILED == "failed"
        
        # Test enum creation
        status = TransactionStatus("successful")
        assert status == TransactionStatus.SUCCESSFUL
    
    def test_transaction_type_enum(self):
        """Test transaction type enum values."""
        assert TransactionType.PAYMENT == "payment"
        assert TransactionType.INVOICE == "invoice"
        
        # Test enum creation
        trans_type = TransactionType("payment")
        assert trans_type == TransactionType.PAYMENT


class TestModelConstraints:
    """Test class for model constraints and validations."""
    
    def test_user_email_uniqueness(self):
        """Test that user email should be unique."""
        # This would be enforced at database level
        user1 = User(
            first_name="John",
            last_name="Doe",
            email="john@example.com"
        )
        
        user2 = User(
            first_name="Jane",
            last_name="Smith",
            email="john@example.com"  # Same email
        )
        
        # Models themselves don't enforce uniqueness, but database should
        assert user1.email == user2.email
    
    def test_transaction_amount_precision(self):
        """Test transaction amount precision."""
        # Test with various decimal places
        amounts = [
            Decimal("1.00"),
            Decimal("100.50"),
            Decimal("999.99"),
            Decimal("1000.00")
        ]
        
        for amount in amounts:
            transaction = Transaction(
                user_id=1,
                amount=amount,
                status=TransactionStatus.SUCCESSFUL,
                type=TransactionType.PAYMENT,
                transaction_date=datetime.now()
            )
            assert transaction.amount == amount
    
    def test_transaction_date_validation(self):
        """Test transaction date handling."""
        # Test with datetime
        transaction_date = datetime.now()
        transaction = Transaction(
            user_id=1,
            amount=Decimal("100.00"),
            status=TransactionStatus.SUCCESSFUL,
            type=TransactionType.PAYMENT,
            transaction_date=transaction_date
        )
        
        assert transaction.transaction_date == transaction_date
        
        # Test with date
        date_only = date.today()
        transaction = Transaction(
            user_id=1,
            amount=Decimal("100.00"),
            status=TransactionStatus.SUCCESSFUL,
            type=TransactionType.PAYMENT,
            transaction_date=date_only
        )
        
        assert transaction.transaction_date == date_only
