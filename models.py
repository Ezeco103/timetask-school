"""Database models for TimeTask School with permissions and Classrooms."""

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class_members = db.Table(
    "class_members",
    db.Column("user_id", db.Integer, db.ForeignKey("user.id"), primary_key=True),
    db.Column(
        "classroom_id", db.Integer, db.ForeignKey("classroom.id"), primary_key=True
    ),
)


class User(db.Model):
    """User model for secure personalized workspaces."""

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    tasks = db.relationship("Task", backref="owner", lazy=True)
    classes_created = db.relationship("Classroom", backref="creator", lazy=True)
    enrolled_classes = db.relationship(
        "Classroom",
        secondary=class_members,
        backref=db.backref("members", lazy=True),
    )


class Classroom(db.Model):
    """Classroom model for shared private spaces using a join code."""

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    code = db.Column(db.String(20), unique=True, nullable=False)
    creator_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    tasks = db.relationship(
        "ClassTask", backref="classroom", cascade="all, delete-orphan", lazy=True
    )


class Task(db.Model):
    """Personal Task model representing individual student assignments."""

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    subject = db.Column(db.String(100), nullable=False, default="General")
    deadline = db.Column(db.Date, nullable=False)
    estimated_time = db.Column(db.Integer, nullable=False)
    priority = db.Column(db.String(50), nullable=False)
    completed = db.Column(db.Boolean, default=False, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)


class ClassTask(db.Model):
    """Shared Task model inside a Classroom with strict permissions."""

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    subject = db.Column(db.String(100), nullable=False, default="General")
    deadline = db.Column(db.Date, nullable=False)
    estimated_time = db.Column(db.Integer, nullable=False)
    priority = db.Column(db.String(50), nullable=False)
    completed = db.Column(db.Boolean, default=False, nullable=False)
    classroom_id = db.Column(
        db.Integer, db.ForeignKey("classroom.id"), nullable=False
    )
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    author_name = db.Column(db.String(100), nullable=False)
