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

## Accounts

The first time you open the app you'll be asked to create an account
(username + password). Everything — subjects, topics, questions, ratings —
is scoped to your account, so it's ready for more than one person to use the
same server if you ever want that. If you're upgrading from a version of
this app that had no login system, your existing data is automatically
folded into a fallback account the first time you run the new code — the
terminal will print a one-time username/password for it.

## How it works

- **Subjects → Topics → Questions.** Add subjects, add topics under them, add
  questions under each topic. Each question can optionally include an image
  (for the question itself and/or the answer) alongside or instead of text.
- **Ratings are shown as words, not numbers** — Needs practice / Developing /
  Good / Strong / Excellent — so you don't need to know what Glicko is to
  read your own dashboard. The raw numbers still drive everything under the
  hood.
- **Sessions are infinite.** Pick a subject (or "All subjects") and go —
  there's no question count to choose. Keep going for as long as you want,
  then hit "End session" whenever you're done.
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
