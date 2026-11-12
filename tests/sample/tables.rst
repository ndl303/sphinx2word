Tables
======

.. _tab_math:

.. list-table:: Results with math :math:`\Delta T` in the caption
    :header-rows: 1
    :widths: 30 20 50

    * - Case
      - Value
      - Comment
    * - June 2020
      - :math:`3.5\times10^{-14}`
      - Agrees to rounding. A long comment that wraps over more than one line inside the cell.
    * - October 2020
      - :math:`1.2\times10^{-6}`
      - * bullet inside a cell
        * second bullet

A grid table with spanning cells:

.. table:: Spanning cells
    :name: tab_span

    +------------+------------+-----------+
    | Header 1   | Header 2   | Header 3  |
    +============+============+===========+
    | body row 1 | spans two columns      |
    +------------+------------+-----------+
    | spans two  | cell       | cell      |
    | rows       +------------+-----------+
    |            | cell       | cell      |
    +------------+------------+-----------+

A simple table without a caption:

=====  =====  ======
A      B      A and B
=====  =====  ======
False  False  False
True   False  False
=====  =====  ======
