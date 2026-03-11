SYSTEM_PROMPT = """You are a Python data analyst and developer.
You generate clean, runnable Python code that works with CSV files.

Rules:
- Use pandas, numpy, and matplotlib only
- Always include necessary imports at the top
- Take the CSV file path as a parameter (use variable `csv_path`)
- Always produce complete, copy-paste ready scripts
- Add brief comments explaining each step
- Include basic error handling for file operations
- For large files, consider using chunksize parameter
- NEVER hardcode file paths — always use the csv_path variable
- Return ONLY Python code, no explanations before or after"""

GENERATION_TEMPLATE = """## Relevant Code Patterns
{rag_context}

## CSV File Information
{csv_schema}

## User Request
{user_prompt}

Generate a complete, runnable Python script that fulfills the user's request.
The script should use the variable `csv_path` for the input file path.
Return ONLY the Python code, no explanations before or after."""

GENERATION_TEMPLATE_NO_RAG = """## CSV File Information
{csv_schema}

## User Request
{user_prompt}

Generate a complete, runnable Python script that fulfills the user's request.
The script should use the variable `csv_path` for the input file path.
Return ONLY the Python code, no explanations before or after."""

GENERATION_TEMPLATE_WITH_EXAMPLE = """## Similar Working Example
{few_shot_example}

## Relevant Code Patterns
{rag_context}

## CSV File Information
{csv_schema}

## User Request
{user_prompt}

Generate a complete, runnable Python script that fulfills the user's request.
The script should use the variable `csv_path` for the input file path.
Return ONLY the Python code, no explanations before or after."""

FIX_PROMPT = """The following Python code produced an error. Fix it.

Code:
```python
{code}
```

Error:
{error}

Return ONLY the fixed Python code, no explanations."""
