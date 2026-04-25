from __future__ import annotations

import re
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from backend.app.models.user import User

_RISK_SUCCESS_RE = re.compile(
    r"başarı\s+(durum|seviye|analizi|özet|skoru)|basari\s+(durum|seviye|analiz|ozet)|"
    r"başarım(\s+nasıl|\s+ne\s+durumda)?|başarı\s+durumum|"
    r"akademik\s+durum|genel\s+(akademik\s+)?durum|"
    r"risk\s+(skoru|skor|faktör|durum|analizi|raporu|degeri|degerleri)|"
    r"risk\s+values?|riskli|risk\s+altinda|risk\s+altında|"
    r"(kimler|hangi\s+ogrenciler|hangi\s+öğrenciler)\s+risk|"
    r"kimler\s+neden\s+riskli|"
    r"bu\s+risk\s+ne\s+anlama\s+geliyor|risk\s+ne\s+anlama\s+geliyor|"
    r"ne\s+kadar\s+başarılı\s+(?!öğrenci)|gelecek\s+beklentisi|"
    r"öğrenci(nin|min)?\s+(?:genel\s+)?(?:başarı|basari|risk|performans)\s+durumu|"
    r"(success|performance)\s+(status|overview)|risk\s+overview|how\s+.*\s+doing\s+academically",
    re.IGNORECASE | re.UNICODE,
)

_RISK_MEANING_RE = re.compile(
    r"risk\s+ne\s+anlama\s+geliyor|bu\s+risk\s+ne\s+anlama\s+geliyor|"
    r"what\s+does\s+(this\s+)?risk\s+mean|meaning\s+of\s+risk",
    re.IGNORECASE | re.UNICODE,
)


def _wants_risk_meaning(question: str) -> bool:
    return bool(_RISK_MEANING_RE.search((question or "").strip()))


def _meaning_text(ui_lang: str) -> str:
    if (ui_lang or "tr") == "en":
        return (
            "Risk score is a 0-100 early-warning signal. "
            "Lower means relatively safer patterns; higher means stronger intervention need. "
            "In this app, scores are interpreted as Low (0-35), Medium (35-65), High (65-100), "
            "using attendance, grade trend, and performance signals together."
        )
    return (
        "Risk skoru 0-100 arası erken uyarı sinyalidir. "
        "Düşük skor görece güvenli örüntüyü, yüksek skor daha güçlü müdahale ihtiyacını gösterir. "
        "Bu uygulamada skorlar Düşük (0-35), Orta (35-65), Yüksek (65-100) olarak yorumlanır; "
        "hesaplamada devamsızlık, not trendi ve performans sinyalleri birlikte değerlendirilir."
    )


def try_risk_success_answer(
    db: Session,
    user: User,
    question: str,
    ui_lang: str,
) -> Optional[Dict[str, Any]]:
    _ = db, user
    if not _RISK_SUCCESS_RE.search((question or "").strip()):
        return None
    if not _wants_risk_meaning(question):
        return None
    return {
        "results": [],
        "sql_query": "",
        "original_query": question,
        "explanation": _meaning_text(ui_lang or "tr"),
        "permissions_applied": True,
        "permission_reason": (
            "Risk açıklaması — kural tabanlı"
            if (ui_lang or "tr") == "tr"
            else "Risk meaning — rule based"
        ),
        "results_count": 0,
        "conversation_mode": "chat",
    }
