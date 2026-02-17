"""
Advanced analytics utilities for transaction reporting.
"""

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Tuple, Any

from sqlalchemy import func, and_, or_, extract, case
from sqlalchemy.orm import Session

from app.models import Transaction, TransactionStatus, TransactionType


class TransactionAnalytics:
    """Advanced analytics calculator for transactions."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_comprehensive_metrics(
        self,
        start_date: date,
        end_date: date,
        status_filter: str = "all",
        type_filter: str = "all"
    ) -> Dict[str, Any]:
        """
        Get comprehensive transaction metrics with optimized queries.
        
        Args:
            start_date: Start date for analysis
            end_date: End date for analysis
            status_filter: Status filter (successful/failed/all)
            type_filter: Type filter (payment/invoice/all)
            
        Returns:
            Dictionary with comprehensive metrics
        """
        # Build base filter conditions
        base_filters = [
            Transaction.transaction_date >= start_date,
            Transaction.transaction_date <= end_date
        ]
        
        # Add status filter
        if status_filter != "all":
            status_enum = TransactionStatus(status_filter.lower())
            base_filters.append(Transaction.status == status_enum)
        
        # Add type filter
        if type_filter != "all":
            type_enum = TransactionType(type_filter.lower())
            base_filters.append(Transaction.type == type_enum)
        
        # Single query for basic metrics
        basic_query = self.db.query(
            func.count(Transaction.id).label('total_count'),
            func.coalesce(func.sum(Transaction.amount), 0).label('total_amount'),
            func.coalesce(func.avg(Transaction.amount), 0).label('avg_amount'),
            func.coalesce(func.min(Transaction.amount), 0).label('min_amount'),
            func.coalesce(func.max(Transaction.amount), 0).label('max_amount')
        ).filter(and_(*base_filters))
        
        basic_result = basic_query.first()
        
        # Successful transactions query
        successful_filters = base_filters + [Transaction.status == TransactionStatus.SUCCESSFUL]
        successful_query = self.db.query(
            func.count(Transaction.id).label('successful_count'),
            func.coalesce(func.sum(Transaction.amount), 0).label('successful_amount'),
            func.coalesce(func.avg(Transaction.amount), 0).label('successful_avg')
        ).filter(and_(*successful_filters))
        
        successful_result = successful_query.first()
        
        # Failed transactions query
        failed_filters = base_filters + [Transaction.status == TransactionStatus.FAILED]
        failed_query = self.db.query(
            func.count(Transaction.id).label('failed_count'),
            func.coalesce(func.sum(Transaction.amount), 0).label('failed_amount')
        ).filter(and_(*failed_filters))
        
        failed_result = failed_query.first()
        
        # Type breakdown
        type_breakdown = self._get_type_breakdown(base_filters)
        
        # Calculate success rate
        total_transactions = basic_result.total_count
        success_rate = (successful_result.successful_count / total_transactions * 100) if total_transactions > 0 else 0
        
        return {
            "total_transactions": basic_result.total_count,
            "total_amount": float(basic_result.total_amount),
            "average_amount": float(basic_result.avg_amount),
            "minimum_amount": float(basic_result.min_amount),
            "maximum_amount": float(basic_result.max_amount),
            "successful_transactions": successful_result.successful_count,
            "successful_amount": float(successful_result.successful_amount),
            "failed_transactions": failed_result.failed_count,
            "success_rate": round(success_rate, 2),
            "type_breakdown": type_breakdown
        }
    
    def get_daily_trends(
        self,
        start_date: date,
        end_date: date,
        status_filter: str = "all",
        type_filter: str = "all"
    ) -> List[Dict[str, Any]]:
        """
        Get daily transaction trends with percentage changes.
        
        Args:
            start_date: Start date for analysis
            end_date: End date for analysis
            status_filter: Status filter
            type_filter: Type filter
            
        Returns:
            List of daily trend data
        """
        # Build base filters
        base_filters = [
            Transaction.transaction_date >= start_date,
            Transaction.transaction_date <= end_date,
            Transaction.status == TransactionStatus.SUCCESSFUL
        ]
        
        if status_filter != "all":
            status_enum = TransactionStatus(status_filter.lower())
            base_filters[2] = (Transaction.status == status_enum)
        
        if type_filter != "all":
            type_enum = TransactionType(type_filter.lower())
            base_filters.append(Transaction.type == type_enum)
        
        # Daily aggregation query
        daily_query = self.db.query(
            func.date(Transaction.transaction_date).label('date'),
            func.count(Transaction.id).label('count'),
            func.coalesce(func.sum(Transaction.amount), 0).label('total_amount'),
            func.coalesce(func.avg(Transaction.amount), 0).label('avg_amount')
        ).filter(and_(*base_filters)).group_by(
            func.date(Transaction.transaction_date)
        ).order_by('date')
        
        results = daily_query.all()
        
        # Calculate trends and percentage changes
        trends = []
        previous_amount = None
        previous_count = None
        
        for result in results:
            current_amount = float(result.total_amount)
            current_count = result.count
            
            # Calculate percentage changes
            amount_change = None
            count_change = None
            
            if previous_amount is not None and previous_amount > 0:
                amount_change = ((current_amount - previous_amount) / previous_amount) * 100
            
            if previous_count is not None and previous_count > 0:
                count_change = ((current_count - previous_count) / previous_count) * 100
            
            trends.append({
                "date": result.date.isoformat(),
                "transaction_count": current_count,
                "total_amount": current_amount,
                "average_amount": float(result.avg_amount),
                "amount_change_percent": round(amount_change, 2) if amount_change is not None else None,
                "count_change_percent": round(count_change, 2) if count_change is not None else None
            })
            
            previous_amount = current_amount
            previous_count = current_count
        
        return trends
    
    def get_monthly_comparison(
        self,
        start_date: date,
        end_date: date,
        status_filter: str = "all",
        type_filter: str = "all"
    ) -> List[Dict[str, Any]]:
        """
        Get monthly comparison data.
        
        Args:
            start_date: Start date for analysis
            end_date: End date for analysis
            status_filter: Status filter
            type_filter: Type filter
            
        Returns:
            List of monthly comparison data
        """
        # Build base filters
        base_filters = [
            Transaction.transaction_date >= start_date,
            Transaction.transaction_date <= end_date,
            Transaction.status == TransactionStatus.SUCCESSFUL
        ]
        
        if status_filter != "all":
            status_enum = TransactionStatus(status_filter.lower())
            base_filters[2] = (Transaction.status == status_enum)
        
        if type_filter != "all":
            type_enum = TransactionType(type_filter.lower())
            base_filters.append(Transaction.type == type_enum)
        
        # Monthly aggregation query
        monthly_query = self.db.query(
            extract('year', Transaction.transaction_date).label('year'),
            extract('month', Transaction.transaction_date).label('month'),
            func.count(Transaction.id).label('count'),
            func.coalesce(func.sum(Transaction.amount), 0).label('total_amount'),
            func.coalesce(func.avg(Transaction.amount), 0).label('avg_amount')
        ).filter(and_(*base_filters)).group_by(
            extract('year', Transaction.transaction_date),
            extract('month', Transaction.transaction_date)
        ).order_by('year', 'month')
        
        results = monthly_query.all()
        
        # Format results
        monthly_data = []
        for result in results:
            month_name = datetime(result.year, int(result.month), 1).strftime('%B %Y')
            
            monthly_data.append({
                "period": month_name,
                "year": int(result.year),
                "month": int(result.month),
                "transaction_count": result.count,
                "total_amount": float(result.total_amount),
                "average_amount": float(result.avg_amount)
            })
        
        return monthly_data
    
    def _get_type_breakdown(self, base_filters: List) -> Dict[str, Any]:
        """Get transaction type breakdown."""
        # Payment transactions
        payment_filters = base_filters + [Transaction.type == TransactionType.PAYMENT]
        payment_query = self.db.query(
            func.count(Transaction.id).label('count'),
            func.coalesce(func.sum(Transaction.amount), 0).label('amount')
        ).filter(and_(*payment_filters))
        
        payment_result = payment_query.first()
        
        # Invoice transactions
        invoice_filters = base_filters + [Transaction.type == TransactionType.INVOICE]
        invoice_query = self.db.query(
            func.count(Transaction.id).label('count'),
            func.coalesce(func.sum(Transaction.amount), 0).label('amount')
        ).filter(and_(*invoice_filters))
        
        invoice_result = invoice_query.first()
        
        return {
            "payment": {
                "count": payment_result.count,
                "amount": float(payment_result.amount)
            },
            "invoice": {
                "count": invoice_result.count,
                "amount": float(invoice_result.amount)
            }
        }
    
    def get_top_transactions(
        self,
        start_date: date,
        end_date: date,
        limit: int = 10,
        status_filter: str = "all",
        type_filter: str = "all"
    ) -> List[Dict[str, Any]]:
        """
        Get top transactions by amount.
        
        Args:
            start_date: Start date for analysis
            end_date: End date for analysis
            limit: Number of top transactions to return
            status_filter: Status filter
            type_filter: Type filter
            
        Returns:
            List of top transactions
        """
        # Build base filters
        base_filters = [
            Transaction.transaction_date >= start_date,
            Transaction.transaction_date <= end_date
        ]
        
        if status_filter != "all":
            status_enum = TransactionStatus(status_filter.lower())
            base_filters.append(Transaction.status == status_enum)
        
        if type_filter != "all":
            type_enum = TransactionType(type_filter.lower())
            base_filters.append(Transaction.type == type_enum)
        
        # Query for top transactions
        top_query = self.db.query(
            Transaction.id,
            Transaction.user_id,
            Transaction.amount,
            Transaction.status,
            Transaction.type,
            Transaction.transaction_date
        ).filter(and_(*base_filters)).order_by(
            Transaction.amount.desc()
        ).limit(limit)
        
        results = top_query.all()
        
        top_transactions = []
        for result in results:
            top_transactions.append({
                "transaction_id": result.id,
                "user_id": result.user_id,
                "amount": float(result.amount),
                "status": result.status.value,
                "type": result.type.value,
                "transaction_date": result.transaction_date.isoformat()
            })
        
        return top_transactions
