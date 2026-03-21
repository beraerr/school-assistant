# Niyet Analizi ve SQL Üretim Süreci - Teknik Detaylar

## 1. GENEL BAKIŞ

Projede niyet analizi (intent analysis) ve SQL komut üretimi, **Large Language Model (LLM)** teknolojisi kullanılarak yapılmaktadır. Sistem, kullanıcının Türkçe doğal dil sorgusunu alır, niyetini anlar ve PostgreSQL uyumlu SQL sorgusuna dönüştürür.

## 2. MİMARİ YAPISI

### 2.1 Bileşenler

```
Kullanıcı Sorgusu (Türkçe)
    ↓
LLMService (LangChain + LLM)
    ↓
Prompt Template (Niyet Analizi + SQL Üretimi)
    ↓
LLM (Ollama DeepSeek veya OpenAI)
    ↓
SQL Sorgusu (PostgreSQL)
```

### 2.2 Kullanılan Teknolojiler

- **LangChain Framework**: LLM entegrasyonu ve prompt yönetimi
- **Ollama (DeepSeek R1:7B)**: Yerel, ücretsiz LLM (varsayılan)
- **OpenAI GPT-4**: Alternatif bulut LLM (opsiyonel)
- **Prompt Engineering**: Türkçe dil desteği için optimize edilmiş prompt şablonları

## 3. NİYET ANALİZİ SÜRECİ

### 3.1 Niyet Analizi Nasıl Yapılıyor?

Niyet analizi, **LLM'in doğal dil işleme yetenekleri** kullanılarak yapılmaktadır. Sistem, geleneksel NLP pipeline (tokenization, POS tagging, named entity recognition) kullanmaz. Bunun yerine, LLM'in eğitim sırasında öğrendiği semantik anlama yeteneğini kullanır.

**Çalışma Prensibi:**

1. **Kullanıcı sorgusu alınır**: "Bu ay devamsızlığı 5 günü geçen öğrencileri göster"

2. **Prompt template'e gönderilir**: LLM'e veritabanı şeması ve kurallar ile birlikte gönderilir

3. **LLM niyeti anlar**: LLM, sorguyu analiz eder ve şunları çıkarır:
   - **Amaç**: Öğrenci listesi göstermek
   - **Filtre**: Devamsızlık > 5 gün
   - **Zaman**: Bu ay (CURRENT_DATE ile ilgili)
   - **Tablo**: students tablosu
   - **İlişkiler**: Gerekirse JOIN işlemleri

4. **SQL'e dönüştürülür**: Anlaşılan niyet, SQL sorgusuna çevrilir

### 3.2 Prompt Template Yapısı

Sistem, LLM'e gönderilen prompt şu yapıdadır:

```
Sen bir SQL sorgu uzmanısın. Türkçe doğal dil sorgularını PostgreSQL SQL sorgularına dönüştürüyorsun.

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

SQL Sorgusu:
```

### 3.3 Niyet Analizi Örnekleri

**Örnek 1: Basit Filtreleme**
```
Kullanıcı: "Bu ay devamsızlığı 5 günü geçen öğrencileri göster"

LLM Analizi:
- Niyet: Liste gösterme
- Filtre: total_absences > 5
- Zaman: CURRENT_DATE ile bu ay kontrolü
- Tablo: students

Üretilen SQL:
SELECT * FROM students 
WHERE total_absences > 5 
AND EXTRACT(MONTH FROM CURRENT_DATE) = EXTRACT(MONTH FROM CURRENT_DATE)
```

**Örnek 2: İlişkisel Sorgu**
```
Kullanıcı: "Çocuğumun matematik notları geçen aya göre nasıl değişti?"

LLM Analizi:
- Niyet: Karşılaştırma analizi
- Tablolar: students, grades (JOIN gerekli)
- Filtre: subject = 'Matematik'
- Zaman: CURRENT_DATE - INTERVAL '1 month' ile karşılaştırma
- Gruplama: Tarih bazlı

Üretilen SQL:
SELECT g.date, g.grade 
FROM grades g
JOIN students s ON g.student_id = s.id
WHERE s.id = {student_id}
AND g.subject = 'Matematik'
AND g.date >= CURRENT_DATE - INTERVAL '1 month'
ORDER BY g.date
```

**Örnek 3: Agregasyon**
```
Kullanıcı: "Devamsızlık oranı en yüksek sınıflar hangileri?"

LLM Analizi:
- Niyet: Gruplama ve sıralama
- Tablo: students
- Agregasyon: AVG(total_absences) GROUP BY class_name
- Sıralama: DESC (en yüksekten düşüğe)

Üretilen SQL:
SELECT class_name, AVG(total_absences) as avg_absences
FROM students
GROUP BY class_name
ORDER BY avg_absences DESC
```

## 4. SQL ÜRETİM SÜRECİ

### 4.1 Adım Adım SQL Üretimi

**Adım 1: Kullanıcı Bağlamı Ekleme**

Kullanıcının rolüne göre sorguya ipuçları eklenir:

```python
# backend/app/services/llm_service.py - convert_to_sql() metodu

enhanced_query = natural_language_query
if user_context:
    role = user_context.get("role")
    if role == "teacher":
        enhanced_query += f" (Not: Kullanıcı öğretmen ve sadece {user_context.get('related_class')} sınıfına erişebilir)"
    elif role == "parent":
        enhanced_query += f" (Not: Kullanıcı veli ve sadece kendi çocuğunun (student_id={user_context.get('related_id')}) verilerine erişebilir)"
```

**Örnek:**
- Orijinal: "Devamsızlığı yüksek öğrencileri göster"
- Enhanced: "Devamsızlığı yüksek öğrencileri göster (Not: Kullanıcı öğretmen ve sadece 9-A sınıfına erişebilir)"

**Adım 2: LLM'e Gönderme**

LangChain'in LLMChain'i kullanılarak prompt LLM'e gönderilir:

```python
result = self.chain.run(query=enhanced_query)
```

**Adım 3: Sonuç Temizleme**

LLM'in döndürdüğü sonuç temizlenir:

```python
sql_query = result.strip()

# Markdown code block'ları kaldır
if sql_query.startswith("```sql"):
    sql_query = sql_query.replace("```sql", "").replace("```", "").strip()
elif sql_query.startswith("```"):
    sql_query = sql_query.replace("```", "").strip()
```

**Adım 4: SQL Döndürme**

Temizlenmiş SQL sorgusu döndürülür:

```python
return {
    "sql": sql_query,
    "original_query": natural_language_query,
    "provider": settings.LLM_PROVIDER,
    "model": settings.OLLAMA_MODEL
}
```

### 4.2 LLM Konfigürasyonu

**Temperature Ayarı:**
```python
temperature=0.1  # Düşük temperature = daha deterministik, tutarlı sonuçlar
```

**Neden 0.1?**
- SQL üretimi için deterministik sonuçlar istenir
- Yüksek temperature (0.7-1.0) yaratıcılık için kullanılır, ama SQL için tutarlılık önemli
- 0.1 ile LLM, aynı sorguya benzer SQL üretir

**Model Seçimi:**
- **Ollama DeepSeek R1:7B**: Yerel, ücretsiz, veri gizliliği yüksek
- **OpenAI GPT-4**: Daha yüksek doğruluk, ama maliyetli ve veri gizliliği dikkat gerektirir

### 4.3 Prompt Engineering Teknikleri

**1. Few-Shot Learning (Örnek Öğrenme)**

Prompt template'e örnekler eklenebilir:

```
Örnek 1:
Kullanıcı: "Matematik notu 80'den yüksek öğrenciler"
SQL: SELECT * FROM students s JOIN grades g ON s.id = g.student_id WHERE g.subject = 'Matematik' AND g.grade > 80

Örnek 2:
Kullanıcı: "Bu ay devamsızlığı 5 günü geçenler"
SQL: SELECT * FROM students WHERE total_absences > 5 AND EXTRACT(MONTH FROM CURRENT_DATE) = EXTRACT(MONTH FROM CURRENT_DATE)
```

**2. Chain-of-Thought (Düşünce Zinciri)**

LLM'e adım adım düşünmesi söylenebilir:

```
1. Önce kullanıcının ne istediğini anla
2. Hangi tabloları kullanacağını belirle
3. Hangi filtreleri uygulayacağını belirle
4. SQL sorgusunu oluştur
```

**3. Schema Context (Şema Bağlamı)**

Veritabanı şeması detaylı şekilde verilir:
- Tablo isimleri
- Kolon isimleri
- Foreign key ilişkileri
- Veri tipleri (opsiyonel)

## 5. KOD AKIŞI

### 5.1 Tam İşlem Akışı

```python
# 1. Kullanıcı sorgusu gelir
query = "Bu ay devamsızlığı 5 günü geçen öğrencileri göster"

# 2. LLMService.convert_to_sql() çağrılır
llm_service = LLMService()
user_context = {
    "role": "teacher",
    "related_class": "9-A"
}

# 3. Sorgu zenginleştirilir
enhanced_query = query + " (Not: Kullanıcı öğretmen ve sadece 9-A sınıfına erişebilir)"

# 4. Prompt template'e yerleştirilir
prompt = f"""
Sen bir SQL sorgu uzmanısın...
VERİTABANI ŞEMASI:
- students (id, name, class_name, total_absences, parent_id)
...

Kullanıcı Sorgusu: {enhanced_query}

SQL Sorgusu:
"""

# 5. LLM'e gönderilir
result = llm.chain.run(query=enhanced_query)

# 6. Sonuç temizlenir
sql = result.strip().replace("```sql", "").replace("```", "").strip()

# 7. SQL döndürülür
return {"sql": sql, ...}
```

### 5.2 Hata Yönetimi

```python
try:
    result = self.chain.run(query=enhanced_query)
    sql_query = result.strip()
    # ... temizleme işlemleri
except Exception as e:
    logger.error(f"Error converting query to SQL: {str(e)}")
    raise Exception(f"SQL dönüştürme hatası: {str(e)}")
```

## 6. NİYET ANALİZİNİN SINIRLARI VE ÇÖZÜMLER

### 6.1 Mevcut Sınırlamalar

**1. Belirsiz Sorgular:**
- "Öğrencileri göster" → Hangi öğrenciler? Tümü mü, belirli bir sınıf mı?
- **Çözüm**: Kullanıcı bağlamı (rol) ile otomatik filtreleme

**2. Çok Karmaşık Sorgular:**
- "Geçen yılki notların ortalaması ile bu yılki notların ortalamasını karşılaştır"
- **Çözüm**: Prompt engineering ile daha iyi açıklamalar

**3. Türkçe Dil Karmaşıklığı:**
- "geçen ay", "bir önceki ay", "önceki ay" → Hepsi aynı anlama gelir
- **Çözüm**: LLM'in semantik anlama yeteneği (eğitim sırasında öğrenilmiş)

### 6.2 İyileştirme Önerileri

**1. Validation Katmanı:**
```python
def validate_sql(sql_query: str) -> bool:
    # SQL syntax kontrolü
    # Tablo/kolon isim kontrolü
    # Sadece SELECT kontrolü
    pass
```

**2. Query Caching:**
```python
# Benzer sorgular için cache
cache_key = hash(natural_language_query)
if cache_key in cache:
    return cache[cache_key]
```

**3. Multi-Step Reasoning:**
```python
# Karmaşık sorgular için adım adım işleme
# 1. Niyeti anla
# 2. Alt sorgulara böl
# 3. Her alt sorguyu çöz
# 4. Birleştir
```

## 7. PERFORMANS VE OPTİMİZASYON

### 7.1 Mevcut Performans

**Ollama (Yerel):**
- Yanıt süresi: 2-5 saniye (model boyutuna göre)
- CPU/GPU kullanımı: Yüksek (yerel işleme)
- Maliyet: Sıfır (sunucu maliyeti hariç)

**OpenAI (Bulut):**
- Yanıt süresi: 1-3 saniye
- API maliyeti: ~$0.01-0.05 per sorgu
- Veri gizliliği: Dikkat gerektirir

### 7.2 Optimizasyon Stratejileri

**1. Prompt Optimization:**
- Daha kısa, net prompt'lar
- Gereksiz bilgi kaldırma
- Örnek sorgular ekleme

**2. Model Quantization:**
- Ollama için daha küçük model (4-bit quantization)
- Hız artışı, hafif doğruluk kaybı

**3. Batch Processing:**
- Birden fazla sorguyu aynı anda işleme
- LLM'in batch inference yeteneği

## 8. SONUÇ

Projede niyet analizi ve SQL üretimi, **modern LLM teknolojisi** kullanılarak yapılmaktadır. Sistem, geleneksel NLP pipeline yerine, LLM'in semantik anlama yeteneğini kullanarak daha esnek ve doğal bir çözüm sunar.

**Avantajlar:**
- Doğal dil anlama
- Türkçe dil desteği
- Karmaşık sorguları anlama
- Kolay genişletilebilirlik

**Geliştirme Alanları:**
- SQL validation katmanı
- Query caching
- Multi-step reasoning
- Daha iyi hata mesajları

**Kod Lokasyonu:**
- `backend/app/services/llm_service.py` - Ana LLM servisi
- `backend/app/api/query.py` - API endpoint'i
- `config/settings.py` - LLM konfigürasyonu
