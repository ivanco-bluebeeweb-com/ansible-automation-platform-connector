# Ansible Automation Platform (Controller/AWX) Connector — Connector Discovery

**Дата discovery:** 2026-08-21
**Статус:** Ярусы 1-3 пройдены (свежее чтение официальной документации docs.ansible.com/projects/awx, docs.redhat.com/.../red_hat_ansible_automation_platform, GitHub ansible/awx, 2026-08-21).
**Объём этого захода:** максимум (Ярус 1 + 2 + 3) — заявлено Владом явно в первом сообщении по этому коннектору («делай это приложение в максимальной комплектации с максимумальным функционалом»), Шаг 5 стандарта не требует переспроса (см. §6).

---

## 1. Целевой сервис и источники

Red Hat Ansible Automation Platform (AAP) — коммерческий enterprise-продукт Red Hat поверх open-source **AWX**. Основной операционный домен — **Automation Controller** (бывший Ansible Tower) — agentless configuration-management/orchestration слой: playbooks, инвентари хостов, job templates, workflows. REST API Automation Controller идентичен по форме API AWX (`/api/v2/...`), что подтверждено официальной документацией.

Источники (прочитаны 2026-08-21):
- `docs.ansible.com/projects/awx/en/latest/rest_api/` — REST API overview, authentication, api_ref
- `docs.ansible.com/projects/awx/en/latest/open_api/` — полная OpenAPI-схема v2
- `docs.ansible.com/projects/awx/en/24.6.1/administration/oauth2_token_auth.html` — OAuth2 Applications/Tokens
- `docs.redhat.com/.../red_hat_ansible_automation_platform/2.5/.../ref-aap-components` — компонентная модель AAP 2.x
- `docs.redhat.com/.../2.7/assembly_upgrade_api_changes`, `.../secure-mandatory_platform_gateway_authentication_in_ansible_automation_platform_2_7` — Platform Gateway с версии 2.5+/2.7 (изменения в маршрутизации API)
- `github.com/ansible/awx/blob/devel/awxkit/awxkit/api/pages/api.py`, `github.com/ansible/awx/blob/devel/docs/named_url.md` — полный перечень top-level ресурсов API v2

## 2. Версионный разброс — критично

С AAP 2.5+ введён единый **Platform Gateway**; с AAP 2.7 прямой доступ к API отдельных компонентов (Controller/Hub/EDA) через их собственные hostname полностью убран — всё идёт через gateway с единой аутентификацией по пути `/api/controller/v2/...`. Для community AWX и более старых AAP/Tower (<2.5) путь прежний: `/api/v2/...` напрямую на контроллере.

**Решение:** коннектор просит пользователя явно указать **Base URL** (полный, включая версионный сегмент пути — `.../api/controller/v2` ИЛИ `.../api/v2`), а не собирает его из домена автоматически. Это тот же паттерн, что уже используется для MuleSoft/Blue Prism при похожем версионном/топологическом разбросе.

Три домена AAP 2.x:
- **Automation Execution** (Controller) — job templates, projects, inventories, credentials, jobs, schedules, workflows. **Это цель коннектора.**
- **Automation Content** (Hub) — Galaxy-style реестр коллекций/ролей. Вне охвата этого захода (отдельный API, отдельная будущая заявка).
- **Automation Decisions** (Event-Driven Ansible) — rulebooks. Вне охвата этого захода.

## 3. Аутентификация

Automation Controller API поддерживает:
- **OAuth2 Personal Access Token** (`/api/v2/users/<id>/personal_tokens/` или через `/api/v2/tokens/`) — рекомендуемый способ для скриптовых/сервисных интеграций, токен передаётся как `Authorization: Bearer <token>`.
- **OAuth2 Application + Token** (`/api/v2/applications/`) — client_credentials/password grant для более формального API-клиента.
- **HTTP Basic Auth** — username/password напрямую, поддерживается, но не рекомендуется для постоянной интеграции.

**Решение:** BYOK — пользователь подключает через Base URL + Personal Access Token (Bearer). Basic Auth как явный fallback-режим для сред, где PAT недоступен (старые Tower). Тот же принцип, что и во всех остальных RPA/оркестрационных коннекторах портфеля (UiPath/Blue Prism/Automation Anywhere/MuleSoft) — учётные данные остаются в инфраструктуре пользователя, Imperal не централизует доступ.

## 4. Карта возможностей (направление на каждую)

| Возможность сервиса | Ingress/Egress/Both | Комментарий |
|---|---|---|
| Organizations — list/get/create/update/delete | Both | Верхнеуровневая единица RBAC |
| Users — list/get/create/update/delete | Both | Управление аккаунтами Controller |
| Teams — list/get/create/update/delete, team↔user membership | Both | Группы доступа |
| Roles (RBAC) — list, assign/remove роль на объект | Both | Права доступа на organizations/inventories/job templates |
| Projects (SCM: Git/SVN/manual) — list/get/create/update/delete, sync (project_update) | Both | Источник playbooks |
| Project Updates (SCM sync jobs) — list/get, cancel | Ingress+Egress | Статус синка проекта с репозиторием |
| Inventories — list/get/create/update/delete | Both | Наборы управляемых хостов |
| Hosts — list/get/create/update/delete, enable/disable | Both | Отдельные управляемые машины |
| Groups — list/get/create/update/delete, host↔group | Both | Группировка хостов внутри inventory |
| Inventory Sources (dynamic inventory: AWS/Azure/GCP/etc) — list/get/create/update/delete, sync (inventory_update) | Both | Динамические источники хостов из облаков |
| Inventory Updates — list/get, cancel | Ingress+Egress | Статус синка динамического inventory |
| Credentials — list/get/create/update/delete | Both | Секреты для SSH/Cloud/Vault (значения секретов НЕ возвращаются обратно API — write-only поля) |
| Credential Types — list/get | Ingress | Схемы полей для кастомных типов credential |
| Job Templates — list/get/create/update/delete, launch | Both | Основная операционная единица — запуск playbook |
| Jobs (job runs) — list/get, cancel, relaunch, stdout/log, job_events | Both | Прогоны job templates |
| Workflow Job Templates — list/get/create/update/delete, launch | Both | Оркестрация цепочек job templates |
| Workflow Jobs — list/get, cancel, relaunch | Both | Прогоны workflow |
| Workflow Job Template Nodes — list/get/create/update/delete | Both | Узлы графа workflow (success/failure/always) |
| Workflow Approvals — list/get, approve/deny | Egress (решение) | Точки ручного апрува внутри workflow |
| Schedules — list/get/create/update/delete, enable/disable | Both | Периодический запуск job/workflow templates |
| Ad Hoc Commands — list/get, launch, cancel | Both | Разовая Ansible-команда на inventory без playbook |
| Notification Templates — list/get/create/update/delete, test | Both | Email/Slack/Webhook/PagerDuty-уведомления о статусе job |
| Notifications (sent) — list/get | Ingress | История отправленных уведомлений |
| Labels — list/get/create/delete | Both | Теги на job templates/jobs |
| Instance Groups — list/get | Ingress | Топология исполнителей (execution nodes) |
| Instances — list/get | Ingress | Отдельные execution/control/hybrid ноды |
| Execution Environments — list/get/create/update/delete | Both | Контейнерные образы окружения выполнения (замена venv, AWX ≥19) |
| Unified Jobs / Unified Job Templates | Ingress | Агрегированный список всех типов jobs/templates разом |
| Activity Stream | Ingred (аудит) | Лог всех изменений в системе |
| Settings | Ingress (read); update — намеренно вне охвата | Системные настройки Controller — риск неверной конфигурации всей платформы при записи |
| Metrics (Prometheus-формат) | Ingress | Метрики производительности Controller |
| Config/Ping (`/api/v2/ping/`, `/api/v2/config/`) | Ingress | Версия, статус кластера, лицензия |
| Mesh Visualizer / Topology | Ingress | Визуализация receptor mesh между нодами |

## 5. Ярус 1 — Ключевые функции (P0-кандидаты)

- Подключение (Base URL + Personal Access Token, health-check через `/api/v2/ping/`), список подключений, отключение
- Job Templates: list/get/create/update/delete, **launch** (главный операционный сценарий)
- Jobs: list/get, stdout/log, cancel, relaunch
- Projects: list/get/create/update/delete, sync (project_update), статус SCM
- Inventories: list/get/create/update/delete
- Hosts: list/get/create/update/delete
- Groups: list/get/create/update/delete
- Credentials: list/get/create/update/delete (без утечки секретных полей)
- Workflow Job Templates: list/get/create/update/delete, launch
- Workflow Jobs: list/get, cancel
- Schedules: list/get/create/update/delete
- Organizations: list/get
- Teams/Users: list/get

## 6. Ярус 2 — Полное покрытие

| Возможность | Статус | Причина/триггер |
|---|---|---|
| Inventory Sources + sync (dynamic inventory) | included | Прямой аналог динамических источников хостов из облаков — реальная ценность для DevOps-пользователя |
| Inventory Updates (list/get/cancel) | included | Статус синка динамического inventory |
| Credential Types (list/get) | included | Нужно для корректного создания Credentials с кастомными схемами полей |
| Ad Hoc Commands (list/get/launch/cancel) | included | Частый сценарий: разовая команда без playbook |
| Notification Templates (CRUD + test) | included | Управление уведомлениями о статусе jobs |
| Notifications (list/get, история отправленных) | included | Аудит уведомлений |
| Labels (CRUD) | included | Тегирование job templates/jobs |
| Workflow Job Template Nodes (CRUD) | included | Построение графа workflow программно |
| Workflow Approvals (list/get, approve/deny) | included | Точки ручного апрува — важный enterprise-сценарий |
| Roles (list, assign/remove) | included | RBAC-управление доступом к объектам |
| Organizations/Teams/Users (полный CRUD) | included | Административный слой — нужен для мультитенантных Controller-инсталляций |
| Execution Environments (CRUD) | included | Актуальная модель окружений выполнения (AWX ≥19, заменила venv) |
| Instance Groups / Instances (list/get) | included | Топология capacity — полезно для диагностики |
| Activity Stream (list) | included | Аудит изменений |
| Unified Jobs / Unified Job Templates (list) | included | Единая витрина по всем типам job |
| Metrics (Prometheus) | included | Здоровье/производительность Controller |
| Config/Ping | included | Версия/лицензия/статус для health-check и диагностики |
| Mesh Visualizer/Topology | deferred | Узкоспециализированная визуализация receptor mesh, низкая ценность как MCP-функция (граф, а не список) |
| Settings — запись/изменение системных настроек | not applicable | Слишком высокий риск неверной конфигурации всей Controller-инсталляции через MCP-вызов; чтение допустимо, запись исключена |

## 7. Ярус 3 — Функции на нашей стороне (value-add)

- **audit_controller_environment** — агрегированный отчёт здоровья: failed/error jobs за период, проекты с проваленным последним sync, inventory sources с ошибками, лицензионный статус — по аналогии с `audit_cloudhub_environment`/`audit_estate` у MuleSoft/Blue Prism/UiPath/Automation Anywhere.
- **bulk_cancel_jobs** — отмена нескольких запущенных jobs одним вызовом по явным id (аналог bulk_stop у остальных RPA-коннекторов).
- **bulk_launch_job_templates** — запуск нескольких job templates одним вызовом (по явным id), с агрегированным отчётом успех/ошибка на каждый.
- **get_stale_projects_report** — value-add отчёт: проекты, чей последний SCM sync провалился или устарел дольше заданного порога (аналог `get_stale_applications` у MuleSoft).
- **get_failed_jobs_report** — value-add отчёт: недавние failed/error jobs с job template/inventory/причиной, за выбранный период.

## 8. Решение по объёму этого захода

Максимум (Ярус 1 + 2 + 3). Основание: явное указание Влада в первом сообщении по этому коннектору — «делай это приложение в максимальной комплектации с максимумальным функционалом» — действует как уже данный ответ на Шаг 5 стандарта discovery (см. `CONNECTOR_DISCOVERY_STANDARD.md` §Шаг 5, «Исключение»). Переход сразу к Фазе 3 (Дизайн)/реализации без отдельного вопроса.
