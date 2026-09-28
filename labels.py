"""Turns raw Glicko numbers into words, so ratings are readable without
knowing what Glicko even is."""

TIERS = [
    (0,    1150, "Needs practice", "tier-weak"),
    (1150, 1350, "Developing",     "tier-mid"),
    (1350, 1650, "Good",           "tier-good"),
    (1650, 1850, "Strong",         "tier-strong"),
    (1850, 10 ** 6, "Excellent",   "tier-excellent"),
]


def rating_label(rating):
    """Returns (label, css_class)."""
    for lo, hi, label, css in TIERS:
        if lo <= rating < hi:
            return label, css
    return "Excellent", "tier-excellent"


def confidence_label(rd):
    """How sure the app is about a rating, in words."""
    if rd <= 80:
        return "well established"
    if rd <= 180:
        return "getting clearer"
    return "still learning this"
