# Numbering, captions and cross-references

The output of a Sphinx project is often copied into a larger Word document, so its numbers must behave like
numbers written in Word. sphinx2word writes every number as a Word field, the same fields that Word's own
**Insert Caption**, **Cross-reference** and numbered headings use:

- When the document is merged into a larger one, its figures, tables and headings are renumbered by that
  document, and the cross-references follow.
- Word's cross-reference dialog lists the captions and headings, so new references can be added in Word.
- **Insert Table of Figures** finds the captions.

Every field is written with its current result, so the document reads correctly before Word has updated anything.
Press **Ctrl+A, F9** in Word to update all fields after editing or merging.

## Headings

- **Numbering in the styles.** If the toctree is `:numbered:`, the numbering (1, 1.1, 1.1.1, …) belongs to the
  `Heading 1` … `Heading 9` styles. It is a multilevel list linked to the styles, as Word sets it up, and no number
  is typed into the heading text.
- **Your template's numbering.** If the heading styles of your [template](templates.md) already have numbering
  (for example "Chapter 1" or "A.1"), that numbering is used.
- **Merging.** When the content is pasted or inserted into another document with its styles ("use destination
  styles"), the headings take the numbering of the receiving document.
- **Unnumbered headings.** Headings that Sphinx does not number, for example from a toctree without `:numbered:`,
  switch the numbering off for that paragraph.
- **Mismatch warning.** The builder counts headings as Word will. It warns if Word would number a heading
  differently from Sphinx, which can happen with several numbered toctrees.

## Captions

Figures, tables and code blocks with a caption, and numbered equations, get Word caption numbers.

### Word numbering (the default)

`word_caption_numbering = "word"` writes captions as Word's Insert Caption does:

```
Figure {SEQ Figure \* ARABIC}: The caption text from Sphinx
Table {SEQ Table \* ARABIC}: ...
Listing {SEQ Listing \* ARABIC}: ...
({SEQ Equation \* ARABIC})                       equation numbers
```

How these captions behave:

- **Numbers:** they run 1, 2, 3, … through the whole document, separately for each label.
- **Format:** the Caption paragraph style formats the whole caption; sphinx2word adds no bold or other direct
  formatting.
- **Text:** Sphinx only gives the caption text.
- **Labels:** the labels, which are also the names of the `SEQ` fields, come from `word_caption_labels`. The
  defaults are `Figure`, `Table`, `Listing` and `Equation`. Word has `Figure`, `Table` and `Equation` built in.
  "Listing" is a custom label; Word handles it like the others, but it only appears in Word's caption dialog after
  you add it there.
- **Separator:** the text between the number and the caption text is `word_caption_separator` (`": "`).

The numbers in Word can differ from the HTML output. With `numfig_secnum_depth`, Sphinx numbers figures per
chapter ("Fig. 4.1"), while Word numbers them through the document ("Figure 7"). To number by chapter in Word,
edit the caption numbering in Word, or use Sphinx numbering.

### Sphinx numbering

`word_caption_numbering = "sphinx"` keeps Sphinx's `numfig_format` and chapter numbers. The caption label is
bold:

```
Fig. {STYLEREF 1 \s}.{SEQ Figure \* ARABIC \s 1}: The caption text
```

This is the form Word's Insert Caption writes with "Include chapter number". The chapter part follows the heading
numbering, so the headings must be numbered: the toctree must be `:numbered:`.

The builder counts the `SEQ` fields as Word will. If Word's count would differ from Sphinx's number (for example
equations that Sphinx numbers per file), that field gets a `\r` switch that sets the number.

## Cross-references

| Sphinx                                         | Word                                                                       |
|------------------------------------------------|----------------------------------------------------------------------------|
| `` :numref:`fig_x` `` (default text)           | `{REF _Ref… \h}` to the caption's label and number: "Figure 7", as Word's "Only label and number" |
| `` :numref:`see figure {number} <fig_x>` ``    | Sphinx's words, with the number as `{REF _Ref… \h}`                         |
| `` :eq:`label` ``                              | "(" `{REF _Ref… \h}` ")": the equation number                              |
| `` :ref:`label` `` to a section, `` :doc: ``   | `{REF _Ref… \h}` to the heading text                                       |
| `` :numref: `` to a numbered section           | `{REF _Ref… \w \h}`: the heading's full paragraph number                    |
| A `:ref:` with its own text, API references    | A hyperlink to a bookmark                                                  |

How the reference fields behave:

- **Clicking:** `\h` makes each reference clickable, like a hyperlink.
- **Formatting:** `\* CHARFORMAT` keeps the formatting of the surrounding text. Without it, a reference would turn
  bold when updated, copying the caption label.
- **Bookmarks:** the bookmarks are hidden `_Ref…` bookmarks, like the ones Word makes, so they do not clutter the
  Bookmark dialog.

## Table of contents and lists of figures and tables

After the title page come:

- the **contents**: a `TOC \o "1-3" \h \z \u` field, with the depth set by `word_toc_depth`;
- a **list of figures** and a **list of tables**: `TOC \h \z \c "Figure"` and `TOC \h \z \c "Table"` fields.

Each starts on a new page. A list is only added if the document has captions of that kind.
`word_list_of_figures` and `word_list_of_tables` turn the lists off. The entries use Word's `TOC 1` … and
`table of figures` styles.

## Filling in the page numbers: `word_update_fields`

Page numbers depend on Word's page layout, which only Word can compute. sphinx2word writes the table of contents
and the lists of figures and tables with their entries (numbers, titles, and links to the headings and captions)
but without page numbers. The indexes are left to Word: until it updates them they hold a placeholder.

The page numbers and the indexes are filled in in one of two ways:

- **On Windows with Word and pywin32 installed:** the builder finishes the document in Word.
  1. It opens the file once in a hidden Word.
  2. Word updates every field and saves the file.
  3. The builder removes the "update fields when opened" flag.

  The document then opens with no prompt. This adds a few seconds to the build.
- **Otherwise** (no Word, no pywin32, Linux or macOS, CI): the document is complete and readable as it is, and it
  asks Word to update its fields when it is first opened. Answer **Yes** to add the page numbers and fill in the
  indexes, or **No** to read it as it is.

pywin32 is never installed with sphinx2word. Install it yourself (`pip install pywin32`, or the shortcut
`pip install sphinx2word[word]`) on machines where you want the finished, prompt-free document.

| `word_update_fields` | Behaviour                                                                                       |
|----------------------|-------------------------------------------------------------------------------------------------|
| `"auto"` (default)   | Use Word if it and pywin32 are available; otherwise prompt on opening                           |
| `"word"`             | As `"auto"`, but warn if Word or pywin32 is missing                                             |
| `"prompt"`           | Never run Word; always prompt on opening                                                        |
| `"none"`             | Never run Word and never prompt. The contents and lists show their entries without page numbers, and the indexes a placeholder, until the fields are updated (**Ctrl+A, F9**) |

### Building without Word (Linux, CI)

A document built without Word, for example in a CI job on Linux (GitHub Actions, GitLab CI), is a single,
complete `.docx` file:

- **Self-contained.** The images, the styles (including those of `word_template`) and all the text are inside the
  file. It does not refer to other files; only web links point outside it.
- **The prompt.** When the file asks to update its fields, Word's prompt says "This document contains fields that
  may refer to other files". Word uses that wording for every document that asks for an update. Nothing outside the
  file is read: updating only lays out the pages and fills in the page numbers and the indexes.
- **Readable as it is.** The contents and the lists of figures and tables already show their entries, so the
  document reads well even if nobody updates its fields. Only the page numbers are missing.
- **Still Word's to number and style.** The prefilled entries are only the starting text of Word's `TOC` fields.
  The headings keep their `Heading 1`–`9` styles and heading numbering, and the captions keep their `SEQ` fields.
  When Word updates the fields (on opening, with **Ctrl+A, F9**, or after the document is merged into a larger
  one), it rebuilds the contents and lists from the headings and captions, with page numbers. Merging and
  restyling work as for a document that Word finished.

For documents built in CI, it can be best to open without a prompt and to leave out the indexes, which would only
show a placeholder there. GitHub Actions and GitLab CI set the `CI` environment variable in their jobs, so
`conf.py` can do this for CI builds only:

```python
import os

if os.environ.get("CI"):              # a CI job (Linux, no Word)
    word_update_fields = "none"       # no prompt; the contents and lists show their entries
    word_index = False                # no index, which needs Word to fill in
    word_module_index = False
```

Word cannot open a file that is already open, and the builder cannot overwrite one either. Close the document in
Word before rebuilding it, or the build warns that it cannot write the file.
