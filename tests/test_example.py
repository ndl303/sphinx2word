"""Build the example document in docs/example with the Word builder: it must build without warnings."""

import os
import subprocess
import sys
import zipfile

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
EXAMPLE = os.path.join(os.path.dirname(HERE), "docs", "example")

pytest.importorskip("sphinxcontrib.bibtex")
pytest.importorskip("sphinxarg")


def test_example_builds_without_warnings(tmp_path):
    # In a separate process: several Sphinx applications in one process warn about re-registered nodes.
    result = subprocess.run(
        [sys.executable, "-m", "sphinx", "-b", "word", "-E", "-q", "-D", "word_update_fields=prompt",
         EXAMPLE, str(tmp_path)],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    assert result.returncode == 0, result.stderr
    assert "WARNING" not in result.stderr and "ERROR" not in result.stderr, result.stderr
    with zipfile.ZipFile(tmp_path / "bigsat_atbd.docx") as z:
        xml = z.read("word/document.xml").decode("utf-8")
    # the reST shown by rst-example (as code) and the result after it (a numbered figure)
    assert "figures/bigsat_patch.png" in xml and ":numref:" in xml
    assert "SEQ Figure" in xml
