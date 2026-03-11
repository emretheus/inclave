import subprocess
import tempfile
import uuid
from pathlib import Path
from dataclasses import dataclass, field


@dataclass
class ExecutionResult:
    success: bool
    output: str
    error: str
    return_code: int
    plot_paths: list[str] = field(default_factory=list)


# Injected at the top of every script that uses matplotlib.
# Switches to non-interactive backend and monkey-patches plt.show()
# to save figures to a temp directory instead.
_PLOT_CAPTURE_PREAMBLE = """
import os as _os
_plot_dir = "{plot_dir}"
_os.makedirs(_plot_dir, exist_ok=True)
_plot_counter = [0]

import matplotlib as _mpl
_mpl.use("Agg")
import matplotlib.pyplot as _plt

_original_show = _plt.show
def _patched_show(*args, **kwargs):
    for _fig_num in _plt.get_fignums():
        _fig = _plt.figure(_fig_num)
        _path = _os.path.join(_plot_dir, f"plot_{{_plot_counter[0]}}.png")
        _fig.savefig(_path, dpi=150, bbox_inches="tight", facecolor="white")
        _plot_counter[0] += 1
    _plt.close("all")
_plt.show = _patched_show
"""


class CodeExecutor:
    """Runs generated Python code in a subprocess and captures output/errors and plots."""

    def __init__(self):
        self._plot_base = Path(tempfile.gettempdir()) / "enclave_plots"
        self._plot_base.mkdir(exist_ok=True)

    def execute(self, code: str, timeout: int = 30) -> ExecutionResult:
        plot_dir = str(self._plot_base / uuid.uuid4().hex[:8])

        uses_matplotlib = "matplotlib" in code or "plt." in code or "plt " in code
        if uses_matplotlib:
            preamble = _PLOT_CAPTURE_PREAMBLE.format(plot_dir=plot_dir)
            code = preamble + "\n" + code

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False
        ) as f:
            f.write(code)
            tmp_path = f.name

        try:
            result = subprocess.run(
                ["python", tmp_path],
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(Path.cwd()),
            )

            plot_paths = []
            plot_dir_path = Path(plot_dir)
            if plot_dir_path.exists():
                plot_paths = sorted(
                    str(p) for p in plot_dir_path.glob("*.png")
                )

            return ExecutionResult(
                success=(result.returncode == 0),
                output=result.stdout[:2000],
                error=result.stderr[:2000],
                return_code=result.returncode,
                plot_paths=plot_paths,
            )
        except subprocess.TimeoutExpired:
            return ExecutionResult(
                success=False,
                output="",
                error="Timeout: code took too long",
                return_code=-1,
            )
        finally:
            Path(tmp_path).unlink(missing_ok=True)
