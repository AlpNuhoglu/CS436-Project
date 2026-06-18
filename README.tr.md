<div align="right">

[English](README.md) | **Türkçe**

</div>

# Ders Forumu

Sabancı Üniversitesi'ne özel hoca & ders değerlendirme platformu.
Öğrenciler anonim olarak hoca ve ders yorumu yazabilir, dönem bazlı filtreler uygulayabilir, yorumları faydalı/faydasız olarak oylayabilir.

> 🌐 **Dil:** Bu sayfa Türkçedir. İngilizce okumak için yukarıdaki **[English](README.md)** bağlantısına tıklayın.

## Teknoloji

| Katman | Teknoloji |
|---|---|
| Backend | FastAPI + SQLAlchemy + Alembic |
| Veritabanı | PostgreSQL 16 |
| Frontend | React + TypeScript + Tailwind CSS + Vite |
| Auth | JWT + e-posta OTP (Gmail SMTP) |
| Container | Docker + Docker Compose |
| Bulut (AWS) | ECS Fargate, RDS, ElastiCache, CloudFront, Cognito, Terraform IaC |

---

## Kurulum

### 1. Repoyu klonla

```bash
git clone <repo-url>
cd CS436-Project
```

### 2. `.env` dosyasını oluştur

```bash
cp .env.example .env
```

Ardından `.env` dosyasını açıp şu alanları doldur:

| Değişken | Açıklama |
|---|---|
| `DATABASE_URL` | Senaryo A/B'ye göre seç (dosya içinde açıklama var) |
| `JWT_SECRET` | `openssl rand -hex 32` komutuyla üret |
| `SMTP_USER` | Gmail adresin |
| `SMTP_PASSWORD` | Gmail **uygulama şifresi** (normal şifren değil) |
| `SMTP_FROM` | Gmail adresin (SMTP_USER ile aynı olabilir) |

> **Gmail uygulama şifresi nasıl alınır?**
> Google Hesabı → Güvenlik → 2 Adımlı Doğrulama (açık olmalı) → Uygulama şifreleri → Yeni oluştur

> **SMTP boş bırakılırsa ne olur?**
> OTP kodları e-posta yerine terminal loglarına yazılır. Geliştirme ortamı için yeterlidir.

---

## Çalıştırma

Üç farklı senaryo desteklenir. Birini seç:

---

### Senaryo A — Her şey Docker'da (en kolay)

Backend + veritabanı Docker'da, frontend lokalde çalışır.

```bash
# 1) Container'ları başlat
docker compose up -d

# 2) Migration'ları uygula (ilk kurulumda ve yeni migration geldiğinde)
docker exec ders_forumu_api alembic upgrade head

# 3) Frontend bağımlılıklarını yükle (ilk kurulumda)
cd frontend && npm install

# 4) Frontend'i başlat
npm run dev
```

| Servis | URL |
|---|---|
| Frontend | http://localhost:5173 |
| Backend API | http://localhost:8000 |
| API Docs (Swagger) | http://localhost:8000/docs |

---

### Senaryo B — Sadece DB Docker'da, backend lokal

Kod değişikliklerini hızlıca test etmek istiyorsan backend'i lokal çalıştırabilirsin.

```bash
# 1) .env içinde DATABASE_URL'yi localhost'a çevir:
#    DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/ders_forumu

# 2) Sadece veritabanını Docker'da başlat
docker compose up -d db

# 3) Python sanal ortamı oluştur (ilk kurulumda)
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 4) Migration'ları uygula (ilk kurulumda ve yeni migration geldiğinde)
alembic upgrade head

# 5) Backend'i başlat
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 6) Ayrı bir terminalde frontend'i başlat
cd frontend && npm install && npm run dev
```

---

### Senaryo C — Her şey lokal (Docker yok)

```bash
# PostgreSQL'i kur ve başlat
brew install postgresql@16
brew services start postgresql@16
createdb ders_forumu

# .env içinde DATABASE_URL:
# DATABASE_URL=postgresql+psycopg2://postgres@localhost:5432/ders_forumu

# Kalan adımlar Senaryo B'nin 3–6. adımlarıyla aynı
```

---

## Sıfırdan İlk Kurulum Özeti (Senaryo A)

```bash
git clone <repo-url> && cd CS436-Project
cp .env.example .env          # .env'i düzenle (JWT_SECRET + SMTP)
docker compose up -d
docker exec ders_forumu_api alembic upgrade head
cd frontend && npm install && npm run dev
```

---

## Yeni Migration Geldiğinde

Ekip üyesi yeni migration ekledi ve `git pull` yaptıysan:

```bash
# Senaryo A (Docker)
docker exec ders_forumu_api alembic upgrade head

# Senaryo B/C (lokal backend)
alembic upgrade head
```

---

## Proje Yapısı

```
CS436-Project/
├── app/
│   ├── main.py              # FastAPI entry point
│   ├── config.py            # Env ayarları
│   ├── database.py          # SQLAlchemy engine & session
│   ├── models/              # ORM modelleri
│   ├── routes/              # API endpoint'leri
│   ├── schemas/             # Pydantic istek/yanıt modelleri
│   ├── auth/                # JWT & bağımlılıklar
│   └── utils/               # Yardımcı fonksiyonlar
├── alembic/
│   └── versions/            # Migration dosyaları
├── frontend/
│   ├── src/
│   │   ├── pages/           # Sayfa bileşenleri
│   │   ├── components/      # Tekrar kullanılabilir bileşenler
│   │   ├── api/             # Backend API çağrıları
│   │   ├── contexts/        # React context'leri (Auth vb.)
│   │   └── types/           # TypeScript tip tanımları
│   └── package.json
├── infra/                   # Terraform altyapı kodu (AWS)
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── .env.example             # Kopyala → .env yap, doldur
└── .gitignore
```

---

## Commit Formatı

```
feat:     yeni özellik
fix:      hata düzeltme
refactor: kod düzenlemesi
docs:     dokümantasyon
chore:    bağımlılık / yapılandırma
```
