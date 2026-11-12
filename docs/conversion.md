# What is converted

sphinx2word combines the master document and everything in its toctree into one document, resolves the
references, and writes each node as WordprocessingML. This page lists what each construct becomes in Word.

## Document structure

- **Title page.** If the master document has a single top-level section, its title becomes the title page with
  the version and author. A [contract report](contract-reports.md) cover page replaces it when those settings are
  used. Set `word_title_page = False` to start directly with the content.
- **Front matter.** The table of contents, list of figures and list of tables follow the title page, each on a new
  page. The front matter is numbered i, ii, iii, …, and the body starts at page 1. They are Word `TOC` fields that
  start out with their entries (numbers, titles and links, without page numbers); Word rebuilds them, with page
  numbers, when it updates the fields. See [Numbering](numbering.md#filling-in-the-page-numbers-word_update_fields).
- **Sections** become `Heading 1` … `Heading 9`. The level follows the nesting: the top sections of the files in
  the master document's toctree are `Heading 1`. With `word_chapter_page_break` (the default) each `Heading 1`
  starts a new page.
- **Section numbers.** If the toctree is `:numbered:`, the heading styles are numbered by Word (1, 1.1, 1.1.1, …).
  See [Numbering](numbering.md).
- **Footer.** The page number, with `word_footer_text` on the left if it is set.

## Text

| reST / Sphinx                                         | Word                                                        |
|-------------------------------------------------------|-------------------------------------------------------------|
| Paragraphs                                            | `Normal` paragraphs                                         |
| `*emphasis*`, `**strong**`, ``` ``literal`` ```       | Italic, bold, `Spx Code Inline`                             |
| `:sub:`, `:sup:`                                      | Subscript, superscript                                      |
| Roles with a class such as `:red:` (from `s5defs.txt`) | Coloured text (red, green, orange, blue, purple, grey), strike-through |
| `:abbr:`                                              | The abbreviation followed by its explanation in parentheses |
| `:guilabel:`, `:menuselection:`                       | Italic                                                      |
| Line blocks (`\| line`)                               | Lines with their breaks and indentation kept                |
| Block quotes, attributions                            | Indented paragraphs                                         |
| Transitions (`----`)                                  | A horizontal rule                                           |
| `.. rubric::`                                         | `Spx Rubric`                                                |
| `.. centered::`                                       | A centred, bold paragraph                                   |

## Lists

| reST                                   | Word                                                                |
|----------------------------------------|---------------------------------------------------------------------|
| Bullet lists                           | Word bullet lists, nested to any depth                              |
| Enumerated lists (`1.`, `a)`, `(iv)`, …) | Word numbered lists in the same style; each list restarts at its own start number |
| Definition lists                       | `Spx Definition Term` and an indented definition                    |
| Field lists, option lists              | The field or option, then an indented body                          |
| `.. hlist::`                           | The items one after the other                                       |

## Links, references and notes

| reST / Sphinx                           | Word                                                                    |
|-----------------------------------------|-------------------------------------------------------------------------|
| External links                          | Hyperlinks                                                              |
| `:numref:`, `:eq:`                      | `REF` fields to the caption or equation number                          |
| `:ref:`, `:doc:` showing a heading's title | `REF` fields to the heading text                                     |
| Other internal links (API entries, labels with own text) | Hyperlinks to bookmarks                                |
| Footnotes (`[#]_`, `[1]_`)              | Word footnotes at the bottom of the page                                |
| Citations: reST `.. [Label]` and sphinxcontrib-bibtex | `Spx Bibliography` entries. Labels such as `[Bre77]` are on a hanging indent sized to the labels, and citations in the text link to the entries |

## Figures and images

- **Formats.** PNG, JPEG, GIF, BMP, TIFF and SVG.
- **SVG.** SVG images are embedded as SVG, which Word 2016 and later show. A PNG fallback is added for older
  versions: rendered with cairosvg if it is installed, otherwise a transparent placeholder.
- **Size.** Images use `:width:`, `:height:` and `:scale:`. Lengths can be in `px`, `pt`, `in`, `cm`, `mm`, `em`
  or `%`. Without them, images use their own size and resolution (Pillow reads the resolution of JPEG/GIF/BMP/TIFF;
  PNG and SVG are read directly).
- **Fit.** Images are shrunk to fit the text width and 90% of the page height.
- **Figures.** A figure is its image(s), side by side if there are several, followed by the caption and legend.
  `:align:` sets the alignment.
- **Any format (`figures/plot.*`).** As with the other builders, the first file that exists is used, in the order
  SVG, PNG, JPEG, GIF, BMP, TIFF.
- **Remote images** (`https://…`) are not downloaded. A red `[image: …]` placeholder and a warning are written
  instead.
- **Diagrams.** `sphinx.ext.graphviz` (`graphviz`, `graph`, `digraph`) and `sphinx.ext.inheritance_diagram` diagrams
  are drawn by Graphviz as SVG and inserted like images, in a figure with a caption if they have one. Graphviz's
  `dot` must be installed (`graphviz_dot` names it, as for the other builders); without it the diagram is left out
  with a warning.

## Tables

- **Kinds of table.** Grid and simple tables, `list-table` and `csv-table` become Word tables in `word_table_style`.
- **Header rows** repeat at the top of each page. Stub columns are bold and lightly shaded.
- **Spanned cells.** Column and row spans become merged cells.
- **Cell content.** Cells can hold several paragraphs, lists, math, images and nested tables.
- **Column widths.** `:widths:` gives proportional widths. Otherwise each column is wide enough for its longest
  word, as in the HTML output, and the rest of the width is shared in proportion to the column widths of the
  source table.
- **Captions.** A table with a title gets a caption above it.

## Code

- **Code blocks.** `code-block`, `literalinclude` and literal blocks (`::`) are shaded `Spx Code Block` paragraphs.
  They are coloured with Pygments in the `pygments_style` colours, unless `word_highlight_code = False` or the
  language is `text`/`none`.
- **Line numbers and emphasis.** `:linenos:` (or `literalinclude`'s `:lineno-match:`) puts grey line numbers before
  the lines, starting at `:lineno-start:`. `:emphasize-lines:` shades the chosen lines yellow.
- **Doctest blocks** are coloured as Python console sessions.
- **Captions.** A code block with `:caption:` gets a numbered "Listing" caption.

## Math

Inline and display math become Word equations. Numbered equations (`:label:`) have their number on the right and
can be referenced with `:eq:`. See [Math](math.md).

## Admonitions and topics

- **Admonitions.** `note`, `warning`, `tip`, `hint`, `important`, `attention`, `caution`, `danger`, `error`,
  `seealso`, `todo` and generic `admonition` become a shaded box with a coloured bar on the left and a title.
- **Colours.** Blue for notes, green for tips, orange for cautions, red for warnings, grey for todo.
- **Topics and sidebars** are boxes too. A `.. contents::` directive is left out, because Word makes its own table
  of contents.
- **Version notes.** `versionadded`, `versionchanged` and `deprecated` are paragraphs in italics.

## API documentation

- **Entries.** autodoc (with napoleon or numpydoc) and Breathe (Doxygen C/C++) entries become an `Spx API Signature`
  line followed by the description, indented.
- **Signatures.** In a signature, the name is bold, the parameters are listed in parentheses, and annotations and
  return types are kept.
- **Links.** Cross-references to API entries are hyperlinks.

## Index

- **Entries.** `.. index::` directives, the `:index:` role and the entries that domains make (autodoc functions and
  classes, for example) become Word index entries, `XE` fields. `single`, `pair` and `triple` entries give one,
  two or three entries with two levels, as in the LaTeX index; `see` and `seealso` give cross-references; a `!`
  before an entry (`!single: gain`) makes its page number bold.
- **The index** is an `INDEX` field at the end of the document, under `word_index_title`, in `word_index_columns`
  columns with a letter before each group. Word fills it in with the other fields. It is only added if there are
  entries; set `word_index = False` to leave it out.
- **The Python module index.** Each Python module (`py:module`, `automodule`) also gets an entry of its own entry
  type (`XE "name" \f "m"`), and an `INDEX \f "m"` field before the index lists them with their pages, as the
  LaTeX builder's module index does. Set `word_module_index = False` to leave it out.

## Appendices

The documents in `word_appendices` go after the chapters, before the indexes. Their headings are numbered by Word
"Appendix A:", A.1 and A.1.1 (three levels), separately from the chapters, and show so in the table of contents.
The appendix numbering is set on the heading paragraphs, not in the heading styles.

## Page layout

- **Page breaks.** `.. raw:: latex` that holds only `\newpage`, `\clearpage`, `\cleardoublepage` or `\pagebreak`
  starts a new page in Word too, so one source breaks the page in the PDF and in Word. Each `Heading 1` starts a
  new page anyway (`word_chapter_page_break`).
- **Landscape pages.** A block with the class `landscape` is put on landscape pages of its own: `.. rst-class::
  landscape` before a table or figure, or `.. container:: landscape` around several blocks. The text width is
  that of the landscape page. The page numbers continue. HTML and the other builders ignore the class.
- **Raw WordprocessingML.** `.. raw:: openxml` is copied into the document as it is: paragraphs (`<w:p>`) or tables
  (`<w:tbl>`) as a directive, runs (`<w:r>`) with a raw role inside a paragraph. It must be well-formed XML with
  the `w:` prefix; it is checked and left out with a warning if it is not. Other builders leave it out.

## Selecting content for Word

The builder's name and format are `word`, so `.. only:: word` includes content in the Word output only, and
`.. only:: not word` leaves it out.

## Skipped and unknown nodes

- **Skipped.** These produce no Word output, as in the LaTeX builder: comments, `.. raw::` for other formats (except
  page breaks), `meta`, substitution definitions, system messages and `productionlist`.
- **Unknown nodes,** for example from an extension sphinx2word does not know, are not dropped. Their content is
  written with the normal rules (paragraphs, text), and the build log names their types, so they can be given
  proper support.
