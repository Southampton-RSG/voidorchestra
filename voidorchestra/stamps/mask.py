from typing import Tuple, Dict

import cv2
from numpy import float32, uint8, NaN
from numpy._typing import NDArray

from molegazer.util.cv import generate_skin_mask, generate_background_mask
from molegazer.log import get_logger


logger = get_logger(__name__.replace(".", "-"))


def mask_image(
        image_data: NDArray[float32],
        params: Dict
) -> Tuple[NDArray[float32], NDArray[float32]]:
    """
    Given a colour image containing skin, returns makes copies of the image in colour and greyscale with
    the non-skin regions masked.

    Parameters
    ----------
    image_data: NDArray[float32]
        The colour image, in Y, X, RGB format, normalised to 0-1.
    params: Dict
        The parameters

    Returns
    -------
    NDArray[float32]:
        A [Y, X. RGB] copy of the image,
        with non-skin areas masked using NaN values
    NDArray[float32]:
        A [Y, X] inverted greyscale copy of the image,
        with non-skin areas masked using NaN values
    """
    # Turn the image greyscale, and invert
    image_grey: NDArray[float32] = 255.0 - cv2.cvtColor(image_data, cv2.COLOR_RGB2GRAY)

    # Run the skin detection algorithm
    mask_skin: NDArray[uint8] = generate_skin_mask(
        image_data,
        params['mask_skin_closure_steps']
    )
    # Run the background detection algorithm
    mask_background: NDArray[uint8] = generate_background_mask(
        image_data,
        corner_fraction=params['mask_background_corner_fraction'],
        colour_range_mult=params['mask_background_colour_range_mult'],
        expand_cycles=int(params['mask_background_expand_cycles'])
    )

    # Combine the two masks, to give 0 where neither apply, 1 where one does, or 2 where both do
    mask: NDArray[uint8] = (1 - mask_skin) + mask_background

    # Now we have the 'closed' mask, apply it to our greyscale image.
    image_grey_masked = image_grey.copy()
    image_grey_masked[mask != 0] = NaN
    image_colour_masked = image_data.copy()
    image_colour_masked[mask != 0] = NaN
    return image_colour_masked, image_grey_masked
