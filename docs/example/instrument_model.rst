..  _chap_instrument_model:

################
Instrument Model
################

LaTeX math becomes native Word equations, which can be edited in Word. Inline math sits in the line of text:

..  rst-example::

    Inline math such as :math:`\frac{a}{b}`, :math:`\sum_{i=1}^{N} x_i`,
    :math:`\int_0^\infty e^{-x}\,dx` or :math:`1.2\times10^{-6}` sits in the line
    of text.

Transfer Function
=================

The signal recorded by pixel :math:`(i, j)` is the radiance weighted by the transfer function of the optical chain.
An equation with a ``:label:`` is numbered, with its number on the right, and ``:eq:`` refers to it:

..  rst-example::

    ..  math::
        :label: eq_signal

        S_{ij} = \int_{\lambda} \iint_{\Omega} T'(\mathbf{\Omega}, \lambda, \mathbf{A})\,
                 I(\mathbf{\Omega}, \lambda)\,\mathrm{d}\Omega\,\mathrm{d}\lambda

    The transfer function in equation :eq:`eq_signal` is split into the product of
    three components, the PSF :math:`P`, the SRF :math:`R` and the PRNU :math:`G`:

    ..  math::
        :label: eq_transfer_split

        T'(\mathbf{\Omega}, \lambda, \mathbf{A}) = P(\mathbf{\Omega}, \lambda, \mathbf{A})\,
                                                  R(\mathbf{\Omega}, \lambda, \mathbf{A})\,
                                                  G(\mathbf{\Omega}, \mathbf{A})

PSF Core and Tails
------------------

For experimental convenience, we split the PSF into a core and a tail. The core comes from the optical design and
its aberrations, while the tail comes from light scattered by imperfections and dust on the optical surfaces
:cite:p:`Harvey2014`. The tail plays a large role for limb-viewing instruments, because it falls off more slowly
than the atmospheric signal. It is fitted with the Harvey model, :func:`~bigsat_cal.harvey_psf`:

..  rst-example::

    ..  math::
        :label: eq_psf_core_tails

        P(\mathbf{\Omega}, \lambda, \mathbf{A}) =
            P_{core}(\mathbf{\Omega}, \lambda, \mathbf{A})
            + P_{tail}(\mathbf{\Omega}, \lambda, \mathbf{A})

    ..  math::
        :label: eq_harvey

        P_{tail}(\theta) = b_0 \left[ 1 + \left( \frac{\theta}{\ell} \right)^2 \right]^{s/2}

Polarization
------------

The polarization of the light is described by the Stokes vector :cite:p:`Chandrasekhar1960,Hansen1974`, and the
instrument by a Mueller matrix. An equation without a label is not numbered. The macros ``\vect`` and ``\RR`` are
defined in ``mathjax3_config`` in ``conf.py``, so they work in both the HTML and the Word output:

..  rst-example::

    ..  math::

        \vect{I}'(\Omega,\lambda) = \begin{bmatrix} I' \\ Q' \\ U' \\ V' \end{bmatrix} =
        \begin{bmatrix}
        m_{11} & m_{12} & m_{13} & m_{14} \\
        m_{21} & m_{22} & m_{23} & m_{24} \\
        m_{31} & m_{32} & m_{33} & m_{34} \\
        m_{41} & m_{42} & m_{43} & m_{44}
        \end{bmatrix}
        \begin{bmatrix} I \\ Q \\ U \\ V \end{bmatrix},
        \quad \vect{I} \in \RR^4

Solar Model
===========

The Sun's disk is darker towards the limb. Its brightness follows a limb-darkening law,
:func:`~bigsat_cal.limb_darkening`, written here with ``cases``:

..  rst-example::

    ..  math::
        :label: eq_limb_darkening

        \frac{I(\mu)}{I(1)} = \begin{cases}
            1 - u\,(1 - \mu) & \text{linear law} \\
            1 - a\,(1 - \mu) - b\,(1 - \mu)^2 & \text{quadratic law} \\
            0 & \text{if } \mu < 0
        \end{cases}

Lines that end in ``\\`` are aligned on the ``&``. ``aligned`` does the same inside one equation:

..  rst-example::

    ..  math::
        :label: eq_disk_edges

        y_1 &= -R_\odot \\
        y_2 &= 0 \\
        y_3 &= +R_\odot

    ..  math::

        \begin{aligned}
        T(y) &= a y^2 + b y + c \\
        \int_{-L/2}^{L/2} T(y)\,\mathrm{d}y &= \frac{a L^3}{12} + c L
        \end{aligned}

Equations separated by a blank line form one numbered block:

..  rst-example::

    ..  math::
        :label: eq_two_parts

        \nabla \cdot \vect{E} = \frac{\rho}{\varepsilon_0}

        \nabla \times \vect{B}
            - \frac{1}{c^2}\frac{\partial \vect{E}}{\partial t} = \mu_0 \vect{J}

``word_math_macros`` in ``conf.py`` adds macros for the Word output, here ``\degC``. It is in
``mathjax3_config`` too, for the HTML output. Accents, fonts and operators are converted as well:

..  rst-example::

    The detector is kept at :math:`-20\,\degC` and must not change by more than
    :math:`0.1\,\degC` during a solar scan.

    ..  math::

        \hat{x}, \bar{y}, \tilde{z}, \vec{v}, \dot{q}, \ddot{q}, \overline{AB},
        \mathcal{L}, \mathbf{M}^{-1}, \operatorname{sinc}(x), \max_{k} |a_k|,
        \sqrt[3]{x+1}, \binom{n}{k}, \underbrace{a + b}_{\text{sum}},
        \lim_{n\to\infty} \left(1 + \frac{1}{n}\right)^n = e

Results
=======

Math can be used in tables and captions, and so can the colour roles. Roles cannot be nested, so a
coloured value is text, not math:

..  rst-example::

    The colour of the slope :math:`s` shows how well the tail was fitted:
    :green:`good`, :orange:`usable` or :red:`poor`.

    ..  _tab_results:

    ..  list-table:: Fitted PSF parameters, with :math:`\chi^2` in the caption
        :header-rows: 1
        :widths: 25 25 25 25

        * - Channel
          - :math:`b_0`
          - :math:`\ell` (degrees)
          - :math:`s`
        * - UV
          - :math:`3.5\times10^{-4}`
          - 0.012
          - :red:`-2.1`
        * - VIS
          - :math:`1.2\times10^{-4}`
          - 0.010
          - :green:`-2.4`
        * - NIR
          - :math:`0.8\times10^{-4}`
          - 0.009
          - :orange:`-2.6`
