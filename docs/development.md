# Development

## Setting up

The group uses [uv](https://docs.astral.sh/uv/) for Python environments. `uv.lock` pins the development
environment and `.python-version` asks for Python 3.12. To create or update `.venv`:

```bash
uv sync
uv run python -m pytest
```

`uv sync` installs sphinx2word in editable mode with the `dev` and `docs` dependency groups from `pyproject.toml`:
pytest, Pillow, cairosvg, PyMuPDF, sphinxcontrib-bibtex and sphinx-argparse, pywin32 on Windows, and MyST-Parser,
pydata-sphinx-theme and sphinx-copybutton for the documentation. pywin32 (with Word installed) runs the optional tests
that open the output in Word and the step that fills in the table of contents.

The tests and the example also need [Graphviz](https://graphviz.org) (`dot`), which is not a Python package: install
it with your system's package manager (`apt-get install graphviz`) or the Windows installer, and put `dot` on the
`PATH`. CI and Read the Docs install it.

After changing the dependencies in `pyproject.toml`, run `uv lock` and commit `uv.lock` with the change.

All the packaging and tool settings are in `pyproject.toml`; there is no `setup.cfg` or `MANIFEST.in`.
`uv build` makes the sdist and wheel, and setuptools_scm sets the version from the git tags. Style checks use
Ruff (`uvx ruff check`), with its E and W style rules.

`.vscode/` holds the VS Code settings, with launch configurations that build the example as HTML or Word, and the
documentation, under the debugger.

## The documentation

The documentation is the Markdown files in `docs/`. They read well on GitHub and GitLab, and Sphinx builds them as HTML with
MyST-Parser and the pydata theme (`docs/conf.py`; `index.md` includes the project README):

```bash
uv run python -m sphinx -b html docs docs/_build/html
```

Before the pages are read, `docs/conf.py` builds the example (below) as a Word document and as HTML, and zips its
source, in `docs/_generated/`. `example.md` offers the zip and the `.docx` for download and links to the HTML. The
example is only rebuilt when it or sphinx2word changed; set `SPHINX2WORD_SKIP_EXAMPLE=1` to skip it. On Windows with
Word and pywin32, the `.docx` has its fields filled in; elsewhere Word asks to update them when it is opened.

The `ci.yml` workflow builds it with warnings as errors and publishes the HTML of `main` on GitHub Pages.
`.readthedocs.yaml` can build it on Read the Docs instead, installing the `docs` group with uv from `uv.lock`.

## The example document

`docs/example` is an example document: an Algorithm Theoretical Basis Document for BigSat, an imaginary satellite.
It uses every feature of the Word builder, with contract-report front matter, and its `conf.py` shows every
`word_*` setting with a comment. Each feature is shown as its reST and then the result, using the small
`rst-example` directive in `docs/example/_ext/rst_example.py`. Build it from `docs/`:

```bash
uv run python -m sphinx -b word example _build/word
uv run python -m sphinx -b html example _build/example-html
```

The Word document is `_build/word/bigsat_atbd.docx`. The HTML build works without sphinx2word, and uses
pydata-sphinx-theme if it is installed, otherwise alabaster. `tests/test_example.py` checks that it builds without
warnings. Keep the reST inside `rst-example` blocks, and `conf.py`, to 88 characters a line, or they wrap in Word's code
blocks. `index.rst` shows the Project, General and Word parts of `conf.py` with `literalinclude`, so the document
always shows the settings it was built with; it uses a rubric, not a section, because a section in the master
document would hold all the chapters of the toctree that follows it.

The BigSat patch, `figures/bigsat_patch.svg`, was drawn for this project; `bigsat_patch.png` is rendered from it
with cairosvg. Word does not draw SVG `<textPath>`, so its lettering is one rotated `<text>` per letter.

The pictures of Word pages on the example page, `docs/images/example-*.png`, are made by
`docs/make_example_images.py` (Windows with Word). It picks the pages by a heading on them. Run it after changing the
example, and look at the pictures.

## Tests

`tests/sample` is a small Sphinx project that uses every feature: lists, footnotes, citations, tables with spans,
figures (PNG and SVG), numbered and aligned equations, code, admonitions, autodoc and cross-references. The tests
build it with the `word` builder, in several configurations, and check the `.docx` package:

- **The package:** every XML part is well-formed, images are packaged, and template styles are merged.
- **References:** every internal link and `REF` field has its bookmark, and every bookmark is closed.
- **Footnotes** are referenced from the text. Word reports a file as damaged if they are not.
- **Fields:**
  - captions, equations and references are Word fields;
  - Word's caption numbering and Sphinx's numbering both give the right numbers;
  - headings are numbered by the heading styles.
- **Front matter:** the lists of figures and tables, the contract-report cover and front matter, and the page
  numbering of the sections.
- **Bibliography:** entries line up on the hanging indent.
- **Change record from git,** in a throwaway repository with lightweight, annotated and off-branch tags.

`tests/test_latex2omml.py` converts about 70 LaTeX expressions, inline and display, and checks the structure of the
OMML for the cases that used to go wrong.

Two tests need Windows with Word and pywin32, and are skipped otherwise:
- one opens the sample in Word, to catch files that Word would call damaged;
- one lets Word fill in the table of contents.

The sample builds use `word_update_fields = "prompt"`, so the rest of the suite does not start Word.

The package requires Python 3.8+ and Sphinx 5 or later. The tests have been run on Python 3.12 with Sphinx 9.1, and
on Python 3.9 with Sphinx 5.3 and docutils 0.17.

## Checking the output in Word

The tests check the XML, but how Word lays it out is the real test. `tests/render_with_word.py` (Windows, Word,
pywin32 and pymupdf) opens a `.docx` in Word, updates the fields, saves it as PDF and renders each page as a PNG
image:

```bash
python tests/render_with_word.py docs/_build/word/project-1.0.docx [outdir]
```

## Code layout

| File                          | Purpose                                                                         |
|-------------------------------|---------------------------------------------------------------------------------|
| `sphinx2word/__init__.py`     | `setup()`: registers the builder and the `word_*` settings                      |
| `sphinx2word/builder.py`      | The `word` builder: combines the toctree into one doctree, resolves references, writes the file |
| `sphinx2word/translator.py`   | The docutils visitor that turns doctree nodes into WordprocessingML              |
| `sphinx2word/latex2omml.py`   | The LaTeX to Office Math (OMML) converter                                       |
| `sphinx2word/docx_package.py` | Styles, numbering, footnotes, relationships, sections and the zip package       |
| `sphinx2word/git_history.py`  | The change record from git tags                                                  |
| `sphinx2word/word_finish.py`  | The optional last step that lets Word fill in the fields (Windows, pywin32)       |

How a build runs:

1. The builder uses `inline_all_toctrees` to combine the master document and its toctree into one doctree, as the
   LaTeX builder does, and resolves its references. Links between files point at a bookmark at the start of each
   file.
2. `WordTranslator` walks the tree.
   - **Before rendering,** it collects every numbered figure, table, code block, equation and section, so that
     forward references can be written as `REF` fields with the right numbers.
   - **Paragraph content** is collected in a `Paragraph` object until the paragraph closes.
   - **Composite blocks** (table cells, admonitions, numbered equations, footnotes) are rendered by walking their
     children into a separate block list.
3. `DocxPackage` writes the parts and zips them.
4. `word_finish` optionally lets Word update the fields.

Earlier versions of sphinx2word drove Word through COM to build the whole document. That code was removed in 1.0;
it is in the git history.

## Continuous integration and releases

GitHub Actions runs two workflows (`.github/workflows/`):

| Workflow      | When                                  | What                                                          |
|---------------|---------------------------------------|---------------------------------------------------------------|
| `ci.yml`      | pushes to `main`, pull requests       | Run the tests (with Graphviz), build the sample with `-b word` (the `.docx` is kept as an artifact), and build the documentation with warnings as errors; for `main`, publish the documentation on GitHub Pages |
| `release.yml` | a version tag such as `1.2.0`         | Build the sdist and the wheel (pure Python, `py3-none-any`) and publish them on PyPI |

The version comes from git tags through setuptools_scm. Tag `X.Y.Z` on `main` for a release; untagged commits get
a development version such as `1.0.1.dev3+g1234abc`. The workflows check out the whole history
(`fetch-depth: 0`), so the tags are there and the version is right.

To release:

1. Add the version and its date to `CHANGELOG.md` and merge the work into `main`.
2. Tag `main` and push the tag: `git tag -a 1.2.0 -m "sphinx2word 1.2.0"`, then `git push origin 1.2.0`.
3. `release.yml` publishes the release on PyPI. It uses PyPI's Trusted Publishing, so no API token is stored: the
   project on pypi.org has this repository's `release.yml` and the environment `pypi` as its trusted publisher.
   For the very first release, add a "pending publisher" with those details on pypi.org before pushing the tag.

GitHub Pages must be set to publish from GitHub Actions (Settings > Pages > Source).
