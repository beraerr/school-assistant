from __future__ import annotations

import re
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from backend.app.models.user import User

_PROJECT_GUIDE_RE = re.compile(
    r"("
    r"sen\s+kimsin|who\s+are\s+you|"
    r"kullanılma\s+amac|kullanilma\s+amac|purpose|what\s+are\s+you\s+for|"
    r"ai\s+workflow|workflow|iş\s+akışı|is\s+akisi|"
    r"winner\s+model|kazanan\s+model|model\s+nasıl\s+seç|model\s+nasil\s+sec|"
    r"risk\s+skor(unu|unu)?\s+nasıl\s+bul|risk\s+score\s+how|"
    r"staj\s+projesi|turskat|"
    r"(mahmut\s+hoca|coach\s+mahmut)\s+(kim|kimsin|nedir|ne\s+için|ne\s+ise\s+yarar|"
    r"who\s+are\s+you|what\s+are\s+you\s+for|purpose)"
    r")",
    re.IGNORECASE | re.UNICODE,
)

_RISK_INTERPRET_RE = re.compile(
    r"("
    r"risk\s+skor(u|unu|unu)?\s+.*(ne\s+anlama|ne\s+ifade|yorumla|degerlendir)|"
    r"risk\s+skor(u|unu|unu)?\s+.*(öneri|oner|önerirsin|onerirsin)|"
    r"bir\s+öğrencinin\s+risk\s+skoru|bir\s+ogrencinin\s+risk\s+skoru|"
    r"what\s+does\s+.*risk\s+score\s+mean|"
    r"when\s+you\s+evaluate\s+.*risk\s+score\s+what\s+.*recommend"
    r")",
    re.IGNORECASE | re.UNICODE,
)

def try_project_guide_answer(
    db: Session,  # noqa: ARG001 - kept for pipeline signature compatibility
    user: User,   # noqa: ARG001 - kept for pipeline signature compatibility
    question: str,
    ui_lang: str,
) -> Optional[Dict[str, Any]]:
    q = (question or "").strip()
    if not (_PROJECT_GUIDE_RE.search(q) or _RISK_INTERPRET_RE.search(q)):
        return None

    tr = (ui_lang or "tr") == "tr"
    if _RISK_INTERPRET_RE.search(q):
        if tr:
            explanation = (
                "Bir öğrenci için risk skoru benim için **erken uyarı sinyali** demektir.\n\n"
                "- **Ne anlatır:** Devamsızlık, not seviyesi ve not trendi birlikte kötüleşiyorsa "
                "öğrencinin dönem sonuna kadar akademik zorlanma ihtimali artar.\n"
                "- **Neden önemli:** Bu projede yaptığımız analizlerde benzer trenddeki öğrenciler "
                "destek verilmediğinde düşük başarı bandında kalma eğilimi gösteriyor.\n"
                "- **Ne öneririm:** (1) devamsızlık kontrol planı, (2) ders bazlı takviye "
                "(özellikle düşen ders), (3) haftalık veli-öğretmen kısa takip döngüsü, "
                "(4) 2-4 haftada bir risk skorunu yeniden ölçme.\n"
                "- **Karar mantığı:** Skor bir etiket değil; erken müdahale önceliğini belirleyen "
                "dinamik bir yol haritasıdır."
            )
        else:
            explanation = (
                "For me, a student's risk score is an **early-warning signal**.\n\n"
                "- **What it means:** if attendance, grade level, and grade trend deteriorate together, "
                "the chance of end-of-term academic struggle increases.\n"
                "- **Why it matters:** in our project analyses, students with similar trends tend to stay "
                "in lower performance bands when no support intervention is applied.\n"
                "- **What I recommend:** (1) attendance control plan, (2) subject-focused support "
                "(especially declining subjects), (3) weekly short parent-teacher follow-up loop, "
                "(4) re-check risk score every 2-4 weeks.\n"
                "- **Decision logic:** the score is not a label; it is a dynamic prioritization map "
                "for early intervention."
            )
        reason = "Mahmut Hoca risk-yorum katmanı (LLM/SQL çalıştırılmadı)." if tr else "Coach Mahmut risk-interpretation layer (no SQL/LLM run)."
        return {
            "results": [],
            "sql_query": "-- Mahmut Hoca risk interpretation answer (no SQL executed)",
            "original_query": question,
            "explanation": explanation,
            "permissions_applied": False,
            "permission_reason": reason,
            "results_count": 0,
            "conversation_mode": "chat",
        }

    if tr:
        explanation = (
            "**Mahmut Hoca** (EN karşılığı: **Coach Mahmut**) Turskat için geliştirilen "
            "staj projesinin okul asistanıdır.\n\n"
            "- **Amaç:** Ailelerin çocuklarının okul durumunu anlamasına; öğretmen/müdürlerin de "
            "sınıf/okul genelini izlemesine yardımcı olmak.\n"
            "- **AI workflow:** (1) niyet analizi ve soru sınıflandırma, "
            "(2) doğal dil → SQL üretimi ve yetki (RBAC) filtreleri, "
            "(3) risk analizi katmanı, "
            "(4) sonuçların kısa ve anlaşılır açıklaması.\n"
            "- **Risk skoru:** Üretimde tek kaynak `student_risk_scores` tablosundaki ML skorudur.\n"
            "- **Winner model seçimi:** Data science pipeline (UCI) model karşılaştırmasıyla "
            "F1/AUC metriklerine göre belirlenir (`winner_meta.json`).\n"
            "- **Risk değerlendirme önerisi:** Bir öğrenci için risk yüksekse; devamsızlık azaltma, "
            "ders bazlı takviye ve düzenli veli-öğretmen takibi önerilir. Orta riskte yakın izleme, "
            "düşük riskte mevcut planın korunması önerilir."
        )
        reason = "Mahmut Hoca proje rehberi (LLM/SQL çalıştırılmadı)."
    else:
        explanation = (
            "**Coach Mahmut** (TR name: **Mahmut Hoca**) is the school assistant built as a "
            "Turskat internship project.\n\n"
            "- **Purpose:** Help families understand their child's school status, and help "
            "teachers/principals monitor class/school-level trends.\n"
            "- **AI workflow:** (1) intent understanding and question routing, "
            "(2) natural language → SQL with RBAC filters, "
            "(3) risk analysis layer, "
            "(4) concise explanation generation.\n"
            "- **Risk score:** Production uses only the ML score in `student_risk_scores`.\n"
            "- **Winner model selection:** chosen in the UCI data-science pipeline using "
            "metrics like F1/AUC (`winner_meta.json`).\n"
            "- **Recommendation logic:** for high risk, focus on attendance reduction, "
            "subject support, and structured parent-teacher follow-up; medium risk needs closer monitoring; "
            "low risk should maintain the current plan."
        )
        reason = "Coach Mahmut project guide (no SQL/LLM run)."

    return {
        "results": [],
        "sql_query": "-- Mahmut Hoca project guide answer (no SQL executed)",
        "original_query": question,
        "explanation": explanation,
        "permissions_applied": False,
        "permission_reason": reason,
        "results_count": 0,
        "conversation_mode": "chat",
    }
