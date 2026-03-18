from src.llm.judge import JudgeAgent

judge = JudgeAgent()

# Test 1: correct code — should PASS
print("Test 1: Correct code")
verdict = judge.review(
    user_prompt="Show total revenue by city",
    csv_schema="Columns: city(str), revenue(float64), product(str)",
    code="import pandas as pd\ndf = pd.read_csv(csv_path)\nprint(df.groupby('city')['revenue'].sum())",
    execution_output="Istanbul  8600.50\nAnkara   5150.00",
)
print(f"Verdict: {verdict.verdict}")
print(f"Issues: {verdict.issues}")

print("\nTest 2: Wrong aggregation — should FAIL")
verdict = judge.review(
    user_prompt="Show total revenue by city",
    csv_schema="Columns: city(str), revenue(float64), product(str)",
    code="import pandas as pd\ndf = pd.read_csv(csv_path)\nprint(df.groupby('city')['revenue'].mean())",
    execution_output="Istanbul  1720.10\nAnkara   1716.67",
)
print(f"Verdict: {verdict.verdict}")
print(f"Issues: {verdict.issues}")

print("\nTest 3: Wrong column — should FAIL")
verdict = judge.review(
    user_prompt="Show total revenue by city",
    csv_schema="Columns: city(str), revenue(float64), product(str)",
    code="import pandas as pd\ndf = pd.read_csv(csv_path)\nprint(df.groupby('product')['revenue'].sum())",
    execution_output="Widget A  6501.50\nWidget B  7250.00",
)
print(f"Verdict: {verdict.verdict}")
print(f"Issues: {verdict.issues}")