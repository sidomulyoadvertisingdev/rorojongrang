<div align="center">

# Roro Jonggrang

**Platform Digital Marketing untuk UMKM Indonesia**

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.0-green.svg)](https://flask.palletsprojects.com)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

</div>

---

## Overview

Roro Jonggrang adalah platform digital marketing all-in-one untuk UMKM Indonesia. Scraping data Google Maps, kelola leads CRM, jadwalkan follow-up, jalankan kampanye, kolaborasi tim dengan Kanban boards, dan upload file ke Google Drive — semuanya dalam satu platform.

**Live:** [rorojonggrang.web.id](https://rorojonggrang.web.id)

---

## Fitur Utama

### Data Scraping
| Fitur | Deskripsi |
|-------|-----------|
| **Google Maps Scraping** | Scraping otomatis ribuan bisnis lokal (nama, alamat, telepon, rating, website) |
| **Terminal Real-time** | Monitor proses scraping langsung dengan tampilan terminal |
| **Multi Lokasi** | 10 lokasi di Jawa Barat |
| **Multi Kategori** | 6 kategori bisnis berbeda |
| **Radius Pencarian** | Atur radius 1km - 20km dari lokasi pusat |
| **Real-time Progress** | SSE via Redis pub/sub untuk update instan |
| **Export CSV/JSON** | Download hasil scraping dalam format CSV atau JSON |

### CRM & Marketing
| Fitur | Deskripsi |
|-------|-----------|
| **Lead Pipeline (CRM)** | Kanban visual untuk pipeline leads — new, contacted, negotiation, won, lost |
| **Follow-up Scheduler** | Jadwalkan follow-up via telepon, WhatsApp, email, atau pertemuan |
| **Campaign Analytics** | Buat kampanye marketing, pantau total leads, conversion rate, dan nilai pipeline |
| **WhatsApp Templates** | Template pesan WhatsApp yang bisa digunakan untuk follow-up |

### Kolaborasi Tim
| Fitur | Deskripsi |
|-------|-----------|
| **Kanban Boards** | Papan Kanban dengan drag-and-drop untuk manajemen tugas tim |
| **Board-Level Files** | Lihat semua file di satu board dalam grid view dengan filter tipe |
| **Comment + File** | Lampirkan file saat kirim comment di task |
| **Task Attachments** | Upload file langsung ke task (tersimpan di Google Drive) |
| **Activity Log** | Pantau aktivitas tim secara real-time |

### Integrasi Cloud
| Fitur | Deskripsi |
|-------|-----------|
| **Google Drive** | Upload file langsung ke Google Drive, auto-share "anyone can view" |
| **Campaign File Upload** | Upload desain/brosur di campaign dengan drag-drop |
| **Auto Folder** | Folder otomatis per board di Google Drive |
| **25MB File Limit** | Support semua format file, maks 25MB per file |

### UI & UX
| Fitur | Deskripsi |
|-------|-----------|
| **Light & Dark Mode** | Default terang, toggle satu klik untuk mode gelap |
| **Collapsible Sidebar** | Sidebar bisa di-collapse ke icon-only |
| **Grouped Menu** | Menu terorganisir dalam grup: Data, Kerja Sama, Marketing, Pengaturan |
| **Mobile Responsive** | Bottom navigation untuk mobile |
| **Bilingual** | Dukungan Bahasa Indonesia dan English |
| **Blog Public** | Halaman publik (Home, Fitur, Roadmap, Panduan, Tentang, FAQ) |

---

## Tech Stack

- **Backend:** Python 3.9, Flask, PyMySQL, Selenium + BeautifulSoup4
- **Frontend:** Jinja2, HTMX, Vanilla JS, Lucide Icons
- **Database:** MySQL
- **Cache/Queue:** Redis
- **Maps:** Leaflet + OpenStreetMap
- **Cloud:** Google Drive API v3 (OAuth 2.0 via Authlib)
- **Design:** Custom CSS dengan yellow neon theme (`#f59e0b`)

---

## Struktur Project

```
gmaps-scraper/
├── app.py                    # Flask app factory
├── config/
│   ├── categories.json       # Keywords & locations
│   ├── settings.py           # App configuration
│   └── web_settings.py       # Flask/SQLAlchemy config
├── core/
│   ├── browser.py            # Selenium browser management
│   ├── navigator.py          # Google Maps navigation
│   ├── parser.py             # Business detail parser
│   └── scraper.py            # Scraper orchestrator
├── helpers/
│   └── drive.py              # Google Drive API v3 helper
├── models/
│   ├── __init__.py           # Model registry
│   ├── user.py               # User + UserDriveToken models
│   ├── task.py               # ScrapingTask model
│   ├── business.py           # Business model
│   ├── board.py              # Board, BoardColumn, BoardTask, TaskActivity, TaskChecklist
│   ├── lead_pipeline.py      # LeadPipeline (CRM)
│   ├── lead_activity.py      # LeadActivity
│   ├── followup.py           # FollowUp (call, WA, email, meeting, survey)
│   ├── campaign.py           # Campaign + CampaignMetric
│   ├── campaign_attachment.py# CampaignAttachment
│   └── task_attachment.py    # TaskAttachment
├── routes/
│   ├── auth.py               # Login/Register/Google Drive OAuth
│   ├── dashboard.py          # Dashboard page
│   ├── scraper.py            # Scraping routes
│   ├── api.py                # REST API + SSE
│   ├── boards.py             # Kanban boards + attachments + comments
│   ├── leads.py              # Lead Pipeline CRUD
│   ├── followups.py          # Follow-up Scheduler
│   ├── campaigns.py          # Campaign CRUD + file uploads
│   ├── analytics.py          # Data Analitik
│   ├── admin.py              # User management + activity log
│   ├── wa_templates.py       # WhatsApp templates
│   └── blog.py               # Public blog
├── templates/
│   ├── base.html             # App layout (grouped sidebar, light/dark mode)
│   ├── auth/                 # Login, Register, Edit Profile, Change Password
│   ├── dashboard/            # Dashboard
│   ├── scraper/              # Scraping form, history, results
│   ├── boards/               # Kanban boards, task detail, board files
│   ├── leads/                # Lead pipeline, detail, create
│   ├── followups/            # Follow-up dashboard, create
│   ├── campaigns/            # Campaign list, create, dashboard
│   ├── analytics/            # Data Analitik
│   ├── admin/                # User management, activity log, feedback
│   ├── wa_templates/         # WhatsApp templates
│   └── blog/                 # Public blog (6 pages)
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
- MySQL
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
# Edit .env with your database credentials and Google OAuth keys

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

### Public
| Route | Description |
|-------|-------------|
| `/blog/` | Blog homepage |
| `/blog/features` | Features page |
| `/blog/roadmap` | Development roadmap |
| `/blog/guide` | User guide |
| `/blog/about` | About page |
| `/blog/faq` | FAQ page |

### Auth
| Route | Description |
|-------|-------------|
| `/login` | Login page |
| `/register` | Register page |
| `/login/google` | Google OAuth (login) |
| `/profile` | Edit profile + Google Drive connection |
| `/profile/change-password` | Change password |

### Dashboard & Scraping
| Route | Description |
|-------|-------------|
| `/` | Dashboard |
| `/scrape` | Scraping form |
| `/history` | Task history |
| `/download/<id>/<fmt>` | Download results (CSV/JSON) |

### Kanban Boards
| Route | Description |
|-------|-------------|
| `/boards` | Board list |
| `/boards/<id>` | Board view (Kanban) |
| `/boards/<id>/files` | Board-level files view |

### CRM & Marketing
| Route | Description |
|-------|-------------|
| `/leads` | Lead Pipeline (Kanban) |
| `/leads/<id>` | Lead detail + activity log |
| `/leads/create` | Create lead |
| `/followups` | Follow-up dashboard |
| `/followups/create` | Schedule follow-up |
| `/campaigns` | Campaign list |
| `/campaigns/create` | Create campaign |
| `/campaigns/<id>/dashboard` | Campaign analytics dashboard |

### Admin
| Route | Description |
|-------|-------------|
| `/admin/users` | User management |
| `/admin/log` | Activity log |
| `/admin/feedback` | Saran & Kritik |

---

## License

MIT License - See [LICENSE](LICENSE) for details.

---

<div align="center">

**Built with ❤ for Ragam Msanfaat Sinergi**

</div>
