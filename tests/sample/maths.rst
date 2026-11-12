Mathematics
===========

Inline math such as :math:`\frac{a}{b}`, :math:`\sum_{i=1}^{N} x_i`, :math:`\int_0^\infty e^{-x}\,dx`,
:math:`10^{-14}`, :math:`1.2\times10^{-6}`, :math:`(y+0.5, x+0.5)` and :math:`m \le 9` sits in the text line.

A numbered equation:

.. math::
    :label: eq_gauss

    G(x) = \frac{1}{\sigma\sqrt{2\pi}} \exp\left(-\frac{(x-\mu)^2}{2\sigma^2}\right)

An aligned multi-line equation (Sphinx wraps lines that end in ``\\`` in a ``split`` environment):

.. math::
    :label: eq_y_bounds

    y_1 &= -L   \\
    y_2 &= 0    \\
    y_3 &= +L

.. math::
    :label: eq_T_quadratic_coeffs

     a &= \frac{1}{2L^2}\left( T_1 - 2T_2 + T_3\right) \\
     b &= \frac{1}{2L}\left(T_3-T_1\right) \\
     c &= T_2

Alignment on the equals sign with left-hand sides of different widths:

.. math::

    \begin{aligned}
    T(y) &= a y^2 + b y + c \\
    \int_{-L/2}^{L/2} T(y)\,\mathrm{d}y &= \frac{a L^3}{12} + c L \\
    x &= 1
    \end{aligned}

Two equations separated by a blank line form one numbered block:

.. math::
    :label: eq_two_parts

    \nabla \cdot \vect{E} = \frac{\rho}{\varepsilon_0}

    \nabla \times \vect{B} - \frac{1}{c^2}\frac{\partial \vect{E}}{\partial t} = \mu_0 \vect{J}

An unnumbered matrix equation:

.. math::

    \begin{bmatrix} y_1 \\ y_2 \\ y_3 \end{bmatrix} =
    \begin{pmatrix} a_{11} & a_{12} & a_{13} \\ a_{21} & a_{22} & a_{23} \\ a_{31} & a_{32} & a_{33} \end{pmatrix}
    \begin{bmatrix} x_1 \\ x_2 \\ x_3 \end{bmatrix}, \quad \vect{x} \in \RR^3

Cases, operators, accents and fonts:

.. math::

    f(x) = \begin{cases} 1 & \text{if } x > 0 \\ 0 & \text{otherwise} \end{cases}
    \qquad \lim_{n\to\infty} \left(1 + \frac{1}{n}\right)^n = e

.. math::

    \hat{x}, \bar{y}, \tilde{z}, \vec{v}, \dot{q}, \ddot{q}, \overline{AB}, \mathrm{d}x, \mathcal{L},
    \mathbf{M}^{-1}, \operatorname{sinc}(x), \max_{k} |a_k|, \sqrt[3]{x+1}, \binom{n}{k},
    \underbrace{a + b}_{\text{sum}}, x' , f''(x)

.. math::

    \mathcal{F}\{f\}(\nu) = \iint_{-\infty}^{\infty} f(x, y)\, e^{-2\pi i (u x + v y)} \,\mathrm{d}x\,\mathrm{d}y
    \approx \sum_{j=0}^{N-1}\sum_{k=0}^{M-1} f_{jk}\, W_N^{uj} W_M^{vk}

.. math::

    \left\| \vect{A}\vect{x} - \vect{b} \right\|_2^2 + \lambda \left\langle \vect{x}, \vect{x} \right\rangle
    \quad\Rightarrow\quad \vect{x} = \left(\vect{A}^T\vect{A} + \lambda I\right)^{-1}\vect{A}^T\vect{b}

Math inside a table cell and a caption works too, see :numref:`tab_math`.
