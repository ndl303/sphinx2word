###################
Processing Software
###################

The calibration is processed by the Python module ``bigsat_cal``, in ``software/bigsat_cal.py``. This chapter shows
code and API documentation.

Code
====

Code blocks are shaded and coloured with Pygments, in the colours of ``pygments_style``. A code block with a
``:caption:`` gets a numbered "Listing" caption; ``word_caption_labels`` in ``conf.py`` sets the label:

..  rst-example::

    ..  code-block:: python
        :caption: Make a PRNU mosaic from a solar scan
        :name: code_mosaic

        from bigsat_cal import FlatField

        flat = FlatField(nx=1024, ny=256)
        for image in solar_scan:            # one image per pointing
            change = flat.update(image)
            print(f"rms change in gain: {change:.2e}")

    The mosaic is made by the code in :numref:`code_mosaic`.

``:linenos:`` numbers the lines, ``:lineno-start:`` sets the first number, and
``:emphasize-lines:`` shades lines:

..  rst-example::

    ..  code-block:: python
        :linenos:
        :lineno-start: 20
        :emphasize-lines: 3,4

        def limb_darkening(mu, u=0.6):
            """Linear limb-darkening law of the solar disk."""
            if not 0 <= mu <= 1:
                raise ValueError("mu must be between 0 and 1")
            return 1.0 - u * (1.0 - mu)

``literalinclude`` reads code from a file. ``:pyobject:`` picks one class or function:

..  rst-example::

    ..  literalinclude:: software/bigsat_cal.py
        :language: python
        :pyobject: limb_darkening

A literal block, introduced with ``::``, is shown as it is. A doctest block is coloured as a Python session, and
code in the ``text`` language is not coloured:

..  rst-example::

    The level 1 header holds::

        LEVEL1_FILE  = bigsat_l1_20260512T101500.nc
        TARGET       = sun
        ND_FILTER    = 3

    >>> from bigsat_cal import limb_darkening
    >>> limb_darkening(0.5)
    0.7

    ..  code-block:: text

        2026-05-12T10:15:00  scan 1 of 24  ok
        2026-05-12T10:15:30  scan 2 of 24  ok

Diagrams
========

``sphinx.ext.graphviz`` draws diagrams with Graphviz. sphinx2word inserts them as SVG
pictures, with a caption if they have one; Graphviz's ``dot`` must be installed.
``inheritance-diagram`` (``sphinx.ext.inheritance_diagram``) draws the classes of a
module the same way:

..  rst-example::

    ..  graphviz::
        :caption: The calibration processing chain
        :name: fig_processing_chain

        digraph chain {
            rankdir=LR;
            node [shape=box, style=rounded, fontname="Helvetica"];
            L0 -> L1 -> calibration -> L2;
            solar [label="solar scans"];
            lunar [label="lunar scans"];
            solar -> calibration;
            lunar -> calibration;
        }

    ..  inheritance-diagram:: bigsat_cal

Command Line
============

sphinx-argparse documents a command line from its ``argparse`` parser:

..  rst-example::

    ..  argparse::
        :module: bigsat_cal
        :func: make_parser
        :prog: bigsat-cal

API
===

autodoc, with napoleon or numpydoc, documents Python code. Each entry is a shaded signature line followed by the
description, indented. A reference to an API entry is a hyperlink:

..  rst-example::

    The gains are kept by :class:`~bigsat_cal.FlatField`, and the stray light is modelled by
    :func:`~bigsat_cal.harvey_psf`.

    ..  automodule:: bigsat_cal
        :members:
