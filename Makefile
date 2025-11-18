.PHONY: install check-venv run migrate migrations help test

install:
	@if [ ! -d ".venv" ]; then \
		echo "Создание виртуального окружения..."; \
		python3 -m venv .venv; \
	fi
	@echo "Обновление PIP..."
	@.venv/bin/pip install --upgrade pip
	@echo "Установка зависимостей..."
	@.venv/bin/pip install -r requirements.txt
	@echo "✓ Готово! Активируйте окружение: source .venv/bin/activate или make activate"

check-venv:
	@if [ ! -d ".venv" ]; then \
		echo "Ошибка: виртуальное окружение не найдено"; \
		echo "Выполните: make install"; \
		exit 1; \
	fi

run: check-venv
	.venv/bin/python backend/manage.py runserver

migrate: check-venv
	.venv/bin/python backend/manage.py migrate

migrations: check-venv
	.venv/bin/python backend/manage.py makemigrations

shell: check-venv
	.venv/bin/python backend/manage.py shell



clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +

help:
	@echo "Доступные команды:"
	@echo "  make help          - Показать это сообщение"
	@echo "  make install       - Установить зависимости"
	@echo "  make run           - Запустить dev сервер"
	@echo "  make migrate       - Применить миграции"
	@echo "  make migrations    - Создать миграции"
	@echo "  make shell         - Открыть Django shell"
	@echo "  make clean         - Очистить кеш и временные файлы"
