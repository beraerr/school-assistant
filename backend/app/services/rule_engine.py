"""
Rule engine for enforcing data access permissions based on user roles
"""
import sys
import os
from typing import Dict, Any, List, Optional
from sqlalchemy import text
from sqlalchemy.orm import Session

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
from backend.app.models.user import User, UserRole
import logging
import re

logger = logging.getLogger(__name__)


class RuleEngine:
    """Rule engine for role-based access control"""
    
    def __init__(self, db: Session, user: User):
        self.db = db
        self.user = user
        self.role = user.role
    
    def apply_permissions(self, sql_query: str) -> Dict[str, Any]:
        """
        Apply role-based permissions to SQL query
        
        Returns:
            Dictionary with modified SQL query and permission info
        """
        original_query = sql_query.strip()
        
        # Principal has full access
        if self.role == UserRole.PRINCIPAL:
            return {
                "sql": original_query,
                "permissions_applied": False,
                "reason": "Müdür tüm verilere erişebilir"
            }
        
        # Teacher: Only their assigned class
        elif self.role == UserRole.TEACHER:
            modified_query = self._restrict_to_class(original_query, self.user.related_class)
            return {
                "sql": modified_query,
                "permissions_applied": True,
                "reason": f"Öğretmen sadece {self.user.related_class} sınıfına erişebilir"
            }
        
        # Parent: Only their child's data
        elif self.role == UserRole.PARENT:
            modified_query = self._restrict_to_student(original_query, self.user.related_id)
            return {
                "sql": modified_query,
                "permissions_applied": True,
                "reason": f"Veli sadece kendi çocuğunun (ID: {self.user.related_id}) verilerine erişebilir"
            }
        
        # Student: Only their own data
        elif self.role == UserRole.STUDENT:
            modified_query = self._restrict_to_student(original_query, self.user.related_id)
            return {
                "sql": modified_query,
                "permissions_applied": True,
                "reason": f"Öğrenci sadece kendi (ID: {self.user.related_id}) verilerine erişebilir"
            }
        
        else:
            raise ValueError(f"Unknown role: {self.role}")
    
    def _restrict_to_class(self, sql_query: str, class_name: str) -> str:
        """Add WHERE clause to restrict query to specific class"""
        if not class_name:
            raise ValueError("Class name not specified for teacher")
        
        # Check if query already has WHERE clause
        sql_upper = sql_query.upper()
        
        # Find the position after FROM/JOIN clauses
        # Simple approach: Add WHERE or AND clause
        if "WHERE" in sql_upper:
            # Add AND condition
            # Find the last WHERE or before GROUP BY/ORDER BY/LIMIT
            pattern = r'(\s+WHERE\s+[^GOL]+?)(?=\s+(?:GROUP\s+BY|ORDER\s+BY|LIMIT|$))'
            match = re.search(pattern, sql_query, re.IGNORECASE | re.DOTALL)
            if match:
                # Add AND condition
                return sql_query[:match.end()] + f" AND students.class_name = '{class_name}'" + sql_query[match.end():]
            else:
                # Add at the end before GROUP BY/ORDER BY/LIMIT
                return re.sub(
                    r'(\s+WHERE\s+.*?)(?=\s+(?:GROUP\s+BY|ORDER\s+BY|LIMIT|$))',
                    lambda m: m.group(1) + f" AND students.class_name = '{class_name}'",
                    sql_query,
                    flags=re.IGNORECASE | re.DOTALL
                )
        else:
            # Add WHERE clause
            # Find position after FROM/JOIN, before GROUP BY/ORDER BY/LIMIT
            pattern = r'(\s+FROM\s+\w+(?:\s+(?:INNER|LEFT|RIGHT|FULL)?\s*JOIN\s+\w+)*)'
            match = re.search(pattern, sql_query, re.IGNORECASE)
            if match:
                insert_pos = match.end()
                # Check if there's GROUP BY/ORDER BY/LIMIT after
                remaining = sql_query[insert_pos:]
                if re.search(r'\s+(GROUP\s+BY|ORDER\s+BY|LIMIT)', remaining, re.IGNORECASE):
                    # Insert before GROUP BY/ORDER BY/LIMIT
                    return re.sub(
                        r'(\s+FROM\s+.*?)(\s+(?:GROUP\s+BY|ORDER\s+BY|LIMIT))',
                        lambda m: m.group(1) + f" WHERE students.class_name = '{class_name}'" + m.group(2),
                        sql_query,
                        flags=re.IGNORECASE | re.DOTALL
                    )
                else:
                    return sql_query[:insert_pos] + f" WHERE students.class_name = '{class_name}'" + sql_query[insert_pos:]
        
        # Fallback: simple append
        return f"{sql_query} WHERE students.class_name = '{class_name}'"
    
    def _restrict_to_student(self, sql_query: str, student_id: int) -> str:
        """Add WHERE clause to restrict query to specific student"""
        if not student_id:
            raise ValueError("Student ID not specified")
        
        sql_upper = sql_query.upper()
        
        # Check if query already has WHERE clause
        if "WHERE" in sql_upper:
            # Add AND condition
            pattern = r'(\s+WHERE\s+[^GOL]+?)(?=\s+(?:GROUP\s+BY|ORDER\s+BY|LIMIT|$))'
            match = re.search(pattern, sql_query, re.IGNORECASE | re.DOTALL)
            if match:
                return sql_query[:match.end()] + f" AND students.id = {student_id}" + sql_query[match.end():]
            else:
                return re.sub(
                    r'(\s+WHERE\s+.*?)(?=\s+(?:GROUP\s+BY|ORDER\s+BY|LIMIT|$))',
                    lambda m: m.group(1) + f" AND students.id = {student_id}",
                    sql_query,
                    flags=re.IGNORECASE | re.DOTALL
                )
        else:
            # Add WHERE clause
            pattern = r'(\s+FROM\s+\w+(?:\s+(?:INNER|LEFT|RIGHT|FULL)?\s*JOIN\s+\w+)*)'
            match = re.search(pattern, sql_query, re.IGNORECASE)
            if match:
                insert_pos = match.end()
                remaining = sql_query[insert_pos:]
                if re.search(r'\s+(GROUP\s+BY|ORDER\s+BY|LIMIT)', remaining, re.IGNORECASE):
                    return re.sub(
                        r'(\s+FROM\s+.*?)(\s+(?:GROUP\s+BY|ORDER\s+BY|LIMIT))',
                        lambda m: m.group(1) + f" WHERE students.id = {student_id}" + m.group(2),
                        sql_query,
                        flags=re.IGNORECASE | re.DOTALL
                    )
                else:
                    return sql_query[:insert_pos] + f" WHERE students.id = {student_id}" + sql_query[insert_pos:]
        
        # Fallback
        return f"{sql_query} WHERE students.id = {student_id}"
    
    def sanitize_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Remove sensitive data based on user role
        
        Args:
            results: Query results
        
        Returns:
            Sanitized results
        """
        if self.role == UserRole.PRINCIPAL:
            # Principal sees everything
            return results
        
        # For other roles, remove sensitive fields if present
        sensitive_fields = ["tc_number", "phone", "address", "email"]
        sanitized = []
        
        for row in results:
            sanitized_row = {k: v for k, v in row.items() if k not in sensitive_fields}
            sanitized.append(sanitized_row)
        
        return sanitized
