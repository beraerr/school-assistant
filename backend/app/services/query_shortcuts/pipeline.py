from __future__ import annotations

from typing import Any, Callable, Dict, Optional

from sqlalchemy.orm import Session

from backend.app.models.user import User

from .parent_benchmark import try_parent_benchmark_answer
from .parent_identity import try_parent_bound_child_answer
from .parent_outlook import try_parent_student_outlook_answer
from .project_guide import try_project_guide_answer
from .risk_summary import try_risk_success_answer

_Handler = Callable[[Session, User, str, str], Optional[Dict[str, Any]]]

class NlQueryShortcutPipeline:
    """Doğal dil sorgusu için LLM öncesi iş mantığı zinciri."""

    HANDLERS: tuple[_Handler, ...] = (
        try_project_guide_answer,
        try_parent_bound_child_answer,
        try_parent_benchmark_answer,
        try_parent_student_outlook_answer,
        try_risk_success_answer,
    )

    @classmethod
    def run_before_llm(
        cls,
        db: Session,
        user: User,
        question: str,
        ui_lang: str,
    ) -> Optional[Dict[str, Any]]:
        for fn in cls.HANDLERS:
            out = fn(db, user, question, ui_lang)
            if out is not None:
                return out
        return None
