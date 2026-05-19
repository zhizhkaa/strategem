"""
Административные views и вспомогательные API.

Включает:
- AdminLoginView, AdminLogoutView, AdminCheckView — аутентификация админа
- TeamGameView — получение игры команды
- DocumentView, DocumentDeleteView — управление документацией
"""

from django.conf import settings
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from django_ratelimit.decorators import ratelimit
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.management.models import Team

from ..engine.calculator import get_calculator
from ..models import Document, Game
from ..serializers import (
    AdminLoginSerializer,
    GameDetailSerializer,
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

        password = serializer.validated_data["password"]

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
    def get(self, request: Request, team_id: int) -> Response:
        """Возвращает игру команды."""
        try:
            team = Team.objects.get(pk=team_id)
        except Team.DoesNotExist:
            return Response(
                {"error": "Команда не найдена"},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not hasattr(team, "game") or team.game is None:
            return Response({"game": None})

        serializer = GameDetailSerializer(team.game)
        return Response({"game": serializer.data})


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

        qs = Document.objects.all()
        if scope:
            qs = qs.filter(scope=scope)
        if minister:
            qs = qs.filter(minister=minister)

        docs = [
            {
                "id": d.id,
                "title": d.title,
                "scope": d.scope,
                "minister": d.minister,
                "url": request.build_absolute_uri(d.file.url),
                "filename": d.file.name.split("/")[-1],
                "uploaded_at": d.uploaded_at.isoformat(),
            }
            for d in qs
        ]
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

        title = request.data.get("title", file.name)
        scope = request.data.get("scope", "general")
        minister = request.data.get("minister") or None

        if scope not in ("general", "minister"):
            return Response({"error": "Недопустимое значение scope"}, status=status.HTTP_400_BAD_REQUEST)

        doc = Document.objects.create(
            title=title,
            file=file,
            scope=scope,
            minister=minister,
        )

        return Response(
            {
                "id": doc.id,
                "title": doc.title,
                "scope": doc.scope,
                "minister": doc.minister,
                "url": request.build_absolute_uri(doc.file.url),
                "filename": doc.file.name.split("/")[-1],
                "uploaded_at": doc.uploaded_at.isoformat(),
            },
            status=status.HTTP_201_CREATED,
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

        calculator = get_calculator()
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
        input_params = ['P9', 'P11', 'P12', 'E20', 'E21', 'E22', 'E24',
                        'E26', 'E27', 'G18', 'G19', 'F14',
                        'TF9', 'TF13', 'TF14', 'TF16', 'TF17']

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
        required = ['P9', 'P11', 'P12', 'E21', 'E22', 'E24',
                     'E26', 'E27', 'G18', 'G19', 'F14',
                     'TF13', 'TF14', 'TF16', 'TF17']
        missing = [p for p in required if p not in input_values or input_values[p] is None]
        if missing:
            return Response({"error": "Не заполнены поля", "missing": missing}, status=400)

        # Получить текущий период
        current_period = game.periods.order_by("-period_number").first()
        if not current_period:
            return Response({"error": "Нет текущего периода"}, status=400)

        params = current_period.get_parameters()
        history = game.get_history()

        # Установить решения
        for k, v in input_values.items():
            params[k] = float(v)

        # Рассчитать
        calculator = get_calculator()
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
        initial_params = get_calculator().get_initial_parameters(game.difficulty)
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
