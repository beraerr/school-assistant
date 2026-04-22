from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from backend.app.models.student import Student
from backend.app.models.user import User, UserRole

_PARENT_CHILD_RE = re.compile(
    r"(ben\s+kimin\s+velisi(yim)?|kimin\s+velisi(yim)?|"
    r"çocuğum(\s+kim)?|çocuğumun\s+(adı|ismi)|"
    r"öğrenci(nin|min)?\s+adı|öğrencim(in)?\s+(adı|kim|ismi)|"
    r"bağlı\s+olduğum\s+öğrenci|velisi\s+olduğum\s+öğrenci|"
    r"who\s+is\s+my\s+child|which\s+student.*\bparent\b)",
    re.IGNORECASE | re.UNICODE,
)

def try_parent_bound_child_answer(
    db: Session,
    user: User,
    question: str,
    ui_lang: str,
) -> Optional[Dict[str, Any]]:
    if user.role != UserRole.PARENT or user.related_id is None:
        return None
    q = (question or "").strip()
    if not _PARENT_CHILD_RE.search(q):
        return None

    sid = int(user.related_id)
    student = db.query(Student).filter(Student.id == sid).first()
    results: List[Dict[str, Any]]
    if not student:
        results = []
        expl_tr = "Hesabınızla eşleşen öğrenci kaydı bulunamadı."
        expl_en = "No student record is linked to this account."
    else:
        results = [
            {
                "id": student.id,
                "name": student.name,
                "class_name": student.class_name,
                "total_absences": student.total_absences,
            }
        ]
        expl_tr = (
            f"Bu hesap {student.class_name} sınıfındaki {student.name} "
            f"(öğrenci kayıt no: {student.id}) velisi olarak tanımlıdır. "
            "Veri sorguları yalnızca bu öğrenci için uygulanır."
        )
        expl_en = (
            f"This account is the parent/guardian of {student.name} "
            f"(student id {student.id}), class {student.class_name}. "
            "Data queries are limited to this student."
        )

    explanation = expl_tr if (ui_lang or "tr") == "tr" else expl_en
    sql_display = (
        "SELECT id, name, class_name, total_absences FROM students WHERE id = "
        f"{sid}  -- veli hesabı related_id ile sınırlandı / bound to parent account"
    )
    pr_tr = "Veli — hesaba bağlı öğrenci (sistem yanıtı, LLM kullanılmadı)."
    pr_en = "Parent — account-bound student (system response, no LLM)."

    return {
        "results": results,
        "sql_query": sql_display,
        "original_query": question,
        "explanation": explanation,
        "permissions_applied": True,
        "permission_reason": pr_tr if (ui_lang or "tr") == "tr" else pr_en,
        "results_count": len(results),
        "conversation_mode": "sql",
    }
