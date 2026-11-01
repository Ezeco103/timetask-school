"""Database models for TimeTask School."""

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Task(db.Model):
    """Task model representing student homework and activities."""

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    deadline = db.Column(db.String(100), nullable=False)
    estimated_time = db.Column(db.Integer, nullable=False)
    priority = db.Column(db.String(50), nullable=False, default="Media")

    def __repr__(self):
        """Return string representation of the task."""
        return f"<Task {self.title}>"
