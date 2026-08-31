"""Pydantic params models + SDL entity contracts for Ansible Automation
Platform (Controller/AWX) Connector.

All params models are module-scope (V17 federal invariant, same rule as
UiPath Connector / Blue Prism Connector / MuleSoft Connector's schemas.py).
"""
from __future__ import annotations

from pydantic import BaseModel, Field
from imperal_sdk import sdl


class NoParams(BaseModel):
    """Explicit empty params model -- V17 disallows untyped handlers."""
    pass


# ──────────────────────────────────────────────────────────────────────────
# Connection
# ──────────────────────────────────────────────────────────────────────────


class ConnectAnsibleParams(BaseModel):
    api_base_url: str = Field(
        "",
        description="Full Controller API base URL, e.g. https://awx.example.com/api/v2 or https://aap.example.com/api/controller/v2",
    )
    token: str = Field(
        "",
        description="Personal Access Token minted in Controller (Users > your user > Tokens, or POST /api/v2/tokens/).",
    )
    label: str = Field("", description="Optional friendly name for this Controller connection.")


class ProviderConnection(sdl.Entity):
    id: str
    title: str
    detail: str


class ProviderConnectionList(sdl.Entity):
    id: str = ""
    title: str = ""
    items: list[ProviderConnection]


class DisconnectAnsibleParams(BaseModel):
    connection_id: str = Field(..., description="Connection id to disconnect, from list_connections.")


class DeleteResult(sdl.Entity):
    id: str = ""
    title: str = ""
    ok: bool
    detail: str = ""


# ──────────────────────────────────────────────────────────────────────────
# Shared helpers
# ──────────────────────────────────────────────────────────────────────────


class _ConnScopedParams(BaseModel):
    connection_id: str = Field("", description="Connection id from list_connections. Omit to use the only connected Controller.")


class _IdParams(_ConnScopedParams):
    resource_id: int = Field(..., description="Resource id.")


# ──────────────────────────────────────────────────────────────────────────
# Job Templates
# ──────────────────────────────────────────────────────────────────────────


class JobTemplate(sdl.Entity):
    title: str = ""
    id: int
    name: str
    description: str = ""
    job_type: str = ""
    inventory: int | None = None
    project: int | None = None
    playbook: str = ""
    status: str = ""
    last_job_run: str = ""


class JobTemplateList(sdl.Entity):
    id: str = ""
    title: str = ""
    items: list[JobTemplate]
    count: int = 0


class ListJobTemplatesParams(_ConnScopedParams):
    limit: int = Field(50, ge=1, le=200)


class GetJobTemplateParams(_IdParams):
    pass


class CreateJobTemplateParams(_ConnScopedParams):
    name: str = Field(..., description="Job template name.")
    job_type: str = Field("run", description="run or check.")
    inventory: int = Field(..., description="Inventory id.")
    project: int = Field(..., description="Project id.")
    playbook: str = Field(..., description="Playbook filename inside the project, e.g. site.yml.")
    description: str = Field("", description="Optional description.")
    credential: int = Field(0, description="Optional default credential id to attach.")
    extra_vars: str = Field("", description="Optional extra vars as YAML/JSON text.")


class UpdateJobTemplateParams(_IdParams):
    name: str = Field("", description="New name, or leave blank to keep current.")
    description: str = Field("", description="New description, or leave blank to keep current.")
    playbook: str = Field("", description="New playbook filename, or leave blank to keep current.")
    extra_vars: str = Field("", description="New extra vars text, or leave blank to keep current.")


class DeleteJobTemplateParams(_IdParams):
    pass


class LaunchJobTemplateParams(_IdParams):
    extra_vars: str = Field("", description="Optional extra vars as YAML/JSON text to override for this run only.")
    limit: str = Field("", description="Optional host pattern to limit this run to.")


class JobLaunchResult(sdl.Entity):
    id: str = ""
    title: str = ""
    job_id: int
    status: str
    detail: str = ""


# ──────────────────────────────────────────────────────────────────────────
# Jobs (job runs)
# ──────────────────────────────────────────────────────────────────────────


class Job(sdl.Entity):
    title: str = ""
    id: int
    name: str
    status: str
    job_type: str = ""
    started: str = ""
    finished: str = ""
    elapsed: float = 0.0
    failed: bool = False


class JobList(sdl.Entity):
    id: str = ""
    title: str = ""
    items: list[Job]
    count: int = 0


class ListJobsParams(_ConnScopedParams):
    status: str = Field("", description="Optional filter: pending, waiting, running, successful, failed, error, canceled.")
    limit: int = Field(50, ge=1, le=200)


class GetJobParams(_IdParams):
    pass


class GetJobStdoutParams(_IdParams):
    format_: str = Field("txt", description="Output format: txt, html, json, ansi.")


class JobStdout(sdl.Entity):
    id: str = ""
    title: str = ""
    job_id: int
    output: str


class CancelJobParams(_IdParams):
    pass


class RelaunchJobParams(_IdParams):
    pass


class BulkJobIdsParams(_ConnScopedParams):
    job_ids: list[int] = Field(..., min_length=1, max_length=100)


class BulkJobResultItem(sdl.Entity):
    id: str = ""
    title: str = ""
    job_id: int
    ok: bool
    detail: str = ""


class BulkJobResult(sdl.Entity):
    id: str = ""
    title: str = ""
    items: list[BulkJobResultItem]


class ListJobEventsParams(_IdParams):
    limit: int = Field(50, ge=1, le=200)


class JobEvent(sdl.Entity):
    title: str = ""
    id: int
    event: str
    stdout: str = ""
    task: str = ""
    host_name: str = ""
    failed: bool = False


class JobEventList(sdl.Entity):
    id: str = ""
    title: str = ""
    items: list[JobEvent]


# ──────────────────────────────────────────────────────────────────────────
# Workflow Job Templates
# ──────────────────────────────────────────────────────────────────────────


class WorkflowJobTemplate(sdl.Entity):
    title: str = ""
    id: int
    name: str
    description: str = ""
    status: str = ""


class WorkflowJobTemplateList(sdl.Entity):
    id: str = ""
    title: str = ""
    items: list[WorkflowJobTemplate]
    count: int = 0


class ListWorkflowJobTemplatesParams(_ConnScopedParams):
    limit: int = Field(50, ge=1, le=200)


class GetWorkflowJobTemplateParams(_IdParams):
    pass


class CreateWorkflowJobTemplateParams(_ConnScopedParams):
    name: str = Field(..., description="Workflow template name.")
    description: str = Field("", description="Optional description.")
    organization: int = Field(0, description="Optional organization id.")


class DeleteWorkflowJobTemplateParams(_IdParams):
    pass


class LaunchWorkflowJobTemplateParams(_IdParams):
    extra_vars: str = Field("", description="Optional extra vars as YAML/JSON text.")


class ListWorkflowJobsParams(_ConnScopedParams):
    status: str = Field("", description="Optional status filter.")
    limit: int = Field(50, ge=1, le=200)


class WorkflowJob(sdl.Entity):
    title: str = ""
    id: int
    name: str
    status: str
    started: str = ""
    finished: str = ""


class WorkflowJobList(sdl.Entity):
    id: str = ""
    title: str = ""
    items: list[WorkflowJob]
    count: int = 0


class ListWorkflowNodesParams(_IdParams):
    pass


class WorkflowNode(sdl.Entity):
    title: str = ""
    id: int
    unified_job_template: int | None = None
    job: int | None = None


class WorkflowNodeList(sdl.Entity):
    id: str = ""
    title: str = ""
    items: list[WorkflowNode]


class ListWorkflowApprovalsParams(_ConnScopedParams):
    limit: int = Field(50, ge=1, le=200)


class WorkflowApproval(sdl.Entity):
    title: str = ""
    id: int
    name: str
    status: str
    can_approve: bool = True


class WorkflowApprovalList(sdl.Entity):
    id: str = ""
    title: str = ""
    items: list[WorkflowApproval]


class ApproveWorkflowParams(_IdParams):
    pass


class DenyWorkflowParams(_IdParams):
    pass


# ──────────────────────────────────────────────────────────────────────────
# Projects
# ──────────────────────────────────────────────────────────────────────────


class Project(sdl.Entity):
    title: str = ""
    id: int
    name: str
    description: str = ""
    scm_type: str = ""
    scm_url: str = ""
    status: str = ""


class ProjectList(sdl.Entity):
    id: str = ""
    title: str = ""
    items: list[Project]
    count: int = 0


class ListProjectsParams(_ConnScopedParams):
    limit: int = Field(50, ge=1, le=200)


class GetProjectParams(_IdParams):
    pass


class CreateProjectParams(_ConnScopedParams):
    name: str = Field(..., description="Project name.")
    scm_type: str = Field("git", description="git, hg, svn, or empty for manual.")
    scm_url: str = Field("", description="Source control URL.")
    scm_branch: str = Field("", description="Optional branch/tag/commit.")
    organization: int = Field(0, description="Optional organization id.")
    description: str = Field("", description="Optional description.")


class UpdateProjectParams(_IdParams):
    name: str = Field("", description="New name, or leave blank to keep current.")
    scm_url: str = Field("", description="New SCM URL, or leave blank to keep current.")
    scm_branch: str = Field("", description="New SCM branch, or leave blank to keep current.")


class DeleteProjectParams(_IdParams):
    pass


class SyncProjectParams(_IdParams):
    pass


# ──────────────────────────────────────────────────────────────────────────
# Inventories / Hosts / Groups
# ──────────────────────────────────────────────────────────────────────────


class Inventory(sdl.Entity):
    title: str = ""
    id: int
    name: str
    description: str = ""
    organization: int | None = None
    total_hosts: int = 0


class InventoryList(sdl.Entity):
    id: str = ""
    title: str = ""
    items: list[Inventory]
    count: int = 0


class ListInventoriesParams(_ConnScopedParams):
    limit: int = Field(50, ge=1, le=200)


class GetInventoryParams(_IdParams):
    pass


class CreateInventoryParams(_ConnScopedParams):
    name: str = Field(..., description="Inventory name.")
    organization: int = Field(..., description="Organization id.")
    description: str = Field("", description="Optional description.")


class UpdateInventoryParams(_IdParams):
    name: str = Field("", description="New name, or leave blank to keep current.")
    description: str = Field("", description="New description, or leave blank to keep current.")


class DeleteInventoryParams(_IdParams):
    pass


class Host(sdl.Entity):
    title: str = ""
    id: int
    name: str
    description: str = ""
    enabled: bool = True
    inventory: int | None = None


class HostList(sdl.Entity):
    id: str = ""
    title: str = ""
    items: list[Host]
    count: int = 0


class ListHostsParams(_IdParams):
    limit: int = Field(50, ge=1, le=200)


class CreateHostParams(_IdParams):
    name: str = Field(..., description="Hostname or IP.")
    variables: str = Field("", description="Optional host variables as YAML/JSON text.")
    description: str = Field("", description="Optional description.")


class UpdateHostParams(_ConnScopedParams):
    host_id: int = Field(..., description="Host id.")
    name: str = Field("", description="New name, or leave blank to keep current.")
    variables: str = Field("", description="New variables text, or leave blank to keep current.")
    enabled: bool = Field(True, description="Whether the host is enabled.")


class DeleteHostParams(_ConnScopedParams):
    host_id: int = Field(..., description="Host id to delete.")


class Group(sdl.Entity):
    title: str = ""
    id: int
    name: str
    description: str = ""
    inventory: int | None = None


class GroupList(sdl.Entity):
    id: str = ""
    title: str = ""
    items: list[Group]


class ListGroupsParams(_IdParams):
    pass


class CreateGroupParams(_IdParams):
    name: str = Field(..., description="Group name.")
    variables: str = Field("", description="Optional group variables as YAML/JSON text.")


class DeleteGroupParams(_ConnScopedParams):
    group_id: int = Field(..., description="Group id to delete.")


class InventorySource(sdl.Entity):
    title: str = ""
    id: int
    name: str
    source: str = ""
    status: str = ""


class InventorySourceList(sdl.Entity):
    id: str = ""
    title: str = ""
    items: list[InventorySource]


class ListInventorySourcesParams(_IdParams):
    pass


class SyncInventorySourceParams(_ConnScopedParams):
    source_id: int = Field(..., description="Inventory source id to sync now.")


# ──────────────────────────────────────────────────────────────────────────
# Credentials / Credential Types
# ──────────────────────────────────────────────────────────────────────────


class Credential(sdl.Entity):
    title: str = ""
    id: int
    name: str
    description: str = ""
    credential_type: int | None = None
    kind: str = ""


class CredentialList(sdl.Entity):
    id: str = ""
    title: str = ""
    items: list[Credential]
    count: int = 0


class ListCredentialsParams(_ConnScopedParams):
    limit: int = Field(50, ge=1, le=200)


class GetCredentialParams(_IdParams):
    pass


class CreateCredentialParams(_ConnScopedParams):
    name: str = Field(..., description="Credential name.")
    credential_type: int = Field(..., description="Credential type id (see list_credential_types).")
    organization: int = Field(0, description="Optional organization id.")
    inputs_json: str = Field("{}", description="Credential field inputs as a JSON object string, e.g. {\"username\":\"x\",\"password\":\"y\"}.")


class DeleteCredentialParams(_IdParams):
    pass


class CredentialType(sdl.Entity):
    title: str = ""
    id: int
    name: str
    kind: str = ""


class CredentialTypeList(sdl.Entity):
    id: str = ""
    title: str = ""
    items: list[CredentialType]


class ListCredentialTypesParams(_ConnScopedParams):
    pass


# ──────────────────────────────────────────────────────────────────────────
# Schedules
# ──────────────────────────────────────────────────────────────────────────


class Schedule(sdl.Entity):
    title: str = ""
    id: int
    name: str
    rrule: str = ""
    enabled: bool = True
    unified_job_template: int | None = None


class ScheduleList(sdl.Entity):
    id: str = ""
    title: str = ""
    items: list[Schedule]


class ListSchedulesParams(_ConnScopedParams):
    limit: int = Field(50, ge=1, le=200)


class CreateScheduleParams(_IdParams):
    name: str = Field(..., description="Schedule name.")
    rrule: str = Field(..., description="iCal RRULE string, e.g. DTSTART;TZID=UTC:20260101T000000 RRULE:FREQ=DAILY;INTERVAL=1")


class SetScheduleEnabledParams(_ConnScopedParams):
    schedule_id: int = Field(..., description="Schedule id.")
    enabled: bool = Field(..., description="True to enable, False to disable.")


class DeleteScheduleParams(_ConnScopedParams):
    schedule_id: int = Field(..., description="Schedule id to delete.")


# ──────────────────────────────────────────────────────────────────────────
# Organizations / Teams / Users
# ──────────────────────────────────────────────────────────────────────────


class Organization(sdl.Entity):
    title: str = ""
    id: int
    name: str
    description: str = ""


class OrganizationList(sdl.Entity):
    id: str = ""
    title: str = ""
    items: list[Organization]


class ListOrganizationsParams(_ConnScopedParams):
    limit: int = Field(50, ge=1, le=200)


class CreateOrganizationParams(_ConnScopedParams):
    name: str = Field(..., description="Organization name.")
    description: str = Field("", description="Optional description.")


class Team(sdl.Entity):
    title: str = ""
    id: int
    name: str
    organization: int | None = None


class TeamList(sdl.Entity):
    id: str = ""
    title: str = ""
    items: list[Team]


class ListTeamsParams(_ConnScopedParams):
    limit: int = Field(50, ge=1, le=200)


class CreateTeamParams(_ConnScopedParams):
    name: str = Field(..., description="Team name.")
    organization: int = Field(..., description="Organization id.")


class AAPUser(sdl.Entity):
    title: str = ""
    id: int
    username: str
    email: str = ""
    is_superuser: bool = False


class AAPUserList(sdl.Entity):
    id: str = ""
    title: str = ""
    items: list[AAPUser]


class ListUsersParams(_ConnScopedParams):
    limit: int = Field(50, ge=1, le=200)


class CreateUserParams(_ConnScopedParams):
    username: str = Field(..., description="Username.")
    password: str = Field(..., description="Initial password.")
    email: str = Field("", description="Optional email.")
    first_name: str = Field("", description="Optional first name.")
    last_name: str = Field("", description="Optional last name.")


class DeleteUserParams(_IdParams):
    pass


# ──────────────────────────────────────────────────────────────────────────
# Ad Hoc Commands
# ──────────────────────────────────────────────────────────────────────────


class RunAdHocCommandParams(_ConnScopedParams):
    inventory: int = Field(..., description="Inventory id to run against.")
    credential: int = Field(..., description="Machine credential id to authenticate with.")
    module_name: str = Field("command", description="Ansible module to run, e.g. command, shell, ping, setup.")
    module_args: str = Field("", description="Arguments passed to the module.")
    limit: str = Field("", description="Optional host pattern to limit the run to.")


class AdHocCommand(sdl.Entity):
    title: str = ""
    id: int
    status: str
    module_name: str = ""


class ListAdHocCommandsParams(_ConnScopedParams):
    limit: int = Field(50, ge=1, le=200)


class AdHocCommandList(sdl.Entity):
    id: str = ""
    title: str = ""
    items: list[AdHocCommand]


# ──────────────────────────────────────────────────────────────────────────
# Notification Templates
# ──────────────────────────────────────────────────────────────────────────


class NotificationTemplate(sdl.Entity):
    title: str = ""
    id: int
    name: str
    notification_type: str = ""


class NotificationTemplateList(sdl.Entity):
    id: str = ""
    title: str = ""
    items: list[NotificationTemplate]


class ListNotificationTemplatesParams(_ConnScopedParams):
    pass


class CreateNotificationTemplateParams(_ConnScopedParams):
    name: str = Field(..., description="Notification template name.")
    organization: int = Field(..., description="Organization id.")
    notification_type: str = Field(..., description="e.g. slack, email, webhook, pagerduty.")
    notification_configuration_json: str = Field(..., description="Notification config as a JSON object string (fields depend on notification_type).")


class DeleteNotificationTemplateParams(_IdParams):
    pass


class TestNotificationTemplateParams(_IdParams):
    pass


# ──────────────────────────────────────────────────────────────────────────
# Instances / Instance Groups (execution mesh)
# ──────────────────────────────────────────────────────────────────────────


class Instance(sdl.Entity):
    title: str = ""
    id: int
    hostname: str
    node_type: str = ""
    capacity: int = 0
    enabled: bool = True


class InstanceList(sdl.Entity):
    id: str = ""
    title: str = ""
    items: list[Instance]


class ListInstancesParams(_ConnScopedParams):
    pass


class InstanceGroup(sdl.Entity):
    title: str = ""
    id: int
    name: str
    capacity: int = 0


class InstanceGroupList(sdl.Entity):
    id: str = ""
    title: str = ""
    items: list[InstanceGroup]


class ListInstanceGroupsParams(_ConnScopedParams):
    pass


# ──────────────────────────────────────────────────────────────────────────
# Execution Environments
# ──────────────────────────────────────────────────────────────────────────


class ExecutionEnvironment(sdl.Entity):
    title: str = ""
    id: int
    name: str
    image: str = ""


class ExecutionEnvironmentList(sdl.Entity):
    id: str = ""
    title: str = ""
    items: list[ExecutionEnvironment]


class ListExecutionEnvironmentsParams(_ConnScopedParams):
    pass


# ──────────────────────────────────────────────────────────────────────────
# Activity Stream / Audit (value-add Tier 3)
# ──────────────────────────────────────────────────────────────────────────


class ActivityStreamEntry(sdl.Entity):
    title: str = ""
    id: int
    operation: str
    changes: str = ""
    timestamp: str = ""
    actor: str = ""


class ActivityStreamList(sdl.Entity):
    id: str = ""
    title: str = ""
    items: list[ActivityStreamEntry]


class ListActivityStreamParams(_ConnScopedParams):
    limit: int = Field(50, ge=1, le=200)


# ──────────────────────────────────────────────────────────────────────────
# Value-add: audit report + bulk helpers
# ──────────────────────────────────────────────────────────────────────────


class AuditControllerParams(_ConnScopedParams):
    pass


class AuditRow(sdl.Entity):
    id: str = ""
    title: str = ""
    job_template_name: str
    last_status: str
    failure_rate_pct: float = 0.0
    total_runs: int = 0


class AuditControllerReport(sdl.Entity):
    id: str = ""
    title: str = ""
    generated_at: str
    rows: list[AuditRow]
    running_jobs: int = 0
    failed_jobs_24h: int = 0
