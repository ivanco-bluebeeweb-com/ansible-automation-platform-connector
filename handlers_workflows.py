"""Chat functions for Workflow Job Templates: list/get/create/delete/launch
multi-step workflows, list workflow job runs and their nodes, and
approve/deny Workflow Approval nodes (a human-in-the-loop gate step)."""
from __future__ import annotations

from imperal_sdk import ActionResult

import ansible_client as ac
from app import ext, chat
from handlers_connection import resolve_connection
from schemas import (
    WorkflowJobTemplate, WorkflowJobTemplateList, ListWorkflowJobTemplatesParams,
    GetWorkflowJobTemplateParams, CreateWorkflowJobTemplateParams,
    DeleteWorkflowJobTemplateParams, LaunchWorkflowJobTemplateParams, JobLaunchResult,
    ListWorkflowJobsParams, WorkflowJob, WorkflowJobList,
    ListWorkflowNodesParams, WorkflowNode, WorkflowNodeList,
    ListWorkflowApprovalsParams, WorkflowApproval, WorkflowApprovalList,
    ApproveWorkflowParams, DenyWorkflowParams, DeleteResult,
)


def _to_wjt(d: dict) -> WorkflowJobTemplate:
    return WorkflowJobTemplate(id=d.get("id", 0), name=d.get("name", ""), description=d.get("description", ""), status=d.get("status", ""))


@chat.function(
    "list_workflow_templates",
    "List Workflow Job Templates (multi-step orchestrated sequences of "
    "job templates, projects, approvals, and other workflows) configured "
    "in the connected Controller.",
    action_type="read", chain_callable=True, data_model=WorkflowJobTemplateList,
    event="ansible-automation-platform-connector.list_workflow_templates",
)
async def list_workflow_templates(ctx, params: ListWorkflowJobTemplatesParams) -> ActionResult:
    """List workflow job templates."""
    r = await resolve_connection(ctx, params.connection_id)
    if isinstance(r, ActionResult):
        return r
    conn, token = r
    try:
        rows = await ac.list_resource(ctx, conn["api_base_url"], token, "workflow_job_templates", params={"page_size": params.limit})
    except ac.ClientFail as e:
        return ActionResult.error(e.payload["error"], code=e.payload["error_code"])
    items = [_to_wjt(d) for d in rows]
    return ActionResult.ok(WorkflowJobTemplateList(title="Workflow Job Templates", items=items, count=len(items)))


@chat.function(
    "get_workflow_job_template",
    "Read one Workflow Job Template in full.",
    action_type="read", chain_callable=True, data_model=WorkflowJobTemplate,
    event="ansible-automation-platform-connector.get_workflow_job_template",
)
async def get_workflow_job_template(ctx, params: GetWorkflowJobTemplateParams) -> ActionResult:
    """Get one workflow job template."""
    r = await resolve_connection(ctx, params.connection_id)
    if isinstance(r, ActionResult):
        return r
    conn, token = r
    try:
        d = await ac.get_resource(ctx, conn["api_base_url"], token, "workflow_job_templates", params.resource_id)
    except ac.ClientFail as e:
        return ActionResult.error(e.payload["error"], code=e.payload["error_code"])
    return ActionResult.ok(_to_wjt(d))


@chat.function(
    "create_workflow_template",
    "Create a new empty Workflow Job Template (its nodes/steps must be "
    "added afterwards via Controller's own UI or the workflow_nodes "
    "sub-resource -- Controller does not offer a single-call way to also "
    "define nodes at creation time).",
    action_type="write", chain_callable=True, data_model=WorkflowJobTemplate,
    event="ansible-automation-platform-connector.create_workflow_template",
    effects=["ansible.workflow_job_template.created"],
)
async def create_workflow_template(ctx, params: CreateWorkflowJobTemplateParams) -> ActionResult:
    """Create a workflow job template."""
    r = await resolve_connection(ctx, params.connection_id)
    if isinstance(r, ActionResult):
        return r
    conn, token = r
    payload = {"name": params.name, "description": params.description}
    if params.organization:
        payload["organization"] = params.organization
    try:
        d = await ac.create_resource(ctx, conn["api_base_url"], token, "workflow_job_templates", payload)
    except ac.ClientFail as e:
        return ActionResult.error(e.payload["error"], code=e.payload["error_code"])
    return ActionResult.ok(_to_wjt(d), message="Workflow Job Template created.")


@chat.function(
    "delete_workflow_template",
    "Permanently delete a Workflow Job Template. Cannot be undone.",
    action_type="write", chain_callable=True, data_model=DeleteResult,
    event="ansible-automation-platform-connector.delete_workflow_template",
    effects=["ansible.workflow_job_template.deleted"],
)
async def delete_workflow_template(ctx, params: DeleteWorkflowJobTemplateParams) -> ActionResult:
    """Delete a workflow job template."""
    r = await resolve_connection(ctx, params.connection_id)
    if isinstance(r, ActionResult):
        return r
    conn, token = r
    try:
        await ac.delete_resource(ctx, conn["api_base_url"], token, "workflow_job_templates", params.resource_id)
    except ac.ClientFail as e:
        return ActionResult.error(e.payload["error"], code=e.payload["error_code"])
    return ActionResult.ok(DeleteResult(ok=True, detail="Workflow Job Template deleted."), message="Workflow Job Template deleted.")


@chat.function(
    "launch_workflow_template",
    "Launch a Workflow Job Template now, running its whole node graph.",
    action_type="write", chain_callable=True, data_model=JobLaunchResult,
    event="ansible-automation-platform-connector.launch_workflow_template",
    effects=["ansible.workflow_job.launched"],
)
async def launch_workflow_template(ctx, params: LaunchWorkflowJobTemplateParams) -> ActionResult:
    """Launch a workflow job template."""
    r = await resolve_connection(ctx, params.connection_id)
    if isinstance(r, ActionResult):
        return r
    conn, token = r
    payload = {}
    if params.extra_vars:
        payload["extra_vars"] = params.extra_vars
    try:
        d = await ac.post_action(ctx, conn["api_base_url"], token, "workflow_job_templates", params.resource_id, "launch", payload)
    except ac.ClientFail as e:
        return ActionResult.error(e.payload["error"], code=e.payload["error_code"])
    return ActionResult.ok(JobLaunchResult(job_id=d.get("id", 0), status=d.get("status", ""), name=d.get("name", "")), message="Workflow job launched.")


@chat.function(
    "list_workflow_jobs",
    "List Workflow Job runs (executions of a Workflow Job Template), optionally filtered by status.",
    action_type="read", chain_callable=True, data_model=WorkflowJobList,
    event="ansible-automation-platform-connector.list_workflow_jobs",
)
async def list_workflow_jobs(ctx, params: ListWorkflowJobsParams) -> ActionResult:
    """List workflow jobs."""
    r = await resolve_connection(ctx, params.connection_id)
    if isinstance(r, ActionResult):
        return r
    conn, token = r
    qp = {"page_size": params.limit}
    if params.status:
        qp["status"] = params.status
    try:
        rows = await ac.list_resource(ctx, conn["api_base_url"], token, "workflow_jobs", params=qp)
    except ac.ClientFail as e:
        return ActionResult.error(e.payload["error"], code=e.payload["error_code"])
    items = [WorkflowJob(id=d.get("id", 0), name=d.get("name", ""), status=d.get("status", ""), started=str(d.get("started") or ""), finished=str(d.get("finished") or "")) for d in rows]
    return ActionResult.ok(WorkflowJobList(title="Workflow Jobs", items=items, count=len(items)))


@chat.function(
    "list_workflow_nodes",
    "List the nodes (steps) of one Workflow Job Template or Workflow Job -- which unified_job_template each node runs and how they chain.",
    action_type="read", chain_callable=True, data_model=WorkflowNodeList,
    event="ansible-automation-platform-connector.list_workflow_nodes",
)
async def list_workflow_nodes(ctx, params: ListWorkflowNodesParams) -> ActionResult:
    """List workflow nodes for a workflow job template."""
    r = await resolve_connection(ctx, params.connection_id)
    if isinstance(r, ActionResult):
        return r
    conn, token = r
    try:
        rows = await ac.get_sub_resource(ctx, conn["api_base_url"], token, "workflow_job_templates", params.resource_id, "workflow_nodes")
    except ac.ClientFail as e:
        return ActionResult.error(e.payload["error"], code=e.payload["error_code"])
    items = [WorkflowNode(id=d.get("id", 0), unified_job_template=d.get("unified_job_template"), job=d.get("job")) for d in rows]
    return ActionResult.ok(WorkflowNodeList(title="Workflow Nodes", items=items))


@chat.function(
    "list_workflow_approvals",
    "List Workflow Approval nodes awaiting a decision -- human-in-the-loop gate steps inside running workflows.",
    action_type="read", chain_callable=True, data_model=WorkflowApprovalList,
    event="ansible-automation-platform-connector.list_workflow_approvals",
)
async def list_workflow_approvals(ctx, params: ListWorkflowApprovalsParams) -> ActionResult:
    """List workflow approvals."""
    r = await resolve_connection(ctx, params.connection_id)
    if isinstance(r, ActionResult):
        return r
    conn, token = r
    try:
        rows = await ac.list_resource(ctx, conn["api_base_url"], token, "workflow_approvals", params={"page_size": params.limit, "status": "pending"})
    except ac.ClientFail as e:
        return ActionResult.error(e.payload["error"], code=e.payload["error_code"])
    items = [WorkflowApproval(id=d.get("id", 0), name=d.get("name", ""), status=d.get("status", ""), can_approve=d.get("can_approve_or_deny", True)) for d in rows]
    return ActionResult.ok(WorkflowApprovalList(title="Workflow Approvals", items=items))


@chat.function(
    "approve_workflow",
    "Approve a pending Workflow Approval node so the workflow continues past its human-in-the-loop gate.",
    action_type="write", chain_callable=True, data_model=DeleteResult,
    event="ansible-automation-platform-connector.approve_workflow",
    effects=["ansible.workflow_approval.approved"],
)
async def approve_workflow(ctx, params: ApproveWorkflowParams) -> ActionResult:
    """Approve a workflow approval node."""
    r = await resolve_connection(ctx, params.connection_id)
    if isinstance(r, ActionResult):
        return r
    conn, token = r
    try:
        await ac.post_action(ctx, conn["api_base_url"], token, "workflow_approvals", params.resource_id, "approve")
    except ac.ClientFail as e:
        return ActionResult.error(e.payload["error"], code=e.payload["error_code"])
    return ActionResult.ok(DeleteResult(ok=True, detail="Workflow approval approved."))


@chat.function(
    "deny_workflow",
    "Deny a pending Workflow Approval node -- stops that branch of the workflow.",
    action_type="write", chain_callable=True, data_model=DeleteResult,
    event="ansible-automation-platform-connector.deny_workflow",
    effects=["ansible.workflow_approval.denied"],
)
async def deny_workflow(ctx, params: DenyWorkflowParams) -> ActionResult:
    """Deny a workflow approval node."""
    r = await resolve_connection(ctx, params.connection_id)
    if isinstance(r, ActionResult):
        return r
    conn, token = r
    try:
        await ac.post_action(ctx, conn["api_base_url"], token, "workflow_approvals", params.resource_id, "deny")
    except ac.ClientFail as e:
        return ActionResult.error(e.payload["error"], code=e.payload["error_code"])
    return ActionResult.ok(DeleteResult(ok=True, detail="Workflow approval denied."))
