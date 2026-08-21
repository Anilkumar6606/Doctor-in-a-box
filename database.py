"""Database setup for Doctor in a Box."""

import os
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv

load_dotenv()

db = SQLAlchemy()


def database_url():
    """Prefer DATABASE_URL; default to local PostgreSQL."""
    url = os.getenv(
        'DATABASE_URL',
        'postgresql+psycopg2://postgres:postgres@localhost:5432/dib_screening'
    )
    # Render / Heroku style URLs
    if url.startswith('postgres://'):
        url = url.replace('postgres://', 'postgresql+psycopg2://', 1)
    elif url.startswith('postgresql://') and '+psycopg' not in url:
        url = url.replace('postgresql://', 'postgresql+psycopg2://', 1)

    # Render managed Postgres usually needs SSL
    if 'render.com' in url and 'sslmode=' not in url:
        sep = '&' if '?' in url else '?'
        url = f'{url}{sep}sslmode=require'
    return url


def init_db(app, create_tables=True):
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url()
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
    }
    try:
        db.init_app(app)
    except Exception as exc:
        print(f'Warning: database engine init failed ({exc})')
        print('On Render: set Python to 3.12 (runtime.txt) and DATABASE_URL from Postgres.')
        return db

    if create_tables:
        with app.app_context():
            try:
                db.create_all()
            except Exception as exc:
                print(f'Warning: database not ready yet ({exc})')
                print('Link a Render PostgreSQL database and set DATABASE_URL.')
    return db
