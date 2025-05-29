from typing import Union, Tuple, Optional, Dict

import cv2
import numpy

from numpy import float32, float64
from numpy._typing import NDArray
from skimage.draw import disk
from skimage.feature import blob_log

import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec

from molegazer import config
from molegazer.log import get_logger


logger = get_logger(__name__.replace(".", "-"))


def _create_blob_image(
        image_data: NDArray[float32],
        position_x: int, position_y: int, size: float
) -> Union[NDArray[float32], None]:
    """
    Given a base image, and the details of a blob, will extract the blob from that image.

    Parameters
    ----------
    image_data: NDArray[float32]
        The image data in [Y, X, RGB].
    position_x: int
        The X position.
    position_y: int
        The Y position.

    Returns
    -------
    NDArray[float32]: An array of image data in [Y, X, RGB].
    None: If the stamp would go outside the bounds of the image.
    """
    window_size_adjusted: int = int(
        config['STAMPS'].getint('stamp_size_base') * size
    )

    window_v_min: int = position_y - window_size_adjusted
    window_v_max: int = position_y + window_size_adjusted
    window_h_min: int = position_x - window_size_adjusted
    window_h_max: int = position_x + window_size_adjusted

    if any((
        window_v_min < 0, window_v_max > image_data.shape[0],
        window_h_min < 0, window_h_max > image_data.shape[1],
    )):
        return None
    else:
        return image_data[
            window_v_min:window_v_max,
            window_h_min:window_h_max,
            :
        ]


def compare_feature_to_surroundings(
    image_data: NDArray[float32],
    centre: Tuple[int, int],
    radius: float64,
    params: Dict[str, float]
) -> float32:
    """
    Given a feature's location and size, compares it to the surrounding area.
    If it's hair, they will probably be very similar.

    Parameters
    ----------
    image_data: NDArray[float32]
        The full image data
    centre: Tuple[int, int]
        The centre of the feature to compare
    radius: float64
        The radius of the feature
    params: Dict[str, float]
        The parameters for the comparison

    Return
    ------
    float32: The Bhattacharyya distance between the two histograms, a measure of their overlap
        The highest it is, the greater the distance and the more dissimilar
        https://en.wikipedia.org/wiki/Bhattacharyya_distance
    """
    radius_outer: int = int(
        radius * params['surroundings_radius_mult_outer'] + params['surroundings_radius_add_outer']
    )
    radius_inner: int = int(
        radius * params['surroundings_radius_mult_inner'] + params['surroundings_radius_add_inner']
    )

    if any([
        centre[0] - radius_outer < 0, centre[0] + radius_outer >= image_data.shape[0],
        centre[1] - radius_outer < 0, centre[1] + radius_outer >= image_data.shape[1]
    ]):
        # If the surroundings extend outside the image, we can't compare. Skip.
        return float32(-1.0)

    image_region: NDArray[float32] = image_data[
        centre[0]-radius_outer: centre[0]+radius_outer,
        centre[1]-radius_outer: centre[1]+radius_outer,
        :
    ]

    mask_feature: NDArray[bool] = numpy.zeros(
        image_region.shape[:2], dtype=bool
    )
    mask_feature[
        disk((radius_outer, radius_outer), radius_inner)
    ] = True

    mask_surroundings: NDArray[bool] = numpy.zeros(
        image_region.shape[:2], dtype=bool
    )
    mask_surroundings[
        disk((radius_outer, radius_outer), radius_outer)
    ] = True
    mask_surroundings[mask_feature] = False

    channel_distance: NDArray[float32] = numpy.zeros(3)
    for channel in (0, 1, 2):
        image_channel = image_region[:, :, channel]
        hist_bins: NDArray[float32] = numpy.linspace(
            image_channel.min(), image_channel.max(), 20, endpoint=True
        )
        hist_feature, hist_bins = numpy.histogram(
            image_channel[mask_feature].flatten(), bins=hist_bins, density=True
        )
        hist_surroundings, _ = numpy.histogram(
            image_channel[mask_surroundings].flatten(), bins=hist_bins, density=True
        )
        channel_distance[channel] = cv2.compareHist(
            hist_feature.astype(numpy.float32),
            hist_surroundings.astype(numpy.float32),
            method=cv2.HISTCMP_BHATTACHARYYA
        )

    return channel_distance.max(initial=0.0)  # PyCharm seems to think it needs an initial guess for a max value?


def detect_blobs(
        image_data: NDArray[float32], params: dict

) -> NDArray[float64]:
    """
    Given a masked array, returns the features detected within it.

    Parameters
    ----------
    image_data: NDArray[float32]
        Greyscale image in [Y, X], masked with NaN for areas to ignore
    params: dict
        Parameters for the blob detection. Those that are supposed to be passed to the actual algorithm
        are prefixed with 'blob_'.

    Returns
    -------
    NDArray[float64]: Four-column array containing blob y and x positions,
        and their size as [Y, X, size]
    """
    blobs: NDArray[float64] = blob_log(
        image_data, **{key.replace('blob_', ''): value for key, value in params.items() if 'blob_' in key}
    )
    return blobs


def filter_blobs(
        blobs: NDArray[float64], image_raw: NDArray[float32], params: Dict[str, float]
):
    """
    Given a list of blobs, and the colour image they were generated from, filters them.

    Parameters
    ----------
    blobs: NDArray[float64]
        Three-column array containing blob y and x positions,
        and their size as [Y, X, size, difference]
    image_raw: NDArray[float32]
        Colour image in [Y, X, RGB]
    params: dict
        Parameters for the blob detection.

    Returns
    -------
    NDArray[float64]: Four-column array containing blob y and x positions,
        and their size and difference as [Y, X, size, difference]
    """
    blob_differences: NDArray[float64] = numpy.zeros(
        (len(blobs), 1), dtype=float64
    )

    # It feels like this should be super inefficient, but it only takes ~3ms per mole
    # It should be vectorised though
    for idx, blob in enumerate(blobs):
        blob_differences[idx] = compare_feature_to_surroundings(
            image_raw, (int(blob[0]), int(blob[1])), blob[2], params=params
        )
    blobs = numpy.concatenate(
        [blobs, blob_differences], axis=1
    )
    return blobs[
        numpy.where(blobs[:, 3] > params['surroundings_difference_min'])
    ]
