"""A small module documented by the sample document."""


def convolve(signal, kernel, mode: str = "same") -> list:
    r"""
    Convolve a signal with a kernel, :math:`y = s * k`.

    Parameters
    ----------
    signal : list of float
        The input signal :math:`s_i`.
    kernel : list of float
        The kernel.
    mode : str
        One of ``"same"`` or ``"full"``.

    Returns
    -------
    list
        The convolved signal.
    """
    return []


class Detector:
    """A detector with :math:`N_x \\times N_y` pixels."""

    def __init__(self, nx: int, ny: int):
        self.nx = nx
        self.ny = ny

    def read(self, exposure: float = 1.0) -> float:
        """Read the detector for ``exposure`` seconds."""
        return 0.0


class CCD(Detector):
    """A CCD detector, shown in an inheritance diagram."""
