# test_ollama_manual.py (run this to verify, don't commit)
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.llm.ollama_client import CodeGenerator

gen = CodeGenerator()

# Check connection
if not gen.health_check():
    print("ERROR: Can't reach Ollama or model not found!")
    print("Make sure 'ollama serve' is running and you pulled the model.")
    exit(1)

print("Ollama connected!\n")

# Test code generation
code = gen.generate(
    system_prompt="You are a Python expert. Return only code, no explanation.",
    prompt="Write a function that reads a CSV file and prints the first 5 rows using pandas.",
)
print("--- Generated Code ---")
print(code)

# Verify syntax
try:
    compile(code, "<string>", "exec")
    print("\n✓ Valid Python syntax!")
except SyntaxError as e:
    print(f"\n✗ Syntax error: {e}")