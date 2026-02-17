"""
SQLAlchemy models for users and transactions.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    Boolean, Column, DateTime, 
    Enum, ForeignKey, Index, Integer, Numeric, String
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class TransactionType(str, Enum):
    """Transaction type enumeration."""
    PAYMENT = "payment"
    INVOICE = "invoice"


class TransactionStatus(str, Enum):
    """Transaction status enumeration."""
    SUCCESSFUL = "successful"
    FAILED = "failed"


class User(Base):
    """
    User model representing application users.
    
    Attributes:
        id: Primary key
        first_name: User's first name
        last_name: User's last name
        email: User's email (unique)
        created_at: Account creation timestamp
        updated_at: Last update timestamp
        is_active: Whether user is active
        transactions: Relationship to user's transactions
    """
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Relationships
    transactions = relationship("Transaction", back_populates="user", cascade="all, delete-orphan")
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_users_email_active', 'email', 'is_active'),
        Index('idx_users_created_at', 'created_at'),
    )
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email})>"


class Transaction(Base):
    """
    Transaction model representing financial transactions.
    
    Attributes:
        id: Primary key
        user_id: Foreign key to user
        amount: Transaction amount
        status: Transaction status (successful/failed)
        type: Transaction type (payment/invoice)
        transaction_date: Date of transaction
        created_at: Record creation timestamp
        updated_at: Last update timestamp
        user: Relationship to transaction owner
    """
    __tablename__ = "transactions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    amount = Column(Numeric(10, 2), nullable=False)
    status = Column(String(20), nullable=False, index=True)
    type = Column(String(20), nullable=False, index=True)
    transaction_date = Column(DateTime(timezone=True), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="transactions")
    
    # Indexes for performance optimization
    __table_args__ = (
        Index('idx_transactions_user_status', 'user_id', 'status'),
        Index('idx_transactions_date_status', 'transaction_date', 'status'),
        Index('idx_transactions_type_status', 'type', 'status'),
        Index('idx_transactions_user_date', 'user_id', 'transaction_date'),
        Index('idx_transactions_amount_status', 'amount', 'status'),
    )
    
    def __repr__(self) -> str:
        return f"<Transaction(id={self.id}, user_id={self.user_id}, amount={self.amount}, status={self.status})>"
    
    @property
    def amount_decimal(self) -> Decimal:
        """Get amount as Decimal for precise calculations."""
        return Decimal(str(self.amount))
