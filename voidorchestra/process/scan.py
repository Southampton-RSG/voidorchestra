from typing import Tuple, List, Optional


from pathlib import Path
import numpy
from matplotlib.colors import rgb2hex
from matplotlib.cm import coolwarm
from numpy import float64, float32, uint8
from numpy._typing import NDArray
from pandas import DataFrame, read_csv
from PIL import Image as PILImage
from PIL.ImageDraw import Draw
from PIL.Image import Image as PILImageClass

from voidorchestra.db import Image
from molegazer.process.stamps.mask import mask_image
from molegazer.process.stamps.blob import detect_blobs, filter_blobs
from molegazer.util.image import read_image_nef
from molegazer.util.pil import draw_frame_and_circle, draw_circle, get_font_sizes, convert_array_to_pixels
from molegazer.util.cv import generate_contour
from molegazer.input.config import load_feature_params, FILTERING_PARAMETERS
from molegazer.log import get_logger


logger = get_logger(__name__.replace(".", "-"))


def sweep_param_space(
        image: Image, test_param: str,
        test_param_range: Tuple[float, float],
        test_param_steps: int,
        blob_file: Optional[Path] = None
):
    """
    Given an image, sweeps the parameter space to see how the detected features change.

    Parameters
    ----------
    image: Image
        The image to parameter scan
    test_param: str
        The parameter to sweep over
    test_param_range: Tuple[float, float]
        The (lowest, highest) parameter values to test
    test_param_steps: int
        The number of values of the parameter to test
    blob_file: Path
        The location of a file containing previously-detected blobs

    Outputs
    -------
    collage_{TEST PARAMETER AND RANGE DETAILS}.png:
        A figure showing which moles are dropped across the parameter sweep.
        The top group is moles that are only detected at the initial param value, no others.
        The group below is moles that could be detected with param value 2, but no others
        This repeats until the last line is moles that were detected across the whole range.
        These groups are sorted by feature size.

    overview_{TEST PARAMETER AND RANGE DETAILS}.png:
        The full-body image, with the moles found labelled on it.
        Each is circled, with a radius proportional to the mole size, plus a base, where the
        colour of the circle reflects the position through the parameter scan it dropped;
        from blue (early), through white, to red (remained until the end).
    """
    logger.debug(f"Processing {image}: {image.filepath}")

    # Get the default parameters, then replace one with our testing range
    test_params: dict = load_feature_params()
    param_range: NDArray[float64] = numpy.linspace(
        test_param_range[0], test_param_range[1],
        num=test_param_steps, endpoint=True
    )
    test_params[test_param] = param_range

    # Log to the console for the user, and file for full details
    logger.info(
        f"Scanning '{test_param}' range: {param_range}"
    )
    logger.debug(
        f"Test parameters are:\n{test_params}"
    )

    # Load our image, and set up the masked versions of it
    image_raw: NDArray[float32] = read_image_nef(image)
    image_colour_masked: NDArray[float32] = None
    image_grey_masked: NDArray[float32] = None
    list_masks: List[NDArray[float32]] = []

    # Prepare our list of blobs, and load them to save time if we're not re-running the blob detection
    blobs_for_params: List[NDArray[float64]] = []
    if not blob_file:
        blobs: NDArray[float64] = None
    else:
        blob_dataframe = read_csv(blob_file)
        blobs = blob_dataframe[['y', 'x', 'radius']].to_numpy(dtype=float64)

    # Sweep over all our values of the test parameter
    for param_value in test_params[test_param]:
        logger.debug(
            f"Testing {test_param}={param_value}..."
        )

        params_copy: dict = test_params.copy()
        params_copy[test_param] = param_value

        # If we haven't yet generated our masked image, *or* we're testing varying the mask
        if image_colour_masked is None or 'mask' in test_param:
            logger.debug("Generating mask...")
            image_colour_masked, image_grey_masked = mask_image(
                image_raw, params=params_copy
            )
            # If we're testing mask params, we want to save the mask
            if 'mask' in test_param:
                list_masks.append(
                    generate_contour(image_grey_masked, iterations=5)
                )

        # If we haven't yet generated our masked image, *or* we're testing actual image generation params
        if blobs is None or test_param not in FILTERING_PARAMETERS:
            logger.debug(f"Running blob detection...")
            blobs = detect_blobs(
                image_grey_masked, params=params_copy
            )

        # Then filter the blobs, and append them to our list,
        # tagged with an extra column that's the value of the tested parameter
        blobs_filtered: NDArray[float64] = filter_blobs(
            blobs, image_colour_masked, params=params_copy
        )

        blobs_for_params.append(
            numpy.concatenate(
                [
                    blobs_filtered,
                    numpy.ones((len(blobs_filtered), 1), dtype=float64) * param_value
                ],
                axis=1
            )
        )

        logger.debug(
            f"{test_param}={param_value}: Found {len(blobs_filtered)} blobs"
        )

    # Now, concatenate them all into a single dataframe, and remove duplicates;
    # we only want the latest possible detection for each
    dataframe: DataFrame = DataFrame(
        data=numpy.concatenate(blobs_for_params),
        columns=[
            "y", "x", "radius", "difference", test_param
        ]
    ).drop_duplicates(
        subset=["x", "y"], keep='last'
    ).sort_values(
        by=[test_param, 'radius', 'difference']
    )

    # We save to disk for future use
    dataframe.to_csv(f'{image.image_name}_blobs.csv')

    # Make the images
    pil_font_20, pil_font_40, pil_font_60 = get_font_sizes([20, 40, 60])
    pil_image: PILImageClass = PILImage.fromarray(
        image_raw.astype(uint8)
    )

    # Prepare the 'collage'. We need to know how many rows of pictures there will be
    image_rows: int = test_param_steps
    for param_value, count in dataframe[test_param].value_counts().items():
        image_rows += (count // 20)

    pil_collage: PILImageClass = PILImage.new(
        'RGBA',
        (2200, (100*image_rows)+25*(image_rows - 1)),
        (0, 0, 0, 0)
    )
    draw_collage: Draw = Draw(pil_collage)

    # Prepare the 'overview' (a copy of the detected picture)
    pil_overview: PILImageClass = pil_image.copy()
    draw_overview: Draw = Draw(pil_overview)
    _, _, overview_line_width, overview_line_height = draw_overview.textbbox(
        (0, 0), f"{test_param}", font=pil_font_40
    )

    # Draw the mask contours on the image
    if 'mask' in test_param and test_param_steps > 1:
        # If we're testing a mask parameter, then plot them colour-matching the circles
        for param_index, image_mask_contour in enumerate(list_masks):
            values_rgb: List[float] = coolwarm(param_index / (test_param_steps - 1))
            pil_contour: NDArray[uint8] = convert_array_to_pixels(
                image_mask_contour, rgb=values_rgb[:3]
            )
            pil_overview.paste(
                pil_contour, (0, 0), pil_contour
            )

    else:
        image_mask_contour = generate_contour(image_grey_masked, iterations=5)
        pil_contour: NDArray[uint8] = convert_array_to_pixels(
            image_mask_contour, rgb=[1, 0, 1]
        )
        pil_overview.paste(
            pil_contour, (0, 0), pil_contour
        )

    # Draw the background for the text, and the text itself
    draw_overview.rectangle(
        (
            (25, 25),
            (25 + overview_line_width + 50, 50 + overview_line_height*(1+test_param_steps) + 50)
        ),
        fill='black'
    )
    draw_overview.text(
        (50, 50), f"{test_param}", font=pil_font_40
    )

    # So, for each parameter value, we now want to go through all the features last detected
    # at that parameter value, and add them to the collage and overview
    current_y: int = 0
    for param_index, param_value in enumerate(param_range):
        current_x: int = 0

        # Allow for situation where we're just testing a single value
        if test_param_steps > 1:
            colour_rgb: str = rgb2hex(
                coolwarm(param_index / (test_param_steps - 1))
            )
        else:
            colour_rgb: str = 'fuchsia'

        for _, row in dataframe[
            dataframe[test_param] == param_value
        ].iterrows():

            right = int(row.x + 50)
            left = int(row.x - 50)
            top = int(row.y - 50)
            bottom = int(row.y + 50)

            # Add the snapshot of the mole to the collage
            pil_collage.paste(
                pil_image.crop(
                    (left, top, right, bottom)
                ),
                (current_x, current_y)
            )
            draw_frame_and_circle(
                draw_collage, (current_x, current_y), (100, 100),
                circle_radius=int(5+row.radius*2),
                line_width=1, border_colour='black', circle_colour='red'
            )
            draw_collage.text(
                (current_x + 5, current_y + 2),
                f"r {round(row.radius, 2)}",
                font=pil_font_20, fill='red'
            )
            draw_collage.text(
                (current_x + 5, current_y + 72),
                f"d {round(row.difference, 2)}",
                font=pil_font_20, fill='blue'
            )

            # Add the mole to the overview
            draw_circle(
                draw_overview, (row.x, row.y), int(8+row.radius*2),
                line_width=3, line_colour=colour_rgb
            )

            # Now advance the position, and go down a row on the collage if we've made it
            # to the end of a line
            current_x += 100
            if current_x >= 2000:
                current_x = 0
                current_y += 100

        # Now add on the 'current value' test on the collage
        draw_collage.text(
            (current_x+10, current_y+10),
            f"{test_param}={round(param_value, 2)}",
            font=pil_font_40
        )

        # Add the parameter colour to the overview as well
        draw_overview.text(
            (50, 50 + overview_line_height*(param_index+1)),
            f"{round(param_value, 2)}",
            font=pil_font_60, fill=colour_rgb
        )

        current_y += 125

    pil_collage.save(f'{image.image_name}_collage_{test_param}_{test_param_range[0]}_{test_param_range[1]}.png')
    pil_overview.save(f'{image.image_name}_overview_{test_param}_{test_param_range[0]}_{test_param_range[1]}.png')
    logger.info(
        "Saved outputs."
    )
