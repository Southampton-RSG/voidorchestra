"""
Test script for Hough Line detection - intended to explore if hair can be spotted using it.
"""
from pathlib import Path
from typing import Dict, Optional
import numpy
from numpy import float32, float64, uint8, NaN
from numpy.typing import NDArray
from numpy.ma import masked_invalid
from matplotlib import pyplot as plt
import cv2
from pandas import DataFrame, read_csv

from molegazer.util.cv import generate_skin_mask
from molegazer.util.rawpy import read_and_rescale_nef
from molegazer.process.stamps import detect_blobs, mask_image
from molegazer.input.config import load_feature_params

image_file: Path = Path(
    "data/raw/A001/2021-08-19/A001_19_08_2021_002.NEF"
)
blob_file: Path = Path(
    "test_hough_lines_blobs.csv"
)

print(f"Loading {image_file} and masking...")
image_raw: NDArray[float32] = read_and_rescale_nef(image_file)
image_skin_mask: NDArray[uint8] = detect_skin(image_raw)
image_colour_masked, image_grey_masked = mask_image(image_raw)
blob_params: Dict[str, float] = load_feature_params()

if blob_file.exists():
    print(f"Loading blobs from {blob_file}...")
    dataframe: DataFrame = read_csv(blob_file)
else:
    print(f"Detecting blobs and saving to {blob_file}...")
    blobs: NDArray[float64] = detect_blobs(image_grey_masked, params=blob_params)
    dataframe: DataFrame = DataFrame(
        data=blobs,
        columns=[
            "y", "x", "radius"
        ]
    )
    dataframe.to_csv(blob_file)

image_background = image_raw.copy()
image_background[image_skin_mask != 0] = NaN

fig, (ax_orig, ax_detect) = plt.subplots(1, 2, figsize=(12, 10))
ax_orig.imshow(image_colour_masked / 255)
ax_detect.imshow(
    image_background / 255
)

plt.show()

# print(f"Hough Line detection...")
# image_integer: NDArray[uint8] = numpy.nan_to_num(image_grey_masked).astype(uint8)
#
# for idx, row in dataframe.iterrows():
#     blob_x = int(row.x)
#     blob_y = int(row.y)
#     # image_region: NDArray[uint8] = image_integer[
#     #     blob_y-40: blob_y+40, blob_x-40: blob_x+40
#     # ]
#     image_region: NDArray[float32] = image_raw[
#         blob_y - 20: blob_y + 20, blob_x - 20: blob_x + 20, :
#     ]
#
#     fig, (ax_orig, ax_detect) = plt.subplots(1, 2, figsize=(12, 10))
#     fig.suptitle(f"{idx}, radius: {row.radius}")
#     ax_orig.imshow(image_region / 255)
#     ax_detect.imshow(detect_skin(image_region), vmin=0, vmax=1)
#
#     plt.show()
#
#     # lines: NDArray = cv2.HoughLinesP(
#     #     image_region,
    #     rho=1, theta=numpy.pi/180, threshold=500, minLineLength=3, maxLineGap=2
    # )
    # if lines:
    #     fig, ax = plt.subplots(1, 1)
    #     ax.imshow(255 - image_region, cmap='gray', vmin=0, vmax=255)
    #
    #     for i in range(len(lines)):
    #         ax.plot(
    #             [lines[i, 0, 0], lines[i, 0, 2]],
    #             [lines[i, 0, 1], lines[i, 0, 3]]
    #         )
    #
    #     plt.show()


# for xcen, ycen, radius, name in centres:
#     print(name)
#
#     fig, ax = plt.subplots(5, 3, figsize=(12, 10))
#     for j in range(3):
#         ax[0, j].axis('off')
#         ax[2, j].axis('off')
#         ax[4, j].axis('off')
#
#     window_size = radius * 2 + 15
#     window = numpy.s_[
#         ycen-window_size:ycen+window_size,
#         xcen-window_size:xcen+window_size
#     ]
#
#     mask_coords_inner = disk((ycen, xcen), radius)
#     mask_coords_outer = disk((ycen, xcen), radius * 2 + 5)
#
#     mask_feature = numpy.zeros_like(i_red, dtype=bool)
#     mask_environment = numpy.zeros_like(i_red, dtype=bool)
#
#     mask_feature[mask_coords_inner] = True
#     mask_environment[mask_coords_outer] = True
#     mask_environment[mask_coords_inner] = False
#
#     mask_feature = mask_feature[window]
#     mask_environment = mask_environment[window]
#
#     red = i_red[window]
#     green = i_green[window]
#     blue = i_blue[window]
#
#     alpha_environment = numpy.zeros_like(red, dtype=numpy.float32)
#     alpha_environment[mask_environment] = 1.0
#
#     alpha_feature = numpy.zeros_like(red, dtype=numpy.float32)
#     alpha_feature[mask_feature] = 1.0
#
#     ax[0, 0].imshow(red, cmap='gray', alpha=alpha_environment)
#     ax[0, 1].imshow(green, cmap='gray', alpha=alpha_environment)
#     ax[0, 2].imshow(blue, cmap='gray', alpha=alpha_environment)
#
#     hist_env_red, hist_bins = histogram(red[mask_environment].flatten(), nbins=32, normalize=True)
#     hist_env_green, _ = histogram(green[mask_environment].flatten(), nbins=32, normalize=True)
#     hist_env_blue, _ = histogram(blue[mask_environment].flatten(), nbins=32, normalize=True)
#
#     ax[1, 0].plot(hist_bins, hist_env_red, color='r')
#     ax[1, 1].plot(hist_bins, hist_env_green, color='g')
#     ax[1, 2].plot(hist_bins, hist_env_blue, color='b')
#
#     ax[2, 0].imshow(red, cmap='gray')
#     ax[2, 1].imshow(green, cmap='gray')
#     ax[2, 2].imshow(blue, cmap='gray')
#
#     hist_feat_red, _ = histogram(red[mask_feature].flatten(), nbins=32, normalize=True)
#     hist_feat_green, _ = histogram(green[mask_feature].flatten(), nbins=32, normalize=True)
#     hist_feat_blue, _ = histogram(blue[mask_feature].flatten(), nbins=32, normalize=True)
#
#     ax[3, 0].plot(hist_bins, hist_feat_red, color='r')
#     ax[3, 1].plot(hist_bins, hist_feat_green, color='g')
#     ax[3, 2].plot(hist_bins, hist_feat_blue, color='b')
#
#     ax[4, 0].imshow(red, cmap='gray', alpha=alpha_feature)
#     ax[4, 1].imshow(green, cmap='gray', alpha=alpha_feature)
#     ax[4, 2].imshow(blue, cmap='gray', alpha=alpha_feature)
#
#     diff_red_correl = cv2.compareHist(
#         hist_env_red.astype(numpy.float32), hist_feat_red.astype(numpy.float32),
#         method=cv2.HISTCMP_CORREL
#     )
#     diff_green_correl = cv2.compareHist(
#         hist_env_green.astype(numpy.float32), hist_feat_green.astype(numpy.float32),
#         method=cv2.HISTCMP_CORREL
#     )
#     diff_blue_correl = cv2.compareHist(
#         hist_env_blue.astype(numpy.float32), hist_feat_green.astype(numpy.float32),
#         method=cv2.HISTCMP_CORREL
#     )
#
#     diff_red_bhat = cv2.compareHist(
#         hist_env_red.astype(numpy.float32), hist_feat_red.astype(numpy.float32),
#         method=cv2.HISTCMP_BHATTACHARYYA
#     )
#     diff_green_bhat = cv2.compareHist(
#         hist_env_green.astype(numpy.float32), hist_feat_green.astype(numpy.float32),
#         method=cv2.HISTCMP_BHATTACHARYYA
#     )
#     diff_blue_bhat = cv2.compareHist(
#         hist_env_blue.astype(numpy.float32), hist_feat_green.astype(numpy.float32),
#         method=cv2.HISTCMP_BHATTACHARYYA
#     )
#
#     ax[0, 0].text(0, 0, f"Correlation: {diff_red_correl}")
#     ax[0, 1].text(0, 0, f"Correlation: {diff_green_correl}")
#     ax[0, 2].text(0, 0, f"Correlation: {diff_blue_correl}")
#
#     ax[0, 0].text(0, 12, f"Bhattacharyva: {diff_red_bhat}")
#     ax[0, 1].text(0, 12, f"Bhattacharyva: {diff_green_bhat}")
#     ax[0, 2].text(0, 12, f"Bhattacharyva: {diff_blue_bhat}")
#
#     plt.tight_layout()
#     plt.savefig(f'hist_comparison_{name}.png')
