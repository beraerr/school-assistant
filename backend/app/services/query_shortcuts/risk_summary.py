from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from backend.app.api.risk import RiskItem, compute_student_risk_item, filter_students_for_risk
from backend.app.models.student import Student
from backend.app.models.user import User

_RISK_SUCCESS_RE = re.compile(
    r"başarı\s+(durum|seviye|analizi|özet|skoru)|basari\s+(durum|seviye|analiz|ozet)|"
    r"başarım(\s+nasıl|\s+ne\s+durumda)?|başarı\s+durumum|"
    r"akademik\s+durum|genel\s+(akademik\s+)?durum|"
    r"risk\s+(skoru|skor|faktör|durum|analizi|raporu|degeri|degerleri)|"
    r"risk\s+values?|"
    r"ne\s+kadar\s+başarılı\s+(?!öğrenci)|gelecek\s+beklentisi|"
    r"öğrenci(nin|min)?\s+(?:genel\s+)?(?:başarı|basari|risk|performans)\s+durumu|"
    r"(success|performance)\s+(status|overview)|risk\s+overview|how\s+.*\s+doing\s+academically",
    re.IGNORECASE | re.UNICODE,
)

_HIGHEST_RISK_RE = re.compile(
    r"en\s+yuksek|en\s+yüksek|highest|top|maximum|max(imum)?",
    re.IGNORECASE | re.UNICODE,
)

_FULL_LIST_RE = re.compile(
    r"tüm\s+öğrenci|tum\s+ogrenci|hepsini|tam\s+liste|full\s+list|all\s+students|complete\s+list",
    re.IGNORECASE | re.UNICODE,
)

_TOKEN_RE = re.compile(r"[A-Za-zçğıöşüÇĞİÖŞÜ]+", re.UNICODE)
_POSSESSIVE_SUFFIXES = (
    "larından", "lerinden", "larına", "lerine", "larında", "lerinde",
    "ının", "inin", "unun", "ünün", "nın", "nin", "nun", "nün",
    "ımın", "imin", "umun", "ümün", "mın", "min", "mun", "mün",
    "ı", "i", "u", "ü", "ın", "in", "un", "ün",
)

def _fold(s: str) -> str:
    t = (s or "").strip().lower()
    t = t.replace("ı", "i").replace("İ", "i")
    trans = str.maketrans("çğıöşü", "cgiosu")
    return t.translate(trans)

def _strip_tr_suffix(token: str) -> str:
    if len(token) < 4:
        return token
    for suf in sorted(_POSSESSIVE_SUFFIXES, key=len, reverse=True):
        if len(token) > len(suf) + 2 and token.endswith(suf):
            return token[: -len(suf)]
    return token

def _question_token_bag(question: str) -> set[str]:
    bag: set[str] = set()
    for raw in _TOKEN_RE.findall(question or ""):
        folded = _fold(raw)
        bag.add(folded)
        bag.add(_strip_tr_suffix(folded))
    return {t for t in bag if len(t) >= 2}

def narrow_students_by_name_mention(students: List[Student], question: str) -> List[Student]:
    if len(students) <= 1:
        return students
    q_tokens = _question_token_bag(question)
    if not q_tokens:
        return students

    matched: List[Student] = []
    first_only_hits: List[Student] = []

    for st in students:
        parts = (st.name or "").split()
        if not parts:
            continue
        first = _fold(parts[0])
        if len(parts) >= 2:
            last = _fold(parts[-1])
            if first in q_tokens and last in q_tokens:
                matched.append(st)
        else:
            if first in q_tokens:
                first_only_hits.append(st)

    if matched:
        return matched
    if len(first_only_hits) == 1:
        return first_only_hits
    return students

def _risk_row(item: RiskItem) -> Dict[str, Any]:
    row: Dict[str, Any] = {
        "student_id": item.student_id,
        "student_name": item.student_name,
        "class_name": item.class_name,
        "risk_score": item.risk_score,
        "risk_level": item.risk_level,
        "interpretation": item.explanation,
        "ml_risk_score": item.ml_risk_score,
        "ml_risk_level": item.ml_risk_level,
        "ml_computed_at": item.ml_computed_at,
    }
    return row

def _wants_highest_risk_only(question: str) -> bool:
    return bool(_HIGHEST_RISK_RE.search((question or "").strip()))

def _pick_highest_risk_items(items: List[RiskItem], question: str) -> List[RiskItem]:
    if not items or not _wants_highest_risk_only(question):
        return items
    top_score = items[0].risk_score
    return [it for it in items if abs(it.risk_score - top_score) < 1e-9]

def _wants_full_list(question: str) -> bool:
    return bool(_FULL_LIST_RE.search((question or "").strip()))

def _explain_risk_block(items: List[RiskItem], ui_lang: str) -> str:
    parts: List[str] = []
    for it in items:
        ml_bits = ""
        if it.ml_risk_score is not None:
            if (ui_lang or "tr") == "en":
                ml_bits = f" | ML: {it.ml_risk_score}/100 ({it.ml_risk_level or '-'})"
            else:
                ml_bits = f" | ML: {it.ml_risk_score}/100 ({it.ml_risk_level or '-'})"
        if (ui_lang or "tr") == "en":
            parts.append(
                f"**{it.student_name}** ({it.class_name}): "
                f"Risk {it.risk_score}/100 — {it.risk_level}.{ml_bits} "
                f"{it.explanation}"
            )
        else:
            parts.append(
                f"**{it.student_name}** ({it.class_name}): "
                f"Risk {it.risk_score}/100 — {it.risk_level}.{ml_bits} "
                f"{it.explanation}"
            )
    return "\n\n".join(parts)

def try_risk_success_answer(
    db: Session,
    user: User,
    question: str,
    ui_lang: str,
) -> Optional[Dict[str, Any]]:
    if not _RISK_SUCCESS_RE.search((question or "").strip()):
        return None

    students = filter_students_for_risk(db, user, class_name=None)
    if not students:
        empty_tr = "Görüntülenecek öğrenci kaydı yok veya yetki kapsamı dışında."
        empty_en = "No students in scope for this account."
        return {
            "results": [],
            "sql_query": "-- Risk / başarı özeti (GET /risk/students ile aynı motor)",
            "original_query": question,
            "explanation": empty_tr if (ui_lang or "tr") == "tr" else empty_en,
            "permissions_applied": True,
            "permission_reason": (
                "Risk özeti — rol kapsamı / Risk summary — role scope"
                if (ui_lang or "tr") == "tr"
                else "Risk summary — role scope"
            ),
            "results_count": 0,
            "conversation_mode": "sql",
        }

    students = narrow_students_by_name_mention(students, question)

    items = [compute_student_risk_item(db, s) for s in students]
    items.sort(key=lambda i: i.risk_score, reverse=True)
    items = _pick_highest_risk_items(items, question)
    total_items = len(items)
    if total_items > 10 and not _wants_full_list(question):
        items = items[:10]
    rows = [_risk_row(i) for i in items]

    pr_tr = (
        f"Risk özeti — {len(items)} öğrenci (Risk sekmesiyle aynı hesap) / "
        f"Risk summary — {len(items)} student(s)"
    )
    pr_en = f"Risk summary — {len(items)} student(s), same engine as Risk tab"

    explanation = _explain_risk_block(items, ui_lang or "tr")
    if total_items > len(items):
        if (ui_lang or "tr") == "tr":
            explanation += (
                f"\n\nUzun liste yerine ilk **{len(items)}** kayıt gösterildi. "
                "Tam liste için soruyu 'tüm öğrenciler / tam liste' şeklinde yazabilirsiniz."
            )
        else:
            explanation += (
                f"\n\nShowing the first **{len(items)}** records instead of the full list. "
                "Ask with 'all students / complete list' to get full output."
            )

    return {
        "results": rows,
        "sql_query": "-- Risk / başarı özeti (backend risk motoru; LLM SQL kullanılmadı)",
        "original_query": question,
        "explanation": explanation,
        "permissions_applied": True,
        "permission_reason": pr_tr if (ui_lang or "tr") == "tr" else pr_en,
        "results_count": len(rows),
        "conversation_mode": "sql",
    }
