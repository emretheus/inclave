import httpx
import pytest
from enclave_ollama.api import generate, list_models


def is_ollama_running() -> bool:
    try:
        httpx.get("http://127.0.0.1:11434/api/tags", timeout=1.0)
        return True
    except Exception:
        return False


@pytest.mark.integration
@pytest.mark.skipif(not is_ollama_running(), reason="Ollama is not running locally")
def test_ollama_list_models_real() -> None:
    """Can we retrieve the model list from a real Ollama instance?"""
    models = list_models()

    assert isinstance(models, list)


@pytest.mark.integration
@pytest.mark.skipif(not is_ollama_running(), reason="Ollama is not running locally")
def test_ollama_generate_real() -> None:
    """Can we get a short response from a real Ollama instance?"""

    try:
        response = generate("Hi, are you there?", model="qwen2.5-coder:14b")
        assert isinstance(response, str)
        assert len(response) > 0
    except Exception as e:
        pytest.fail(f"The generate test with the real Ollama instance failed: {e}")
