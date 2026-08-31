"""Chat functions for Ad Hoc Commands (one-off module runs against an
Inventory, outside any Job Template) and Notification Templates (Slack/
email/webhook/PagerDuty alerts Controller can fire on job events)."""
from __future__ import annotations

import json

from imperal_sdk import ActionResult

import ansible_client as ac
from app import ext, chat
from handlers_connection import resolve_connection
from schemas import (
    RunAdHocCommandParams, AdHocCommand, ListAdHocCommandsParams, AdHocCommandList,
    NotificationTemplate, NotificationTemplateList, ListNotificationTemplatesParams,
    CreateNotificationTemplateParams, DeleteNotificationTemplateParams,
    TestNotificationTemplateParams, DeleteResult,
)


@chat.function(
    "run_ad_hoc_command",
    "Run a one-off Ansible module (e.g. command, shell, ping, setup) "
    "against an Inventory right now, outside of any Job Template.",
    action_type="write", chain_callable=True, data_model=AdHocCommand,
    event="ansible-automation-platform-connector.run_ad_hoc_command",
    effects=["ansible.ad_hoc_command.launched"],
)
async def run_ad_hoc_command(ctx, params: RunAdHocCommandParams) -> ActionResult:
    """Launch an ad hoc command."""
    r = await resolve_connection(ctx, params.connection_id)
    if isinstance(r, ActionResult):
        return r
    conn, token = r
    payload = {
        "inventory": params.inventory, "credential": params.credential,
        "module_name": params.module_name, "module_args": params.module_args,
    }
    if params.limit:
        payload["limit"] = params.limit
    try:
        d = await ac.create_resource(ctx, conn["api_base_url"], token, "ad_hoc_commands", payload)
    except ac.ClientFail as e:
        return ActionResult.error(e.payload["error"], code=e.payload["error_code"])
    return ActionResult.success(AdHocCommand(id=d.get("id", 0), status=d.get("status", ""), module_name=d.get("module_name", "")), message="Ad hoc command launched.", summary="Ad hoc command run requested.")


@chat.function(
    "list_ad_hoc_commands",
    "List past Ad Hoc Command runs in the connected Controller.",
    action_type="read", chain_callable=True, data_model=AdHocCommandList,
    event="ansible-automation-platform-connector.list_ad_hoc_commands",
)
async def list_ad_hoc_commands(ctx, params: ListAdHocCommandsParams) -> ActionResult:
    """List ad hoc commands."""
    r = await resolve_connection(ctx, params.connection_id)
    if isinstance(r, ActionResult):
        return r
    conn, token = r
    try:
        rows = await ac.list_resource(ctx, conn["api_base_url"], token, "ad_hoc_commands", params={"page_size": params.limit})
    except ac.ClientFail as e:
        return ActionResult.error(e.payload["error"], code=e.payload["error_code"])
    items = [AdHocCommand(id=d.get("id", 0), status=d.get("status", ""), module_name=d.get("module_name", "")) for d in rows]
    return ActionResult.success(AdHocCommandList(title="Ad Hoc Commands", items=items), summary="Ad hoc commands listed.")


def _to_nt(d: dict) -> NotificationTemplate:
    return NotificationTemplate(id=d.get("id", 0), name=d.get("name", ""), notification_type=d.get("notification_type", ""))


@chat.function(
    "list_notif_templates",
    "List Notification Templates (Slack/email/webhook/PagerDuty alerts Controller can fire on job events) configured in the connected Controller.",
    action_type="read", chain_callable=True, data_model=NotificationTemplateList,
    event="ansible-automation-platform-connector.list_notif_templates",
)
async def list_notif_templates(ctx, params: ListNotificationTemplatesParams) -> ActionResult:
    """List notification templates."""
    r = await resolve_connection(ctx, params.connection_id)
    if isinstance(r, ActionResult):
        return r
    conn, token = r
    try:
        rows = await ac.list_resource(ctx, conn["api_base_url"], token, "notification_templates")
    except ac.ClientFail as e:
        return ActionResult.error(e.payload["error"], code=e.payload["error_code"])
    items = [_to_nt(d) for d in rows]
    return ActionResult.success(NotificationTemplateList(title="Notification Templates", items=items), summary="Notif templates listed.")


@chat.function(
    "create_notif_template",
    "Create a new Notification Template (e.g. Slack, email, webhook, PagerDuty) for job/workflow event alerts.",
    action_type="write", chain_callable=True, data_model=NotificationTemplate,
    event="ansible-automation-platform-connector.create_notif_template",
    effects=["ansible.notification_template.created"],
)
async def create_notif_template(ctx, params: CreateNotificationTemplateParams) -> ActionResult:
    """Create a notification template."""
    r = await resolve_connection(ctx, params.connection_id)
    if isinstance(r, ActionResult):
        return r
    conn, token = r
    try:
        config = json.loads(params.notification_configuration_json)
    except Exception:
        return ActionResult.error("notification_configuration_json must be valid JSON.", code="AAP_VALIDATION_FAILED")
    payload = {
        "name": params.name, "organization": params.organization,
        "notification_type": params.notification_type, "notification_configuration": config,
    }
    try:
        d = await ac.create_resource(ctx, conn["api_base_url"], token, "notification_templates", payload)
    except ac.ClientFail as e:
        return ActionResult.error(e.payload["error"], code=e.payload["error_code"])
    return ActionResult.success(_to_nt(d), message="Notification template created.", summary="Notif template created.")


@chat.function(
    "delete_notif_template",
    "Permanently delete a Notification Template. Cannot be undone.",
    action_type="write", chain_callable=True, data_model=DeleteResult,
    event="ansible-automation-platform-connector.delete_notif_template",
    effects=["ansible.notification_template.deleted"],
)
async def delete_notif_template(ctx, params: DeleteNotificationTemplateParams) -> ActionResult:
    """Delete a notification template."""
    r = await resolve_connection(ctx, params.connection_id)
    if isinstance(r, ActionResult):
        return r
    conn, token = r
    try:
        await ac.delete_resource(ctx, conn["api_base_url"], token, "notification_templates", params.resource_id)
    except ac.ClientFail as e:
        return ActionResult.error(e.payload["error"], code=e.payload["error_code"])
    return ActionResult.success(DeleteResult(ok=True, detail="Notification template deleted."), summary="Notif template deleted.")


@chat.function(
    "test_notif_template",
    "Send a test notification through a Notification Template so you can confirm the destination actually receives it.",
    action_type="write", chain_callable=True, data_model=DeleteResult,
    event="ansible-automation-platform-connector.test_notif_template",
    effects=["ansible.notification_template.tested"],
)
async def test_notif_template(ctx, params: TestNotificationTemplateParams) -> ActionResult:
    """Send a test notification."""
    r = await resolve_connection(ctx, params.connection_id)
    if isinstance(r, ActionResult):
        return r
    conn, token = r
    try:
        await ac.post_action(ctx, conn["api_base_url"], token, "notification_templates", params.resource_id, "test")
    except ac.ClientFail as e:
        return ActionResult.error(e.payload["error"], code=e.payload["error_code"])
    return ActionResult.success(DeleteResult(ok=True, detail="Test notification sent."), summary="Test notif template done.")
