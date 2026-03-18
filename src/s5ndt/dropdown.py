# Copyright (c) Simon Niederberger.
# Distributed under the terms of the MIT License.

from __future__ import annotations

from typing import Any

import dash
from dash import Input, Output, State, html


def build_dropdown(
    dropdown_id: str,
    children: Any,
    trigger_label: str = "···",
    close_inputs: list[Input] | None = None,
) -> html.Div:
    """A generic toggle dropdown anchored to a trigger button.

    Parameters
    ----------
    dropdown_id :
        Unique namespace for component IDs.
    children :
        Content rendered inside the dropdown panel.
    trigger_label :
        Label for the trigger button. Defaults to ``"···"``.
    close_inputs :
        Additional :class:`dash.Input` objects that close the dropdown
        (e.g. a reset button click).

    Returns
    -------
    html.Div
        Self-contained component; place it anywhere in the layout.
    """
    trigger_id = f"_s5ndt_dd_trigger_{dropdown_id}"
    panel_id = f"_s5ndt_dd_panel_{dropdown_id}"
    overlay_id = f"_s5ndt_dd_overlay_{dropdown_id}"

    _panel_hidden = {
        "display": "none",
        "position": "absolute",
        "right": "0",
        "background": "white",
        "border": "1px solid #ccc",
        "zIndex": 100,
        "whiteSpace": "nowrap",
    }
    _panel_visible = {**_panel_hidden, "display": "block"}
    _overlay_hidden = {
        "display": "none",
        "position": "fixed",
        "inset": "0",
        "zIndex": 99,
    }
    _overlay_visible = {**_overlay_hidden, "display": "block"}

    extra_close = close_inputs or []

    @dash.callback(
        Output(panel_id, "style"),
        Output(overlay_id, "style"),
        Input(trigger_id, "n_clicks"),
        Input(overlay_id, "n_clicks"),
        *extra_close,
        State(panel_id, "style"),
        prevent_initial_call=True,
    )
    def _toggle(*args):
        current_style = args[-1]
        if dash.ctx.triggered_id == trigger_id:
            already_open = current_style and current_style.get("display") == "block"
            if already_open:
                return _panel_hidden, _overlay_hidden
            return _panel_visible, _overlay_visible
        return _panel_hidden, _overlay_hidden

    return html.Div(
        style={"position": "relative", "display": "inline-block"},
        children=[
            html.Button(trigger_label, id=trigger_id),
            html.Div(
                id=overlay_id,
                n_clicks=0,
                style=_overlay_hidden,
            ),
            html.Div(
                id=panel_id,
                style=_panel_hidden,
                children=children,
            ),
        ],
    )
