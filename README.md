<div align="center">

# RoroJonggrang Data Scrape

**Platform Scraping Data Google Maps untuk Digital Marketing**

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.0-green.svg)](https://flask.palletsprojects.com)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

</div>

---

## Overview

RoroJonggrang adalah platform scraping data Google Maps yang dirancang khusus untuk kebutuhan digital marketing Indonesia. Kumpulkan data ribuan bisnis lokal — nama, alamat, telepon, rating — secara otomatis dengan interface premium.

**Live Demo:** [http://localhost:5001/blog/](http://localhost:5001/blog/)

---

## Fitur Utama

| Fitur | Deskripsi |
|-------|-----------|
| **Terminal Real-time** | Monitor proses scraping secara langsung dengan tampilan terminal premium |
| **Radius Pencarian** | Atur radius 1km - 20km dari lokasi pusat |
| **Dark/Light Mode** | Tampilan premium dengan mode malam dan siang |
| **Sidebar Collapsible** | Sidebar yang bisa dibuka/tutup untuk produktivitas |
| **Export CSV/JSON** | Download hasil scraping dalam format CSV atau JSON |
| **Real-time Progress** | SSE via Redis pub/sub untuk update instan |
| **Multi Lokasi** | 10 lokasi di Jawa Barat |
| **Multi Kategori** | 6 kategori bisnis berbeda |
| **Blog Public** | Halaman pengenalan 5 halaman (Home, Fitur, Panduan, Tentang, FAQ) |
| **Bilingual** | Dukungan Bahasa Indonesia dan English |

---

## Tech Stack

- **Backend:** Python 3.9, Flask, Celery, SQLAlchemy
- **Frontend:** HTML/CSS (Custom), HTMX, SSE
- **Database:** MySQL 8.0
- **Cache/Queue:** Redis
- **Browser Automation:** Selenium + Chrome (Headless)
- **Infrastructure:** Docker (MySQL, Redis)

---

## Timeline Pengembangan

### Phase 1: Core Engine (13 Juli 2026)
- [x] Selenium browser management dengan anti-detection
- [x] Google Maps navigation & scrolling
- [x] Business detail parser (nama, alamat, telepon, rating)
- [x] CLI scraper orchestrator
- [x] MySQL database schema
- [x] Rate limiter & random delays

### Phase 2: Web Application (13 Juli 2026)
- [x] Flask web app dengan authentication
- [x] Dashboard dengan statistik
- [x] Scraping form dengan lokasi & kategori
- [x] Celery background task processing
- [x] SSE real-time progress updates
- [x] Task history & pagination
- [x] Download CSV/JSON

### Phase 3: Premium UI (13 Juli 2026)
- [x] Dark/Light mode toggle
- [x] Collapsible sidebar
- [x] Gradient & glass morphism design
- [x] Terminal-style scraping log
- [x] Radius picker (1-20km)
- [x] Premium table styling
- [x] Mobile responsive

### Phase 4: Public Blog (13 Juli 2026)
- [x] 5-page blog (Home, Fitur, Panduan, Tentang, FAQ)
- [x] Bilingual support (ID/EN)
- [x] Language toggle
- [x] Dark/Light mode
- [x] Premium design dengan animations

### Phase 5: Backend Optimization (13 Juli 2026)
- [x] Redis pub/sub untuk real-time logs
- [x] SSE via Redis (bukan polling DB)
- [x] Radius parameter di Google Maps URL
- [x] Database migration (search_radius column)

---

## Struktur Project

```
gmaps-scraper/
├── app.py                    # Flask app factory
├── celery_worker.py          # Celery worker config
├── main.py                   # CLI entry point
├── start.sh / stop.sh        # Service management
├── config/
│   ├── categories.json       # Keywords & locations
│   ├── settings.py           # App configuration
│   └── web_settings.py       # Flask/SQLAlchemy config
├── core/
│   ├── browser.py            # Selenium browser management
│   ├── navigator.py          # Google Maps navigation
│   ├── parser.py             # Business detail parser
│   └── scraper.py            # Scraper orchestrator
├── models/
│   ├── user.py               # User model
│   ├── task.py               # ScrapingTask model
│   └── business.py           # Business model
├── routes/
│   ├── auth.py               # Login/Register/Logout
│   ├── dashboard.py          # Dashboard page
│   ├── scraper.py            # Scraping routes
│   ├── api.py                # REST API + SSE
│   └── blog.py               # Public blog
├── services/
│   └── scraping_service.py   # Celery scraping task
├── templates/
│   ├── base.html             # App layout
│   ├── auth/                 # Login & Register
│   ├── dashboard/            # Dashboard
│   ├── scraper/              # Scraping form & history
│   └── blog/                 # Public blog (5 pages)
├── utils/
│   ├── helpers.py            # Utility functions
│   ├── logger.py             # Logging setup
│   └── rate_limiter.py       # Rate limiting
└── static/
    └── css/                  # Static assets
```

---

## Instalasi

### Prerequisites
- Python 3.9+
- MySQL 8.0
- Redis
- Google Chrome

### Setup

```bash
# Clone repository
git clone git@github.com:sidomulyoadvertisingdev/rorojongrang.git
cd rorojongrang

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Setup environment
cp .env.example .env
# Edit .env with your database credentials

# Start MySQL & Redis (via Docker)
docker-compose up -d

# Initialize database
python -c "from app import create_app; app=create_app(); app.app_context().push(); from models import db; db.create_all()"

# Start the app
python app.py
```

### Default Account
- **Email:** admin@rorojonggrang.com
- **Password:** admin123

---

## Routes

| Route | Description | Auth |
|-------|-------------|------|
| `/blog/` | Public blog homepage | No |
| `/blog/features` | Features page | No |
| `/blog/guide` | User guide | No |
| `/blog/about` | About page | No |
| `/blog/faq` | FAQ page | No |
| `/login` | Login page | No |
| `/register` | Register page | No |
| `/` | Dashboard | Yes |
| `/scrape` | Scraping form | Yes |
| `/history` | Task history | Yes |
| `/download/<id>/<fmt>` | Download results | Yes |

---

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/task/<id>/status` | GET | Get task status |
| `/api/task/<id>/progress` | GET | SSE progress stream |
| `/api/tasks/active` | GET | List active tasks |

---

## License

MIT License - See [LICENSE](LICENSE) for details.

---

<div align="center">

**Built with ❤ for Digital Marketing Indonesia**

</div>
