import copy
import io
from datetime import date, datetime
from typing import Literal

import matplotlib.pyplot as plt
import plotly.graph_objects as go
from dash import Dash, dcc, html

from s5ndt.mpl_export import FromPlotly, mpl_export_button

app = Dash(__name__)

# --- figure ---

graph = dcc.Graph(id="main-graph", figure=go.Figure(
    go.Scatter(x=[1, 2, 3, 4, 5], y=[4, 2, 5, 1, 3], mode="markers"),
    layout={"title": {"text": "All-types example"}, "xaxis": {"title": {"text": "X axis"}}},
))


# --- renderer 1: full custom renderer, all field types ---

def full_renderer(
    _fig_data,
    title: str = FromPlotly("layout.title.text", graph),
    xlabel: str = FromPlotly("layout.xaxis.title.text", graph),
    dpi: int = 100,
    alpha: float = 0.8,
    show_grid: bool = True,
    report_date: date | None = None,
    as_of: datetime | None = None,
    marker_style: Literal["o", "s", "^", "x"] = "o",
    y_ticks: list[float] | None = None,
    xlim: tuple[float, float] | None = None,
):
    x = _fig_data["data"][0]["x"]
    y = _fig_data["data"][0]["y"]

    fig, ax = plt.subplots(dpi=dpi)
    ax.scatter(x, y, alpha=alpha, marker=marker_style)
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.grid(show_grid)

    if xlim:
        ax.set_xlim(*xlim)
    if y_ticks:
        ax.set_yticks(y_ticks)
    if report_date:
        fig.text(0, 0, str(report_date), fontsize=7)
    if as_of:
        ax.set_xlabel(f"as of {as_of.strftime('%Y-%m-%d %H:%M')}")

    return fig


# --- renderer 2: snapshot — strips plotly title before snapshotting,
#     pre-fills title/suptitle from the live figure so nothing is lost ---

def snapshot_renderer(
    _fig_data,
    title: str = FromPlotly("layout.title.text", graph),
    suptitle: str = "",
):
    plotly_fig = go.Figure(copy.deepcopy(_fig_data))
    plotly_fig.update_layout(title_text="", margin_t=20)
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


# --- layout ---

app.layout = html.Div([
    graph,
    html.Div([
        mpl_export_button(graph_id="main-graph", renderer=full_renderer),
        mpl_export_button(graph_id="main-graph", renderer=snapshot_renderer),
    ], style={"display": "flex", "gap": "8px"}),
])

if __name__ == "__main__":
    app.run(debug=True)
