"""
Query endpoints for natural language queries
"""
import sys
import os
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Dict, Any

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
from backend.app.core.database import get_db
from backend.app.api.dependencies import get_current_user
from backend.app.models.user import User
from backend.app.services.llm_service import LLMService
from backend.app.services.rule_engine import RuleEngine
from backend.app.utils.query_executor import QueryExecutor
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/query", tags=["queries"])

# Initialize LLM service (singleton)
llm_service = LLMService()


class QueryRequest(BaseModel):
    query: str  # Turkish natural language query


class QueryResponse(BaseModel):
    results: List[Dict[str, Any]]
    sql_query: str
    original_query: str
    explanation: str
    permissions_applied: bool
    permission_reason: str
    results_count: int


@router.post("/", response_model=QueryResponse)
async def execute_query(
    query_request: QueryRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Execute natural language query with role-based permissions
    """
    try:
        # Step 1: Convert Turkish NLQ to SQL using LLM
        user_context = {
            "role": current_user.role.value,
            "related_id": current_user.related_id,
            "related_class": current_user.related_class
        }
        
        llm_result = llm_service.convert_to_sql(
            query_request.query,
            user_context=user_context
        )
        sql_query = llm_result["sql"]
        
        # Step 2: Apply role-based permissions using rule engine
        rule_engine = RuleEngine(db, current_user)
        permission_result = rule_engine.apply_permissions(sql_query)
        final_sql = permission_result["sql"]
        
        # Step 3: Execute query
        query_executor = QueryExecutor(db)
        results = query_executor.execute_query(final_sql)
        
        # Step 4: Sanitize results (remove sensitive data)
        sanitized_results = rule_engine.sanitize_results(results)
        
        # Step 5: Generate explanation
        explanation = llm_service.explain_query(
            final_sql,
            query_request.query,
            len(sanitized_results)
        )
        
        return {
            "results": sanitized_results,
            "sql_query": final_sql,
            "original_query": query_request.query,
            "explanation": explanation,
            "permissions_applied": permission_result["permissions_applied"],
            "permission_reason": permission_result["reason"],
            "results_count": len(sanitized_results)
        }
    
    except Exception as e:
        logger.error(f"Query execution error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Sorgu işlenirken hata oluştu: {str(e)}"
        )
