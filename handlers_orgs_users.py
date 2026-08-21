"""Chat functions for Organizations, Teams, and Users -- the access/tenancy
layer Controller resources belong to."""
from __future__ import annotations

from imperal_sdk import ActionResult

import ansible_client as ac
from app import ext, chat
from handlers_connection import resolve_connection
from schemas import (
    Organization, OrganizationList, ListOrganizationsParams, CreateOrganizationParams,
    Team, TeamList, ListTeamsParams, CreateTeamParams,
    AAPUser, AAPUserList, ListUsersParams, CreateUserParams, DeleteUserParams,
    DeleteResult,
)


@chat.function(
    "list_organizations",
    "List Organizations (top-level tenancy grouping) defined in the connected Controller.",
    action_type="read", chain_callable=True, data_model=OrganizationList,
    event="ansible-automation-platform-connector.list_organizations",
)
async def list_organizations(ctx, params: ListOrganizationsParams) -> ActionResult:
    """List organizations."""
    r = await resolve_connection(ctx, params.connection_id)
    if isinstance(r, ActionResult):
        return r
    conn, token = r
    try:
        rows = await ac.list_resource(ctx, conn["api_base_url"], token, "organizations", params={"page_size": params.limit})
    except ac.ClientFail as e:
        return ActionResult.error(e.payload["error"], code=e.payload["error_code"])
    items = [Organization(id=d.get("id", 0), name=d.get("name", ""), description=d.get("description", "")) for d in rows]
    return ActionResult.ok(OrganizationList(title="Organizations", items=items))


@chat.function(
    "create_organization",
    "Create a new Organization.",
    action_type="write", chain_callable=True, data_model=Organization,
    event="ansible-automation-platform-connector.create_organization",
    effects=["ansible.organization.created"],
)
async def create_organization(ctx, params: CreateOrganizationParams) -> ActionResult:
    """Create an organization."""
    r = await resolve_connection(ctx, params.connection_id)
    if isinstance(r, ActionResult):
        return r
    conn, token = r
    try:
        d = await ac.create_resource(ctx, conn["api_base_url"], token, "organizations", {"name": params.name, "description": params.description})
    except ac.ClientFail as e:
        return ActionResult.error(e.payload["error"], code=e.payload["error_code"])
    return ActionResult.ok(Organization(id=d.get("id", 0), name=d.get("name", ""), description=d.get("description", "")), message="Organization created.")


@chat.function(
    "list_teams",
    "List Teams (groups of users sharing role-based access) defined in the connected Controller.",
    action_type="read", chain_callable=True, data_model=TeamList,
    event="ansible-automation-platform-connector.list_teams",
)
async def list_teams(ctx, params: ListTeamsParams) -> ActionResult:
    """List teams."""
    r = await resolve_connection(ctx, params.connection_id)
    if isinstance(r, ActionResult):
        return r
    conn, token = r
    try:
        rows = await ac.list_resource(ctx, conn["api_base_url"], token, "teams", params={"page_size": params.limit})
    except ac.ClientFail as e:
        return ActionResult.error(e.payload["error"], code=e.payload["error_code"])
    items = [Team(id=d.get("id", 0), name=d.get("name", ""), organization=d.get("organization")) for d in rows]
    return ActionResult.ok(TeamList(title="Teams", items=items))


@chat.function(
    "create_team",
    "Create a new Team inside an Organization.",
    action_type="write", chain_callable=True, data_model=Team,
    event="ansible-automation-platform-connector.create_team",
    effects=["ansible.team.created"],
)
async def create_team(ctx, params: CreateTeamParams) -> ActionResult:
    """Create a team."""
    r = await resolve_connection(ctx, params.connection_id)
    if isinstance(r, ActionResult):
        return r
    conn, token = r
    try:
        d = await ac.create_resource(ctx, conn["api_base_url"], token, "teams", {"name": params.name, "organization": params.organization})
    except ac.ClientFail as e:
        return ActionResult.error(e.payload["error"], code=e.payload["error_code"])
    return ActionResult.ok(Team(id=d.get("id", 0), name=d.get("name", ""), organization=d.get("organization")), message="Team created.")


@chat.function(
    "list_users",
    "List Users registered in the connected Controller.",
    action_type="read", chain_callable=True, data_model=AAPUserList,
    event="ansible-automation-platform-connector.list_users",
)
async def list_users(ctx, params: ListUsersParams) -> ActionResult:
    """List users."""
    r = await resolve_connection(ctx, params.connection_id)
    if isinstance(r, ActionResult):
        return r
    conn, token = r
    try:
        rows = await ac.list_resource(ctx, conn["api_base_url"], token, "users", params={"page_size": params.limit})
    except ac.ClientFail as e:
        return ActionResult.error(e.payload["error"], code=e.payload["error_code"])
    items = [AAPUser(id=d.get("id", 0), username=d.get("username", ""), email=d.get("email", ""), is_superuser=bool(d.get("is_superuser", False))) for d in rows]
    return ActionResult.ok(AAPUserList(title="Users", items=items))


@chat.function(
    "create_user",
    "Create a new User in the connected Controller.",
    action_type="write", chain_callable=True, data_model=AAPUser,
    event="ansible-automation-platform-connector.create_user",
    effects=["ansible.user.created"],
)
async def create_user(ctx, params: CreateUserParams) -> ActionResult:
    """Create a user."""
    r = await resolve_connection(ctx, params.connection_id)
    if isinstance(r, ActionResult):
        return r
    conn, token = r
    payload = {"username": params.username, "password": params.password}
    if params.email:
        payload["email"] = params.email
    if params.first_name:
        payload["first_name"] = params.first_name
    if params.last_name:
        payload["last_name"] = params.last_name
    try:
        d = await ac.create_resource(ctx, conn["api_base_url"], token, "users", payload)
    except ac.ClientFail as e:
        return ActionResult.error(e.payload["error"], code=e.payload["error_code"])
    return ActionResult.ok(AAPUser(id=d.get("id", 0), username=d.get("username", ""), email=d.get("email", ""), is_superuser=bool(d.get("is_superuser", False))), message="User created.")


@chat.function(
    "delete_user",
    "Permanently delete a User from the connected Controller. Cannot be undone.",
    action_type="write", chain_callable=True, data_model=DeleteResult,
    event="ansible-automation-platform-connector.delete_user",
    effects=["ansible.user.deleted"],
)
async def delete_user(ctx, params: DeleteUserParams) -> ActionResult:
    """Delete a user."""
    r = await resolve_connection(ctx, params.connection_id)
    if isinstance(r, ActionResult):
        return r
    conn, token = r
    try:
        await ac.delete_resource(ctx, conn["api_base_url"], token, "users", params.resource_id)
    except ac.ClientFail as e:
        return ActionResult.error(e.payload["error"], code=e.payload["error_code"])
    return ActionResult.ok(DeleteResult(ok=True, detail="User deleted."))


@chat.function(
    "list_users",
    "List Users registered in the connected Controller.",
    action_type="read", chain_callable=True, data_model=AAPUserList,
    event="ansible-automation-platform-connector.list_users",
)
async def list_users(ctx, params: ListUsersParams) -> ActionResult:
    """List users."""
    r = await resolve_connection(ctx, params.connection_id)
    if isinstance(r, ActionResult):
        return r
    conn, token = r
    try:
        rows = await ac.list_resource(ctx, conn["api_base_url"], token, "users", params={"page_size": params.limit})
    except ac.ClientFail as e:
        return ActionResult.error(e.payload["error"], code=e.payload["error_code"])
    items = [AAPUser(id=d.get("id", 0), username=d.get("username", ""), email=d.get("email", ""), is_superuser=bool(d.get("is_superuser", False))) for d in rows]
    return ActionResult.ok(AAPUserList(title="Users", items=items))


@chat.function(
    "create_user",
    "Create a new User on the connected Controller.",
    action_type="write", chain_callable=True, data_model=AAPUser,
    event="ansible-automation-platform-connector.create_user",
    effects=["ansible.user.created"],
)
async def create_user(ctx, params: CreateUserParams) -> ActionResult:
    """Create a user."""
    r = await resolve_connection(ctx, params.connection_id)
    if isinstance(r, ActionResult):
        return r
    conn, token = r
    payload = {"username": params.username, "password": params.password, "email": params.email, "first_name": params.first_name, "last_name": params.last_name}
    try:
        d = await ac.create_resource(ctx, conn["api_base_url"], token, "users", payload)
    except ac.ClientFail as e:
        return ActionResult.error(e.payload["error"], code=e.payload["error_code"])
    return ActionResult.ok(AAPUser(id=d.get("id", 0), username=d.get("username", ""), email=d.get("email", ""), is_superuser=bool(d.get("is_superuser", False))), message="User created.")


@chat.function(
    "delete_user",
    "Permanently delete a User from the connected Controller. Cannot be undone.",
    action_type="write", chain_callable=True, data_model=DeleteResult,
    event="ansible-automation-platform-connector.delete_user",
    effects=["ansible.user.deleted"],
)
async def delete_user(ctx, params: DeleteUserParams) -> ActionResult:
    """Delete a user."""
    r = await resolve_connection(ctx, params.connection_id)
    if isinstance(r, ActionResult):
        return r
    conn, token = r
    try:
        await ac.delete_resource(ctx, conn["api_base_url"], token, "users", params.resource_id)
    except ac.ClientFail as e:
        return ActionResult.error(e.payload["error"], code=e.payload["error_code"])
    return ActionResult.ok(DeleteResult(ok=True, detail="User deleted."))
