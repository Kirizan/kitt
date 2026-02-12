"""Local benchmark execution on the agent."""

import logging
import subprocess
import threading
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)


class BenchmarkExecutor:
    """Executes KITT benchmarks locally on the agent machine."""

    def __init__(self) -> None:
        self._current_process: subprocess.Popen | None = None
        self._lock = threading.Lock()

    def run_benchmark(
        self,
        model_path: str,
        engine: str,
        suite: str = "quick",
        output_dir: str = "",
        on_log: Callable[[str], None] | None = None,
    ) -> dict[str, Any]:
        """Run a KITT benchmark as a subprocess.

        Args:
            model_path: Path to the model.
            engine: Engine name (vllm, tgi, etc.).
            suite: Benchmark suite name.
            output_dir: Optional output directory.
            on_log: Callback for each log line.

        Returns:
            Dict with status, output_dir, and error.
        """
        args = ["kitt", "run", "-m", model_path, "-e", engine, "-s", suite]
        if output_dir:
            args.extend(["-o", output_dir])

        logger.info(f"Executing: {' '.join(args)}")

        try:
            with self._lock:
                self._current_process = subprocess.Popen(
                    args,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                )

            result_output_dir = ""
            lines = []

            for line in self._current_process.stdout or []:
                line = line.rstrip()
                lines.append(line)
                if on_log:
                    on_log(line)
                if "kitt-results" in line.lower():
                    for word in line.split():
                        if "kitt-results" in word:
                            result_output_dir = word.strip()

            return_code = self._current_process.wait()

            with self._lock:
                self._current_process = None

            if return_code != 0:
                error = "\n".join(lines[-20:])
                return {
                    "status": "failed",
                    "output_dir": result_output_dir,
                    "error": f"Exit code {return_code}: {error}",
                }

            return {
                "status": "completed",
                "output_dir": result_output_dir,
                "error": "",
            }

        except Exception as e:
            with self._lock:
                self._current_process = None
            return {
                "status": "failed",
                "output_dir": "",
                "error": str(e),
            }

    def cancel(self) -> bool:
        """Cancel the currently running benchmark."""
        with self._lock:
            if self._current_process is not None:
                self._current_process.terminate()
                return True
        return False

    @property
    def is_running(self) -> bool:
        with self._lock:
            return self._current_process is not None
