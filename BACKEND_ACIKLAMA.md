# Backend Nasıl Çalışıyor? - Kod İncelemesi

## 🎯 Backend'in Ana Görevi

Backend, **FastAPI** ile yazılmış bir REST API'dir. Frontend'den gelen Türkçe sorguları alır, AI ile SQL'e çevirir, güvenlik kontrolü yapar ve sonuçları döndürür.

---

## 📁 Backend Yapısı

```
backend/
├── app/
│   ├── main.py              # FastAPI uygulaması (giriş noktası)
│   ├── api/
│   │   ├── auth.py          # Giriş/çıkış işlemleri
│   │   ├── query.py         # Sorgu işleme endpoint'i (ANA KISIM)
│   │   └── dependencies.py  # Kimlik doğrulama yardımcıları
│   ├── core/
│   │   ├── database.py      # Veritabanı bağlantısı
│   │   └── security.py      # Şifre hashleme, JWT token
│   ├── services/
│   │   ├── llm_service.py    # AI servisi (Türkçe → SQL)
│   │   └── rule_engine.py   # Rol bazlı güvenlik
│   └── utils/
│       └── query_executor.py # SQL sorgu çalıştırıcı
```

---

## 🔥 Ana Akış: Bir Sorgu Nasıl İşlenir?

### 1️⃣ **Frontend'den Sorgu Gelir**

Frontend (Streamlit) kullanıcıdan Türkçe sorgu alır:
```python
# Frontend: "Bu ay devamsızlığı 5 günü geçen öğrencileri göster"
POST /query/
Headers: Authorization: Bearer <token>
Body: {"query": "Bu ay devamsızlığı 5 günü geçen öğrencileri göster"}
```

### 2️⃣ **query.py - Ana Endpoint**

```python
# backend/app/api/query.py

@router.post("/", response_model=QueryResponse)
async def execute_query(
    query_request: QueryRequest,           # Türkçe sorgu
    current_user: User = Depends(get_current_user),  # Kimlik doğrulama
    db: Session = Depends(get_db)          # Veritabanı bağlantısı
):
```

**Bu fonksiyon 5 adımda çalışır:**

#### **Adım 1: Türkçe → SQL Dönüşümü (LLM Service)**

```python
# Kullanıcı bilgilerini hazırla
user_context = {
    "role": current_user.role.value,        # "teacher", "parent", vb.
    "related_id": current_user.related_id,   # Öğrenci ID'si (veli/öğrenci için)
    "related_class": current_user.related_class  # Sınıf adı (öğretmen için)
}

# LLM servisine gönder
llm_result = llm_service.convert_to_sql(
    query_request.query,      # "Bu ay devamsızlığı 5 günü geçen öğrencileri göster"
    user_context=user_context
)

sql_query = llm_result["sql"]  # SELECT * FROM students WHERE total_absences > 5 ...
```

**Ne oluyor?**
- `llm_service.py` içindeki `LLMService` sınıfı devreye girer
- Ollama veya OpenAI'ye prompt gönderilir
- LLM, Türkçe sorguyu PostgreSQL SQL'e çevirir

#### **Adım 2: Rol Bazlı Güvenlik (Rule Engine)**

```python
# Rule Engine oluştur
rule_engine = RuleEngine(db, current_user)

# Sorguya güvenlik kuralları uygula
permission_result = rule_engine.apply_permissions(sql_query)
final_sql = permission_result["sql"]
```

**Ne oluyor?**
- Eğer kullanıcı **öğretmen** ise → SQL'e `WHERE students.class_name = '9-A'` eklenir
- Eğer kullanıcı **veli** ise → SQL'e `WHERE students.id = 123` eklenir
- Eğer kullanıcı **müdür** ise → SQL değiştirilmez (tüm verilere erişim)

**Örnek:**
```python
# Öğretmen sorgusu: "Tüm öğrencileri göster"
# LLM üretir: SELECT * FROM students
# Rule Engine ekler: SELECT * FROM students WHERE students.class_name = '9-A'
```

#### **Adım 3: SQL Sorgusunu Çalıştır**

```python
query_executor = QueryExecutor(db)
results = query_executor.execute_query(final_sql)
```

**Ne oluyor?**
- `query_executor.py` içindeki `QueryExecutor` sınıfı devreye girer
- Sadece **SELECT** sorgularına izin verilir (güvenlik)
- PostgreSQL'de sorgu çalıştırılır
- Sonuçlar dictionary listesi olarak döner

#### **Adım 4: Hassas Verileri Temizle**

```python
sanitized_results = rule_engine.sanitize_results(results)
```

**Ne oluyor?**
- TC kimlik, telefon, adres gibi hassas veriler kaldırılır
- Müdür hariç diğer roller için uygulanır

#### **Adım 5: AI Açıklaması Üret**

```python
explanation = llm_service.explain_query(
    final_sql,
    query_request.query,
    len(sanitized_results)
)
```

**Ne oluyor?**
- LLM, sorgunun nasıl işlendiğini Türkçe olarak açıklar
- "Sorgunuz şu şekilde işlendi: Bu ay içinde toplam devamsızlığı 5 günü aşan öğrenciler filtrelendi..."

#### **Sonuç Döndür**

```python
return {
    "results": sanitized_results,           # Veriler
    "sql_query": final_sql,                 # Oluşturulan SQL
    "original_query": query_request.query,   # Orijinal Türkçe sorgu
    "explanation": explanation,              # AI açıklaması
    "permissions_applied": permission_result["permissions_applied"],
    "permission_reason": permission_result["reason"],
    "results_count": len(sanitized_results)
}
```

---

## 🔐 Kimlik Doğrulama (Authentication)

### **auth.py - Giriş İşlemi**

```python
# backend/app/api/auth.py

@router.post("/login")
async def login(login_data: LoginRequest, db: Session = Depends(get_db)):
    # 1. Kullanıcıyı veritabanından bul
    user = db.query(User).filter(User.username == login_data.username).first()
    
    # 2. Şifreyi kontrol et
    if not user or not verify_password(login_data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Kullanıcı adı veya şifre hatalı")
    
    # 3. JWT token oluştur
    access_token = create_access_token(
        data={"sub": user.username, "role": user.role.value},
        expires_delta=timedelta(minutes=30)
    )
    
    # 4. Token'ı döndür
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {...}
    }
```

**Ne oluyor?**
- Kullanıcı adı/şifre kontrol edilir
- Bcrypt ile şifre hash'i doğrulanır
- JWT token oluşturulur (30 dakika geçerli)
- Token frontend'e gönderilir

### **dependencies.py - Token Doğrulama**

```python
# backend/app/api/dependencies.py

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    # 1. Token'ı al
    token = credentials.credentials
    
    # 2. Token'ı decode et
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(401, "Geçersiz token")
    
    # 3. Kullanıcıyı veritabanından bul
    username = payload.get("sub")
    user = db.query(User).filter(User.username == username).first()
    
    # 4. Kullanıcıyı döndür
    return user
```

**Ne oluyor?**
- Her API isteğinde token kontrol edilir
- Token geçerliyse kullanıcı bilgileri döner
- Geçersizse 401 hatası döner

---

## 🤖 AI Servisi (LLM Service)

### **llm_service.py - Türkçe → SQL**

```python
# backend/app/services/llm_service.py

class LLMService:
    def convert_to_sql(self, natural_language_query: str, user_context: dict):
        # 1. Kullanıcı bağlamını ekle
        enhanced_query = natural_language_query
        if user_context["role"] == "teacher":
            enhanced_query += f" (Not: Kullanıcı öğretmen ve sadece {user_context['related_class']} sınıfına erişebilir)"
        
        # 2. Prompt template'e yerleştir
        prompt = f"""
        Sen bir SQL sorgu uzmanısın. Türkçe doğal dil sorgularını PostgreSQL SQL sorgularına dönüştürüyorsun.
        
        VERİTABANI ŞEMASI:
        - students (id, name, class_name, total_absences, parent_id)
        - grades (id, student_id, subject, grade, date)
        ...
        
        Kullanıcı Sorgusu: {enhanced_query}
        
        SQL Sorgusu:
        """
        
        # 3. LLM'e gönder (Ollama veya OpenAI)
        result = self.chain.run(query=enhanced_query)
        
        # 4. Sonucu temizle
        sql_query = result.strip().replace("```sql", "").replace("```", "")
        
        return {"sql": sql_query, ...}
```

**Ne oluyor?**
- LangChain ile LLM'e bağlanır
- Prompt template'e veritabanı şeması ve kullanıcı sorgusu eklenir
- LLM (Ollama DeepSeek veya OpenAI) SQL üretir
- Sonuç temizlenir ve döndürülür

---

## 🛡️ Güvenlik Motoru (Rule Engine)

### **rule_engine.py - Rol Bazlı Filtreleme**

```python
# backend/app/services/rule_engine.py

class RuleEngine:
    def apply_permissions(self, sql_query: str):
        # Müdür: Tüm verilere erişim
        if self.role == UserRole.PRINCIPAL:
            return {"sql": sql_query, "permissions_applied": False}
        
        # Öğretmen: Sadece kendi sınıfı
        elif self.role == UserRole.TEACHER:
            modified_query = self._restrict_to_class(sql_query, self.user.related_class)
            return {"sql": modified_query, "permissions_applied": True}
        
        # Veli/Öğrenci: Sadece kendi verileri
        elif self.role == UserRole.PARENT or self.role == UserRole.STUDENT:
            modified_query = self._restrict_to_student(sql_query, self.user.related_id)
            return {"sql": modified_query, "permissions_applied": True}
    
    def _restrict_to_class(self, sql_query: str, class_name: str):
        # SQL'e WHERE veya AND ekle
        if "WHERE" in sql_query.upper():
            # Mevcut WHERE'e AND ekle
            return sql_query + f" AND students.class_name = '{class_name}'"
        else:
            # Yeni WHERE ekle
            return sql_query + f" WHERE students.class_name = '{class_name}'"
```

**Ne oluyor?**
- Regex ile SQL parse edilir
- Kullanıcının rolüne göre WHERE clause eklenir/değiştirilir
- GROUP BY, ORDER BY gibi yapılar korunur

---

## 💾 Veritabanı İşlemleri

### **database.py - Bağlantı Yönetimi**

```python
# backend/app/core/database.py

# PostgreSQL bağlantısı oluştur
engine = create_engine(
    settings.DATABASE_URL,  # postgresql://user:pass@localhost:5432/school_db
    pool_pre_ping=True    # Bağlantı kontrolü
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """Her istek için yeni session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()  # İstek bitince kapat
```

**Ne oluyor?**
- PostgreSQL'e bağlanır
- Her API isteği için yeni session açar
- İstek bitince otomatik kapatır

### **query_executor.py - Güvenli SQL Çalıştırma**

```python
# backend/app/utils/query_executor.py

class QueryExecutor:
    def execute_query(self, sql_query: str):
        # 1. Sadece SELECT sorgularına izin ver
        sql_upper = sql_query.strip().upper()
        if not sql_upper.startswith("SELECT"):
            raise ValueError("Sadece SELECT sorgularına izin verilir")
        
        # 2. Sorguyu çalıştır
        result = self.db.execute(text(sql_query))
        
        # 3. Sonuçları dictionary listesine çevir
        columns = result.keys()
        rows = []
        for row in result:
            row_dict = {col: value for col, value in zip(columns, row)}
            rows.append(row_dict)
        
        return rows
```

**Ne oluyor?**
- SQL injection koruması: Sadece SELECT sorguları
- PostgreSQL'de sorgu çalıştırılır
- Sonuçlar Python dictionary listesine çevrilir

---

## 🔒 Güvenlik (Security)

### **security.py - Şifre ve Token İşlemleri**

```python
# backend/app/core/security.py

# Bcrypt ile şifre hashleme
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Şifreyi doğrula"""
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: timedelta):
    """JWT token oluştur"""
    to_encode = data.copy()
    expire = datetime.utcnow() + expires_delta
    to_encode.update({"exp": expire})
    
    # JWT encode
    encoded_jwt = jwt.encode(
        to_encode, 
        settings.SECRET_KEY, 
        algorithm="HS256"
    )
    return encoded_jwt
```

**Ne oluyor?**
- Şifreler Bcrypt ile hashlenir (güvenli)
- JWT token oluşturulur (30 dakika geçerli)
- Token içinde kullanıcı adı ve rol bilgisi var

---

## 🚀 main.py - FastAPI Uygulaması

```python
# backend/app/main.py

app = FastAPI(
    title="Smart School Information System",
    version="1.0.0"
)

# CORS middleware (frontend'den isteklere izin ver)
app.add_middleware(CORSMiddleware, allow_origins=["*"])

# Router'ları ekle
app.include_router(auth.router)    # /auth/login
app.include_router(query.router)   # /query/

@app.on_event("startup")
async def startup_event():
    """Uygulama başlarken veritabanını hazırla"""
    init_db()
```

**Ne oluyor?**
- FastAPI uygulaması oluşturulur
- CORS ayarları yapılır (frontend'den isteklere izin)
- Router'lar eklenir (auth, query)
- Uygulama başlarken veritabanı tabloları oluşturulur

---

## 📊 Tam Akış Özeti

```
1. Kullanıcı giriş yapar
   → auth.py → JWT token alır

2. Kullanıcı sorgu gönderir
   → query.py → execute_query() çağrılır

3. Kimlik doğrulama
   → dependencies.py → get_current_user() → Token kontrolü

4. Türkçe → SQL
   → llm_service.py → LLM'e gönder → SQL üretir

5. Güvenlik kontrolü
   → rule_engine.py → Rol bazlı filtreleme → SQL'e WHERE ekler

6. SQL çalıştır
   → query_executor.py → PostgreSQL'de çalıştır → Sonuçlar

7. Veri temizle
   → rule_engine.py → Hassas verileri kaldır

8. Açıklama üret
   → llm_service.py → AI açıklaması üretir

9. Sonuç döndür
   → Frontend'e JSON gönder
```

---

## 🎯 Özet

**Backend'in yaptığı 3 ana iş:**

1. **Kimlik Doğrulama**: Kullanıcı girişi, JWT token yönetimi
2. **AI İşleme**: Türkçe sorguyu SQL'e çevirme
3. **Güvenlik**: Rol bazlı filtreleme, SQL injection koruması, veri temizleme

**Backend = FastAPI + PostgreSQL + LangChain + Güvenlik Motoru**

Tüm bu işlemler **asenkron** (async) olarak çalışır, yani hızlıdır! 🚀
