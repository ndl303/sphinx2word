# Sphinx configuration for the sphinx2word example document.
#
# The document shows every feature of the word builder next to the reStructuredText
# that makes it, using BigSat, an imaginary satellite, as its subject. index.rst shows
# the Project, General and Word parts of this file. Build it from the folder that holds
# this one:
#
#     python -m sphinx -b word example _build/word
#     python -m sphinx -b html example _build/html
#
# Lines are kept to 88 characters, so they do not wrap in the Word document.
import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
# sphinx2word from its repository, if this folder is in it
sys.path.insert(0, os.path.join(HERE, "..", ".."))
# bigsat_cal, documented by autodoc
sys.path.insert(0, os.path.join(HERE, "software"))
# rst_example: the directive that shows the reST next to the result
sys.path.insert(0, os.path.join(HERE, "_ext"))

# -- Project ---------------------------------------------------------------------------

project = "BigSat In-Flight Calibration"
author = "BigSat Science Team"
copyright = "2026, BigSat Science Team"
version = "1.2"
release = "1.2.0"
language = "en"

# -- General ---------------------------------------------------------------------------

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.mathjax",
    "sphinx.ext.todo",
    "sphinxcontrib.bibtex",
    "sphinxarg.ext",
    "sphinx.ext.graphviz",
    "sphinx.ext.inheritance_diagram",
    "rst_example",
]
# Use the word builder when sphinx2word is installed, so HTML builds without it.
if importlib.util.find_spec("sphinx2word") is not None:
    extensions.append("sphinx2word")

master_doc = "index"
source_suffix = ".rst"
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]
templates_path = ["_templates"]

numfig = True               # number figures, tables and code blocks with captions
numfig_secnum_depth = 1     # used by word_caption_numbering = "sphinx" and in HTML
math_numfig = True
todo_include_todos = True
add_function_parentheses = False
add_module_names = False
pygments_style = "sphinx"   # also the colours of code in Word

# Coloured text roles such as :red:`text` (s5defs.txt defines them) and a
# strike-through role. Word colours red, green, orange, blue, purple and gray;
# sksoftware.css colours them in HTML.
rst_prolog = """
.. include:: <s5defs.txt>
.. role:: strike
"""

bibtex_bibfiles = ["bibliographies/references.bib"]
bibtex_reference_style = "author_year"

# LaTeX macros for the HTML output. sphinx2word reads them too, so the same math
# works in Word.
mathjax3_config = {
    "tex": {
        "macros": {
            "vect": [r"\mathbf{#1}", 1],
            "RR": r"\mathbb{R}",
            "degC": r"{}^{\circ}\mathrm{C}",
        }
    }
}

# -- HTML ------------------------------------------------------------------------------

if importlib.util.find_spec("pydata_sphinx_theme"):
    html_theme = "pydata_sphinx_theme"
else:
    html_theme = "alabaster"
html_logo = "figures/bigsat_patch.png"
html_favicon = "_static/bigsat_icon_32.ico"
html_static_path = ["_static"]
html_css_files = ["sksoftware.css"]

# -- Word (sphinx2word) ----------------------------------------------------------------
# Every setting is optional; see the Configuration page of the sphinx2word
# documentation. The commented ones show the default or an alternative.

# Page and output
word_filename = "bigsat_atbd.docx"    # default: "<project>-<version>.docx"
word_paper_size = "letter"            # or "a4"
word_margins_inch = 1.0
# word_template = "_templates/company.dotx"   # the styles of your own template
word_chapter_page_break = True        # each Heading 1 starts a new page
# word_table_style = "SpxTable"
word_highlight_code = True            # colour code with Pygments

# Title page, contents and lists
word_toc = True
word_toc_title = "Contents"
word_toc_depth = 2
word_list_of_figures = True           # only written if there are figure captions
word_list_of_tables = True            # only written if there are table captions
# With Word and pywin32, Word fills in the contents and page numbers after the build
word_update_fields = "auto"

# Indexes at the end: the Python modules, then everything else (if there are entries)
word_module_index = True
word_module_index_title = "Python Module Index"
word_index = True
word_index_title = "Index"
word_index_columns = 2

# Appendices: these documents go after the chapters, numbered "Appendix A:", A.1, ...
word_appendices = ["appendix_flatfield"]
word_appendix_label = "Appendix"

# Labels left at their English defaults ("Contents", "Figure", "Index", "Appendix")
# are written in the language of the project (language = "de": "Inhaltsverzeichnis",
# "Abbildung", ...). False keeps them in English.
word_translate_labels = True

# Captions and numbering
word_caption_numbering = "word"       # "Figure 3"; "sphinx" gives "Fig. 2.1"
word_caption_separator = ": "
word_caption_labels = {"code-block": "Listing"}

# Math macros for Word, in addition to those in mathjax3_config. A macro defined in
# both uses this definition in Word: here the degree sign is one character, which
# looks better in Word than {}^{\circ}.
word_math_macros = {"degC": r"\mathrm{°C}"}

# Contract report: cover page, contributor and distribution lists, change record
word_contract = ["BigSat Phase B2/C/D", "Contract No. BS-26-001"]
word_cover_figure = "figures/bigsat_patch.png"
word_cover_figure_width = "2.5in"
word_document_title = ["Algorithm Theoretical Basis Document:",
                       "BigSat In-Flight Calibration"]
word_prepared_by = [("Ada Marsh", "Calibration Scientist"),
                    ("Ben Okafor", "Instrument Engineer")]
word_reviewed_by = [("Clara Voss", "Principal Investigator"),
                    ("Dev Raman", "Project Manager")]
word_distribution = [("J. Smith", "Example Space Agency"), ("R. Patel", "Example Aerospace Ltd")]
word_footer_text = "BigSat Phase B2/C/D"
# The change record can also come from the git tags: word_change_record = "git"
word_change_record = [
    ("1", "0", "2025-06-12", "All", "First issue for the preliminary design review"),
    ("1", "1", "2025-11-03", "4, 7", "Moon and star calibration added"),
    {"issue": "1", "revision": "2", "date": "2026-02-20", "pages": "All",
     "description": "Updated after the critical design review"},
]
