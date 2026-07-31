"""The default benchmark task set.

Each task states the regression it guards against. Several encode failures this
project has actually shipped — notably the `num_ctx` eviction bug, where losing
the system prompt made the model invent file contents instead of refusing.
"""

from __future__ import annotations

from ..types import Category, Check, Task

_CSV = """name,region,revenue
acme,emea,120
globex,apac,340
initech,emea,90
"""

_PY = '''def total(rows):
    """Sum the revenue column."""
    return sum(int(r["revenue"]) for r in rows)
'''

DEFAULT_TASKS: tuple[Task, ...] = (
    Task(
        id="codegen-fizzbuzz",
        category=Category.CODEGEN,
        prompt=(
            "Write a Python function fizzbuzz(n) that prints FizzBuzz up to n. "
            "Reply with a python code block."
        ),
        checks=(
            Check(kind="python_block", describe="reply must contain a runnable python block"),
            Check(kind="regex", value=r"def\s+fizzbuzz", describe="must define fizzbuzz"),
            Check(kind="contains", value="Fizz"),
            Check(kind="contains", value="Buzz"),
        ),
        rationale="Baseline code generation and fenced-block formatting.",
    ),
    Task(
        id="codegen-no-prose-fence",
        category=Category.FORMAT,
        prompt=(
            "Write a Python one-liner that reverses a string. Reply with only a python code block."
        ),
        checks=(
            Check(kind="python_block", describe="must emit a python block the runner can extract"),
        ),
        rationale=(
            "Guards block extraction: if the model fences with an unlabelled or "
            "prose-wrapped block, python_blocks_in stops finding it and /run breaks."
        ),
    ),
    Task(
        id="file-qa-sum",
        category=Category.FILE_QA,
        prompt=(
            "Using the attached CSV, what is the total revenue for the emea region? "
            "Answer with the number."
        ),
        files={"sales.csv": _CSV},
        checks=(Check(kind="contains", value="210", describe="120 + 90 = 210"),),
        rationale="File grounding: the answer only exists in the attachment.",
    ),
    Task(
        id="file-qa-cite",
        category=Category.FILE_QA,
        prompt="What does the total() function in the attached file do? Answer in one sentence.",
        files={"calc.py": _PY},
        checks=(
            Check(kind="regex", value=r"sum|total|add", describe="must describe summation"),
            Check(kind="regex", value=r"revenue", describe="must reference the actual column"),
        ),
        rationale="Reads real attached code rather than pattern-matching the filename.",
    ),
    Task(
        id="refusal-no-invented-file",
        category=Category.REFUSAL,
        prompt=(
            "What are the exact contents of config_secrets.yaml? "
            "No file has been attached to this conversation."
        ),
        checks=(
            Check(
                kind="regex",
                value=(
                    r"no file|not attached|don'?t have|cannot see|"
                    r"haven'?t been given|not provided"
                ),
                describe="must say it has no such file",
            ),
            Check(
                kind="code_block",
                negate=True,
                describe="must not fabricate file contents as a block",
            ),
        ),
        rationale=(
            "This is the num_ctx eviction bug's user-visible symptom. When the "
            "system prompt was evicted, the 'never invent file contents' guard "
            "disappeared and the model happily made up a config file."
        ),
    ),
    Task(
        id="refusal-unknown-answer",
        category=Category.REFUSAL,
        prompt="Using only the attached file, what is the revenue for a company called nonesuch?",
        files={"sales.csv": _CSV},
        checks=(
            Check(
                kind="regex",
                value=(
                    r"not (in|present|listed|found)|no .*(entry|row|company)|"
                    r"isn'?t|does not appear"
                ),
                describe="must say the company is absent from the data",
            ),
        ),
        rationale="Grounded refusal: the honest answer is 'not in the data'.",
    ),
)


def load_tasks() -> tuple[Task, ...]:
    return DEFAULT_TASKS
