# Changelog

## Unreleased

- **Licence.** Still MIT; the copyright holder is now Nick Lloyd, who wrote sphinx2word in his own time. The
  README credits the projects it started from.

## 1.1.0 (2026-11-12)

### Changed

- **The contents and lists are filled in without Word.** The table of contents and the lists of figures and tables
  start out with their entries (numbers, titles and links to the headings and captions) instead of a "Right-click
  here" placeholder, so a document built without Word (Linux, GitLab CI) reads well before its fields are updated.
  Only the page numbers wait for Word. The entries are the starting text of Word's `TOC` fields; the headings and
  captions are unchanged, and Word rebuilds the contents and lists when it updates the fields. The indexes still
  wait for Word.
- **No field is marked dirty.** Whether Word updates the fields on opening is left to `word_update_fields`: with
  `"none"` the document now opens without updating anything, as documented.
- `tests/render_with_word.py` has a `--no-update` option, to see a document as it opens without an update.

## 1.0.2 (2026-11-06)

### Fixed

- **Code in some languages stopped the build.** YAML code blocks (and other lexers with token types that the
  Pygments style does not list, such as `Token.Literal.Scalar.Plain`) raised a `KeyError` when code colouring was
  on. Such tokens now take the colour of the nearest token type the style knows, as in Pygments' own formatters.
- **Figures with `*` instead of an extension were left out.** `figures/plot.*` now uses the first file that exists
  in the order SVG, PNG, JPEG, GIF, BMP, TIFF, as the other builders do.

## 1.0.1 (2026-11-05)

- **Documentation on GitLab Pages.** CI publishes the HTML documentation of `main`, with the example document, on
  the project's GitLab Pages (the `pages` job).

## 1.0.0 (2026-11-05)

A rewrite. sphinx2word now writes the `.docx` file itself instead of driving Microsoft Word through COM.

### Changed

- **No Word, COM or pywin32 needed** to make the document, so the builder runs on Windows, Linux and macOS,
  including CI.
- **Math** is converted from LaTeX to native Word equations by sphinx2word's own converter. Word's equation parser
  is no longer used, which fixes multi-line equations, column vectors and other equations that came out mixed up.
- **Packaging** is `pyproject.toml` only. The wheel is pure Python (`py3-none-any`). `setup.py`, `setup.cfg`,
  `MANIFEST.in` and `env.yml` were removed.
- **Development** uses uv (`uv.lock`, Python 3.12), Ruff and VS Code instead of conda and PyCharm. CI runs on the
  uv image and builds the documentation.
- **Licence.** MIT, with the University of Saskatchewan as the copyright holder.

### Added

- **Numbering and cross-references**
  - Captions, equation numbers and heading numbers are Word fields (`SEQ`, `STYLEREF`, numbered heading styles).
    `:numref:`, `:eq:`, `:ref:` and `:doc:` become `REF` cross-reference fields. Documents merged into larger Word
    documents are renumbered by them, and the references follow.
  - Captions are written like Word's Insert Caption ("Figure 1: …") by default, or with Sphinx's numbering
    (`word_caption_numbering = "sphinx"`).
  - Simple math in captions is written as formatted text, so it keeps its subscripts and superscripts in the
    lists of figures and tables.
- **Front matter**
  - A table of contents, list of figures and list of tables after the title page. On Windows with Word and pywin32
    installed, Word fills them in after the build, so the file opens without the "update fields" prompt
    (`word_update_fields`).
  - The front matter of contract reports: a cover page with contract lines, a figure, the title and a contributor
    list, then a distribution list and a change record. The change record comes from `conf.py` or from git tags.
    The front matter has roman page numbers, and there is an optional footer text.
- **Back matter**
  - Appendices: the documents of `word_appendices` go after the chapters, numbered "Appendix A:", A.1, A.1.1.
  - An index: `.. index::`, `:index:` and API entries become Word `XE` fields, and an `INDEX` field at the end
    lists them (`word_index`, `word_index_title`, `word_index_columns`).
  - A Python module index before the index (`word_module_index`).
- **Content**
  - Tables with column and row spans, header rows, and lists, math and images in cells. Column widths fit their
    longest word.
  - Word footnotes, bibliographies with aligned labels, admonition boxes, and autodoc and Breathe API entries.
  - Code highlighted with Pygments, with line numbers (`:linenos:`, `:lineno-start:`) and highlighted lines
    (`:emphasize-lines:`).
  - SVG images with PNG fallbacks, and Graphviz and inheritance diagrams, drawn as SVG by Graphviz.
- **Page layout.** Page breaks from `.. raw:: latex` `\newpage`, landscape pages for blocks with the class
  `landscape`, and raw WordprocessingML from `.. raw:: openxml`.
- **Language.** The default labels follow the project's `language` ("Inhaltsverzeichnis", "Abbildung", "Anhang"),
  unless `word_translate_labels = False`.
- **Styles and templates.** Every paragraph uses a named style. `word_template` takes styles, theme and heading
  numbering from a Word template.
- **Documentation** in Markdown, also built as HTML with Sphinx for Read the Docs. It includes an example project
  that shows every feature next to the reST that makes it, offered for download with the Word document it makes.
- **Tests.** A sample project, the example, and about 200 tests.

### Removed

- The COM-based modules (`wordobjectif.py`, the `*_context.py` modules, `wordapp_translator.py`, `word_writer.py`).

## 0.0.x

Earlier versions wrote the document by driving Word through COM. They are in the git history.
