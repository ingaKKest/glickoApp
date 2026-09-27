# Glicko Study

A math (or any-subject) practice app that ranks your mastery of each topic with a
Glicko rating, and uses that rating to decide what you study next.

## Running it

```bash
pip install -r requirements.txt
python app.py
```

Then open **http://localhost:5000**. Data is stored in `glicko_app.db` (SQLite),
created automatically next to `app.py` — everything persists across restarts.

## How it works

- **Subjects → Topics → Questions.** Add subjects, add topics under them, add
  questions under each topic (with an optional answer/solution shown after you
  self-grade).
- **Glicko ratings, per topic and per question.** Everyone starts at 1500 / RD 350.
  A new question starts at its topic's current average question rating (or 1500
  if the topic has no questions yet).
- **Topic ratings update in batches of 5** ("rating periods"), buffered until 5
  answers accumulate, then flushed with a standard Glicko batch update.
- **Question ratings update immediately** after each answer, treating the topic's
  rating as the "opponent" with the complementary score (a question you get wrong
  effectively "wins" against you).
- **RD grows back up** the longer a topic or question goes untouched, so your
  confidence in a rating decays if you stop practicing it.
- **Topic selection during a session uses Thompson sampling**: each draw samples
  from every topic's Normal(rating, RD) and picks the lowest sample. Weak topics
  get drawn more often on average, strong topics still get a chance, and topics
  interleave naturally instead of being studied in blocks.
- **Question selection within a topic** samples once from the topic's own
  Normal(rating, RD) and picks the nearest-rated question via binary search —
  so you land on the question that best matches your current level in that topic.
- **SM-2 scheduling runs alongside Glicko**, separately, per question (n, EF,
  interval, next-eligible-date), controlling when a question is allowed to
  reappear. A session prefers due questions, and falls back to the full topic
  pool if nothing is due yet.
- Scoring is self-graded on three levels: **Correct (1)**, **Minor error (0.7)**,
  **Incorrect (0)**.

## A couple of judgment calls worth knowing about

The original design notes didn't fully specify two things, so I made reasonable
choices — both easy to change in `glicko.py` if you'd rather tune them:

- **RD inflation rate** — I used a constant (`C = 44.7` in `glicko.py`) such that
  roughly 60 days of inactivity pushes a fully-confident rating (RD 50) back up
  toward the RD 350 ceiling.
- **Question-level updates** — since only the topic side of Glicko had an explicit
  5-question batching rule, questions update immediately after every answer
  (effectively a rating-period-of-1), using the topic's rating at the moment of
  the answer as the opponent.

## Project layout

```
app.py          - routes
db.py           - SQLite schema + connection
glicko.py       - Glicko-1 rating engine
sm2.py          - SM-2 scheduler
selection.py    - Thompson-sampling topic/question picker for sessions
templates/      - Jinja templates
static/         - CSS + the study-session JS
```
