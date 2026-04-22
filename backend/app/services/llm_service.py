import json
import os
import re
from typing import Any, Dict, List, Optional

import requests

from config.settings import settings
import logging

logger = logging.getLogger(__name__)

_EMOJI_RE = re.compile(
    "["
    "\U0001F600-\U0001F64F"
    "\U0001F300-\U0001F5FF"
    "\U0001F680-\U0001F6FF"
    "\U0001F1E0-\U0001F1FF"
    "\U00002700-\U000027BF"
    "\U0001F900-\U0001F9FF"
    "\U00002600-\U000026FF"
    "]+",
    flags=re.UNICODE,
)

def _strip_emojis(text: str) -> str:
    if not text:
        return text
    return _EMOJI_RE.sub("", text).strip()

_PROSE_AFTER_SQL = re.compile(
    r"^(Wait|Here|Note:|Alternatively|Let me|I think|We can| cleaner|Better:|Second|This is|The |I |We )\b",
    re.I,
)

def extract_first_select_sql(raw: str) -> str:
    """
    Keep a single SELECT statement: strip leading junk, first `;` wins, then drop trailing prose lines.
    """
    s = (raw or "").strip()
    if not s:
        return s
    m0 = re.search(r"\bSELECT\b", s, re.IGNORECASE)
    if m0:
        s = s[m0.start() :].strip()
    if ";" in s:
        s = s.split(";", 1)[0].strip()
    lines = s.splitlines()
    kept: List[str] = []
    for line in lines:
        st = line.strip()
        if st and _PROSE_AFTER_SQL.match(st):
            break
        kept.append(line)
    return "\n".join(kept).strip()

class LLMService:
    """Modular LLM service for Turkish NLQ to SQL conversion"""
    
    def __init__(self):
        self.provider = settings.LLM_PROVIDER.lower()
        self.llm_local_config = self._load_local_llm_config()
        if self.provider == "ollama":
            self.model = settings.OLLAMA_MODEL
        elif self.provider == "openai":
            self.model = settings.OPENAI_MODEL
        elif self.provider == "anthropic":
            self.model = self._anthropic_model_id()
        else:
            self.model = "unknown"
        self.prompt_template = self._create_prompt_template()

    def _anthropic_model_id(self) -> str:
        """Prefer config/llm.local.json so shell ANTHROPIC_MODEL cannot pin a retired id."""
        raw = self.llm_local_config.get("anthropic_model")
        if isinstance(raw, str) and raw.strip():
            return raw.strip()
        return (settings.ANTHROPIC_MODEL or "").strip() or "claude-sonnet-4-6"

    @staticmethod
    def _sql_dialect() -> str:
        """Proje yalnızca PostgreSQL kullanır. / Project uses PostgreSQL only."""
        return "postgresql"

    def _load_local_llm_config(self) -> Dict[str, Any]:
        """
        Load optional local credentials file, ignored by git.
        Environment variables still take precedence.
        """
        config_path = settings.LLM_CONFIG_PATH
        if not config_path:
            return {}
        if not os.path.exists(config_path):
            return {}
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as exc:
            logger.warning(f"Could not read local LLM config: {exc}")
            return {}
    
    def _call_ollama(self, prompt: str) -> str:
        """Call Ollama generate API and return plain text output."""
        response = requests.post(
            f"{settings.OLLAMA_BASE_URL}/api/generate",
            json={
                "model": settings.OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False
            },
            timeout=60
        )
        response.raise_for_status()
        return response.json().get("response", "").strip()

    def _call_openai(self, prompt: str) -> str:
        """Call OpenAI chat completions API and return plain text output."""
        openai_api_key = settings.OPENAI_API_KEY or self.llm_local_config.get("openai_api_key")
        if not openai_api_key:
            raise ValueError("OPENAI_API_KEY not set in environment")
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {openai_api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": settings.OPENAI_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.1
            },
            timeout=60
        )
        response.raise_for_status()
        choices = response.json().get("choices", [])
        if not choices:
            return ""
        return choices[0]["message"]["content"].strip()

    def _call_anthropic(self, prompt: str, max_tokens: int = 800) -> str:
        """Call Anthropic Messages API and return plain text output."""
        anthropic_api_key = settings.ANTHROPIC_API_KEY or self.llm_local_config.get("anthropic_api_key")
        if not anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY not set in environment or local config")

        model_id = self._anthropic_model_id()
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": anthropic_api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": model_id,
                "max_tokens": max_tokens,
                "temperature": 0.1,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=60,
        )
        if response.status_code == 404:
            raise ValueError(
                f"Anthropic HTTP 404: model '{model_id}' is unknown or retired. "
                "Set `anthropic_model` in config/llm.local.json (overrides env) or ANTHROPIC_MODEL in .env "
                "to a current id (e.g. claude-sonnet-4-6). If your shell exports ANTHROPIC_MODEL, run `unset ANTHROPIC_MODEL`."
            )
        response.raise_for_status()
        content = response.json().get("content", [])
        if not content:
            return ""
        return content[0].get("text", "").strip()

    def _invoke(self, prompt: str, max_tokens: Optional[int] = None) -> str:
        """Route prompt to configured provider."""
        if self.provider == "ollama":
            return self._call_ollama(prompt)
        if self.provider == "openai":
            return self._call_openai(prompt)
        if self.provider == "anthropic":
            return self._call_anthropic(prompt, max_tokens=max_tokens or 800)
        raise ValueError(f"Unsupported LLM provider: {settings.LLM_PROVIDER}")

    @staticmethod
    def _extract_json_object(text: str) -> Optional[dict]:
        """Parse first JSON object from model output (handles ```json fences)."""
        s = text.strip()
        if s.startswith("```"):
            s = re.sub(r"^```(?:json)?\s*", "", s, flags=re.IGNORECASE)
            s = re.sub(r"\s*```$", "", s)
        try:
            return json.loads(s)
        except json.JSONDecodeError:
            m = re.search(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", s, re.DOTALL)
            if m:
                try:
                    return json.loads(m.group(0))
                except json.JSONDecodeError:
                    return None
            return None

    def interpret_intent(
        self,
        user_message: str,
        user_context: Optional[Dict[str, Any]] = None,
        ui_lang: str = "tr",
    ) -> Dict[str, Any]:
        """
        Decide if the message needs DB-backed NL→SQL or is casual chat / off-topic.
        Returns {"mode": "data"} or {"mode": "chat", "reply": "..."}.
        """
        enhanced = user_message
        if user_context:
            role = user_context.get("role")
            if role == "teacher":
                enhanced += f" (Not: kullanıcı öğretmen, sadece {user_context.get('related_class')} sınıfı)"
            elif role == "parent":
                enhanced += (
                    f" (Not: veli; çocuk students.id={user_context.get('related_id')}; "
                    "users/role sorgulama.)"
                )
            elif role == "student":
                enhanced += f" (Not: kullanıcı öğrenci, student_id={user_context.get('related_id')})"

        if ui_lang == "en":
            prompt = f"""You are the front-line assistant of a school information system (institutional tone: concise, neutral, professional — not chatty, not therapeutic, no emojis).

Classify the message.

If the user asks for data from the school database (students, grades, attendance, classes, teachers, etc.), return ONLY this JSON (no other text):
{{"mode":"data"}}

If the message is administrative small talk only (greeting, thanks, brief procedural question) and NOT a database question, return ONLY:
{{"mode":"chat","reply":"A brief reply in English only (max 3 short sentences). No moral lectures, no familiarity, no emojis."}}

Rules: Single JSON object; no markdown fences.

Message:
{enhanced}
"""
        else:
            prompt = f"""Sen bir okul bilgi sisteminin ön yüz asistanısın. Üslup: kurumsal, özlü, tarafsız ve resmi; samimi sohbet, telkin veya duygusal destek dili kullanma; emoji kullanma.

Mesajı sınıflandır.

Eğer mesaj okul veritabanından öğrenci, not, devamsızlık, sınıf, öğretmen vb. veri istiyorsa YALNIZCA şu JSON'u döndür (başka metin yok):
{{"mode":"data"}}

Eğer mesaj yalnızca idari nezaket / kısa prosedür (selam, teşekkür, yönlendirme sorusu) ise ve veritabanı sorusu DEĞİLse YALNIZCA şu JSON'u döndür:
{{"mode":"chat","reply":"En fazla 3 kısa cümle; yalnızca Türkçe, resmi ve net. Telkin ve emoji yok."}}

Kurallar: Tek JSON nesnesi; markdown yok.

Mesaj:
{enhanced}
"""
        raw = self._invoke(prompt, max_tokens=400)
        parsed = self._extract_json_object(raw) or {}
        mode = parsed.get("mode")
        if mode == "chat" and isinstance(parsed.get("reply"), str) and parsed["reply"].strip():
            return {"mode": "chat", "reply": _strip_emojis(parsed["reply"].strip())}
        return {"mode": "data"}
    
    def _create_prompt_template(self) -> str:
        """PostgreSQL için NLQ → SQL prompt şablonu oluşturur."""
        date_rules = (
            "3. For dates use PostgreSQL: CURRENT_DATE, CURRENT_DATE - INTERVAL '1 month', etc.\n"
            "   Example — grades that changed from last month to now:\n"
            "     SELECT s.name, g_now.subject,\n"
            "            ROUND(AVG(g_now.grade)::numeric, 1) AS avg_now,\n"
            "            ROUND(AVG(g_prev.grade)::numeric, 1) AS avg_prev,\n"
            "            ROUND((AVG(g_now.grade) - AVG(g_prev.grade))::numeric, 1) AS delta\n"
            "     FROM students s\n"
            "     JOIN grades g_now  ON g_now.student_id  = s.id AND g_now.date  >= CURRENT_DATE - INTERVAL '30 days'\n"
            "     JOIN grades g_prev ON g_prev.student_id = s.id AND g_prev.date >= CURRENT_DATE - INTERVAL '60 days'\n"
            "                       AND g_prev.date < CURRENT_DATE - INTERVAL '30 days'\n"
            "     GROUP BY s.name, g_now.subject;\n"
            "3b. PostgreSQL: AVG() is double precision — use ROUND((AVG(col))::numeric, 2), never ROUND(AVG(col), 2).\n"
        )

        return f"""You are an SQL expert for an institutional school database. Output is technical only: no small talk, no emojis.

Convert Turkish natural language questions into PostgreSQL SQL.

DATABASE SCHEMA:
- students (id, name, class_name, total_absences, parent_id)
- grades (id, student_id, subject, grade, date)
  * grade values are 0–100 (passing = 50)
  * subject values (Turkish name / English name):
      Matematik / Mathematics
      Türkçe / Turkish
      Fen Bilgisi / Science
      İngilizce / English
      Kimya / Chemistry
      Coğrafya / Geography
      Tarih / History
      Beden Eğitimi / Physical Education
- attendance (id, student_id, date, status)
- teachers (id, name, class_name)
- users (id, username, password_hash, role, related_id, related_class)
- student_risk_scores (id, student_id, ml_risk_score, ml_risk_level, features_json, computed_at)

RULES:
1. Return only ONE single SELECT statement — no English sentences, no "Wait", no alternative drafts, no markdown
2. The query must start with SELECT
{date_rules}4. Map Turkish month names (Ocak, Şubat, …) to proper date literals or functions
5. Use only existing tables and columns
6. Use correct foreign keys when JOINing
7. Do not use emojis in any output
8. End the statement with a semicolon OR end immediately after the final SQL token — never append text after the semicolon
9. If the question is about student performance, achievement (başarı), risk level, or future outlook, include ML columns via
   LEFT JOIN student_risk_scores srs ON srs.student_id = <students-alias>.id
   (use the same table alias you used for students in FROM) and select srs.ml_risk_score, srs.ml_risk_level, srs.computed_at
10. "Geçen aya göre" / "last month comparison" queries: use the two-join pattern from Rule 3 to compare
    grades within the last 30 days against the previous 30-day window.

User query: {{query}}

SQL:"""
    
    def convert_to_sql(self, natural_language_query: str, user_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Convert Turkish natural language query to SQL
        
        Args:
            natural_language_query: Turkish natural language query
            user_context: Optional user context for role-based filtering hints
        
        Returns:
            Dictionary with SQL query and metadata
        """
        try:
            enhanced_query = natural_language_query
            if user_context:
                role = user_context.get("role")
                if role == "teacher":
                    enhanced_query += f" (Not: Kullanıcı öğretmen ve sadece {user_context.get('related_class')} sınıfına erişebilir)"
                elif role == "parent":
                    enhanced_query += (
                        f" (Not: Kullanıcı veli; çocuk kaydı students.id = {user_context.get('related_id')} "
                        "ile tanımlıdır. SQL'de users tablosuna veya role = 'parent' gibi ifadelere başvurma; "
                        "students üzerinden bu id ile filtrele.)"
                    )
                elif role == "student":
                    enhanced_query += f" (Not: Kullanıcı öğrenci ve sadece kendi (student_id={user_context.get('related_id')}) verilerine erişebilir)"
            
            prompt = self.prompt_template.format(query=enhanced_query)
            result = self._invoke(prompt)
            
            sql_query = result.strip()
            
            if sql_query.startswith("```sql"):
                sql_query = sql_query.replace("```sql", "").replace("```", "").strip()
            elif sql_query.startswith("```"):
                sql_query = sql_query.replace("```", "").strip()

            sql_query = extract_first_select_sql(sql_query)
            
            return {
                "sql": sql_query,
                "original_query": natural_language_query,
                "provider": self.provider,
                "model": self.model
            }
        except Exception as e:
            logger.error(f"Error converting query to SQL: {str(e)}")
            raise Exception(f"SQL dönüştürme hatası: {str(e)}")
    
    @staticmethod
    def _results_preview_json(rows: List[Dict[str, Any]], max_rows: int = 30, max_chars: int = 16000) -> str:
        """Compact JSON preview of query rows for the LLM (bounded size)."""
        if not rows:
            return "[]"
        chunk = rows[:max_rows]
        s = json.dumps(chunk, ensure_ascii=False, default=str)
        if len(s) > max_chars:
            return s[:max_chars] + "\n…(truncated)"
        return s

    def explain_query(
        self,
        sql_query: str,
        natural_language_query: str,
        results_count: int,
        result_rows: List[Dict[str, Any]],
        ui_lang: str = "tr",
    ) -> str:
        """
        Explain results in the user's UI language. The model sees a JSON preview of returned rows.
        """
        preview = self._results_preview_json(result_rows)
        if ui_lang == "en":
            explanation_template = """You summarize authorized query results for staff in a school information system.

Tone: institutional, neutral, concise — professional memo style. Not conversational, not therapeutic, no moral lectures, no emojis, no exclamation-heavy enthusiasm.

User question: {nl_query}
Executed SQL: {sql_query}
Row count returned: {results_count}

Rows returned (JSON array; may be truncated — base your answer ONLY on this data; do not invent rows):
{preview}

Write in English only. Keep the answer to 3–4 sentences maximum for simple queries; use a short bullet list only if the data has multiple distinct items to compare. Answer the question directly with figures and names exactly as present in the JSON. If the result set is empty, state that plainly in one sentence. Do not repeat the full SQL. Do not begin with filler interjections (e.g. "Hmm", "Oh")."""
        else:
            explanation_template = """Yetkili kullanıcıya dönen sorgu sonuçlarını kurum içi bilgi notu üslubunda özetliyorsun.

Üslup: resmi, tarafsız, özlü; samimi sohbet, telkin, duygusal destek veya uzun ahlakî yönlendirme yok; emoji yok; abartılı neşe yok.

Kullanıcının sorusu: {nl_query}
Çalıştırılan SQL: {sql_query}
Dönen satır sayısı: {results_count}

Dönen satırlar (JSON dizi; kesilmiş olabilir — yanıtını YALNIZCA bu verilere dayandır; uydurma):
{preview}

Yalnızca Türkçe yaz. Basit sorularda 3–4 cümleyi geçme; karşılaştırmalı veya çok kalemli veride kısa madde listesi kullanabilirsin. Net soruya doğrudan ve sayılarla cevap ver; JSON'da geçen ad ve değerleri aynen kullanabilirsin. Sonuç boşsa bunu tek cümleyle belirt. Tam SQL'i tekrarlama. Cümleye "Hımm", "Hmm" vb. dolgu ile başlama."""

        try:
            prompt = explanation_template.format(
                nl_query=natural_language_query,
                sql_query=sql_query,
                results_count=results_count,
                preview=preview,
            )
            explanation = self._invoke(prompt, max_tokens=1600)
            return _strip_emojis(explanation.strip())
        except Exception as e:
            logger.error(f"Error generating explanation: {str(e)}")
            if ui_lang == "en":
                return f"Query finished; {results_count} row(s) returned."
            return f"Sorgu tamamlandı; {results_count} satır döndü."
