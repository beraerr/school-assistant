from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Dict, Any, Literal

from backend.app.core.database import get_db
from backend.app.api.dependencies import get_current_user
from backend.app.models.user import User
from backend.app.services.llm_service import LLMService
from backend.app.services.rule_engine import RuleEngine
from backend.app.utils.query_executor import QueryExecutor
from backend.app.services.query_shortcuts import NlQueryShortcutPipeline
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/query", tags=["queries"])

class QueryRequest(BaseModel):
    query: str  # Turkish natural language query
    ui_lang: Literal["tr", "en"] = "tr"

class QueryResponse(BaseModel):
    results: List[Dict[str, Any]]
    sql_query: str
    original_query: str
    explanation: str
    permissions_applied: bool
    permission_reason: str
    results_count: int
    conversation_mode: Literal["sql", "chat"] = "sql"

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
        shortcut = NlQueryShortcutPipeline.run_before_llm(
            db, current_user, query_request.query, query_request.ui_lang
        )
        if shortcut:
            return shortcut

        llm_service = LLMService()
        user_context = {
            "role": current_user.role.value,
            "related_id": current_user.related_id,
            "related_class": current_user.related_class
        }

        intent = llm_service.interpret_intent(
            query_request.query,
            user_context=user_context,
            ui_lang=query_request.ui_lang,
        )
        if intent.get("mode") == "chat":
            pr = (
                "Sohbet modu — SQL çalıştırılmadı."
                if query_request.ui_lang == "tr"
                else "Chat mode — no SQL executed."
            )
            return {
                "results": [],
                "sql_query": "",
                "original_query": query_request.query,
                "explanation": intent.get("reply", ""),
                "permissions_applied": False,
                "permission_reason": pr,
                "results_count": 0,
                "conversation_mode": "chat",
            }

        llm_result = llm_service.convert_to_sql(
            query_request.query,
            user_context=user_context
        )
        sql_query = llm_result["sql"]
        
        rule_engine = RuleEngine(db, current_user)
        permission_result = rule_engine.apply_permissions(sql_query)
        final_sql = permission_result["sql"]
        bindparams = permission_result.get("bindparams") or {}
        
        query_executor = QueryExecutor(db)
        results = query_executor.execute_query(final_sql, bindparams=bindparams)
        
        sanitized_results = rule_engine.sanitize_results(results)
        
        explanation = llm_service.explain_query(
            final_sql,
            query_request.query,
            len(sanitized_results),
            sanitized_results,
            ui_lang=query_request.ui_lang,
        )
        
        return {
            "results": sanitized_results,
            "sql_query": final_sql,
            "original_query": query_request.query,
            "explanation": explanation,
            "permissions_applied": permission_result["permissions_applied"],
            "permission_reason": permission_result["reason"],
            "results_count": len(sanitized_results),
            "conversation_mode": "sql",
        }
    
    except Exception as e:
        logger.error(f"Query execution error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Sorgu işlenirken hata oluştu: {str(e)}"
        )
