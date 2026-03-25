"""Test system prompts — the model should return ONLY code, no explanations."""
import ollama

response = ollama.chat(
    model="qwen2.5-coder:14b",
    messages=[
        {
            "role": "system",
            "content": "You are a Python expert. Return ONLY code. No explanations, no markdown, no quotes."
        },
        {
            "role": "user",
            "content": "Write a function that reads a CSV and returns the number of rows and columns"
        }
    ],
    options={
        "temperature": 0.1,    # Lower = more predictable output
    }
)

code = response["message"]["content"]

# --- TEMİZLİK ADIMI ---
# Eğer model inatla markdown blokları içine koyduysa onları ayıklayalım
if "```python" in code:
    code = code.split("```python")[1].split("```")[0].strip()
elif "```" in code:
    code = code.split("```")[1].split("```")[0].strip()
# ----------------------

print("Temizlenmiş Kod:\n", code)

# Artık compile edebilirsin
try:
    compile(code, "<string>", "exec")
    print("\n✓ Temizlenmiş kod geçerli bir Python kodudur!")
except SyntaxError as e:
    print(f"\n✗ Hata devam ediyor: {e}")