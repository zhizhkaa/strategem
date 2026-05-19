"""
ViewSet для управления играми.

Включает GameViewSet с действиями: state, calculations, next-period,
pause, resume, periods, validate-period, interpolation-tables,
decision-structure, charts, parameter-history.
"""

from datetime import datetime, timezone
from pathlib import Path

import yaml
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from ..engine import get_calculator, get_state_manager
from ..engine.interpolation import Interpolator
from ..engine.state_manager import DecisionState
from ..models import PARAMETERS_CONFIG, Game, GamePeriod, GameStatus
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

# ========================================
# СТРУКТУРА СВОДНОГО ЛИСТА
# ========================================
# Определяет группировку этапов для сводной таблицы.
# Каждая запись объединяет один или несколько этапов из decision_order.yaml.
# Это единственное место определения — фронтенд получает данные через API.

SUMMARY_GROUP_DEFS = [
    {
        "number": 1,
        "stages": ["food_distribution"],
        "label": None,
        "total": {"expr": "P9+P10 = P2", "ref": "P2"},
    },
    {
        "number": 2,
        "stages": ["goods_distribution"],
        "label": None,
        "total": {"expr": "P11+P12+P13 = P3", "ref": "P3"},
    },
    {
        "number": 3,
        "stages": ["energy_distribution"],
        "label": None,
        "total": {"expr": "E20+E21+E22+E23 = E7", "ref": "E7"},
    },
    {
        "number": 4,
        "stages": ["energy_production"],
        "label": None,
        "total": {"expr": "E24+E25 = E23", "ref": "E23"},
    },
    {
        "number": 5,
        "stages": [
            "energy_investment",
            "industry_investment",
            "agriculture_investment",
        ],
        "label": "Капиталовложения",
        "total": {"expr": "E26+E27+G18+G19+F14+F15 = P12", "ref": "P12"},
    },
    {
        "number": 6,
        "stages": ["currency_revenue"],
        "label": None,
        "total": None,
    },
    {
        "number": 7,
        "stages": ["loan"],
        "label": None,
        "total": {"expr": "TF13 \u2264 TF5", "ref": "TF5"},
    },
    {
        "number": 8,
        "stages": ["debt_payment"],
        "label": None,
        "total": None,
    },
    {
        "number": 9,
        "stages": ["import_distribution"],
        "label": None,
        "total": {"expr": "TF16+TF17+TF18 = TF15", "ref": "TF15"},
    },
]

MINISTER_SHORT_NAMES = {
    "population": "Население",
    "energy": "Энергетика",
    "industry": "Промышленность",
    "agriculture": "С/х",
    "trade_finance": "Торговля",
}

# Параметры «Текущая ситуация» и «Информация к сведению» для каждого министра.
# Определяются здесь однократно и отдаются фронтенду через API.
MINISTER_CONTEXT_PARAMS = {
    "population": {
        "info_first": [],
        "situation": ["P1", "P2", "P3"],
        "info": ["P4", "P5", "P6", "P7", "P8"],
    },
    "energy": {
        "info_first": [],
        "situation": ["E1", "E2", "E3", "E4", "E5", "E6", "E7"],
        "info": [
            "E8",
            "E9",
            "E10",
            "E11",
            "E12",
            "E13",
            "E14",
            "E15",
            "E16",
            "E17",
            "E18",
            "E19",
        ],
    },
    "industry": {
        "info_first": [],
        "situation": ["G1", "G2", "G3", "G4", "G5", "G6"],
        "info": [
            "G7",
            "G8",
            "G9",
            "G10",
            "G11",
            "G12",
            "G13",
            "G14",
            "G15",
            "G16",
            "G17",
        ],
    },
    "agriculture": {
        "info_first": [],
        "situation": ["F1", "F2", "F3", "F4", "F5", "F6"],
        "info": ["F7", "F8", "F9", "F10", "F11", "F12", "F13"],
    },
    "trade_finance": {
        "info_first": ["TF1"],
        "situation": ["TF2", "TF3", "TF4", "TF5", "TF6", "TF7", "TF8"],
        "info": [],
    },
}

# Ключи таблиц интерполяции, показываемых на листе каждого министра.
MINISTER_INTERPOLATION_KEYS = {
    "population": ["P1", "P2", "P3", "P4"],
    "energy": ["E1", "E2"],
    "industry": ["G1", "G2", "G3"],
    "agriculture": ["F1", "F2", "F3", "F4"],
    "trade_finance": ["TF1", "TF2"],
}

# Целевые значения параметров (финальное состояние страны).
PARAMETER_TARGETS: dict[str, float] = {
    "P1": 500,
    "P2": 12500,
    "P3": 68600,
    "P4": 5,
    "P5": 10,
    "P6": 15,
    "P7": 18,
    "P8": 10,
    "E1": 1200,
    "E2": 4800,
    "E3": 6000,
    "E4": 840,
    "E5": 3360,
    "E6": 4200,
    "E7": 56000,
    "E8": 0.2,
    "E9": 7500,
    "E10": 0.4,
    "E11": 5,
    "E12": 12500,
    "E13": 8,
    "E14": 36000,
    "E15": 48500,
    "E16": 5,
    "E17": 30000,
    "E18": 0,
    "E19": 26000,
    "G1": 900,
    "G2": 3600,
    "G3": 4500,
    "G4": 1000,
    "G5": 8000,
    "G6": 9000,
    "G7": 36,
    "G8": 19.4,
    "G9": 18,
    "G10": 4.9,
    "G11": 1,
    "G12": 68600,
    "G13": 26000,
    "G14": 0,
    "G15": 68600,
    "G16": 68600,
    "G17": 5110,
    "F1": 500,
    "F2": 2000,
    "F3": 2500,
    "F4": 6700,
    "F5": 3300,
    "F6": 10000,
    "F7": 0.8,
    "F8": 2.8,
    "F9": 12500,
    "F10": 1,
    "F11": 12500,
    "F12": 0,
    "F13": 0,
}


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
        state_manager = get_state_manager()
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

        calculator = get_calculator()
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
        decision_state = DecisionState()
        decision_state.from_dict(game.get_decision_states())
        state_manager = get_state_manager()
        can_advance = state_manager._can_advance_period(
            decision_state, current_period.user_inputs
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

        success = game.advance_period()

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

        calculator = get_calculator()
        state_manager = get_state_manager()
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
                params, param_name, value, history
            )
            if not is_valid:
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
            fillable = state_manager._get_fillable_params(decision_state)
            stages = state_manager._get_available_stages(
                decision_state, params, current_period.user_inputs
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
                decision_state, current_period.user_inputs
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
        interp = Interpolator()
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
        data_dir = Path(__file__).resolve().parent.parent / "data"
        with open(data_dir / "decision_order.yaml", "r", encoding="utf-8") as f:
            order_config = yaml.safe_load(f)

        # Удаляем служебные секции
        stages = {
            k: v
            for k, v in order_config.items()
            if k not in ("calculation_order", "ministers")
        }
        ministers_config = order_config.get("ministers", {})

        # Строим summary_groups из SUMMARY_GROUP_DEFS
        summary_groups = []
        for grp_def in SUMMARY_GROUP_DEFS:
            inputs_all = []
            auto_all = []
            first_minister = None
            stage_names = []
            for stage_key in grp_def["stages"]:
                stage = stages.get(stage_key, {})
                if first_minister is None:
                    first_minister = stage.get("minister")
                stage_names.append(stage.get("name", stage_key))
                inputs_all += [inp["param"] for inp in stage.get("inputs", [])]
                auto_all += [ac["param"] for ac in stage.get("auto_calculated", [])]

            label = grp_def["label"] or " / ".join(stage_names)
            summary_groups.append(
                {
                    "number": grp_def["number"],
                    "minister": first_minister,
                    "label": label,
                    "inputs": inputs_all,
                    "auto": auto_all,
                    "total": grp_def["total"],
                }
            )

        # Строим minister_configs с полными секциями решений
        minister_configs = {}
        for minister_key, minister_data in ministers_config.items():
            context = MINISTER_CONTEXT_PARAMS.get(minister_key, {})

            # Секции решений из YAML
            decisions = []
            for stage_key in minister_data.get("decisions", []):
                stage = stages.get(stage_key, {})
                # Собираем inputs с полем note
                inputs_with_notes = [
                    {
                        "param": inp["param"],
                        "note": inp.get("note"),
                        "validation": inp.get("validation"),
                    }
                    for inp in stage.get("inputs", [])
                ]
                decisions.append(
                    {
                        "key": stage_key,
                        "number": stage.get("order", 0),
                        "name": stage.get("name", stage_key),
                        "inputs": [inp["param"] for inp in stage.get("inputs", [])],
                        "inputs_detail": inputs_with_notes,
                        "auto": [
                            ac["param"] for ac in stage.get("auto_calculated", [])
                        ],
                        "total": next(
                            (
                                grp_def["total"]
                                for grp_def in SUMMARY_GROUP_DEFS
                                if stage_key in grp_def["stages"]
                            ),
                            None,
                        ),
                    }
                )

            minister_configs[minister_key] = {
                "name": minister_data.get("name", minister_key),
                "short_name": MINISTER_SHORT_NAMES.get(minister_key, minister_key),
                "info_first": context.get("info_first", []),
                "situation": context.get("situation", []),
                "info": context.get("info", []),
                "decisions": decisions,
                "interpolation_keys": MINISTER_INTERPOLATION_KEYS.get(minister_key, []),
            }

        # Собираем все коды параметров, нужные в таблицах (и сводном листе, и листах министров)
        all_codes: set[str] = set()
        for grp in summary_groups:
            all_codes.update(grp["inputs"])
            all_codes.update(grp["auto"])
            if grp["total"]:
                all_codes.add(grp["total"]["ref"])
        for mc in minister_configs.values():
            for section in ("info_first", "situation", "info"):
                all_codes.update(mc[section])

        # Строим словарь параметров из PARAMETERS_CONFIG (все, что есть в all_codes)
        parameters = {}
        for code in all_codes:
            cfg = PARAMETERS_CONFIG.get(code, {})
            parameters[code] = {
                "verbose_name": cfg.get("verbose_name", code),
                "default": cfg.get("default", 0),
                "is_input": cfg.get("is_input", False),
                "category": cfg.get("category", ""),
                "target_value": PARAMETER_TARGETS.get(code),
            }

        return Response(
            {
                "summary_groups": summary_groups,
                "parameters": parameters,
                "ministers": minister_configs,
            }
        )

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
                ("TF13", "Новый кредит"),
                ("TF14", "Выплаты по долгу"),
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
