"""
Административные views и вспомогательные API.

Включает:
- AdminLoginView, AdminLogoutView, AdminCheckView — аутентификация админа
- TeamGameView — получение игры команды
- DocumentView, DocumentDownloadView, DocumentDeleteView — управление документацией
"""

from typing import Any, cast

import yaml
from django.conf import settings
from django.http import FileResponse, HttpResponse
from django.shortcuts import render
from django.templatetags.static import static
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from django_ratelimit.decorators import ratelimit
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.management.models import Group, Team

from ..configuration import (
    CONFIG_FILENAMES,
    CONFIG_LABELS,
    apply_runtime_settings,
    bump_or_create_config,
    get_active_config_contents,
    get_calculator_for_game,
    get_config_label,
    get_state_manager_for_game,
    settings_payload,
)
from ..engine.validator import FormulaValidator
from ..exports import build_group_results_xlsx
from ..models import (
    ConfigFile,
    Document,
    Game,
    GamePeriod,
    GlobalGameSettings,
    read_builtin_config_file,
)
from ..player_documents import PLAYER_DOCUMENT_SLOT_BY_ID, PLAYER_DOCUMENT_SLOTS
from ..serializers import (
    AdminLoginSerializer,
    GameDetailSerializer,
)

DOCUMENT_MINISTERS = {
    "population",
    "energy",
    "industry",
    "agriculture",
    "trade_finance",
}


def _document_payload(request: Request, doc: Document) -> dict[str, Any]:
    filename = doc.file.name.split("/")[-1]
    slot_meta = PLAYER_DOCUMENT_SLOT_BY_ID.get(doc.slot or "")
    return {
        "id": doc.id,
        "slot": doc.slot,
        "title": slot_meta.title if slot_meta else doc.title,
        "scope": slot_meta.scope if slot_meta else doc.scope,
        "minister": slot_meta.minister if slot_meta else doc.minister,
        "url": request.build_absolute_uri(doc.file.url),
        "download_url": request.build_absolute_uri(
            f"/api/documents/{doc.id}/download/"
        ),
        "filename": filename,
        "uploaded_at": doc.uploaded_at.isoformat(),
        "is_builtin": slot_meta is not None,
        "uses_default_file": False,
        "order": slot_meta.order if slot_meta else 1000,
    }


def _builtin_document_payload(request: Request, slot) -> dict[str, Any]:
    file_url = request.build_absolute_uri(static(slot.static_path))
    return {
        "id": None,
        "slot": slot.slot,
        "title": slot.title,
        "scope": slot.scope,
        "minister": slot.minister,
        "url": file_url,
        "download_url": file_url,
        "filename": slot.filename,
        "uploaded_at": None,
        "is_builtin": True,
        "uses_default_file": True,
        "order": slot.order,
    }


def _is_truthy(value: str | None) -> bool:
    return str(value or "").lower() in {"1", "true", "yes", "on"}


def _is_pdf_upload(file) -> bool:
    filename = str(getattr(file, "name", "") or "").lower()
    content_type = str(getattr(file, "content_type", "") or "").lower()
    return filename.endswith(".pdf") and (
        not content_type or content_type == "application/pdf"
    )


class AdminLoginView(APIView):
    """View для входа администратора."""

    @extend_schema(
        summary="Вход администратора",
        description="Проверяет пароль и устанавливает сессию администратора",
        request=AdminLoginSerializer,
        responses={
            200: OpenApiResponse(description="Успешный вход"),
            401: OpenApiResponse(description="Неверный пароль"),
        },
    )
    @method_decorator(ratelimit(key='ip', rate='5/m', method='POST', block=True))
    def post(self, request: Request, *args, **kwargs) -> Response:
        """Выполняет вход администратора."""
        serializer = AdminLoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        validated_data = cast(dict[str, Any], serializer.validated_data)
        password = validated_data["password"]

        # Получаем пароль из настроек или используем значение по умолчанию
        admin_password = getattr(settings, "ADMIN_PASSWORD", "admin123")

        if password != admin_password:
            return Response(
                {"error": "Неверный пароль"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        # Устанавливаем сессию
        request.session["is_admin"] = True

        return Response(
            {
                "success": True,
                "message": "Вход выполнен успешно",
            }
        )


class AdminLogoutView(APIView):
    """View для выхода администратора."""

    @extend_schema(
        summary="Выход администратора",
        description="Завершает сессию администратора",
        responses={200: OpenApiResponse(description="Успешный выход")},
    )
    def post(self, request: Request) -> Response:
        """Выполняет выход администратора."""
        request.session["is_admin"] = False
        return Response(
            {
                "success": True,
                "message": "Выход выполнен успешно",
            }
        )


class AdminCheckView(APIView):
    """View для проверки прав администратора."""

    @extend_schema(
        summary="Проверка прав администратора",
        description="Проверяет, является ли текущий пользователь администратором",
        responses={
            200: OpenApiResponse(
                description="Информация о правах",
            )
        },
    )
    def get(self, request: Request) -> Response:
        """Проверяет права администратора."""
        is_admin = request.session.get("is_admin", False)
        return Response({"is_admin": is_admin})


class TeamGameView(APIView):
    """View для получения игры команды."""

    @extend_schema(
        summary="Игра команды",
        description="Возвращает активную игру команды или null если игры нет",
        responses={
            200: GameDetailSerializer,
            404: OpenApiResponse(description="Команда не найдена"),
        },
    )
    def _get_team(self, team_id: int) -> Team | None:
        try:
            return Team.objects.get(pk=team_id)
        except Team.DoesNotExist:
            return None

    def _game_response(self, team: Team) -> Response:
        if not hasattr(team, "game") or team.game is None:
            return Response({"game": None})

        serializer = GameDetailSerializer(team.game)
        return Response({"game": serializer.data})

    def get(self, request: Request, team_id: int) -> Response:
        """Возвращает игру команды для админа или уже авторизованной команды."""
        team = self._get_team(team_id)
        if team is None:
            return Response(
                {"error": "Команда не найдена"},
                status=status.HTTP_404_NOT_FOUND,
            )

        is_admin = request.session.get("is_admin", False)
        is_team_session = request.session.get("team_id") == team.id
        if not is_admin and not is_team_session:
            return Response(
                {"error": "Введите пароль команды"},
                status=status.HTTP_403_FORBIDDEN,
            )

        return self._game_response(team)

    def post(self, request: Request, team_id: int) -> Response:
        """Проверяет пароль команды и возвращает игру."""
        team = self._get_team(team_id)
        if team is None:
            return Response(
                {"error": "Команда не найдена"},
                status=status.HTTP_404_NOT_FOUND,
            )

        provided_password = str(request.data.get("password", ""))
        game_settings = GlobalGameSettings.get_solo()
        if (
            game_settings.use_team_passwords
            and team.access_password
            and not team.check_access_password(provided_password)
        ):
            return Response(
                {"error": "Неверный пароль команды"},
                status=status.HTTP_403_FORBIDDEN,
            )

        request.session["team_id"] = team.id
        return self._game_response(team)


class DocumentView(APIView):
    """
    Управление файлами документации.

    GET  /api/documents/         — список файлов
    POST /api/documents/         — загрузить файл (только admin)
    """

    def get(self, request: Request) -> Response:
        """Возвращает список документов."""
        scope = request.query_params.get("scope")
        minister = request.query_params.get("minister")
        include_builtin = _is_truthy(request.query_params.get("include_builtin"))

        qs = Document.objects.all()
        if scope:
            qs = qs.filter(scope=scope)
        if minister:
            qs = qs.filter(minister=minister)

        docs = []
        if include_builtin:
            slot_ids = [slot.slot for slot in PLAYER_DOCUMENT_SLOTS]
            overrides = {
                doc.slot: doc
                for doc in Document.objects.filter(slot__in=slot_ids)
            }
            for slot in PLAYER_DOCUMENT_SLOTS:
                override = overrides.get(slot.slot)
                payload = (
                    _document_payload(request, override)
                    if override is not None
                    else _builtin_document_payload(request, slot)
                )
                if scope and payload["scope"] != scope:
                    continue
                if minister and payload["minister"] != minister:
                    continue
                docs.append(payload)

            qs = qs.filter(slot__isnull=True)

        docs.extend(_document_payload(request, d) for d in qs)
        docs.sort(key=lambda item: (item.get("order", 1000), item["title"]))
        return Response({"documents": docs})

    def post(self, request: Request) -> Response:
        """Загружает новый документ (только admin)."""
        if not request.session.get("is_admin", False):
            return Response(
                {"error": "Требуются права администратора"},
                status=status.HTTP_403_FORBIDDEN,
            )

        file = request.FILES.get("file")
        if not file:
            return Response({"error": "Файл не передан"}, status=status.HTTP_400_BAD_REQUEST)
        if not _is_pdf_upload(file):
            return Response(
                {"error": "Загружать можно только PDF-файлы"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        slot_id = request.data.get("slot") or None
        slot_meta = None
        if slot_id:
            slot_meta = PLAYER_DOCUMENT_SLOT_BY_ID.get(str(slot_id))
            if slot_meta is None:
                return Response(
                    {"error": "Неизвестный слот документа"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        title = request.data.get("title", file.name)
        scope = request.data.get("scope", "general")
        minister = request.data.get("minister") or None
        if slot_meta is not None:
            title = title or slot_meta.title
            scope = slot_meta.scope
            minister = slot_meta.minister

        if scope not in ("general", "minister"):
            return Response({"error": "Недопустимое значение scope"}, status=status.HTTP_400_BAD_REQUEST)
        if scope == "general":
            minister = None
        elif minister not in DOCUMENT_MINISTERS:
            return Response(
                {
                    "error": (
                        "Для scope=minister нужно передать minister: "
                        + ", ".join(sorted(DOCUMENT_MINISTERS))
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if slot_meta is not None:
            doc = Document.objects.filter(slot=slot_meta.slot).first()
            if doc is None:
                doc = Document.objects.create(
                    title=title or slot_meta.title,
                    file=file,
                    slot=slot_meta.slot,
                    scope=scope,
                    minister=minister,
                )
            else:
                doc.file.delete(save=False)
                doc.title = title or slot_meta.title
                doc.file = file
                doc.scope = scope
                doc.minister = minister
                doc.save()
        else:
            doc = Document.objects.create(
                title=title,
                file=file,
                scope=scope,
                minister=minister,
            )

        return Response(_document_payload(request, doc), status=status.HTTP_201_CREATED)


class DocumentDownloadView(APIView):
    """GET /api/documents/{id}/download/"""

    def get(self, request: Request, doc_id: int) -> FileResponse | Response:
        try:
            doc = Document.objects.get(pk=doc_id)
        except Document.DoesNotExist:
            return Response({"error": "Документ не найден"}, status=status.HTTP_404_NOT_FOUND)

        filename = doc.file.name.split("/")[-1]
        return FileResponse(
            doc.file.open("rb"),
            as_attachment=True,
            filename=filename,
        )


class DocumentDeleteView(APIView):
    """DELETE /api/documents/{id}/"""

    def delete(self, request: Request, doc_id: int) -> Response:
        if not request.session.get("is_admin", False):
            return Response(
                {"error": "Требуются права администратора"},
                status=status.HTTP_403_FORBIDDEN,
            )
        try:
            doc = Document.objects.get(pk=doc_id)
        except Document.DoesNotExist:
            return Response({"error": "Документ не найден"}, status=status.HTTP_404_NOT_FOUND)

        doc.file.delete(save=False)
        doc.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


def _admin_required(request: Request) -> Response | None:
    if not request.session.get("is_admin", False):
        return Response(
            {"error": "Требуются права администратора"},
            status=status.HTTP_403_FORBIDDEN,
        )
    return None


def _line_for_token(content: str, token: str) -> int | None:
    if not token:
        return None
    for index, line in enumerate(content.splitlines(), start=1):
        if token in line:
            return index
    return None


def _validation_item(
    filename: str,
    message: str,
    *,
    line: int | None = None,
    severity: str = "error",
) -> dict[str, Any]:
    return {
        "filename": filename,
        "line": line,
        "message": message,
        "severity": severity,
    }


def _parse_config_contents(contents: dict[str, str]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    parsed = {}
    errors = []
    for filename in CONFIG_FILENAMES:
        content = contents.get(filename, "")
        try:
            parsed[filename] = yaml.safe_load(content) or {}
        except yaml.YAMLError as exc:
            line = None
            mark = getattr(exc, "problem_mark", None)
            if mark is not None:
                line = int(mark.line) + 1
            errors.append(
                _validation_item(filename, f"YAML не читается: {exc}", line=line)
            )
    return parsed, errors


def validate_config_contents(contents: dict[str, str]) -> dict[str, Any]:
    parsed, errors = _parse_config_contents(contents)
    warnings = []
    if errors:
        return {"valid": False, "errors": errors, "warnings": warnings}

    parameters_root = parsed.get("parameters.yaml") or {}
    formulas_root = parsed.get("formulas.yaml") or {}
    decision_order = parsed.get("decision_order.yaml") or {}
    interpolation = parsed.get("interpolation.yaml") or {}
    difficulties = parsed.get("difficulties.yaml") or {}

    parameter_names = set()
    if not isinstance(parameters_root, dict):
        errors.append(_validation_item("parameters.yaml", "Корень файла должен быть словарём категорий."))
    else:
        for category_name, category in parameters_root.items():
            if not isinstance(category, dict):
                errors.append(
                    _validation_item(
                        "parameters.yaml",
                        f"Категория {category_name} должна быть словарём параметров.",
                        line=_line_for_token(contents["parameters.yaml"], str(category_name)),
                    )
                )
                continue
            for param_name, config in category.items():
                parameter_names.add(param_name)
                if not hasattr(GamePeriod, param_name):
                    errors.append(
                        _validation_item(
                            "parameters.yaml",
                            f"Для параметра {param_name} нет поля в GamePeriod.",
                            line=_line_for_token(contents["parameters.yaml"], str(param_name)),
                        )
                    )
                if not isinstance(config, dict):
                    errors.append(
                        _validation_item(
                            "parameters.yaml",
                            f"Параметр {param_name} должен быть словарём.",
                            line=_line_for_token(contents["parameters.yaml"], str(param_name)),
                        )
                    )
                    continue
                for required_key in ("default", "verbose_name"):
                    if required_key not in config:
                        errors.append(
                            _validation_item(
                                "parameters.yaml",
                                f"У параметра {param_name} нет обязательного поля {required_key}.",
                                line=_line_for_token(contents["parameters.yaml"], str(param_name)),
                            )
                        )

    if isinstance(decision_order, dict):
        calculation_order = decision_order.get("calculation_order", [])
        if not isinstance(calculation_order, list):
            errors.append(_validation_item("decision_order.yaml", "calculation_order должен быть списком."))
        else:
            for section_name in calculation_order:
                if section_name not in formulas_root:
                    errors.append(
                        _validation_item(
                            "decision_order.yaml",
                            f"calculation_order ссылается на отсутствующую секцию formulas.yaml: {section_name}.",
                            line=_line_for_token(contents["decision_order.yaml"], str(section_name)),
                        )
                    )

        for stage_key, stage in decision_order.items():
            if not isinstance(stage, dict) or "order" not in stage:
                continue
            for input_config in stage.get("inputs", []):
                param_name = input_config.get("param") if isinstance(input_config, dict) else None
                if param_name and param_name not in parameter_names:
                    errors.append(
                        _validation_item(
                            "decision_order.yaml",
                            f"Этап {stage_key} использует неизвестный параметр {param_name}.",
                            line=_line_for_token(contents["decision_order.yaml"], str(param_name)),
                        )
                    )
            for auto_config in stage.get("auto_calculated", []):
                param_name = auto_config.get("param") if isinstance(auto_config, dict) else None
                if param_name and param_name not in parameter_names:
                    errors.append(
                        _validation_item(
                            "decision_order.yaml",
                            f"Этап {stage_key} авторассчитывает неизвестный параметр {param_name}.",
                            line=_line_for_token(contents["decision_order.yaml"], str(param_name)),
                        )
                    )
    else:
        errors.append(_validation_item("decision_order.yaml", "Корень файла должен быть словарём."))

    if isinstance(formulas_root, dict):
        for section_name, section in formulas_root.items():
            if not isinstance(section, dict):
                continue
            for param_name in section:
                if param_name not in parameter_names:
                    errors.append(
                        _validation_item(
                            "formulas.yaml",
                            f"Формула {section_name}.{param_name} записывает неизвестный параметр {param_name}.",
                            line=_line_for_token(contents["formulas.yaml"], str(param_name)),
                        )
                    )
    else:
        errors.append(_validation_item("formulas.yaml", "Корень файла должен быть словарём секций."))

    if isinstance(interpolation, dict):
        for table_name, table in interpolation.items():
            if not isinstance(table, dict):
                errors.append(
                    _validation_item(
                        "interpolation.yaml",
                        f"Таблица {table_name} должна быть словарём.",
                        line=_line_for_token(contents["interpolation.yaml"], str(table_name)),
                    )
                )
                continue
            x_values = table.get("x", [])
            y_values = table.get("y", [])
            if not isinstance(x_values, list) or not isinstance(y_values, list) or not x_values or not y_values:
                errors.append(
                    _validation_item(
                        "interpolation.yaml",
                        f"У таблицы {table_name} должны быть непустые списки x и y.",
                        line=_line_for_token(contents["interpolation.yaml"], str(table_name)),
                    )
                )
            elif len(x_values) != len(y_values):
                errors.append(
                    _validation_item(
                        "interpolation.yaml",
                        f"У таблицы {table_name} разная длина x и y.",
                        line=_line_for_token(contents["interpolation.yaml"], str(table_name)),
                    )
                )
    else:
        errors.append(_validation_item("interpolation.yaml", "Корень файла должен быть словарём таблиц."))

    if isinstance(difficulties, dict):
        for profile_name, profile in difficulties.items():
            if not isinstance(profile, dict):
                errors.append(
                    _validation_item(
                        "difficulties.yaml",
                        f"Профиль {profile_name} должен быть словарём.",
                        line=_line_for_token(contents["difficulties.yaml"], str(profile_name)),
                    )
                )
                continue
            overrides = profile.get("overrides", {})
            if isinstance(overrides, dict):
                for param_name in overrides:
                    if param_name not in parameter_names:
                        errors.append(
                            _validation_item(
                                "difficulties.yaml",
                                f"Профиль {profile_name} переопределяет неизвестный параметр {param_name}.",
                                line=_line_for_token(contents["difficulties.yaml"], str(param_name)),
                            )
                        )
    else:
        errors.append(_validation_item("difficulties.yaml", "Корень файла должен быть словарём профилей."))

    runtime_config = apply_runtime_settings(parsed, settings_payload(GlobalGameSettings.get_solo()))
    formula_validator = FormulaValidator(config_data=runtime_config)
    formula_errors, formula_warnings = formula_validator.validate_all()
    cycles = formula_validator.check_circular_dependencies()
    for message in formula_errors:
        filename = "formulas.yaml" if message.startswith("formulas.yaml") else "parameters.yaml"
        errors.append(
            _validation_item(
                filename,
                message,
                line=_line_for_token(contents[filename], message.split("'")[-2] if "'" in message else ""),
            )
        )
    for message in formula_warnings:
        filename = "formulas.yaml" if message.startswith("formulas.yaml") else "interpolation.yaml"
        warnings.append(
            _validation_item(filename, message, severity="warning")
        )
    for cycle in cycles:
        warnings.append(
            _validation_item(
                "formulas.yaml",
                f"Возможная циклическая зависимость формул: {cycle}.",
                severity="warning",
            )
        )

    return {"valid": len(errors) == 0, "errors": errors, "warnings": warnings}


def _config_payload(config_file: ConfigFile | None, filename: str) -> dict[str, Any]:
    builtin_content = read_builtin_config_file(filename)
    content = config_file.content if config_file is not None else builtin_content
    return {
        "filename": filename,
        "title": CONFIG_LABELS.get(filename, filename),
        "content": content,
        "builtin_content": builtin_content,
        "is_modified": config_file is not None,
        "version": config_file.version if config_file is not None else 0,
        "updated_at": config_file.updated_at.isoformat() if config_file is not None else None,
    }


class ConfigFilesView(APIView):
    """GET /api/admin/config-files/"""

    def get(self, request: Request) -> Response:
        denied = _admin_required(request)
        if denied is not None:
            return denied
        overrides = {cfg.filename: cfg for cfg in ConfigFile.objects.all()}
        return Response(
            {
                "files": [
                    {
                        **_config_payload(overrides.get(filename), filename),
                        "content": None,
                        "builtin_content": None,
                    }
                    for filename in CONFIG_FILENAMES
                ],
                "label": get_config_label(),
            }
        )


class ConfigFileDetailView(APIView):
    """GET/PATCH /api/admin/config-files/{filename}/"""

    def get(self, request: Request, filename: str) -> Response:
        denied = _admin_required(request)
        if denied is not None:
            return denied
        if filename not in CONFIG_FILENAMES:
            return Response({"error": "Неизвестный конфигурационный файл"}, status=status.HTTP_404_NOT_FOUND)
        config_file = ConfigFile.objects.filter(filename=filename).first()
        return Response(_config_payload(config_file, filename))

    def patch(self, request: Request, filename: str) -> Response:
        denied = _admin_required(request)
        if denied is not None:
            return denied
        if filename not in CONFIG_FILENAMES:
            return Response({"error": "Неизвестный конфигурационный файл"}, status=status.HTTP_404_NOT_FOUND)
        content = str(request.data.get("content", ""))
        contents = get_active_config_contents()
        contents[filename] = content
        validation = validate_config_contents(contents)
        if not validation["valid"]:
            return Response(validation, status=status.HTTP_400_BAD_REQUEST)
        config_file = bump_or_create_config(filename, content)
        return Response({**_config_payload(config_file, filename), "validation": validation})


class ConfigFileValidateView(APIView):
    """POST /api/admin/config-files/{filename}/validate/"""

    def post(self, request: Request, filename: str) -> Response:
        denied = _admin_required(request)
        if denied is not None:
            return denied
        if filename not in CONFIG_FILENAMES:
            return Response({"error": "Неизвестный конфигурационный файл"}, status=status.HTTP_404_NOT_FOUND)
        contents = get_active_config_contents()
        contents[filename] = str(request.data.get("content", ""))
        return Response(validate_config_contents(contents))


class ConfigFileResetView(APIView):
    """POST /api/admin/config-files/{filename}/reset/"""

    def post(self, request: Request, filename: str) -> Response:
        denied = _admin_required(request)
        if denied is not None:
            return denied
        if filename not in CONFIG_FILENAMES:
            return Response({"error": "Неизвестный конфигурационный файл"}, status=status.HTTP_404_NOT_FOUND)
        ConfigFile.objects.filter(filename=filename).delete()
        config_file = ConfigFile.objects.filter(filename=filename).first()
        return Response(_config_payload(config_file, filename))


class GlobalSettingsView(APIView):
    """GET/PATCH /api/admin/settings/"""

    def get(self, request: Request) -> Response:
        denied = _admin_required(request)
        if denied is not None:
            return denied
        return Response(settings_payload(GlobalGameSettings.get_solo()))

    def patch(self, request: Request) -> Response:
        denied = _admin_required(request)
        if denied is not None:
            return denied
        settings_obj = GlobalGameSettings.get_solo()
        for field in (
            "use_team_passwords",
            "auto_calculate_decision_residuals",
            "parallel_decision_mode",
        ):
            if field in request.data:
                setattr(settings_obj, field, bool(request.data[field]))
        settings_obj.save()
        return Response(settings_payload(settings_obj))


class GroupGamesExcelExportView(APIView):
    """GET /api/groups/{group_id}/export/excel/"""

    def get(self, request: Request, group_id: int) -> HttpResponse | Response:
        denied = _admin_required(request)
        if denied is not None:
            return denied
        try:
            group = Group.objects.select_related("faculty").get(pk=group_id)
        except Group.DoesNotExist:
            return Response(
                {"error": "Группа не найдена"},
                status=status.HTTP_404_NOT_FOUND,
            )

        filename = f"strategem-group-{group.id}-games.xlsx"
        response = HttpResponse(
            build_group_results_xlsx(group),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = f"attachment; filename={filename}"
        return response


class CalculatorStateView(APIView):
    """GET /api/admin/calculator/{game_id}/state/
    Возвращает полное состояние игры для калькулятора."""

    def get(self, request, game_id):
        if not request.session.get("is_admin", False):
            return Response({"error": "Не авторизован"}, status=403)

        try:
            game = Game.objects.get(id=game_id)
        except Game.DoesNotExist:
            return Response({"error": "Игра не найдена"}, status=404)

        calculator = get_calculator_for_game(game)
        periods_data = []

        all_periods = list(game.periods.order_by("period_number"))
        all_params = [p.get_parameters() for p in all_periods]
        for i, period in enumerate(all_periods):
            params = all_params[i]
            # prev() должен ссылаться на предыдущий сохранённый период.
            # Подстановка может не совпадать с расчётом для input-параметров,
            # т.к. решения игрока модифицировали params при расчёте, но не
            # сохранялись в предыдущий период. Проверка на фронте.
            history = all_params[:i]
            formulas = calculator.get_all_formulas_with_substitutions(params, history)

            periods_data.append({
                "period_number": period.period_number,
                "params": params,
                "formulas": formulas,
            })

        # Интерполяционные таблицы
        interp_tables = calculator.get_interpolation_tables()

        # Список input-параметров
        input_params = get_state_manager_for_game(game).get_all_input_params()

        # Все параметры с названиями
        param_config = calculator.get_parameters_config()

        return Response({
            "game_id": game_id,
            "game_name": f"{game.team.name}" if game.team else f"Игра #{game_id}",
            "current_period": game.current_period,
            "periods": periods_data,
            "interpolation_tables": interp_tables,
            "input_params": input_params,
            "param_config": param_config,
        })


class CalculatorCalcView(APIView):
    """POST /api/admin/calculator/{game_id}/calculate/
    Принимает input-параметры, рассчитывает следующий период."""

    def post(self, request, game_id):
        if not request.session.get("is_admin", False):
            return Response({"error": "Не авторизован"}, status=403)

        try:
            game = Game.objects.get(id=game_id)
        except Game.DoesNotExist:
            return Response({"error": "Игра не найдена"}, status=404)

        input_values = request.data.get("parameters", {})

        # Проверка заполненности
        required = get_state_manager_for_game(game).get_all_input_params()
        missing = [
            p for p in required
            if p not in input_values or input_values[p] is None
        ]
        if missing:
            return Response(
                {"error": "Не заполнены решения", "missing": missing},
                status=400,
            )

        # Получить текущий период
        current_period = game.periods.order_by("-period_number").first()
        if not current_period:
            return Response({"error": "Нет текущего периода"}, status=400)

        params = current_period.get_parameters()
        history = game.get_history()

        # Установить решения
        for k, v in input_values.items():
            params[k] = float(v)

        calculator = get_calculator_for_game(game)
        state_manager = get_state_manager_for_game(game)
        fixed_formula_params = []
        for param_name in calculator.get_decision_parameter_names():
            if not calculator.is_fixed_parameter(param_name):
                continue
            _stage_key, stage_config = state_manager._get_stage_for_param(param_name)
            if stage_config is not None and state_manager._is_team_stage(stage_config):
                continue
            fixed_formula_params.append(param_name)
        if fixed_formula_params:
            params = calculator.apply_decision_formulas(
                params,
                history,
                fixed_formula_params,
            )
        errors = calculator.get_decision_residual_errors(
            params, history, input_values.keys()
        )

        if errors:
            return Response(
                {
                    "error": "Ошибки в параметрах",
                    "errors": errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Рассчитать
        if calculator.auto_calculate_decision_residuals():
            calculator.apply_decision_formulas(params, history)
        current_period.set_parameters(params)
        current_period.user_inputs = sorted(
            set(current_period.user_inputs or [])
            | set(input_values.keys())
            | set(calculator.get_decision_parameter_names())
        )
        current_period.save()

        new_params = calculator.calculate_next_period(
            params,
            history,
            recalculate_decisions=False,
        )
        reset_params = game._get_period_reset_parameter_names() | set(input_values.keys())
        for param_name in reset_params:
            if param_name in new_params:
                new_params[param_name] = 0.0

        # Создать новый период
        new_period_num = current_period.period_number + 1
        new_period = game.periods.create(period_number=new_period_num)
        new_period.set_parameters(new_params)
        new_period.save()
        game.current_period = new_period_num
        game.reset_decisions()
        game.save(update_fields=[
            "current_period",
            "decision_capital",
            "decision_energy",
            "decision_finance",
            "decision_import",
            "updated_at",
        ])

        # Формулы с подстановками для нового периода
        new_history = history + [params]
        formulas = calculator.get_all_formulas_with_substitutions(new_params, new_history)

        return Response({
            "success": True,
            "period_number": new_period_num,
            "params": new_params,
            "formulas": formulas,
        })


class CalculatorResetView(APIView):
    """POST /api/admin/calculator/{game_id}/reset/
    Сбрасывает игру до начального состояния."""

    def post(self, request, game_id):
        if not request.session.get("is_admin", False):
            return Response({"error": "Не авторизован"}, status=403)

        try:
            game = Game.objects.get(id=game_id)
        except Game.DoesNotExist:
            return Response({"error": "Игра не найдена"}, status=404)

        # Удалить все периоды кроме начального и восстановить начальный,
        # если старый reset уже успел удалить все периоды.
        game.periods.filter(period_number__gt=1).delete()
        initial_period = game.periods.filter(period_number=1).first()
        initial_params = get_calculator_for_game(game).get_initial_parameters(game.difficulty)
        if initial_period is None:
            initial_period = game.periods.create(period_number=1)
            initial_period.set_parameters(initial_params)
            initial_period.save()
        else:
            initial_period.set_parameters(initial_params)
            initial_period.user_inputs = []
            initial_period.validation_state = {}
            initial_period.save()

        # Сбросить decision states
        game.current_period = 1
        game.decision_capital = 0
        game.decision_energy = 0
        game.decision_finance = 0
        game.decision_import = 0
        game.save(update_fields=[
            "current_period",
            "decision_capital",
            "decision_energy",
            "decision_finance",
            "decision_import",
            "updated_at",
        ])

        return Response({"success": True, "message": "Игра сброшена"})


@ensure_csrf_cookie
def calculator_page(request):
    """Страница калькулятора для отладки формул."""
    return render(request, "admin/calculator.html")
