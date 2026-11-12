# sphinx2word documentation

| Page                                                     | Contents                                                           |
|----------------------------------------------------------|--------------------------------------------------------------------|
| [Configuration](configuration.md)                        | Every `word_*` setting in `conf.py`                                |
| [What is converted](conversion.md)                       | How each Sphinx and reST construct appears in Word, and the limits |
| [Math](math.md)                                          | The LaTeX supported in equations, macros, and what happens to errors |
| [Numbering, captions and cross-references](numbering.md) | Word fields, caption numbering, merging into larger documents, the "update fields" prompt |
| [Contract reports](contract-reports.md)                  | Cover page, contributor and distribution lists, change record from git |
| [Word templates and styles](templates.md)                | Using your own template, and the list of styles sphinx2word uses    |
| [Example document](example.md)                           | A complete Sphinx project that shows every feature, with its reST   |
| [Development](development.md)                            | Tests, code layout, checking the output in Word, CI and releases    |

Start with the [project README](../README.md) for installation and a quick start.

These pages are also built as HTML with Sphinx (`docs/conf.py`, `index.md`), for example on Read the Docs; see
[Development](development.md#the-documentation). `docs/example` is the example Sphinx project, described in
[Example document](example.md).
