from unittest.mock import MagicMock, patch

from inclave_ollama.hardware import get_total_ram_gb


@patch("inclave_ollama.hardware.platform.system")
@patch("inclave_ollama.hardware.os.popen")
def test_get_total_ram_gb_mac_success(mock_popen: MagicMock, mock_system: MagicMock) -> None:
    """Should return the correct GB value when the sysctl command succeeds on macOS."""
    mock_system.return_value = "Darwin"

    # Simulate 16 GB RAM in bytes
    mock_read = MagicMock()
    mock_read.read.return_value = str(16 * (1024**3))
    mock_popen.return_value = mock_read

    assert get_total_ram_gb() == 16.0


@patch("inclave_ollama.hardware.platform.system")
@patch("inclave_ollama.hardware.os.popen")
def test_get_total_ram_gb_mac_error(mock_popen: MagicMock, mock_system: MagicMock) -> None:
    """Should not crash and return 0.0 if the sysctl command fails on macOS."""
    mock_system.return_value = "Darwin"
    mock_popen.side_effect = Exception("Sysctl command failed")

    assert get_total_ram_gb() == 0.0
