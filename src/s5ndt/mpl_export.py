# Copyright (c) Simon Niederberger.
# Distributed under the terms of the MIT License.

from __future__ import annotations

import base64
import io
from typing import Any, Callable

import dash
import matplotlib.pyplot as plt
import plotly.graph_objects as go
from dash import Input, Output, State, dcc, html

from s5ndt._ids import id_generator
from s5ndt.config_builder import FromComponent, build_config
from s5ndt.wizard import build_wizard

plt.switch_backend("agg")


class FromPlotly(FromComponent):
    """Read a value from the Plotly figure as the field default.

    Parameters
    ----------
    path :
        Dot-separated path into the figure dict, e.g. ``"layout.title.text"``.
    graph :
        The ``dcc.Graph`` component whose figure to read.
    """

    def __init__(self, path: str, graph: dcc.Graph):
        super().__init__(graph, "figure")
        self.path = path

    def get_default(self, figure: dict) -> Any:
        return _get_nested(figure, self.path)


def _snapshot_renderer(_fig_data: dict, suptitle: str = "", title: str = ""):
    plotly_fig = go.Figure(_fig_data)
    img_bytes = plotly_fig.to_image(format="png")
    img = plt.imread(io.BytesIO(img_bytes))
    fig, ax = plt.subplots()
    ax.imshow(img)
    ax.axis("off")
    if title:
        ax.set_title(title)
    if suptitle:
        fig.suptitle(suptitle)
    return fig


def mpl_export_button(
    graph_id: str,
    renderer: Callable = _snapshot_renderer,
) -> html.Div:
    """Add a matplotlib export wizard button for a dcc.Graph.

    Parameters
    ----------
    graph_id :
        The ``id`` of the ``dcc.Graph`` component in the layout.
    renderer :
        Callable ``(_fig_data, **kwargs) -> matplotlib.figure.Figure``.
        Parameters after ``_fig_data`` are introspected to build the wizard fields.
        Parameters whose default is a :class:`FromPlotly` instance are populated
        from the live Plotly figure when the wizard opens.
        Defaults to :func:`_snapshot_renderer`.

    Returns
    -------
    html.Div
        A component containing the trigger button and the self-contained modal.
        Place it anywhere in the layout.
    """
    uid = id_generator(graph_id)
    config_id = f"_s5ndt_cfg_{uid}"
    wizard_id = f"_s5ndt_mpl_{uid}"
    preview_id = f"_s5ndt_preview_{uid}"
    generate_id = f"_s5ndt_generate_{uid}"
    download_id = f"_s5ndt_download_{uid}"

    config = build_config(config_id, renderer)

    body = html.Div(
        style={"display": "flex", "gap": "24px"},
        children=[
            html.Div(
                style={
                    "display": "flex",
                    "flexDirection": "column",
                    "gap": "8px",
                    "minWidth": "160px",
                },
                children=[
                    config.div,
                    html.Button("Generate", id=generate_id),
                    dcc.Download(id=download_id),
                    html.Button("Download PNG", id=f"{download_id}_btn"),
                ],
            ),
            html.Div(
                children=[html.Img(id=preview_id, style={"maxWidth": "400px"})],
            ),
        ],
    )

    wizard = build_wizard(
        wizard_id, body, trigger_label="Export", title="Export as matplotlib figure"
    )
    config.register_populate_callback(wizard.open_input)

    @dash.callback(
        Output(preview_id, "src"),
        Input(generate_id, "n_clicks"),
        State(graph_id, "figure"),
        *config.states,
        prevent_initial_call=True,
    )
    def generate_preview(n_clicks, _fig_data, *field_values):
        kwargs = config.build_kwargs(field_values)
        fig = renderer(_fig_data, **kwargs)
        return _fig_to_src(fig)

    @dash.callback(
        Output(download_id, "data"),
        Input(f"{download_id}_btn", "n_clicks"),
        State(graph_id, "figure"),
        *config.states,
        prevent_initial_call=True,
    )
    def download_figure(n_clicks, _fig_data, *field_values):
        kwargs = config.build_kwargs(field_values)
        fig = renderer(_fig_data, **kwargs)
        return dcc.send_bytes(_fig_to_bytes(fig), "figure.png")

    return wizard.div


def _fig_to_bytes(fig) -> bytes:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf.read()


def _fig_to_src(fig) -> str:
    encoded = base64.b64encode(_fig_to_bytes(fig)).decode("utf-8")
    return f"data:image/png;base64,{encoded}"


def _get_nested(data: dict, path: str) -> Any:
    for key in path.split("."):
        if not isinstance(data, dict):
            return None
        data = data.get(key)
        if data is None:
            return None
    return data
