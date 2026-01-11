"""
Query executor for safe SQL execution
"""
from typing import List, Dict, Any
from sqlalchemy import text
from sqlalchemy.orm import Session
import logging

logger = logging.getLogger(__name__)


class QueryExecutor:
    """Safe SQL query executor"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def execute_query(self, sql_query: str) -> List[Dict[str, Any]]:
        """
        Execute SQL query safely
        
        Args:
            sql_query: SQL query to execute
        
        Returns:
            List of dictionaries representing rows
        """
        try:
            # Validate query - only SELECT allowed
            sql_upper = sql_query.strip().upper()
            if not sql_upper.startswith("SELECT"):
                raise ValueError("Sadece SELECT sorgularına izin verilir")
            
            # Execute query
            result = self.db.execute(text(sql_query))
            
            # Convert to list of dictionaries
            columns = result.keys()
            rows = []
            for row in result:
                row_dict = {col: value for col, value in zip(columns, row)}
                rows.append(row_dict)
            
            return rows
        
        except Exception as e:
            logger.error(f"Query execution error: {str(e)}")
            raise Exception(f"Sorgu çalıştırma hatası: {str(e)}")
