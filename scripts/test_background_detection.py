"""
Test script for background detection - intended to stop 'background behind hair' being flagged as a feature
"""
from pathlib import Path
from typing import Dict, Tuple
import numpy
from numpy import float32, float64, uint8, NaN
from numpy.typing import NDArray
from matplotlib import pyplot as plt
from matplotlib.patches import Circle
import cv2
from pandas import DataFrame, read_csv

from molegazer.util.cv import generate_skin_mask, generate_contour
from molegazer.util.rawpy import read_and_rescale_nef
from molegazer.process.stamps import detect_blobs, filter_blobs, mask_image
from molegazer.input.config import load_feature_params

IMAGE_FILE: Path = Path(  # Woman with longer hair
    "data/raw/B002/2021-12-10/B002_10_12_2021_001.NEF"
)
# IMAGE_FILE: Path = Path(  # Generic white male with short hair
#     "data/raw/A001/2021-11-11/A001_11_11_2021_002.NEF"
# )
BLOB_FILE: Path = Path(
    "test_background_detection_blobs.csv"
)
COLOUR_RANGE_SIZE: float = 0.2
CORNER_Y_FRACTION: float = 0.1
CORNER_X_FRACTION: float = 0.1

# Load parameters
blob_params: Dict[str, float] = load_feature_params()

print(f"Loading {IMAGE_FILE} and masking...")
image_raw: NDArray[float32] = read_and_rescale_nef(IMAGE_FILE)
image_skin_mask: NDArray[uint8] = generate_skin_mask(image_raw, close_mask=5)
image_colour_masked, image_grey_masked = mask_image(image_raw, params=blob_params)

# Mask off everything but the corners, then get the main colour there
image_corner_mask: NDArray[uint8] = numpy.zeros_like(image_skin_mask)
corner_y_bottom: int = int(image_corner_mask.shape[0] * CORNER_Y_FRACTION)
corner_x_left: int = int(image_corner_mask.shape[1] * CORNER_X_FRACTION)
corner_x_right: int = int(image_corner_mask.shape[1] * (1 - CORNER_X_FRACTION))
image_corner_mask[:corner_y_bottom, :corner_x_left] = 1
image_corner_mask[:corner_y_bottom, corner_x_right:] = 1

border_pixels: NDArray[float32] = image_raw[image_corner_mask != 0]

# Use KMeans to identify the colours in this border region
print("Using KMeans to select background...")
kmeans_criteria: Tuple = (
    cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0
)

compactness, labels, centres = cv2.kmeans(
    border_pixels, 3, None,
    criteria=kmeans_criteria, attempts=10,
    flags=cv2.KMEANS_RANDOM_CENTERS
)

# See what the most common background colour is
most_common_colour: NDArray[float32] = centres[
    numpy.unique(labels, return_counts=True)[1].argmax()
]

# See which areas the code thinks are background, for a given colour range size
background_colour_lower: NDArray[float32] = most_common_colour * (1-COLOUR_RANGE_SIZE)
background_colour_upper: NDArray[float32] = most_common_colour * (1+COLOUR_RANGE_SIZE)
image_background_mask: NDArray[uint8] = cv2.inRange(
    image_raw,
    lowerb=background_colour_lower, upperb=background_colour_upper
) / 255

# Expand the background to clip off the edge
print("Expanding background selection...")
BACKGROUND_EXPAND_CYCLES: int = 10
image_background_mask_dilated = cv2.dilate(
    image_background_mask, numpy.ones((5, 5), uint8),
    iterations=BACKGROUND_EXPAND_CYCLES
)

# Do canny edge detection as a test
image_edges = cv2.Canny(
    (255 - cv2.cvtColor(image_raw, cv2.COLOR_RGB2GRAY)).astype(uint8), 25, 50, 5
)
image_edges = cv2.dilate(image_edges, numpy.ones((3, 3)), 10)
cv2.imwrite("edges.png", image_edges)

mask_comparison = numpy.zeros_like(image_background_mask)
mask_comparison[image_background_mask_dilated != 0] = 1
mask_comparison[image_background_mask != 0] = 2

# Display the combo of the background and skin masks
print("Generating final mask")
final_mask = image_background_mask_dilated + (1-image_skin_mask)
image_background_masked = image_raw.copy()
image_background_masked[final_mask != 0] = [0, 255, 255]
image_grey_masked[final_mask != 0] = NaN

# Create the contour (we could do this directly from the actual mask we just generated, but it's a trial)
image_mask_contour = generate_contour(image_grey_masked, iterations=5)

# Load the blobs, or greate new ones
if BLOB_FILE.exists():
    print(f"Loading blobs from {BLOB_FILE}...")
    dataframe: DataFrame = read_csv(BLOB_FILE)
else:
    print(f"Detecting blobs and saving to {BLOB_FILE}...")
    blobs: NDArray[float64] = detect_blobs(image_grey_masked, params=blob_params)
    blobs = filter_blobs(
        blobs=blobs, image_raw=image_raw, params=blob_params
    )
    dataframe: DataFrame = DataFrame(
        data=blobs,
        columns=[
            "y", "x", "radius", "difference"
        ]
    )
    print(f"Detected {len(blobs)} blobs")
    dataframe.to_csv(BLOB_FILE)

# Now plot the original image, our final mask, and tbe background image
fig, (ax_orig, ax_mask_background, ax_mask_skin, ax_mask_combined, ax_contour, ax_masked) = plt.subplots(
    1, 6, figsize=(12, 10)
)
ax_orig.imshow(image_raw / 255)

ax_mask_background.set_title("Background mask")
ax_mask_background.imshow(
    mask_comparison
)
ax_mask_skin.set_title("Skin mask")
ax_mask_skin.imshow(
    image_skin_mask
)
ax_mask_combined.set_title("Combined mask")
ax_mask_combined.imshow(
    final_mask
)
ax_contour.imshow(
    image_edges
)
ax_masked.imshow(
    image_background_masked / 255
)

for _, row in dataframe.iterrows():
    circle = Circle(
        (row.x, row.y), (row.radius*2) + 5, color='red', fill=False
    )
    ax_masked.add_patch(circle)


plt.show()
