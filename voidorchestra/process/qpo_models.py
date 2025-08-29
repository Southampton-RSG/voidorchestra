from math import ceil
from pathlib import Path
from random import randrange
from typing import List, Tuple

import numpy as np
from astropy import units as u
from astropy.time import Time, TimeDelta
from astropy.timeseries import TimeSeries
from astropy.units import Quantity
from mind_the_gaps.simulator import Simulator
from numpy import floating
from numpy.typing import NDArray
from plotly.graph_objects import Figure, Scatter
from plotly.subplots import make_subplots
from stingray import Lightcurve, Powerspectrum, StingrayTimeseries

from voidorchestra import config_paths
from voidorchestra.db import QPOModel


def plot_power_spectrum(
    timeseries: TimeSeries,
    figure_title: str,
    figure_vlines: List[Tuple[TimeDelta, str]],
) -> Figure:
    """
    Given a simulated lightcurve, takes the power spectrum and plots it.

    Parameters
    ----------
    timeseries: TimeSeries
        The lightcurve table to plot.
    figure_title: str
        The title for the combined plot.
    figure_vlines: List[Tuple[TimeDelta, str]]
        A list of model component frequencies to add to the graph.

    Returns
    -------
    Figure:
        The plotted figure, with the simulated lightcurve and PSD derived for it.
    """
    timeseries["counts"] = timeseries["rate"]  # Stingray can't work with 'rate'
    stingray_lightcurve: Lightcurve = Lightcurve.from_astropy_timeseries(timeseries)
    power_spectrum: Powerspectrum = Powerspectrum(stingray_lightcurve, norm="frac")

    frequency = power_spectrum.freq
    power = power_spectrum.power
    timeseries["time"].format = "datetime"

    figure: Figure = make_subplots(rows=2, cols=1)

    figure.add_trace(
        Scatter(
            x=timeseries["time"].to_datetime(),
            y=timeseries["rate"].value,
            mode="lines",
        ),
        row=1,
        col=1,
    )
    figure.add_trace(
        Scatter(
            x=np.log10(frequency),
            y=np.log10(power),
            mode="lines",
        ),
        row=2,
        col=1,
    )
    figure.update_layout(
        dict(
            title=dict(
                text=figure_title,
                font_size=10,
            ),
            xaxis=dict(
                title="Time",
            ),
            yaxis=dict(
                title=f"Rate ({timeseries['rate'].unit})",
            ),
            xaxis2=dict(
                title=f"Log Frequency ({timeseries['rate'].unit})",
            ),
            yaxis2=dict(
                title="Power Spectrum",
            ),
            template="plotly_dark",
            showlegend=False,
        ),
    )
    for iter, figure_vline in enumerate(figure_vlines):
        x_vline: float = np.log10((1 / figure_vline[0].to(u.s)).value)
        figure.add_vline(
            x=x_vline,
            row=2,
            col=1,
            line_width=2,
        )
        figure.add_annotation(x=x_vline, y=randrange(-1, 1), row=2, col=1, text=figure_vline[1], showarrow=True, arrowhead=1)

    return figure


def write_psd_images(qpo_models: List[QPOModel], filenames: List[str]|None = None):
    """
    Simulates high-resolution spectra of the provided QPO models, and writes images of the PSDs.

    Intended to be used for verification purposes.

    Parameters
    ----------
    qpo_models: List[QPOModel]
        The models to write images of.
    filenames: List[str]|None
        If present, the filenames for the models to save to.

    Returns
    -------
    None
    """
    # Very high rate so the Poisson noise is very low, and the model components dominate.
    rate_mean: Quantity = 1.0e6 * u.s ** -1

    time_start: Time = Time.now()
    time_start.format = "unix"

    for idx, qpo_model in enumerate(qpo_models):
        print("Processing QPO model:", qpo_model)
        figure_title: str = ""
        figure_vlines: List[Tuple[TimeDelta, str]] = []

        # Start off setting a search window for the periods.
        period_longest: TimeDelta = TimeDelta(0, format="sec")
        period_shortest: TimeDelta = TimeDelta(3.0e38, format="sec")

        if len(qpo_model.qpo_model_children):
            qpo_model_details: List[QPOModel] = qpo_model.qpo_model_children
        else:
            qpo_model_details: List[QPOModel] = [qpo_model]

        for qpo_model_detail in qpo_model_details:
            period: TimeDelta = qpo_model_detail.get_period()
            period.format = "sec"
            figure_title += f"{qpo_model_detail.model_name} ({period.to(u.s):.2e}{period.format}, Δ={qpo_model_detail.variance_fraction:.2f}) "
            figure_vlines.append((period, qpo_model_detail.model_name))

            if period > period_longest:
                period_longest = period

            if period and period < period_shortest:
                period_shortest = period

        # Capture 100 of the longest period, at a resolution of 1/10th of a period
        period_longest *= 100.0
        period_shortest /= 10.0
        required_samples: int = ceil(period_longest / period_shortest)
        time_delta: TimeDelta = TimeDelta(period_shortest, format="sec")

        print(f"Generating timeseries with {required_samples} observations, spacing {time_delta}...")
        timeseries: TimeSeries = TimeSeries(
            time_start=time_start,
            time_delta=time_delta,
            n_samples=required_samples,
            data={
                "rate": np.ones(required_samples) * rate_mean,
            },
        )

        # Simulate this, for very short exposures at a very high rate to minimise noise
        print(f"Simulating observations at mean rate {rate_mean}...")
        simulator: Simulator = Simulator(
            qpo_model.get_model_for_mean_rate(rate_mean),
            times=timeseries["time"].value,
            exposures=1.0,
            mean=rate_mean.value,
            pdf="Gaussian",
            extension_factor=2.0,
            random_state=1,
        )
        rates_clean: NDArray[floating] = simulator.generate_lightcurve()
        timeseries["rate"] = rates_clean * rate_mean.unit

        # Generate and plot the figure
        print(f"Plotting PSDs for QPO model...")
        figure: Figure = plot_power_spectrum(timeseries, figure_title, figure_vlines)

        if not len(filenames):
            path: Path = config_paths["output"] / f"qpo_models/qpo_model-{qpo_model.id}.psd.png"
        else:
            path: Path = config_paths["output"] / f"qpo_models/{filenames[idx]}.png"

        print(f"Writing PSD figure to: {path}")
        figure.write_image(path)