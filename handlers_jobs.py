"""Chat functions for Jobs (job runs): list/get/stdout/cancel/relaunch,
bulk cancel, and job events (per-task execution timeline)."""
from __future__ import annotations

from imperal_sdk import ActionResult

import ansible_client as ac
from app import ext, chat
from handlers_connection import resolve_connection
from schemas import (
    ListJobsParams, Job, JobList, GetJobParams, GetJobStdoutParams, JobStdout,
    CancelJobParams, RelaunchJobParams, JobLaunchResult,
    BulkJobIdsParams, BulkJobResultItem, BulkJobResult,
    ListJobEventsParams, JobEvent, JobEventList,
)


def _to_job(d: dict) -> Job:
    return Job(
        id=d.get("id", 0), name=d.get("name", ""), status=d.get("status", ""),
        job_type=d.get("job_type", ""), started=str(d.get("started") or ""),
        finished=str(d.get("finished") or ""), elapsed=float(d.get("elapsed") or 0.0),
        failed=bool(d.get("failed", False)),
    )


@chat.function(
    "list_jobs",
    "List Jobs (playbook run executions) in the connected Controller, optionally filtered by status.",
    action_type="read", chain_callable=True, data_model=JobList,
    event="ansible-automation-platform-connector.list_jobs",
)
async def list_jobs(ctx, params: ListJobsParams) -> ActionResult:
    """List jobs."""
    r = await resolve_connection(ctx, params.connection_id)
    if isinstance(r, ActionResult):
        return r
    conn, token = r
    qp = {"page_size": params.limit}
    if params.status:
        qp["status"] = params.status
    try:
        rows = await ac.list_resource(ctx, conn["api_base_url"], token, "jobs", params=qp)
    except ac.ClientFail as e:
        return ActionResult.error(e.payload["error"], code=e.payload["error_code"])
    items = [_to_job(d) for d in rows]
    return ActionResult.success(JobList(title="Jobs", items=items, count=len(items)), summary="Jobs listed.")


@chat.function(
    "get_job",
    "Read one Job in full: status, timing, and whether it failed.",
    action_type="read", chain_callable=True, data_model=Job,
    event="ansible-automation-platform-connector.get_job",
)
async def get_job(ctx, params: GetJobParams) -> ActionResult:
    """Get one job."""
    r = await resolve_connection(ctx, params.connection_id)
    if isinstance(r, ActionResult):
        return r
    conn, token = r
    try:
        d = await ac.get_resource(ctx, conn["api_base_url"], token, "jobs", params.resource_id)
    except ac.ClientFail as e:
        return ActionResult.error(e.payload["error"], code=e.payload["error_code"])
    return ActionResult.success(_to_job(d), summary="Job retrieved.")


@chat.function(
    "get_job_stdout",
    "Read a Job's console output (ansible-playbook stdout), in txt/html/json/ansi format.",
    action_type="read", chain_callable=True, data_model=JobStdout,
    event="ansible-automation-platform-connector.get_job_stdout",
)
async def get_job_stdout(ctx, params: GetJobStdoutParams) -> ActionResult:
    """Get job stdout."""
    r = await resolve_connection(ctx, params.connection_id)
    if isinstance(r, ActionResult):
        return r
    conn, token = r
    try:
        text = await ac.get_stdout(ctx, conn["api_base_url"], token, params.resource_id, format_=params.format_)
    except ac.ClientFail as e:
        return ActionResult.error(e.payload["error"], code=e.payload["error_code"])
    return ActionResult.success(JobStdout(job_id=params.resource_id, output=text), summary="Job stdout retrieved.")


@chat.function(
    "cancel_job",
    "Cancel a running or pending Job.",
    action_type="write", chain_callable=True, data_model=Job,
    event="ansible-automation-platform-connector.cancel_job",
    effects=["ansible.job.canceled"],
)
async def cancel_job(ctx, params: CancelJobParams) -> ActionResult:
    """Cancel a job."""
    r = await resolve_connection(ctx, params.connection_id)
    if isinstance(r, ActionResult):
        return r
    conn, token = r
    try:
        await ac.post_action(ctx, conn["api_base_url"], token, "jobs", params.resource_id, "cancel")
        d = await ac.get_resource(ctx, conn["api_base_url"], token, "jobs", params.resource_id)
    except ac.ClientFail as e:
        return ActionResult.error(e.payload["error"], code=e.payload["error_code"])
    return ActionResult.success(_to_job(d), message="Job cancel requested.", summary="Cancel job done.")


@chat.function(
    "relaunch_job",
    "Relaunch a finished Job -- runs the same job template again with the same parameters.",
    action_type="write", chain_callable=True, data_model=JobLaunchResult,
    event="ansible-automation-platform-connector.relaunch_job",
    effects=["ansible.job.relaunched"],
)
async def relaunch_job(ctx, params: RelaunchJobParams) -> ActionResult:
    """Relaunch a job."""
    r = await resolve_connection(ctx, params.connection_id)
    if isinstance(r, ActionResult):
        return r
    conn, token = r
    try:
        d = await ac.post_action(ctx, conn["api_base_url"], token, "jobs", params.resource_id, "relaunch")
    except ac.ClientFail as e:
        return ActionResult.error(e.payload["error"], code=e.payload["error_code"])
    return ActionResult.success(JobLaunchResult(job_id=d.get("id", 0), status=d.get("status", ""), detail="Job relaunched."), summary="Relaunch job done.")


@chat.function(
    "bulk_cancel_jobs",
    "Cancel several Jobs in one call, by explicit job ids. Continues past per-item failures and reports per-job results.",
    action_type="destructive", chain_callable=True, data_model=BulkJobResult,
    event="ansible-automation-platform-connector.bulk_cancel_jobs",
    effects=["ansible.job.canceled"],
)
async def bulk_cancel_jobs(ctx, params: BulkJobIdsParams) -> ActionResult:
    """Cancel several jobs."""
    r = await resolve_connection(ctx, params.connection_id)
    if isinstance(r, ActionResult):
        return r
    conn, token = r
    results: list[BulkJobResultItem] = []
    for jid in params.job_ids:
        try:
            await ac.post_action(ctx, conn["api_base_url"], token, "jobs", jid, "cancel")
            results.append(BulkJobResultItem(job_id=jid, ok=True, detail="Cancel requested."))
        except ac.ClientFail as e:
            results.append(BulkJobResultItem(job_id=jid, ok=False, detail=e.payload["error"]))
    return ActionResult.success(BulkJobResult(items=results), summary="Bulk cancel jobs done.")


@chat.function(
    "list_job_events",
    "List the per-task execution events (timeline) of one Job -- each play/task/host result as it ran.",
    action_type="read", chain_callable=True, data_model=JobEventList,
    event="ansible-automation-platform-connector.list_job_events",
)
async def list_job_events(ctx, params: ListJobEventsParams) -> ActionResult:
    """List job events."""
    r = await resolve_connection(ctx, params.connection_id)
    if isinstance(r, ActionResult):
        return r
    conn, token = r
    try:
        rows = await ac.get_sub_resource(ctx, conn["api_base_url"], token, "jobs", params.resource_id, "job_events", params={"page_size": params.limit})
    except ac.ClientFail as e:
        return ActionResult.error(e.payload["error"], code=e.payload["error_code"])
    items = [JobEvent(id=d.get("id", 0), event=d.get("event", ""), stdout=d.get("stdout", ""), task=d.get("task", ""), host_name=d.get("host_name", ""), failed=bool(d.get("failed", False))) for d in rows]
    return ActionResult.success(JobEventList(title="Job Events", items=items), summary="Job events listed.")
