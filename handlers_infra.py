"""Chat functions for the execution mesh: Instances (worker nodes),
Instance Groups (named pools), and Execution Environments (containers
job runs execute inside)."""
from __future__ import annotations

from imperal_sdk import ActionResult

import ansible_client as ac
from app import ext, chat
from handlers_connection import resolve_connection
from schemas import (
    Instance, InstanceList, ListInstancesParams,
    InstanceGroup, InstanceGroupList, ListInstanceGroupsParams,
    ExecutionEnvironment, ExecutionEnvironmentList, ListExecutionEnvironmentsParams,
)


@chat.function(
    "list_instances",
    "List Instances (worker nodes in the Controller's execution mesh) -- their hostname, node type, capacity, and enabled state.",
    action_type="read", chain_callable=True, data_model=InstanceList,
    event="ansible-automation-platform-connector.list_instances",
)
async def list_instances(ctx, params: ListInstancesParams) -> ActionResult:
    """List instances."""
    r = await resolve_connection(ctx, params.connection_id)
    if isinstance(r, ActionResult):
        return r
    conn, token = r
    try:
        rows = await ac.list_resource(ctx, conn["api_base_url"], token, "instances")
    except ac.ClientFail as e:
        return ActionResult.error(e.payload["error"], code=e.payload["error_code"])
    items = [Instance(id=d.get("id", 0), hostname=d.get("hostname", ""), node_type=d.get("node_type", ""), capacity=d.get("capacity", 0), enabled=bool(d.get("enabled", True))) for d in rows]
    return ActionResult.ok(InstanceList(title="Instances", items=items))


@chat.function(
    "list_instance_groups",
    "List Instance Groups (named pools of Instances a Job Template/Organization can be pinned to) in the connected Controller.",
    action_type="read", chain_callable=True, data_model=InstanceGroupList,
    event="ansible-automation-platform-connector.list_instance_groups",
)
async def list_instance_groups(ctx, params: ListInstanceGroupsParams) -> ActionResult:
    """List instance groups."""
    r = await resolve_connection(ctx, params.connection_id)
    if isinstance(r, ActionResult):
        return r
    conn, token = r
    try:
        rows = await ac.list_resource(ctx, conn["api_base_url"], token, "instance_groups")
    except ac.ClientFail as e:
        return ActionResult.error(e.payload["error"], code=e.payload["error_code"])
    items = [InstanceGroup(id=d.get("id", 0), name=d.get("name", ""), capacity=d.get("capacity", 0)) for d in rows]
    return ActionResult.ok(InstanceGroupList(title="Instance Groups", items=items))


@chat.function(
    "list_exec_environments",
    "List Execution Environments (the container images job runs execute inside) configured in the connected Controller.",
    action_type="read", chain_callable=True, data_model=ExecutionEnvironmentList,
    event="ansible-automation-platform-connector.list_exec_environments",
)
async def list_exec_environments(ctx, params: ListExecutionEnvironmentsParams) -> ActionResult:
    """List execution environments."""
    r = await resolve_connection(ctx, params.connection_id)
    if isinstance(r, ActionResult):
        return r
    conn, token = r
    try:
        rows = await ac.list_resource(ctx, conn["api_base_url"], token, "execution_environments")
    except ac.ClientFail as e:
        return ActionResult.error(e.payload["error"], code=e.payload["error_code"])
    items = [ExecutionEnvironment(id=d.get("id", 0), name=d.get("name", ""), image=d.get("image", "")) for d in rows]
    return ActionResult.ok(ExecutionEnvironmentList(title="Execution Environments", items=items))
