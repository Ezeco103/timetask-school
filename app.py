"""Application module for TimeTask School with full classroom validation and editing."""

import asyncio
from datetime import date, datetime
import os
import random
import string
import edge_tts
from flask import Flask, redirect, render_template, request, session, url_for
from models import ClassTask, Classroom, Task, User, db

app = Flask(__name__)
app.secret_key = "timetask_school_final_key"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///timetask.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)

with app.app_context():
    db.create_all()
    os.makedirs("static", exist_ok=True)


def calculate_priority(estimated_time, deadline_date):
    """Calculate task priority based on estimated time and days left."""
    today = date.today()
    days_left = (deadline_date - today).days

    if estimated_time > 60 or days_left <= 1:
        return "Alta"
    elif 30 <= estimated_time <= 60 or days_left <= 3:
        return "Media"
    else:
        return "Baja"


def generate_class_code():
    """Generate a random 6-character alphanumeric code for classrooms."""
    letters_digits = string.ascii_uppercase + string.digits
    return "".join(random.choice(letters_digits) for _ in range(6))


@app.route("/login", methods=["GET", "POST"])
def login():
    """Handle professional user login."""
    error = None
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]

        user = User.query.filter_by(username=username).first()
        if user and user.password == password:
            session["user_id"] = user.id
            session["username"] = user.username
            return redirect(url_for("index"))
        else:
            error = "Usuario o contraseña incorrectos."

    return render_template("login.html", error=error)


@app.route("/register", methods=["GET", "POST"])
def register():
    """Handle professional user registration."""
    error = None
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]

        if not username or not password:
            error = "Todos los campos son obligatorios."
        elif User.query.filter_by(username=username).first():
            error = "El nombre de usuario ya está en uso."
        else:
            new_user = User(username=username, password=password)
            db.session.add(new_user)
            db.session.commit()
            session["user_id"] = new_user.id
            session["username"] = new_user.username
            return redirect(url_for("index"))

    return render_template("register.html", error=error)


@app.route("/logout")
def logout():
    """Log out current user and clear session."""
    session.clear()
    return redirect(url_for("login"))


@app.route("/")
def index():
    """Render personal dashboard with safe session validation."""
    if "user_id" not in session:
        return redirect(url_for("login"))

    user = User.query.get(session["user_id"])
    if not user:
        session.clear()
        return redirect(url_for("login"))

    today = date.today()
    priority_filter = request.args.get("priority")
    search_query = request.args.get("search", "").strip()

    pending_query = Task.query.filter_by(
        user_id=user.id, completed=False
    ).filter(Task.deadline >= today)

    if priority_filter in ["Alta", "Media", "Baja"]:
        pending_query = pending_query.filter_by(priority=priority_filter)

    if search_query:
        pending_query = pending_query.filter(
            Task.title.ilike(f"%{search_query}%")
        )

    pending_tasks = pending_query.order_by(Task.deadline.asc()).all()

    expired_tasks = Task.query.filter_by(
        user_id=user.id, completed=False
    ).filter(Task.deadline < today).order_by(Task.deadline.asc()).all()

    completed_tasks = Task.query.filter_by(
        user_id=user.id, completed=True
    ).order_by(Task.deadline.desc()).all()

    total_tasks = Task.query.filter_by(user_id=user.id).count()
    total_completed = Task.query.filter_by(
        user_id=user.id, completed=True
    ).count()
    progress_percentage = (
        int((total_completed / total_tasks) * 100) if total_tasks > 0 else 0
    )

    return render_template(
        "index.html",
        user=user,
        tasks=pending_tasks,
        expired_tasks=expired_tasks,
        completed_tasks=completed_tasks,
        current_filter=priority_filter,
        search_query=search_query,
        today=today,
        total_tasks=total_tasks,
        total_completed=total_completed,
        progress_percentage=progress_percentage,
    )


@app.route("/add", methods=["GET", "POST"])
def add_task():
    """Handle adding a new personal task."""
    if "user_id" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":
        title = request.form["title"]
        subject = request.form["subject"].strip() or "General"
        deadline_str = request.form["deadline"].strip()
        estimated_time = int(request.form["estimated_time"])

        try:
            deadline_date = datetime.strptime(deadline_str, "%Y-%m-%d").date()
        except ValueError:
            return render_template(
                "error.html",
                error_message="La fecha debe seguir el formato AAAA-MM-DD.",
                back_url="/add",
            ), 400

        if deadline_date < date.today():
            return render_template(
                "error.html",
                error_message="No puedes programar tareas en fechas pasadas.",
                back_url="/add",
            ), 400

        priority = calculate_priority(estimated_time, deadline_date)
        new_task = Task(
            title=title,
            subject=subject,
            deadline=deadline_date,
            estimated_time=estimated_time,
            priority=priority,
            user_id=session["user_id"],
        )
        db.session.add(new_task)
        db.session.commit()
        return redirect(url_for("index"))

    return render_template("add_task.html")


@app.route("/edit/<int:id>", methods=["GET", "POST"])
def edit_task(id):
    """Handle editing an existing personal task."""
    if "user_id" not in session:
        return redirect(url_for("login"))
    task = Task.query.filter_by(id=id, user_id=session["user_id"]).first_or_404()

    if request.method == "POST":
        task.title = request.form["title"]
        task.subject = request.form["subject"].strip() or "General"
        deadline_str = request.form["deadline"].strip()
        task.estimated_time = int(request.form["estimated_time"])

        try:
            task.deadline = datetime.strptime(deadline_str, "%Y-%m-%d").date()
        except ValueError:
            return render_template(
                "error.html",
                error_message="Formato de fecha inválido.",
                back_url=f"/edit/{id}",
            ), 400

        if task.deadline < date.today():
            return render_template(
                "error.html",
                error_message="No puedes poner fechas pasadas.",
                back_url=f"/edit/{id}",
            ), 400

        task.priority = calculate_priority(task.estimated_time, task.deadline)
        db.session.commit()
        return redirect(url_for("index"))

    return render_template("edit_task.html", task=task)


@app.route("/speak")
def speak_tasks():
    """Generate audio summary for personal tasks."""
    if "user_id" not in session:
        return redirect(url_for("login"))
    user = User.query.get(session["user_id"])
    today = date.today()
    tasks = Task.query.filter_by(
        user_id=user.id, completed=False
    ).filter(Task.deadline >= today).all()

    if not tasks:
        text_to_read = "No tienes tareas pendientes para hoy o el futuro."
    else:
        text_to_read = "Aquí tienes tus tareas pendientes. "
        for t in tasks:
            urgency_text = (
                "¡Se presenta hoy!"
                if t.deadline == today
                else f"Plazo {t.deadline}"
            )
            text_to_read += (
                f"Materia {t.subject}, tarea: {t.title}, "
                f"con {urgency_text}, prioridad {t.priority}. "
            )

    os.makedirs("static", exist_ok=True)
    audio_path = os.path.join("static", "tasks_speech.mp3")

    async def generate_audio():
        communicate = edge_tts.Communicate(text_to_read, "es-ES-AlvaroNeural")
        await communicate.save(audio_path)

    asyncio.run(generate_audio())
    return redirect(url_for("index", play_audio="1"))


@app.route("/complete/<int:id>")
def complete_task(id):
    """Mark personal task as completed."""
    if "user_id" not in session:
        return redirect(url_for("login"))
    task = Task.query.filter_by(id=id, user_id=session["user_id"]).first_or_404()
    task.completed = True
    db.session.commit()
    return redirect(url_for("index"))


@app.route("/delete/<int:id>")
def delete_task(id):
    """Delete personal task."""
    if "user_id" not in session:
        return redirect(url_for("login"))
    task = Task.query.filter_by(id=id, user_id=session["user_id"]).first_or_404()
    db.session.delete(task)
    db.session.commit()
    return redirect(url_for("index"))


# --- RUTAS DE CLASES ---


@app.route("/classes")
def classes_dashboard():
    """Render list of classes and handle invalid code notification."""
    if "user_id" not in session:
        return redirect(url_for("login"))
    user = User.query.get(session["user_id"])
    error = request.args.get("error")
    return render_template(
        "classes.html",
        user=user,
        created_classes=user.classes_created,
        enrolled_classes=user.enrolled_classes,
        error=error,
    )


@app.route("/create-class", methods=["POST"])
def create_class():
    """Create a new classroom."""
    if "user_id" not in session:
        return redirect(url_for("login"))
    name = request.form["class_name"].strip()
    if name:
        code = generate_class_code()
        while Classroom.query.filter_by(code=code).first():
            code = generate_class_code()

        new_class = Classroom(
            name=name, code=code, creator_id=session["user_id"]
        )
        db.session.add(new_class)
        db.session.commit()
    return redirect(url_for("classes_dashboard"))


@app.route("/join-class", methods=["POST"])
def join_class():
    """Join classroom via code and handle invalid codes."""
    if "user_id" not in session:
        return redirect(url_for("login"))
    code = request.form["class_code"].strip().upper()
    user = User.query.get(session["user_id"])
    classroom = Classroom.query.filter_by(code=code).first()

    if not classroom:
        return redirect(
            url_for("classes_dashboard", error="¡Código no válido! La clase no existe.")
        )

    if classroom.creator_id == user.id:
        return redirect(
            url_for("classes_dashboard", error="Eres el creador de esta clase.")
        )

    if classroom not in user.enrolled_classes:
        user.enrolled_classes.append(classroom)
        db.session.commit()

    return redirect(url_for("classes_dashboard"))


@app.route("/class/<int:class_id>")
def view_class(class_id):
    """View classroom workspace, ordered tasks, and expired ones."""
    if "user_id" not in session:
        return redirect(url_for("login"))
    user = User.query.get(session["user_id"])
    classroom = Classroom.query.get_or_404(class_id)

    if classroom.creator_id != user.id and classroom not in user.enrolled_classes:
        return redirect(url_for("classes_dashboard"))

    today = date.today()
    # Ordenadas por urgencia (deadline asc)
    pending_tasks = ClassTask.query.filter_by(
        classroom_id=classroom.id, completed=False
    ).filter(ClassTask.deadline >= today).order_by(ClassTask.deadline.asc()).all()

    expired_tasks = ClassTask.query.filter_by(
        classroom_id=classroom.id, completed=False
    ).filter(ClassTask.deadline < today).order_by(ClassTask.deadline.asc()).all()

    completed_tasks = ClassTask.query.filter_by(
        classroom_id=classroom.id, completed=True
    ).order_by(ClassTask.deadline.desc()).all()

    is_creator = classroom.creator_id == user.id

    return render_template(
        "classroom.html",
        classroom=classroom,
        tasks=pending_tasks,
        expired_tasks=expired_tasks,
        completed_tasks=completed_tasks,
        today=today,
        is_creator=is_creator,
        current_user_id=user.id,
    )


@app.route("/class/<int:class_id>/delete", methods=["POST"])
def delete_classroom(class_id):
    """Allow creator to completely delete a classroom."""
    if "user_id" not in session:
        return redirect(url_for("login"))
    classroom = Classroom.query.get_or_404(class_id)
    if classroom.creator_id == session["user_id"]:
        db.session.delete(classroom)
        db.session.commit()
    return redirect(url_for("classes_dashboard"))


@app.route("/class/<int:class_id>/remove-member/<int:user_id>", methods=["POST"])
def remove_member(class_id, user_id):
    """Allow only the classroom creator to remove a member."""
    if "user_id" not in session:
        return redirect(url_for("login"))
    classroom = Classroom.query.get_or_404(class_id)

    if classroom.creator_id == session["user_id"]:
        member_to_remove = User.query.get_or_404(user_id)
        if member_to_remove in classroom.members:
            classroom.members.remove(member_to_remove)
            db.session.commit()

    return redirect(url_for("view_class", class_id=class_id))


@app.route("/class/<int:class_id>/add", methods=["POST"])
def add_class_task(class_id):
    """Add a shared task to classroom with strict date validation."""
    if "user_id" not in session:
        return redirect(url_for("login"))
    user = User.query.get(session["user_id"])
    classroom = Classroom.query.get_or_404(class_id)

    if classroom.creator_id != user.id and classroom not in user.enrolled_classes:
        return redirect(url_for("classes_dashboard"))

    title = request.form["title"]
    subject = request.form["subject"].strip() or "General"
    deadline_str = request.form["deadline"].strip()
    estimated_time = int(request.form["estimated_time"])

    try:
        deadline_date = datetime.strptime(deadline_str, "%Y-%m-%d").date()
    except ValueError:
        return render_template(
            "error.html",
            error_message="Formato de fecha inválido.",
            back_url=f"/class/{class_id}",
        ), 400

    if deadline_date < date.today():
        return render_template(
            "error.html",
            error_message="No puedes programar tareas en fechas pasadas para la clase.",
            back_url=f"/class/{class_id}",
        ), 400

    priority = calculate_priority(estimated_time, deadline_date)
    new_task = ClassTask(
        title=title,
        subject=subject,
        deadline=deadline_date,
        estimated_time=estimated_time,
        priority=priority,
        classroom_id=classroom.id,
        user_id=user.id,
        author_name=user.username,
    )
    db.session.add(new_task)
    db.session.commit()
    return redirect(url_for("view_class", class_id=class_id))


@app.route("/class/task-edit/<int:task_id>", methods=["GET", "POST"])
def edit_class_task(task_id):
    """Allow only task author or room creator to edit class task."""
    if "user_id" not in session:
        return redirect(url_for("login"))
    task = ClassTask.query.get_or_404(task_id)
    classroom = Classroom.query.get_or_404(task.classroom_id)

    # Validar permisos: solo el creador de la clase o el autor de la tarea
    if classroom.creator_id != session["user_id"] and task.user_id != session["user_id"]:
        return redirect(url_for("view_class", class_id=classroom.id))

    if request.method == "POST":
        task.title = request.form["title"]
        task.subject = request.form["subject"].strip() or "General"
        deadline_str = request.form["deadline"].strip()
        task.estimated_time = int(request.form["estimated_time"])

        try:
            task.deadline = datetime.strptime(deadline_str, "%Y-%m-%d").date()
        except ValueError:
            return render_template(
                "error.html",
                error_message="Formato de fecha inválido.",
                back_url=f"/class/task-edit/{task_id}",
            ), 400

        if task.deadline < date.today():
            return render_template(
                "error.html",
                error_message="No puedes poner fechas pasadas.",
                back_url=f"/class/task-edit/{task_id}",
            ), 400

        task.priority = calculate_priority(task.estimated_time, task.deadline)
        db.session.commit()
        return redirect(url_for("view_class", class_id=classroom.id))

    return render_template("edit_class_task.html", task=task, classroom=classroom)


@app.route("/class/task-complete/<int:task_id>")
def complete_class_task(task_id):
    """Mark class task as completed with strict permission check."""
    if "user_id" not in session:
        return redirect(url_for("login"))
    task = ClassTask.query.get_or_404(task_id)
    classroom = Classroom.query.get_or_404(task.classroom_id)

    if classroom.creator_id == session["user_id"] or task.user_id == session["user_id"]:
        task.completed = True
        db.session.commit()

    return redirect(url_for("view_class", class_id=task.classroom_id))


@app.route("/class/task-delete/<int:task_id>")
def delete_class_task(task_id):
    """Delete class task with strict permission check."""
    if "user_id" not in session:
        return redirect(url_for("login"))
    task = ClassTask.query.get_or_404(task_id)
    classroom = Classroom.query.get_or_404(task.classroom_id)
    class_id = task.classroom_id

    if classroom.creator_id == session["user_id"] or task.user_id == session["user_id"]:
        db.session.delete(task)
        db.session.commit()

    return redirect(url_for("view_class", class_id=class_id))


if __name__ == "__main__":
    app.run(debug=True)
