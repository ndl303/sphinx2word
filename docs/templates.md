# Word templates and styles

Everything sphinx2word writes uses named Word styles, with as little direct formatting as possible. The look of the
document can therefore be changed in Word, by editing the styles, or before the build, with a template.

## Using a template

1. Make or open a document in Word and change the styles you care about. For example `Normal`, `Heading 1` …,
   `Title`, `Caption`, `Spx Code Block`, the table style, or the heading numbering (Home → Multilevel List, linked
   to the heading styles).
2. Save it as a `.dotx` template or a `.docx` document, next to `conf.py` or in `_templates`.
3. Point `conf.py` at it:

   ```python
   word_template = "_templates/company.dotx"     # relative to conf.py
   ```

From the template sphinx2word takes:

- the **styles** (`word/styles.xml`). Styles that sphinx2word uses but the template does not define are added with
  their default look, so the template only needs the styles you want to change;
- the **theme** (colours and theme fonts) and the **font table**.

The template's text, headers, footers and page setup are not used. The page size and margins come from
`word_paper_size` and `word_margins_inch`.

To use a table style of the template for all tables, give its style id:

```python
word_table_style = "GridTable4-Accent1"
```

The style id is the style's name without spaces; Word shows the name in the Table Design gallery.

## Heading numbering

If the template's `Heading 1` … `Heading 9` styles already have numbering, it is kept: chapters can be "Chapter 1",
"A", "1.0", or anything Word allows. If they have none and the toctree is `:numbered:`, sphinx2word links a 1, 1.1,
1.1.1 numbering to the heading styles. See [Numbering](numbering.md).

## The styles sphinx2word uses

Word's built-in styles:

| Style                                   | Used for                                                       |
|-----------------------------------------|----------------------------------------------------------------|
| `Normal`                                | Body text                                                      |
| `Title`, `Subtitle`                     | The plain title page                                           |
| `Heading 1` … `Heading 9`               | Section headings                                               |
| `TOC Heading`                           | Headings of the contents and the lists of figures and tables   |
| `TOC 1` … `TOC 6`, `table of figures`   | Entries of the contents and of the lists                       |
| `caption`                               | Figure, table and code captions                                |
| `List Paragraph`                        | List items                                                     |
| `footnote text`, `footnote reference`   | Footnotes                                                      |
| `Hyperlink`                             | External links (character style)                               |
| `footer`                                | The page footer                                                |

sphinx2word's own styles, whose names all start with `Spx`:

| Style                      | Type      | Used for                                                    |
|----------------------------|-----------|-------------------------------------------------------------|
| `Spx Code Block`           | paragraph | Code blocks and literal blocks                              |
| `Spx Code Inline`          | character | ``` ``inline code`` ``` and literal roles                   |
| `Spx Figure`               | paragraph | The paragraph holding a figure's image                      |
| `Spx Equation`             | paragraph | Display equations                                           |
| `Spx Table Text`           | paragraph | Text in table cells                                         |
| `Spx Table`                | table     | Tables (default of `word_table_style`)                      |
| `Spx Admonition Title`     | paragraph | Titles of notes, warnings and topics                        |
| `Spx Rubric`               | paragraph | `.. rubric::` and other titles that are not headings         |
| `Spx Definition Term`      | paragraph | Terms of definition lists                                   |
| `Spx API Signature`        | paragraph | autodoc / Breathe signature lines                           |
| `Spx Bibliography`         | paragraph | Bibliography entries                                        |
| `Spx Cover Title`          | paragraph | Contract and title lines of a [contract report](contract-reports.md) cover |
| `Spx Cover Figure`         | paragraph | The cover figure                                            |
| `Spx Front Heading`        | paragraph | Contributor List, Distribution List, Change Record          |
| `Spx Front Table Text`     | paragraph | Text in the front-matter tables                             |

Some things are direct formatting rather than styles, because they depend on the content:
- the colours of highlighted code;
- the coloured bar and shading of admonition boxes;
- the colours of `:red:`-style roles;
- the widths of table columns.

## Without a template

The built-in styles use Calibri for text and Calibri Light for headings, with dark-blue headings, on Letter paper
with 1 inch margins (`word_paper_size = "a4"` for A4).
