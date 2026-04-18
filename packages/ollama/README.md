# enclave_ollama

The LLM integration layer for **Enclave Code**.

## Overview

This package acts as the bridge between the Enclave CLI and the local Ollama daemon. It provides a strictly typed, stateless, and synchronous Python API for model management and text inference.

It is designed to isolate the rest of the application from the underlying HTTP implementations and daemon connection issues.

## Scope & Responsibilities (Ollama Domain)

This package strictly owns:

- **Stateless Inference:** Exposing `generate` (one-shot) and `stream` (chunked) text generation.
- **Model Lifecycle:** Handling model listing, pulling (with progress), and removal.
- **Anti-Corruption Layer:** Trapping all low-level HTTP or connection errors from the `ollama` client and translating them into domain-specific exceptions (`OllamaUnavailableError`, `OllamaError`).

**Out of Scope:**

- This package does **NOT** handle conversation history or multi-turn state.
- This package does **NOT** render UI components or terminal outputs.
- This package does **NOT** execute sandbox code.

## Prerequisites

- macOS
- [Ollama](https://ollama.com) must be installed and running locally.
- Expected Ollama version: `>= 0.2.0`

### Installing Ollama

To run tests or use this package, ensure the daemon is running:

```bash
brew install ollama
ollama serve
```

## Usage

The CLI package interacts with this module statelessly:

```python
import enclave_ollama as oll
from enclave_core.errors import OllamaUnavailableError

try:
    # Set the default model
    oll.set_default("llama3.2")

    # Stream a response (stateless call)
    for chunk in oll.stream(
        prompt="Summarize the attached spreadsheet",
        model="llama3.2",
        system="<injected_file_context_from_cli>"
    ):
        print(chunk, end="", flush=True)

except OllamaUnavailableError as e:
    print(f"error: {e.message}")  # e.g., "Ollama is not running."
```