"""
Database models for Instagram Transcriber.
Uses SQLAlchemy with SQLite.
"""

from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class User(UserMixin, db.Model):
    """User model for authentication."""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    name = db.Column(db.String(100), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    phone_carrier = db.Column(db.String(20), nullable=True)  # For SMS gateway
    whatsapp = db.Column(db.String(20), nullable=True)  # WhatsApp number with country code
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship to transcripts
    transcripts = db.relationship('Transcript', backref='user', lazy='dynamic')
    
    def set_password(self, password):
        """Hash and set password."""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check password against hash."""
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.email}>'


class Transcript(db.Model):
    """Transcript model to store history."""
    __tablename__ = 'transcripts'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    instagram_url = db.Column(db.String(500), nullable=False)
    transcript_text = db.Column(db.Text, nullable=False)
    language = db.Column(db.String(50), nullable=True)
    line_count = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Delivery tracking
    sent_email = db.Column(db.Boolean, default=False)
    sent_sms = db.Column(db.Boolean, default=False)
    sent_whatsapp = db.Column(db.Boolean, default=False)
    
    def __repr__(self):
        return f'<Transcript {self.id} by User {self.user_id}>'
