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
from s5ndt.dropdown import build_dropdown
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


def make_snapshot(fig_data: dict, strip_title: bool = False):
    """Render a Plotly figure dict to a numpy image array via kaleido.

    Parameters
    ----------
    strip_title :
        Strip the Plotly title before snapshotting so it does not appear in
        the image (useful when matplotlib will add its own title).

    Returns
    -------
    numpy.ndarray
        RGBA image array suitable for ``ax.imshow()``.
    """
    plotly_fig = go.Figure(fig_data)
    if strip_title:
        plotly_fig.update_layout(title_text="", margin_t=20)
    img_bytes = plotly_fig.to_image(format="png")
    return plt.imread(io.BytesIO(img_bytes))


def snapshot_renderer(_fig_data: dict, title: str = ""):
    """Render a Plotly figure as a matplotlib snapshot.

    Converts the Plotly figure to a PNG image via kaleido and displays it
    on a plain matplotlib axes. Default renderer for :func:`mpl_export_button`.

    Parameters
    ----------
    _fig_data :
        Plotly figure dict (passed automatically by the export button).
    title :
        Axes title.

    Returns
    -------
    matplotlib.figure.Figure
    """
    img = make_snapshot(_fig_data)
    fig, ax = plt.subplots()
    ax.imshow(img)
    ax.axis("off")
    if title:
        ax.set_title(title)
    return fig


def mpl_export_button(
    graph_id: str,
    renderer: Callable = snapshot_renderer,
    label: str = "Export",
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
        Defaults to :func:`snapshot_renderer`.
    label :
        Label for the trigger button. Defaults to ``"Export"``.

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
    interval_id = f"_s5ndt_interval_{uid}"
    restore_id = f"_s5ndt_restore_{uid}"
    menu_id = f"_s5ndt_menu_{uid}"
    autogenerate_id = f"_s5ndt_autogen_{uid}"

    config = build_config(config_id, renderer)

    menu = build_dropdown(
        menu_id,
        trigger_label="···",
        close_inputs=[Input(restore_id, "n_clicks")],
        children=[
            html.Button("Reset to defaults", id=restore_id),
            dcc.Checklist(
                id=autogenerate_id,
                options=[{"label": " Auto-generate", "value": "auto"}],
                value=[],
                style={"padding": "4px 8px"},
            ),
        ],
    )

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
                style={"position": "relative", "width": "400px", "height": "300px"},
                children=[
                    dcc.Loading(
                        type="circle",
                        children=[html.Img(id=preview_id, style={"maxWidth": "400px"})],
                    ),
                ],
            ),
            dcc.Interval(
                id=interval_id,
                interval=500,
                n_intervals=0,
                max_intervals=1,
                disabled=True,
            ),
        ],
    )

    wizard = build_wizard(
        wizard_id, body, trigger_label=label, title="Export as matplotlib figure",
        header_actions=menu,
    )
    config.register_populate_callback(wizard.open_input)
    config.register_restore_callback(Input(restore_id, "n_clicks"))

    @dash.callback(
        Output(interval_id, "disabled"),
        Output(interval_id, "n_intervals"),
        wizard.open_input,
        prevent_initial_call=True,
    )
    def arm_interval(is_open):
        return (not is_open, 0)

    @dash.callback(
        Output(preview_id, "src"),
        Input(generate_id, "n_clicks"),
        Input(interval_id, "n_intervals"),
        State(graph_id, "figure"),
        *config.states,
        prevent_initial_call=True,
    )
    def generate_preview(n_clicks, n_intervals, _fig_data, *field_values):
        kwargs = config.build_kwargs(field_values)
        fig = renderer(_fig_data, **kwargs)
        return _fig_to_src(fig)

    _config_inputs = [
        Input(s.component_id, s.component_property) for s in config.states
    ]

    @dash.callback(
        Output(preview_id, "src", allow_duplicate=True),
        *_config_inputs,
        State(autogenerate_id, "value"),
        State(graph_id, "figure"),
        prevent_initial_call=True,
    )
    def autogenerate_preview(*args):
        *field_values, autogen, _fig_data = args
        if not autogen:
            return dash.no_update
        kwargs = config.build_kwargs(tuple(field_values))
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


def _get_nested(data: Any, path: str) -> Any:
    for key in path.split("."):
        if not isinstance(data, dict):
            return None
        data = data.get(key)
        if data is None:
            return None
    return data
