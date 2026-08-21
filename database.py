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
    # Render / Heroku sometimes provide postgres:// which SQLAlchemy 2 rejects
    if url.startswith('postgres://'):
        url = url.replace('postgres://', 'postgresql+psycopg2://', 1)
    return url


def init_db(app, create_tables=True):
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url()
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)
    if create_tables:
        with app.app_context():
            try:
                db.create_all()
            except Exception as exc:
                print(f"Warning: database not ready yet ({exc})")
                print("Run: python setup_db.py  after PostgreSQL is installed.")
    return db
