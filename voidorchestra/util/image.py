"""
Helper functions used for Image model. Arguably should be methods on the Image model.
"""
from pathlib import Path

from numpy import float32
from numpy.typing import NDArray

from voidorchestra.db import Image
from molegazer import config
from molegazer.util.rawpy import read_and_rescale_nef


def read_image_nef(image: Image) -> NDArray[float32]:
    """
    Given an image, reads in the associated NEF file.

    Parameters
    ----------
    image: Image
        The image file. Expecting it to be associated with a 13-bit NEF file.

    Returns
    -------
    NDArray[float32]:
        Image data in Y, X , RGB format, normalised to 0-255.
        OpenCV can't cope with 64-bit channels, and requires a 0-255 range for output.
    """
    return read_and_rescale_nef(
        Path(config['PATHS']['images_raw']) / image.filepath
    )
