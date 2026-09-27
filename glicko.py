"""
Glicko-1 rating engine.

Each topic AND each question carries its own (rating, RD) pair.
- Topic ratings update in batches ("rating periods") of up to 5 questions,
  buffered in topics.pending_results and flushed once 5 accumulate.
- Question ratings update immediately after every answer (rating period = 1),
  using the topic's rating/RD at the moment of the answer as the sole "opponent",
  with the complementary score (1 - player_score) since a question "wins" when
  the player gets it wrong.
- RD inflates toward the 350 ceiling based on days elapsed since the last
  update, before any new result is folded in, so ratings you haven't touched
  in a while become less certain again.
"""
import math
from datetime import datetime

Q = math.log(10) / 400
C = 44.7        # RD inflation constant: ~60 days of inactivity pushes RD from 50 back to 350
MAX_RD = 350.0
MIN_RD = 30.0
DEFAULT_RATING = 1500.0
DEFAULT_RD = 350.0


def _g(rd):
    return 1 / math.sqrt(1 + 3 * Q ** 2 * rd ** 2 / math.pi ** 2)


def _e(rating, opp_rating, opp_rd):
    return 1 / (1 + 10 ** (-_g(opp_rd) * (rating - opp_rating) / 400))


def days_between(iso_then, now=None):
    if not iso_then:
        return 0
    then = datetime.fromisoformat(iso_then)
    now = now or datetime.utcnow()
    return max(0.0, (now - then).total_seconds() / 86400)


def inflate_rd(rd, days_elapsed):
    """Grow RD toward MAX_RD based on time since the last update."""
    if days_elapsed <= 0:
        return rd
    inflated = math.sqrt(rd ** 2 + C ** 2 * days_elapsed)
    return min(MAX_RD, inflated)


def update_rating(rating, rd, results, days_elapsed):
    """
    results: list of (opp_rating, opp_rd, score) tuples, score in [0, 1]
    Returns (new_rating, new_rd).
    """
    rd = inflate_rd(rd, days_elapsed)
    if not results:
        return rating, rd

    d2_inv_sum = 0.0
    sum_term = 0.0
    for opp_rating, opp_rd, score in results:
        g_val = _g(opp_rd)
        e_val = _e(rating, opp_rating, opp_rd)
        d2_inv_sum += g_val ** 2 * e_val * (1 - e_val)
        sum_term += g_val * (score - e_val)

    if d2_inv_sum <= 0:
        return rating, rd

    d2 = 1 / (Q ** 2 * d2_inv_sum)
    denom = (1 / rd ** 2) + (1 / d2)
    new_rd = math.sqrt(1 / denom)
    new_rating = rating + (Q / denom) * sum_term
    new_rd = max(MIN_RD, min(MAX_RD, new_rd))
    return new_rating, new_rd
