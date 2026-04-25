# Akıllı Okul Bilgi Sistemi

Okul ortamında farklı rollere sahip kullanıcıların (yönetici, öğretmen, veli) doğal dil ile sorgu yapabildiği, yapay zeka destekli bir bilgi sistemi. FastAPI tabanlı backend, Streamlit arayüzü ve PostgreSQL veritabanından oluşuyor.

## Proje Hakkında

Projenin temel fikri şu: kullanıcı SQL bilmeden, kendi cümleleriyle sisteme soru sorabilsin. "Bu dönem devamsızlığı en yüksek 5 öğrenci kimler?" ya da "Matematik notu düşen öğrenciler hangi velilerle iletişime geçmeliyim?" gibi sorgular doğrudan işlenip yanıtlanıyor.

Rol bazlı erişim kontrolü var — her kullanıcı sadece kendi yetkisi dahilindeki verileri görebiliyor. Veli yalnızca kendi çocuğuna, öğretmen yalnızca kendi derslerine ait verilere erişebiliyor.

Ayrıca bir risk analizi modülü de var: öğrenci devamsızlık, not trendi ve davranış verilerini birleştirerek erken uyarı skoru üretiyor. Makine öğrenmesi pipeline'ı UCI Student Performance veri setiyle eğitildi.

## Teknik Yapı

```
backend/      → FastAPI + SQLAlchemy + JWT auth
frontend/     → Streamlit (TR/EN bilingual)
data_science/ → sklearn pipeline, risk modeli, raporlar
database/     → seed scriptleri, PostgreSQL şeması
config/       → LLM ayarları (Anthropic / Ollama)
```

Backend, gelen doğal dil sorgusunu önce bir shortcut pipeline'ından geçiriyor — sık sorulan soru türlerini pattern matching ile hızlıca çözüyor. Pattern eşleşmezse LLM'e (Claude) devredip SQL üretiyor, güvenlik filtresinden geçiriyor ve çalıştırıyor.

## Kurulum

Docker Compose ile tüm stack ayağa kalkar:

```bash
cp .env.example .env          # API key ve secret ekle
docker compose up --build
```

Backend: `http://localhost:8000`
Frontend: `http://localhost:8501`
API docs: `http://localhost:8000/docs`

Demo (canlı): [http://46.224.34.44:8501/](http://46.224.34.44:8501/)

## Hetzner Auto-Restart (systemd)

`nohup` yerine servis yöneticisi kullanın:

```bash
cd /root/.openclaw/workspace/school-assistant
sudo bash deploy/systemd/install_services.sh
```

Servis kontrolü:

```bash
sudo systemctl status school-backend.service
sudo systemctl status school-frontend.service
sudo journalctl -u school-backend.service -f
sudo journalctl -u school-frontend.service -f
```

Manuel kurulum için:

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn backend.app.main:app --reload      # terminal 1
streamlit run frontend/app.py              # terminal 2
```

## Ortam Değişkenleri

```
DATABASE_URL       → PostgreSQL bağlantısı
ANTHROPIC_API_KEY  → Claude API key
ANTHROPIC_MODEL    → Claude model id (örn. claude-sonnet-4-6)
SECRET_KEY         → JWT imzalama için rastgele string
```

## Testler

```bash
pytest backend/tests/ -v
```

---

# Smart School Information System

A role-based AI assistant for school environments. Administrators, teachers, and parents can query the school database using natural language — no SQL required.

## What It Does

Users ask questions in plain language. The system figures out what they're asking, generates a safe SQL query, runs it, and returns a readable answer. Role-based access control ensures each user only sees data they're authorized for.

There's also a risk scoring module that combines attendance, grade trends, and behavior data to flag students who may need early intervention. The underlying model was trained on the UCI Student Performance dataset.

## Stack

- **Backend:** FastAPI, SQLAlchemy, JWT authentication
- **Frontend:** Streamlit with Turkish/English toggle
- **Database:** PostgreSQL
- **AI:** Anthropic Claude
- **ML:** scikit-learn risk pipeline

## Running Locally

```bash
cp .env.example .env
docker compose up --build
```

Or manually:

```bash
pip install -r requirements.txt
uvicorn backend.app.main:app --reload
streamlit run frontend/app.py
```

Live demo: [http://46.224.34.44:8501/](http://46.224.34.44:8501/)

## Environment Variables

```
DATABASE_URL       → PostgreSQL connection string
ANTHROPIC_API_KEY  → Claude API key
ANTHROPIC_MODEL    → Claude model id (e.g. claude-sonnet-4-6)
SECRET_KEY         → random string for JWT signing
```

## Tests

```bash
pytest backend/tests/ -v
```
