from unittest.mock import MagicMock, patch

import httpx
import ollama
import pytest
from enclave_ollama.api import (
    generate,
    get_default,
    is_model_fully_vram_compatible,
    list_models,
    pull_model,
    remove_model,
    requires_ollama,
    set_default,
    stream,
)
from enclave_ollama.errors import OllamaError, OllamaUnavailableError


@patch("enclave_ollama.api.get_default")
@patch("enclave_ollama.api.ollama.list")
def test_list_models_success(mock_list: MagicMock, mock_get_default: MagicMock) -> None:
    """Test that list_models correctly parses the Ollama API response."""

    mock_get_default.return_value = "llama3:latest"
    mock_list.return_value = {
        "models": [
            {
                "name": "llama3:latest",
                "size": 4700000000,
                "details": {"family": "llama", "parameter_size": "8B"},
            },
            {
                "name": "mistral:latest",
                "size": 4100000000,
                "details": {"family": "llama", "parameter_size": "7B"},
            },
        ]
    }

    models = list_models()

    assert len(models) == 2
    assert models[0].name == "llama3:latest"
    assert models[0].is_default is True
    assert models[1].name == "mistral:latest"
    assert models[1].is_default is False


@patch("enclave_ollama.api.ollama.list")
def test_list_models_unavailable(mock_list: MagicMock) -> None:
    """Test that list_models raises the correct domain error when daemon is down."""
    mock_list.side_effect = httpx.ConnectError("Connection refused")

    with pytest.raises(OllamaUnavailableError, match="Ollama is not running"):
        list_models()


@patch("enclave_ollama.api.ollama.chat")
def test_generate_success(mock_chat: MagicMock) -> None:
    """Test that generate extracts the correct string content from the response."""
    mock_chat.return_value = {"message": {"role": "assistant", "content": "Hello from mock!"}}

    result = generate("Say hello", model="llama3")

    assert result == "Hello from mock!"

    mock_chat.assert_called_once_with(
        model="llama3", messages=[{"role": "user", "content": "Say hello"}]
    )


@patch("enclave_ollama.api.ollama.chat")
def test_generate_api_error(mock_chat: MagicMock) -> None:
    """Test response when Ollama API returns an error (e.g., model not found)."""
    mock_chat.side_effect = ollama.ResponseError("model 'llama3' not found")

    with pytest.raises(OllamaError, match="Ollama error: model 'llama3' not found"):
        generate("Hi", model="llama3")


def test_generate_requires_model() -> None:
    """Test that generation fails immediately if no model is provided."""
    with pytest.raises(OllamaError, match="A model must be specified"):
        generate("Hello", model="")


@patch("enclave_ollama.api.load_config")
def test_get_default_success(mock_load_config: MagicMock) -> None:
    """Test whether the correct model is being read from the configuration file."""
    mock_config = MagicMock()
    mock_config.default_model = "qwen2:latest"
    mock_load_config.return_value = mock_config

    assert get_default() == "qwen2:latest"


@patch("enclave_ollama.api.save_config")
@patch("enclave_ollama.api.load_config")
def test_set_default_success(mock_load_config: MagicMock, mock_save_config: MagicMock) -> None:
    """Test whether the default model is correctly written to the configuration file."""
    mock_config = MagicMock()
    mock_load_config.return_value = mock_config

    set_default("llama3:latest")

    assert mock_config.default_model == "llama3:latest"
    mock_save_config.assert_called_once_with(mock_config)


@patch("enclave_ollama.api.load_config")
def test_config_errors_are_wrapped(mock_load_config: MagicMock) -> None:
    """Test system safety when the config file cannot be read or is corrupted."""
    mock_load_config.side_effect = Exception("File is locked")

    with pytest.raises(OllamaError, match="Failed to get default model"):
        get_default()

    with pytest.raises(OllamaError, match="Failed to set default model"):
        set_default("llama3")


@patch("enclave_ollama.api.ollama.delete")
def test_remove_model_success(mock_delete: MagicMock) -> None:
    """Test that remove_model calls the Ollama delete API correctly."""
    remove_model("llama3")
    mock_delete.assert_called_once_with("llama3")


@patch("enclave_ollama.api.ollama.delete")
def test_remove_model_error(mock_delete: MagicMock) -> None:
    """Test that API errors during removal are wrapped correctly."""
    mock_delete.side_effect = ollama.ResponseError("model not found")

    with pytest.raises(OllamaError, match="Failed to remove model: model not found"):
        remove_model("llama3")


@patch("enclave_ollama.api.ollama.pull")
def test_pull_model_success(mock_pull: MagicMock) -> None:
    """Test that pull_model yields human-readable progress strings."""

    mock_pull.return_value = [
        {"status": "pulling manifest"},
        {"status": "downloading 9af3d51f1126", "completed": 50, "total": 100},
        {"status": "success"},
    ]

    progress_stream = pull_model("llama3")
    results = list(progress_stream)

    assert len(results) == 3
    assert results[0] == "pulling manifest"
    assert "downloading" in results[1]
    assert results[2] == "success"

    mock_pull.assert_called_once_with("llama3", stream=True)


@patch("enclave_ollama.api.ollama.pull")
def test_pull_model_error(mock_pull: MagicMock) -> None:
    """Test that API errors during model pull are wrapped correctly."""
    mock_pull.side_effect = ollama.ResponseError("repository not found")

    with pytest.raises(OllamaError, match="Failed to pull model: repository not found"):
        list(pull_model("invalid_model"))


@patch("enclave_ollama.api.ollama.chat")
def test_stream_success(mock_chat: MagicMock) -> None:
    """Test that stream yields content chunks correctly."""

    mock_chat.return_value = [
        {"message": {"content": "Hello"}},
        {"message": {"content": " from"}},
        {"message": {"content": " stream!"}},
    ]

    chunks = list(stream("Say hello", model="llama3"))

    assert len(chunks) == 3
    assert chunks[0] == "Hello"
    assert chunks[1] == " from"
    assert chunks[2] == " stream!"

    mock_chat.assert_called_once_with(
        model="llama3", messages=[{"role": "user", "content": "Say hello"}], stream=True
    )


def test_stream_requires_model() -> None:
    """Test that streaming fails immediately if no model is provided."""
    with pytest.raises(OllamaError, match="A model must be specified"):
        list(stream("Hello", model=""))


@patch("enclave_ollama.api.ollama.chat")
def test_stream_error(mock_chat: MagicMock) -> None:
    """Test that API errors during streaming are wrapped correctly."""
    mock_chat.side_effect = ollama.ResponseError("model not found")

    with pytest.raises(OllamaError, match="Ollama error: model not found"):
        list(stream("Hi", model="invalid_model"))


@patch("enclave_ollama.api.httpx.get")
def test_requires_ollama_success(mock_get: MagicMock) -> None:
    """Test that the decorator allows execution if Ollama is running."""

    mock_get.return_value.status_code = 200

    @requires_ollama
    def dummy_function() -> str:
        return "it works"

    assert dummy_function() == "it works"
    mock_get.assert_called_once_with("http://127.0.0.1:11434/api/tags", timeout=2.0)


@patch("enclave_ollama.api.httpx.get")
def test_requires_ollama_failure(mock_get: MagicMock) -> None:
    """Test that the decorator raises OllamaUnavailableError if Ollama is down."""

    mock_get.side_effect = httpx.ConnectError("Connection refused")

    @requires_ollama
    def dummy_function() -> str:
        return "this should never run"

    expected_msg = r"Ollama is not running\. Start it with: ollama serve"
    with pytest.raises(OllamaUnavailableError, match=expected_msg):
        dummy_function()


@patch("enclave_ollama.api.get_total_ram_gb")
def test_is_model_fully_vram_compatible(mock_get_ram: MagicMock) -> None:
    """Tests the boundary values for VRAM capacity calculations on Apple Silicon."""

    # Scenario 1: System RAM could not be read (returns 0.0) -> Expect None
    mock_get_ram.return_value = 0.0
    assert is_model_fully_vram_compatible(1000) is None

    # Scenario 2: Memory is sufficient (True)
    # System RAM = 16 GB. 70% limit = 11.2 GB available VRAM.
    # Model 5 GB + 2 GB Context = 7 GB. (7 <= 11.2)
    mock_get_ram.return_value = 16.0
    five_gb_bytes = 5 * (1024**3)
    assert is_model_fully_vram_compatible(five_gb_bytes, context_gb=2.0) is True

    # Scenario 3: Memory is insufficient (False)
    # System RAM = 8 GB. 70% limit = 5.6 GB available VRAM.
    # Model 5 GB + 2 GB Context = 7 GB. (7 > 5.6)
    mock_get_ram.return_value = 8.0
    assert is_model_fully_vram_compatible(five_gb_bytes, context_gb=2.0) is False
