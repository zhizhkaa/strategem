# Стратегема

Веб-приложение для проведения учебной стратегической игры. Проект разработан на **Django 5.2**. Фронтенд использует **Django Templates**, **Alpine.js** и **Tailwind CSS**. Для продакшена подготовлена Docker Compose-схема с **PostgreSQL**, **Gunicorn**, **nginx** и **certbot**. Для офлайн-режима предусмотрена Windows-сборка в один `.exe` файл через **PyInstaller**.

## Содержание

- [Требования](#требования)
- [Быстрый старт](#быстрый-старт)
- [Основные страницы](#основные-страницы)
- [Сборка проекта](#сборка-проекта)
- [Тесты](#тесты)
- [Архитектура проекта](#архитектура-проекта)
- [Модели данных](#модели-данных)
- [Конфигурация игры](#конфигурация-игры)
- [Расчётный движок](#расчётный-движок)
- [API](#api)
- [Фронтенд](#фронтенд)
- [Экспорт игр](#экспорт-игр)
- [Работа с документами](#работа-с-документами)
- [Переменные окружения](#переменные-окружения)

## Требования

- **Python 3.12**
- **Node.js 22** или выше
- **npm**
- **SQLite** для локальной разработки
- **PostgreSQL** для продакшена

## Быстрый старт

Склонируйте репозиторий:

```bash
git clone https://github.com/zhizhkaa/strategem.git
```

Создайте виртуальное окружение:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Установите Python-зависимости:

```bash
pip install -r requirements.txt
```

Соберите фронтенд:

```bash
cd frontend
npm ci
npm run build
cd ..
```

Создайте `.env` из примера:

```bash
cp env.example .env
```

Для локального запуска на SQLite удалите или закомментируйте в `.env` переменные `POSTGRES_DB`, `POSTGRES_USER` и `POSTGRES_PASSWORD`. Минимальный локальный `.env`:

```dotenv
SECRET_KEY=local-development-key
DEBUG=True
```

Если `POSTGRES_DB` не задан, Django использует SQLite-базу `backend/data/db.sqlite3`. Загруженные файлы по умолчанию лежат в `backend/media`. Запустите проект:

```bash
cd backend
python manage.py migrate
python manage.py runserver
```

## Основные страницы

- `/` — выбор команды.
- `/game/` — основной экран игры.
- `/admin-login/` — авторизация в панели администратора.
- `/admin-panel/` — панель администратора.
- `/api/docs/` — Swagger UI, доступен после входа администратором.

## Сборка проекта

### Фронтенд-статика

```bash
cd frontend
npm ci
npm run build
```

Команда `npm run build` копирует локальные browser-зависимости в `frontend/static/vendor` и собирает Tailwind CSS в `frontend/static/css/tailwind.css`.

### Локальный Django

```bash
source .venv/bin/activate
cd backend
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py check
python manage.py runserver
```

`collectstatic` складывает продакшен-статику в `backend/staticfiles`.

### Docker Compose

Заполните `.env` для сервера:

```dotenv
SECRET_KEY=long-random-secret
DEBUG=False
ADMIN_PASSWORD=strong-admin-password
DOMAIN=example.com
ALLOWED_HOSTS=example.com,www.example.com
LETSENCRYPT_EMAIL=admin@example.com
POSTGRES_DB=strategem
POSTGRES_USER=strategem
POSTGRES_PASSWORD=strong-postgres-password
```

Соберите и запустите контейнеры:

```bash
docker compose build web
docker compose up -d db
docker compose up -d web nginx certbot
docker compose exec web python manage.py migrate --noinput
docker compose exec web python manage.py collectstatic --noinput --clear
docker compose exec web python manage.py check --deploy
```

Сервисы:

- `web` — Django под Gunicorn на `8000`.
- `db` — PostgreSQL 16.
- `nginx` — обратный прокси на Django, отдача `/static/` и `/media/`.
- `certbot` — обновление сертификатов.

### GitHub Actions

`.github/workflows/deploy.yml` деплоит `main` на VPS через SSH, пересобирает `web`, применяет миграции, собирает статику и перезапускает nginx. `.github/workflows/windows-portable.yml` собирает `.exe` вручную через `workflow_dispatch` или по тегам `v*` и `windows-*`, затем публикует файл в GitHub Release.

### Windows portable

Офлайн-сборка создаёт файл `dist/Strategem-Windows/Strategem.exe`. Сборка Windows `.exe` должна выполняться в Windows-среде, потому что PyInstaller не кросс-компилирует `.exe` на macOS.

```powershell
cd frontend
npm ci
npm run build
cd ..
.\scripts\windows\build-portable.ps1
```

Скрипт проверяет наличие собранной статики, копирует `backend` и `frontend` во временную staging-директорию, ставит зависимости в отдельный venv и собирает `Strategem.exe` через **PyInstaller**. При запуске `Strategem.exe` применяются миграции, стартует локальный Django `runserver` на `127.0.0.1:8000`, браузер открывает главную страницу, данные хранятся в `%LOCALAPPDATA%\Strategem`, если не задан `STRATEGEM_RUNTIME_DIR`. Порт Windows portable launcher можно переопределить через `STRATEGEM_PORT`.

## Тесты

```bash
cd backend
python manage.py test apps.game.tests apps.management.tests
```

Текущие тестовые зоны:

- `backend/apps/game/tests.py` — API игры, игровые расчёты, конфигурация, документы и Excel-экспорт.
- `backend/apps/management/tests.py` — факультеты, группы, команды и management API.

## Архитектура проекта

```text
.
├── backend/                    # Django-проект и приложения
│   ├── manage.py
│   ├── strategem/              # настройки, ASGI/WSGI, корневые URL
│   └── apps/
│       ├── game/               # игровая логика, API, расчёты
│       └── management/         # управление командами
├── frontend/                   # шаблоны, JS, CSS
│   ├── templates/
│   ├── static/
│   ├── styles/
│   └── scripts/
├── nginx/                      # nginx template для Docker-продакшена
├── scripts/windows/            # PyInstaller-сборка и launcher
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── env.example
```

## Модели данных

### `apps.management.models`

`Faculty` — факультет. Поле `name` уникально. `Group` — учебная группа. Связана с `Faculty`, содержит `year`. Уникальность: `name + faculty + year`. `Team` — команда. Связана с `Group`, содержит `access_password`. При сохранении обычный пароль автоматически хешируется.

Методы `Team`:

- `access_password_is_hashed()` — проверяет, что пароль уже в Django hash format.
- `set_access_password(raw_password)` — хеширует пароль.
- `check_access_password(raw_password)` — проверяет введённый пароль.
- `save()` — хеширует нехешированный пароль перед сохранением.

### `apps.game.models`

`GameStatus` — статусы игры: `created`, `active`, `finished`, `paused`. `GameDifficulty` — профили сложности: `simple`, `standard`, `tough`, `veryhard`, `higheq`. `Game` — одна игра для одной команды. Хранит статус, текущий период, количество периодов, сложность, уровни принятых решений, архивирование и снимок YAML-конфигурации.

Методы `Game`:

- `clean()` — проверяет допустимое число периодов и текущий период.
- `reset_decisions()` — сбрасывает прогресс решений на новый период.
- `get_decision_states()` / `set_decision_states()` — сериализует и восстанавливает прогресс решений.
- `get_current_period_obj()` — возвращает или создаёт текущий `GamePeriod`.
- `get_history()` — возвращает параметры предыдущих периодов.
- `can_advance_period()` — проверяет, приняты ли обязательные решения.
- `advance_period()` — рассчитывает следующий период, создаёт новый `GamePeriod`, сбрасывает решения или завершает игру.

`GamePeriod` — снимок игровых параметров за период. Хранит поля `P*`, `E*`, `G*`, `F*`, `TF*`, список `user_inputs` и `validation_state`.

Методы `GamePeriod`:

- `get_parameters()` — собирает параметры в словарь.
- `set_parameters(params)` — записывает словарь в поля модели.
- `set_parameter(param_name, value, mark_as_user_input=True)` — меняет один параметр.
- `is_user_input(param_name)` — проверяет, вводил ли параметр пользователь.
- `mark_as_user_input(param_name)` — помечает параметр как введённый.
- `get_parameter(param_name)` — читает один параметр.

`Document` — загруженный PDF-документ для игроков. Поддерживает общий scope и scope министра. `ConfigFile` — переопределение встроенного YAML-файла через админку. Хранит имя файла, содержимое и версию. `GlobalGameSettings` — singleton-настройки игрового процесса.

Поля и методы `GlobalGameSettings`:

- `use_team_passwords` — включает пароли команд.
- `auto_calculate_decision_residuals` — включает авторасчёт остаточных параметров.
- `parallel_decision_mode` — включает параллельный режим решений.
- `get_solo()` — возвращает или создаёт singleton-запись.

## Конфигурация игры

Конфигурационные YAML-файлы лежат в `backend/apps/game/data`. `parameters.yaml` — описание всех параметров: дефолты, названия, категории, признак пользовательского ввода, границы и зависимости. `decision_order.yaml` — этапы принятия решений, министры, порядок, зависимости, поля ввода, operator-controlled параметры и режимы. `formulas.yaml` — формулы расчёта следующего периода и формулы текущих решений. `difficulties.yaml` — профили начальных значений и метаданные сложности. `interpolation.yaml` — таблицы линейной интерполяции.

Режимы `decision_order.yaml`:

- `parallel_mode` — разрешить ли все этапы одновременно.
- `auto_calculate_decision_residuals` — считать ли остаточные decision-поля автоматически.

Формулы поддерживают функции `min`, `max`, `round`, `interpolate`, `mean` и `prev`.

### Работа с конфигурациями

`backend/apps/game/configuration.py`

Основные методы:

- `get_builtin_config_contents()` — читает встроенные YAML.
- `get_active_config_contents()` — накладывает DB-переопределения.
- `get_game_config_snapshot()` — готовит снимок для новой игры.
- `get_config_label()` — строит подпись версии конфигурации.
- `apply_runtime_settings()` — применяет runtime-настройки к `decision_order`.
- `config_data_from_snapshot()` — парсит снимок игры.
- `get_calculator_for_game(game)` — возвращает калькулятор с конфигом игры.
- `get_state_manager_for_game(game)` — возвращает state manager с конфигом игры.
- `bump_or_create_config(filename, content)` — создаёт или версионирует переопределённый YAML.

## Расчётный движок

### Расчёты игры: `backend/apps/game/engine/calculator.py`

`GameCalculator` загружает YAML-конфигурацию и отвечает за расчёты.

Основные методы:

- `reload_config()` — перечитать YAML и таблицы интерполяции.
- `get_calculation_order()` — порядок групп расчёта из `decision_order.yaml`.
- `get_decision_stages()` — этапы принятия решений.
- `calculate_next_period(current_params, history, recalculate_decisions=True)` — расчёт параметров следующего периода.
- `apply_decision_formulas(params, history, parameter_names=None)` — пересчёт формул блока `decisions`.
- `get_decision_residual_errors(...)` — ошибки по остаточным балансам.
- `apply_decision(...)` — применить decision-формулы для этапа.
- `validate_input(...)` — проверить ввод пользователя.
- `get_parameter_bounds(params, param_name, history)` — динамические границы параметра.
- `evaluate_with_substitution(...)` и `get_calculations_detail(...)` — детали расчётов для UI и отладки.
- `get_initial_parameters(difficulty)` — стартовые параметры сложности.
- `get_input_parameters()` — список пользовательских input-параметров.

### Состояние игры: `backend/apps/game/engine/state_manager.py`

`DecisionState` хранит уровни решений по категориям `capital`, `energy`, `finance`, `import`. `GameStateManager` определяет, что доступно пользователю сейчас.

Основные методы:

- `get_full_state(...)` — полное состояние для UI.
- `get_batch_processing_order(param_names)` — порядок пакетного сохранения.
- `is_operator_controlled_param(param_name)` — проверяет, заполняет ли параметр оператор.
- `get_operator_controlled_params()` — возвращает все operator-controlled параметры.
- `get_param_to_minister_map()` — возвращает соответствие параметра министру.
- `get_all_input_params()` — возвращает все вводимые параметры.
- `set_parameter(...)` — устанавливает значение, валидирует ввод, запускает авторасчёты и обновляет decision state.

### Интерполяции и валидация формул

`backend/apps/game/engine/interpolation.py` `Interpolator` читает `interpolation.yaml` и выполняет линейную интерполяцию. Основные методы: `get_table_names()`, `get_table(name)`, `get_all_tables()`, `interpolate(table_name, x)`, `interpolate_with_bounds(...)`.

`backend/apps/game/engine/validator.py` `FormulaValidator` проверяет формулы и выражения. Внешние функции: `get_validator()`, `validate_formulas()`, `validate_expression(expression)`.

## API

Основной API доступен по `/api/`.

ViewSets:

- `/api/faculties/` — факультеты.
- `/api/groups/` — группы, поддерживает фильтр `?faculty=<id>`.
- `/api/teams/` — команды, поддерживает фильтр `?group=<id>`.
- `/api/games/` — игры.

Дополнительные действия игры:

- `GET /api/games/<id>/state/` — полное состояние для UI.
- `GET /api/games/<id>/calculations/` — детали расчётов.
- `POST /api/games/<id>/next-period/` — переход к следующему периоду.
- `POST /api/games/<id>/pause/` — пауза.
- `POST /api/games/<id>/resume/` — продолжить.
- `GET /api/games/<id>/periods/` — периоды игры.
- `POST /api/games/<id>/validate-period/` — валидация текущего периода.
- `GET /api/games/interpolation-tables/` — таблицы интерполяции.
- `GET /api/games/decision-structure/` — структура решений для UI.
- `GET /api/games/<id>/charts/` — данные графиков.
- `GET /api/games/<id>/parameter-history/<param>/` — история параметра.
- `GET /api/games/<id>/export/excel/` — Excel-экспорт игры.
- `POST /api/games/<id>/archive/` и `/unarchive/` — архивирование.

Параметры:

- `GET /api/games/<game_id>/parameters/<param>/` — текущее значение, метаданные, границы и статус.
- `POST /api/games/<game_id>/parameters/<param>/` — установить один параметр.
- `POST /api/games/<game_id>/parameters/batch/` — пакетное сохранение.
- `GET /api/games/<game_id>/validation/` — сохранённое состояние валидации для polling на фронтенде.

Админские эндпоинты:

- `POST /api/admin/login/` — создать админ-сессию по `ADMIN_PASSWORD`.
- `POST /api/admin/logout/` — выйти.
- `GET /api/admin/check/` — проверить сессию.
- `GET/PATCH /api/admin/settings/` — глобальные настройки игры.
- `GET /api/admin/config-files/` — список YAML-файлов.
- `GET/PATCH /api/admin/config-files/<filename>/` — чтение и запись YAML.
- `POST /api/admin/config-files/<filename>/validate/` — валидация YAML.
- `POST /api/admin/config-files/<filename>/reset/` — сброс к встроенному YAML.
- `GET /api/groups/<group_id>/export/excel/` — Excel-экспорт группы.
- `GET/POST /api/documents/` — список и загрузка документов.
- `GET /api/documents/<id>/download/` — скачать документ.
- `DELETE /api/documents/<id>/` — удалить документ.

Отдельный `/api/management/` подключает `apps.management.views`. Это простой CRUD для факультетов, групп и команд. В основном UI используется API из `apps.game.views.management`, потому что там есть проверки админ-сессии, фильтрация и расширенные сериализаторы.

## Фронтенд

Шаблоны лежат в `frontend/templates`:

- `base.html` — общий layout.
- `index.html` — выбор команды.
- `game/play.html` — основной игровой экран.
- `game/minister.html` — экран министра.
- `game/review.html` — сводный экран решений.
- `game/charts.html` — графики.
- `game/results.html` — результаты.
- `game/status.html` — состояние страны из админки.
- `game/docs.html` — документы игроков.
- `admin/login.html` — вход оператора.
- `admin/panel.html` — панель оператора.
- `admin/config-editor.html` — YAML-редактор.
- `admin/calculator.html` — отладочный калькулятор.

JavaScript лежит в `frontend/static/js`:

- `app.js` — общие helpers.
- `i18n.js` — текстовые и локализационные helpers.
- `pages/team-selection.js` — выбор команды и вход.
- `pages/game-play.js` — основной игровой UI.
- `pages/minister.js` — лист решений министра.
- `pages/status.js` — состояние страны.
- `pages/charts.js` — Chart.js-графики.
- `pages/results.js` — результаты.
- `pages/docs.js` — документы и pdf.js.
- `pages/admin-login.js` — вход оператора.
- `pages/admin-panel.js` — админ-панель.
- `pages/admin-config-editor.js` — YAML-редактор.
- `pages/calculator.js` — отладочный калькулятор.

CSS:

- `frontend/styles/tailwind.css` — исходник Tailwind.
- `frontend/static/css/tailwind.css` — собранный Tailwind.
- `frontend/static/css/main.css` — дополнительный CSS.

Встроенные PDF-документы игроков описаны в `backend/apps/game/player_documents.py`. Файлы встроенных PDF-документов лежат в `frontend/static/docs/players`.

## Экспорт игр

`backend/apps/game/exports.py` строит Excel-отчёты через **openpyxl**.

Основные функции:

- `build_export_context(game)` — нормализованные данные игры.
- `build_results_xlsx(game)` — подробный Excel по игре.
- `build_group_results_xlsx(group)` — Excel по группе.

## Работа с документами

`DocumentView`, `DocumentDownloadView` и `DocumentDeleteView` находятся в `backend/apps/game/views/admin.py`. API объединяет встроенные PDF-слоты и загруженные оператором документы.

## Переменные окружения

- `SECRET_KEY` — обязательный Django secret key.
- `DEBUG` — `True` для разработки, `False` для продакшена.
- `ADMIN_PASSWORD` — пароль оператора для `/admin-login/`.
- `DOMAIN` — домен для CORS, CSRF, nginx и HTTPS.
- `ALLOWED_HOSTS` — дополнительный список хостов через запятую.
- `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`, `POSTGRES_PORT` — настройки PostgreSQL.
- `STRATEGEM_DATA_DIR` — директория SQLite-базы в локальном и portable режиме.
- `STRATEGEM_MEDIA_DIR` — директория загруженных файлов.
- `STRATEGEM_RUNTIME_DIR` — runtime-директория Windows portable.
- `STRATEGEM_PORT` — порт Windows portable launcher.
