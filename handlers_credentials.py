"""Chat functions for Credentials (secrets Controller uses to access
machines/SCM/cloud providers) and Credential Types (the field schema each
credential kind requires -- names/types only, never secret values)."""
from __future__ import annotations

import json

from imperal_sdk import ActionResult

import ansible_client as ac
from app import ext, chat
from handlers_connection import resolve_connection
from schemas import (
    Credential, CredentialList, ListCredentialsParams, GetCredentialParams,
    CreateCredentialParams, DeleteCredentialParams,
    CredentialType, CredentialTypeList, ListCredentialTypesParams,
    DeleteResult,
)


def _to_cred(d: dict) -> Credential:
    return Credential(id=d.get("id", 0), name=d.get("name", ""), description=d.get("description", ""), credential_type=d.get("credential_type"), kind=d.get("kind", ""))


@chat.function(
    "list_credentials",
    "List Credentials (secrets Controller uses to reach machines/SCM/cloud "
    "providers) configured in the connected Controller -- names/types only, "
    "never their secret field values (Controller's own API never returns those either).",
    action_type="read", chain_callable=True, data_model=CredentialList,
    event="ansible-automation-platform-connector.list_credentials",
)
async def list_credentials(ctx, params: ListCredentialsParams) -> ActionResult:
    """List credentials."""
    r = await resolve_connection(ctx, params.connection_id)
    if isinstance(r, ActionResult):
        return r
    conn, token = r
    try:
        rows = await ac.list_resource(ctx, conn["api_base_url"], token, "credentials", params={"page_size": params.limit})
    except ac.ClientFail as e:
        return ActionResult.error(e.payload["error"], code=e.payload["error_code"])
    items = [_to_cred(d) for d in rows]
    return ActionResult.ok(CredentialList(title="Credentials", items=items, count=len(items)))


@chat.function(
    "get_credential",
    "Read one Credential's metadata (name, type, kind) -- never its secret field values.",
    action_type="read", chain_callable=True, data_model=Credential,
    event="ansible-automation-platform-connector.get_credential",
)
async def get_credential(ctx, params: GetCredentialParams) -> ActionResult:
    """Get one credential."""
    r = await resolve_connection(ctx, params.connection_id)
    if isinstance(r, ActionResult):
        return r
    conn, token = r
    try:
        d = await ac.get_resource(ctx, conn["api_base_url"], token, "credentials", params.resource_id)
    except ac.ClientFail as e:
        return ActionResult.error(e.payload["error"], code=e.payload["error_code"])
    return ActionResult.ok(_to_cred(d))


@chat.function(
    "create_credential",
    "Create a new Credential (secret) of a given Credential Type. Field "
    "values are write-only -- Controller's own API never echoes them back either.",
    action_type="write", chain_callable=True, data_model=Credential,
    event="ansible-automation-platform-connector.create_credential",
    effects=["ansible.credential.created"],
)
async def create_credential(ctx, params: CreateCredentialParams) -> ActionResult:
    """Create a credential."""
    r = await resolve_connection(ctx, params.connection_id)
    if isinstance(r, ActionResult):
        return r
    conn, token = r
    try:
        inputs = json.loads(params.inputs_json) if params.inputs_json else {}
    except Exception:
        return ActionResult.error("inputs_json must be valid JSON.", code="AAP_VALIDATION_FAILED")
    payload = {"name": params.name, "credential_type": params.credential_type, "inputs": inputs}
    if params.organization:
        payload["organization"] = params.organization
    try:
        d = await ac.create_resource(ctx, conn["api_base_url"], token, "credentials", payload)
    except ac.ClientFail as e:
        return ActionResult.error(e.payload["error"], code=e.payload["error_code"])
    return ActionResult.ok(_to_cred(d), message="Credential created.")


@chat.function(
    "delete_credential",
    "Permanently delete a Credential. Cannot be undone -- anything using it will stop working.",
    action_type="write", chain_callable=True, data_model=DeleteResult,
    event="ansible-automation-platform-connector.delete_credential",
    effects=["ansible.credential.deleted"],
)
async def delete_credential(ctx, params: DeleteCredentialParams) -> ActionResult:
    """Delete a credential."""
    r = await resolve_connection(ctx, params.connection_id)
    if isinstance(r, ActionResult):
        return r
    conn, token = r
    try:
        await ac.delete_resource(ctx, conn["api_base_url"], token, "credentials", params.resource_id)
    except ac.ClientFail as e:
        return ActionResult.error(e.payload["error"], code=e.payload["error_code"])
    return ActionResult.ok(DeleteResult(ok=True, detail="Credential deleted."))


@chat.function(
    "list_credential_types",
    "List Credential Types (the field schema each credential kind requires, e.g. Machine, Source Control, Vault, cloud providers).",
    action_type="read", chain_callable=True, data_model=CredentialTypeList,
    event="ansible-automation-platform-connector.list_credential_types",
)
async def list_credential_types(ctx, params: ListCredentialTypesParams) -> ActionResult:
    """List credential types."""
    r = await resolve_connection(ctx, params.connection_id)
    if isinstance(r, ActionResult):
        return r
    conn, token = r
    try:
        rows = await ac.list_resource(ctx, conn["api_base_url"], token, "credential_types")
    except ac.ClientFail as e:
        return ActionResult.error(e.payload["error"], code=e.payload["error_code"])
    items = [CredentialType(id=d.get("id", 0), name=d.get("name", ""), kind=d.get("kind", "")) for d in rows]
    return ActionResult.ok(CredentialTypeList(title="Credential Types", items=items))
