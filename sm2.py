"""
SM-2 (Anki-derived) scheduler, kept separate from Glicko.
Glicko drives difficulty/selection; SM-2 drives when a question re-enters
the eligible pool (n, EF, interval, next_eligible_date).
"""
from datetime import datetime, timedelta


def score_to_quality(score):
    # score: 1 = fully correct, 0.7 = minor error, 0 = incorrect
    if score >= 1:
        return 5
    if score >= 0.7:
        return 3
    return 0


def sm2_update(score, n, ef, interval):
    quality = score_to_quality(score)

    if quality < 3:
        n = 0
        interval = 1
    else:
        if n == 0:
            interval = 1
        elif n == 1:
            interval = 6
        else:
            interval = round(interval * ef)
        n += 1

    ef = ef + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
    ef = max(1.3, ef)

    next_eligible = (datetime.utcnow() + timedelta(days=interval)).isoformat()
    return n, ef, interval, next_eligible
