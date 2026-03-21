# Hızlı Başlangıç
carga@carga:~/some_projects/smart_school_information_system$ pip install -r requirements.txt
error: externally-managed-environment

× This environment is externally managed
╰─> To install Python packages system-wide, try apt install
    python3-xyz, where xyz is the package you are trying to
    install.
    
    If you wish to install a non-Debian-packaged Python package,
    create a virtual environment using python3 -m venv path/to/venv.
    Then use path/to/venv/bin/python and path/to/venv/bin/pip. Make
    sure you have python3-full installed.
    
    If you wish to install a non-Debian packaged Python application,
    it may be easiest to use pipx install xyz, which will manage a
    virtual environment for you. Make sure you have pipx installed.
    
    See /usr/share/doc/python3.12/README.venv for more information.

note: If you believe this is a mistake, please contact your Python installation or OS distribution provider. You can override this, at the risk of breaking your Python installation or OS, by passing --break-system-packages.
hint: See PEP 668 for the detailed specification.
## Kurulum

### 1. Python Sanal Ortamı Oluştur (Önerilen)

Modern Linux sistemlerinde (Debian/Ubuntu) Python paketlerini doğrudan yüklemek yerine sanal ortam kullanın:

```bash
python3 -m venv venv
source venv/bin/activate
```

### 2. Bağımlılıkları Yükle

```bash
pip install -r requirements.txt
```

**Not:** Her yeni terminal açtığınızda sanal ortamı aktifleştirmeyi unutmayın:
```bash
source venv/bin/activate
```

### 3. Veritabanını Hazırla

PostgreSQL'in çalıştığından emin olun, sonra veritabanını oluşturun:

```bash
createdb school_db
```

### 4. Ortam Değişkenlerini Ayarla

`.env` dosyası oluşturun:

```bash
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/school_db
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=deepseek-r1:7b
SECRET_KEY=your-secret-key-change-in-production
```

### 5. Veritabanını Başlat

```bash
python database/init_db.py
```

Bu komut tüm tabloları oluşturur ve örnek verilerle doldurur.

### 6. Backend'i Başlat

```bash
./run_backend.sh
```

Backend http://localhost:8000 adresinde çalışacak.

### 7. Frontend'i Başlat (yeni terminal)

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

### Python Paket Yükleme Hatası (externally-managed-environment)

Eğer `pip install` komutunda "externally-managed-environment" hatası alıyorsanız, sanal ortam kullanmanız gerekiyor:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Sanal ortam aktifken, komut satırında `(venv)` öneki görünecektir.
