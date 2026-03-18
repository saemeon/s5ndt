# Copyright (c) Simon Niederberger.
# Distributed under the terms of the MIT License.

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import dash
from dash import Input, Output, dcc, html


@dataclass
class Wizard:
    """Return value of :func:`build_wizard`.

    Attributes
    ----------
    div :
        Self-contained component; place anywhere in the layout.
    open_input :
        ``Input(store_id, "data")`` — pass to
        :meth:`Config.register_populate_callback` to populate hooked fields
        when the wizard opens.
    """

    div: html.Div
    open_input: Input


def build_wizard(
    wizard_id: str,
    body: Any,
    trigger_label: str = "Open",
    title: str = "",
    header_actions: Any = None,
) -> Wizard:
    """Wrap *body* in a modal wizard popup.

    Parameters
    ----------
    wizard_id :
        Unique namespace for component IDs.
    body :
        Any Dash component rendered inside the dialog, below the header.
    trigger_label :
        Label for the button that opens the wizard.
    title :
        Text shown in the dialog header.
    header_actions :
        Optional component(s) rendered in the header row between the title
        and the ✕ close button.

    Returns
    -------
    Wizard
        ``.div`` — place anywhere in the layout.
        ``.open_input`` — pass to :meth:`Config.register_populate_callback`
        so hooked fields are populated when the wizard opens.
    """
    trigger_id = f"_s5ndt_wiz_trigger_{wizard_id}"
    close_id = f"_s5ndt_wiz_close_{wizard_id}"
    store_id = f"_s5ndt_wiz_store_{wizard_id}"
    modal_id = f"_s5ndt_wiz_modal_{wizard_id}"
    open_input = Input(store_id, "data")

    modal = html.Div(
        id=modal_id,
        style={"display": "none"},
        children=[
            # overlay (decorative, does not capture clicks)
            html.Div(
                style={
                    "position": "fixed",
                    "inset": "0",
                    "background": "rgba(0,0,0,0.4)",
                    "zIndex": 1000,
                    "pointerEvents": "none",
                }
            ),
            # dialog
            html.Div(
                style={
                    "position": "fixed",
                    "top": "50%",
                    "left": "50%",
                    "transform": "translate(-50%, -50%)",
                    "background": "white",
                    "padding": "24px",
                    "zIndex": 1001,
                    "display": "flex",
                    "flexDirection": "column",
                    "gap": "16px",
                    "minWidth": "600px",
                },
                children=[
                    html.Div(
                        style={"display": "flex", "justifyContent": "space-between", "alignItems": "center"},
                        children=[
                            html.Strong(title),
                            html.Div(
                                style={"display": "flex", "gap": "4px", "alignItems": "center"},
                                children=[
                                    *([header_actions] if header_actions is not None else []),
                                    html.Button("✕", id=close_id),
                                ],
                            ),
                        ],
                    ),
                    body,
                ],
            ),
        ],
    )

    store = dcc.Store(id=store_id, data=False)

    @dash.callback(
        Output(store_id, "data"),
        Input(trigger_id, "n_clicks"),
        Input(close_id, "n_clicks"),
        prevent_initial_call=True,
    )
    def toggle_store(open_clicks, close_clicks):
        return dash.ctx.triggered_id == trigger_id

    @dash.callback(
        Output(modal_id, "style"),
        open_input,
    )
    def update_visibility(is_open):
        return {"display": "block"} if is_open else {"display": "none"}

    return Wizard(div=html.Div([html.Button(trigger_label, id=trigger_id), store, modal]), open_input=open_input)
