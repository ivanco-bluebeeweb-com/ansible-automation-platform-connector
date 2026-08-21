"""Chat functions for Activity Stream (Controller's own audit log of who
changed what) and a value-add aggregated health/audit report across Job
Templates -- same 'audit_*' pattern as Blue Prism Connector's
audit_estate / UiPath Connector's audit_folder."""
from __future__ import annotations

import datetime as _dt

from imperal_sdk import ActionResult

import ansible_client as ac
from app import ext, chat
from handlers_connection import resolve_connection
from schemas import (
    ActivityStreamEntry, ActivityStreamList, ListActivityStreamParams,
    AuditControllerParams, AuditRow, AuditControllerReport,
)


@chat.function(
    "list_activity_stream",
    "Read Controller's own Activity Stream -- an audit log of who created/updated/deleted what and when.",
    action_type="read", chain_callable=True, data_model=ActivityStreamList,
    event="ansible-automation-platform-connector.list_activity_stream",
)
async def list_activity_stream(ctx, params: ListActivityStreamParams) -> ActionResult:
    """List activity stream entries."""
    r = await resolve_connection(ctx, params.connection_id)
    if isinstance(r, ActionResult):
        return r
    conn, token = r
    try:
        rows = await ac.list_resource(ctx, conn["api_base_url"], token, "activity_stream", params={"page_size": params.limit})
    except ac.ClientFail as e:
        return ActionResult.error(e.payload["error"], code=e.payload["error_code"])
    items = []
    for d in rows:
        actor = ""
        try:
            actors = d.get("summary_fields", {}).get("actor")
            if actors:
                actor = actors.get("username", "")
        except Exception:
            pass
        items.append(ActivityStreamEntry(
            id=d.get("id", 0), operation=d.get("operation", ""),
            changes=str(d.get("changes", ""))[:500], timestamp=str(d.get("timestamp") or ""),
            actor=actor,
        ))
    return ActionResult.ok(ActivityStreamList(title="Activity Stream", items=items))


@chat.function(
    "audit_controller",
    "Build one aggregated health report across every Job Template in the "
    "connected Controller: last run status, failure rate, total run count "
    "per template, plus currently running jobs and jobs failed in the "
    "last 24 hours -- a value-add report Controller's own UI does not "
    "surface in one view (same idea as Blue Prism Connector's audit_estate "
    "/ UiPath Connector's audit_folder).",
    action_type="read", chain_callable=True, data_model=AuditControllerReport,
    event="ansible-automation-platform-connector.audit_controller",
)
async def audit_controller(ctx, params: AuditControllerParams) -> ActionResult:
    """Aggregate a health report across job templates and recent jobs."""
    r = await resolve_connection(ctx, params.connection_id)
    if isinstance(r, ActionResult):
        return r
    conn, token = r
    try:
        templates = await ac.list_resource(ctx, conn["api_base_url"], token, "job_templates", params={"page_size": 200})
        recent_jobs = await ac.list_resource(ctx, conn["api_base_url"], token, "jobs", params={"page_size": 200, "order_by": "-created"})
    except ac.ClientFail as e:
        return ActionResult.error(e.payload["error"], code=e.payload["error_code"])

    jobs_by_template: dict[int, list[dict]] = {}
    running_jobs = 0
    failed_24h = 0
    now = _dt.datetime.now(_dt.timezone.utc)
    for j in recent_jobs:
        jt_id = j.get("job_template")
        if jt_id is not None:
            jobs_by_template.setdefault(jt_id, []).append(j)
        if j.get("status") in ("pending", "waiting", "running"):
            running_jobs += 1
        if j.get("failed"):
            finished = j.get("finished")
            if finished:
                try:
                    ts = _dt.datetime.fromisoformat(str(finished).replace("Z", "+00:00"))
                    if (now - ts).total_seconds() <= 86400:
                        failed_24h += 1
                except Exception:
                    pass

    rows = []
    for t in templates:
        tid = t.get("id")
        runs = jobs_by_template.get(tid, [])
        total = len(runs)
        failures = sum(1 for j in runs if j.get("failed"))
        rate = round((failures / total) * 100, 1) if total else 0.0
        last_status = runs[0].get("status", "") if runs else t.get("status", "")
        rows.append(AuditRow(
            job_template_name=t.get("name", ""), last_status=last_status,
            failure_rate_pct=rate, total_runs=total,
        ))

    return ActionResult.ok(AuditControllerReport(
        title="Controller Audit",
        generated_at=now.isoformat(),
        rows=rows, running_jobs=running_jobs, failed_jobs_24h=failed_24h,
    ))
