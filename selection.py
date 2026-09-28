"""
Infinite-session question selection:
- Thompson sampling picks which topic each question is drawn from: sample
  Normal(rating, RD) per topic, take the LOWEST sample. Weak topics (low
  rating) draw low samples more often, so they get picked more often, but
  every topic still has a chance - this reproduces "weighted inversely by
  elo" without a hard-coded weighting formula.
- Within the chosen topic, sample once from the topic's own Normal(rating, RD),
  binary-search a rating-sorted list of that topic's questions, and take the
  nearest neighbor.
- One question is picked per call, so sessions can run indefinitely; the
  caller re-calls this after every answer, which naturally interleaves topics.
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


def pick_next_question(conn, topics, exclude_ids):
    """topics: pre-filtered (already scoped to the right user/subject).
    exclude_ids: recently-seen question ids to avoid immediate repeats.
    Returns a single question row, or None if there are truly no questions
    anywhere in scope."""
    if not topics:
        return None

    now_iso = datetime.utcnow().isoformat()
    topic_pools = {}
    for t in topics:
        due = conn.execute(
            "SELECT * FROM questions WHERE topic_id = ? AND (next_eligible IS NULL OR next_eligible <= ?)",
            (t['id'], now_iso)
        ).fetchall()
        all_q = conn.execute("SELECT * FROM questions WHERE topic_id = ?", (t['id'],)).fetchall()
        topic_pools[t['id']] = list(due) if due else list(all_q)

    available_topics = [
        t for t in topics if any(q['id'] not in exclude_ids for q in topic_pools[t['id']])
    ]
    if not available_topics:
        # every question in scope was recently seen - relax and allow repeats
        available_topics = [t for t in topics if topic_pools[t['id']]]
        exclude_ids = set()
        if not available_topics:
            return None

    topic = thompson_pick_topic(available_topics)
    pool = topic_pools[topic['id']]
    q = pick_question(topic, pool, exclude_ids)
    if q is None:
        q = pick_question(topic, pool, set())
    return q
