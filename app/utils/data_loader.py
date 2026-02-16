"""
Utility functions for loading and processing external data.
"""

import pandas as pd
from typing import Dict, Optional

def load_user_countries(csv_path: str) -> Dict[int, str]:
    """
    Load user-country mapping from CSV file.
    
    Args:
        csv_path: Path to the CSV file
        
    Returns:
        Dictionary mapping user_id to country
    """
    try:
        df = pd.read_csv(csv_path, sep=';')
        # Convert to dictionary
        user_countries = dict(zip(df['user_id'], df['country']))
        return user_countries
    except Exception as e:
        print(f"Error loading user countries: {e}")
        return {}
