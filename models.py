from datetime import datetime
from app import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    password_hash = db.Column(db.String(256))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship to votes
    votes = db.relationship('Vote', backref='voter', lazy='dynamic')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Vote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    food_type = db.Column(db.String(20), nullable=False)  # 'pizza' or 'burger'
    vote_id = db.Column(db.String(100), nullable=False)  # User-provided ID for tracking
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    gemini_response = db.Column(db.Text)  # Store the unique response from Gemini
    
    def __repr__(self):
        return f'<Vote {self.id}: {self.food_type} by {self.voter.username}>'

class ResponseHistory(db.Model):
    """Track used responses to ensure uniqueness"""
    id = db.Column(db.Integer, primary_key=True)
    response_hash = db.Column(db.String(64), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
