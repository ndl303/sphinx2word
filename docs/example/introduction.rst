..  _chap_introduction:

############
Introduction
############
This document is used to showcase the features of ``sphinx2word``. We are illustrating the examples on an HTML page but
keep in mind that we are really showing features for Word output. Each feature is shown twice: first the source
reStructuredText and second the resultant word output.

If you are interested, the example blocks shown in this document are made by a small directive, ``rst-example``, which
invokes a python subroutine, ``_ext/rst_example.py``, to display the Word output in HTML. You do not need this function
for your Sphinx-to-Word projects. We first summarize the various features available and then use an example project,
BigSat, to illustrate the features in a realistic scenario.

Document Structure
==================

Headings
--------

Sections become Word's ``Heading 1`` to ``Heading 9`` styles. The level follows the nesting of the sections, not the
characters used to underline them. This document uses these underlines; the toctree in ``index.rst`` is
``:numbered:``, so Word numbers the headings 1, 1.1, 1.1.1:

..  code-block:: rst

    ############
    Introduction
    ############

    Document Structure
    ==================

    Headings
    --------

    Normalization
    ^^^^^^^^^^^^^

Contents and Numbering
----------------------

The toctree of the master document, ``index.rst``, lists the chapters; they become one Word
document. The option ``:numbered:`` makes Word number the headings, through the numbering of the
heading styles. This is the toctree of this document; it is shown as a code block because a toctree
only works in the master document:

..  code-block:: rst

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

Word makes its own table of contents after the title page, with ``word_toc_depth`` heading levels.
The ``:caption:`` and ``:maxdepth:`` of the toctree are only used in HTML.

Content for Word Only
---------------------

The directive ``only`` selects content for some builders. The Word builder's name is ``word``, so
``only:: word`` puts content in the Word document only and ``only:: not word`` leaves it out:

..  rst-example::

    ..  only:: word

        This paragraph is only in the Word document.

    ..  only:: not word

        This paragraph is in every output except the Word document.

Index Entries
-------------

The ``index`` directive and the ``:index:`` role make Word index entries (``XE``
fields). The index itself is at the end of the document, where Word fills it in; see
``word_index``, ``word_index_title`` and ``word_index_columns`` in ``conf.py``. Python
modules (``py:module``, ``automodule``) also get a Python Module Index before it
(``word_module_index``). A ``!`` before an entry makes its page number bold, for the
main entry:

..  rst-example::

    ..  index::
        single: calibration; in flight
        pair: point spread function; PSF
        see: PRNU; pixel response non-uniformity
        !single: BigSat

    BigSat is calibrated in flight. Index entries can also be part of the text, like
    the :index:`limb <single: limb; viewing geometry>` of the Earth.

Page Breaks and Raw Word Content
--------------------------------

``raw:: latex`` with ``\newpage`` or ``\clearpage`` starts a new page in the Word
document as well as in the PDF. ``raw:: openxml`` puts WordprocessingML into the Word
document as it is; the other builders leave it out:

..  rst-example::

    ..  raw:: latex

        \newpage

    This paragraph starts a new page.

    ..  raw:: openxml

        <w:p><w:pPr><w:jc w:val="center"/></w:pPr>
        <w:r><w:rPr><w:caps/><w:color w:val="C00000"/></w:rPr>
        <w:t>A paragraph written in WordprocessingML</w:t></w:r></w:p>

Appendices and the Language of Labels
-------------------------------------

The documents in ``word_appendices`` go after the chapters, with their headings
numbered "Appendix A:", A.1 and A.1.1; :ref:`appendix_flatfield` is one. List them at
the end of the toctree too, so that HTML shows them and Sphinx numbers their figures.

The labels that sphinx2word writes itself, such as "Contents", "List of Figures",
"Figure", "Index" and "Appendix", follow ``language`` in ``conf.py`` when
``word_translate_labels`` is ``True`` (the default). With ``language = "de"`` they are
"Inhaltsverzeichnis", "Abbildungsverzeichnis", "Abbildung", "Stichwortverzeichnis" and
"Anhang". A label you set yourself, for example ``word_toc_title``, is kept as it is.

Cross-references
----------------

A label before a section can be referenced with ``:ref:``, and a document with ``:doc:``. In Word, a reference that
shows a heading's title is a ``REF`` field to that heading.

..  rst-example::

    :ref:`chap_calibration` describes the targets, :ref:`chap_instrument_model`
    the mathematics, and :doc:`software` the processing code. The label of this
    chapter is defined above its title with ``.. _chap_introduction:``.

Text
====

Inline Markup
-------------

..  rst-example::

    Paragraphs can have *emphasis*, **strong text**, ``inline code`` and a
    `hyperlink <https://www.sphinx-doc.org>`_. Chemical formulas and units use
    subscripts and superscripts: H\ :sub:`2`\ O, O\ :sub:`3`, cm\ :sup:`-1` and
    W m\ :sup:`-2` sr\ :sup:`-1` nm\ :sup:`-1`. Inline math such as
    :math:`\lambda = 550\,\mathrm{nm}` sits in the line of text.

Abbreviations are followed by their explanation in parentheses. ``:guilabel:`` and ``:menuselection:`` are in
italics:

..  rst-example::

    The reviewers at the :abbr:`PDR (Preliminary Design Review)` asked for the
    in-flight calibration of the :abbr:`PSF (point spread function)`. Press
    :guilabel:`Yes` when Word asks to update the fields, or choose
    :menuselection:`File --> Info --> Check for Issues`.

Coloured Text
-------------

The roles in ``s5defs.txt`` colour text. ``conf.py`` includes the file in ``rst_prolog`` and adds a ``strike``
role. Word knows red, green, orange, blue, purple and gray.

..  rst-example::

    The roles colour text: :red:`red`, :green:`green`, :orange:`orange`,
    :blue:`blue`, :purple:`purple` and :gray:`gray`. Text can also be
    :strike:`struck through`.

Footnotes and Citations
-----------------------

Footnotes become Word footnotes at the bottom of the page. Citations come from a BibTeX file with
sphinxcontrib-bibtex, or from reST citations, which are written where they are defined.

..  rst-example::

    Pre-flight calibration is described elsewhere [#preflight]_. Footnotes are
    numbered automatically [#auto]_ or by hand [1]_. Citations come from a BibTeX
    file :cite:p:`Harvey2014` or from a reST citation [ISO12233]_.

    ..  [#preflight] The pre-flight calibration plan is document BS-PLN-0042. A
        footnote can have *italic* text and math, :math:`\sigma^2`.
    ..  [#auto] An auto-numbered footnote.
    ..  [1] A footnote with a fixed number.
    ..  [ISO12233] ISO 12233:2017, Photography --- Electronic still picture
        imaging --- Resolution and spatial frequency responses.

Lines and Quotes
----------------

Line blocks keep their line breaks and indentation. A block quote is indented, and an attribution is in italics:

..  rst-example::

    | BigSat Science Team
    | Astronomy Tower
    |     Northgate University
    |     1 Observatory Road, Northgate

    The Sun is the brightest, most stable and best understood calibration source
    available to a satellite in low Earth orbit:

        It is also the most dangerous one to look at.

        --- BigSat calibration handbook

A rubric is a heading that is not in the table of contents. ``centered`` makes a centred, bold line:

..  rst-example::

    ..  rubric:: Calibration Requirements

    ..  centered:: A centred line of text

A transition, four or more dashes on their own between paragraphs, becomes a horizontal line. It cannot be inside
another directive, so this one is written without the ``rst-example`` block:

..  code-block:: rst

    The text before the line.

    ----------

    The text after the line.

The text before the line.

----------

The text after the line.

Lists
=====

Definition, field and option lists have their term in bold and their body indented. ``hlist`` lists short items
one after the other:

..  rst-example::

    Point spread function (PSF)
        The image of a point source on the detector, for one wavelength.

    Spectral response function (SRF) : per pixel
        The response of one pixel as a function of wavelength.

        A definition can have several paragraphs.

    :Document: BS-ATBD-0007
    :Issue: 1.2
    :Status: Approved for the critical design review

    -t TARGET      The calibration target: ``sun``, ``moon``, ``stars`` or ``earth``.
    -v, --verbose  Print progress messages.

    ..  hlist::
        :columns: 3

        * UV channel
        * VIS channel
        * NIR channel
        * Sun sensor

Bullet and enumerated lists are in :ref:`sect_lists`.

Boxes
=====

Admonitions
-----------

Admonitions become a shaded box with a coloured bar and a title: blue for notes, green for tips, orange for
cautions, red for warnings and gray for todo items.

..  rst-example::

    ..  note::

        A note can hold **bold** text, math :math:`\sqrt{2}` and lists:

        * one item
        * another item

    ..  tip:: A tip has a green bar.

    ..  caution:: A caution has an orange bar.

    ..  warning:: Do not point BigSat at the Sun without the neutral density filter.

    ..  seealso:: :ref:`chap_instrument_model` for the mathematics of the calibration.

    ..  todo:: Add the star catalogue to the next issue.
        ``todo_include_todos = True`` in ``conf.py`` shows it.

    ..  admonition:: A generic admonition with its own title

        Its body is a normal paragraph.

The other admonitions are ``hint`` (green), ``important`` and ``attention`` (orange), and ``danger`` and ``error``
(red):

..  rst-example::

    ..  hint:: A hint.

    ..  important:: An important admonition.

    ..  attention:: An attention admonition.

    ..  danger:: A danger admonition.

    ..  error:: An error admonition.

Topics, Sidebars and Version Notes
----------------------------------

Topics and sidebars are boxes too. Version notes are paragraphs in italics.

..  rst-example::

    ..  topic:: A topic

        A topic is a self-contained block of text with a title.

    ..  sidebar:: A sidebar

        A sidebar is a box beside the text in HTML. In Word it is a box in the text.

    ..  versionadded:: 1.1
        The Moon and star calibration.

    ..  versionchanged:: 1.2
        The PSF tail uses the Harvey model.

    ..  deprecated:: 1.2
        The crater-blurring technique.
