"""Standalone Flask demo of the AI quiz app — for live demos to managers/TLs.

Run with: python app.py
Automatically opens the quiz in the default browser.
"""
import functools
import os
import random
import re
import sys
import threading
import time
import uuid
import webbrowser

from flask import Flask, render_template, request, redirect, url_for, session, send_file, flash

# Reuse the AI question generator + timer config from the main project.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from quiz_engine import generate_mixed_ai_questions, generate_mixed_doc_questions, _question_hash, GENAI_AVAILABLE, PASS_PERCENTAGE  # noqa: E402
from database import SKILL_LEVELS  # noqa: E402
from runtime_paths import app_dir  # noqa: E402

import quiz_store
import admin_secrets

app = Flask(__name__)
app.secret_key = os.urandom(24).hex()

HOST = "0.0.0.0"  # listen on all interfaces so other laptops on the same network can connect
PORT = 5050

# Admin credentials — plain constants in admin_secrets.py.
ADMIN_PASSWORD = admin_secrets.get_admin_password()
EXPORT_PASSWORD = admin_secrets.get_export_password()


def admin_required(view):
    @functools.wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("is_admin"):
            return redirect(url_for("admin_login", next=request.path))
        return view(*args, **kwargs)
    return wrapped

# The quiz is fixed to AI topics — a topic is picked at random per session (not
# user-selected) so a long multi-laptop event spreads questions across a wide
# pool instead of hammering one topic+level combo and repeating questions.
AI_TOPICS = [
    "Prompt Engineering",
    "Machine Learning",
    "Deep Learning",
    "Generative AI",
    "Natural Language Processing",
    "Computer Vision",
    "Transformers and Large Language Models",
    "Retrieval-Augmented Generation (RAG)",
    "AI Agents",
    "MLOps and Model Deployment",
    "Responsible AI and Ethics",
    "Model Evaluation and Metrics",
    "Neural Network Architectures",
    "Reinforcement Learning",
    "Data Preprocessing and Feature Engineering",
]

NUM_QUESTIONS = 10          # 5 AI-general + 5 from Doc folder
AI_QUESTIONS = 5
DOC_QUESTIONS = 5
PER_QUESTION_SEC = 30       # each question is shown for 30 seconds max
QUIZ_DURATION_SEC = NUM_QUESTIONS * PER_QUESTION_SEC
DOCUMENTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Doc")

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

        if quiz_store.ntid_has_attempted(ntid):
            errors["ntid"] = "🚫 Sneaky! This NTID already took the quiz. One shot, one chance — no second bites!"
            return render_template("home.html", errors=errors, form=request.form)

        sid = str(uuid.uuid4())
        # level=0 is a sentinel meaning "mixed" — no user selection needed
        _SESSIONS[sid] = {"name": name, "ntid": ntid, "topic": random.choice(AI_TOPICS), "level": 0}
        session["sid"] = sid
        return redirect(url_for("loading"))

    session.pop("sid", None)
    return render_template("home.html", errors={}, form={})


@app.route("/loading")
def loading():
    qs = _get_quiz_session()
    if qs is None or "topic" not in qs:
        return redirect(url_for("home"))
    return render_template("waiting.html", user=qs)


@app.route("/generate")
def generate():
    """Called by the waiting page via fetch(); generates questions then signals ready."""
    qs = _get_quiz_session()
    if qs is None or "topic" not in qs:
        return {"ok": False, "error": "session expired"}, 400

    if not GENAI_AVAILABLE:
        return {"ok": False, "error": "AI service is not configured (missing API key)."}, 500

    ai_questions = []
    doc_questions = []
    ai_error = doc_error = None

    def _gen_ai():
        nonlocal ai_error
        try:
            ai_questions.extend(generate_mixed_ai_questions(qs["topic"], AI_QUESTIONS))
        except Exception as exc:  # noqa: BLE001
            ai_error = exc

    def _gen_doc():
        nonlocal doc_error
        try:
            doc_questions.extend(generate_mixed_doc_questions(DOCUMENTS_DIR, DOC_QUESTIONS))
        except Exception as exc:  # noqa: BLE001
            doc_error = exc

    # 2 parallel calls — one to AI general knowledge, one grounded in docs
    ai_thread = threading.Thread(target=_gen_ai)
    doc_thread = threading.Thread(target=_gen_doc)
    ai_thread.start()
    doc_thread.start()
    ai_thread.join()
    doc_thread.join()

    if ai_error and doc_error:
        return {"ok": False, "error": str(ai_error)}, 500
    if ai_error:
        return {"ok": False, "error": str(ai_error)}, 500
    if doc_error:
        return {"ok": False, "error": f"Doc questions failed: {doc_error}"}, 500

    # Dedup doc questions against AI questions
    ai_hashes = {_question_hash(q["question"]) for q in ai_questions}
    doc_questions = [q for q in doc_questions if _question_hash(q["question"]) not in ai_hashes]

    combined = ai_questions + doc_questions
    random.shuffle(combined)

    qs["questions"] = combined
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
        level_name="Mixed",
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

    record = quiz_store.save_attempt(
        qs["name"], qs["ntid"], qs["topic"], "Mixed",
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


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    error = None
    if request.method == "POST":
        if ADMIN_PASSWORD and request.form.get("password") == ADMIN_PASSWORD:
            session["is_admin"] = True
            return redirect(request.args.get("next") or url_for("admin"))
        error = "Incorrect password." if ADMIN_PASSWORD else (
            "Admin password is not configured in admin_secrets.py — admin login is disabled."
        )
    return render_template("admin_login.html", error=error)


@app.route("/admin/logout")
def admin_logout():
    session.pop("is_admin", None)
    return redirect(url_for("admin_login"))


@app.route("/admin")
@admin_required
def admin():
    attempts = quiz_store.get_all_attempts()
    # highest percentage first; tie-break on shorter duration
    attempts.sort(key=lambda a: (-a["percentage"], a["duration_sec"]))
    return render_template("admin.html", attempts=attempts)


@app.route("/admin/reset/<ntid>", methods=["POST"])
@admin_required
def admin_reset_attempt(ntid):
    quiz_store.delete_attempt_by_ntid(ntid)
    flash(f"Attempt for NTID '{ntid}' has been reset. They may now retake the quiz.", "success")
    return redirect(url_for("admin"))


@app.route("/admin/apikey", methods=["POST"])
@admin_required
def admin_update_apikey():
    new_key = request.form.get("api_key", "").strip()
    if not new_key:
        flash("API key cannot be empty.", "error")
        return redirect(url_for("admin"))
    try:
        from quiz_engine import persist_api_key  # noqa: PLC0415
        persist_api_key(new_key)
        flash("API key updated and saved successfully.", "success")
    except Exception as exc:  # noqa: BLE001
        flash(f"Failed to save API key: {exc}", "error")
    return redirect(url_for("admin"))


@app.route("/admin/download")
@admin_required
def admin_download():
    if not EXPORT_PASSWORD:
        return "Export password is not configured in admin_secrets.py — export is disabled.", 500
    encrypted = quiz_store.export_encrypted(EXPORT_PASSWORD)
    return send_file(
        encrypted, as_attachment=True, download_name="quiz_results.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


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
