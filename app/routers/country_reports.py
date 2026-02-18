"""
Country-based transaction reports API endpoints.
"""

from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
import pandas as pd

from app.database import get_db
from app.models import Transaction, TransactionStatus, User
from app.utils.data_loader import load_user_countries

router = APIRouter(prefix="/report", tags=["country_reports"])


@router.get("/by-country")
async def get_country_report(
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    status: str = Query("successful", description="Filter by status: successful, failed, all"),
    type: str = Query("all", description="Filter by type: payment, invoice, all"),
    sort_by: str = Query("total", description="Sort by: count, total, avg"),
    top_n: int = Query(10, description="Number of top countries to return", ge=1, le=100),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Generate transaction analytics report aggregated by country.
    
    Args:
        start_date: Start date for filtering (optional)
        end_date: End date for filtering (optional)
        status: Filter by transaction status
        type: Filter by transaction type
        sort_by: Sort metric (count, total, avg)
        top_n: Number of countries to return
        db: Database session
        
    Returns:
        Dictionary with country-based transaction analytics
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
        
        if sort_by not in ["count", "total", "avg"]:
            raise HTTPException(status_code=400, detail=f"Invalid sort_by: {sort_by}")
        
        # Load user-country mapping
        user_countries = load_user_countries("data/user_countries.csv")
        if not user_countries:
            raise HTTPException(status_code=500, detail="Could not load user-country data")
        
        # Get transaction data
        transactions_df = _get_transactions_dataframe(
            db, parsed_start_date, parsed_end_date, status, type
        )
        
        if transactions_df.empty:
            return {
                "period": {
                    "start_date": parsed_start_date.isoformat(),
                    "end_date": parsed_end_date.isoformat()
                },
                "filters": {
                    "status": status,
                    "type": type,
                    "sort_by": sort_by,
                    "top_n": top_n
                },
                "countries": [],
                "summary": {
                    "total_countries": 0,
                    "total_transactions": 0,
                    "total_amount": 0.0
                }
            }
        
        # Map users to countries
        transactions_df['country'] = transactions_df['user_id'].map(user_countries)
        
        # Filter out transactions without country mapping
        transactions_df = transactions_df.dropna(subset=['country'])
        
        if transactions_df.empty:
            return {
                "period": {
                    "start_date": parsed_start_date.isoformat(),
                    "end_date": parsed_end_date.isoformat()
                },
                "filters": {
                    "status": status,
                    "type": type,
                    "sort_by": sort_by,
                    "top_n": top_n
                },
                "countries": [],
                "summary": {
                    "total_countries": 0,
                    "total_transactions": 0,
                    "total_amount": 0.0
                }
            }
        
        # Aggregate by country
        country_stats = _aggregate_by_country(transactions_df)
        
        # Sort and limit results
        sorted_countries = _sort_and_filter_countries(country_stats, sort_by, top_n)
        
        # Calculate summary statistics
        summary = _calculate_country_summary(sorted_countries, transactions_df)
        
        return {
            "period": {
                "start_date": parsed_start_date.isoformat(),
                "end_date": parsed_end_date.isoformat()
            },
            "filters": {
                "status": status,
                "type": type,
                "sort_by": sort_by,
                "top_n": top_n
            },
            "countries": sorted_countries,
            "summary": summary
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


def _get_transactions_dataframe(
    db: Session,
    start_date: date,
    end_date: date,
    status_filter: str,
    type_filter: str
) -> pd.DataFrame:
    """
    Get transactions as pandas DataFrame.
    
    Args:
        db: Database session
        start_date: Start date
        end_date: End date
        status_filter: Status filter
        type_filter: Type filter
        
    Returns:
        DataFrame with transaction data
    """
    # Build base query
    query = db.query(
        Transaction.user_id,
        Transaction.amount,
        Transaction.status,
        Transaction.type,
        Transaction.transaction_date
    ).filter(
        Transaction.transaction_date >= start_date,
        Transaction.transaction_date <= end_date
    )
    
    # Apply status filter
    if status_filter != "all":
        status_enum = TransactionStatus(status_filter.lower())
        query = query.filter(Transaction.status == status_enum)
    
    # Apply type filter
    if type_filter != "all":
        type_enum = TransactionType(type_filter.lower())
        query = query.filter(Transaction.type == type_enum)
    
    # Execute query and convert to DataFrame
    results = query.all()
    
    if not results:
        return pd.DataFrame()
    
    # Convert to DataFrame
    data = []
    for result in results:
        data.append({
            'user_id': result.user_id,
            'amount': float(result.amount),
            'status': result.status,
            'type': result.type,
            'transaction_date': result.transaction_date
        })
    
    return pd.DataFrame(data)


def _aggregate_by_country(transactions_df: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Aggregate transaction data by country.
    
    Args:
        transactions_df: DataFrame with transaction data
        
    Returns:
        List of country statistics
    """
    # Group by country and calculate metrics
    grouped = transactions_df.groupby('country').agg({
        'amount': ['sum', 'mean', 'count'],
        'user_id': 'nunique'  # Count unique users
    }).round(2)
    
    # Flatten column names
    grouped.columns = ['total_amount', 'average_amount', 'transaction_count', 'unique_users']
    
    # Reset index to make country a column
    grouped = grouped.reset_index()
    
    # Convert to list of dictionaries
    countries = []
    for _, row in grouped.iterrows():
        countries.append({
            "country": row['country'],
            "transaction_count": int(row['transaction_count']),
            "total_amount": float(row['total_amount']),
            "average_amount": float(row['average_amount']),
            "unique_users": int(row['unique_users'])
        })
    
    return countries


def _sort_and_filter_countries(
    countries: List[Dict[str, Any]],
    sort_by: str,
    top_n: int
) -> List[Dict[str, Any]]:
    """
    Sort countries by specified metric and limit to top_n.
    
    Args:
        countries: List of country statistics
        sort_by: Sort metric (count, total, avg)
        top_n: Number of countries to return
        
    Returns:
        Sorted and filtered list of countries
    """
    # Define sort mappings
    sort_mapping = {
        "count": lambda x: x["transaction_count"],
        "total": lambda x: x["total_amount"],
        "avg": lambda x: x["average_amount"]
    }
    
    # Sort countries
    sorted_countries = sorted(
        countries,
        key=sort_mapping[sort_by],
        reverse=True
    )
    
    # Limit to top_n
    return sorted_countries[:top_n]


def _calculate_country_summary(
    countries: List[Dict[str, Any]],
    transactions_df: pd.DataFrame
) -> Dict[str, Any]:
    """
    Calculate summary statistics for country report.
    
    Args:
        countries: List of country statistics
        transactions_df: Original transaction DataFrame
        
    Returns:
        Summary statistics
    """
    if not countries:
        return {
            "total_countries": 0,
            "total_transactions": 0,
            "total_amount": 0.0,
            "average_per_country": 0.0,
            "top_performer": None
        }
    
    # Calculate totals
    total_transactions = sum(country["transaction_count"] for country in countries)
    total_amount = sum(country["total_amount"] for country in countries)
    
    # Average per country
    average_per_country = total_amount / len(countries) if countries else 0
    
    # Get overall statistics from DataFrame
    overall_stats = {
        "total_countries_found": len(transactions_df['country'].unique()),
        "total_transactions_all": len(transactions_df),
        "total_amount_all": float(transactions_df['amount'].sum()),
        "average_transaction_all": float(transactions_df['amount'].mean())
    }
    
    return {
        "total_countries": len(countries),
        "total_transactions": total_transactions,
        "total_amount": round(total_amount, 2),
        "average_per_country": round(average_per_country, 2),
        "top_performer": countries[0]["country"] if countries else None,
        "overall_stats": overall_stats
    }


def _parse_date(date_str: Optional[str]) -> Optional[date]:
    """Parse date string in YYYY-MM-DD format."""
    if not date_str:
        return None
    
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {date_str}. Use YYYY-MM-DD")
