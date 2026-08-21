"""Extension declaration, secrets, lifecycle hooks.

WHY BYOK (bring-your-own-key), same reasoning as UiPath Connector / Blue
Prism Connector / Automation Anywhere Connector / MuleSoft Connector.
Automation Controller (Ansible Automation Platform / AWX) lives inside the
USER'S OWN infrastructure -- Imperal cannot and should not broker access to
someone else's Controller instance centrally.

WHY A PERSONAL ACCESS TOKEN + FULL BASE URL, NOT OAUTH2 CLIENT CREDENTIALS.

See ansible_client.py's module docstring for the full architectural
reasoning (Controller's PAT model, and the AAP 2.5+/2.7 Platform Gateway
version/topology split documented in CONNECTOR_DISCOVERY.md that forces the
user to supply the exact base URL rather than have the connector guess it).

WHY `write_mode="both"`, SAME REASONING AS UiPath/Blue Prism/Automation
Anywhere/MuleSoft CONNECTOR.

Declaring `write_mode="user"` would mean only the platform's generic
Secrets screen could write these -- leaving a first-time user with no
in-app screen explaining what a Personal Access Token even is or how to
mint one. `"both"` keeps the generic Secrets screen as a fallback while
letting `connect_ansible` be the friendly guided path.

WHY SCOPE IS PER-ACCOUNT, NOT APP-LEVEL, SAME AS UiPath/Blue Prism/
Automation Anywhere/MuleSoft CONNECTOR.

Each user connects their OWN Controller instance -- these are not
developer-owned app credentials, so the connections secret is declared
per-account (default scope), not `scope="app"`.

WHY ONE SECRET HOLDING A JSON ARRAY, NOT FLAT SECRETS FOR "the" INSTANCE
(multi-instance support).

A user may run more than one Controller (e.g. staging AWX + production
AAP) -- same structural problem UiPath/Blue Prism/MuleSoft already solved
for multi-org/multi-estate/multi-environment setups. `ctx.secrets` only
supports a fixed, manifest-declared set of NAMES -- there is no "one
secret per connection_id" primitive. This connector follows the same
precedent: `ansible_connections` holds a JSON array of `{id, label,
api_base_url, token}` objects. `schemas.py`'s `connection_id` parameter on
every tool call addresses one specific entry in that array -- see
handlers_connection.py's `_load_connections`/`_save_connections` helpers.

SCOPE OF THIS RELEASE (Ярус 1 + 2 + 3, maximum functionality per explicit
instruction): Job Templates + Jobs (launch/monitor/cancel/relaunch/stdout/
events), Workflow Job Templates + Workflow Jobs (launch/monitor/nodes/
approvals), Projects (SCM-backed playbook repos, sync), Inventories + Hosts
+ Groups + Inventory Sources (sync), Credentials + Credential Types,
Schedules, Organizations/Teams/Users, Ad Hoc Commands, Notification
Templates (+ test), Instances/Instance Groups (execution capacity),
Execution Environments, Activity Stream (audit log), plus Imperal-side
value-add: bulk job actions and an aggregated Controller health/audit
report. Automation Hub (Galaxy-style content registry) and Event-Driven
Ansible (rulebooks) are explicitly OUT OF SCOPE for this release -- they
are separate AAP components with their own API surfaces (Automation
Content / Automation Decisions, per CONNECTOR_DISCOVERY.md's component
map), materially different from Automation Execution/Controller which this
connector targets, same boundary discipline as MuleSoft's Design Center
exclusion.
"""
from __future__ import annotations

from imperal_sdk import ChatExtension, Extension

ext = Extension(
    "ansible-automation-platform-connector",
    version="0.1.0",
    display_name="Ansible Automation Platform",
    description=(
        "Connect your own Ansible Automation Platform (Automation "
        "Controller) or open-source AWX instance to manage job templates, "
        "launch and monitor jobs, run workflows, manage projects/"
        "inventories/hosts/credentials/schedules, browse organizations/"
        "teams/users, run ad hoc commands, configure notifications, and "
        "audit your automation estate's health -- all from Imperal. Uses "
        "your own Controller Personal Access Token -- nothing is hosted "
        "or proxied by Imperal beyond the request itself. Note: this "
        "manages Automation Controller (Automation Execution) resources "
        "only; Automation Hub (content registry) and Event-Driven Ansible "
        "(rulebooks) are separate AAP components, out of scope."
    ),
    icon="icon.svg",
    capabilities=[
        "ansible:read",
        "ansible:write",
    ],
    actions_explicit=True,
    system=False,
)

chat = ChatExtension(
    ext,
    tool_name="ansible",
    description=(
        "Ansible Automation Platform Connector -- connect your own "
        "Automation Controller/AWX instance via a Personal Access Token, "
        "then list/launch/monitor job templates and jobs, manage "
        "workflows, projects, inventories, credentials, schedules, "
        "organizations/teams/users, run ad hoc commands, and audit your "
        "estate's health."
    ),
)

ext.secret(
    "ansible_connections",
    (
        "Your connected Ansible Automation Platform / AWX Controller "
        "instances -- stored as a JSON array, one entry per instance, "
        "each with its own api_base_url and Personal Access Token. "
        "Managed through connect_ansible / disconnect_ansible -- you "
        "should not need to edit this directly."
    ),
    required=True,
    write_mode="both",
    max_bytes=65536,
    rotation_hint_days=180,
)(lambda: None)


@ext.health_check
async def health_check(ctx) -> dict:
    """Fast configuration health; no third-party call -- just confirms at
    least one Controller connection is stored, same shape as UiPath/Blue
    Prism/MuleSoft Connector's health_check."""
    import json as _json
    raw = await ctx.secrets.get("ansible_connections")
    try:
        count = len(_json.loads(raw)) if raw else 0
    except Exception:
        count = 0
    return {
        "healthy": True,
        "detail": (
            f"{count} Controller instance(s) connected." if count
            else "Not connected yet -- run connect_ansible."
        ),
    }
