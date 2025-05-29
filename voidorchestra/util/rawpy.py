from pathlib import Path

from rawpy import imread
from numpy import float32, uint16
from numpy.typing import NDArray

from molegazer.log import get_logger


logger = get_logger(__name__.replace(".", "-"))


def read_and_rescale_nef(path: Path) -> NDArray[float32]:
    """
    Given a path to a NEF file, reads it in and rescales it.

    Parameters
    ----------
    path: Path
        The path to a 13-bit NEF file.

    Returns
    -------
    NDArray[float32]:
        Image data in Y, X , RGB format, normalised to 0-255.
        OpenCV can't cope with 64-bit channels, and requires a 0-255 range for output.
    """

    image_data: NDArray[uint16] = imread(
        str(path)
    ).postprocess(
        output_bps=16  # If we don't specify, it downscales to 8-bit colour depth!
    )
    # We need to rescale from 0-65535 (16-bit integer depth) to 0-256 float
    return image_data.astype(float32) * 255 / 65535
