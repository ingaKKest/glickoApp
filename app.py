import json
import os
import secrets
import uuid
from datetime import datetime

from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash

import db
import glicko
import sm2
from selection import pick_next_question
from labels import rating_label, confidence_label
from auth import login_required

app = Flask(__name__)

# Persist the secret key across restarts so logins survive a server restart.
SECRET_KEY_PATH = os.path.join(os.path.dirname(__file__), '.secret_key')
if os.path.exists(SECRET_KEY_PATH):
    with open(SECRET_KEY_PATH) as f:
        app.secret_key = f.read().strip()
else:
    key = secrets.token_hex(32)
    with open(SECRET_KEY_PATH, 'w') as f:
        f.write(key)
    app.secret_key = key

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), 'static', 'uploads')
os.makedirs(UPLOAD_DIR, exist_ok=True)
ALLOWED_EXT = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

db.init_db()

app.jinja_env.globals['rating_label'] = rating_label
app.jinja_env.globals['confidence_label'] = confidence_label


# ---------- helpers ----------

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXT


def save_image(file_storage):
    if file_storage and file_storage.filename and allowed_file(file_storage.filename):
        ext = file_storage.filename.rsplit('.', 1)[1].lower()
        fname = f"{uuid.uuid4().hex}.{ext}"
        file_storage.save(os.path.join(UPLOAD_DIR, fname))
        return fname
    return None


def topic_due_count(conn, topic_id):
    now_iso = datetime.utcnow().isoformat()
    row = conn.execute(
        "SELECT COUNT(*) c FROM questions WHERE topic_id = ? AND (next_eligible IS NULL OR next_eligible <= ?)",
        (topic_id, now_iso)
    ).fetchone()
    return row['c']


def user_topics(conn, uid, subject_id):
    if subject_id:
        return conn.execute(
            "SELECT topics.* FROM topics JOIN subjects ON subjects.id = topics.subject_id "
            "WHERE subjects.user_id = ? AND topics.subject_id = ?", (uid, subject_id)
        ).fetchall()
    return conn.execute(
        "SELECT topics.* FROM topics JOIN subjects ON subjects.id = topics.subject_id WHERE subjects.user_id = ?",
        (uid,)
    ).fetchall()


def question_payload(conn, qid, answered_so_far):
    q = conn.execute(
        "SELECT questions.*, topics.name AS topic_name FROM questions "
        "JOIN topics ON topics.id = questions.topic_id WHERE questions.id = ?", (qid,)
    ).fetchone()
    return {
        'count': answered_so_far,
        'topic_name': q['topic_name'],
        'text': q['text'],
        'answer': q['answer'] or '',
        'image_url': url_for('static', filename='uploads/' + q['image_filename']) if q['image_filename'] else None,
        'answer_image_url': url_for('static', filename='uploads/' + q['answer_image_filename']) if q['answer_image_filename'] else None,
    }


# ---------- auth ----------

@app.route('/register', methods=['GET', 'POST'])
def register():
    if session.get('user_id'):
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        confirm = request.form.get('confirm', '')
        if not username or not password:
            flash('Username and password are required.', 'error')
            return redirect(url_for('register'))
        if password != confirm:
            flash("Passwords don't match.", 'error')
            return redirect(url_for('register'))
        conn = db.get_db()
        try:
            cur = conn.execute(
                "INSERT INTO users (username, password_hash, created_at) VALUES (?, ?, ?)",
                (username, generate_password_hash(password), datetime.utcnow().isoformat())
            )
            conn.commit()
            session['user_id'] = cur.lastrowid
            session['username'] = username
            conn.close()
            return redirect(url_for('dashboard'))
        except db.sqlite3.IntegrityError:
            conn.close()
            flash('That username is already taken.', 'error')
            return redirect(url_for('register'))
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('user_id'):
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        conn = db.get_db()
        user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        conn.close()
        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            next_url = request.args.get('next') or url_for('dashboard')
            return redirect(next_url)
        flash('Incorrect username or password.', 'error')
        return redirect(url_for('login'))
    return render_template('login.html')


@app.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return redirect(url_for('login'))


# ---------- dashboard ----------

@app.route('/')
@login_required
def dashboard():
    uid = session['user_id']
    conn = db.get_db()
    subjects = conn.execute("SELECT * FROM subjects WHERE user_id = ? ORDER BY name", (uid,)).fetchall()

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
@login_required
def manage():
    uid = session['user_id']
    conn = db.get_db()
    subjects = conn.execute("SELECT * FROM subjects WHERE user_id = ? ORDER BY name", (uid,)).fetchall()
    topics = conn.execute(
        "SELECT topics.*, subjects.name AS subject_name FROM topics "
        "JOIN subjects ON subjects.id = topics.subject_id WHERE subjects.user_id = ? "
        "ORDER BY subjects.name, topics.name", (uid,)
    ).fetchall()
    conn.close()
    return render_template('manage.html', subjects=subjects, topics=topics)


@app.route('/subjects/add', methods=['POST'])
@login_required
def add_subject():
    uid = session['user_id']
    name = request.form.get('name', '').strip()
    if not name:
        flash('Subject name cannot be empty.', 'error')
        return redirect(url_for('manage'))
    conn = db.get_db()
    try:
        conn.execute("INSERT INTO subjects (user_id, name) VALUES (?, ?)", (uid, name))
        conn.commit()
        flash(f'Added subject "{name}".', 'success')
    except db.sqlite3.IntegrityError:
        flash(f'Subject "{name}" already exists.', 'error')
    conn.close()
    return redirect(url_for('manage'))


@app.route('/subjects/<int:subject_id>/delete', methods=['POST'])
@login_required
def delete_subject(subject_id):
    uid = session['user_id']
    conn = db.get_db()
    conn.execute("DELETE FROM subjects WHERE id = ? AND user_id = ?", (subject_id, uid))
    conn.commit()
    conn.close()
    flash('Subject deleted.', 'success')
    return redirect(url_for('manage'))


@app.route('/topics/add', methods=['POST'])
@login_required
def add_topic():
    uid = session['user_id']
    subject_id = request.form.get('subject_id')
    name = request.form.get('name', '').strip()
    if not subject_id or not name:
        flash('Pick a subject and enter a topic name.', 'error')
        return redirect(url_for('manage'))
    conn = db.get_db()
    owned = conn.execute("SELECT id FROM subjects WHERE id = ? AND user_id = ?", (subject_id, uid)).fetchone()
    if not owned:
        conn.close()
        flash('Subject not found.', 'error')
        return redirect(url_for('manage'))
    try:
        conn.execute(
            "INSERT INTO topics (subject_id, name, rating, rd, last_update) VALUES (?, ?, ?, ?, ?)",
            (subject_id, name, glicko.DEFAULT_RATING, glicko.DEFAULT_RD, datetime.utcnow().isoformat())
        )
        conn.commit()
        flash(f'Added topic "{name}".', 'success')
    except db.sqlite3.IntegrityError:
        flash('That topic already exists in this subject.', 'error')
    conn.close()
    return redirect(url_for('manage'))


@app.route('/topics/<int:topic_id>/delete', methods=['POST'])
@login_required
def delete_topic(topic_id):
    uid = session['user_id']
    conn = db.get_db()
    conn.execute(
        "DELETE FROM topics WHERE id = ? AND subject_id IN (SELECT id FROM subjects WHERE user_id = ?)",
        (topic_id, uid)
    )
    conn.commit()
    conn.close()
    flash('Topic deleted.', 'success')
    return redirect(url_for('manage'))


# ---------- manage: questions ----------

@app.route('/questions')
@login_required
def questions():
    uid = session['user_id']
    conn = db.get_db()
    topic_filter = request.args.get('topic_id', type=int)
    topics = conn.execute(
        "SELECT topics.*, subjects.name AS subject_name FROM topics "
        "JOIN subjects ON subjects.id = topics.subject_id WHERE subjects.user_id = ? "
        "ORDER BY subjects.name, topics.name", (uid,)
    ).fetchall()

    if topic_filter:
        q_rows = conn.execute(
            "SELECT questions.*, topics.name AS topic_name FROM questions "
            "JOIN topics ON topics.id = questions.topic_id "
            "JOIN subjects ON subjects.id = topics.subject_id "
            "WHERE topics.id = ? AND subjects.user_id = ? ORDER BY questions.id DESC",
            (topic_filter, uid)
        ).fetchall()
    else:
        q_rows = conn.execute(
            "SELECT questions.*, topics.name AS topic_name FROM questions "
            "JOIN topics ON topics.id = questions.topic_id "
            "JOIN subjects ON subjects.id = topics.subject_id "
            "WHERE subjects.user_id = ? ORDER BY questions.id DESC LIMIT 100",
            (uid,)
        ).fetchall()

    conn.close()
    return render_template('questions.html', topics=topics, questions=q_rows, topic_filter=topic_filter)


@app.route('/questions/add', methods=['POST'])
@login_required
def add_question():
    uid = session['user_id']
    topic_id = request.form.get('topic_id')
    text = request.form.get('text', '').strip()
    answer = request.form.get('answer', '').strip()
    if not topic_id or not text:
        flash('Pick a topic and enter question text.', 'error')
        return redirect(url_for('questions'))

    conn = db.get_db()
    owned = conn.execute(
        "SELECT topics.id FROM topics JOIN subjects ON subjects.id = topics.subject_id "
        "WHERE topics.id = ? AND subjects.user_id = ?", (topic_id, uid)
    ).fetchone()
    if not owned:
        conn.close()
        flash('Topic not found.', 'error')
        return redirect(url_for('questions'))

    avg_row = conn.execute("SELECT AVG(rating) a FROM questions WHERE topic_id = ?", (topic_id,)).fetchone()
    start_rating = avg_row['a'] if avg_row['a'] is not None else glicko.DEFAULT_RATING

    image_filename = save_image(request.files.get('image'))
    answer_image_filename = save_image(request.files.get('answer_image'))

    conn.execute(
        "INSERT INTO questions (topic_id, text, answer, rating, rd, last_update, image_filename, answer_image_filename) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (topic_id, text, answer or None, start_rating, glicko.DEFAULT_RD, datetime.utcnow().isoformat(),
         image_filename, answer_image_filename)
    )
    conn.commit()
    conn.close()
    flash('Question added.', 'success')
    return redirect(url_for('questions', topic_id=topic_id))


@app.route('/questions/<int:question_id>/delete', methods=['POST'])
@login_required
def delete_question(question_id):
    uid = session['user_id']
    topic_id = request.form.get('topic_id', type=int)
    conn = db.get_db()
    q = conn.execute(
        "SELECT questions.* FROM questions JOIN topics ON topics.id = questions.topic_id "
        "JOIN subjects ON subjects.id = topics.subject_id WHERE questions.id = ? AND subjects.user_id = ?",
        (question_id, uid)
    ).fetchone()
    if q:
        conn.execute("DELETE FROM questions WHERE id = ?", (question_id,))
        conn.commit()
        for fname in (q['image_filename'], q['answer_image_filename']):
            if fname:
                path = os.path.join(UPLOAD_DIR, fname)
                if os.path.exists(path):
                    try:
                        os.remove(path)
                    except OSError:
                        pass
    conn.close()
    flash('Question deleted.', 'success')
    return redirect(url_for('questions', topic_id=topic_id))


# ---------- study (infinite session) ----------

@app.route('/study')
@login_required
def study_setup():
    uid = session['user_id']
    conn = db.get_db()
    subjects = conn.execute("SELECT * FROM subjects WHERE user_id = ? ORDER BY name", (uid,)).fetchall()
    conn.close()
    return render_template('study_setup.html', subjects=subjects)


def _start_session(subject_id):
    session['study_subject_id'] = subject_id
    session['study_scores'] = []
    session['study_seen'] = []
    session.pop('study_current_qid', None)


@app.route('/study/start', methods=['POST'])
@login_required
def study_start():
    subject_id = request.form.get('subject_id')
    _start_session(int(subject_id) if subject_id else None)
    return redirect(url_for('study_session'))


@app.route('/study/quickstart/<int:subject_id>')
@login_required
def study_quickstart(subject_id):
    uid = session['user_id']
    conn = db.get_db()
    owned = conn.execute("SELECT id FROM subjects WHERE id = ? AND user_id = ?", (subject_id, uid)).fetchone()
    conn.close()
    if not owned:
        flash('Subject not found.', 'error')
        return redirect(url_for('dashboard'))
    _start_session(subject_id)
    return redirect(url_for('study_session'))


@app.route('/study/session')
@login_required
def study_session():
    uid = session['user_id']
    if 'study_scores' not in session:
        return redirect(url_for('study_setup'))

    conn = db.get_db()
    qid = session.get('study_current_qid')
    if not qid:
        topics = user_topics(conn, uid, session.get('study_subject_id'))
        q = pick_next_question(conn, topics, set(session.get('study_seen', [])))
        if not q:
            conn.close()
            flash('No questions available yet for this — add some first.', 'error')
            return redirect(url_for('questions'))
        qid = q['id']
        session['study_current_qid'] = qid

    payload = question_payload(conn, qid, len(session.get('study_scores', [])))
    conn.close()
    return render_template('study_session.html', q=payload)


@app.route('/study/answer', methods=['POST'])
@login_required
def study_answer():
    uid = session['user_id']
    qid = session.get('study_current_qid')
    if not qid:
        return jsonify({'error': 'no active question'}), 400

    score = float(request.json.get('score'))
    now = datetime.utcnow()
    now_iso = now.isoformat()

    conn = db.get_db()
    q = conn.execute(
        "SELECT questions.* FROM questions JOIN topics ON topics.id = questions.topic_id "
        "JOIN subjects ON subjects.id = topics.subject_id "
        "WHERE questions.id = ? AND subjects.user_id = ?", (qid, uid)
    ).fetchone()
    if not q:
        conn.close()
        return jsonify({'error': 'not found'}), 404

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
        conn.execute("UPDATE topics SET pending_results = ? WHERE id = ?", (json.dumps(pending), t['id']))

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

    scores = session.get('study_scores', [])
    scores.append(score)
    session['study_scores'] = scores
    seen = session.get('study_seen', [])
    seen.append(qid)
    session['study_seen'] = seen[-12:]
    session.pop('study_current_qid', None)

    topics = user_topics(conn, uid, session.get('study_subject_id'))
    nxt = pick_next_question(conn, topics, set(session['study_seen']))
    if not nxt:
        conn.close()
        return jsonify({'empty': True})

    session['study_current_qid'] = nxt['id']
    payload = question_payload(conn, nxt['id'], len(scores))
    conn.close()
    return jsonify({'empty': False, 'next': payload})


@app.route('/study/complete')
@login_required
def study_complete():
    scores = session.get('study_scores', [])
    total = len(scores)
    avg = round(sum(scores) / total, 2) if total else 0
    correct = sum(1 for s in scores if s >= 1)
    minor = sum(1 for s in scores if 0 < s < 1)
    wrong = sum(1 for s in scores if s <= 0)

    session.pop('study_subject_id', None)
    session.pop('study_scores', None)
    session.pop('study_seen', None)
    session.pop('study_current_qid', None)

    return render_template('study_complete.html', total=total, avg=avg, correct=correct, minor=minor, wrong=wrong)


if __name__ == '__main__':
    app.run(debug=True, port=5000)
