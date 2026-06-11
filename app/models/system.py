from app.extensions import db
from datetime import datetime, timezone

class SystemSetting(db.Model):
    __tablename__ = "system_settings"

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False, index=True)
    value = db.Column(db.Text, nullable=True)
    type = db.Column(db.String(20), default="string") # string, boolean, int, json
    description = db.Column(db.String(255), nullable=True)
    
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    @classmethod
    def get(cls, key, default=None):
        setting = cls.query.filter_by(key=key).first()
        if not setting:
            return default
        
        if setting.type == "boolean":
            return setting.value.lower() in ("true", "1", "yes")
        elif setting.type == "int":
            try:
                return int(setting.value)
            except (ValueError, TypeError):
                return default
        return setting.value

    @classmethod
    def set(cls, key, value, type="string"):
        setting = cls.query.filter_by(key=key).first()
        if not setting:
            setting = cls(key=key, type=type)
            db.session.add(setting)
        
        if type == "boolean":
            setting.value = "true" if value else "false"
        else:
            setting.value = str(value)
        db.session.commit()
        return setting
