# Ansible Automation Platform Connector — идеальный первый запуск

Источник: `ONBOARDING_FIRST_LAUNCH_STANDARD.md`. Целевой пользователь: DevOps/
инфраструктурный инженер, использующий AWX/Tower.

## 1. Credential type
Self-hosted API key: `api_base_url` (произвольный URL) + `token`. Класс
"self-hosted + token" — требует SSRF-защиты base_url (см. `APP_SAFETY_CHECKLIST.md`).

## 2. Идеальный флоу
1. **Первое открытие** — `Empty` с объяснением, что нужен URL СВОЕГО AWX/Controller +
   Personal Access Token оттуда (Settings > Users > Tokens), с примером формата URL.
2. **Форма** — `api_base_url` (placeholder показывает оба варианта: AWX и AAP Controller
   URL-схему, т.к. они отличаются — `/api/v2` vs `/api/controller/v2`) + token
   (password-type).
3. **Валидация base_url на лету** — идеально: клиентская проверка, что введён https://
   и похоже на валидный AWX endpoint, ДО отправки — не дожидаться сетевой ошибки.
4. **После успеха** — сводка недавних job-запусков (успех/провал/хост) сразу.
5. **Ошибка "SSL certificate verify failed"** — частый кейс для self-hosted инсталляций
   с самоподписанным сертификатом — конкретное сообщение об этом классе ошибки (не
   "не удалось подключиться"), т.к. решение (добавить сертификат в доверенные) отличается
   от решения при обычном таймауте.
6. **Ошибка недоступности хоста (DNS/connection refused)** — self-hosted инстанс может
   быть недоступен из интернета (внутренняя сеть без VPN) — конкретное объяснение этого
   класса, отличное от "неверный токен".

## 3. Разница с реализацией сейчас
См. `UI_COMPONENT_PLAN.md` §0.
