"""SQLAlchemy models for Doctor in a Box screenings."""

from datetime import datetime, timezone

from database import db


def utcnow():
    return datetime.now(timezone.utc)


class Screening(db.Model):
    __tablename__ = 'screenings'

    id = db.Column(db.Integer, primary_key=True)
    screening_id = db.Column(db.String(32), unique=True, nullable=False, index=True)
    person = db.Column(db.JSON, nullable=False, default=dict)
    checkups = db.Column(db.JSON, nullable=False, default=dict)
    results = db.Column(db.JSON, nullable=False, default=dict)
    tests = db.Column(db.JSON, nullable=False, default=list)
    amount = db.Column(db.Float, nullable=False, default=0)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)

    def to_dict(self):
        return {
            'id': self.screening_id,
            'person': self.person or {},
            'checkups': self.checkups or {},
            'results': self.results or {},
            'tests': self.tests or [],
            'amount': float(self.amount or 0),
            'createdAt': self.created_at.isoformat() if self.created_at else None,
            'updatedAt': self.updated_at.isoformat() if self.updated_at else None,
        }

    @classmethod
    def from_payload(cls, payload, existing=None):
        screening_id = payload.get('id') or payload.get('screening_id')
        if not screening_id:
            raise ValueError('screening id is required')

        row = existing or cls(screening_id=screening_id)
        row.screening_id = screening_id
        row.person = payload.get('person') or {}
        row.checkups = payload.get('checkups') or {}
        row.results = payload.get('results') or {}
        row.tests = payload.get('tests') or []
        try:
            row.amount = float(payload.get('amount') or 0)
        except (TypeError, ValueError):
            row.amount = 0
        row.updated_at = utcnow()
        if not existing:
            created = payload.get('createdAt')
            if created:
                try:
                    row.created_at = datetime.fromisoformat(created.replace('Z', '+00:00'))
                except ValueError:
                    row.created_at = utcnow()
            else:
                row.created_at = utcnow()
        return row


class AppMeta(db.Model):
    """App-level settings: counter, campaign location."""

    __tablename__ = 'app_meta'

    key = db.Column(db.String(64), primary_key=True)
    value = db.Column(db.JSON, nullable=False, default=dict)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)

    @staticmethod
    def get_value(key, default=None):
        row = db.session.get(AppMeta, key)
        if not row:
            return default
        return row.value

    @staticmethod
    def set_value(key, value):
        row = db.session.get(AppMeta, key)
        if not row:
            row = AppMeta(key=key, value=value)
            db.session.add(row)
        else:
            row.value = value
            row.updated_at = utcnow()
        return row
