"""
API endpoints for transaction reports and analytics.
"""

from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, extract
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Transaction, TransactionStatus, TransactionType

router = APIRouter(prefix="/report", tags=["reports"])


@router.get("/")
async def get_transaction_report(
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    status: str = Query("all", description="Filter by status: successful, failed, all"),
    type: str = Query("all", description="Filter by type: payment, invoice, all"),
    include_avg: bool = Query(False, description="Include average amount"),
    include_min: bool = Query(False, description="Include minimum amount"),
    include_max: bool = Query(False, description="Include maximum amount"),
    include_daily_shift: bool = Query(False, description="Include daily data with % change"),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Generate transaction analytics report.
    
    Args:
        start_date: Start date for filtering (optional)
        end_date: End date for filtering (optional)
        status: Filter by transaction status
        type: Filter by transaction type
        include_avg: Include average amount in response
        include_min: Include minimum amount in response
        include_max: Include maximum amount in response
        include_daily_shift: Include daily breakdown with percentage changes
        db: Database session
        
    Returns:
        Dictionary with transaction analytics
    """
    try:
        # Parse dates
        default_start = date.today().replace(day=1)  # First day of current month
        default_end = date.today()
        
        parsed_start_date = _parse_date(start_date) or default_start
        parsed_end_date = _parse_date(end_date) or default_end
        
        # Validate date range
        if parsed_start_date > parsed_end_date:
            raise HTTPException(status_code=400, detail="Start date cannot be after end date")
        
        # Build base query
        query = db.query(Transaction).filter(
            Transaction.transaction_date >= parsed_start_date,
            Transaction.transaction_date <= parsed_end_date
        )
        
        # Apply status filter
        if status != "all":
            try:
                status_enum = TransactionStatus(status.lower())
                query = query.filter(Transaction.status == status_enum)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
        
        # Apply type filter
        if type != "all":
            try:
                type_enum = TransactionType(type.lower())
                query = query.filter(Transaction.type == type_enum)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid type: {type}")
        
        # Calculate basic metrics
        total_count = query.count()
        
        # Calculate total amount (only for successful transactions)
        successful_query = query.filter(Transaction.status == TransactionStatus.SUCCESSFUL)
        total_amount_result = successful_query.with_entities(
            func.coalesce(func.sum(Transaction.amount), 0)
        ).scalar()
        total_amount = Decimal(str(total_amount_result))
        
        # Build response
        response = {
            "period": {
                "start_date": parsed_start_date.isoformat(),
                "end_date": parsed_end_date.isoformat()
            },
            "filters": {
                "status": status,
                "type": type
            },
            "metrics": {
                "total_transactions": total_count,
                "total_amount": float(total_amount)
            }
        }
        
        # Add optional metrics
        if include_avg and total_count > 0:
            avg_result = successful_query.with_entities(
                func.coalesce(func.avg(Transaction.amount), 0)
            ).scalar()
            response["metrics"]["average_amount"] = float(avg_result)
        
        if include_min and total_count > 0:
            min_result = successful_query.with_entities(
                func.coalesce(func.min(Transaction.amount), 0)
            ).scalar()
            response["metrics"]["minimum_amount"] = float(min_result)
        
        if include_max and total_count > 0:
            max_result = successful_query.with_entities(
                func.coalesce(func.max(Transaction.amount), 0)
            ).scalar()
            response["metrics"]["maximum_amount"] = float(max_result)
        
        # Add daily breakdown if requested
        if include_daily_shift:
            daily_data = _get_daily_breakdown(db, parsed_start_date, parsed_end_date, status, type)
            response["daily_breakdown"] = daily_data
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


def _parse_date(date_str: Optional[str]) -> Optional[date]:
    """Parse date string in YYYY-MM-DD format."""
    if not date_str:
        return None
    
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {date_str}. Use YYYY-MM-DD")


def _get_daily_breakdown(
    db: Session, 
    start_date: date, 
    end_date: date, 
    status: str, 
    type: str
) -> List[Dict[str, Any]]:
    """
    Get daily transaction breakdown with percentage changes.
    
    Args:
        db: Database session
        start_date: Start date
        end_date: End date
        status: Status filter
        type: Type filter
        
    Returns:
        List of daily breakdown data
    """
    # Build base query for daily data
    query = db.query(
        func.date(Transaction.transaction_date).label('date'),
        func.count(Transaction.id).label('count'),
        func.coalesce(func.sum(Transaction.amount), 0).label('total_amount')
    ).filter(
        Transaction.transaction_date >= start_date,
        Transaction.transaction_date <= end_date,
        Transaction.status == TransactionStatus.SUCCESSFUL
    )
    
    # Apply filters
    if status != "all":
        query = query.filter(Transaction.status == TransactionStatus(status.lower()))
    if type != "all":
        query = query.filter(Transaction.type == TransactionType(type.lower()))
    
    # Group by date and order
    daily_results = query.group_by(
        func.date(Transaction.transaction_date)
    ).order_by('date').all()
    
    # Convert to list and calculate percentage changes
    daily_data = []
    previous_amount = None
    
    for result in daily_results:
        current_amount = float(result.total_amount)
        percent_change = None
        
        if previous_amount is not None and previous_amount > 0:
            percent_change = ((current_amount - previous_amount) / previous_amount) * 100
        
        daily_data.append({
            "date": result.date.isoformat(),
            "transaction_count": result.count,
            "total_amount": current_amount,
            "percent_change": round(percent_change, 2) if percent_change is not None else None
        })
        
        previous_amount = current_amount
    
    return daily_data
