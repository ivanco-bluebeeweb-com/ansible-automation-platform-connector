# Ansible Automation Platform (Controller/AWX) Connector — Preparation

**Статус:** Фаза 1 (Discovery + архитектурные решения) завершена. Влад
подтвердил объём релиза 2026-08-21 — «максимум» (Ярус 1+2+3), заявлено с
первого сообщения по этому коннектору.
**Владелец продукта:** vlad@bluebeeweb.com
**Дата подготовки:** 2026-08-21, v0.1
**Vikunja task:** #2224 (BBW Imperal Apps), [App Development].

**Почему сейчас:** Red Hat Ansible Automation Platform — доминирующий
enterprise-стандарт agentless configuration-management/orchestration
(playbooks, инвентари, job templates, workflows). Закрывает нишу DevOps/SRE
автоматизации инфраструктуры, которую не покрывает ни один из RPA-коннекторов
портфеля (UiPath/Blue Prism/Automation Anywhere — desktop/process RPA, не
config management). API идентичен по форме открытому AWX — зрелая, полностью
задокументированная поверхность.

---

## 1. Паспорт приложения

**Название в Marketplace (display_name): «Ansible Automation Platform»**.
Внутренний app_id/папка: `ansible-automation-platform-connector`.

**Ansible Automation Platform Connector** — коннектор к Automation Controller
(бывший Ansible Tower / open-source AWX) REST API v2. BYOK: пользователь
подключает свой собственный Controller instance через Base URL + Personal
Access Token (Bearer). Imperal ничего не хостит и не проксирует — все
job/playbook-исполнения происходят на инфраструктуре пользователя.

---

## 2. Ключевые факты об API (см. `CONNECTOR_DISCOVERY.md`)

### 2.1 Версионный/топологический разброс — Base URL обязателен явно

С AAP 2.5+ введён Platform Gateway; с AAP 2.7 прямой доступ к
Controller/Hub/EDA API отдельно от gateway убран — путь становится
`.../api/controller/v2/...`. Community AWX и старые Tower/AAP (<2.5)
используют прежний `.../api/v2/...`. Решение: пользователь указывает полный
Base URL (включая версионный сегмент), коннектор не собирает его сам —
тот же паттерн, что уже применён для MuleSoft/Blue Prism при похожем
топологическом разбросе.

### 2.2 Auth — Personal Access Token (Bearer)

Основной способ: OAuth2 Personal Access Token, передаётся как
`Authorization: Bearer <token>`. Пользователь создаёт токен в
Controller UI (Users → своя учётка → Tokens) или через
`/api/v2/users/<id>/personal_tokens/`. Basic Auth (username/password)
поддержан как явный fallback для очень старых Tower-инсталляций без PAT.

Требуемые поля от пользователя:
1. `base_url` — полный API base URL, например `https://aap.example.com/api/controller/v2` или `https://awx.example.com/api/v2`
2. `token` — Personal Access Token (Bearer)
3. `verify_ssl` (опционально, default true) — многие on-prem инсталляции с self-signed сертификатами
4. `label` (опционально) — поддержка нескольких Controller-инстансов в одном секрете

### 2.3 Ключевая операционная модель Controller

- **Job Template** → **Job** (запуск = "launch"). Job template ссылается на Project (SCM-репозиторий с playbooks) + Inventory (хосты) + Credential(s).
- **Workflow Job Template** → **Workflow Job** — цепочка job templates/approval nodes.
- **Inventory** содержит **Groups** и **Hosts**; может синхироваться из внешнего источника через **Inventory Source** (`update` endpoint — sync).
- **Project** синхронизируется из SCM (git/svn) через `update` endpoint — аналог `sync`.
- **Credential** — секреты Controller (SSH keys, Vault passwords, Cloud creds) — читаем метаданные, никогда не запрашиваем/не возвращаем сами секретные значения (аналог поведения `get_asset` у UiPath — credential asset никогда не отдаёт значение).
- **Ad Hoc Command** — разовая Ansible-команда без playbook (module + args) против инвентаря.
- **Workflow Approval** — узел workflow, ожидающий approve/deny от человека — здесь Webbee ТОЛЬКО читает статус и может approve/deny по явной команде, это named human action.

---

## 3. Решённые архитектурные вопросы

| # | Вопрос | Решение | Обоснование |
|---|---|---|---|
| 1 | BYOK или центральный брокер? | **BYOK** | Controller живёт в инфраструктуре пользователя (on-prem/private cloud), Imperal не хостит и не проксирует. |
| 2 | Auth механизм? | **Personal Access Token (Bearer)**, Basic Auth как fallback | Официально рекомендованный способ для скриптовых интеграций. |
| 3 | Какой API-домен основной? | **Automation Controller** (Automation Execution) | Ближайший операционный аналог "сценариев+запусков" из портфеля; Hub/EDA — вне охвата. |
| 4 | Base URL авто-детект или явный ввод? | **Явный ввод пользователем**, включая версионный сегмент пути | Разброс `/api/v2` vs `/api/controller/v2` между AWX/старым Tower и AAP 2.7+ gateway — нельзя гадать. |
| 5 | Возвращать значения Credential? | **Никогда** | Credential values в Controller самом по себе write-only через API; коннектор читает только метаданные (имя, тип, организация). |
| 6 | Workflow Approval — авто-approve? | **Нет, только явный вызов по запросу человека** | Named human approval gate, тот же принцип, что Salesforce `process_approval`. |
| 7 | Объём релиза? | **«Максимум» = Ярус 1+2+3** | Заявлено Владом с первого сообщения 2026-08-21. |
| 8 | Automation Hub / Event-Driven Ansible? | **Вне охвата этого захода**, задокументировано как отдельные будущие коннекторы | Отдельные API-поверхности, не Automation Execution. |

---

## 4. Функциональный охват («максимум» = Ярус 1+2+3)

### Ярус 1 (P0 — ключевые функции)
- `connect_ansible` (base_url, token, verify_ssl, label) — проверка (`GET /me/` или `/ping/`) + сохранение через `ctx.secrets`
- `disconnect_ansible`, `list_connections`
- `list_job_templates`, `get_job_template`, `launch_job_template`
- `list_jobs`, `get_job`, `get_job_stdout`, `cancel_job`
- `list_projects`, `get_project`, `sync_project` (update)
- `list_inventories`, `get_inventory`, `list_inventory_hosts`, `list_inventory_groups`
- `list_workflow_job_templates`, `get_workflow_job_template`, `launch_workflow_job_template`
- `list_workflow_jobs`, `get_workflow_job`

### Ярус 2 (полное покрытие Automation Execution)
- `create_job_template` / `update_job_template` / `delete_job_template`
- `create_project` / `update_project` / `delete_project`
- `create_inventory` / `update_inventory` / `delete_inventory`
- `create_host` / `update_host` / `delete_host`, `create_group` / `delete_group`
- `list_inventory_sources`, `sync_inventory_source`
- `list_credentials`, `get_credential` (метаданные, без значений), `list_credential_types`
- `list_organizations`, `get_organization`, `create_organization`
- `list_teams`, `list_users`, `get_user`
- `list_schedules`, `create_schedule`, `update_schedule`, `delete_schedule`
- `run_ad_hoc_command`, `get_ad_hoc_command`, `list_ad_hoc_commands`
- `list_workflow_approvals`, `approve_workflow_approval`, `deny_workflow_approval`
- `list_notification_templates`, `create_notification_template`
- `list_execution_environments`, `list_instance_groups`, `list_instances`
- `list_activity_stream`
- `get_config` / `ping` (версия, лицензия, статус)

### Ярус 3 (наш value-add)
- `audit_controller_environment` — агрегированный health-отчёт: failed/error jobs за период, проекты с проваленным sync, inventory sources с ошибками, лицензионный статус
- `bulk_cancel_jobs` — отмена нескольких запущенных jobs по explicit id
- `bulk_launch_job_templates` — запуск нескольких job templates одним вызовом с агрегированным отчётом
- `get_stale_projects_report` — проекты с проваленным/устаревшим SCM sync
- `get_failed_jobs_report` — недавние failed/error jobs с контекстом (template/inventory/причина)

---

## 5. Открытые вопросы для Влада

Нет открытых вопросов — объём релиза подтверждён 2026-08-21 («максимум»).

---

## 6. Журнал проверки дублей

`search_marketplace` по «Ansible»/«AWX»/«Automation Controller» — дублей не
найдено в существующем портфеле Imperal на момент 2026-08-21.
