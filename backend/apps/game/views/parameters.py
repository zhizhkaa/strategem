"""
Views для работы с параметрами и состоянием валидации.

Включает ParameterView и ValidationStateView.
"""

from django.db import transaction
from django.http import Http404
from django.utils import timezone
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from ..engine import get_calculator, get_state_manager
from ..engine.state_manager import DecisionState
from ..models import PARAMETERS_CONFIG, Game, GameStatus
from ..serializers import (
    BatchParameterInputSerializer,
    BatchParameterUpdateResponseSerializer,
    ParameterInputSerializer,
    ParameterStateSerializer,
    ParameterUpdateResponseSerializer,
    ValidationErrorSerializer,
)
from .game import _normalize_validation_state


class ParameterView(APIView):
    """
    View для работы с параметрами игры.

    GET /api/games/{game_id}/parameters/{param}/ - получить параметр
    POST /api/games/{game_id}/parameters/{param}/ - установить параметр
    """

    def get_game(self, game_id: int) -> Game:
        """Получает игру по ID."""
        try:
            return Game.objects.select_related("team__group__faculty").get(pk=game_id)
        except Game.DoesNotExist:
            raise Http404("Игра не найдена")

    def validate_parameter(self, param: str) -> bool:
        """Проверяет существование параметра."""
        return param in PARAMETERS_CONFIG

    @extend_schema(
        summary="Получить параметр",
        description="Возвращает текущее значение параметра с метаданными",
        responses={
            200: ParameterStateSerializer,
            404: OpenApiResponse(description="Параметр не найден"),
        },
    )
    def get(self, request: Request, game_id: int, param: str) -> Response:
        """Возвращает значение параметра."""
        if not self.validate_parameter(param):
            return Response(
                {"error": f"Параметр '{param}' не существует"},
                status=status.HTTP_404_NOT_FOUND,
            )

        game = self.get_game(game_id)
        current_period = game.get_current_period_obj()
        history = game.get_history()

        # Получаем конфигурацию параметра
        config = PARAMETERS_CONFIG.get(param, {})
        if not isinstance(config, dict):
            config = {"default": config}

        value = getattr(current_period, param, config.get("default", 0))

        # Получаем границы
        calculator = get_calculator()
        min_val, max_val = calculator.get_parameter_bounds(
            current_period.get_parameters(), param, history
        )

        # Определяем статус
        decision_state = DecisionState()
        decision_state.from_dict(game.get_decision_states())
        state_manager = get_state_manager()
        fillable = state_manager._get_fillable_params(decision_state)

        is_input = config.get("is_input", False)
        if is_input:
            if value != 0 and value != config.get("default", 0):
                param_status = "filled"
            elif param in fillable:
                param_status = "next_to_fill"
            else:
                param_status = "locked"
        else:
            param_status = "calculated"

        return Response(
            {
                "value": value,
                "verbose_name": config.get("verbose_name", param),
                "category": config.get("category", "unknown"),
                "is_input": is_input,
                "status": param_status,
                "bounds": {"min": min_val, "max": max_val},
                "depends_on": config.get("depends_on", []),
                "decision_group": config.get("decision_group"),
            }
        )

    @extend_schema(
        summary="Установить параметр",
        description="""
        Устанавливает значение параметра.

        Выполняет валидацию значения и пересчитывает зависимые параметры.
        Обновляет состояния решений при необходимости.
        """,
        request=ParameterInputSerializer,
        responses={
            200: ParameterUpdateResponseSerializer,
            400: ValidationErrorSerializer,
            403: OpenApiResponse(description="Параметр недоступен для ввода"),
        },
    )
    def post(self, request: Request, game_id: int, param: str) -> Response:
        """Устанавливает значение параметра."""
        if not self.validate_parameter(param):
            return Response(
                {"error": f"Параметр '{param}' не существует"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Валидация входных данных
        serializer = ParameterInputSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        value = serializer.validated_data["value"]

        game = self.get_game(game_id)

        # Проверяем, что игра не приостановлена
        if game.status == GameStatus.PAUSED:
            return Response(
                {"error": "Игра приостановлена. Принятие решений недоступно."},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Проверяем, что игра не завершена
        if game.status == GameStatus.FINISHED:
            return Response(
                {"error": "Игра завершена. Принятие решений недоступно."},
                status=status.HTTP_403_FORBIDDEN,
            )

        current_period = game.get_current_period_obj()
        history = game.get_history()
        params = current_period.get_parameters()

        # Создаём состояние решений
        decision_state = DecisionState()
        decision_state.from_dict(game.get_decision_states())

        # force=True пропускает проверку границ (используется при сохранении министром)
        force = bool(request.data.get("force", False))

        # Устанавливаем параметр
        state_manager = get_state_manager()
        if state_manager.is_operator_controlled_param(param) and not force:
            return Response(
                {"error": f"Параметр {param} задаётся оператором, а не командой."},
                status=status.HTTP_403_FORBIDDEN,
            )

        success, error, updated_params = state_manager.set_parameter(
            params=params,
            decision_state=decision_state,
            param_name=param,
            value=value,
            history=history,
            user_inputs=current_period.user_inputs,
            force=force,
        )

        if not success:
            calculator = get_calculator()
            min_val, max_val = calculator.get_parameter_bounds(params, param, history)
            return Response(
                {
                    "error": error,
                    "bounds": {"min": min_val, "max": max_val},
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Сохраняем обновлённые параметры
        current_period.set_parameters(updated_params)

        # Помечаем основной параметр как введённый пользователем
        current_period.mark_as_user_input(param)
        # Также помечаем параметры, которые были ИЗМЕНЕНЫ (автозаполненные фиксированные параметры)
        # Сравниваем с исходными параметрами, чтобы найти только изменённые
        for updated_param, new_value in updated_params.items():
            if updated_param != param:
                old_value = params.get(updated_param)
                # Если значение изменилось, помечаем как введённое
                if old_value != new_value:
                    current_period.mark_as_user_input(updated_param)

        # Убираем параметр из validation_state (ошибка исправлена вводом нового значения)
        vs = current_period.validation_state or {}
        changed = False
        for key in ("errors", "incomplete"):
            if param in vs.get(key, []):
                vs[key] = [p for p in vs[key] if p != param]
                changed = True
        if "by_minister" in vs:
            for m_data in vs["by_minister"].values():
                for key in ("errors", "incomplete"):
                    if param in m_data.get(key, []):
                        m_data[key] = [p for p in m_data[key] if p != param]
                        changed = True
        if changed:
            current_period.validation_state = vs

        current_period.save()

        # Сохраняем состояния решений
        game.set_decision_states(decision_state.to_dict())
        game.save()

        # Возвращаем только изменившиеся параметры (delta), чтобы фронтенд
        # не перезаписывал пользовательский ввод значениями из БД
        changed_params = {k: v for k, v in updated_params.items() if params.get(k) != v}

        return Response(
            {
                "success": True,
                "error": None,
                "parameter": param,
                "value": value,
                "updated_parameters": changed_params,
                "decision_states": decision_state.to_dict(),
                "validation_state": _normalize_validation_state(
                    current_period.validation_state
                ),
            }
        )


class ValidationStateView(APIView):
    """
    Лёгкий эндпоинт для получения текущего состояния валидации.

    GET /api/games/{game_id}/validation/

    Используется для периодического опроса (polling) со всех экранов,
    чтобы ошибки, выставленные одним игроком, синхронизировались
    на экранах других министров без перезагрузки страницы.
    """

    @extend_schema(
        summary="Состояние валидации",
        description=(
            "Возвращает текущее состояние валидации периода: ошибки и незаполненные параметры. "
            "Не выполняет расчётов — только читает сохранённое состояние. "
            "Рекомендуемый интервал опроса: 5 секунд."
        ),
        responses={200: {}},
    )
    def get(self, request: Request, game_id: int) -> Response:
        try:
            game = Game.objects.get(pk=game_id)
        except Game.DoesNotExist:
            raise Http404("Игра не найдена")

        current_period = game.get_current_period_obj()
        return Response(
            {
                "period": game.current_period,
                "validation_state": _normalize_validation_state(
                    current_period.validation_state
                ),
            }
        )


class BatchParameterView(APIView):
    """
    Пакетное обновление параметров.

    POST /api/games/{game_id}/parameters/batch/
    Body: { "parameters": {"P9": 100, "P10": 200, ...}, "minister": "population" }
    """

    @extend_schema(
        request=BatchParameterInputSerializer,
        responses={200: BatchParameterUpdateResponseSerializer},
    )
    def post(self, request: Request, game_id: int) -> Response:
        serializer = BatchParameterInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        parameters = serializer.validated_data["parameters"]
        minister_key = serializer.validated_data.get("minister")

        try:
            game = Game.objects.select_related("team").get(id=game_id)
        except Game.DoesNotExist:
            return Response(
                {"error": "Игра не найдена"},
                status=status.HTTP_404_NOT_FOUND,
            )

        if game.status != GameStatus.ACTIVE:
            return Response(
                {"error": "Игра не активна"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        period = game.periods.order_by("-period_number").first()
        if not period:
            return Response(
                {"error": "Нет текущего периода"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        calculator = get_calculator()
        state_manager = get_state_manager()
        current_params = period.get_parameters()
        history = game.get_history()
        operator_params = sorted(
            param_name
            for param_name in parameters
            if state_manager.is_operator_controlled_param(param_name)
        )
        if operator_params:
            return Response(
                {
                    "success": False,
                    "updated_parameters": {},
                    "auto_calculated": {},
                    "errors": {
                        param_name: "Параметр задаётся оператором и не входит в командный batch."
                        for param_name in operator_params
                    },
                    "validation_state": _normalize_validation_state(
                        period.validation_state
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Валидируем и применяем пакет на накопленном временном состоянии.
        errors = {}
        updated_params = dict(current_params)
        auto_calculated = {}
        user_inputs = list(period.user_inputs or [])
        decision_state = DecisionState()
        decision_state.from_dict(game.get_decision_states())

        ordered_param_names = state_manager.get_batch_processing_order(list(parameters.keys()))

        for param_name in ordered_param_names:
            value = parameters[param_name]
            if value < 0:
                errors[param_name] = "Значение не может быть отрицательным"
                continue

            before_apply = dict(updated_params)
            success, error, result_params = state_manager.set_parameter(
                params=updated_params,
                decision_state=decision_state,
                param_name=param_name,
                value=value,
                history=history,
                user_inputs=user_inputs,
                force=False,
            )
            if not success:
                errors[param_name] = error or "Значение вне допустимого диапазона"
                continue

            updated_params = result_params
            if param_name not in user_inputs:
                user_inputs.append(param_name)
            for changed_param, new_value in result_params.items():
                if changed_param != param_name and before_apply.get(changed_param) != new_value:
                    auto_calculated[changed_param] = new_value
                    if changed_param not in user_inputs:
                        user_inputs.append(changed_param)

        if errors:
            return Response(
                {
                    "success": False,
                    "updated_parameters": {},
                    "auto_calculated": {},
                    "errors": errors,
                    "validation_state": _normalize_validation_state(
                        period.validation_state
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            period.set_parameters(updated_params)
            period.user_inputs = user_inputs
            game.set_decision_states(decision_state.to_dict())
            game.save(
                update_fields=[
                    "decision_capital",
                    "decision_energy",
                    "decision_finance",
                    "decision_import",
                ]
            )
            vs = self._build_validation_state(
                params=updated_params,
                user_inputs=user_inputs,
                decision_state=decision_state,
                calculator=calculator,
                state_manager=state_manager,
                history=history,
            )
            period.validation_state = vs
            period.save()

        return Response(
            {
                "success": True,
                "updated_parameters": {k: updated_params[k] for k in parameters},
                "auto_calculated": auto_calculated,
                "errors": {},
                "validation_state": _normalize_validation_state(vs),
            }
        )

    def _build_validation_state(
        self,
        *,
        params,
        user_inputs,
        decision_state,
        calculator,
        state_manager,
        history,
    ):
        """Строит validation_state, пригодный для strict blocking UI."""
        user_inputs = set(user_inputs or [])
        errors = []

        for param_name in user_inputs:
            value = params.get(param_name, 0)
            is_valid, _, _ = calculator.validate_input(params, param_name, value, history)
            if not is_valid:
                errors.append(param_name)
        for param_name in calculator.get_decision_residual_errors(params, history):
            if param_name not in errors:
                errors.append(param_name)

        incomplete = self._collect_incomplete_params(
            params=params,
            user_inputs=user_inputs,
            decision_state=decision_state,
            calculator=calculator,
            state_manager=state_manager,
        )
        by_minister = self._group_validation_state_by_minister(
            state_manager, errors, incomplete
        )

        return {
            "errors": errors,
            "incomplete": incomplete,
            "by_minister": by_minister,
            "last_validated": timezone.now().isoformat(),
        }

    def _collect_incomplete_params(
        self,
        *,
        params,
        user_inputs: set[str],
        decision_state,
        calculator,
        state_manager,
    ) -> list[str]:
        """Возвращает все блокирующе незаполненные input-параметры текущего периода."""
        if state_manager.parallel_mode:
            return [
                param
                for param in state_manager.get_all_input_params()
                if param not in user_inputs
                and not calculator.is_fixed_parameter(param)
            ]

        fillable = state_manager._get_fillable_params(decision_state)
        stages = state_manager._get_available_stages(
            decision_state, params, list(user_inputs)
        )

        incomplete = []
        for stage in stages:
            if not stage["available"] or stage["completed"]:
                continue
            for param in stage["inputs"]:
                if param and param not in user_inputs and param in fillable:
                    incomplete.append(param)
        return incomplete

    def _group_validation_state_by_minister(
        self, state_manager, errors: list[str], incomplete: list[str]
    ) -> dict[str, dict[str, list[str]]]:
        """Разбивает validation_state по министрам согласно decision_order."""
        param_to_minister = state_manager.get_param_to_minister_map()
        ministers = list(state_manager._decision_order.get("ministers", {}).keys())
        by_minister = {
            minister_key: {"errors": [], "incomplete": []}
            for minister_key in ministers
        }

        for param in errors:
            minister_key = param_to_minister.get(param)
            if minister_key in by_minister:
                by_minister[minister_key]["errors"].append(param)

        for param in incomplete:
            minister_key = param_to_minister.get(param)
            if minister_key in by_minister:
                by_minister[minister_key]["incomplete"].append(param)

        return by_minister
