"""Application module for TimeTask School."""

from datetime import date, datetime
from flask import Flask, redirect, render_template, request, url_for
from models import Task, db

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///timetask.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)

with app.app_context():
    db.create_all()


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


@app.route("/")
def index():
    """Render the main dashboard with all tasks."""
    tasks = Task.query.all()
    return render_template("index.html", tasks=tasks)


@app.route("/add", methods=["GET", "POST"])
def add_task():
    """Handle adding a new task with strict format validation."""
    if request.method == "POST":
        title = request.form["title"]
        deadline_str = request.form["deadline"].strip()
        estimated_time = int(request.form["estimated_time"])

        try:
            deadline_date = datetime.strptime(deadline_str, "%Y-%m-%d").date()
        except ValueError:
            return (
                "<h1>Error de formato ❌</h1>"
                "<p>La fecha debe seguir estrictamente el modelo "
                "<strong>AAAA-MM-DD</strong> (Ejemplo: 2026-11-15).</p>"
                "<br><a href='/add'>Volver a intentarlo</a>",
                400,
            )

        priority = calculate_priority(estimated_time, deadline_date)

        new_task = Task(
            title=title,
            deadline=deadline_date,
            estimated_time=estimated_time,
            priority=priority,
        )

        db.session.add(new_task)
        db.session.commit()

        return redirect(url_for("index"))

    return render_template("add_task.html")


@app.route("/complete/<int:id>")
def complete_task(id):
    """Complete and remove a task by its ID."""
    task = Task.query.get_or_404(id)
    db.session.delete(task)
    db.session.commit()
    return redirect(url_for("index"))


@app.route("/delete/<int:id>")
def delete_task(id):
    """Delete a task by its ID."""
    task = Task.query.get_or_404(id)
    db.session.delete(task)
    db.session.commit()
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(debug=True)
