# Doctor in a Box — PostgreSQL setup

## 1. Install Python packages
```bash
pip install -r requirements.txt
```

## 2. Install PostgreSQL
- Windows: install **PostgreSQL 17** (winget / EnterpriseDB installer)
- During install, set a password for user `postgres` and remember it
- Default port: `5432`

## 3. Configure `.env`
```bash
copy .env.example .env
```

Edit `.env` and set your password:
```
DATABASE_URL=postgresql+psycopg2://postgres:YOUR_PASSWORD@localhost:5432/dib_screening
```

## 4. Create database + tables
```bash
python setup_db.py
```

## 5. Start the server
```bash
python app.py
```

Open: http://localhost:5000

## What gets stored in PostgreSQL
| Table | Contents |
|-------|----------|
| `screenings` | Patient info, tests, results, amount, report IDs |
| `app_meta` | Screening counter + campaign location |

## API
- `GET /api/health` — server + DB status
- `GET /api/store` — full history (same shape as localStorage)
- `PUT /api/store` — replace/sync store
- `POST /api/migrate-local` — import browser localStorage dump
- `GET/POST /api/screenings`
- `GET/PUT/DELETE /api/screenings/<id>`

The web UI still caches in localStorage for speed, and syncs to PostgreSQL when the Flask API is available.
