"""Entrypoint for the web-kernel and CLI tools (imperal validate/build).

Sets up sys.path, purges stale module cache, then imports ext/chat and all
handler modules so their decorators register on the same Extension instance
-- same pattern as UiPath Connector's / Blue Prism Connector's main.py.
"""

import os
import sys

_EXT_DIR = os.path.dirname(os.path.abspath(__file__))
if _EXT_DIR not in sys.path:
    sys.path.insert(0, _EXT_DIR)

_LOCAL = (
    "app", "schemas", "ansible_client",
    "handlers_connection", "handlers_job_templates", "handlers_jobs",
    "handlers_workflows", "handlers_projects_inventories",
    "handlers_credentials", "handlers_schedules", "handlers_orgs_users",
    "handlers_adhoc_notifications", "handlers_infra", "handlers_audit",
    "panels", "panels_settings",
)
for _mod in _LOCAL:
    sys.modules.pop(_mod, None)

from app import ext, chat  # noqa: E402,F401
import handlers_connection  # noqa: E402,F401
import handlers_job_templates  # noqa: E402,F401
import handlers_jobs  # noqa: E402,F401
import handlers_workflows  # noqa: E402,F401
import handlers_projects_inventories  # noqa: E402,F401
import handlers_credentials  # noqa: E402,F401
import handlers_schedules  # noqa: E402,F401
import handlers_orgs_users  # noqa: E402,F401
import handlers_adhoc_notifications  # noqa: E402,F401
import handlers_infra  # noqa: E402,F401
import handlers_audit  # noqa: E402,F401
import panels  # noqa: E402,F401
import panels_settings  # noqa: E402,F401
