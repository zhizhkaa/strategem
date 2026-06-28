"""
ViewSet для управления играми.

Включает GameViewSet с действиями: state, calculations, next-period,
pause, resume, periods, validate-period, interpolation-tables,
decision-structure, charts, parameter-history.
"""

from datetime import datetime, timezone
from urllib.parse import quote

from django.http import HttpResponse
from django.utils import timezone as django_timezone
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from ..configuration import (
    get_calculator_for_game,
    get_game_config_data,
    get_state_manager_for_game,
)
from ..engine.interpolation import Interpolator
from ..engine.state_manager import DecisionState
from ..exports import build_results_xlsx
from ..models import PARAMETERS_CONFIG, Game, GamePeriod, GameStatus
from ..decision_structure import build_decision_structure
from ..serializers import (
    CalculationGroupSerializer,
    GameChartsSerializer,
    GameCreateSerializer,
    GameDetailSerializer,
    GameListSerializer,
    GamePeriodListSerializer,
    GameStateSerializer,
    NextPeriodResponseSerializer,
)


def _normalize_validation_state(vs: dict) -> dict:
    """
    Возвращает validation_state с гарантированными полями.

    Если период ещё не валидировался (vs пустой), возвращает структуру с нулями.
    """
    if not vs:
        return {
            "errors": [],
            "incomplete": [],
            "by_minister": {},
            "last_validated": None,
        }
    return {
        "errors": vs.get("errors", []),
        "incomplete": vs.get("incomplete", []),
        "by_minister": vs.get("by_minister", {}),
        "last_validated": vs.get("last_validated"),
    }


class GameViewSet(viewsets.ModelViewSet):
    """
    ViewSet для управления играми.

    Предоставляет CRUD операции для игр.
    Создание игр доступно только администраторам.
    """

    queryset = Game.objects.select_related("team__group__faculty").all()

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.action != "list":
            return queryset

        archived = self.request.query_params.get("archived")
        include_archived = self.request.query_params.get("include_archived")

        if archived in {"1", "true", "yes"}:
            return queryset.filter(is_archived=True)
        if archived == "all" or include_archived in {"1", "true", "yes"}:
            return queryset
        return queryset.filter(is_archived=False)

    def get_serializer_class(self):
        if self.action == "create":
            return GameCreateSerializer
        elif self.action in ["retrieve", "update", "partial_update"]:
            return GameDetailSerializer
        return GameListSerializer

    @extend_schema(
        summary="Список игр",
        description="Возвращает список всех игр",
        responses={200: GameListSerializer(many=True)},
    )
    def list(self, request: Request) -> Response:
        return super().list(request)

    @extend_schema(
        summary="Создать игру",
        description="Создаёт новую игру для команды. Требуются права администратора.",
        request=GameCreateSerializer,
        responses={
            201: GameDetailSerializer,
            400: OpenApiResponse(description="Ошибка валидации"),
            403: OpenApiResponse(description="Требуются права администратора"),
        },
    )
    def create(self, request: Request) -> Response:
        # Проверяем права администратора
        if not request.session.get("is_admin", False):
            return Response(
                {"error": "Требуются права администратора"},
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().create(request)

    @extend_schema(
        summary="Детали игры",
        description="Возвращает подробную информацию об игре",
        responses={200: GameDetailSerializer},
    )
    def retrieve(self, request: Request, pk=None) -> Response:
        return super().retrieve(request, pk)

    @extend_schema(
        summary="Удалить игру",
        description="Удаляет игру. Требуются права администратора.",
        responses={
            204: OpenApiResponse(description="Игра удалена"),
            403: OpenApiResponse(description="Требуются права администратора"),
        },
    )
    def destroy(self, request: Request, pk=None) -> Response:
        if not request.session.get("is_admin", False):
            return Response(
                {"error": "Требуются права администратора"},
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().destroy(request, pk)

    @extend_schema(
        summary="Архивировать игру",
        description=(
            "Скрывает игру из основного списка администратора. "
            "Данные игры остаются доступны для просмотра и экспорта."
        ),
        responses={200: GameDetailSerializer},
    )
    @action(detail=True, methods=["post"], url_path="archive")
    def archive(self, request: Request, pk=None) -> Response:
        """Архивирует игру без изменения её игрового статуса."""
        if not request.session.get("is_admin", False):
            return Response(
                {"error": "Требуются права администратора"},
                status=status.HTTP_403_FORBIDDEN,
            )

        game = self.get_object()
        if not game.is_archived:
            game.is_archived = True
            game.archived_at = django_timezone.now()
            game.save(update_fields=["is_archived", "archived_at", "updated_at"])

        serializer = GameDetailSerializer(game)
        return Response(serializer.data)

    @extend_schema(
        summary="Вернуть игру из архива",
        description="Возвращает игру в основной список администратора.",
        responses={200: GameDetailSerializer},
    )
    @action(detail=True, methods=["post"], url_path="unarchive")
    def unarchive(self, request: Request, pk=None) -> Response:
        """Возвращает игру из архива."""
        if not request.session.get("is_admin", False):
            return Response(
                {"error": "Требуются права администратора"},
                status=status.HTTP_403_FORBIDDEN,
            )

        game = self.get_object()
        if game.is_archived:
            game.is_archived = False
            game.archived_at = None
            game.save(update_fields=["is_archived", "archived_at", "updated_at"])

        serializer = GameDetailSerializer(game)
        return Response(serializer.data)

    def _export_response(
        self,
        content: bytes,
        filename: str,
        content_type: str,
    ) -> HttpResponse:
        response = HttpResponse(content, content_type=content_type)
        quoted = quote(filename)
        response["Content-Disposition"] = (
            f"attachment; filename*=UTF-8''{quoted}"
        )
        return response

    @extend_schema(
        summary="Экспорт итогов игры в Excel",
        description="Скачивает XLSX с подробными данными по всем периодам.",
        responses={200: OpenApiResponse(description="XLSX-файл")},
    )
    @action(detail=True, methods=["get"], url_path="export/excel")
    def export_excel(self, request: Request, pk=None) -> HttpResponse:
        game = self.get_object()
        filename = f"strategem-game-{game.id}-details.xlsx"
        return self._export_response(
            build_results_xlsx(game),
            filename,
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    @extend_schema(
        summary="Состояние игры",
        description="""
        Возвращает полное состояние игры для UI и ИИ-агентов.

        Включает:
        - Информацию об игре (период, статус)
        - Состояния решений
        - Все параметры с метаданными (значение, границы, статус)
        - Доступные этапы решений
        - Рекомендуемые следующие действия
        - Информацию о министрах
        """,
        responses={200: GameStateSerializer},
    )
    @action(detail=True, methods=["get"], url_path="state")
    def state(self, request: Request, pk=None) -> Response:
        """Возвращает полное состояние игры."""
        game = self.get_object()
        current_period = game.get_current_period_obj()
        history = game.get_history()

        # Создаём состояние решений
        decision_state = DecisionState()
        decision_state.from_dict(game.get_decision_states())

        # Получаем полное состояние
        state_manager = get_state_manager_for_game(game)
        full_state = state_manager.get_full_state(
            params=current_period.get_parameters(),
            decision_state=decision_state,
            history=history,
            current_period=game.current_period,
            total_periods=game.total_periods,
            user_inputs=current_period.user_inputs,
        )

        # Add game status to game_info
        full_state["game_info"]["status"] = game.status

        # Включаем серверное состояние валидации для синхронизации между экранами
        vs = current_period.validation_state or {}
        full_state["validation_state"] = _normalize_validation_state(vs)

        serializer = GameStateSerializer(full_state)
        return Response(serializer.data)

    @extend_schema(
        summary="Детали расчётов текущего периода",
        description="""
        Возвращает детальную информацию о расчётах: формулы,
        подстановку значений и результаты для всех параметров.
        """,
        responses={200: CalculationGroupSerializer(many=True)},
    )
    @action(detail=True, methods=["get"], url_path="calculations")
    def calculations(self, request: Request, pk=None) -> Response:
        """Возвращает детали расчётов текущего периода."""
        game = self.get_object()
        current_period = game.get_current_period_obj()
        history = game.get_history()

        calculator = get_calculator_for_game(game)
        details = calculator.get_calculations_detail(
            current_params=current_period.get_parameters(),
            history=history,
        )

        serializer = CalculationGroupSerializer(details, many=True)
        return Response(serializer.data)

    @extend_schema(
        summary="Перейти к следующему периоду",
        description="""
        Переходит к следующему периоду игры.

        Возможно только если все решения приняты.
        При переходе рассчитываются новые параметры.
        """,
        responses={
            200: NextPeriodResponseSerializer,
            400: OpenApiResponse(description="Невозможно перейти к следующему периоду"),
        },
    )
    @action(detail=True, methods=["post"], url_path="next-period")
    def next_period(self, request: Request, pk=None) -> Response:
        """Переходит к следующему периоду."""
        game = self.get_object()

        current_period = game.get_current_period_obj()
        history = game.get_history()
        params = current_period.get_parameters()
        calculator = get_calculator_for_game(game)
        decision_state = DecisionState()
        decision_state.from_dict(game.get_decision_states())
        state_manager = get_state_manager_for_game(game)

        error_params = []
        residual_error_params = set(
            calculator.get_decision_residual_errors(
                params, history, current_period.user_inputs
            )
        )
        for param_name in current_period.user_inputs:
            if param_name not in residual_error_params:
                continue
            config = calculator._parameters_config.get(param_name, {})
            if not config.get("is_input", False):
                continue
            value = params.get(param_name)
            if value is None:
                continue
            is_valid, _err, _bounds = calculator.validate_input(
                params,
                param_name,
                value,
                history,
                current_period.user_inputs,
            )
            if not is_valid and param_name not in error_params:
                error_params.append(param_name)
        for param_name in residual_error_params:
            if param_name not in error_params:
                error_params.append(param_name)

        if error_params:
            param_to_minister = state_manager.get_param_to_minister_map()
            ministers = list(state_manager._decision_order.get("ministers", {}).keys())
            by_minister: dict[str, dict] = {
                m: {"errors": [], "incomplete": []} for m in ministers
            }
            for param_name in error_params:
                minister = param_to_minister.get(param_name)
                if minister in by_minister:
                    by_minister[minister]["errors"].append(param_name)

            validation_state = {
                "errors": error_params,
                "incomplete": [],
                "by_minister": by_minister,
                "last_validated": datetime.now(timezone.utc).isoformat(),
            }
            current_period.validation_state = validation_state
            current_period.save(update_fields=["validation_state"])
            return Response(
                {
                    "success": False,
                    "error": "В параметрах периода есть ошибки. Исправьте их перед переходом.",
                    "current_period": game.current_period,
                    "game_finished": False,
                    "validation_state": validation_state,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        can_advance = state_manager._can_advance_period(
            decision_state,
            current_period.user_inputs,
            params=params,
            current_period=game.current_period,
        )

        if not can_advance:
            return Response(
                {
                    "success": False,
                    "error": "Не все решения приняты. Завершите все этапы перед переходом.",
                    "current_period": game.current_period,
                    "game_finished": False,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        game.advance_period()

        return Response(
            {
                "success": True,
                "error": None,
                "current_period": game.current_period,
                "game_finished": game.status == GameStatus.FINISHED,
            }
        )

    @extend_schema(
        summary="Приостановить игру",
        description="""
        Приостанавливает игру. Команды смогут только просматривать игру, но не принимать решения.
        Требуются права администратора.
        """,
        responses={
            200: OpenApiResponse(description="Игра приостановлена"),
            400: OpenApiResponse(description="Невозможно приостановить игру"),
            403: OpenApiResponse(description="Требуются права администратора"),
        },
    )
    @action(detail=True, methods=["post"], url_path="pause")
    def pause(self, request: Request, pk=None) -> Response:
        """Приостанавливает игру."""
        if not request.session.get("is_admin", False):
            return Response(
                {"error": "Требуются права администратора"},
                status=status.HTTP_403_FORBIDDEN,
            )

        game = self.get_object()

        if game.status == GameStatus.FINISHED:
            return Response(
                {"error": "Нельзя приостановить завершённую игру"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if game.status == GameStatus.PAUSED:
            return Response(
                {"error": "Игра уже приостановлена"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        game.status = GameStatus.PAUSED
        game.save()

        return Response(
            {
                "success": True,
                "message": "Игра приостановлена",
                "status": game.status,
            }
        )

    @extend_schema(
        summary="Возобновить игру",
        description="""
        Возобновляет приостановленную игру. Команды снова смогут принимать решения.
        Требуются права администратора.
        """,
        responses={
            200: OpenApiResponse(description="Игра возобновлена"),
            400: OpenApiResponse(description="Невозможно возобновить игру"),
            403: OpenApiResponse(description="Требуются права администратора"),
        },
    )
    @action(detail=True, methods=["post"], url_path="resume")
    def resume(self, request: Request, pk=None) -> Response:
        """Возобновляет игру."""
        if not request.session.get("is_admin", False):
            return Response(
                {"error": "Требуются права администратора"},
                status=status.HTTP_403_FORBIDDEN,
            )

        game = self.get_object()

        if game.status == GameStatus.FINISHED:
            return Response(
                {"error": "Нельзя возобновить завершённую игру"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if game.status != GameStatus.PAUSED:
            return Response(
                {"error": "Игра не приостановлена"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        game.status = GameStatus.ACTIVE
        game.save()

        return Response(
            {
                "success": True,
                "message": "Игра возобновлена",
                "status": game.status,
            }
        )

    @extend_schema(
        summary="История периодов",
        description="Возвращает краткую информацию о всех периодах игры",
        responses={200: GamePeriodListSerializer(many=True)},
    )
    @action(detail=True, methods=["get"], url_path="periods")
    def periods(self, request: Request, pk=None) -> Response:
        """Возвращает список периодов игры."""
        game = self.get_object()
        periods = GamePeriod.objects.filter(game=game).order_by("period_number")
        serializer = GamePeriodListSerializer(periods, many=True)
        return Response(serializer.data)

    @extend_schema(
        summary="Проверить параметры текущего периода",
        description="""
        Проверяет все введённые параметры текущего периода на соответствие границам.
        Не изменяет состояние игры.

        Возвращает:
        - valid: True если все параметры корректны
        - errors: список кодов параметров, нарушающих границы
        - can_advance: True если все этапы завершены
        """,
        responses={200: {}},
    )
    @action(detail=True, methods=["post"], url_path="validate-period")
    def validate_period(self, request: Request, pk=None) -> Response:
        """
        Проверяет параметры периода.

        Сохраняет результат в GamePeriod.validation_state для синхронизации
        между всеми экранами (сводный лист + листы министров).
        """
        game = self.get_object()
        current_period = game.get_current_period_obj()
        history = game.get_history()
        params = current_period.get_parameters()

        calculator = get_calculator_for_game(game)
        state_manager = get_state_manager_for_game(game)
        decision_state = DecisionState()
        decision_state.from_dict(game.get_decision_states())

        # --- Параметры с ошибками (красная подсветка) ---
        error_params = []
        for param_name in current_period.user_inputs:
            config = calculator._parameters_config.get(param_name, {})
            if not config.get("is_input", False):
                continue
            value = params.get(param_name)
            if value is None:
                continue
            is_valid, _err, _bounds = calculator.validate_input(
                params,
                param_name,
                value,
                history,
                current_period.user_inputs,
            )
            if not is_valid:
                error_params.append(param_name)
        for param_name in calculator.get_decision_residual_errors(
            params, history, current_period.user_inputs
        ):
            if param_name not in error_params:
                error_params.append(param_name)

        # --- Незаполненные параметры (жёлтая подсветка) ---
        # В параллельном режиме проверяем ВСЕ вводимые параметры;
        # в последовательном — только те, что сейчас доступны.
        user_inputs_set = set(current_period.user_inputs)
        incomplete_params = []

        if state_manager.parallel_mode:
            all_input_params = state_manager.get_all_input_params()
            for p in all_input_params:
                if p not in user_inputs_set:
                    # Фиксированные параметры пропускаем — они заполняются автоматически
                    if not calculator.is_fixed_parameter(p):
                        incomplete_params.append(p)
        else:
            fillable = state_manager._get_fillable_params(
                decision_state,
                params=params,
                user_inputs=current_period.user_inputs,
                current_period=game.current_period,
            )
            stages = state_manager._get_available_stages(
                decision_state, params, current_period.user_inputs, game.current_period
            )
            for stage in stages:
                if not stage["available"] or stage["completed"]:
                    continue
                for p in stage["inputs"]:
                    if p and p not in user_inputs_set and p in fillable:
                        incomplete_params.append(p)

        # --- Разбивка по министрам ---
        param_to_minister = state_manager.get_param_to_minister_map()
        ministers = list(state_manager._decision_order.get("ministers", {}).keys())
        by_minister: dict[str, dict] = {
            m: {"errors": [], "incomplete": []} for m in ministers
        }

        for p in error_params:
            m = param_to_minister.get(p)
            if m and m in by_minister:
                by_minister[m]["errors"].append(p)

        for p in incomplete_params:
            m = param_to_minister.get(p)
            if m and m in by_minister:
                by_minister[m]["incomplete"].append(p)

        # --- Сохраняем в БД для синхронизации между экранами ---
        validation_state = {
            "errors": error_params,
            "incomplete": incomplete_params,
            "by_minister": by_minister,
            "last_validated": datetime.now(timezone.utc).isoformat(),
        }
        current_period.validation_state = validation_state
        current_period.save(update_fields=["validation_state"])

        # --- can_advance ---
        can_advance = (
            state_manager._can_advance_period(
                decision_state,
                current_period.user_inputs,
                params=params,
                current_period=game.current_period,
            )
            and len(error_params) == 0
        )

        return Response(
            {
                "valid": len(error_params) == 0,
                "can_advance": can_advance,
                "validation_state": validation_state,
                # Обратная совместимость — старые поля тоже возвращаем
                "errors": error_params,
                "incomplete_by_minister": {
                    m: data["incomplete"]
                    for m, data in by_minister.items()
                    if data["incomplete"]
                },
                "decision_states": game.get_decision_states(),
            }
        )

    @extend_schema(
        summary="Таблицы интерполяции",
        description="Возвращает все таблицы интерполяции из interpolation.yaml",
        responses={200: {}},
    )
    @action(detail=False, methods=["get"], url_path="interpolation-tables")
    def interpolation_tables(self, request: Request) -> Response:
        """Возвращает все таблицы интерполяции."""
        game_id = request.query_params.get("game_id")
        interp = Interpolator()
        if game_id:
            try:
                game = Game.objects.get(pk=int(game_id))
                config_data = get_game_config_data(game)
                if config_data is not None:
                    interp = Interpolator(tables=config_data.get("interpolation.yaml") or {})
            except (Game.DoesNotExist, ValueError):
                pass
        result = {}
        for name in interp.get_table_names():
            table = interp.get_table(name)
            if table:
                result[name] = {
                    "description": table.get("description", ""),
                    "x": table.get("x", []),
                    "y": table.get("y", []),
                }
        return Response(result)

    @extend_schema(
        summary="Структура решений",
        description=(
            "Возвращает структуру сводного листа и листов министров, "
            "производную из decision_order.yaml и parameters.yaml. "
            "Используется фронтендом вместо захардкоженных данных."
        ),
        responses={200: {}},
    )
    @action(detail=False, methods=["get"], url_path="decision-structure")
    def decision_structure(self, request: Request) -> Response:
        """Возвращает полную структуру принятия решений из YAML-конфигов."""
        game_id = request.query_params.get("game_id")
        if game_id:
            try:
                game = Game.objects.get(pk=int(game_id))
                config_data = get_game_config_data(game)
                if config_data is not None:
                    return Response(build_decision_structure(config_data=config_data))
            except (Game.DoesNotExist, ValueError):
                pass
        return Response(build_decision_structure())

    @extend_schema(
        summary="Данные для графиков",
        description="Возвращает данные для построения графиков состояния страны",
        responses={200: GameChartsSerializer},
    )
    @action(detail=True, methods=["get"], url_path="charts")
    def charts(self, request: Request, pk=None) -> Response:
        """Возвращает данные для графиков."""
        game = self.get_object()
        periods = GamePeriod.objects.filter(game=game).order_by("period_number")

        # Группы параметров для графиков
        chart_groups = {
            "population": [
                ("P1", "Численность населения"),
                ("P4", "Продовольствие на душу населения"),
                ("P6", "Товары на душу населения"),
                ("P7", "Услуги на душу населения"),
                ("P5", "Уровень смертности"),
                ("P8", "Уровень рождаемости"),
            ],
            "economy": [
                ("F11", "Производство продовольствия"),
                ("G12", "Производство товаров"),
                ("E17", "Производство энергии"),
            ],
            "energy": [
                ("E7", "Всего энергоресурсов"),
                ("E17", "Производство энергии"),
                ("E15", "Потребность в энергии для производства"),
                ("E19", "Импорт энергоресурсов"),
                ("E22", "Энергоресурсы в резерв"),
            ],
            "capital": [
                ("F3", "Капитал сельского хозяйства"),
                ("G3", "Капитал промышленности"),
                ("E3", "Капитал энергетики"),
                ("G6", "Капитал сферы услуг"),
            ],
            "environment": [
                ("F7", "Состояние окружающей среды"),
                ("F6", "Природоохранный капитал"),
            ],
            "finance": [
                ("TF1", "Внешний долг"),
                ("TF10", "Экспорт энергии"),
                ("TF11", "Экспорт товаров"),
                ("TF12", "Экспорт продовольствия"),
                ("TF13", "Новый кредит"),
                ("TF14", "Выплаты по долгу"),
                ("TF16", "Импорт энергии"),
                ("TF17", "Импорт товаров"),
                ("TF18", "Импорт продовольствия"),
            ],
        }

        result = {}
        for group_name, params in chart_groups.items():
            group_data = []
            for param_name, verbose_name in params:
                data_points = []
                for period in periods:
                    value = getattr(period, param_name, 0)
                    data_points.append({"period": period.period_number, "value": value})
                group_data.append(
                    {
                        "parameter": param_name,
                        "verbose_name": verbose_name,
                        "data": data_points,
                    }
                )
            result[group_name] = group_data

        # Add computed finance metrics: export revenue and import expenses
        export_data = []
        import_data = []
        for period in periods:
            export_total = (
                getattr(period, "TF10", 0)
                + getattr(period, "TF11", 0)
                + getattr(period, "TF12", 0)
            )
            import_total = (
                getattr(period, "TF16", 0)
                + getattr(period, "TF17", 0)
                + getattr(period, "TF18", 0)
            )
            export_data.append({"period": period.period_number, "value": export_total})
            import_data.append({"period": period.period_number, "value": import_total})

        result["finance"].append(
            {
                "parameter": "export_total",
                "verbose_name": "Экспортная выручка",
                "data": export_data,
            }
        )
        result["finance"].append(
            {
                "parameter": "import_total",
                "verbose_name": "Расходы на импорт",
                "data": import_data,
            }
        )

        return Response(result)

    @action(detail=True, methods=["get"], url_path=r"parameter-history/(?P<param>[^/.]+)")
    def parameter_history(self, request: Request, pk=None, param=None) -> Response:
        """Возвращает историю параметра по всем периодам игры."""
        game = self.get_object()

        if param not in PARAMETERS_CONFIG:
            return Response(
                {"error": f"Параметр '{param}' не найден"},
                status=status.HTTP_404_NOT_FOUND,
            )

        periods = GamePeriod.objects.filter(game=game).order_by("period_number")
        config = PARAMETERS_CONFIG.get(param, {})

        data = []
        for period in periods:
            value = getattr(period, param, None)
            data.append({"period": period.period_number, "value": value})

        return Response({
            "parameter": param,
            "verbose_name": config.get("verbose_name", param),
            "data": data,
        })
