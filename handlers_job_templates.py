"""Chat functions for Job Templates: list/get/create/update/delete/launch --
Automation Controller's core reusable "what to run" definitions (playbook +
inventory + project + credentials).
"""
from __future__ import annotations

from imperal_sdk import ActionResult

import ansible_client as ac
from app import ext, chat
from handlers_connection import resolve_connection
from schemas import (
    JobTemplate, JobTemplateList, ListJobTemplatesParams, GetJobTemplateParams,
    CreateJobTemplateParams, UpdateJobTemplateParams, DeleteJobTemplateParams,
    LaunchJobTemplateParams, JobLaunchResult, DeleteResult,
)


def _to_jt(d: dict) -> JobTemplate:
    return JobTemplate(
        id=d.get("id", 0),
        name=d.get("name", ""),
        description=d.get("description", ""),
        job_type=d.get("job_type", ""),
        inventory=d.get("inventory"),
        project=d.get("project"),
        playbook=d.get("playbook", ""),
        status=d.get("status", ""),
        last_job_run=str(d.get("last_job_run") or ""),
    )


@chat.function(
    "list_job_templates",
    "List Job Templates (reusable playbook + inventory + project run "
    "definitions) configured in the connected Controller.",
    action_type="read",
    chain_callable=True,
    data_model=JobTemplateList,
    event="ansible-automation-platform-connector.list_job_templates",
)
async def list_job_templates(ctx, params: ListJobTemplatesParams) -> ActionResult:
    """List job templates."""
    r = await resolve_connection(ctx, params.connection_id)
    if isinstance(r, ActionResult):
        return r
    conn, token = r
    try:
        rows = await ac.list_resource(ctx, conn["api_base_url"], token, "job_templates", params={"page_size": params.limit})
    except ac.ClientFail as e:
        return ActionResult.error(e.payload["error"], code=e.payload["error_code"])
    items = [_to_jt(d) for d in rows]
    return ActionResult.ok(JobTemplateList(items=items, count=len(items)))


@chat.function(
    "get_job_template",
    "Read one Job Template in full.",
    action_type="read",
    chain_callable=True,
    data_model=JobTemplate,
    event="ansible-automation-platform-connector.get_job_template",
)
async def get_job_template(ctx, params: GetJobTemplateParams) -> ActionResult:
    """Read one job template."""
    r = await resolve_connection(ctx, params.connection_id)
    if isinstance(r, ActionResult):
        return r
    conn, token = r
    try:
        d = await ac.get_resource(ctx, conn["api_base_url"], token, "job_templates", params.resource_id)
    except ac.ClientFail as e:
        return ActionResult.error(e.payload["error"], code=e.payload["error_code"])
    return ActionResult.ok(_to_jt(d))


@chat.function(
    "create_job_template",
    "Create a new Job Template: name, job type, inventory, project, "
    "playbook, and optional default credential/extra vars.",
    action_type="write",
    chain_callable=True,
    data_model=JobTemplate,
    event="ansible-automation-platform-connector.create_job_template",
    effects=["ansible.job_template.created"],
)
async def create_job_template(ctx, params: CreateJobTemplateParams) -> ActionResult:
    """Create a job template."""
    r = await resolve_connection(ctx, params.connection_id)
    if isinstance(r, ActionResult):
        return r
    conn, token = r
    payload = {
        "name": params.name,
        "job_type": params.job_type,
        "inventory": params.inventory,
        "project": params.project,
        "playbook": params.playbook,
        "description": params.description,
    }
    if params.credential:
        payload["credential"] = params.credential
    if params.extra_vars:
        payload["extra_vars"] = params.extra_vars
    try:
        d = await ac.create_resource(ctx, conn["api_base_url"], token, "job_templates", payload)
    except ac.ClientFail as e:
        return ActionResult.error(e.payload["error"], code=e.payload["error_code"])
    return ActionResult.ok(_to_jt(d), message="Job Template created.")


@chat.function(
    "update_job_template",
    "Update selected fields of an existing Job Template. Only given "
    "fields change.",
    action_type="write",
    chain_callable=True,
    data_model=JobTemplate,
    event="ansible-automation-platform-connector.update_job_template",
    effects=["ansible.job_template.updated"],
)
async def update_job_template(ctx, params: UpdateJobTemplateParams) -> ActionResult:
    """Update a job template."""
    r = await resolve_connection(ctx, params.connection_id)
    if isinstance(r, ActionResult):
        return r
    conn, token = r
    payload = {}
    if params.name:
        payload["name"] = params.name
    if params.description:
        payload["description"] = params.description
    if params.playbook:
        payload["playbook"] = params.playbook
    if params.extra_vars:
        payload["extra_vars"] = params.extra_vars
    if not payload:
        return ActionResult.error("No fields given to update.", code="AAP_NO_FIELDS")
    try:
        d = await ac.update_resource(ctx, conn["api_base_url"], token, "job_templates", params.resource_id, payload)
    except ac.ClientFail as e:
        return ActionResult.error(e.payload["error"], code=e.payload["error_code"])
    return ActionResult.ok(_to_jt(d), message="Job Template updated.")


@chat.function(
    "delete_job_template",
    "Permanently delete a Job Template. Cannot be undone.",
    action_type="write",
    chain_callable=True,
    data_model=DeleteResult,
    event="ansible-automation-platform-connector.delete_job_template",
    effects=["ansible.job_template.deleted"],
)
async def delete_job_template(ctx, params: DeleteJobTemplateParams) -> ActionResult:
    """Delete a job template."""
    r = await resolve_connection(ctx, params.connection_id)
    if isinstance(r, ActionResult):
        return r
    conn, token = r
    try:
        await ac.delete_resource(ctx, conn["api_base_url"], token, "job_templates", params.resource_id)
    except ac.ClientFail as e:
        return ActionResult.error(e.payload["error"], code=e.payload["error_code"])
    return ActionResult.ok(DeleteResult(ok=True, detail="Job Template deleted."), message="Job Template deleted.")


@chat.function(
    "launch_job_template",
    "Launch a Job Template now -- runs its playbook against its "
    "inventory, optionally overriding extra vars or a host limit for "
    "this run only.",
    action_type="write",
    chain_callable=True,
    data_model=JobLaunchResult,
    event="ansible-automation-platform-connector.launch_job_template",
    effects=["ansible.job.launched"],
)
async def launch_job_template(ctx, params: LaunchJobTemplateParams) -> ActionResult:
    """Launch a job template."""
    r = await resolve_connection(ctx, params.connection_id)
    if isinstance(r, ActionResult):
        return r
    conn, token = r
    payload = {}
    if params.extra_vars:
        payload["extra_vars"] = params.extra_vars
    if params.limit:
        payload["limit"] = params.limit
    try:
        d = await ac.post_action(ctx, conn["api_base_url"], token, "job_templates", params.resource_id, "launch", payload)
    except ac.ClientFail as e:
        return ActionResult.error(e.payload["error"], code=e.payload["error_code"])
    return ActionResult.ok(
        JobLaunchResult(job_id=d.get("job", d.get("id", 0)), status=d.get("status", "pending"), detail="Launched."),
        message="Job launched.",
    )
