import ollama

# Step 1: Check if Ollama is running
try:
    models = ollama.list()
    print("Ollama is running!")
    print(f"Available models: {[m.model for m in models.models]}")
except Exception as e:
    print(f"ERROR: Can't connect to Ollama. Is it running? ({e})")
    exit(1)

# Step 2: Send a simple prompt
print("\n--- Generating code ---\n")

response = ollama.chat(
    model="qwen2.5-coder:7b",          # change to your model
    messages=[
        {"role": "user", "content": "Write a Python function that reads a CSV and prints column names"}
    ],
)

print(response["message"]["content"])