"""Chat functions for connection management: connect/disconnect/list saved
Ansible Automation Platform (Controller/AWX) instances. Built on
ansible_client.py / schemas.py, same shape as UiPath/Blue Prism
Connector's handlers.py connection section.
"""
from __future__ import annotations

import json
import uuid

from imperal_sdk import ActionResult

import ansible_client as ac
from app import ext, chat
from schemas import (
    NoParams,
    ConnectAnsibleParams, ProviderConnection, ProviderConnectionList,
    DisconnectAnsibleParams, DeleteResult,
)

_SECRET_NAME = "ansible_connections"


async def _load_connections(ctx) -> list[dict]:
    raw = await ctx.secrets.get(_SECRET_NAME)
    try:
        return json.loads(raw) if raw else []
    except Exception:
        return []


async def _save_connections(ctx, connections: list[dict]) -> None:
    await ctx.secrets.set(_SECRET_NAME, json.dumps(connections))


def _to_provider_connection(c: dict) -> ProviderConnection:
    return ProviderConnection(
        id=c.get("id", ""),
        title=c.get("label") or c.get("api_base_url", "Controller instance"),
        detail=c.get("api_base_url", ""),
    )


async def resolve_connection(ctx, connection_id: str = ""):
    """Resolve a connection_id (or the first saved connection) to
    (conn_dict, token). Returns an ActionResult.error(...) instead if none
    match -- callers must check `isinstance(result, ActionResult)`."""
    connections = await _load_connections(ctx)
    if not connections:
        return ActionResult.error(
            "No Ansible Automation Platform / AWX instance connected yet. Use connect_ansible first.",
            code="AAP_NOT_CONNECTED",
        )
    conn = None
    if connection_id:
        conn = next((c for c in connections if c.get("id") == connection_id), None)
        if conn is None:
            return ActionResult.error(f"No connection found with id {connection_id}.", code="AAP_CONNECTION_NOT_FOUND")
    else:
        conn = connections[0]
    return conn, conn.get("token", "")


@chat.function(
    "connect_ansible",
    "Connect your own Ansible Automation Platform (Automation Controller) "
    "or open-source AWX instance by saving its full API base URL and a "
    "Personal Access Token, after checking they actually work.",
    action_type="write",
    chain_callable=True,
    data_model=ProviderConnection,
    event="ansible-automation-platform-connector.connect_ansible",
    effects=["ansible.provider.connected"],
)
async def connect_ansible(ctx, params: ConnectAnsibleParams) -> ActionResult:
    """Connect a Controller/AWX instance."""
    check = await ac.check_connection(ctx, params.api_base_url, params.token)
    if not check.get("ok"):
        return ActionResult.error(check.get("error", "Failed to connect to Ansible Automation Platform."), code=check.get("error_code", "AAP_ERROR"))
    connections = await _load_connections(ctx)
    conn_id = str(uuid.uuid4())
    entry = {
        "id": conn_id,
        "api_base_url": params.api_base_url.rstrip("/"),
        "token": params.token,
        "label": params.label,
    }
    connections.append(entry)
    await _save_connections(ctx, connections)
    return ActionResult.success(_to_provider_connection(entry), message="Ansible Automation Platform instance connected.", summary="Ansible connected.")


@chat.function(
    "list_connections",
    "List the connected Ansible Automation Platform / AWX instances.",
    action_type="read",
    chain_callable=True,
    data_model=ProviderConnectionList,
    event="ansible-automation-platform-connector.list_connections",
)
async def list_connections(ctx, params: NoParams) -> ActionResult:
    """List connected instances."""
    connections = await _load_connections(ctx)
    items = [_to_provider_connection(c) for c in connections]
    return ActionResult.success(ProviderConnectionList(title="Connected Ansible Automation Platform instances", items=items), summary="Connections listed.")


@chat.function(
    "disconnect_ansible",
    "Disconnect one Ansible Automation Platform / AWX instance. Nothing "
    "in Controller itself is changed; only the saved token here is deleted.",
    action_type="write",
    chain_callable=True,
    data_model=DeleteResult,
    event="ansible-automation-platform-connector.disconnect_ansible",
    effects=["ansible.provider.disconnected"],
)
async def disconnect_ansible(ctx, params: DisconnectAnsibleParams) -> ActionResult:
    """Disconnect a connection by id."""
    connections = await _load_connections(ctx)
    remaining = [c for c in connections if c.get("id") != params.connection_id]
    if len(remaining) == len(connections):
        return ActionResult.error(f"No connection found with id {params.connection_id}.", code="AAP_CONNECTION_NOT_FOUND")
    await _save_connections(ctx, remaining)
    return ActionResult.success(DeleteResult(ok=True, detail="Disconnected."), message="Disconnected.", summary="Ansible disconnected.")
