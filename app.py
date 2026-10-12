"""Flask-приложение: образовательный квиз Information Security Awareness."""

import random

from flask import Flask, abort, redirect, render_template, request, session, url_for

from questions import QUESTIONS

# Сколько вопросов задаётся за одно прохождение
SESSION_SIZE = 30

app = Flask(__name__)
app.secret_key = "change-me-in-production-please"

# Быстрый доступ к вопросу по id
QUESTIONS_BY_ID = {q["id"]: q for q in QUESTIONS}


def build_session():
    """Формирует новую случайную выборку вопросов для прохождения."""
    size = min(SESSION_SIZE, len(QUESTIONS))
    picked = random.sample(QUESTIONS, size)
    session["question_ids"] = [q["id"] for q in picked]
    session["index"] = 0
    session["answers"] = []  # список dict: id, chosen, correct, is_right


def current_question():
    """Возвращает текущий вопрос или None, если прохождение закончено."""
    ids = session.get("question_ids", [])
    idx = session.get("index", 0)
    if idx >= len(ids):
        return None
    return QUESTIONS_BY_ID.get(ids[idx])


@app.route("/")
@app.route("/index")
def index():
    return render_template("index.html", total_questions=len(QUESTIONS), session_size=min(SESSION_SIZE, len(QUESTIONS)))


@app.route("/start", methods=["GET", "POST"])
def start():
    build_session()
    return redirect(url_for("question"))


@app.route("/question", methods=["GET"])
def question():
    q = current_question()
    if q is None:
        return redirect(url_for("result"))

    ids = session["question_ids"]
    idx = session["index"]
    progress = {
        "number": idx + 1,
        "total": len(ids),
        "percent": int(round((idx) / len(ids) * 100)),
    }
    return render_template("question.html", question=q, progress=progress)


@app.route("/answer", methods=["POST"])
def answer():
    q = current_question()
    if q is None:
        return redirect(url_for("result"))

    raw = request.form.get("choice")
    if raw is None:
        return render_template("error.html", message="Вы не выбрали вариант ответа."), 400
    try:
        chosen = int(raw)
    except ValueError:
        return render_template("error.html", message="Некорректный вариант ответа."), 400

    if chosen < 0 or chosen >= len(q["options"]):
        return render_template("error.html", message="Вариант ответа вне диапазона."), 400

    is_right = chosen == q["correct"]
    session["answers"].append(
        {
            "id": q["id"],
            "chosen": chosen,
            "correct": q["correct"],
            "is_right": is_right,
        }
    )
    session.modified = True

    ids = session["question_ids"]
    idx = session["index"]
    progress = {
        "number": idx + 1,
        "total": len(ids),
        "percent": int(round((idx + 1) / len(ids) * 100)),
    }

    is_last = (idx + 1) >= len(ids)
    return render_template(
        "feedback.html",
        question=q,
        chosen=chosen,
        is_right=is_right,
        progress=progress,
        is_last=is_last,
    )


@app.route("/next", methods=["POST"])
def next_question():
    ids = session.get("question_ids", [])
    idx = session.get("index", 0)
    session["index"] = idx + 1
    session.modified = True

    if session["index"] >= len(ids):
        return redirect(url_for("result"))
    return redirect(url_for("question"))


@app.route("/result")
def result():
    answers = session.get("answers", [])
    if not answers:
        return redirect(url_for("index"))

    total = len(answers)
    correct_count = sum(1 for a in answers if a["is_right"])
    percent = int(round(correct_count / total * 100)) if total else 0

    mistakes = []
    for a in answers:
        if not a["is_right"]:
            q = QUESTIONS_BY_ID.get(a["id"])
            if q is None:
                continue
            mistakes.append(
                {
                    "question": q,
                    "chosen_text": q["options"][a["chosen"]],
                    "correct_text": q["options"][a["correct"]],
                    "chosen": a["chosen"],
                    "correct": a["correct"],
                }
            )

    return render_template(
        "result.html",
        total=total,
        correct_count=correct_count,
        percent=percent,
        mistakes=mistakes,
    )


@app.route("/restart", methods=["POST"])
def restart():
    session.clear()
    return redirect(url_for("index"))


@app.errorhandler(404)
def not_found(_e):
    return render_template("error.html", message="Страница не найдена."), 404


if __name__ == "__main__":
    app.run(debug=True, port=5001)
