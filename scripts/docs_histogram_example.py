"""
Demonstration code for generating image that illustrates how the histogram metrics system works.
Uses output of the 'scan' command for a given image. Does not make calls to the database.

Usage:
    docs_histogram_example.py PATH_TO_IMAGE PATH_TO_CSV_FILE_OF_BLOBS
"""
from sys import argv

from matplotlib import pyplot as plt
from matplotlib.gridspec import GridSpec
from numpy import float64, float32
from numpy._typing import NDArray
from pandas import DataFrame, read_csv
from rawpy import imread
from skimage.draw import disk
from cv2 import compareHist, HISTCMP_BHATTACHARYYA

import numpy

from molegazer.input.config import load_feature_params


# Loads the image data
image_data: NDArray[float32] = imread(
    argv[1]  # e.g. 'data/raw/A001/2021-08-19/A001_19_08_2021_002.NEF'
).postprocess(
    output_bps=16  # If we don't specify, it downscales to 8-bit colour depth!
).astype(float32) * 255 / 65535

# Load info on the blobs in that image. Does not enforce it is the same image!
blob_dataframe: DataFrame = read_csv(
    argv[2]  # Should be in the format of the test.csv files that scan writes out
)
blobs = blob_dataframe[['y', 'x', 'radius']].to_numpy(dtype=float64)

params = load_feature_params()

for blob in blobs:
    # Get the stats of the blob from the array; Y, X, size
    centre = (int(blob[0]), int(blob[1]))
    radius_outer: int = int(
        blob[2] * params['surroundings_radius_mult_outer'] + params['surroundings_radius_add_outer']
    )
    radius_inner: int = int(
        blob[2] * params['surroundings_radius_mult_inner'] + params['surroundings_radius_add_inner']
    )
    # Exclude
    if any([
        centre[0] - radius_outer < 0, centre[0] + radius_outer >= image_data.shape[0],
        centre[1] - radius_outer < 0, centre[1] + radius_outer >= image_data.shape[1]
    ]):
        # If the surroundings extend outside the image, we can't compare. Skip.
        continue

    # Select the subset we'll be comparing
    image_region: NDArray[float32] = image_data[
        centre[0]-radius_outer: centre[0]+radius_outer,
        centre[1]-radius_outer: centre[1]+radius_outer,
        :
    ]

    # We set up a large grid of matplotlib figures. I should not have chosen MatPlotLib; it's *awful*.
    fig = plt.figure(figsize=(12, 6))
    gs = GridSpec(
        3, 5, width_ratios=[1, 1, 1, 1, 2], height_ratios=[1, 1, 1],
        wspace=0.0, hspace=0.0, top=0.9, bottom=0.1, left=0.1, right=0.9
    )

    # The first subplot is the 'full image'
    ax_base = fig.add_subplot(gs[1, 0])
    ax_base.imshow(image_region/255)
    ax_base.set_ylabel('Y')
    ax_base.set_xlabel('X')

    # Now we repeat the masking/histogram creation/comparison from our blob detection code
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

    histogram_axes = []

    channel_distance: NDArray[float32] = numpy.zeros(3)
    for channel, colour in zip((0, 1, 2), ('Red', 'Green', 'Blue')):
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
        channel_distance[channel] = compareHist(
            hist_feature.astype(numpy.float32),
            hist_surroundings.astype(numpy.float32),
            method=HISTCMP_BHATTACHARYYA
        )

        ax_full = fig.add_subplot(gs[channel, 1])
        ax_full.imshow(image_channel, cmap=colour+'s_r', norm=None)
        ax_full.get_xaxis().set_visible(False)
        ax_full.get_yaxis().set_visible(False)

        ax_feat = fig.add_subplot(gs[channel, 2])
        ax_feat.get_xaxis().set_visible(False)
        ax_feat.get_yaxis().set_visible(False)
        ax_feat.imshow(
            image_channel, cmap=colour+'s_r', alpha=mask_feature.astype(float32),
            norm=None
        )

        ax_surr = fig.add_subplot(gs[channel, 3])
        ax_surr.get_xaxis().set_visible(False)
        ax_surr.get_yaxis().set_visible(False)
        ax_surr.imshow(
            image_channel, cmap=colour+'s_r', alpha=mask_surroundings.astype(float32),
            norm=None
        )

        ax_hist = fig.add_subplot(gs[channel, 4])
        ax_hist.yaxis.tick_right()
        ax_hist.set_box_aspect(1/2)

        ax_hist.stairs(
            hist_feature, hist_bins, label='Feature'
        )
        ax_hist.stairs(
            hist_surroundings, hist_bins, label='Surroundings'
        )
        ax_hist.plot(
            [], [], ' ', label=f"{colour} distance: {channel_distance[channel].round(3)}"
        )
        ax_hist.legend(loc='upper left', fontsize=8)

        histogram_axes.append(ax_hist)

    x_min = min([histogram_axis.get_xlim()[0] for histogram_axis in histogram_axes])
    x_max = max([histogram_axis.get_xlim()[1] for histogram_axis in histogram_axes])

    histogram_axes[0].set_xlim((x_min, x_max))
    histogram_axes[1].set_xlim((x_min, x_max))
    histogram_axes[2].set_xlim((x_min, x_max))

    histogram_axes[0].xaxis.tick_top()
    histogram_axes[1].xaxis.set_visible(False)
    histogram_axes[1].yaxis.set_label_position("right")
    histogram_axes[1].set_ylabel('Probability density')
    histogram_axes[2].set_xlabel('Inverse Value')

    fig.savefig(f'channel_distances_{channel_distance.max()}.png')
    plt.close(fig)
