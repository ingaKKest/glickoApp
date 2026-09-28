"""
Seed script to populate 'testuser' with dozens of subjects, topics, and questions.
Run with: python seed.py
"""
import random
from datetime import datetime
from werkzeug.security import generate_password_hash
import db
import glicko

SEED_DATA = {
    "Computer Systems & OS": {
        "xv6 Kernel & System Calls": [
            ("What trap mechanism moves execution from User Mode to Kernel Mode in x86/xv6?", "An interrupt trap gate (e.g. <code>INT 64</code> or <code>SYSENTER</code>)."),
            ("How does <code>pipeexec()</code> ensure concurrent safety when writing?", "It uses a spinlock around the ring buffer index."),
            ("What does <code>getppid()</code> return?", "Returns the process ID (PID) of the parent process."),
            ("Why does xv6 acquire `ptable.lock` before calling `sched()`?", "To protect thread state transitions during context switching.")
        ],
        "Virtual Memory & Paging": [
            ("What is the purpose of the TLB (Translation Lookaside Buffer)?", "A hardware cache for virtual-to-physical address translations."),
            ("Explain the difference between internal and external memory fragmentation.", "Internal happens inside allocated pages; external happens across unallocated free space."),
            ("What is page fault thrashing?", "When system spends more time paging data in/out of disk than executing processes.")
        ],
        "CPU Scheduling": [
            ("Define Multi-Level Feedback Queue (MLFQ).", "A priority-based scheduler that dynamically adjusts priorities based on process CPU usage history."),
            ("What is round-robin scheduling time quantum trade-off?", "Too short = excessive context switch overhead; too long = poor response time.")
        ]
    },
    "Software Engineering": {
        "Database Architecture & SQL": [
            ("What are ACID properties in relational databases?", "Atomicity, Consistency, Isolation, Durability."),
            ("Explain Third Normal Form (3NF).", "Every non-key attribute must depend directly on the primary key, avoiding transitive dependencies."),
            ("When should you index a database column?", "When read/query volume on that column heavily outweighs write volume.")
        ],
        "Design Patterns": [
            ("What problem does the Factory Method pattern solve?", "Decouples object instantiation logic from client code."),
            ("Explain the Observer Pattern.", "Publish-subscribe pattern where dependent objects are automatically notified on state change.")
        ]
    },
    "Mathematics & Analysis": {
        "Complex Analysis": [
            ("State the Residue Theorem equation.", "$\\oint_C f(z) dz = 2\\pi i \\sum \\text{Res}(f, z_k)$"),
            ("What does $e^{j2\\pi}$ simplify to?", "It equals $1$."),
            ("Define an Analytic Function.", "A function complex-differentiable at every point in a neighborhood.")
        ],
        "Multivariable Calculus": [
            ("What is the physical interpretation of Gradient?", "Direction and rate of steepest ascent of a scalar field."),
            ("What does a Divergence of zero signify in fluid dynamics?", "Incompressible fluid flow.")
        ]
    },
    "Competitive Pokémon Format": {
        "Hyper Offense & VGC Roles": [
            ("What is the main goal of a Screen Setter in Hyper Offense?", "Set Reflect and Light Screen to reduce incoming damage while setup sweepers boost."),
            ("What does EV spread 252 Atk / 4 SpD / 252 Speed maximize?", "Maximum physical damage output and highest possible speed tier."),
            ("How does Tailwind affect turn order?", "Doubles the Speed stats of all allied Pokémon for 4 turns.")
        ]
    }
}

def run_seed():
    db.init_db()
    conn = db.get_db()

    username = "testuser"
    password = "password123"

    user = conn.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
    if not user:
        cur = conn.execute(
            "INSERT INTO users (username, password_hash, created_at) VALUES (?, ?, ?)",
            (username, generate_password_hash(password), datetime.utcnow().isoformat())
        )
        uid = cur.lastrowid
        print(f"Created account: {username}")
    else:
        uid = user['id']
        print(f"Updating account: {username}")

    total_topics = 0
    total_q = 0

    for subject_name, topics in SEED_DATA.items():
        try:
            cur = conn.execute("INSERT INTO subjects (user_id, name) VALUES (?, ?)", (uid, subject_name))
            sub_id = cur.lastrowid
        except db.sqlite3.IntegrityError:
            sub_id = conn.execute("SELECT id FROM subjects WHERE user_id = ? AND name = ?", (uid, subject_name)).fetchone()['id']

        for topic_name, questions in topics.items():
            try:
                cur = conn.execute(
                    "INSERT INTO topics (subject_id, name, rating, rd, last_update) VALUES (?, ?, ?, ?, ?)",
                    (sub_id, topic_name, random.randint(1100, 1600), random.randint(60, 150), datetime.utcnow().isoformat())
                )
                top_id = cur.lastrowid
            except db.sqlite3.IntegrityError:
                top_id = conn.execute("SELECT id FROM topics WHERE subject_id = ? AND name = ?", (sub_id, topic_name)).fetchone()['id']

            total_topics += 1

            for q_prompt, q_ans in questions:
                conn.execute(
                    "INSERT INTO questions (topic_id, text, answer, rating, rd, last_update) VALUES (?, ?, ?, ?, ?, ?)",
                    (top_id, q_prompt, q_ans, random.randint(1100, 1600), glicko.DEFAULT_RD, datetime.utcnow().isoformat())
                )
                total_q += 1

    conn.commit()
    conn.close()
    print(f"Seed complete! Loaded {len(SEED_DATA)} subjects, {total_topics} topics, and {total_q} questions into 'testuser'.")

if __name__ == '__main__':
    run_seed()