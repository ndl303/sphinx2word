# Sphinx configuration for the sphinx2word sample document used by the tests.
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

project = "sphinx2word sample"
author = "ARG"
version = "2.0"
release = "2.0"
extensions = ["sphinx.ext.autodoc", "sphinx.ext.napoleon", "sphinx.ext.mathjax", "sphinx.ext.todo",
              "sphinx.ext.graphviz", "sphinx.ext.inheritance_diagram", "sphinx2word"]
master_doc = "index"
numfig = True
numfig_secnum_depth = 1
todo_include_todos = True
exclude_patterns = ["_build"]
rst_prolog = """
.. role:: raw-openxml(raw)
    :format: openxml
"""
word_appendices = ["appendix"]
word_math_macros = {"vect": [r"\mathbf{#1}", 1], "RR": r"\mathbb{R}"}
