"""Chat functions for Schedules (recurring launches of a job/workflow
template on an RRULE cadence)."""
from __future__ import annotations

from imperal_sdk import ActionResult

import ansible_client as ac
from app import ext, chat
from handlers_connection import resolve_connection
from schemas import (
    Schedule, ScheduleList, ListSchedulesParams, CreateScheduleParams,
    SetScheduleEnabledParams, DeleteScheduleParams, DeleteResult,
)


def _to_sched(d: dict) -> Schedule:
    return Schedule(id=d.get("id", 0), name=d.get("name", ""), rrule=d.get("rrule", ""), enabled=bool(d.get("enabled", True)), unified_job_template=d.get("unified_job_template"))


@chat.function(
    "list_schedules",
    "List Schedules (recurring launches of a job/workflow template) configured in the connected Controller.",
    action_type="read", chain_callable=True, data_model=ScheduleList,
    event="ansible-automation-platform-connector.list_schedules",
)
async def list_schedules(ctx, params: ListSchedulesParams) -> ActionResult:
    """List schedules."""
    r = await resolve_connection(ctx, params.connection_id)
    if isinstance(r, ActionResult):
        return r
    conn, token = r
    try:
        rows = await ac.list_resource(ctx, conn["api_base_url"], token, "schedules", params={"page_size": params.limit})
    except ac.ClientFail as e:
        return ActionResult.error(e.payload["error"], code=e.payload["error_code"])
    items = [_to_sched(d) for d in rows]
    return ActionResult.success(ScheduleList(title="Schedules", items=items), summary="Schedules listed.")


@chat.function(
    "create_schedule",
    "Create a new Schedule on a Job Template or Workflow Job Template -- an iCal RRULE cadence Controller uses to launch it automatically.",
    action_type="write", chain_callable=True, data_model=Schedule,
    event="ansible-automation-platform-connector.create_schedule",
    effects=["ansible.schedule.created"],
)
async def create_schedule(ctx, params: CreateScheduleParams) -> ActionResult:
    """Create a schedule on a job template."""
    r = await resolve_connection(ctx, params.connection_id)
    if isinstance(r, ActionResult):
        return r
    conn, token = r
    payload = {"name": params.name, "rrule": params.rrule}
    try:
        d = await ac.post_action(ctx, conn["api_base_url"], token, "job_templates", params.resource_id, "schedules", payload)
    except ac.ClientFail as e:
        return ActionResult.error(e.payload["error"], code=e.payload["error_code"])
    return ActionResult.success(_to_sched(d), message="Schedule created.", summary="Schedule created.")


@chat.function(
    "set_schedule_enabled",
    "Enable or disable a Schedule without deleting it.",
    action_type="write", chain_callable=True, data_model=Schedule,
    event="ansible-automation-platform-connector.set_schedule_enabled",
    effects=["ansible.schedule.updated"],
)
async def set_schedule_enabled(ctx, params: SetScheduleEnabledParams) -> ActionResult:
    """Enable/disable a schedule."""
    r = await resolve_connection(ctx, params.connection_id)
    if isinstance(r, ActionResult):
        return r
    conn, token = r
    try:
        d = await ac.update_resource(ctx, conn["api_base_url"], token, "schedules", params.schedule_id, {"enabled": params.enabled})
    except ac.ClientFail as e:
        return ActionResult.error(e.payload["error"], code=e.payload["error_code"])
    return ActionResult.success(_to_sched(d), message="Schedule updated.", summary="Schedule enabled updated.")


@chat.function(
    "delete_schedule",
    "Permanently delete a Schedule. Cannot be undone.",
    action_type="write", chain_callable=True, data_model=DeleteResult,
    event="ansible-automation-platform-connector.delete_schedule",
    effects=["ansible.schedule.deleted"],
)
async def delete_schedule(ctx, params: DeleteScheduleParams) -> ActionResult:
    """Delete a schedule."""
    r = await resolve_connection(ctx, params.connection_id)
    if isinstance(r, ActionResult):
        return r
    conn, token = r
    try:
        await ac.delete_resource(ctx, conn["api_base_url"], token, "schedules", params.schedule_id)
    except ac.ClientFail as e:
        return ActionResult.error(e.payload["error"], code=e.payload["error_code"])
    return ActionResult.success(DeleteResult(ok=True, detail="Schedule deleted."), summary="Schedule deleted.")
