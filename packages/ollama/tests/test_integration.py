import pytest
from enclave_ollama.api import generate, list_models


@pytest.mark.integration
def test_ollama_list_models_real() -> None:
    """Can we retrieve the model list from a real Ollama instance?"""
    models = list_models()

    assert isinstance(models, list)


@pytest.mark.integration
def test_ollama_generate_real() -> None:
    """Can we get a short response from a real Ollama instance?"""

    try:
        response = generate("Hi, are you there?", model="qwen2.5-coder:14b")
        assert isinstance(response, str)
        assert len(response) > 0
    except Exception as e:
        pytest.fail(f"The generate test with the real Ollama instance failed: {e}")
