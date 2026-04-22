from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.app.api.risk import compute_student_risk_item
from backend.app.models.grade import Grade
from backend.app.models.student import Student
from backend.app.models.user import User, UserRole

_OUTLOOK_RE = re.compile(
    r"("
    r"olasılık|olasilik|olasiligi|olasılığı|"
    r"şans|sans|şansı|sansi|"
    r"probability|likelihood|\bchance\b|how\s+likely|"
    r"dönem\s+sonu|donem\s+sonu|end\s+of\s+term|term\s*end|"
    r"başarı\s+beklentisi|basari\s+beklentisi|başarıya|basariya|"
    r"başarı\s+görme|basari\s+gorme|"
    r"succeed|success\s+(chance|likelihood|probability)|"
    r"do\s+well|beklenti|outlook|prognosis"
    r")",
    re.IGNORECASE | re.UNICODE,
)

_OUTLOOK_CONTEXT = re.compile(
    r"\b("
    r"risk|skor|score|matematik|mathematics|\bmath\b|"
    r"türkçe|turkce|fizik|kimya|ders|not|grades?|"
    r"başarı|basari|success|dönem|donem|term"
    r")\b",
    re.IGNORECASE | re.UNICODE,
)

_MATH_HINT = re.compile(
    r"matematik|mathematics|\bmath\b",
    re.IGNORECASE | re.UNICODE,
)

def _math_avg(db: Session, student_id: int) -> Optional[float]:
    v = (
        db.query(func.avg(Grade.grade))
        .filter(Grade.student_id == student_id, Grade.subject == "Matematik")
        .scalar()
    )
    return float(v) if v is not None else None

def _build_narrative(
    *,
    child_name: str,
    class_name: str,
    item,
    ui_lang: str,
    math_avg: Optional[float],
    math_focus: bool,
) -> str:
    score = float(item.risk_score)
    level = item.risk_level or ""
    ml = item.ml_risk_score
    ml_lev = item.ml_risk_level or ""
    tr = (ui_lang or "tr") == "tr"

    if score < 35:
        band_tr = "Mevcut sinyaller genel olarak olumlu; dönem sonu için güçlü bir çıkış potansiyeli görülüyor."
        band_en = "Signals are broadly positive; end-of-term outlook looks comparatively strong."
    elif score < 65:
        band_tr = "Mevcut sinyaller karışık; dönem sonu için düzenli takip ve akademik destek faydalı olur."
        band_en = "Signals are mixed; steady follow-up and academic support would help toward term-end goals."
    else:
        band_tr = "Mevcut sinyaller yüksek risk bandında; dönem sonu öncesi müdahale ve destek planı önerilir."
        band_en = "Signals sit in the high-risk band; a support plan before term end is recommended."

    ml_line = ""
    if ml is not None:
        if tr:
            ml_line = (
                f" ML modeli olasılık göstergesi **{ml:.0f}/100** "
                f"({ml_lev or '—'}); bu, geçmiş benzer kayıtlara dayalı istatistiksel bir özet olup "
                "kesin sonuç taahhüdü değildir."
            )
        else:
            ml_line = (
                f" The ML indicator is **{ml:.0f}/100** "
                f"({ml_lev or '—'}); this is a statistical summary from similar historical patterns, "
                "not a guarantee."
            )

    math_line = ""
    if math_focus and math_avg is not None:
        if tr:
            math_line = (
                f"\n\nMatematik ders not ortalaması **{math_avg:.1f}/100**; "
                "ML risk skoru genel akademik örüntüleri birlikte değerlendirir."
            )
        else:
            math_line = (
                f"\n\nMathematics average **{math_avg:.1f}/100**; "
                "the ML risk score still reflects overall academic patterns."
            )

    if tr:
        return (
            f"**{child_name}** ({class_name}) için güncel risk skoru **{score:.1f}/100** "
            f"({level}). {band_tr}{ml_line}{math_line}\n\n"
            "Bu metin risk sinyallerine dayalı bir destek özetidir; resmi karar yerine geçmez."
        )
    return (
        f"For **{child_name}** ({class_name}), the current risk score is **{score:.1f}/100** "
        f"({level}). {band_en}{ml_line}{math_line}\n\n"
        "This is a risk-signal support summary, not a formal decision."
    )

def try_parent_student_outlook_answer(
    db: Session,
    user: User,
    question: str,
    ui_lang: str,
) -> Optional[Dict[str, Any]]:
    if user.role not in (UserRole.PARENT, UserRole.STUDENT) or user.related_id is None:
        return None
    q = (question or "").strip()
    if not (_OUTLOOK_RE.search(q) and _OUTLOOK_CONTEXT.search(q)):
        return None

    sid = int(user.related_id)
    student = db.query(Student).filter(Student.id == sid).first()
    if not student:
        msg = (
            "Kayıtlı öğrenci bulunamadı."
            if (ui_lang or "tr") == "tr"
            else "No linked student record."
        )
        return {
            "results": [],
            "sql_query": "-- Beklenti özeti (risk motoru; LLM yok)",
            "original_query": question,
            "explanation": msg,
            "permissions_applied": True,
            "permission_reason": (
                "Veli/öğrenci — risk özetli beklenti / Parent/student — risk-based outlook"
                if (ui_lang or "tr") == "tr"
                else "Parent/student — risk-based outlook"
            ),
            "results_count": 0,
            "conversation_mode": "sql",
        }

    item = compute_student_risk_item(db, student)
    math_focus = bool(_MATH_HINT.search(q))
    mavg = _math_avg(db, sid) if math_focus else None

    expl = _build_narrative(
        child_name=student.name,
        class_name=student.class_name,
        item=item,
        ui_lang=ui_lang or "tr",
        math_avg=mavg,
        math_focus=math_focus,
    )

    lang_tr = (ui_lang or "tr") == "tr"
    rows: List[Dict[str, Any]] = [
        {
            "metric": "Güncel risk skoru" if lang_tr else "Current risk score",
            "value": round(float(item.risk_score), 2),
        },
        {
            "metric": "Risk seviyesi" if lang_tr else "Risk level",
            "value": item.risk_level or "",
        },
    ]
    if math_focus and mavg is not None:
        rows.append(
            {
                "metric": "Matematik not ortalaması" if lang_tr else "Mathematics grade average",
                "value": round(mavg, 2),
            }
        )

    return {
        "results": rows,
        "sql_query": (
            "-- Veli/öğrenci kısayolu: beklenti metni (GET /risk ile aynı hesap; LLM SQL yok)\n"
            f"-- student_id={sid}"
        ),
        "original_query": question,
        "explanation": expl,
        "permissions_applied": True,
        "permission_reason": (
            "Veli/öğrenci — risk skoruna dayalı beklenti özeti (başka öğrenci verisi yok)"
            if lang_tr
            else "Parent/student — term outlook from risk score only (no peer data)"
        ),
        "results_count": len(rows),
        "conversation_mode": "sql",
    }
