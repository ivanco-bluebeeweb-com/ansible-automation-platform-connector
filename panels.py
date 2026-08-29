"""Panel UI -- connections list/connect form + Job Templates list.

SIDEBAR CONTENT -- NO CARDS ANYWHERE, per ~/UI_INTERFACE_STANDARD.md's
"left sidebar, no decorated cards" rule (same convention as UiPath/Blue
Prism/MuleSoft Connector's panels.py).

Every section (connections, connect form, job templates) is a plain
ui.Stack, content stacked vertically and left-aligned, sections separated
by ui.Divider() -- no Card border/background/shadow anywhere in this slot.
Disconnect lives only in the "App settings" screen (panels_settings.py).
The one secondary "App settings" button is always the LAST element at the
bottom of the sidebar.

WHY A SHORT FORM (base URL + token + label), NOT A LONG OAUTH2 FORM LIKE
UiPath/Blue Prism/MuleSoft CONNECTOR.

Ansible Automation Platform / AWX auth is a single Personal Access Token
plus the Controller's own base API URL -- see ansible_client.py's module
docstring for the full reasoning (PAT model, AAP 2.5+/2.7 Platform Gateway
version/topology split forcing an explicit base URL field). The form
therefore asks for two required fields plus an optional label, with a help
panel (opened via ui.Call("__panel__ansible_connect_help")) explaining
where to find each one. No intro heading/description text lives in the
sidebar itself -- that walkthrough lives ONLY in the help panel's content,
per UI_INTERFACE_STANDARD.md's "no sidebar instructions duplicating the
modal" rule. Form container is stretched full-width per the same standard.

CENTER SLOT -- per ~/UI_INTERFACE_STANDARD.md, an app with no dedicated
center content needs a base (non-overlay) center panel with the canonical
"Nothing to show here" text, registered with center_overlay=True so the
session-init batch actually picks it up (lesson learned/recorded for
MuleSoft/Make.com/n8n/Power Automate/UiPath/Blue Prism Connector).
"""
from __future__ import annotations

from imperal_sdk import ui

import ansible_client as ac
from app import ext
import handlers_connection as h


def _settings_button() -> ui.UINode:
    """The one required secondary entry point into the settings screen --
    always the last element at the bottom of the sidebar."""
    return ui.Button(
        "App settings", variant="secondary", size="sm", full_width=True,
        icon="settings", on_click=ui.Call("__panel__ansible_settings"),
    )


def _connection_row(c: dict) -> ui.UINode:
    label = c.get("label") or c.get("api_base_url", "")
    return ui.Stack(direction="v", gap=1, children=[
        ui.Text(label, variant="body"),
        ui.Text(c.get("api_base_url", ""), variant="caption"),
    ])


def _connections_section(connections: list[dict]) -> ui.UINode:
    if not connections:
        return ui.Text("No Controller instances connected yet.", variant="caption")
    children: list[ui.UINode] = []
    for i, c in enumerate(connections):
        if i > 0:
            children.append(ui.Divider())
        children.append(_connection_row(c))
    return ui.Stack(direction="v", gap=2, children=children)


def _job_template_row(jt: dict) -> ui.UINode:
    """One Job Template row -- plain content, no Card wrapper, no
    padding/border, per Vlad's standing sidebar rule."""
    return ui.Stack(direction="v", gap=1, children=[
        ui.Text(jt.get("name", ""), variant="body"),
        ui.Text(jt.get("playbook", "") or jt.get("job_type", ""), variant="caption"),
    ])


def _job_templates_section(templates: list[dict]) -> ui.UINode:
    if not templates:
        return ui.Text("No job templates yet.", variant="caption")
    children: list[ui.UINode] = []
    for i, jt in enumerate(templates[:20]):
        if i > 0:
            children.append(ui.Divider())
        children.append(_job_template_row(jt))
    return ui.Stack(direction="v", gap=2, children=children)


def _connect_section() -> ui.UINode:
    """Plain content, no Card wrapper. Stretched full-width per
    UI_INTERFACE_STANDARD.md (2026-08-20). No intro heading/description
    text here -- the connect walkthrough lives ONLY in
    ansible_connect_help's panel (button below opens it); repeating it
    here would duplicate that instruction."""
    return ui.Stack(direction="v", gap=3, align="stretch", children=[
        ui.Button("How do I set this up?", variant="ghost", size="sm",
                  icon="HelpCircle",
                  on_click=ui.Call("__panel__ansible_connect_help")),
        ui.Form(
            action="connect_ansible",
            submit_label="Verify and connect",
            children=[
                ui.Stack(direction="v", gap=1, align="stretch", children=[
                    ui.Text("Controller API base URL", variant="caption"),
                    ui.Input(param_name="api_base_url",
                             placeholder="e.g. https://aap.example.com/api/controller/v2"),
                ]),
                ui.Stack(direction="v", gap=1, align="stretch", children=[
                    ui.Text("Personal Access Token", variant="caption"),
                    ui.Password(param_name="token",
                                 placeholder="Personal Access Token"),
                ]),
                ui.Stack(direction="v", gap=1, align="stretch", children=[
                    ui.Text("Label (optional)", variant="caption"),
                    ui.Input(param_name="label", placeholder="e.g. Production AAP"),
                ]),
            ],
        ),
    ])


@ext.panel("ansible_connect", slot="left", title="Ansible", icon="⚙️",
           default_width=320, min_width=260, max_width=420)
async def ansible_connect_panel(ctx, **kwargs) -> object:
    connections = await h._load_connections(ctx)
    connected = bool(connections)

    header = ui.Header(text="Ansible Automation Platform", level=2,
                        subtitle="Manage your Job Templates, jobs and workflows from Imperal")

    if not connected:
        return ui.Stack(direction="v", gap=4, align="stretch", children=[
            header,
            _connect_section(),
            ui.Divider(),
            _settings_button(),
        ])

    templates: list[dict] = []
    first = connections[0]
    try:
        rows = await ac.list_resource(ctx, first["api_base_url"], first["token"], "job_templates", params={"page_size": 20})
        templates = rows
    except ac.ClientFail:
        templates = []

    return ui.Stack(direction="v", gap=4, align="stretch", children=[
        header,
        ui.Text("Connected instances", variant="subtitle"),
        _connections_section(connections),
        ui.Divider(),
        _connect_section(),
        ui.Divider(),
        ui.Text(f"Job Templates -- {first.get('label') or first.get('api_base_url', '')}", variant="subtitle"),
        _job_templates_section(templates),
        ui.Divider(),
        ui.Button("View controller audit", variant="primary", size="sm", full_width=True,
                  icon="LayoutDashboard", on_click=ui.Call("__panel__ansible_center")),
        ui.Divider(),
        _settings_button(),
    ])


@ext.panel("ansible_connect_help", slot="center",
           title="How to connect Ansible Automation Platform", center_overlay=True)
async def ansible_connect_help(ctx, **kwargs) -> object:
    content = ui.Stack(direction="v", gap=3, children=[
        ui.Text("1. Log into your Automation Controller (or AWX) as a user/service account that will own the token."),
        ui.Text("2. Go to Access > Users > your user > Tokens, then Add -- or POST to /api/v2/tokens/ directly."),
        ui.Text("3. Copy the token value shown once -- Controller never shows it again."),
        ui.Text("4. Your API base URL depends on your platform version/topology: community AWX or Tower/AAP < 2.5 use https://<host>/api/v2 directly; AAP 2.5+ behind the unified Platform Gateway use https://<host>/api/controller/v2 instead."),
        ui.Divider(),
        ui.Alert(
            title="Controller/AWX resources only",
            message=(
                "This manages job templates, jobs, workflows, projects, "
                "inventories, credentials, schedules, organizations/teams/"
                "users, ad hoc commands and notification templates. "
                "Automation Content (Hub) and Automation Decisions (EDA) "
                "are separate AAP products and out of scope here."
            ),
            type="warning",
        ),
        ui.Divider(),
        ui.Link(
            label="Open the official Controller API token auth guide",
            href="https://docs.ansible.com/projects/awx/en/24.6.1/administration/oauth2_token_auth.html",
        ),
    ])
    return ui.Dialog(
        title="How to connect Ansible Automation Platform",
        content=content,
        confirm_label="",
        cancel_label="Close",
    )


@ext.panel("ansible_center", slot="center", title="Ansible", icon="⚙️", center_overlay=True)
async def ansible_center_panel(ctx, **kwargs) -> object:
    """Base center panel -- per UI_INTERFACE_STANDARD.md (2026-08-20).
    This app has no list/detail content of its own to show in the center
    by default (everything lives in the sidebar). MUST carry
    center_overlay=True: per docs.imperal.io/en/concepts/panels, a plain
    slot="center" panel is registered but the Panel app never fetches it
    at session-init without that flag. Text is the shared canonical
    wording -- must stay identical across every app in this situation."""
    connections = await h._load_connections(ctx)
    if not connections:
        return ui.Empty(message="Connect an Automation Controller from the sidebar to see it here.", icon="⚙️")

    import handlers_audit as ha
    from schemas import AuditControllerParams
    conn_id = connections[0].get("id", "")
    body: list[ui.UINode] = [ui.Text("Controller audit", variant="subtitle")]
    audit_result = await ha.audit_controller(ctx, AuditControllerParams(connection_id=conn_id))
    if audit_result.success and audit_result.data:
        r = audit_result.data
        body.append(ui.Stats(children=[
            ui.Stat(label="Running jobs", value=str(r.running_jobs)),
            ui.Stat(label="Failed (24h)", value=str(r.failed_jobs_24h)),
        ]))
        for row in r.rows[:15]:
            color = "red" if row.failure_rate_pct >= 25 else ("yellow" if row.failure_rate_pct > 0 else "green")
            body.append(ui.Stack(direction="h", gap=2, align="center", children=[
                ui.Badge(label=row.last_status or "UNKNOWN", color=color),
                ui.Text(row.job_template_name, variant="body"),
                ui.Text(f"failure rate: {row.failure_rate_pct:.0f}% · runs: {row.total_runs}", variant="caption"),
            ]))
    else:
        body.append(ui.Text("Could not load the controller audit.", variant="caption"))

    return ui.Stack(direction="v", gap=3, align="stretch", children=body)
