"""Create PostgreSQL database + tables for Doctor in a Box."""

import os
import sys

from dotenv import load_dotenv

load_dotenv()


def ensure_database():
    import psycopg2
    from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
    from urllib.parse import urlparse

    url = os.getenv(
        'DATABASE_URL',
        'postgresql+psycopg2://postgres:postgres@localhost:5432/dib_screening'
    )
    if url.startswith('postgresql+psycopg2://'):
        url = url.replace('postgresql+psycopg2://', 'postgresql://', 1)

    parsed = urlparse(url)
    db_name = (parsed.path or '/dib_screening').lstrip('/') or 'dib_screening'
    user = parsed.username or 'postgres'
    password = parsed.password or 'postgres'
    host = parsed.hostname or 'localhost'
    port = parsed.port or 5432

    print(f"Connecting to PostgreSQL at {host}:{port} as {user}...")
    conn = psycopg2.connect(
        dbname='postgres',
        user=user,
        password=password,
        host=host,
        port=port,
    )
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (db_name,))
    exists = cur.fetchone()
    if exists:
        print(f"Database '{db_name}' already exists.")
    else:
        cur.execute(f'CREATE DATABASE "{db_name}"')
        print(f"Created database '{db_name}'.")
    cur.close()
    conn.close()
    return True


def create_tables():
    from app import app
    from database import db
    with app.app_context():
        db.create_all()
        print("Tables created: screenings, app_meta")


if __name__ == '__main__':
    try:
        ensure_database()
        create_tables()
        print("PostgreSQL setup complete.")
    except Exception as exc:
        print("Setup failed:", exc)
        print()
        print("Fix tips:")
        print("1. Install PostgreSQL and start the service")
        print("2. Copy .env.example to .env and set DATABASE_URL")
        print("   Default: postgresql+psycopg2://postgres:YOUR_PASSWORD@localhost:5432/dib_screening")
        print("3. Re-run: python setup_db.py")
        sys.exit(1)
