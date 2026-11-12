"""
In-flight calibration tools for the imaginary BigSat instrument.

The module is documented by the example document with autodoc, ``literalinclude`` and sphinx-argparse. The
functions work, but the numbers are made up.
"""
import argparse
import math
from typing import List, Sequence


def limb_darkening(mu: float, u: float = 0.6) -> float:
    r"""
    Linear limb-darkening law of the solar disk.

    .. math::

        \frac{I(\mu)}{I(1)} = 1 - u\,(1 - \mu)

    Parameters
    ----------
    mu : float
        Cosine of the angle between the line of sight and the normal to the solar surface,
        :math:`0 \le \mu \le 1`.
    u : float
        Limb-darkening coefficient. The default is typical of visible wavelengths.

    Returns
    -------
    float
        The intensity relative to the centre of the disk.

    Examples
    --------
    >>> limb_darkening(1.0)
    1.0
    >>> round(limb_darkening(0.5), 2)
    0.7
    """
    return 1.0 - u * (1.0 - mu)


def harvey_psf(theta: Sequence[float], b0: float, ell: float, s: float) -> List[float]:
    r"""
    Harvey model of the scattered-light tail of the point spread function.

    .. math::

        P_{tail}(\theta) = b_0 \left[ 1 + \left( \frac{\theta}{\ell} \right)^2 \right]^{s/2}

    Parameters
    ----------
    theta : sequence of float
        Angles from the centre of the PSF, in degrees.
    b0 : float
        Scatter at :math:`\theta = 0`.
    ell : float
        Roll-off angle :math:`\ell` in degrees.
    s : float
        Slope of the tail on a log-log plot (negative).

    Returns
    -------
    list of float
        The tail of the PSF at each angle.
    """
    return [b0 * (1.0 + (t / ell) ** 2) ** (s / 2.0) for t in theta]


class FlatField:
    """
    Pixel response non-uniformity (PRNU) of one detector.

    Parameters
    ----------
    nx, ny : int
        Number of pixels in each direction.

    Attributes
    ----------
    gain : list of list of float
        The relative gain of each pixel, 1.0 until :meth:`update` is called.
    """

    def __init__(self, nx: int, ny: int):
        self.nx = nx
        self.ny = ny
        self.gain = [[1.0] * nx for _ in range(ny)]

    def update(self, image: Sequence[Sequence[float]]) -> float:
        """
        Update the gains from a mosaic of solar images.

        Parameters
        ----------
        image : 2-D sequence of float
            The mean of the mosaic, one value per pixel.

        Returns
        -------
        float
            The root-mean-square change in gain.
        """
        mean = sum(sum(row) for row in image) / (self.nx * self.ny)
        change = 0.0
        for j, row in enumerate(image):
            for i, value in enumerate(row):
                new = value / mean
                change += (new - self.gain[j][i]) ** 2
                self.gain[j][i] = new
        return math.sqrt(change / (self.nx * self.ny))


class LunarFlatField(FlatField):
    """
    PRNU from lunar scans: the same as :class:`FlatField`, with the lunar albedo removed
    first.
    """


def make_parser() -> argparse.ArgumentParser:
    """Return the command-line parser of ``bigsat-cal``."""
    parser = argparse.ArgumentParser(prog="bigsat-cal", description="Process BigSat in-flight calibration data.")
    parser.add_argument("level1", help="Level 1 file with the calibration observations")
    parser.add_argument("-t", "--target", choices=["sun", "moon", "stars", "earth"], default="sun",
                        help="Calibration target")
    parser.add_argument("-o", "--output", default="calibration.nc", help="Output file")
    parser.add_argument("-v", "--verbose", action="store_true", help="Print progress messages")
    return parser


def main(argv=None) -> int:
    """Run ``bigsat-cal``."""
    args = make_parser().parse_args(argv)
    if args.verbose:
        print(f"Calibrating {args.level1} with the {args.target}")
    return 0
