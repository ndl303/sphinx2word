"""
sphinx2word: a Sphinx builder that writes Microsoft Word (.docx) documents directly.

Add ``"sphinx2word"`` to ``extensions`` in ``conf.py`` and build with ``sphinx-build -b word <src> <out>``.
"""

from .builder import WordBuilder

try:
    from ._version import version as __version__
except ImportError:      # pragma: no cover - not installed from a git checkout
    __version__ = "0.0.0"


def setup(app):
    app.add_builder(WordBuilder)
    app.add_config_value("word_template", None, "env")             # .docx/.dotx whose styles are used
    app.add_config_value("word_paper_size", "letter", "env")       # "letter" or "a4"
    app.add_config_value("word_margins_inch", 1.0, "env")
    app.add_config_value("word_title_page", True, "env")           # title page from the master document title
    app.add_config_value("word_toc", True, "env")                  # Word table of contents after the title page
    app.add_config_value("word_toc_title", "Contents", "env")
    app.add_config_value("word_toc_depth", 3, "env")
    # "auto": fill in the contents and page numbers with Word if it is installed (no prompt when the file is
    # opened), otherwise Word asks to update fields on opening; "word": the same, but warn without Word;
    # "prompt": always ask on opening; "none": never ask (the contents stay empty until fields are updated)
    app.add_config_value("word_update_fields", "auto", "")
    app.add_config_value("word_list_of_figures", True, "env")      # Word table of figures after the contents
    app.add_config_value("word_list_of_figures_title", "List of Figures", "env")
    app.add_config_value("word_list_of_tables", True, "env")       # Word table of tables after the figures
    app.add_config_value("word_list_of_tables_title", "List of Tables", "env")
    app.add_config_value("word_index", True, "env")                # Word index at the end, if there are entries
    app.add_config_value("word_index_title", "Index", "env")
    app.add_config_value("word_index_columns", 2, "env")
    app.add_config_value("word_module_index", True, "env")         # Python module index, if there are modules
    app.add_config_value("word_module_index_title", "Python Module Index", "env")
    app.add_config_value("word_appendices", [], "env")             # documents at the end, numbered A, B, C
    app.add_config_value("word_appendix_label", "Appendix", "env")
    # Default labels ("Contents", "Figure", "Appendix", ...) in the project's language
    app.add_config_value("word_translate_labels", True, "env")
    app.add_config_value("word_chapter_page_break", True, "env")   # start each Heading 1 on a new page
    app.add_config_value("word_table_style", "SpxTable", "env")    # styleId of the table style
    app.add_config_value("word_highlight_code", True, "env")       # colour code blocks with Pygments
    app.add_config_value("word_math_macros", {}, "env")            # {"R": r"\mathbb{R}", "v": [r"\mathbf{#1}", 1]}
    app.add_config_value("word_filename", None, "env")             # default: <project>-<version>.docx
    # Word caption labels (SEQ field identifiers) of numbered items, e.g. {"code-block": "Listing"}
    app.add_config_value("word_caption_labels", {}, "env")
    # "word": captions are "Figure 1" as Word's Insert Caption writes them; "sphinx": numfig_format and chapter numbers
    app.add_config_value("word_caption_numbering", "word", "env")
    app.add_config_value("word_caption_separator", ": ", "env")    # between the caption number and the caption text

    # Front matter of a contract report. Setting any of these replaces the plain title page.
    app.add_config_value("word_contract", None, "env")             # lines above the cover figure (str or list)
    app.add_config_value("word_cover_figure", None, "env")         # image on the cover, relative to conf.py
    app.add_config_value("word_cover_figure_width", "3in", "env")
    app.add_config_value("word_document_title", None, "env")       # default: title of the master document
    app.add_config_value("word_prepared_by", [], "env")            # [(name, function), ...]
    app.add_config_value("word_reviewed_by", [], "env")            # [(name, function), ...]
    app.add_config_value("word_distribution", [], "env")           # [(name, company), ...]
    app.add_config_value("word_change_record", None, "env")        # "git" or [(issue, rev, date, pages, text), ...]
    app.add_config_value("word_change_record_tags", "*", "env")    # with "git": tag names to list (fnmatch)
    app.add_config_value("word_change_record_notes", {}, "env")    # with "git": {tag: description or dict}
    app.add_config_value("word_front_matter_labels", {}, "env")    # headings / column titles, e.g. {"issue": "Issue"}
    app.add_config_value("word_footer_text", None, "env")          # footer text left of the page number
    return {"version": __version__, "parallel_read_safe": True, "parallel_write_safe": False}
