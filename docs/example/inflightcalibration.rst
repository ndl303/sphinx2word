..  _chap_calibration:

######################
In-Flight Calibration
######################

This chapter shows figures, lists and tables. A figure becomes a picture with a caption below it, numbered by Word
("Figure 1"), and a ``:numref:`` to it becomes a cross-reference field:

..  rst-example::

    ..  _fig_bigsat_patch:

    ..  figure:: figures/bigsat_patch.png
        :width: 6cm

        The BigSat mission patch. The satellite looks at the limb of the Earth,
        the line of sight is :math:`\sim 3000\,\mathrm{km}` long, and the Sun
        rises behind the limb.

        This paragraph is the legend of the figure. It follows the caption.

    The BigSat patch is shown in :numref:`fig_bigsat_patch`.

Overview
========

The Astronomy Department of Northgate University has developed techniques to provide in-flight calibration of the three optical
chains of the **BigSat** instrument (:numref:`fig_bigsat_patch`). The goal is to *demonstrate* that the techniques
give enough accuracy and precision for BigSat to meet its requirements.

The BigSat optical chains have a nominal 2 degree field of view, which is imaged by approximately 250,000 science
pixels in the VIS and NIR channels and 27,000 science pixels in the UV channel. In principle, each pixel of each
detector maps to a unique incoming direction and has its own set of in-flight calibration parameters. In practice,
a complete set of calibration parameters is made by interpolating smaller sets of observations.

..  _sect_lists:

Assumptions
-----------

The operation of each optical chain is defined in :ref:`chap_instrument_model` as a transfer function,
:math:`T'(\mathbf{\Omega}, \lambda, \mathbf{A})`. Equation :eq:`eq_transfer_split` splits it into three components.
The model makes the assumptions below. Bullet and numbered lists become Word lists, nested to any depth:

..  rst-example::

    #.  the wavelength variation of the PSF is constant over a small wavelength range,

        * which holds within one spectral sample,
        * and within one :math:`\Psi_e(\Omega)` bin,

          #. checked by ray tracing,
          #. and by the pre-flight measurements;

    #.  the variation of the SRF on the image plane is constant over a small spatial range;
    #.  the variations of PSF and SRF are small over small changes in the incident angle.

Enumerated lists keep their style, and each list starts at its own first number:

..  rst-example::

    I.  the Sun,
    #.  the Moon,
    #.  the stars.

    iv. the Earth's limb,
    #.  the Earth's surface.

    (a) a lower-case list in parentheses,
    (b) its second item.

    A)  an upper-case list with a closing bracket,
    B)  its second item.

These assumptions depend on the context, and care must be taken to know when they are valid and, more importantly,
when they are not. The optical design and the instrument builders guide this.

Normalization
^^^^^^^^^^^^^

We normalize the PSF and SRF, which moves most of the absolute calibration into the PRNU term. The PSF
normalization is the integral over the image plane for a single wavelength, a single incident direction and a
single instrument setting. The SRF normalization is the integral over wavelength for a single incident direction and
a single instrument setting.

Similarly, and perhaps even odder, the PRNU for a single instrument setting does not depend on wavelength or image
location: it only depends on the incoming direction. This seems contrary to common sense, as intuitively *"the PRNU
must change with wavelength"*. The statement only applies to a single instrument setting, which many people casually
call *wavelength*. All of the wavelength dependence at one instrument setting is in the SRF.

Calibration Targets
===================

BigSat has no on-board calibration system, so in-flight calibrations must use natural targets: the Sun, the Moon,
the stars and the Earth. Observations of the Sun have been used many times for accurate calibration of space-borne
instruments, usually through a diffusing plate :cite:p:`Barnes2001,Eplee2012`. The Sun has its own complexity, such
as limb darkening :cite:p:`Neckel1994`, which must be managed.

SVG images are embedded as SVG, which Word 2016 and later show. A PNG fallback is added for older versions, made
with cairosvg if it is installed. ``:name:`` gives a figure a label without a separate target line:

..  rst-example::

    ..  figure:: figures/bigsat_patch.svg
        :width: 5cm
        :name: fig_targets

        An SVG figure. Word 2016 and later show the SVG; older versions show a PNG fallback.

Images can be placed side by side in a table. ``:width:``, ``:height:`` and ``:scale:`` set their size:

..  rst-example::

    ..  list-table::
        :widths: 50 50

        * - ..  image:: figures/bigsat_patch.png
                :width: 3cm
          - ..  image:: figures/bigsat_patch.svg
                :width: 2cm

Sun
---

A ``list-table`` with a title gets a numbered caption above it. Header rows repeat on each page, stub columns are
bold and shaded, and cells can hold math, lists and citations:

..  rst-example::

    ..  _tab_suncal_pot:

    ..  list-table:: Calibration potential of the Sun
        :header-rows: 1
        :stub-columns: 1
        :widths: 15 10 10 25 40

        * - Calibration
          - Possible
          - Used
          - Technique
          - Issues
        * - PSF Core
          - Yes
          - No
          - Curved edge technique :cite:p:`Reichenbach1991`
          - Possible thermal :math:`\frac{2\pi}{\nu}` issues if looking at the Sun too long
        * - PSF Tails
          - Yes
          - No
          - Two Harvey fit technique
          - * Dangerous without the neutral density filter
            * Needs a long exposure
        * - SRF
          - Yes
          - Yes
          - Fraunhofer registration with a solar spectrum :cite:p:`Thuillier2003`
          - Wavelength registration only
        * - Polarization
          - No
          -
          -
          - Solar signal not strongly polarized

Moon
----

The Moon is a very stable radiometric source whose brightness is well matched to that of the Earth. A simple table
has no caption:

..  rst-example::

    ============ ======== ==== ======================= ===============================
    Calibration  Possible Used Technique               Issues
    ============ ======== ==== ======================= ===============================
    PSF Core     Yes      Yes  Curved edge technique   Structure along the lunar edge
    PSF Tails    Yes      Yes  Two Harvey fit          Must account for lunar structure
    SRF          Yes      No   Fraunhofer registration Needs tables of lunar albedo
    PRNU         Yes      Yes  Lunar irradiance        Measures the ND transmission
    ============ ======== ==== ======================= ===============================

Stars
-----

Stars are point sources, which is highly desirable, but they are too dim and too small to cover the detector. A
``csv-table`` reads its data as CSV:

..  rst-example::

    ..  _tab_stars:

    ..  csv-table:: Stars used to check the PSF
        :header: "Star", "Magnitude", "Spectral type", "Use"
        :widths: 20, 15, 20, 45

        "Sirius", -1.46, "A1V", "PSF core, pointing"
        "Canopus", -0.74, "A9II", "PSF core"
        "Vega", 0.03, "A0V", "Spectral response, standard star"
        "Betelgeuse", 0.50, "M1-2Ia", "Not used: variable"

Schedule
--------

A grid table can span columns and rows; the spans become merged cells. ``table`` gives it a title and a label:

..  rst-example::

    ..  table:: Calibration schedule
        :name: tab_schedule

        +--------------+-------------------------------+---------------------------+
        | Target       | Commissioning                 | Routine operations        |
        |              +---------------+---------------+-------------+-------------+
        |              | Month 1       | Month 2       | Monthly     | Yearly      |
        +==============+===============+===============+=============+=============+
        | Sun          | PRNU, SRF                     | PRNU        | SRF         |
        +--------------+---------------+---------------+-------------+-------------+
        | Moon         | PSF core      | PSF tails     | Irradiance  | ---         |
        +--------------+---------------+---------------+-------------+             |
        | Earth limb   | ---           | Polarization  | Pointing    |             |
        +--------------+---------------+---------------+-------------+-------------+

    The calibration potential of each target is in :numref:`tab_suncal_pot`,
    :numref:`tab_stars` and :numref:`tab_schedule`.

Calendar
--------

A block with the class ``landscape`` is put on its own landscape pages. ``rst-class``
gives the next block a class, and ``container:: landscape`` holds several blocks. HTML
ignores the class:

..  rst-example::

    ..  rst-class:: landscape

    ..  csv-table:: Calibration calendar of the first year
        :name: tab_calendar
        :header: Target, Jan, Feb, Mar, Apr, May, Jun, Jul, Aug, Sep, Oct, Nov, Dec
        :stub-columns: 1

        Sun, PRNU, SRF, PRNU, SRF, PRNU, SRF, PRNU, SRF, PRNU, SRF, PRNU, SRF
        Moon, PSF, , PSF, , PSF, , PSF, , PSF, , PSF,
        Stars, , PSF, , , PSF, , , PSF, , , PSF,
        Earth limb, , , Pol., , , Pol., , , Pol., , , Pol.

In-Flight Calibration Products
==============================

The in-flight calibration delivers these five products to the level 1 processor:

#.  the PSF core,
#.  the PSF tails,
#.  the SRF,
#.  the PRNU,
#.  the polarization sensitivity.
