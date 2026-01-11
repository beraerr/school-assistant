"""
Modular LLM service for natural language to SQL conversion
Supports both Ollama and OpenAI
"""
import sys
import os
from typing import Dict, Any, Optional
from langchain_community.llms import Ollama
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
from config.settings import settings
import logging

logger = logging.getLogger(__name__)


class LLMService:
    """Modular LLM service for Turkish NLQ to SQL conversion"""
    
    def __init__(self):
        self.llm = self._initialize_llm()
        self.prompt_template = self._create_prompt_template()
        self.chain = LLMChain(llm=self.llm, prompt=self.prompt_template)
    
    def _initialize_llm(self):
        """Initialize LLM based on provider setting"""
        if settings.LLM_PROVIDER.lower() == "ollama":
            logger.info(f"Initializing Ollama with model: {settings.OLLAMA_MODEL}")
            return Ollama(
                base_url=settings.OLLAMA_BASE_URL,
                model=settings.OLLAMA_MODEL,
                temperature=0.1
            )
        elif settings.LLM_PROVIDER.lower() == "openai":
            if not settings.OPENAI_API_KEY:
                raise ValueError("OPENAI_API_KEY not set in environment")
            logger.info(f"Initializing OpenAI with model: {settings.OPENAI_MODEL}")
            return ChatOpenAI(
                model=settings.OPENAI_MODEL,
                temperature=0.1,
                api_key=settings.OPENAI_API_KEY
            )
        else:
            raise ValueError(f"Unsupported LLM provider: {settings.LLM_PROVIDER}")
    
    def _create_prompt_template(self) -> PromptTemplate:
        """Create prompt template for Turkish NLQ to SQL conversion"""
        template = """Sen bir SQL sorgu uzmanısın. Türkçe doğal dil sorgularını PostgreSQL SQL sorgularına dönüştürüyorsun.

VERİTABANI ŞEMASI:
- students (id, name, class_name, total_absences, parent_id)
- grades (id, student_id, subject, grade, date)
- attendance (id, student_id, date, status)
- teachers (id, name, class_name)
- users (id, username, password_hash, role, related_id, related_class)

ÖNEMLİ KURALLAR:
1. Sadece SQL sorgusu döndür, başka açıklama yapma
2. SQL sorgusu SELECT ile başlamalı
3. Tarih karşılaştırmaları için CURRENT_DATE, CURRENT_DATE - INTERVAL '1 month' gibi PostgreSQL fonksiyonlarını kullan
4. Türkçe ay isimlerini (Ocak, Şubat, vb.) tarih fonksiyonlarına çevir
5. Sadece mevcut tabloları ve kolonları kullan
6. JOIN kullanırken doğru foreign key ilişkilerini kullan

Kullanıcı Sorgusu: {query}

SQL Sorgusu:"""
        
        return PromptTemplate(input_variables=["query"], template=template)
    
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
            # Add user context hints to query if provided
            enhanced_query = natural_language_query
            if user_context:
                role = user_context.get("role")
                if role == "teacher":
                    enhanced_query += f" (Not: Kullanıcı öğretmen ve sadece {user_context.get('related_class')} sınıfına erişebilir)"
                elif role == "parent":
                    enhanced_query += f" (Not: Kullanıcı veli ve sadece kendi çocuğunun (student_id={user_context.get('related_id')}) verilerine erişebilir)"
                elif role == "student":
                    enhanced_query += f" (Not: Kullanıcı öğrenci ve sadece kendi (student_id={user_context.get('related_id')}) verilerine erişebilir)"
            
            result = self.chain.run(query=enhanced_query)
            
            # Clean up the result - extract SQL query
            sql_query = result.strip()
            
            # Remove markdown code blocks if present
            if sql_query.startswith("```sql"):
                sql_query = sql_query.replace("```sql", "").replace("```", "").strip()
            elif sql_query.startswith("```"):
                sql_query = sql_query.replace("```", "").strip()
            
            return {
                "sql": sql_query,
                "original_query": natural_language_query,
                "provider": settings.LLM_PROVIDER,
                "model": settings.OLLAMA_MODEL if settings.LLM_PROVIDER == "ollama" else settings.OPENAI_MODEL
            }
        except Exception as e:
            logger.error(f"Error converting query to SQL: {str(e)}")
            raise Exception(f"SQL dönüştürme hatası: {str(e)}")
    
    def explain_query(self, sql_query: str, natural_language_query: str, results_count: int) -> str:
        """
        Generate explanation for the query execution
        
        Args:
            sql_query: Generated SQL query
            natural_language_query: Original natural language query
            results_count: Number of results returned
        
        Returns:
            Explanation text in Turkish
        """
        explanation_template = PromptTemplate(
            input_variables=["nl_query", "sql_query", "results_count"],
            template="""Aşağıdaki Türkçe sorguyu nasıl işlediğini açıkla:

Kullanıcı Sorgusu: {nl_query}
Oluşturulan SQL: {sql_query}
Sonuç Sayısı: {results_count}

Açıklama (Türkçe, kısa ve anlaşılır):"""
        )
        
        try:
            explanation_chain = LLMChain(llm=self.llm, prompt=explanation_template)
            explanation = explanation_chain.run(
                nl_query=natural_language_query,
                sql_query=sql_query,
                results_count=results_count
            )
            return explanation.strip()
        except Exception as e:
            logger.error(f"Error generating explanation: {str(e)}")
            return f"Sorgu başarıyla işlendi. {results_count} sonuç bulundu."
