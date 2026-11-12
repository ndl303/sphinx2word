############################
Sphinx2Word Example
############################

This document provides an example of documents produced by
`sphinx2word <https://github.com/ndl303/sphinx2word>`_: it illustrates every feature of the Word
builder along with the corresponding reStructuredText. The comments in ``conf.py`` explain the Word
settings.

..  rubric:: Settings in conf.py

A section here would hold the chapters of the toctree below, so this heading is a ``rubric``. The
Word document is shaped by the settings in ``conf.py``. Without the contract-report settings, the
title of this master document would become the title page. Here the cover page of a contract report
replaces it: its title comes from ``word_document_title``, and the contributor and distribution lists
and the change record come from the settings after it.

The project and general settings used for this document. ``project`` and ``version`` would name the
Word file if ``word_filename`` were not set, ``numfig`` numbers the captions, and ``rst_prolog`` and
``mathjax3_config`` give the colour roles and math macros used in the examples:

..  literalinclude:: conf.py
    :language: python
    :start-at: project =
    :end-before: # -- HTML

The Word settings. Each one is described on the Configuration page of the sphinx2word documentation:

..  literalinclude:: conf.py
    :language: python
    :start-at: # Every setting is optional

..  toctree::
    :numbered:
    :maxdepth: 2
    :caption: Contents

    introduction
    inflightcalibration
    instrument_model
    software
    bibliographies/bibliography
    appendix_flatfield

..  only:: html

    ..  rubric:: Indices and tables

    * :ref:`genindex`
    * :ref:`modindex`
    * :ref:`search`
