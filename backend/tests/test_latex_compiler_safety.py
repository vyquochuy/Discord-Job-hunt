"""Compilation succeeds only for a fresh, readable, single-page PDF."""
import subprocess
from unittest.mock import patch

import pytest
from pypdf import PdfWriter

from app.services.tailoring.latex_compiler import LaTeXCompiler


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "pages,exit_code,expected",
    [(1, 0, True), (2, 0, False), (0, 0, False), (10, 1, False),
     (None, 0, False), (-1, 0, False)],
)
async def test_compile_validates_output(tmp_path, pages, exit_code, expected):
    def compile_pdf(*args, **kwargs):
        target = tmp_path / "job" / "resume.pdf"
        if pages is None:
            target.write_bytes(b"not a PDF")
        elif pages >= 0:
            writer = PdfWriter()
            for _ in range(pages):
                writer.add_blank_page(width=595, height=842)
            writer.write(target)
        return subprocess.CompletedProcess(args, exit_code, b"", b"")

    with (
        patch.object(LaTeXCompiler, "get_storage_root", return_value=tmp_path),
        patch("shutil.which", return_value="pdflatex"),
        patch("subprocess.run", side_effect=compile_pdf),
    ):
        ok, path, error = await LaTeXCompiler.compile_tex("source", "job")
    assert ok is expected
    if expected:
        assert path and error is None
    else:
        assert path is None and error
        assert not (tmp_path / "job" / "resume.pdf").exists()


@pytest.mark.asyncio
async def test_missing_binary_is_failure(tmp_path):
    target = tmp_path / "job" / "resume.pdf"
    target.parent.mkdir()
    target.write_bytes(b"stale PDF")
    with (
        patch.object(LaTeXCompiler, "get_storage_root", return_value=tmp_path),
        patch("shutil.which", return_value=None),
    ):
        ok, path, error = await LaTeXCompiler.compile_tex("source", "job")
    assert not ok and path is None and error
    assert not target.exists()
    assert target.with_suffix(".tex").read_text() == "source"


@pytest.mark.asyncio
async def test_compiler_timeout_is_failure(tmp_path):
    with (
        patch.object(LaTeXCompiler, "get_storage_root", return_value=tmp_path),
        patch("shutil.which", return_value="pdflatex"),
        patch("subprocess.run", side_effect=subprocess.TimeoutExpired("pdflatex", 30)),
    ):
        ok, path, error = await LaTeXCompiler.compile_tex("source", "job")
    assert not ok and path is None and "timed out" in error
