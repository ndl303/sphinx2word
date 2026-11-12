Layout and Diagrams
===================

.. index:: calibration; flat field
.. index::
    pair: detector; dark current
    triple: solar; limb; darkening
    see: PRNU; flat field
    seealso: detector; calibration
    !single: gain

Index entries come from the ``index`` directive and from the :index:`role <single: index role>` in a
paragraph, with a colon in :index:`a term: with a colon`.

.. raw:: latex

    \newpage

This paragraph starts a new page.

.. raw:: openxml

    <w:p><w:r><w:t>Raw WordprocessingML paragraph.</w:t></w:r></w:p>

A paragraph with an inline raw run: :raw-openxml:`<w:r><w:rPr><w:b/></w:rPr><w:t>bold raw run</w:t></w:r>`.

.. rst-class:: landscape

.. table:: A wide table on a landscape page
    :name: tab_wide

    =====  =====  =====  =====  =====  =====  =====  =====  =====  =====
    A      B      C      D      E      F      G      H      I      J
    =====  =====  =====  =====  =====  =====  =====  =====  =====  =====
    1      2      3      4      5      6      7      8      9      10
    =====  =====  =====  =====  =====  =====  =====  =====  =====  =====

Back in portrait.

.. code-block:: python
    :linenos:
    :lineno-start: 10
    :emphasize-lines: 2,3

    def gaussian(x, sigma=1.0):
        """Return a Gaussian."""
        return np.exp(-0.5 * (x / sigma) ** 2)

.. graphviz::
    :caption: A Graphviz diagram
    :name: fig_graphviz

    digraph pipeline { rankdir=LR; level0 -> level1 -> level2; }

.. inheritance-diagram:: sample_module.CCD

.. code-block:: yaml

    # a YAML block: Pygments gives it token types that the style does not list
    instrument: BigSat
    channels: [UV, VIS, NIR]
    calibration:
      sun: {prnu: true, srf: true}
