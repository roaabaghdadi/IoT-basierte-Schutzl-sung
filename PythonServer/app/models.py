

from app import db
from datetime import datetime

class SensorData(db.Model):

    id = db.Column(db.Integer, primary_key=True)
    sensor_type = db.Column(db.String(50), nullable=False)
    value = db.Column(db.Float, nullable=False)
    unit = db.Column(db.String(10), nullable=False)
    status = db.Column(db.String(20), default='normal')
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)

    def __repr__(self):
        return f'<SensorData {self.sensor_type}: {self.value} {self.unit}>'

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)

    def __repr__(self):
        return f'<User {self.email}>'


class Alert(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), nullable=True)
    url = db.Column(db.String(500), nullable=True)
    threshold_value = db.Column(db.Float, nullable=False)
    sensor_type = db.Column(db.String(50), nullable=False)
    alert_type = db.Column(db.String(20), nullable=False, default='email')
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    def __repr__(self):
        if self.alert_type == 'email':
            return f'<Email Alert for {self.sensor_type} on {self.email}>'
        else:
            return f'<URL Alert for {self.sensor_type} to {self.url}>'