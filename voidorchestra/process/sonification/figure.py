"""
Creates figures for the sonification plots.
"""
from logging import Logger

from astropy.timeseries import TimeSeries
from numpy import floating
from numpy.typing import NDArray
from plotly.graph_objs import Figure, Scatter
from plotly.graph_objs.layout import Template
from plotly.io import templates

from voidorchestra.log import get_logger

logger: Logger = get_logger(__name__.replace(".", "-"))


templates['zooniverse']: Template = Template(
    layout={
        'paper_bgcolor': '#333333',
        'plot_bgcolor': '#272727',
        'font': {
            'family': 'Karla, Arial, sans-serif',
            'color': 'rgb(226, 229, 233)',
            'size': 13,
        },
        'xaxis': {
            'showticklabels': False,
            'gridcolor': '#204d4f',
            'linecolor': '#0097d9',
            'title_font': {
                'weight': 400,
                'size': 18,
            },
        },
        'yaxis': {
            'showticklabels': False,
            'gridcolor': '#204d4f',
            'linecolor': '#0097d9',
            'title_font': {
                'weight': 400,
                'size': 18,
            },
        },
        'margin': {
            'l': 60,
            'r': 40,
            't': 40,
            'b': 50,
            # 'pad': 15,
        },
        'width': 800,
        'height': 450,
    }
)
templates.default = 'plotly_dark+zooniverse'


def plot_lightcurve(
        lightcurve: TimeSeries,
) -> Figure:
    """
    Given a lightcurve, plots it (with uncertainty regions).

    Parameters
    ----------
    lightcurve: TimeSeries
        The lightcurve table to plot.

    Returns
    -------
    Figure:
        The plotted figure.
    """
    time: NDArray[floating] = lightcurve["time"].jd
    figure: Figure = Figure(
        # data=[
        #     Scatter(
        #         x=time,
        #         y=lightcurve['rate'].to(u.s**-1),
        #         showlegend=False,
        #         line={
        #             'color': 'rgb(173, 221, 224)',
        #             'width': 2,
        #         }
        #     ),
        #     Scatter(
        #         x=time,
        #         y=(lightcurve["rate"]+lightcurve["error"]).to(u.s**-1),
        #         showlegend=False,
        #         line_width=0,
        #     ),
        #     Scatter(
        #         x=time,
        #         y=(lightcurve["rate"]-lightcurve["error"]).to(u.s**-1),
        #         showlegend=False,
        #         line_width=0, fill="tonexty", fillcolor="rgba(173,221,224,0.5)",
        #     )
        # ] if not observations_only else
        data=[
            Scatter(
                x=time,
                y=lightcurve["rate"],
                mode="markers",
            )
        ],
        layout={
            "xaxis_title": "TIME",
            "yaxis_title": "X-RAY EMISSION",
            # "xaxis_title": f"Time ({time_units})",
            # "yaxis_title": f"Count rate ({rate_units})"
        }
    )

    return figure
