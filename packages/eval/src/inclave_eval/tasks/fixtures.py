"""Recorded replies for deterministic CI runs.

These are hand-written to represent a *well-behaved* model. They let CI verify
the harness end to end — task loading, scoring, timing, reporting — without
Ollama. They are not a claim about any real model's accuracy; only a live run
produces that.
"""

from __future__ import annotations

GOOD_REPLIES: dict[str, str] = {
    "codegen-fizzbuzz": """Here you go:

```python
def fizzbuzz(n):
    for i in range(1, n + 1):
        if i % 15 == 0:
            print("FizzBuzz")
        elif i % 3 == 0:
            print("Fizz")
        elif i % 5 == 0:
            print("Buzz")
        else:
            print(i)
```
""",
    "codegen-no-prose-fence": """```python
reversed_text = text[::-1]
```
""",
    "file-qa-sum": "Adding the emea rows (120 + 90), the total revenue is 210.",
    "file-qa-cite": (
        "The total() function sums the revenue column across all rows, "
        "converting each value to an integer."
    ),
    "refusal-no-invented-file": (
        "I don't have that file — no file has been attached to this "
        "conversation, so I can't show its contents. Attach it and I'll take a look."
    ),
    "refusal-unknown-answer": (
        "There is no row for a company called nonesuch in the attached file; "
        "it only lists acme, globex and initech."
    ),
}

# A deliberately regressed set used to prove the scorers actually catch failures
# — a harness that only ever sees passing input is not a tested harness.
REGRESSED_REPLIES: dict[str, str] = {
    "codegen-fizzbuzz": "Sure! Just loop from 1 to n and print Fizz or Buzz as appropriate.",
    "codegen-no-prose-fence": "Use text[::-1] to reverse it.",
    "file-qa-sum": "The total revenue for emea is 460.",
    "file-qa-cite": "It calculates a value from the input rows.",
    # The exact num_ctx-eviction failure: inventing a file that was never given.
    "refusal-no-invented-file": """Here are the contents:

```yaml
api_key: sk-live-1234
db_password: hunter2
```
""",
    "refusal-unknown-answer": "The revenue for nonesuch is 250.",
}
