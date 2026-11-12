..  _appendix_flatfield:

####################
Flat-Field Mosaics
####################

This document is an appendix. ``word_appendices`` in ``conf.py`` lists it, so the Word
document puts it after the chapters and numbers its headings "Appendix A:", A.1 and
A.1.1, as LaTeX numbers ``latex_appendices``. It is also the last entry of the toctree,
so the HTML output shows it, and Sphinx numbers its figures, tables and equations:

..  code-block:: python

    word_appendices = ["appendix_flatfield"]
    word_appendix_label = "Appendix"

Mosaic Pattern
==============

The Sun is scanned across the field of view in a raster of overlapping images. Each
pixel sees the centre of the solar disk at least four times.

..  math::
    :label: eq_mosaic_mean

    \bar{G}_{ij} = \frac{1}{N} \sum_{k=1}^{N} \frac{S_{ij,k}}{I_k(\mu_{ij,k})}

Overlap
-------

Neighbouring images overlap by a third of the field of view, so the limb darkening of
equation :eq:`eq_mosaic_mean` can be fitted at the same time as the gains.

..  list-table:: Raster of a solar scan
    :header-rows: 1

    * - Channel
      - Images
      - Overlap
    * - UV
      - 24
      - 33 %
    * - VIS and NIR
      - 36
      - 33 %
