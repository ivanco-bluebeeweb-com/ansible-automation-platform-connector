"""Chat functions for Projects (SCM-backed playbook sources) and
Inventories/Hosts/Groups/Inventory Sources (target host management)."""
from __future__ import annotations

from imperal_sdk import ActionResult

import ansible_client as ac
from app import ext, chat
from handlers_connection import resolve_connection
from schemas import (
    Project, ProjectList, ListProjectsParams, GetProjectParams,
    CreateProjectParams, UpdateProjectParams, DeleteProjectParams, SyncProjectParams,
    Inventory, InventoryList, ListInventoriesParams, GetInventoryParams,
    CreateInventoryParams, UpdateInventoryParams, DeleteInventoryParams,
    Host, HostList, ListHostsParams, CreateHostParams, UpdateHostParams, DeleteHostParams,
    Group, GroupList, ListGroupsParams, CreateGroupParams, DeleteGroupParams,
    InventorySource, InventorySourceList, ListInventorySourcesParams, SyncInventorySourceParams,
    DeleteResult,
)


def _to_project(d: dict) -> Project:
    return Project(id=d.get("id", 0), name=d.get("name", ""), description=d.get("description", ""), scm_type=d.get("scm_type", ""), scm_url=d.get("scm_url", ""), status=d.get("status", ""))


def _to_inventory(d: dict) -> Inventory:
    return Inventory(id=d.get("id", 0), name=d.get("name", ""), description=d.get("description", ""), organization=d.get("organization"), total_hosts=d.get("total_hosts", 0))


@chat.function(
    "list_projects",
    "List Projects (SCM-backed sources of playbooks -- git/hg/svn repos or manual) configured in the connected Controller.",
    action_type="read", chain_callable=True, data_model=ProjectList,
    event="ansible-automation-platform-connector.list_projects",
)
async def list_projects(ctx, params: ListProjectsParams) -> ActionResult:
    """List projects."""
    r = await resolve_connection(ctx, params.connection_id)
    if isinstance(r, ActionResult):
        return r
    conn, token = r
    try:
        rows = await ac.list_resource(ctx, conn["api_base_url"], token, "projects", params={"page_size": params.limit})
    except ac.ClientFail as e:
        return ActionResult.error(e.payload["error"], code=e.payload["error_code"])
    items = [_to_project(d) for d in rows]
    return ActionResult.success(ProjectList(title="Projects", items=items, count=len(items)), summary="Projects listed.")


@chat.function(
    "get_project",
    "Read one Project in full -- its SCM type/URL and current sync status.",
    action_type="read", chain_callable=True, data_model=Project,
    event="ansible-automation-platform-connector.get_project",
)
async def get_project(ctx, params: GetProjectParams) -> ActionResult:
    """Get one project."""
    r = await resolve_connection(ctx, params.connection_id)
    if isinstance(r, ActionResult):
        return r
    conn, token = r
    try:
        d = await ac.get_resource(ctx, conn["api_base_url"], token, "projects", params.resource_id)
    except ac.ClientFail as e:
        return ActionResult.error(e.payload["error"], code=e.payload["error_code"])
    return ActionResult.success(_to_project(d), summary="Project retrieved.")


@chat.function(
    "create_project",
    "Create a new Project (SCM-backed or manual source of playbooks).",
    action_type="write", chain_callable=True, data_model=Project,
    event="ansible-automation-platform-connector.create_project",
    effects=["ansible.project.created"],
)
async def create_project(ctx, params: CreateProjectParams) -> ActionResult:
    """Create a project."""
    r = await resolve_connection(ctx, params.connection_id)
    if isinstance(r, ActionResult):
        return r
    conn, token = r
    payload = {"name": params.name, "scm_type": params.scm_type, "description": params.description}
    if params.scm_url:
        payload["scm_url"] = params.scm_url
    if params.scm_branch:
        payload["scm_branch"] = params.scm_branch
    if params.organization:
        payload["organization"] = params.organization
    try:
        d = await ac.create_resource(ctx, conn["api_base_url"], token, "projects", payload)
    except ac.ClientFail as e:
        return ActionResult.error(e.payload["error"], code=e.payload["error_code"])
    return ActionResult.success(_to_project(d), message="Project created.", summary="Project created.")


@chat.function(
    "update_project",
    "Update selected fields of an existing Project. Only given fields change.",
    action_type="write", chain_callable=True, data_model=Project,
    event="ansible-automation-platform-connector.update_project",
    effects=["ansible.project.updated"],
)
async def update_project(ctx, params: UpdateProjectParams) -> ActionResult:
    """Update a project."""
    r = await resolve_connection(ctx, params.connection_id)
    if isinstance(r, ActionResult):
        return r
    conn, token = r
    payload = {}
    if params.name:
        payload["name"] = params.name
    if params.scm_url:
        payload["scm_url"] = params.scm_url
    if params.scm_branch:
        payload["scm_branch"] = params.scm_branch
    try:
        d = await ac.update_resource(ctx, conn["api_base_url"], token, "projects", params.resource_id, payload)
    except ac.ClientFail as e:
        return ActionResult.error(e.payload["error"], code=e.payload["error_code"])
    return ActionResult.success(_to_project(d), message="Project updated.", summary="Project updated.")


@chat.function(
    "delete_project",
    "Permanently delete a Project. Cannot be undone.",
    action_type="write", chain_callable=True, data_model=DeleteResult,
    event="ansible-automation-platform-connector.delete_project",
    effects=["ansible.project.deleted"],
)
async def delete_project(ctx, params: DeleteProjectParams) -> ActionResult:
    """Delete a project."""
    r = await resolve_connection(ctx, params.connection_id)
    if isinstance(r, ActionResult):
        return r
    conn, token = r
    try:
        await ac.delete_resource(ctx, conn["api_base_url"], token, "projects", params.resource_id)
    except ac.ClientFail as e:
        return ActionResult.error(e.payload["error"], code=e.payload["error_code"])
    return ActionResult.success(DeleteResult(ok=True, detail="Project deleted."), summary="Project deleted.")


@chat.function(
    "sync_project",
    "Trigger a Project SCM sync (git pull, etc.) right now, refreshing its playbook files from source control.",
    action_type="write", chain_callable=True, data_model=DeleteResult,
    event="ansible-automation-platform-connector.sync_project",
    effects=["ansible.project.synced"],
)
async def sync_project(ctx, params: SyncProjectParams) -> ActionResult:
    """Sync a project from SCM."""
    r = await resolve_connection(ctx, params.connection_id)
    if isinstance(r, ActionResult):
        return r
    conn, token = r
    try:
        await ac.post_action(ctx, conn["api_base_url"], token, "projects", params.resource_id, "update")
    except ac.ClientFail as e:
        return ActionResult.error(e.payload["error"], code=e.payload["error_code"])
    return ActionResult.success(DeleteResult(ok=True, detail="Project sync started."), summary="Project sync requested.")


@chat.function(
    "list_inventories",
    "List Inventories (collections of target hosts/groups) configured in the connected Controller.",
    action_type="read", chain_callable=True, data_model=InventoryList,
    event="ansible-automation-platform-connector.list_inventories",
)
async def list_inventories(ctx, params: ListInventoriesParams) -> ActionResult:
    """List inventories."""
    r = await resolve_connection(ctx, params.connection_id)
    if isinstance(r, ActionResult):
        return r
    conn, token = r
    try:
        rows = await ac.list_resource(ctx, conn["api_base_url"], token, "inventories", params={"page_size": params.limit})
    except ac.ClientFail as e:
        return ActionResult.error(e.payload["error"], code=e.payload["error_code"])
    items = [_to_inventory(d) for d in rows]
    return ActionResult.success(InventoryList(title="Inventories", items=items, count=len(items)), summary="Inventories listed.")


@chat.function(
    "get_inventory",
    "Read one Inventory in full, including its total host count.",
    action_type="read", chain_callable=True, data_model=Inventory,
    event="ansible-automation-platform-connector.get_inventory",
)
async def get_inventory(ctx, params: GetInventoryParams) -> ActionResult:
    """Get one inventory."""
    r = await resolve_connection(ctx, params.connection_id)
    if isinstance(r, ActionResult):
        return r
    conn, token = r
    try:
        d = await ac.get_resource(ctx, conn["api_base_url"], token, "inventories", params.resource_id)
    except ac.ClientFail as e:
        return ActionResult.error(e.payload["error"], code=e.payload["error_code"])
    return ActionResult.success(_to_inventory(d), summary="Inventory retrieved.")


@chat.function(
    "create_inventory",
    "Create a new Inventory (a named collection of target hosts/groups).",
    action_type="write", chain_callable=True, data_model=Inventory,
    event="ansible-automation-platform-connector.create_inventory",
    effects=["ansible.inventory.created"],
)
async def create_inventory(ctx, params: CreateInventoryParams) -> ActionResult:
    """Create an inventory."""
    r = await resolve_connection(ctx, params.connection_id)
    if isinstance(r, ActionResult):
        return r
    conn, token = r
    payload = {"name": params.name, "description": params.description}
    if params.organization:
        payload["organization"] = params.organization
    try:
        d = await ac.create_resource(ctx, conn["api_base_url"], token, "inventories", payload)
    except ac.ClientFail as e:
        return ActionResult.error(e.payload["error"], code=e.payload["error_code"])
    return ActionResult.success(_to_inventory(d), message="Inventory created.", summary="Inventory created.")


@chat.function(
    "update_inventory",
    "Update selected fields of an existing Inventory. Only given fields change.",
    action_type="write", chain_callable=True, data_model=Inventory,
    event="ansible-automation-platform-connector.update_inventory",
    effects=["ansible.inventory.updated"],
)
async def update_inventory(ctx, params: UpdateInventoryParams) -> ActionResult:
    """Update an inventory."""
    r = await resolve_connection(ctx, params.connection_id)
    if isinstance(r, ActionResult):
        return r
    conn, token = r
    payload = {}
    if params.name:
        payload["name"] = params.name
    if params.description:
        payload["description"] = params.description
    try:
        d = await ac.update_resource(ctx, conn["api_base_url"], token, "inventories", params.resource_id, payload)
    except ac.ClientFail as e:
        return ActionResult.error(e.payload["error"], code=e.payload["error_code"])
    return ActionResult.success(_to_inventory(d), message="Inventory updated.", summary="Inventory updated.")


@chat.function(
    "delete_inventory",
    "Permanently delete an Inventory. Cannot be undone.",
    action_type="write", chain_callable=True, data_model=DeleteResult,
    event="ansible-automation-platform-connector.delete_inventory",
    effects=["ansible.inventory.deleted"],
)
async def delete_inventory(ctx, params: DeleteInventoryParams) -> ActionResult:
    """Delete an inventory."""
    r = await resolve_connection(ctx, params.connection_id)
    if isinstance(r, ActionResult):
        return r
    conn, token = r
    try:
        await ac.delete_resource(ctx, conn["api_base_url"], token, "inventories", params.resource_id)
    except ac.ClientFail as e:
        return ActionResult.error(e.payload["error"], code=e.payload["error_code"])
    return ActionResult.success(DeleteResult(ok=True, detail="Inventory deleted."), summary="Inventory deleted.")


@chat.function(
    "list_hosts",
    "List Hosts (target machines) inside one Inventory.",
    action_type="read", chain_callable=True, data_model=HostList,
    event="ansible-automation-platform-connector.list_hosts",
)
async def list_hosts(ctx, params: ListHostsParams) -> ActionResult:
    """List hosts in an inventory."""
    r = await resolve_connection(ctx, params.connection_id)
    if isinstance(r, ActionResult):
        return r
    conn, token = r
    try:
        rows = await ac.get_sub_resource(ctx, conn["api_base_url"], token, "inventories", params.resource_id, "hosts", params={"page_size": params.limit})
    except ac.ClientFail as e:
        return ActionResult.error(e.payload["error"], code=e.payload["error_code"])
    items = [Host(id=d.get("id", 0), name=d.get("name", ""), description=d.get("description", ""), enabled=d.get("enabled", True), inventory=d.get("inventory")) for d in rows]
    return ActionResult.success(HostList(title="Hosts", items=items, count=len(items)), summary="Hosts listed.")


@chat.function(
    "create_host",
    "Add a new Host to an Inventory.",
    action_type="write", chain_callable=True, data_model=Host,
    event="ansible-automation-platform-connector.create_host",
    effects=["ansible.host.created"],
)
async def create_host(ctx, params: CreateHostParams) -> ActionResult:
    """Create a host in an inventory."""
    r = await resolve_connection(ctx, params.connection_id)
    if isinstance(r, ActionResult):
        return r
    conn, token = r
    payload = {"name": params.name, "description": params.description}
    if params.variables:
        payload["variables"] = params.variables
    try:
        d = await ac.post_action(ctx, conn["api_base_url"], token, "inventories", params.resource_id, "hosts", payload)
    except ac.ClientFail as e:
        return ActionResult.error(e.payload["error"], code=e.payload["error_code"])
    return ActionResult.success(Host(id=d.get("id", 0), name=d.get("name", ""), description=d.get("description", ""), enabled=d.get("enabled", True), inventory=d.get("inventory")), message="Host created.", summary="Host created.")


@chat.function(
    "update_host",
    "Update selected fields of an existing Host (name, variables, enabled state). Only given fields change.",
    action_type="write", chain_callable=True, data_model=Host,
    event="ansible-automation-platform-connector.update_host",
    effects=["ansible.host.updated"],
)
async def update_host(ctx, params: UpdateHostParams) -> ActionResult:
    """Update a host."""
    r = await resolve_connection(ctx, params.connection_id)
    if isinstance(r, ActionResult):
        return r
    conn, token = r
    payload: dict = {"enabled": params.enabled}
    if params.name:
        payload["name"] = params.name
    if params.variables:
        payload["variables"] = params.variables
    try:
        d = await ac.update_resource(ctx, conn["api_base_url"], token, "hosts", params.host_id, payload)
    except ac.ClientFail as e:
        return ActionResult.error(e.payload["error"], code=e.payload["error_code"])
    return ActionResult.success(Host(id=d.get("id", 0), name=d.get("name", ""), description=d.get("description", ""), enabled=d.get("enabled", True), inventory=d.get("inventory")), message="Host updated.", summary="Host updated.")


@chat.function(
    "delete_host",
    "Permanently remove a Host from its inventory. Cannot be undone.",
    action_type="write", chain_callable=True, data_model=DeleteResult,
    event="ansible-automation-platform-connector.delete_host",
    effects=["ansible.host.deleted"],
)
async def delete_host(ctx, params: DeleteHostParams) -> ActionResult:
    """Delete a host."""
    r = await resolve_connection(ctx, params.connection_id)
    if isinstance(r, ActionResult):
        return r
    conn, token = r
    try:
        await ac.delete_resource(ctx, conn["api_base_url"], token, "hosts", params.host_id)
    except ac.ClientFail as e:
        return ActionResult.error(e.payload["error"], code=e.payload["error_code"])
    return ActionResult.success(DeleteResult(ok=True, detail="Host deleted."), summary="Host deleted.")


@chat.function(
    "list_groups",
    "List Groups (named subsets of hosts) inside one Inventory.",
    action_type="read", chain_callable=True, data_model=GroupList,
    event="ansible-automation-platform-connector.list_groups",
)
async def list_groups(ctx, params: ListGroupsParams) -> ActionResult:
    """List groups in an inventory."""
    r = await resolve_connection(ctx, params.connection_id)
    if isinstance(r, ActionResult):
        return r
    conn, token = r
    try:
        rows = await ac.get_sub_resource(ctx, conn["api_base_url"], token, "inventories", params.resource_id, "groups")
    except ac.ClientFail as e:
        return ActionResult.error(e.payload["error"], code=e.payload["error_code"])
    items = [Group(id=d.get("id", 0), name=d.get("name", ""), description=d.get("description", ""), inventory=d.get("inventory")) for d in rows]
    return ActionResult.success(GroupList(title="Groups", items=items), summary="Groups listed.")


@chat.function(
    "create_group",
    "Add a new Group to an Inventory.",
    action_type="write", chain_callable=True, data_model=Group,
    event="ansible-automation-platform-connector.create_group",
    effects=["ansible.group.created"],
)
async def create_group(ctx, params: CreateGroupParams) -> ActionResult:
    """Create a group in an inventory."""
    r = await resolve_connection(ctx, params.connection_id)
    if isinstance(r, ActionResult):
        return r
    conn, token = r
    payload = {"name": params.name}
    if params.variables:
        payload["variables"] = params.variables
    try:
        d = await ac.post_action(ctx, conn["api_base_url"], token, "inventories", params.resource_id, "groups", payload)
    except ac.ClientFail as e:
        return ActionResult.error(e.payload["error"], code=e.payload["error_code"])
    return ActionResult.success(Group(id=d.get("id", 0), name=d.get("name", ""), description=d.get("description", ""), inventory=d.get("inventory")), message="Group created.", summary="Group created.")


@chat.function(
    "delete_group",
    "Permanently remove a Group. Cannot be undone.",
    action_type="write", chain_callable=True, data_model=DeleteResult,
    event="ansible-automation-platform-connector.delete_group",
    effects=["ansible.group.deleted"],
)
async def delete_group(ctx, params: DeleteGroupParams) -> ActionResult:
    """Delete a group."""
    r = await resolve_connection(ctx, params.connection_id)
    if isinstance(r, ActionResult):
        return r
    conn, token = r
    try:
        await ac.delete_resource(ctx, conn["api_base_url"], token, "groups", params.group_id)
    except ac.ClientFail as e:
        return ActionResult.error(e.payload["error"], code=e.payload["error_code"])
    return ActionResult.success(DeleteResult(ok=True, detail="Group deleted."), summary="Group deleted.")


@chat.function(
    "list_inventory_sources",
    "List Inventory Sources (dynamic host-sourcing configs, e.g. cloud provider sync) configured on one Inventory.",
    action_type="read", chain_callable=True, data_model=InventorySourceList,
    event="ansible-automation-platform-connector.list_inventory_sources",
)
async def list_inventory_sources(ctx, params: ListInventorySourcesParams) -> ActionResult:
    """List inventory sources."""
    r = await resolve_connection(ctx, params.connection_id)
    if isinstance(r, ActionResult):
        return r
    conn, token = r
    try:
        rows = await ac.get_sub_resource(ctx, conn["api_base_url"], token, "inventories", params.resource_id, "inventory_sources")
    except ac.ClientFail as e:
        return ActionResult.error(e.payload["error"], code=e.payload["error_code"])
    items = [InventorySource(id=d.get("id", 0), name=d.get("name", ""), source=d.get("source", ""), status=d.get("status", "")) for d in rows]
    return ActionResult.success(InventorySourceList(title="Inventory Sources", items=items), summary="Inventory sources listed.")


@chat.function(
    "sync_inventory_source",
    "Trigger a sync (update) of an Inventory Source right now, pulling fresh hosts from its dynamic provider.",
    action_type="write", chain_callable=True, data_model=DeleteResult,
    event="ansible-automation-platform-connector.sync_inventory_source",
    effects=["ansible.inventory_source.synced"],
)
async def sync_inventory_source(ctx, params: SyncInventorySourceParams) -> ActionResult:
    """Sync an inventory source."""
    r = await resolve_connection(ctx, params.connection_id)
    if isinstance(r, ActionResult):
        return r
    conn, token = r
    try:
        await ac.post_action(ctx, conn["api_base_url"], token, "inventory_sources", params.source_id, "update")
    except ac.ClientFail as e:
        return ActionResult.error(e.payload["error"], code=e.payload["error_code"])
    return ActionResult.success(DeleteResult(ok=True, detail="Inventory source sync started."), summary="Inventory source sync requested.")
