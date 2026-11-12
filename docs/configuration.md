# Configuration

All settings go in the project's `conf.py` and all are optional. They only affect the `word` builder. Any of them
can also be set for one build on the command line, e.g. `python -m sphinx -b word -D word_toc=0 …`.

sphinx2word also reads several standard Sphinx settings: `project`, `version`, `author`, `master_doc`, `numfig`,
`numfig_format`, `numfig_secnum_depth`, `math_numfig`, `math_eqref_format`, `pygments_style`,
`highlight_language` and `mathjax3_config`.

## Page and output

| Setting               | Default    | Meaning                                                                       |
|-----------------------|------------|-------------------------------------------------------------------------------|
| `word_filename`       | `None`     | Output file name. Default `<project>-<version>.docx`                          |
| `word_paper_size`     | `"letter"` | `"letter"` or `"a4"`                                                          |
| `word_margins_inch`   | `1.0`      | Page margins in inches                                                        |
| `word_template`       | `None`     | A `.docx` or `.dotx` whose styles (and theme) are used, relative to `conf.py`. See [Word templates and styles](templates.md) |
| `word_chapter_page_break` | `True` | Start every `Heading 1` on a new page                                       |
| `word_table_style`    | `"SpxTable"` | Style id of the table style used for tables, for example a style from your template |
| `word_highlight_code` | `True`     | Colour code blocks with Pygments (using `pygments_style`)                     |

## Title page, contents and lists

| Setting                       | Default             | Meaning                                                      |
|-------------------------------|---------------------|--------------------------------------------------------------|
| `word_title_page`             | `True`              | Make a title page (title, version, author) from the master document's title |
| `word_toc`                    | `True`              | Insert a Word table of contents after the title page         |
| `word_toc_title`              | `"Contents"`        | Heading above the table of contents                          |
| `word_toc_depth`              | `3`                 | Heading levels shown in the table of contents                |
| `word_list_of_figures`        | `True`              | Insert a list of figures after the contents, if there are figure captions |
| `word_list_of_figures_title`  | `"List of Figures"` | Heading above the list of figures                            |
| `word_list_of_tables`         | `True`              | Insert a list of tables after the figures, if there are table captions |
| `word_list_of_tables_title`   | `"List of Tables"`  | Heading above the list of tables                             |
| `word_index`                  | `True`              | Insert a Word index at the end, if there are index entries   |
| `word_index_title`            | `"Index"`           | Heading above the index                                      |
| `word_index_columns`          | `2`                 | Number of columns of the index                               |
| `word_module_index`           | `True`              | Insert a Python module index before the index, if there are Python modules |
| `word_module_index_title`     | `"Python Module Index"` | Heading above the module index                           |
| `word_update_fields`          | `"auto"`            | How the contents and page numbers are filled in: `"auto"`, `"word"`, `"prompt"` or `"none"`. See [below](#word_update_fields) |

The contents and lists are only written when there is a title page. The title page, contents and lists are the
front matter, numbered i, ii, iii, …; the body starts at page 1.

### word_update_fields

| Value      | What happens                                                                                        |
|------------|-----------------------------------------------------------------------------------------------------|
| `"auto"`   | On Windows with Word and `pywin32`, Word fills in the contents, lists and page numbers after the build, and the file opens without a prompt. Otherwise Word asks to update the fields when the file is opened. |
| `"word"`   | As `"auto"`, but warn if Word or `pywin32` is missing                                               |
| `"prompt"` | Never run Word; Word always asks to update the fields when the file is opened                       |
| `"none"`   | Never run Word and never ask. The contents and lists show their entries without page numbers, and the indexes a placeholder, until you press **Ctrl+A, F9** in Word |

Without Word (Linux, CI) the document is still a single, complete file; see
[Building without Word](numbering.md#building-without-word-linux-ci).

## Appendices and language

| Setting                  | Default      | Meaning                                                                       |
|--------------------------|--------------|-------------------------------------------------------------------------------|
| `word_appendices`        | `[]`         | Documents that go after the chapters as appendices, with headings numbered "Appendix A:", A.1, A.1.1 (like `latex_appendices`) |
| `word_appendix_label`    | `"Appendix"` | The word before the appendix letter                                           |
| `word_translate_labels`  | `True`       | Write the default labels in the project's `language`: the titles of the contents, lists and indexes, the caption labels "Figure", "Table" and "Listing", "Appendix", and "see" in the index |

A document in `word_appendices` that is in the toctree is moved to the end; any other document is added there.
List the appendices at the end of the toctree as well, so that HTML shows them and Sphinx numbers their figures,
tables and equations (Sphinx only numbers those of documents in the toctree). Put `:orphan:` at the top of an
appendix that is not in the toctree, to avoid Sphinx's warning.

`word_translate_labels` only changes labels that are left at their English defaults; a label you set yourself, such
as `word_toc_title = "Table of Contents"`, is kept. The words come from a table like LaTeX's babel for German,
French, Spanish, Italian, Dutch, Portuguese, Swedish, Danish, Norwegian, Finnish, Polish and Czech, and otherwise
from Sphinx's own translations, which cover "Contents", "Index", "Python Module Index" and the caption labels for
many more languages. The front matter of contract reports is not translated (see `word_front_matter_labels`).

## Captions and numbering

| Setting                  | Default  | Meaning                                                                           |
|--------------------------|----------|-----------------------------------------------------------------------------------|
| `word_caption_numbering` | `"word"` | `"word"`: captions start like Word's Insert Caption (`Figure 1`), numbered through the document. `"sphinx"`: Sphinx's `numfig_format` and chapter numbers (`Fig. 4.1`) |
| `word_caption_separator` | `": "`   | Text between the caption number and the caption text (with `"word"` numbering)    |
| `word_caption_labels`    | `{}`     | Caption labels, which are also the names of the `SEQ` fields. Merged with `{"figure": "Figure", "table": "Table", "code-block": "Listing", "displaymath": "Equation"}` |

See [Numbering, captions and cross-references](numbering.md).

## Math

| Setting            | Default | Meaning                                                                                  |
|--------------------|---------|------------------------------------------------------------------------------------------|
| `word_math_macros` | `{}`    | LaTeX macros: `{"R": r"\mathbb{R}", "vect": [r"\mathbf{#1}", 1]}` (a definition, or a definition and its number of arguments) |

Macros in `mathjax3_config["tex"]["macros"]` are used as well, so math that renders in the HTML output also
renders in Word. See [Math](math.md).

## Contract reports

Setting any of `word_contract`, `word_cover_figure`, `word_prepared_by`, `word_reviewed_by`, `word_distribution`
or `word_change_record` replaces the plain title page with the cover page and front matter of a contract report.
See [Contract reports](contract-reports.md).

| Setting                    | Default | Meaning                                                                 |
|----------------------------|---------|-------------------------------------------------------------------------|
| `word_contract`            | `None`  | Lines above the cover figure, e.g. `["Project", "Contract No. 123"]` (a string may contain `\n`) |
| `word_cover_figure`        | `None`  | Image on the cover page, relative to `conf.py`                          |
| `word_cover_figure_width`  | `"3in"` | Width of the cover image (any reST length: `in`, `cm`, `mm`, `px`, `%`) |
| `word_document_title`      | `None`  | Title lines on the cover. Default: the master document's title          |
| `word_prepared_by`         | `[]`    | `[(name, function), ...]`                                               |
| `word_reviewed_by`         | `[]`    | `[(name, function), ...]`                                               |
| `word_distribution`        | `[]`    | `[(name, company), ...]`                                                |
| `word_change_record`       | `None`  | `"git"`, or a list of `(issue, revision, date, pages, description)` tuples or dicts with those keys |
| `word_change_record_tags`  | `"*"`   | With `"git"`: the tag names to list (an `fnmatch` pattern such as `"v1.*"`) |
| `word_change_record_notes` | `{}`    | With `"git"`: `{tag: description}` or `{tag: {"issue": ..., "pages": ..., "description": ...}}` |
| `word_front_matter_labels` | `{}`    | Headings and column titles of the front matter, e.g. `{"issue": "Issue"}` |
| `word_footer_text`         | `None`  | Footer text left of the page number. Default: the first line of `word_contract` |

## Example

```python
extensions = ["sphinx.ext.autodoc", "sphinx.ext.mathjax", "sphinxcontrib.bibtex", "sphinx2word"]
numfig = True

word_paper_size = "a4"
word_template = "_templates/company.dotx"
word_toc_depth = 2
word_caption_labels = {"code-block": "Code"}
word_math_macros = {"R": r"\mathbb{R}"}

word_contract = ["BigSat Phase B2/C/D", "Contract No. BS-26-001"]
word_cover_figure = "figures/bigsat_patch.png"
word_prepared_by = [("Ada Marsh", "Calibration Scientist")]
word_change_record = "git"
word_change_record_tags = "1.*"
```
