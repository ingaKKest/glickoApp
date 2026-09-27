"""
Session generation:
- Thompson sampling picks which topic each question is drawn from: sample
  Normal(rating, RD) per topic, take the LOWEST sample. Weak topics (low
  rating) draw low samples more often, so they get picked more often, but
  every topic still has a chance - this reproduces "weighted inversely by
  elo" without a hard-coded weighting formula.
- Within the chosen topic, sample once from the topic's own Normal(rating, RD),
  binary-search a rating-sorted list of that topic's questions, and take the
  nearest neighbor.
- Repeating this draw-by-draw naturally interleaves topics rather than
  blocking by topic.
"""
import random
import bisect
from datetime import datetime


def thompson_pick_topic(topics):
    best, best_val = None, None
    for t in topics:
        val = random.gauss(t['rating'], max(t['rd'], 1))
        if best_val is None or val < best_val:
            best_val, best = val, t
    return best


def pick_question(topic, questions, exclude_ids):
    candidates = [q for q in questions if q['id'] not in exclude_ids]
    if not candidates:
        return None
    candidates.sort(key=lambda q: q['rating'])
    ratings = [q['rating'] for q in candidates]
    sample = random.gauss(topic['rating'], max(topic['rd'], 1))
    idx = bisect.bisect_left(ratings, sample)

    best_idx, best_dist = None, None
    for cand_idx in (idx - 1, idx):
        if 0 <= cand_idx < len(candidates):
            dist = abs(ratings[cand_idx] - sample)
            if best_dist is None or dist < best_dist:
                best_dist, best_idx = dist, cand_idx
    return candidates[best_idx]


def build_session(db, subject_id, count):
    if subject_id:
        topics = db.execute("SELECT * FROM topics WHERE subject_id = ?", (subject_id,)).fetchall()
    else:
        topics = db.execute("SELECT * FROM topics").fetchall()

    if not topics:
        return []

    now_iso = datetime.utcnow().isoformat()
    topic_questions = {}
    for t in topics:
        due = db.execute(
            "SELECT * FROM questions WHERE topic_id = ? AND (next_eligible IS NULL OR next_eligible <= ?)",
            (t['id'], now_iso)
        ).fetchall()
        all_q = db.execute("SELECT * FROM questions WHERE topic_id = ?", (t['id'],)).fetchall()
        topic_questions[t['id']] = {'due': list(due), 'all': list(all_q)}

    session_ids = []
    exclude_ids = set()
    attempts, max_attempts = 0, count * 25

    while len(session_ids) < count and attempts < max_attempts:
        attempts += 1
        available_topics = [
            t for t in topics
            if any(q['id'] not in exclude_ids for q in
                   (topic_questions[t['id']]['due'] or topic_questions[t['id']]['all']))
        ]
        if not available_topics:
            break
        topic = thompson_pick_topic(available_topics)
        pool = topic_questions[topic['id']]['due'] or topic_questions[topic['id']]['all']
        q = pick_question(topic, pool, exclude_ids)
        if q is None:
            continue
        session_ids.append(q['id'])
        exclude_ids.add(q['id'])

    return session_ids
