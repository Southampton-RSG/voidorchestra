import cv2
import numpy
from numpy import float32, uint8
from numpy.typing import NDArray
from molegazer.log import get_logger


logger = get_logger(__name__.replace(".", "-"))


def _detect_skin(img: NDArray) -> NDArray[uint8]:
    """
    Detects regions of skin in an image and generates a mask
    Derived from: https://github.com/CHEREF-Mehdi/SkinDetection

    Parameters
    ----------
    img: A numpy array containing an RGB image of a person.

    Returns
    -------
    A boolean array with 255 where there is skin and 0 where there is none

    Citation
    --------
    Djamila Dahmani, Mehdi Cheref, Slimane Larabi,
    Zero-sum game theory model for segmenting skin regions,
    Image and Vision Computing, Volume 99, 2020, 103925,ISSN 0262-8856,
    https://doi.org/10.1016/j.imavis.2020.103925.
    """
    img = img.astype(uint8)

    # converting from gbr to hsv color space
    img_HSV = cv2.cvtColor(img, cv2.COLOR_RGB2HSV)
    # skin color range for hsv color space
    HSV_mask = cv2.inRange(img_HSV, (0, 15, 0), (17, 170, 255))
    HSV_mask = cv2.morphologyEx(HSV_mask, cv2.MORPH_OPEN, numpy.ones((3, 3), uint8))

    # converting from gbr to YCbCr color space
    img_YCrCb = cv2.cvtColor(img, cv2.COLOR_RGB2YCrCb)
    # skin color range for hsv color space
    YCrCb_mask = cv2.inRange(img_YCrCb, (0, 135, 85), (255, 180, 135))
    YCrCb_mask = cv2.morphologyEx(YCrCb_mask, cv2.MORPH_OPEN, numpy.ones((3, 3), uint8))

    # merge skin detection (YCbCr and hsv)
    global_mask = cv2.bitwise_and(YCrCb_mask, HSV_mask)
    global_mask = cv2.medianBlur(global_mask, 3)
    global_mask: NDArray[uint8] = cv2.morphologyEx(global_mask, cv2.MORPH_OPEN, numpy.ones((4, 4), uint8))

    HSV_result = cv2.bitwise_not(HSV_mask)
    YCrCb_result = cv2.bitwise_not(YCrCb_mask)
    # global_result = cv2.bitwise_not(global_mask)

    return global_mask


def generate_background_mask(
        image_data: NDArray[float32],
        corner_fraction: float,
        colour_range_mult: float,
        expand_cycles: int
) -> NDArray[uint8]:
    """
    Given an image, detects the background colour (assuming the top left and right corners are background) and
    creates a mask based on selecting it and expanding that selection.

    Parameters
    ----------
    image_data: NDArray[float32]
        The image to mask, in [Y, X, RGB] format
    corner_fraction: float, default 0.1
        What fraction of the image's top left and right corners are the background (e.g. for a 100x100 picture,
        0,1 would assume the top 10x10 pixels in each corner are mostly 'background'
    colour_range_mult: float, default 0.2
        The range in RGB values around the background colour to consider 'background'
        (e.g. 100,100,100 background would match 80-120,80-120,80-120)
        TODO: This should almost certainly be rejigged into hue-saturation-value space with absolute values
    expand_cycles: int, default 20
        How many dilate cycles to run with a 5x5 grid to catch pixels *near* the background.
        Approximately how many pixels outwards to expand the region. Designed to catch halos of hair around bodies.

    Returns
    -------
    NDArray[uint8]: The mask, where 1 is "Background (or near background)" and 0 is "Not background"
    """
    # Mask off everything but the corners, then get the main colour there
    image_corner_mask: NDArray[uint8] = numpy.zeros_like(image_data)
    corner_y_bottom: int = int(image_corner_mask.shape[0] * corner_fraction)
    corner_x_left: int = int(image_corner_mask.shape[1] * corner_fraction)
    corner_x_right: int = int(image_corner_mask.shape[1] * (1 - corner_fraction))
    image_corner_mask[:corner_y_bottom, :corner_x_left] = 1
    image_corner_mask[:corner_y_bottom, corner_x_right:] = 1

    border_pixels: NDArray[float32] = image_data[image_corner_mask != 0]

    # Use KMeans to identify the colours in this border region
    compactness, labels, centres = cv2.kmeans(
        border_pixels, 3, None,
        criteria=(
            cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER,
            10,
            1.0
        ),
        attempts=10,
        flags=cv2.KMEANS_RANDOM_CENTERS
    )
    # See what the most common background colour is
    most_common_colour: NDArray[float32] = centres[
        numpy.unique(labels, return_counts=True)[1].argmax()
    ]

    # See which areas the code thinks are background, for a given colour range size
    background_colour_lower: NDArray[float32] = most_common_colour * (1 - colour_range_mult)
    background_colour_upper: NDArray[float32] = most_common_colour * (1 + colour_range_mult)
    image_background_mask: NDArray[uint8] = cv2.inRange(
        image_data,
        lowerb=background_colour_lower, upperb=background_colour_upper
    ) / 255

    # Expand the background to clip off the edge
    return cv2.dilate(
        image_background_mask.astype(uint8), numpy.ones((5, 5), uint8),
        iterations=expand_cycles
    )


def generate_skin_mask(
        image_data: NDArray, close_mask: int
) -> NDArray:
    """
    Given an image, generates a mask of the skin regions for it.

    Parameters
    ----------
    image_data: NDArray[float32]
        The image to mask, in [Y, X, RGB] format
    close_mask: int, default 5
        Whether to run an erode/dilate cycle to close small holes in the mask,
        and how many cycles to run.

    Returns
    -------
    NDArray[uint8]: The mask, where 1 is "Skin" and 0 is "Not skin"
    """
    mask: NDArray[uint8] = _detect_skin(image_data)

    if close_mask:
        # Run an erode/dilate cycle, to remove small gaps in the mask (e.g. potentially moles!)
        mask: NDArray[uint8] = cv2.morphologyEx(
            mask, cv2.MORPH_CLOSE, numpy.ones((5, 5), uint8),
            iterations=close_mask
        )

    return mask / 255


def generate_contour(
        image_masked: NDArray[float32], iterations: int
) -> NDArray[float32]:
    """
    Given a greyscale image masked using the above functions, writes a contour around the edge of the masked region.

    Parameters
    ----------
    image_masked: NDArray[float32]
        A greyscale image with pixels masked off using NaN
    iterations: int
        The number of dilate iterations to expand the single-pixel boundary using

    Returns
    -------
    NDArray[uint8]: The contour pixels, expanded slightly, with a value of 1 for the edge
    """
    # We reverse-engineer the mask here
    # No point having the mask code return the full mask as we'd always throw it away except during scans
    image_mask = numpy.zeros_like(image_masked, dtype=uint8)
    image_mask[numpy.isnan(image_masked)] = 1
    image_mask_contour = cv2.Canny(
        image_mask, 0, 1
    )

    image_mask_contour = cv2.dilate(
        image_mask_contour, numpy.ones((3, 3)), iterations=iterations
    )

    return image_mask_contour
