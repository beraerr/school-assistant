# Akıllı Okul Bilgi Sistemi - Proje Özeti

## 🎯 Proje Nedir?

**Akıllı Okul Bilgi Sistemi**, yapay zeka destekli bir okul yönetim sistemidir. Kullanıcılar SQL bilmeden, **Türkçe konuşma diliyle** veritabanı sorguları yapabilir. Örneğin: *"Bu ay devamsızlığı 5 günü geçen öğrencileri göster"* gibi bir soru sorulduğunda, sistem otomatik olarak SQL sorgusuna dönüştürür ve sonuçları gösterir.

## 🔧 Nasıl Çalışıyor?

### 1. **Doğal Dil İşleme (NLP)**
- Kullanıcı Türkçe bir soru sorar: *"Çocuğumun matematik notlarını göster"*
- **LLM (Large Language Model)** - Ollama DeepSeek veya OpenAI - bu soruyu analiz eder
- Veritabanı şeması bilgisi ile birlikte SQL sorgusuna dönüştürür

### 2. **Rol Tabanlı Güvenlik (Rule Engine)**
- Her kullanıcının rolü vardır: **Müdür, Öğretmen, Veli, Öğrenci**
- Sistem, kullanıcının rolüne göre sorguyu otomatik olarak kısıtlar:
  - **Öğretmen**: Sadece kendi sınıfını görür
  - **Veli**: Sadece kendi çocuğunun verilerini görür
  - **Öğrenci**: Sadece kendi verilerini görür
  - **Müdür**: Tüm verilere erişir

### 3. **Güvenlik Kontrolü**
- Sadece **SELECT** sorgularına izin verilir (SQL injection koruması)
- Hassas veriler (TC kimlik, telefon, adres) rol bazlı filtrelenir
- Her sorgu loglanır

### 4. **Sonuç Gösterimi**
- SQL sorgusu çalıştırılır
- Sonuçlar kullanıcıya gösterilir
- AI, sorgunun nasıl işlendiğini Türkçe olarak açıklar (Explainable AI)

## 🛠️ Kullanılan Teknolojiler

### Backend (FastAPI - Python)
- **FastAPI**: Modern, hızlı web framework
- **SQLAlchemy**: Veritabanı ORM (Object-Relational Mapping)
- **PostgreSQL**: İlişkisel veritabanı
- **JWT**: Token tabanlı kimlik doğrulama
- **Bcrypt**: Şifre hashleme

### AI/LLM Katmanı
- **LangChain**: LLM entegrasyonu ve prompt yönetimi
- **Ollama**: Yerel, ücretsiz LLM (DeepSeek R1:7B modeli)
- **OpenAI**: Alternatif bulut LLM (opsiyonel)
- **Prompt Engineering**: Türkçe dil desteği için optimize edilmiş prompt şablonları

### Frontend (Streamlit - Python)
- **Streamlit**: Hızlı web arayüzü geliştirme
- **Pandas**: Veri işleme ve görselleştirme
- Türkçe kullanıcı arayüzü

### Güvenlik
- **JWT Token**: Oturum yönetimi
- **Role-Based Access Control (RBAC)**: Rol tabanlı erişim kontrolü
- **SQL Injection Koruması**: Sadece SELECT sorguları
- **CORS Middleware**: Cross-origin güvenliği

## 📊 Veritabanı Yapısı

Sistem şu tabloları içerir:
- **students**: Öğrenci bilgileri (id, name, class_name, total_absences, parent_id)
- **grades**: Not bilgileri (id, student_id, subject, grade, date)
- **attendance**: Devamsızlık kayıtları (id, student_id, date, status)
- **teachers**: Öğretmen bilgileri (id, name, class_name)
- **users**: Kullanıcı hesapları (id, username, password_hash, role, related_id, related_class)

## 🚀 Çalışma Akışı (5 Adım)

1. **Kullanıcı sorgusu gelir**: "Bu ay devamsızlığı 5 günü geçen öğrencileri göster"
2. **LLM analiz eder**: Sorguyu anlar ve SQL'e dönüştürür
3. **Rule Engine devreye girer**: Kullanıcının rolüne göre sorguyu kısıtlar
4. **Güvenlik kontrolü**: Sadece SELECT sorgularına izin verilir
5. **Sonuç gösterilir**: Veriler kullanıcıya sunulur ve AI açıklama yapar

## 💡 Örnek Kullanım Senaryoları

### Müdür için:
- "Devamsızlık oranı en yüksek sınıflar hangileri?"
- "Tüm sınıfların ortalama notlarını göster"

### Öğretmen için:
- "Sınıfımdaki öğrencilerin matematik notlarını listele"
- "En yüksek not alan öğrencileri göster"

### Veli için:
- "Çocuğumun matematik notları geçen aya göre nasıl değişti?"
- "Çocuğumun bu ayki devamsızlık durumu nedir?"

### Öğrenci için:
- "Benim matematik notlarım geçen aya göre nasıl değişti?"
- "Tüm ders notlarımı göster"

## 🎓 Önemli Özellikler

1. **Doğal Dil Sorgulama**: SQL bilmeden Türkçe soru sorma
2. **Otomatik Rol Filtreleme**: Kullanıcı yetkilerine göre otomatik kısıtlama
3. **Explainable AI**: Her sorgu sonrası Türkçe açıklama
4. **Modüler LLM Entegrasyonu**: Farklı LLM sağlayıcılarına geçiş imkanı
5. **Güvenli**: KVKK uyumlu, rol tabanlı veri koruma

## 📁 Proje Yapısı

```
smart_school_information_system/
├── backend/              # FastAPI backend
│   ├── app/
│   │   ├── api/         # API endpoints (auth, query)
│   │   ├── core/        # Database ve security
│   │   ├── models/      # Veritabanı modelleri
│   │   ├── services/    # LLM ve Rule Engine servisleri
│   │   └── utils/       # Yardımcı fonksiyonlar
│   └── main.py          # FastAPI uygulaması
├── frontend/
│   └── app.py           # Streamlit frontend
├── config/
│   └── settings.py      # Konfigürasyon
├── database/
│   └── init_db.py       # Veritabanı başlatma
└── requirements.txt      # Python bağımlılıkları
```

## 🔐 Demo Kullanıcılar

- **Müdür**: `principal` / `admin123` (Tüm verilere erişim)
- **Öğretmen**: `teacher1` / `teacher123` (Sadece 9-A sınıfı)
- **Veli**: `parent1` / `parent123` (Sadece kendi çocuğu)
- **Öğrenci**: `student1` / `student123` (Sadece kendi verileri)

## 🎯 Proje Amacı

Bu proje, e-devlet sistemlerinde vatandaş deneyimini iyileştirmek için geliştirilmiştir. Teknik bilgisi olmayan kullanıcıların da karmaşık menüler yerine doğal dilleriyle sorgu yapabilmesini sağlar. Aynı teknoloji, sağlık, vergi, belediye gibi diğer e-devlet servislerine de uygulanabilir.

---

**Teknoloji Stack**: Python, FastAPI, PostgreSQL, LangChain, Ollama/OpenAI, Streamlit
**Durum**: Prototip tamamlandı, production hazırlığı aşamasında
