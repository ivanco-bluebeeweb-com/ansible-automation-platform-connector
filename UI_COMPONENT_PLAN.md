# Ansible Automation Platform Connector — UI component plan

Источники: `Docs/session-notes/UI_COMPONENT_VOCABULARY.md`, `UI_INTERFACE_STANDARD.md`,
`concepts/panels.md`. Основано на функционале `ansible-automation-platform-connector`.

## 1. Компоненты

| Экран | Примитивы | Почему именно эти |
|---|---|---|
| Sidebar (left) | `ui.Column`(align="start") + `ui.Text`(Controller URL) + `ui.Divider` + navigation `ui.ListItem`(Job Templates/Jobs/Inventories/Workflows) + `ui.Button`("App settings") | Без карточек по стандарту. |
| Job Template List (center, `center_overlay=True`) | `ui.Stats`(Running/Failed today/Instances online) + `ui.DataTable`(name, inventory, project; sortable) | `DataTable` — обзор доступных Job Templates. |
| Job List | `ui.Select`(param_name="status_filter") + `ui.DataTable`(template, status Badge successful/failed/running, started; sortable) | Табличная история/поток запусков playbook. |
| Job Detail | Back-button + `ui.KeyValue`(template/inventory/duration) + `ui.Code`(language="text", stdout, readonly) + `ui.Button`("Cancel") | `Code` — прямое попадание для ansible-playbook stdout (моноширинный вывод). |
| Job Events Timeline | `ui.Timeline`(play→task→host события, статус каждого) | `Timeline` отражает последовательность выполнения play/task/host. |
| Launch Job Dialog | `ui.Dialog`(title="Запустить job template?", content=`ui.TextArea`(param_name="extra_vars", placeholder="Extra vars (YAML/JSON)..."), confirm_label="Запустить") | Запуск с опциональными extra vars — явное подтверждение параметров. |
| Workflow Approval Queue | `ui.List`(pending approvals: workflow name, node name) + `ui.Row`(Button "Approve", "Deny") | Human-in-the-loop гейты workflow — простой список с точечными действиями. |
| Inventory/Host List | `ui.DataTable`(host, groups, enabled Badge; sortable) | Обзор хостов инвентаря. |
| Credential List | `ui.DataTable`(name, credential type — метаданные без значений) | Список credential-записей без утечки секретов. |
| App Settings | `ui.Accordion`([Connections+Disconnect, Controller URL/Token]) | Централизованные настройки по стандарту. |

## 2. User flow (валидно по panel lifecycle)

1. **SESSION INIT** → `__panel__aap_sidebar` рендерит Controller URL + разделы,
   `auto_action` открывает Job Template List.
2. Job Template List: клик на шаблон → Launch Job Dialog (extra vars) → confirm
   вызывает `launch_job_template` → `refresh_panels` на Job List.
3. Job List: клик на строку → Job Detail (тот же center handler, параметр
   `job_id`) → вкладка/секция "Events" переключает на Job Events Timeline
   (через `ui.Tabs` внутри Job Detail) → "Cancel" — прямой Call.
4. Workflow Approval Queue: "Approve"/"Deny" — прямые Call без Dialog (решение
   уже осознанное — сам список появления в очереди требует внимания пользователя).
5. App Settings — единственная точка входа через кнопку в сайдбаре.

## 3. Экраны (конкретно, по файлам `panels.py`)

1. `aap_sidebar` (`slot="left"`) — навигация, App settings button.
2. `aap_center` (`slot="center"`, `center_overlay=True`) — параметризован `view`
   (templates/jobs/job_detail/approvals/inventories/credentials).
3. `aap_settings` (`slot="center"`, `panels_settings.py`) — Accordion с
   Connections/Controller URL.
