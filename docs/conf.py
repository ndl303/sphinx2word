# Sphinx configuration of the sphinx2word documentation (HTML, e.g. for Read the Docs).
#
# The pages are the Markdown files in this folder, read with MyST, so they also read well on GitHub and GitLab. The example
# project in example/ is not part of these pages: before an HTML build, it is built on its own as a Word document
# and as HTML, and zipped, so the pages can link to it and offer it for download (see build_example below).
#
#     python -m sphinx -b html docs docs/_build/html
import os
import shutil
import subprocess
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))           # sphinx2word from this repository

import sphinx2word  # noqa: E402

# -- Project ----------------------------------------------------------------------------------------------------------

project = "sphinx2word"
author = "Nick Lloyd"
copyright = "2023-2026, Nick Lloyd"
release = sphinx2word.__version__
version = ".".join(release.split(".")[:2])

# -- General ----------------------------------------------------------------------------------------------------------

extensions = ["myst_parser", "sphinx_copybutton"]
source_suffix = {".md": "markdown"}
root_doc = "index"
exclude_patterns = ["_build", "_generated", "example", "README.md", "Thumbs.db", ".DS_Store"]

myst_heading_anchors = 3              # links such as configuration.md#word_update_fields
myst_enable_extensions = ["colon_fence"]
copybutton_exclude = ".linenos, .gp"  # do not copy line numbers or prompts

# -- HTML -------------------------------------------------------------------------------------------------------------

html_theme = "pydata_sphinx_theme"
html_title = f"sphinx2word {release}"
html_logo = "example/figures/bigsat_patch.png"
html_favicon = "example/_static/bigsat_icon_32.ico"
html_static_path = ["_static"]
html_css_files = ["docs.css"]
html_theme_options = {
    "icon_links": [{"name": "GitHub", "url": "https://github.com/ndl303/sphinx2word", "icon": "fa-brands fa-github"}],
    "show_toc_level": 2,
}
# The example, built as HTML, is copied into the output as example/ (see build_example).
GENERATED = os.path.join(HERE, "_generated")
html_extra_path = [os.path.join(GENERATED, "extra")]
os.makedirs(html_extra_path[0], exist_ok=True)


# -- The example document ---------------------------------------------------------------------------------------------

EXAMPLE = os.path.join(HERE, "example")


def _newest_mtime(*folders):
    newest = 0.0
    for folder in folders:
        for dirpath, dirnames, filenames in os.walk(folder):
            dirnames[:] = [d for d in dirnames if d not in ("_build", "__pycache__")]
            for name in filenames:
                newest = max(newest, os.path.getmtime(os.path.join(dirpath, name)))
    return newest


def build_example(app):
    """
    Build the example as Word and HTML and zip its source, before the pages are read.

    The results go in _generated/: downloads/bigsat_atbd.docx and downloads/bigsat_example.zip for the
    {download} links on example.md, and extra/example/ (the HTML), which html_extra_path copies into the output.
    They are only rebuilt when the example or sphinx2word changed. Set SPHINX2WORD_SKIP_EXAMPLE=1 to skip it.
    """
    if app.builder.format != "html" or os.environ.get("SPHINX2WORD_SKIP_EXAMPLE"):
        return
    downloads = os.path.join(GENERATED, "downloads")
    docx = os.path.join(downloads, "bigsat_atbd.docx")
    zip_path = os.path.join(downloads, "bigsat_example.zip")
    html = os.path.join(html_extra_path[0], "example")
    package = os.path.dirname(sphinx2word.__file__)
    sources = _newest_mtime(EXAMPLE, package)
    if all(os.path.exists(p) for p in (docx, zip_path, os.path.join(html, "index.html"))) and \
            min(os.path.getmtime(p) for p in (docx, zip_path)) > sources:
        return
    os.makedirs(downloads, exist_ok=True)
    work = os.path.join(GENERATED, "build")
    shutil.rmtree(work, ignore_errors=True)
    shutil.rmtree(html, ignore_errors=True)
    sphinx = [sys.executable, "-m", "sphinx", "-q", "-E"]
    print("sphinx2word docs: building the example as Word and HTML")
    subprocess.run(sphinx + ["-b", "word", EXAMPLE, os.path.join(work, "word")], check=True)
    shutil.copyfile(os.path.join(work, "word", "bigsat_atbd.docx"), docx)
    subprocess.run(sphinx + ["-b", "html", EXAMPLE, html], check=True)
    shutil.rmtree(os.path.join(html, ".doctrees"), ignore_errors=True)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for dirpath, dirnames, filenames in os.walk(EXAMPLE):
            dirnames[:] = sorted(d for d in dirnames if d not in ("_build", "__pycache__"))
            for name in sorted(filenames):
                path = os.path.join(dirpath, name)
                z.write(path, os.path.join("bigsat_example", os.path.relpath(path, EXAMPLE)))


def setup(app):
    app.connect("builder-inited", build_example)
