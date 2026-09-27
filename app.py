import json
import secrets
from datetime import datetime

from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify

import db
import glicko
import sm2
from selection import build_session

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)  # regenerates each run; sessions don't need to survive restarts

db.init_db()


# ---------- helpers ----------

def get_subject_or_404(conn, subject_id):
    row = conn.execute("SELECT * FROM subjects WHERE id = ?", (subject_id,)).fetchone()
    return row


def topic_due_count(conn, topic_id):
    now_iso = datetime.utcnow().isoformat()
    row = conn.execute(
        "SELECT COUNT(*) c FROM questions WHERE topic_id = ? AND (next_eligible IS NULL OR next_eligible <= ?)",
        (topic_id, now_iso)
    ).fetchone()
    return row['c']


# ---------- dashboard ----------

@app.route('/')
def dashboard():
    conn = db.get_db()
    subjects = conn.execute("SELECT * FROM subjects ORDER BY name").fetchall()

    subject_data = []
    total_topics = total_questions = total_due = 0
    for s in subjects:
        topics = conn.execute("SELECT * FROM topics WHERE subject_id = ? ORDER BY name", (s['id'],)).fetchall()
        topic_rows = []
        for t in topics:
            qcount = conn.execute("SELECT COUNT(*) c FROM questions WHERE topic_id = ?", (t['id'],)).fetchone()['c']
            due = topic_due_count(conn, t['id'])
            total_topics += 1
            total_questions += qcount
            total_due += due
            pct = min(100, max(0, (t['rating'] - 1000) / 10))
            topic_rows.append({'row': t, 'qcount': qcount, 'due': due, 'pct': pct})
        subject_data.append({'row': s, 'topics': topic_rows})

    conn.close()
    return render_template(
        'dashboard.html',
        subject_data=subject_data,
        total_subjects=len(subjects),
        total_topics=total_topics,
        total_questions=total_questions,
        total_due=total_due,
    )


# ---------- manage: subjects & topics ----------

@app.route('/manage')
def manage():
    conn = db.get_db()
    subjects = conn.execute("SELECT * FROM subjects ORDER BY name").fetchall()
    topics = conn.execute(
        "SELECT topics.*, subjects.name AS subject_name FROM topics "
        "JOIN subjects ON subjects.id = topics.subject_id ORDER BY subjects.name, topics.name"
    ).fetchall()
    conn.close()
    return render_template('manage.html', subjects=subjects, topics=topics)


@app.route('/subjects/add', methods=['POST'])
def add_subject():
    name = request.form.get('name', '').strip()
    if not name:
        flash('Subject name cannot be empty.', 'error')
        return redirect(url_for('manage'))
    conn = db.get_db()
    try:
        conn.execute("INSERT INTO subjects (name) VALUES (?)", (name,))
        conn.commit()
        flash(f'Added subject "{name}".', 'success')
    except db.sqlite3.IntegrityError:
        flash(f'Subject "{name}" already exists.', 'error')
    conn.close()
    return redirect(url_for('manage'))


@app.route('/subjects/<int:subject_id>/delete', methods=['POST'])
def delete_subject(subject_id):
    conn = db.get_db()
    conn.execute("DELETE FROM subjects WHERE id = ?", (subject_id,))
    conn.commit()
    conn.close()
    flash('Subject deleted.', 'success')
    return redirect(url_for('manage'))


@app.route('/topics/add', methods=['POST'])
def add_topic():
    subject_id = request.form.get('subject_id')
    name = request.form.get('name', '').strip()
    if not subject_id or not name:
        flash('Pick a subject and enter a topic name.', 'error')
        return redirect(url_for('manage'))
    conn = db.get_db()
    try:
        conn.execute(
            "INSERT INTO topics (subject_id, name, rating, rd, last_update) VALUES (?, ?, ?, ?, ?)",
            (subject_id, name, glicko.DEFAULT_RATING, glicko.DEFAULT_RD, datetime.utcnow().isoformat())
        )
        conn.commit()
        flash(f'Added topic "{name}".', 'success')
    except db.sqlite3.IntegrityError:
        flash(f'That topic already exists in this subject.', 'error')
    conn.close()
    return redirect(url_for('manage'))


@app.route('/topics/<int:topic_id>/delete', methods=['POST'])
def delete_topic(topic_id):
    conn = db.get_db()
    conn.execute("DELETE FROM topics WHERE id = ?", (topic_id,))
    conn.commit()
    conn.close()
    flash('Topic deleted.', 'success')
    return redirect(url_for('manage'))


# ---------- manage: questions ----------

@app.route('/questions')
def questions():
    conn = db.get_db()
    topic_filter = request.args.get('topic_id', type=int)
    topics = conn.execute(
        "SELECT topics.*, subjects.name AS subject_name FROM topics "
        "JOIN subjects ON subjects.id = topics.subject_id ORDER BY subjects.name, topics.name"
    ).fetchall()

    if topic_filter:
        q_rows = conn.execute(
            "SELECT questions.*, topics.name AS topic_name FROM questions "
            "JOIN topics ON topics.id = questions.topic_id WHERE topics.id = ? ORDER BY questions.id DESC",
            (topic_filter,)
        ).fetchall()
    else:
        q_rows = conn.execute(
            "SELECT questions.*, topics.name AS topic_name FROM questions "
            "JOIN topics ON topics.id = questions.topic_id ORDER BY questions.id DESC LIMIT 100"
        ).fetchall()

    conn.close()
    return render_template('questions.html', topics=topics, questions=q_rows, topic_filter=topic_filter)


@app.route('/questions/add', methods=['POST'])
def add_question():
    topic_id = request.form.get('topic_id')
    text = request.form.get('text', '').strip()
    answer = request.form.get('answer', '').strip()
    if not topic_id or not text:
        flash('Pick a topic and enter question text.', 'error')
        return redirect(url_for('questions'))

    conn = db.get_db()
    avg_row = conn.execute("SELECT AVG(rating) a FROM questions WHERE topic_id = ?", (topic_id,)).fetchone()
    start_rating = avg_row['a'] if avg_row['a'] is not None else glicko.DEFAULT_RATING

    conn.execute(
        "INSERT INTO questions (topic_id, text, answer, rating, rd, last_update) VALUES (?, ?, ?, ?, ?, ?)",
        (topic_id, text, answer or None, start_rating, glicko.DEFAULT_RD, datetime.utcnow().isoformat())
    )
    conn.commit()
    conn.close()
    flash('Question added.', 'success')
    return redirect(url_for('questions', topic_id=topic_id))


@app.route('/questions/<int:question_id>/delete', methods=['POST'])
def delete_question(question_id):
    topic_id = request.form.get('topic_id', type=int)
    conn = db.get_db()
    conn.execute("DELETE FROM questions WHERE id = ?", (question_id,))
    conn.commit()
    conn.close()
    flash('Question deleted.', 'success')
    return redirect(url_for('questions', topic_id=topic_id))


# ---------- study ----------

@app.route('/study')
def study_setup():
    conn = db.get_db()
    subjects = conn.execute("SELECT * FROM subjects ORDER BY name").fetchall()
    conn.close()
    return render_template('study_setup.html', subjects=subjects)


@app.route('/study/start', methods=['POST'])
def study_start():
    subject_id = request.form.get('subject_id') or None
    count = request.form.get('count', type=int) or 10
    count = max(1, min(count, 50))

    conn = db.get_db()
    session_ids = build_session(conn, subject_id, count)
    conn.close()

    if not session_ids:
        flash('No questions available yet — add some topics and questions first.', 'error')
        return redirect(url_for('questions'))

    session['session_ids'] = session_ids
    session['session_index'] = 0
    session['session_scores'] = []
    session['session_subject_id'] = subject_id
    return redirect(url_for('study_session'))


def _question_payload(conn, qid, index, total):
    q = conn.execute(
        "SELECT questions.*, topics.name AS topic_name FROM questions "
        "JOIN topics ON topics.id = questions.topic_id WHERE questions.id = ?", (qid,)
    ).fetchone()
    return {
        'index': index,
        'total': total,
        'topic_name': q['topic_name'],
        'text': q['text'],
        'answer': q['answer'] or '',
        'rating': round(q['rating']),
    }


@app.route('/study/session')
def study_session():
    session_ids = session.get('session_ids')
    if not session_ids:
        return redirect(url_for('study_setup'))
    idx = session.get('session_index', 0)
    if idx >= len(session_ids):
        return redirect(url_for('study_complete'))

    conn = db.get_db()
    payload = _question_payload(conn, session_ids[idx], idx, len(session_ids))
    conn.close()
    return render_template('study_session.html', q=payload)


@app.route('/study/answer', methods=['POST'])
def study_answer():
    session_ids = session.get('session_ids')
    idx = session.get('session_index', 0)
    if not session_ids or idx >= len(session_ids):
        return jsonify({'error': 'no active session'}), 400

    score = float(request.json.get('score'))
    qid = session_ids[idx]
    now = datetime.utcnow()
    now_iso = now.isoformat()

    conn = db.get_db()
    q = conn.execute("SELECT * FROM questions WHERE id = ?", (qid,)).fetchone()
    t = conn.execute("SELECT * FROM topics WHERE id = ?", (q['topic_id'],)).fetchone()

    # --- topic (player) side: buffer into the rating period, flush at 5 ---
    pending = json.loads(t['pending_results'])
    pending.append([q['rating'], q['rd'], score])

    if len(pending) >= 5:
        days_elapsed = glicko.days_between(t['last_update'], now)
        new_t_rating, new_t_rd = glicko.update_rating(t['rating'], t['rd'], pending, days_elapsed)
        conn.execute(
            "UPDATE topics SET rating = ?, rd = ?, last_update = ?, pending_results = '[]' WHERE id = ?",
            (new_t_rating, new_t_rd, now_iso, t['id'])
        )
    else:
        conn.execute(
            "UPDATE topics SET pending_results = ? WHERE id = ?",
            (json.dumps(pending), t['id'])
        )

    # --- question side: immediate update, opponent = topic rating/RD as of this answer ---
    q_days_elapsed = glicko.days_between(q['last_update'], now)
    new_q_rating, new_q_rd = glicko.update_rating(
        q['rating'], q['rd'], [(t['rating'], t['rd'], 1 - score)], q_days_elapsed
    )

    # --- SM-2 scheduling for this question ---
    n, ef, interval, next_eligible = sm2.sm2_update(score, q['sm2_n'], q['sm2_ef'], q['sm2_interval'])

    conn.execute(
        "UPDATE questions SET rating = ?, rd = ?, last_update = ?, sm2_n = ?, sm2_ef = ?, "
        "sm2_interval = ?, next_eligible = ? WHERE id = ?",
        (new_q_rating, new_q_rd, now_iso, n, ef, interval, next_eligible, qid)
    )
    conn.execute(
        "INSERT INTO answer_log (question_id, topic_id, score, answered_at) VALUES (?, ?, ?, ?)",
        (qid, t['id'], score, now_iso)
    )
    conn.commit()

    idx += 1
    session['session_index'] = idx
    scores = session.get('session_scores', [])
    scores.append(score)
    session['session_scores'] = scores

    if idx >= len(session_ids):
        conn.close()
        return jsonify({'done': True})

    payload = _question_payload(conn, session_ids[idx], idx, len(session_ids))
    conn.close()
    return jsonify({'done': False, 'next': payload})


@app.route('/study/complete')
def study_complete():
    scores = session.get('session_scores', [])
    total = len(scores)
    avg = round(sum(scores) / total, 2) if total else 0
    correct = sum(1 for s in scores if s >= 1)
    minor = sum(1 for s in scores if 0 < s < 1)
    wrong = sum(1 for s in scores if s <= 0)

    session.pop('session_ids', None)
    session.pop('session_index', None)
    session.pop('session_scores', None)
    session.pop('session_subject_id', None)

    return render_template('study_complete.html', total=total, avg=avg, correct=correct, minor=minor, wrong=wrong)


if __name__ == '__main__':
    app.run(debug=True, port=5000)
