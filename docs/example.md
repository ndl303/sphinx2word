# Example document

The example is a complete Sphinx project that uses every feature of sphinx2word: an Algorithm Theoretical Basis
Document for BigSat, an imaginary satellite, with the front matter of a contract report. Each feature is shown
twice, first as the reStructuredText that makes it and then as the result, so you can see what to write and copy
it into your own documents. The comments in its `conf.py` explain every Word setting.

- **Download the project:** {download}`bigsat_example.zip <_generated/downloads/bigsat_example.zip>`
- **Download the Word document it makes:** {download}`bigsat_atbd.docx <_generated/downloads/bigsat_atbd.docx>`
- **Read it as HTML:** <a href="example/index.html">the example document</a>

The project is also in the repository, in
[`docs/example`](https://github.com/ndl303/sphinx2word/tree/main/docs/example).

```{note}
If the Word document offered here was made without Word, as on Read the Docs, Word asks to update the fields when
you open it. Answer **Yes** to fill in the table of contents, the lists of figures and tables, and the page numbers. On Windows with
Word and pywin32 installed, your own build fills them in for you (see
[word_update_fields](configuration.md#word_update_fields)).
```

## What it looks like in Word

These are pages of the Word document. The cover page and the change record come from `conf.py`. In the pages of
the document, each shaded code block is the reST of the result that follows it.

```{image} images/example-cover.png
:alt: The cover page
:width: 31%
:class: word-page
:target: _images/example-cover.png
```
```{image} images/example-text.png
:alt: Text features and their reST
:width: 31%
:class: word-page
:target: _images/example-text.png
```
```{image} images/example-math.png
:alt: Equations and their reST
:width: 31%
:class: word-page
:target: _images/example-math.png
```

## Build it yourself

Unzip the project and install sphinx2word with the extensions the example uses:

```bash
pip install sphinx2word sphinxcontrib-bibtex sphinx-argparse
```

The diagrams need [Graphviz](https://graphviz.org): install it so that its `dot` program is on the `PATH`.

Then build it as Word and as HTML from the folder that holds `bigsat_example`:

```bash
python -m sphinx -b word bigsat_example _build/word
python -m sphinx -b html bigsat_example _build/html
```

The Word document is `_build/word/bigsat_atbd.docx`, the name set by `word_filename`. On Windows, add
`pip install pywin32` to have Word fill in the contents and page numbers during the build.

## The files

| File                               | What it shows                                                                         |
|------------------------------------|---------------------------------------------------------------------------------------|
| `conf.py`                          | Every `word_*` setting, with a comment on each; the HTML build works without sphinx2word |
| `index.rst`                        | The master document: its title, the settings from `conf.py` it is built with, and the toctree |
| `introduction.rst`                 | Headings, the numbered toctree, `.. only:: word`, index entries, appendices and translated labels, page breaks, raw WordprocessingML, inline markup, colours, footnotes, citations, line blocks, quotes, definition, field and option lists, admonitions, topics and version notes |
| `inflightcalibration.rst`          | Figures in PNG and SVG, images in a table, nested and enumerated lists, every kind of table, and a landscape page |
| `instrument_model.rst`             | Inline and numbered equations, matrices, cases, aligned equations, macros, and math in tables and captions |
| `software.rst`                     | Code blocks with captions, line numbers and highlighted lines, `literalinclude`, doctest, Graphviz and inheritance diagrams, sphinx-argparse and autodoc |
| `bibliographies/bibliography.rst`  | The bibliography from `references.bib` (sphinxcontrib-bibtex)                         |
| `appendix_flatfield.rst`           | An appendix (`word_appendices`), numbered "Appendix A:"                               |
| `software/bigsat_cal.py`           | The small Python module documented by autodoc                                         |
| `figures/bigsat_patch.svg`         | The BigSat patch (and `bigsat_patch.png`, rendered from it)                           |
| `_ext/rst_example.py`              | The `rst-example` directive that shows the reST next to its result                    |

The `rst-example` directive is only there to show the source of each feature. Your documents do not need it: copy
the reST from the code blocks.

## conf.py

```{literalinclude} example/conf.py
:language: python
```

## index.rst

```{literalinclude} example/index.rst
:language: rst
```
