"""Ansible Automation Platform (Automation Controller / AWX) HTTP client --
Bearer-token auth against a user's own Controller instance, thin wrappers
around the Controller REST API v2 (job_templates/jobs/projects/inventories/
credentials/schedules/workflow_job_templates/organizations/teams/users/
notification_templates/instances/instance_groups/ad_hoc_commands).

WHY BEARER PERSONAL ACCESS TOKEN, NOT OAUTH2 CLIENT CREDENTIALS.

Automation Controller/AWX supports both session auth and token auth. For a
headless server-to-server integration like this connector, the documented
path is a Personal Access Token (PAT) minted once by a user/service account
in Controller's own UI or via `POST /api/v2/tokens/` and then sent as
`Authorization: Bearer <token>` on every call (docs.ansible.com/projects/
awx/en/24.6.1/administration/oauth2_token_auth.html, confirmed during
Discovery 2026-08-21). This mirrors n8n/Make.com Connector's simple
long-lived API key shape rather than UiPath/Blue Prism/MuleSoft's
client_id+client_secret OAuth2 dance -- Controller's PAT model is simpler
and does not require registering a separate OAuth2 Application first.

WHY THE USER SUPPLIES THE FULL BASE URL INCLUDING THE API VERSION SEGMENT.

AAP 2.5+ introduced a unified Platform Gateway; AAP 2.7 removed direct
component API access entirely -- Controller then lives under
`https://<gateway>/api/controller/v2/...`. Community AWX and older
Tower/AAP (<2.5) instead use `https://<host>/api/v2/...` directly. This
version/topology split is confirmed in CONNECTOR_DISCOVERY.md and cannot be
safely guessed by the connector -- the user pastes their own full base URL
(e.g. `https://awx.example.com/api/v2` or
`https://aap.example.com/api/controller/v2`) at connect time, same
principle as MuleSoft's/Blue Prism's explicit base-URL fields.

WHY 401 vs 403 ARE HANDLED DIFFERENTLY, SAME PRINCIPLE AS UiPath/Blue
Prism/Automation Anywhere/MuleSoft CONNECTOR's clients.

A 401 means the token is missing/invalid/expired -- Controller rejected
the credential itself. A 403 means the token is valid but the token's
owning user lacks the RBAC permission (Controller's own Organization/Team/
role-based access control) for this specific object (e.g. no "Execute"
permission on a Job Template, or no access to an Organization) -- a
materially different, more specific and more fixable cause (the fix is an
RBAC grant in Controller, not re-entering credentials) that must not be
reported as "wrong credentials".
"""
from __future__ import annotations

import json as _json

TOKEN_MISSING = "AAP_TOKEN_MISSING"
TOKEN_REJECTED = "AAP_TOKEN_REJECTED"
PERMISSION_DENIED = "AAP_PERMISSION_DENIED"
NOT_FOUND = "AAP_NOT_FOUND"
VALIDATION_FAILED = "AAP_VALIDATION_FAILED"
RESPONSE_UNEXPECTED = "AAP_RESPONSE_UNEXPECTED"
UNREACHABLE = "AAP_UNREACHABLE"
RATE_LIMITED = "AAP_RATE_LIMITED"
BACKEND_5XX = "AAP_BACKEND_5XX"
BACKEND_TIMEOUT = "AAP_BACKEND_TIMEOUT"

_MESSAGES = {
    TOKEN_MISSING: "No Ansible Automation Platform / AWX instance is connected yet.",
    TOKEN_REJECTED: "Controller rejected this token. Check the Personal Access Token and base URL, then reconnect.",
    PERMISSION_DENIED: "Controller accepted the token, but this account lacks the RBAC permission for this operation. Grant the required role/permission on the Organization, Team, or object in Controller.",
    NOT_FOUND: "Controller has no such job template/job/project/inventory/credential, or this account cannot access it.",
    VALIDATION_FAILED: "Controller rejected the request as invalid.",
    RESPONSE_UNEXPECTED: "Controller returned a response the connector could not safely interpret.",
    UNREACHABLE: "Could not reach the Ansible Automation Platform / AWX instance.",
    RATE_LIMITED: "Controller is rate-limiting requests; try again shortly.",
    BACKEND_5XX: "Controller returned a server error; try again shortly.",
    BACKEND_TIMEOUT: "Controller took too long to respond; try again shortly.",
}
_RETRYABLE = {RATE_LIMITED, BACKEND_5XX, BACKEND_TIMEOUT}


def fail(code: str, detail: str = "") -> dict:
    message = _MESSAGES.get(code, code)
    if detail:
        message = f"{message} ({detail})"
    return {"ok": False, "error_code": code, "error": message, "retryable": code in _RETRYABLE}


class ClientFail(Exception):
    def __init__(self, payload: dict):
        super().__init__(payload.get("error", "Ansible Automation Platform request failed"))
        self.payload = payload


def _base(api_base_url: str) -> str:
    return api_base_url.rstrip("/")


def _headers(token: str) -> dict:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }


def _check_status(resp, action: str) -> dict | list:
    if resp.status_code in (200, 201, 202, 204):
        if resp.status_code == 204:
            return {}
        return resp.body if isinstance(resp.body, (dict, list)) else {}
    if resp.status_code == 401:
        raise ClientFail(fail(TOKEN_REJECTED, action))
    if resp.status_code == 403:
        raise ClientFail(fail(PERMISSION_DENIED, action))
    if resp.status_code == 404:
        raise ClientFail(fail(NOT_FOUND, action))
    if resp.status_code == 429:
        raise ClientFail(fail(RATE_LIMITED, action))
    if resp.status_code >= 500:
        raise ClientFail(fail(BACKEND_5XX, action))
    if resp.status_code == 400:
        raise ClientFail(fail(VALIDATION_FAILED, action))
    raise ClientFail(fail(RESPONSE_UNEXPECTED, f"{action}: HTTP {resp.status_code}"))


def _items(body) -> list[dict]:
    if isinstance(body, dict):
        return body.get("results", []) or []
    return body or []


async def check_connection(ctx, api_base_url: str, token: str) -> dict:
    """Cheap GET /me/ to prove the token is accepted and the base URL is
    reachable and correctly formed."""
    resp = await ctx.http.get(f"{_base(api_base_url)}/me/", headers=_headers(token))
    try:
        _check_status(resp, "verify connection")
    except ClientFail as e:
        return e.payload
    return {"ok": True}


# ──────────────────────────────────────────────────────────────────────────
# Generic list/get/post/patch/delete helpers against Controller's uniform
# REST resource shape (every resource: list w/ pagination, retrieve, create,
# update, delete -- same shape across job_templates/projects/inventories/
# credentials/organizations/teams/users/schedules/etc.)
# ──────────────────────────────────────────────────────────────────────────


async def list_resource(ctx, api_base_url: str, token: str, path: str, *, params: dict | None = None) -> list[dict]:
    resp = await ctx.http.get(f"{_base(api_base_url)}/{path}/", headers=_headers(token), params=params or {})
    body = _check_status(resp, f"list {path}")
    return _items(body)


async def get_resource(ctx, api_base_url: str, token: str, path: str, resource_id) -> dict:
    resp = await ctx.http.get(f"{_base(api_base_url)}/{path}/{resource_id}/", headers=_headers(token))
    return _check_status(resp, f"get {path}")


async def create_resource(ctx, api_base_url: str, token: str, path: str, payload: dict) -> dict:
    resp = await ctx.http.post(f"{_base(api_base_url)}/{path}/", headers=_headers(token), json=payload)
    return _check_status(resp, f"create {path}")


async def update_resource(ctx, api_base_url: str, token: str, path: str, resource_id, payload: dict) -> dict:
    resp = await ctx.http.patch(f"{_base(api_base_url)}/{path}/{resource_id}/", headers=_headers(token), json=payload)
    return _check_status(resp, f"update {path}")


async def delete_resource(ctx, api_base_url: str, token: str, path: str, resource_id) -> None:
    resp = await ctx.http.delete(f"{_base(api_base_url)}/{path}/{resource_id}/", headers=_headers(token))
    _check_status(resp, f"delete {path}")


async def post_action(ctx, api_base_url: str, token: str, path: str, resource_id, action: str, payload: dict | None = None) -> dict:
    """POST to a sub-action endpoint, e.g. /job_templates/{id}/launch/,
    /jobs/{id}/cancel/, /jobs/{id}/relaunch/."""
    resp = await ctx.http.post(
        f"{_base(api_base_url)}/{path}/{resource_id}/{action}/",
        headers=_headers(token), json=payload or {},
    )
    return _check_status(resp, f"{action} {path}")


async def get_sub_resource(ctx, api_base_url: str, token: str, path: str, resource_id, sub: str, *, params: dict | None = None) -> list[dict]:
    """GET a related-resource list, e.g. /jobs/{id}/job_events/,
    /jobs/{id}/stdout/, /job_templates/{id}/survey_spec/."""
    resp = await ctx.http.get(
        f"{_base(api_base_url)}/{path}/{resource_id}/{sub}/",
        headers=_headers(token), params=params or {},
    )
    body = _check_status(resp, f"get {path} {sub}")
    if isinstance(body, dict) and "results" in body:
        return _items(body)
    return body if isinstance(body, list) else [body] if body else []


async def get_stdout(ctx, api_base_url: str, token: str, job_id, *, format_: str = "txt") -> str:
    resp = await ctx.http.get(
        f"{_base(api_base_url)}/jobs/{job_id}/stdout/",
        headers=_headers(token), params={"format": format_},
    )
    body = _check_status(resp, "get job stdout")
    if isinstance(body, dict):
        return body.get("content", "") or _json.dumps(body)
    return str(body) if body else ""
