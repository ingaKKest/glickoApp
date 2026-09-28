"""Turns raw Glicko numbers into words, so ratings are readable without
knowing what Glicko even is."""

# Topic Mastery Tiers (Higher = Player is more skilled)
TIERS = [
    (0,    1150, "Needs practice", "tier-weak"),
    (1150, 1350, "Developing",     "tier-mid"),
    (1350, 1650, "Good",           "tier-good"),
    (1650, 1850, "Strong",         "tier-strong"),
    (1850, 10 ** 6, "Excellent",   "tier-excellent"),
]

# Question Difficulty Tiers (Lower = Question is easier for the player)
DIFFICULTY_TIERS = [
    (0,    1200, "Easy",        "tier-good"),
    (1200, 1400, "Moderate",    "tier-mid"),
    (1400, 1650, "Challenging", "tier-strong"),
    (1650, 10 ** 6, "Hard",     "tier-weak"),
]


def rating_label(rating):
    """Returns (label, css_class) for Topic Skill level."""
    for lo, hi, label, css in TIERS:
        if lo <= rating < hi:
            return label, css
    return "Excellent", "tier-excellent"


def question_rating_label(rating):
    """Returns (label, css_class) for Question Difficulty."""
    for lo, hi, label, css in DIFFICULTY_TIERS:
        if lo <= rating < hi:
            return label, css
    return "Hard", "tier-weak"


def confidence_label(rd):
    """How sure the app is about a rating, in words."""
    if rd <= 80:
        return "well established"
    if rd <= 180:
        return "getting clearer"
    return "still learning this"