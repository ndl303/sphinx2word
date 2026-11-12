.. _chap_text:

Text and Lists
==============

Paragraphs contain *emphasis*, **strong text**, ``inline code``, H\ :sub:`2`\ O, E = mc\ :sup:`2` and a
`hyperlink <https://www.usask.ca>`_. A cross-reference to :ref:`sec_lists` and to :numref:`fig_patch` and to
equation :eq:`eq_gauss`. Footnotes work too [#first]_ and again [#second]_.

.. [#first] This is the first footnote. It has *italic* text and math :math:`x^2`.
.. [#second] The second footnote.

.. _sec_lists:

Lists
-----

#. First numbered item with a long line that wraps across the page so that the hanging indent can be checked by
   eye in the Word document.
#. Second item

   * nested bullet one
   * nested bullet two with ``code``

     #. third level numbered
     #. third level again

#. Third item, the numbering continues after the nested list.

A second numbered list restarts its numbering:

#. Alpha
#. Beta

a. Lower alpha list
b. Second entry

* A bullet list
* With math :math:`\alpha + \beta = \gamma` inside an item

Term one
    Definition of the first term.

Term two : classifier
    Definition of the second term, with two paragraphs.

    The second paragraph of the definition.

:Field name: field body text
:Another: more text

Code and Notes
--------------

.. code-block:: python
    :caption: A small Python example

    def gaussian(x, sigma=1.0):
        """Return a Gaussian."""
        return np.exp(-0.5 * (x / sigma) ** 2)   # comment

.. note::

    This is a note with **bold** text and math :math:`\sqrt{2}`.

.. warning:: Warnings are shown with a red bar.

.. todo:: A todo item.

    Block quote text is indented from the margin.

Line blocks keep line breaks:

| Line one
| Line two
|     Indented line three

Citations are listed with their labels [Lia90]_ [vHDD+18]_ [Chandrasekhar60]_.

.. [Lia90] Q.-T. Liang. Simple ray tracing formulas for uniaxial optical crystals. Appl. Opt., 1990.
.. [vHDD+18] G. van Harten et al. Calibration and validation of airborne multiangle spectropolarimetric imager
   polarization measurements. Appl. Opt., 2018.
.. [Chandrasekhar60] Subrahmanyan Chandrasekhar. Radiative transfer. Dover Publications, 1960.
