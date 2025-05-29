"""
Helper functions that use functionality from the Python Image Library module

The typing looks a little messy as, infuriatingly, PIL has a horrible design pattern with factories in modules that
generate identically-named classes, and other capitalised functions that are function factories.

i.e.
  PIL.Image.fromarray is a function that returns a PIL.Image.Image
  PIL.ImageDraw is a function that returns a PIL.ImageDraw.ImageDraw

Why is Draw capitalised? Why doesn't it follow the same pattern as 'fromarray'?

This isn't PEP8 compliant at all and is a real annoyance.
"""
from typing import Tuple, Optional, List

from numpy._typing import NDArray
from numpy import uint8
import numpy
from PIL.ImageDraw import ImageDraw, Draw
from PIL import ImageFont, Image
from PIL.ImageFont import FreeTypeFont
from PIL.Image import Image as PILImageClass
from matplotlib.font_manager import findSystemFonts

from molegazer.log import get_logger


logger = get_logger(__name__.replace(".", "-"))


def convert_array_to_image(array: NDArray[uint8]) -> Tuple[PILImageClass, ImageDraw]:
    """
    Given an NDArray that corresponds to an RGB image, converts it into a PIL Image, with a drawing attachment.

    Parameters
    ----------
    array: NDArray[uint8]
        An array of RGB image data, in integer format. The type loaded by RawPy.

    Returns
    -------
    Image: The image, in PIL Image format.
    ImageDraw: A handle to draw on the image using PIL functions.
    """
    image: PILImageClass = Image.fromarray(
        array.astype(uint8)
    )
    return image, Draw(image)


def convert_array_to_pixels(array: NDArray[uint8], rgb: List[float]) -> PILImageClass:
    """
    Given an NDArray that's 0 where it should be transparent and nonzero where it should be opaque,
    returns an image matching those specifications in a given colour

    Parameters
    ----------
    array: NDArray[uint8]
        A mask where 0 is 'transparent' and
    rgb: List[float]
        The RGB colour to show the array pixels

    Returns
    -------
    Image: The image, in PIL Image format (i.e. integers from 0-255)
    """
    array_colour: NDArray[uint8] = numpy.full(
        (array.shape[0], array.shape[1], 3),
        (numpy.array(rgb, dtype=float) * 255).astype(uint8),
        dtype=uint8
    )
    image_colour: PILImageClass = Image.fromarray(
        array_colour, mode='RGB'
    )
    image_alpha: PILImageClass = Image.fromarray(
        array
    )
    image_colour.putalpha(
        image_alpha
    )
    return image_colour


def draw_frame_and_circle(
        draw: ImageDraw,
        position: Tuple[int, int], size: Tuple[int, int], circle_radius: int,
        line_width: Optional[int] = 1,
        border_colour: Optional[str] = 'black',
        circle_colour: Optional[str] = 'red'
):
    """
    Draws the border and hint circle on a panel within a context stamp.

    Parameters
    ----------
    draw: Draw
        A Python Image Library drawing canvas handle, linked to an image
    position: Tuple[position_x, position_y]
        The X and Y positions on the drawing canvas to begin the border and dircle
    size: Tuple[size_w, size_h]:
        The width and height of the border to draw (x and y)
    circle_radius: int
        The radius of the circle to draw in the middle of the frame
    line_width: Optional[int], default 1
        The widths of the frame and circle lines
    border_colour: Optional[str], default 'black', valid colour
        The colour of the frame bordering the image.
    circle_colour: Optional[str], default 'red', valid colour
        The colour of the hint circle in the centre of the image
    """
    position_x, position_y = position
    size_w, size_h = size

    draw.rectangle(
        xy=(
            (position_x, position_y),
            (position_x + size_w - 1, position_y + size_h - 1)
        ),
        width=line_width,
        outline=border_colour
    )
    draw_circle(
        draw,
        centre=(position_x + size_w//2, position_y + size_h//2),
        radius=circle_radius,
        line_width=line_width, line_colour=circle_colour
    )


def draw_circle(
        draw: ImageDraw,
        centre: Tuple[int, int], radius: int,
        line_width: Optional[int] = 1,
        line_colour: Optional[str] = 'red'
):
    """
    Draws a circle on an image.

    Parameters
    ----------
    draw: Draw
        A Python Image Library drawing canvas handle, linked to an image
    centre: Tuple[centre_x, centre_y]
        The X and Y positions on the drawing canvas to centre the circle
    radius: int
        The radius of the circle to draw
    line_width: Optional[int], default 1
        The widths of the frame and circle lines
    line_colour: Optional[str], default 'red', valid colour
        The colour of the circle
    """
    centre_x, centre_y = centre

    draw.ellipse(
        xy=(
            (centre_x - radius, centre_y - radius),
            (centre_x + radius, centre_y + radius),
        ),
        width=line_width,
        outline=line_colour
    )


def get_font_sizes(
    sizes: List[int],
    name: Optional[str] = None,
) -> List[FreeTypeFont]:
    """
    Gets

    Parameters
    ----------
    sizes: List[int]
        The sizes of font you would like to get
    name: Optional[str]
        The name of the font you would like to use, or defaults to the first 'Mono' font,
        or if no 'Mono' font the first font.

    Returns
    -------
    List[FreeTypeFont]: The font sizes requested.
    """

    font: str = ''
    system_fonts: List[str] = [
        system_font for system_font in findSystemFonts() if '.ttf' in system_font
    ]
    if name:
        for system_font in system_fonts:
            if name in system_font:
                font = system_font
                break
    if not font:
        for system_font in system_fonts:
            if 'Mono' in system_font:
                font = system_font
                break
    if not font:
        font = system_fonts[0]

    return [
        ImageFont.truetype(font, size=size) for size in sizes
    ]
