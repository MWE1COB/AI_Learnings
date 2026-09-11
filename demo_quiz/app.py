"""Standalone Flask demo of the AI quiz app — for live demos to managers/TLs.

Run with: python app.py
Automatically opens the quiz in the default browser.
"""
import os
import re
import sys
import threading
import time
import uuid
import webbrowser

from flask import Flask, render_template, request, redirect, url_for, session, send_file, flash

# Reuse the AI question generator + timer config from the main project.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from quiz_engine import generate_quiz_with_ai, GENAI_AVAILABLE, PASS_PERCENTAGE  # noqa: E402
from database import SKILL_LEVELS  # noqa: E402
from runtime_paths import app_dir  # noqa: E402

import quiz_store

app = Flask(__name__)
app.secret_key = os.urandom(24).hex()

HOST = "0.0.0.0"  # listen on all interfaces so other laptops on the same network can connect
PORT = 5050

# Quiz is fixed to AI topics only — the user no longer picks a topic.
AI_TOPICS = ["Prompt Engineering", "Machine Learning", "Deep Learning", "Generative AI"]
AI_TOPIC_LABEL = "Artificial Intelligence (" + ", ".join(AI_TOPICS) + ")"

NUM_QUESTIONS = 5  # kept short for live demos
PER_QUESTION_SEC = 30  # each question is shown for 30 seconds max
QUIZ_DURATION_SEC = NUM_QUESTIONS * PER_QUESTION_SEC  # fixed 2:30 quiz for demos
DOCUMENTS_DIR = os.path.join(app_dir(), "documents")

# In-memory store for in-progress quiz sessions, keyed by a server-side session id.
# (Keeps the browser cookie small — only the session id is stored client-side.)
_SESSIONS = {}


def _get_quiz_session():
    sid = session.get("sid")
    if not sid or sid not in _SESSIONS:
        return None
    return _SESSIONS[sid]


@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        ntid = request.form.get("ntid", "").strip()

        errors = {}
        if not name:
            errors["name"] = "Name is required."
        elif not re.match(r"^[A-Za-z ]+$", name):
            errors["name"] = "Name must contain letters only."

        if not ntid:
            errors["ntid"] = "NTID is required."
        elif not re.match(r"^[A-Za-z0-9]+$", ntid):
            errors["ntid"] = "NTID must be alphanumeric."

        if errors:
            return render_template("home.html", errors=errors, form=request.form)

        sid = str(uuid.uuid4())
        _SESSIONS[sid] = {"name": name, "ntid": ntid, "topic": AI_TOPIC_LABEL}
        session["sid"] = sid
        return redirect(url_for("level"))

    session.pop("sid", None)
    return render_template("home.html", errors={}, form={})


@app.route("/level", methods=["GET", "POST"])
def level():
    qs = _get_quiz_session()
    if qs is None or "topic" not in qs:
        return redirect(url_for("home"))

    if request.method == "POST":
        level_id = request.form.get("level")
        if level_id not in ("1", "2", "3", "4"):
            flash("Please select a valid level.")
            return redirect(url_for("level"))
        qs["level"] = int(level_id)
        return redirect(url_for("loading"))

    return render_template("level.html", levels=SKILL_LEVELS, user=qs)


@app.route("/loading")
def loading():
    qs = _get_quiz_session()
    if qs is None or "level" not in qs:
        return redirect(url_for("home"))
    return render_template("waiting.html", user=qs)


@app.route("/generate")
def generate():
    """Called by the waiting page via fetch(); generates questions then signals ready."""
    qs = _get_quiz_session()
    if qs is None or "level" not in qs:
        return {"ok": False, "error": "session expired"}, 400

    if not GENAI_AVAILABLE:
        return {"ok": False, "error": "AI service is not configured (missing API key)."}, 500

    try:
        questions = generate_quiz_with_ai(
            qs["topic"], qs["level"], NUM_QUESTIONS, single_batch=True, documents_dir=DOCUMENTS_DIR
        )
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)}, 500

    qs["questions"] = questions
    qs["duration_sec"] = QUIZ_DURATION_SEC
    qs["start_time"] = time.time()
    return {"ok": True}


@app.route("/quiz")
def quiz():
    qs = _get_quiz_session()
    if qs is None or "questions" not in qs:
        return redirect(url_for("home"))
    return render_template(
        "quiz.html",
        user=qs,
        questions=qs["questions"],
        duration_sec=qs["duration_sec"],
        per_question_sec=PER_QUESTION_SEC,
        level_name=SKILL_LEVELS.get(qs["level"], "Beginner"),
    )


@app.route("/submit", methods=["POST"])
def submit():
    qs = _get_quiz_session()
    if qs is None or "questions" not in qs:
        return redirect(url_for("home"))

    questions = qs["questions"]
    score = 0
    review = []
    for i, q in enumerate(questions):
        answer = request.form.get(f"q{i}")
        selected = int(answer) if answer is not None else None
        is_correct = selected is not None and selected == q["answer"]
        if is_correct:
            score += 1
        review.append({
            "question": q["question"],
            "options": q["options"],
            "correct_answer": q["answer"],
            "selected_answer": selected,
            "is_correct": is_correct,
        })

    duration = int(time.time() - qs.get("start_time", time.time()))
    level_name = SKILL_LEVELS.get(qs["level"], "Beginner")

    record = quiz_store.save_attempt(
        qs["name"], qs["ntid"], qs["topic"], level_name,
        score, len(questions), duration,
    )

    passed = record["percentage"] >= PASS_PERCENTAGE
    next_level_name = SKILL_LEVELS.get(qs["level"] + 1) if passed else None

    record["passed"] = passed
    record["next_level"] = next_level_name

    qs["result"] = record
    qs["review"] = review
    return redirect(url_for("result"))


@app.route("/result")
def result():
    qs = _get_quiz_session()
    if qs is None or "result" not in qs:
        return redirect(url_for("home"))
    record = qs["result"]
    review = qs.get("review", [])
    _SESSIONS.pop(session.get("sid"), None)
    session.pop("sid", None)
    return render_template("result.html", record=record, review=review, pass_percentage=PASS_PERCENTAGE)


@app.route("/admin")
def admin():
    attempts = quiz_store.get_all_attempts()
    return render_template("admin.html", attempts=attempts)


@app.route("/admin/download")
def admin_download():
    quiz_store._ensure_workbook()
    return send_file(quiz_store.EXCEL_PATH, as_attachment=True, download_name="quiz_results.xlsx")


def _open_browser():
    webbrowser.open(f"http://127.0.0.1:{PORT}/")


def _local_ip():
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"
    finally:
        s.close()


if __name__ == "__main__":
    threading.Timer(1.0, _open_browser).start()
    print(f" * Share this URL with others on the same Wi-Fi/network: http://{_local_ip()}:{PORT}/")
    app.run(host=HOST, port=PORT, debug=False)
