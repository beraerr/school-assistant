# Hızlı Başlangıç

## Kurulum

### 1. Bağımlılıkları Yükle

```bash
pip install -r requirements.txt
```

### 2. Veritabanını Hazırla

PostgreSQL'in çalıştığından emin olun, sonra veritabanını oluşturun:

```bash
createdb school_db
```

### 3. Ortam Değişkenlerini Ayarla

`.env` dosyası oluşturun:

```bash
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/school_db
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=deepseek-r1:7b
SECRET_KEY=your-secret-key-change-in-production
```

### 4. Veritabanını Başlat

```bash
python database/init_db.py
```

Bu komut tüm tabloları oluşturur ve örnek verilerle doldurur.

### 5. Backend'i Başlat

```bash
./run_backend.sh
```

Backend http://localhost:8000 adresinde çalışacak.

### 6. Frontend'i Başlat (yeni terminal)

```bash
./run_frontend.sh
```

Frontend http://localhost:8501 adresinde açılacak.

## Test Etme

1. Tarayıcıda http://localhost:8501 adresini açın
2. Demo kullanıcı ile giriş yapın: `principal` / `admin123`
3. Bir sorgu deneyin: "Bu ay devamsızlığı 5 günü geçen öğrencileri göster"

## Demo Kullanıcılar

- Müdür: `principal` / `admin123` (Tüm verilere erişim)
- Öğretmen: `teacher1` / `teacher123` (Sadece 9-A sınıfı)
- Veli: `parent1` / `parent123` (Sadece kendi çocuğu)
- Öğrenci: `student1` / `student123` (Sadece kendi verileri)

## Sorun Giderme

### Ollama Bağlantı Hatası

Ollama'nın çalıştığından emin olun:

```bash
ollama serve
```

Modelin yüklü olduğunu kontrol edin:

```bash
ollama pull deepseek-r1:7b
```

### Veritabanı Bağlantı Hatası

PostgreSQL'in çalıştığını ve `.env` dosyasındaki bilgilerin doğru olduğunu kontrol edin.
