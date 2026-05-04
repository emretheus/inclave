import os
import platform


def get_total_ram_gb() -> float:
    """
    Returns the total system RAM in GB.
    Currently only supports macOS (Darwin). Returns 0.0 if it cannot be read.
    """
    if platform.system() != "Darwin":
        return 0.0

    try:
        # sysctl -n hw.memsize The command gives the RAM in exact bytes on Mac.
        total_bytes = int(os.popen("sysctl -n hw.memsize").read().strip())
        return total_bytes / (1024**3)
    except Exception:
        return 0.0
