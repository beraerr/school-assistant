from typing import Any, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session
import logging

logger = logging.getLogger(__name__)

class QueryExecutor:
    """Safe SQL query executor"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def execute_query(
        self, sql_query: str, bindparams: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Execute SQL query safely
        
        Args:
            sql_query: SQL query to execute
            bindparams: Optional bound parameters (e.g. RBAC filters from RuleEngine)
        
        Returns:
            List of dictionaries representing rows
        """
        try:
            sql_upper = sql_query.strip().upper()
            if not sql_upper.startswith("SELECT"):
                raise ValueError("Sadece SELECT sorgularına izin verilir")
            
            params = bindparams or {}
            result = self.db.execute(text(sql_query), params)
            
            columns = result.keys()
            rows = []
            for row in result:
                row_dict = {col: value for col, value in zip(columns, row)}
                rows.append(row_dict)
            
            return rows
        
        except Exception as e:
            logger.error(f"Query execution error: {str(e)}")
            raise Exception(f"Sorgu çalıştırma hatası: {str(e)}")
