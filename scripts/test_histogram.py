import numpy
from numpy.ma import masked_where
import rawpy
from skimage.draw import disk
from skimage.exposure import histogram
from matplotlib import pyplot as plt
import cv2

i = rawpy.imread(
        "data/raw/A001/2021-08-19/A001_19_08_2021_002.NEF"
).postprocess(
    output_bps=16  # If we don't specify, it downscales to 8-bit colour depth!
).astype(numpy.float32) * 255 / 65535

# Normal mole: 1330, 2533
# Hair: 2572, 1549

xmin = 1000
xmax = 2000
ymin = 2000
ymax = 3000

xcen = 2572
ycen = 1549

centres = [
    (2572, 1549, 10, 'hair1'),
    (1355, 589, 12, 'hair2'),
    (1330, 2533, 12, 'mole1'),
    (3122, 4745, 10, 'mole2_near_hair'),
    (1800, 856, 12, 'mole3_pale'),
    (2577, 544, 28, 'mole4_large_hair')
]

print("Setting up arrays")
i_red = i[:, :, 0]
i_green = i[:, :, 1]
i_blue = i[:, :, 2]

for xcen, ycen, radius, name in centres:
    print(name)

    fig, ax = plt.subplots(5, 3, figsize=(12, 10))
    for j in range(3):
        ax[0, j].axis('off')
        ax[2, j].axis('off')
        ax[4, j].axis('off')

    window_size = radius * 2 + 15
    window = numpy.s_[
        ycen-window_size:ycen+window_size,
        xcen-window_size:xcen+window_size
    ]

    mask_coords_inner = disk((ycen, xcen), radius)
    mask_coords_outer = disk((ycen, xcen), radius * 2 + 5)

    mask_feature = numpy.zeros_like(i_red, dtype=bool)
    mask_environment = numpy.zeros_like(i_red, dtype=bool)

    mask_feature[mask_coords_inner] = True
    mask_environment[mask_coords_outer] = True
    mask_environment[mask_coords_inner] = False

    mask_feature = mask_feature[window]
    mask_environment = mask_environment[window]

    red = i_red[window]
    green = i_green[window]
    blue = i_blue[window]

    alpha_environment = numpy.zeros_like(red, dtype=numpy.float32)
    alpha_environment[mask_environment] = 1.0

    alpha_feature = numpy.zeros_like(red, dtype=numpy.float32)
    alpha_feature[mask_feature] = 1.0

    ax[0, 0].imshow(red, cmap='gray', alpha=alpha_environment)
    ax[0, 1].imshow(green, cmap='gray', alpha=alpha_environment)
    ax[0, 2].imshow(blue, cmap='gray', alpha=alpha_environment)

    hist_env_red, hist_bins = histogram(red[mask_environment].flatten(), nbins=32, normalize=True)
    hist_env_green, _ = histogram(green[mask_environment].flatten(), nbins=32, normalize=True)
    hist_env_blue, _ = histogram(blue[mask_environment].flatten(), nbins=32, normalize=True)

    ax[1, 0].plot(hist_bins, hist_env_red, color='r')
    ax[1, 1].plot(hist_bins, hist_env_green, color='g')
    ax[1, 2].plot(hist_bins, hist_env_blue, color='b')

    ax[2, 0].imshow(red, cmap='gray')
    ax[2, 1].imshow(green, cmap='gray')
    ax[2, 2].imshow(blue, cmap='gray')

    hist_feat_red, _ = histogram(red[mask_feature].flatten(), nbins=32, normalize=True)
    hist_feat_green, _ = histogram(green[mask_feature].flatten(), nbins=32, normalize=True)
    hist_feat_blue, _ = histogram(blue[mask_feature].flatten(), nbins=32, normalize=True)

    ax[3, 0].plot(hist_bins, hist_feat_red, color='r')
    ax[3, 1].plot(hist_bins, hist_feat_green, color='g')
    ax[3, 2].plot(hist_bins, hist_feat_blue, color='b')

    ax[4, 0].imshow(red, cmap='gray', alpha=alpha_feature)
    ax[4, 1].imshow(green, cmap='gray', alpha=alpha_feature)
    ax[4, 2].imshow(blue, cmap='gray', alpha=alpha_feature)

    diff_red_correl = cv2.compareHist(
        hist_env_red.astype(numpy.float32), hist_feat_red.astype(numpy.float32),
        method=cv2.HISTCMP_CORREL
    )
    diff_green_correl = cv2.compareHist(
        hist_env_green.astype(numpy.float32), hist_feat_green.astype(numpy.float32),
        method=cv2.HISTCMP_CORREL
    )
    diff_blue_correl = cv2.compareHist(
        hist_env_blue.astype(numpy.float32), hist_feat_green.astype(numpy.float32),
        method=cv2.HISTCMP_CORREL
    )

    diff_red_bhat = cv2.compareHist(
        hist_env_red.astype(numpy.float32), hist_feat_red.astype(numpy.float32),
        method=cv2.HISTCMP_BHATTACHARYYA
    )
    diff_green_bhat = cv2.compareHist(
        hist_env_green.astype(numpy.float32), hist_feat_green.astype(numpy.float32),
        method=cv2.HISTCMP_BHATTACHARYYA
    )
    diff_blue_bhat = cv2.compareHist(
        hist_env_blue.astype(numpy.float32), hist_feat_green.astype(numpy.float32),
        method=cv2.HISTCMP_BHATTACHARYYA
    )

    ax[0, 0].text(0, 0, f"Correlation: {diff_red_correl}")
    ax[0, 1].text(0, 0, f"Correlation: {diff_green_correl}")
    ax[0, 2].text(0, 0, f"Correlation: {diff_blue_correl}")

    ax[0, 0].text(0, 12, f"Bhattacharyva: {diff_red_bhat}")
    ax[0, 1].text(0, 12, f"Bhattacharyva: {diff_green_bhat}")
    ax[0, 2].text(0, 12, f"Bhattacharyva: {diff_blue_bhat}")

    plt.tight_layout()
    plt.savefig(f'hist_comparison_{name}.png')
