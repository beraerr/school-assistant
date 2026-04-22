from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.app.api.risk import compute_student_risk_item
from backend.app.models.grade import Grade
from backend.app.models.student import Student
from backend.app.models.user import User, UserRole

_PARENT_STATS_RE = re.compile(
    r"("
    r"kaç(ı|i)ncı|kacinci|"
    r"sırası|sirasi|"
    r"\bsıra\b|\bsira\b|"
    r"okul(da|da)\s+kaç|okul(da|da)\s+.*sıra|"
    r"okula\s+göre|okula\s+gore|"
    r"kıyas|kiyas|karşılaştır|karsilastir|"
    r"sınıf.{0,30}ortalama|sinif.{0,30}ortalama|"
    r"ortalama.{0,20}sınıf|ortalama.{0,20}sinif|"
    r"okul.{0,25}ortalama|okulun\s+ortalama|"
    r"matematik.{0,25}ortalama|ortalama.{0,20}matematik|"
    r"türkçe.{0,25}ortalama|turkce.{0,25}ortalama|"
    r"fizik.{0,25}ortalama|"
    r"genel\s+ortalama|not\s+ortalaması|not\s+ortalamasi|"
    r"ortalaması\s+ne|ortalamasi\s+ne|"
    r"derece|yüzdelik|yuzdelik|percentile|sıralama|siralama"
    r")",
    re.IGNORECASE | re.UNICODE,
)

_SUBJECT_KEYWORDS: Tuple[Tuple[str, str], ...] = (
    ("matematik", "Matematik"),
    ("türkçe", "Türkçe"),
    ("turkce", "Türkçe"),
    ("fizik", "Fizik"),
    ("kimya", "Kimya"),
    ("tarih", "Tarih"),
    ("biyoloji", "Biyoloji"),
    ("ingilizce", "İngilizce"),
    ("fen", "Fen Bilgisi"),
)

_PRIVACY_NOTE_RE = re.compile(
    r"gizli|gizlilik|paylaş|paylas|privacy|shared?|anonim",
    re.IGNORECASE | re.UNICODE,
)

_RISK_CONTEXT_RE = re.compile(
    r"risk|yüksek\s+risk|yuksek\s+risk|high\s+risk|ml\s+skor|risk\s+skor",
    re.IGNORECASE | re.UNICODE,
)

_WHY_RE = re.compile(
    r"neden|niye|normal\s*mi|why|how\s+come",
    re.IGNORECASE | re.UNICODE,
)

def _fold(s: str) -> str:
    t = (s or "").lower()
    t = t.replace("ı", "i").replace("İ", "i")
    trans = str.maketrans("çğıöşü", "cgiosu")
    return t.translate(trans)

def _detect_subject(question: str) -> Optional[str]:
    f = _fold(question)
    for key, canonical in _SUBJECT_KEYWORDS:
        if key in f:
            return canonical
    return None

def _per_student_means(
    db: Session, *, subject: Optional[str], class_name: Optional[str]
) -> Dict[int, float]:
    q = (
        db.query(Grade.student_id, func.avg(Grade.grade).label("m"))
        .join(Student, Student.id == Grade.student_id)
    )
    if subject:
        q = q.filter(Grade.subject == subject)
    if class_name:
        q = q.filter(Student.class_name == class_name)
    q = q.group_by(Grade.student_id)
    return {int(r.student_id): float(r.m) for r in q.all()}

def _scalar_avg_grade(
    db: Session, *, student_id: Optional[int], class_name: Optional[str], subject: Optional[str]
) -> Optional[float]:
    q = db.query(func.avg(Grade.grade)).join(Student, Student.id == Grade.student_id)
    if student_id is not None:
        q = q.filter(Grade.student_id == student_id)
    if class_name is not None:
        q = q.filter(Student.class_name == class_name)
    if subject is not None:
        q = q.filter(Grade.subject == subject)
    v = q.scalar()
    return float(v) if v is not None else None

def _strict_rank(my_mean: float, means: Dict[int, float], my_id: int) -> Tuple[int, int]:
    peers = [m for sid, m in means.items() if sid != my_id and m > my_mean + 1e-9]
    r = len(peers) + 1
    return r, len(means)

def _should_include_privacy_note(question: str) -> bool:
    return bool(_PRIVACY_NOTE_RE.search((question or "").strip()))

def try_parent_benchmark_answer(
    db: Session,
    user: User,
    question: str,
    ui_lang: str,
) -> Optional[Dict[str, Any]]:
    if user.role != UserRole.PARENT or user.related_id is None:
        return None
    q = (question or "").strip()
    if not _PARENT_STATS_RE.search(q):
        return None

    sid = int(user.related_id)
    child = db.query(Student).filter(Student.id == sid).first()
    if not child:
        empty = (
            "Hesabınıza bağlı öğrenci bulunamadı."
            if (ui_lang or "tr") == "tr"
            else "No student linked to this account."
        )
        return {
            "results": [],
            "sql_query": "-- Veli kısayolu: toplulaştırıcı istatistik (öğrenci kaydı yok)",
            "original_query": question,
            "explanation": empty,
            "permissions_applied": True,
            "permission_reason": (
                "Veli — yalnızca toplulaştırıcı metrikler / Parent — aggregates only"
                if (ui_lang or "tr") == "tr"
                else "Parent — aggregates only, no peer rows"
            ),
            "results_count": 0,
            "conversation_mode": "sql",
        }

    cls = child.class_name
    subject = _detect_subject(q)
    include_privacy_note = _should_include_privacy_note(q)
    risk_item = compute_student_risk_item(db, child)
    asks_risk_context = bool(_RISK_CONTEXT_RE.search(q))

    school_means = _per_student_means(db, subject=None, class_name=None)
    class_means = _per_student_means(db, subject=None, class_name=cls)
    my_school = school_means.get(sid)
    my_class = class_means.get(sid)

    class_pool_avg = _scalar_avg_grade(db, student_id=None, class_name=cls, subject=None)
    school_pool_avg = _scalar_avg_grade(db, student_id=None, class_name=None, subject=None)

    rows: List[Dict[str, Any]] = []
    lang_tr = (ui_lang or "tr") == "tr"

    def add_row(key_tr: str, key_en: str, value: Any) -> None:
        rows.append(
            {
                "metric": key_tr if lang_tr else key_en,
                "value": value,
            }
        )

    r_school = n_school = r_class = n_class = 0
    if my_school is not None:
        r_school, n_school = _strict_rank(my_school, school_means, sid)
        add_row(
            "Genel not ortalaması (çocuğunuz)",
            "Overall grade average (your child)",
            round(my_school, 2),
        )
        add_row(
            "Sınıf genel not ortalaması (tüm öğrenciler, anonim)",
            "Class overall grade average (anonymous aggregate)",
            round(class_pool_avg, 2) if class_pool_avg is not None else None,
        )
        add_row(
            "Okul genel not ortalaması (anonim)",
            "School overall grade average (anonymous)",
            round(school_pool_avg, 2) if school_pool_avg is not None else None,
        )
        my_class_mean = class_means.get(sid, my_school)
        r_class, n_class = _strict_rank(my_class_mean, class_means, sid)
        add_row(
            "Genel nota göre sınıftaki sıra",
            "Class rank by overall average",
            f"{r_class} / {n_class}",
        )
        add_row(
            "Genel nota göre okuldaki sıra",
            "School rank by overall average",
            f"{r_school} / {n_school}",
        )
        if asks_risk_context:
            add_row(
                "ML risk skoru",
                "ML risk score",
                round(float(risk_item.risk_score), 2),
            )
            add_row(
                "ML risk seviyesi",
                "ML risk level",
                risk_item.risk_level,
            )
    else:
        add_row(
            "Genel not ortalaması",
            "Overall grade average",
            None,
        )

    asks_why = bool(_WHY_RE.search(q))
    if asks_risk_context and asks_why and my_school is not None:
        if lang_tr:
            expl = (
                f"Evet, bu durum mümkün. **{child.name}** için okul sırası not ortalamasına göre "
                f"**{r_school}/{n_school}**, ancak ML risk skoru **{round(float(risk_item.risk_score), 2)}/100** "
                f"({risk_item.risk_level}) seviyesinde. Risk modeli yalnızca ortalamaya değil, "
                "devamsızlık ve not trendi gibi ek sinyallere de bakar; bu yüzden sıralama ile risk seviyesi "
                "tam örtüşmeyebilir."
            )
        else:
            expl = (
                f"Yes, this can happen. For **{child.name}**, school rank by average is **{r_school}/{n_school}**, "
                f"but ML risk is **{round(float(risk_item.risk_score), 2)}/100** ({risk_item.risk_level}). "
                "The risk model uses more than average grades, including additional signals such as absences "
                "and grade trend, so rank and risk level may not perfectly align."
            )
        return {
            "results": [],
            "sql_query": "",
            "original_query": question,
            "explanation": expl,
            "permissions_applied": True,
            "permission_reason": (
                "Veli — sıra/risk farkı açıklaması (kural tabanlı kısa yanıt)"
                if lang_tr
                else "Parent — rank vs risk explanation (rule-based short reply)"
            ),
            "results_count": 0,
            "conversation_mode": "chat",
        }

    my_sub: Optional[float] = None
    r_sub_school = n_sub_school = r_sub_class = n_sub_class = 0
    if subject:
        sm = _per_student_means(db, subject=subject, class_name=None)
        cm = _per_student_means(db, subject=subject, class_name=cls)
        my_sub = sm.get(sid)
        c_avg = _scalar_avg_grade(db, student_id=None, class_name=cls, subject=subject)
        o_avg = _scalar_avg_grade(db, student_id=None, class_name=None, subject=subject)
        if my_sub is not None:
            r_sub_school, n_sub_school = _strict_rank(my_sub, sm, sid)
            r_sub_class, n_sub_class = _strict_rank(my_sub, cm, sid)
            add_row(
                f"{subject} ortalaması (çocuğunuz)",
                f"{subject} average (your child)",
                round(my_sub, 2),
            )
            add_row(
                f"Sınıf {subject} ortalaması (anonim)",
                f"Class {subject} average (anonymous)",
                round(c_avg, 2) if c_avg is not None else None,
            )
            add_row(
                f"Okul {subject} ortalaması (anonim)",
                f"School {subject} average (anonymous)",
                round(o_avg, 2) if o_avg is not None else None,
            )
            add_row(
                f"{subject} notuna göre sınıftaki sıra",
                f"Class rank by {subject} average",
                f"{r_sub_class} / {n_sub_class}",
            )
            add_row(
                f"{subject} notuna göre okuldaki sıra",
                f"School rank by {subject} average",
                f"{r_sub_school} / {n_sub_school}",
            )

    expl_parts: List[str] = []
    if lang_tr:
        if include_privacy_note:
            expl_parts.append(
                f"**{child.name}** ({cls}) için yalnızca kendi notları ve "
                "sınıf/okul düzeyinde **anonim toplulaştırıcı** ortalamalar kullanıldı; "
                "başka öğrencilerin adı veya satır verisi paylaşılmadı."
            )
        if my_school is not None:
            expl_parts.append(
                f"Genel not ortalaması **{round(my_school, 2)}**; okulda **{r_school}.** sırada "
                f"({n_school} not kaydı olan öğrenci arasında; daha yüksek ortalamaya sahip olanlar üst sıradadır)."
            )
        if asks_risk_context:
            expl_parts.append(
                f"Not sırası ile risk skoru farklı sinyallerden hesaplanır. "
                f"Bu öğrencide ML risk skoru **{round(float(risk_item.risk_score), 2)}/100** "
                f"({risk_item.risk_level}) seviyesindedir; risk hesabı not ortalamasına ek olarak "
                "devamsızlık ve not trendini de içerir."
            )
        if subject and my_sub is not None:
            expl_parts.append(
                f"{subject} için ortalama **{round(my_sub, 2)}**; bu derste okul sırası "
                f"**{r_sub_school}.** / {n_sub_school}."
            )
    else:
        if include_privacy_note:
            expl_parts.append(
                f"For **{child.name}** ({cls}) we used only their own grades plus **anonymous** "
                "class/school aggregates. No other students' names or row-level data were returned."
            )
        if my_school is not None:
            expl_parts.append(
                f"Overall average **{round(my_school, 2)}**; school rank **{r_school}** of **{n_school}** "
                "students with grade records (strict ranking by higher average)."
            )
        if asks_risk_context:
            expl_parts.append(
                f"Grade rank and risk score are computed from different signals. "
                f"This student has ML risk **{round(float(risk_item.risk_score), 2)}/100** "
                f"({risk_item.risk_level}); risk modeling considers absences and trend in addition to averages."
            )
        if subject and my_sub is not None:
            expl_parts.append(
                f"In {subject}, average **{round(my_sub, 2)}**; school rank **{r_sub_school}** / {n_sub_school}."
            )

    sql_comment = (
        "-- Veli kısayolu: SQL yerine sunucu tarafında toplulaştırıcı hesap "
        "(yalnızca çocuğunuzun id’si + anonim sınıf/okul AVG ve sıra)\n"
        f"-- student_id={sid}, class={cls!r}, subject={subject!r}"
    )

    return {
        "results": rows,
        "sql_query": sql_comment,
        "original_query": question,
        "explanation": "\n\n".join(expl_parts),
        "permissions_applied": True,
        "permission_reason": (
            "Veli — toplulaştırıcı kıyas (başka öğrenci satırı yok) / "
            "Parent — aggregate benchmark (no peer rows)"
            if lang_tr
            else "Parent — aggregate benchmark (no peer rows)"
        ),
        "results_count": len(rows),
        "conversation_mode": "sql",
    }
