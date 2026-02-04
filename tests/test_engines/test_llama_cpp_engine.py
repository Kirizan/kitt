"""Tests for llama.cpp engine diagnostics."""

import types
from unittest.mock import patch


class TestLlamaCppDiagnose:
    def _get_engine_cls(self):
        from kitt.engines.llama_cpp_engine import LlamaCppEngine

        return LlamaCppEngine

    def test_diagnose_available(self):
        cls = self._get_engine_cls()
        fake_module = types.ModuleType("llama_cpp")
        with patch.dict("sys.modules", {"llama_cpp": fake_module}):
            diag = cls.diagnose()
        assert diag.available is True
        assert diag.engine_type == "python_import"
        assert diag.error is None

    def test_diagnose_not_installed(self):
        cls = self._get_engine_cls()
        with patch.dict("sys.modules", {"llama_cpp": None}):
            diag = cls.diagnose()
        assert diag.available is False
        assert "not installed" in diag.error
        assert "pip install llama-cpp-python" in diag.guidance

    def test_diagnose_cuda_import_error(self):
        cls = self._get_engine_cls()
        with patch.dict("sys.modules", {"llama_cpp": None}):
            import sys

            del sys.modules["llama_cpp"]
            with patch(
                "builtins.__import__",
                side_effect=ImportError(
                    "libcudart.so.12: cannot open shared object file"
                ),
            ):
                diag = cls.diagnose()
        assert diag.available is False
        assert "libcudart" in diag.error
        assert "DGGML_CUDA" in diag.guidance

    def test_diagnose_non_cuda_import_error(self):
        cls = self._get_engine_cls()
        with patch.dict("sys.modules", {"llama_cpp": None}):
            import sys

            del sys.modules["llama_cpp"]
            with patch(
                "builtins.__import__",
                side_effect=ImportError("unrelated import problem"),
            ):
                diag = cls.diagnose()
        assert diag.available is False
        assert "unrelated import problem" in diag.error
        assert diag.guidance is None
