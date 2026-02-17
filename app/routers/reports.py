"""
API endpoints for transaction reports and analytics.
"""

from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Transaction, TransactionStatus, TransactionType
from app.utils.analytics import TransactionAnalytics

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
    include_monthly_comparison: bool = Query(False, description="Include monthly comparison"),
    include_top_transactions: bool = Query(False, description="Include top 10 transactions"),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Generate comprehensive transaction analytics report.
    
    Args:
        start_date: Start date for filtering (optional)
        end_date: End date for filtering (optional)
        status: Filter by transaction status
        type: Filter by transaction type
        include_avg: Include average amount in response
        include_min: Include minimum amount in response
        include_max: Include maximum amount in response
        include_daily_shift: Include daily breakdown with percentage changes
        include_monthly_comparison: Include monthly comparison data
        include_top_transactions: Include top 10 transactions by amount
        db: Database session
        
    Returns:
        Dictionary with comprehensive transaction analytics
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
        
        # Validate filters
        if status not in ["all", "successful", "failed"]:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
        
        if type not in ["all", "payment", "invoice"]:
            raise HTTPException(status_code=400, detail=f"Invalid type: {type}")
        
        # Initialize analytics
        analytics = TransactionAnalytics(db)
        
        # Get comprehensive metrics
        metrics = analytics.get_comprehensive_metrics(
            parsed_start_date, parsed_end_date, status, type
        )
        
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
                "total_transactions": metrics["total_transactions"],
                "total_amount": metrics["total_amount"],
                "success_rate": metrics["success_rate"],
                "successful_transactions": metrics["successful_transactions"],
                "failed_transactions": metrics["failed_transactions"],
                "type_breakdown": metrics["type_breakdown"]
            }
        }
        
        # Add optional metrics
        if include_avg:
            response["metrics"]["average_amount"] = metrics["average_amount"]
        
        if include_min:
            response["metrics"]["minimum_amount"] = metrics["minimum_amount"]
        
        if include_max:
            response["metrics"]["maximum_amount"] = metrics["maximum_amount"]
        
        # Add daily breakdown if requested
        if include_daily_shift:
            daily_data = analytics.get_daily_trends(parsed_start_date, parsed_end_date, status, type)
            response["daily_breakdown"] = daily_data
        
        # Add monthly comparison if requested
        if include_monthly_comparison:
            monthly_data = analytics.get_monthly_comparison(parsed_start_date, parsed_end_date, status, type)
            response["monthly_comparison"] = monthly_data
        
        # Add top transactions if requested
        if include_top_transactions:
            top_transactions = analytics.get_top_transactions(parsed_start_date, parsed_end_date, 10, status, type)
            response["top_transactions"] = top_transactions
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/summary")
async def get_transaction_summary(
    days: int = Query(30, description="Number of days to analyze", ge=1, le=365),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get quick transaction summary for the last N days.
    
    Args:
        days: Number of days to look back
        db: Database session
        
    Returns:
        Dictionary with summary metrics
    """
    try:
        end_date = date.today()
        start_date = end_date - timedelta(days=days)
        
        analytics = TransactionAnalytics(db)
        metrics = analytics.get_comprehensive_metrics(start_date, end_date)
        
        return {
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "days": days
            },
            "summary": {
                "total_transactions": metrics["total_transactions"],
                "total_amount": metrics["total_amount"],
                "success_rate": metrics["success_rate"],
                "average_amount": metrics["average_amount"]
            }
        }
        
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
