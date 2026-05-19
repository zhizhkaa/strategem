"""
Сериализаторы для API игры Стратегема.

Включает сериализаторы для:
- Game: игры
- GamePeriod: периода игры
- GameState: полного состояния игры
- Parameter: параметров игры
"""

from apps.management.models import Faculty, Group, Team
from rest_framework import serializers

from .engine import get_calculator
from .models import ALLOWED_TOTAL_PERIODS, Game, GameDifficulty, GamePeriod, GameStatus

# ========================================
# MANAGEMENT SERIALIZERS
# ========================================


class FacultySerializer(serializers.ModelSerializer):
    """Сериализатор факультета."""

    class Meta:
        model = Faculty
        fields = ["id", "name"]


class FacultyCreateSerializer(serializers.ModelSerializer):
    """Сериализатор для создания факультета."""

    class Meta:
        model = Faculty
        fields = ["id", "name"]
        read_only_fields = ["id"]

    def validate_name(self, value: str) -> str:
        """Проверяет уникальность названия факультета."""
        if Faculty.objects.filter(name=value).exists():
            raise serializers.ValidationError(
                "Факультет с таким названием уже существует."
            )
        return value


class GroupSerializer(serializers.ModelSerializer):
    """Сериализатор группы."""

    faculty_name = serializers.CharField(source="faculty.name", read_only=True)

    class Meta:
        model = Group
        fields = ["id", "name", "faculty", "faculty_name", "year"]


class GroupCreateSerializer(serializers.ModelSerializer):
    """Сериализатор для создания группы."""

    class Meta:
        model = Group
        fields = ["id", "name", "faculty", "year"]
        read_only_fields = ["id"]

    def validate(self, data: dict) -> dict:
        """Проверяет уникальность группы."""
        name = data.get("name")
        faculty = data.get("faculty")
        year = data.get("year")

        if Group.objects.filter(name=name, faculty=faculty, year=year).exists():
            raise serializers.ValidationError(
                "Группа с таким названием уже существует в этом факультете и году."
            )
        return data


class TeamSerializer(serializers.ModelSerializer):
    """Сериализатор команды."""

    group_name = serializers.CharField(source="group.name", read_only=True)
    faculty_name = serializers.CharField(source="group.faculty.name", read_only=True)
    has_active_game = serializers.SerializerMethodField()

    class Meta:
        model = Team
        fields = [
            "id",
            "name",
            "group",
            "group_name",
            "faculty_name",
            "has_active_game",
        ]

    def get_has_active_game(self, obj: Team) -> bool:
        """Проверяет, есть ли активная игра у команды."""
        return hasattr(obj, "game") and obj.game is not None


class TeamCreateSerializer(serializers.ModelSerializer):
    """Сериализатор для создания команды."""

    class Meta:
        model = Team
        fields = ["id", "name", "group"]
        read_only_fields = ["id"]

    def validate(self, data: dict) -> dict:
        """Проверяет уникальность команды."""
        name = data.get("name")
        group = data.get("group")

        if Team.objects.filter(name=name, group=group).exists():
            raise serializers.ValidationError(
                "Команда с таким названием уже существует в этой группе."
            )
        return data


# ========================================
# GAME SERIALIZERS
# ========================================


class GameListSerializer(serializers.ModelSerializer):
    """Сериализатор для списка игр."""

    team_name = serializers.CharField(source="team.name", read_only=True)
    group_name = serializers.CharField(source="team.group.name", read_only=True)
    faculty_name = serializers.CharField(
        source="team.group.faculty.name", read_only=True
    )
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    difficulty_display = serializers.CharField(
        source="get_difficulty_display", read_only=True
    )

    class Meta:
        model = Game
        fields = [
            "id",
            "team",
            "team_name",
            "group_name",
            "faculty_name",
            "status",
            "status_display",
            "difficulty",
            "difficulty_display",
            "current_period",
            "total_periods",
            "created_at",
            "updated_at",
        ]


class GameCreateSerializer(serializers.ModelSerializer):
    """Сериализатор для создания игры."""

    class Meta:
        model = Game
        fields = ["id", "team", "difficulty", "total_periods"]
        read_only_fields = ["id"]

    def validate_team(self, value: Team) -> Team:
        """Проверяет, что у команды нет активной игры."""
        if hasattr(value, "game") and value.game is not None:
            raise serializers.ValidationError(
                "У этой команды уже есть активная игра. "
                "Удалите её перед созданием новой."
            )
        return value

    def validate_total_periods(self, value: int) -> int:
        """Проверяет количество периодов."""
        if value not in ALLOWED_TOTAL_PERIODS:
            allowed = ", ".join(str(periods) for periods in ALLOWED_TOTAL_PERIODS)
            raise serializers.ValidationError(
                f"Количество периодов должно быть одним из: {allowed}."
            )
        return value

    def validate_difficulty(self, value: str) -> str:
        """Проверяет корректность режима сложности."""
        allowed_difficulties = {choice for choice, _ in GameDifficulty.choices}
        if value not in allowed_difficulties:
            raise serializers.ValidationError("Некорректный режим сложности.")
        return value

    def create(self, validated_data: dict) -> Game:
        """Создаёт игру с начальным периодом."""
        game = Game.objects.create(
            **validated_data,
            status=GameStatus.ACTIVE,
        )

        # Создаём первый период с параметрами по умолчанию
        calculator = get_calculator()
        default_params = calculator.get_initial_parameters(game.difficulty)

        GamePeriod.objects.create(
            game=game,
            period_number=1,
            **{k: v for k, v in default_params.items() if hasattr(GamePeriod, k)},
        )

        return game


class GameDetailSerializer(serializers.ModelSerializer):
    """Подробный сериализатор игры."""

    team_name = serializers.CharField(source="team.name", read_only=True)
    group_name = serializers.CharField(source="team.group.name", read_only=True)
    faculty_name = serializers.CharField(
        source="team.group.faculty.name", read_only=True
    )
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    difficulty_display = serializers.CharField(
        source="get_difficulty_display", read_only=True
    )
    decision_states = serializers.SerializerMethodField()
    can_advance_period = serializers.SerializerMethodField()

    class Meta:
        model = Game
        fields = [
            "id",
            "team",
            "team_name",
            "group_name",
            "faculty_name",
            "status",
            "status_display",
            "difficulty",
            "difficulty_display",
            "current_period",
            "total_periods",
            "decision_states",
            "can_advance_period",
            "created_at",
            "updated_at",
        ]

    def get_decision_states(self, obj: Game) -> dict[str, int]:
        """Возвращает состояния решений."""
        return obj.get_decision_states()

    def get_can_advance_period(self, obj: Game) -> bool:
        """Проверяет, можно ли перейти к следующему периоду."""
        return obj.can_advance_period()


# ========================================
# GAME PERIOD SERIALIZERS
# ========================================


class GamePeriodSerializer(serializers.ModelSerializer):
    """Сериализатор периода игры."""

    class Meta:
        model = GamePeriod
        fields = "__all__"
        read_only_fields = ["game", "period_number", "created_at"]


class GamePeriodListSerializer(serializers.ModelSerializer):
    """Краткий сериализатор периода для списка и сводного листа."""

    class Meta:
        model = GamePeriod
        fields = [
            "id",
            "period_number",
            # Население
            "P1", "P2", "P3", "P4", "P5", "P6", "P7", "P8",
            "P9", "P10", "P11", "P12", "P13",
            # Энергетика
            "E7", "E10", "E16",
            "E20", "E21", "E22", "E23", "E24", "E25", "E26", "E27",
            # Промышленность
            "G3", "G6", "G15", "G18", "G19",
            # Сельское хозяйство
            "F3", "F7", "F9", "F14", "F15",
            # Торговля и финансы
            "TF1", "TF5",
            "TF9", "TF10", "TF11", "TF12", "TF13", "TF14", "TF15",
            "TF16", "TF17", "TF18",
            "created_at",
        ]


# ========================================
# PARAMETER SERIALIZERS
# ========================================


class ParameterBoundsSerializer(serializers.Serializer):
    """Сериализатор границ параметра."""

    min = serializers.FloatField(allow_null=True)
    max = serializers.FloatField(allow_null=True)


class ParameterStateSerializer(serializers.Serializer):
    """Сериализатор состояния одного параметра."""

    value = serializers.FloatField()
    verbose_name = serializers.CharField()
    category = serializers.CharField()
    is_input = serializers.BooleanField()
    status = serializers.ChoiceField(
        choices=["filled", "empty", "next_to_fill", "locked", "calculated"]
    )
    bounds = ParameterBoundsSerializer(allow_null=True)
    is_fixed = serializers.BooleanField(default=False)
    depends_on = serializers.ListField(child=serializers.CharField(), allow_empty=True)
    decision_group = serializers.CharField(allow_null=True)


class ParameterInputSerializer(serializers.Serializer):
    """Сериализатор для ввода значения параметра."""

    value = serializers.FloatField()

    def validate_value(self, value: float) -> float:
        """Базовая валидация значения."""
        if value < 0 and not self.context.get("allow_negative", False):
            # Некоторые параметры могут быть отрицательными
            pass
        return value


# ========================================
# GAME STATE SERIALIZERS
# ========================================


class GameInfoSerializer(serializers.Serializer):
    """Сериализатор информации об игре."""

    current_period = serializers.IntegerField()
    total_periods = serializers.IntegerField()
    can_advance_period = serializers.BooleanField()
    status = serializers.CharField(required=False)


class DecisionStageSerializer(serializers.Serializer):
    """Сериализатор этапа принятия решений."""

    key = serializers.CharField()
    order = serializers.IntegerField()
    name = serializers.CharField()
    minister = serializers.CharField(allow_null=True)
    description = serializers.CharField()
    available = serializers.BooleanField()
    completed = serializers.BooleanField()
    missing_requirements = serializers.ListField(
        child=serializers.CharField(), allow_empty=True
    )
    inputs = serializers.ListField(child=serializers.CharField(), allow_empty=True)


class NextActionSerializer(serializers.Serializer):
    """Сериализатор следующего действия."""

    stage_key = serializers.CharField()
    name = serializers.CharField()
    minister = serializers.CharField(allow_null=True)
    inputs = serializers.ListField(child=serializers.CharField(), allow_empty=True)
    priority = serializers.IntegerField()


class MinisterInfoSerializer(serializers.Serializer):
    """Сериализатор информации о министре."""

    name = serializers.CharField()
    decisions = serializers.ListField(child=serializers.CharField(), allow_empty=True)


class GameStateSerializer(serializers.Serializer):
    """
    Полный сериализатор состояния игры.

    Используется для отрисовки UI и для ИИ-агентов.
    Содержит всю необходимую информацию о текущем состоянии игры.
    """

    game_info = GameInfoSerializer()
    decision_states = serializers.DictField(child=serializers.IntegerField())
    parameters = serializers.DictField(child=ParameterStateSerializer())
    available_stages = DecisionStageSerializer(many=True)
    next_actions = NextActionSerializer(many=True)
    ministers = serializers.DictField(child=MinisterInfoSerializer())


# ========================================
# RESPONSE SERIALIZERS
# ========================================


class ParameterUpdateResponseSerializer(serializers.Serializer):
    """Сериализатор ответа на обновление параметра."""

    success = serializers.BooleanField()
    error = serializers.CharField(allow_null=True)
    parameter = serializers.CharField()
    value = serializers.FloatField()
    updated_parameters = serializers.DictField(
        child=serializers.FloatField(), allow_empty=True
    )
    decision_states = serializers.DictField(child=serializers.IntegerField())


class NextPeriodResponseSerializer(serializers.Serializer):
    """Сериализатор ответа на переход к следующему периоду."""

    success = serializers.BooleanField()
    error = serializers.CharField(allow_null=True)
    current_period = serializers.IntegerField()
    game_finished = serializers.BooleanField()


class ValidationErrorSerializer(serializers.Serializer):
    """Сериализатор ошибки валидации."""

    error = serializers.CharField()
    bounds = ParameterBoundsSerializer(allow_null=True)


# ========================================
# CHART DATA SERIALIZERS
# ========================================


class ChartDataPointSerializer(serializers.Serializer):
    """Сериализатор точки данных для графика."""

    period = serializers.IntegerField()
    value = serializers.FloatField()


class ChartDataSerializer(serializers.Serializer):
    """Сериализатор данных для графиков."""

    parameter = serializers.CharField()
    verbose_name = serializers.CharField()
    data = ChartDataPointSerializer(many=True)


class GameChartsSerializer(serializers.Serializer):
    """Сериализатор для всех графиков игры."""

    population = ChartDataSerializer(many=True)
    economy = ChartDataSerializer(many=True)
    energy = ChartDataSerializer(many=True)
    environment = ChartDataSerializer(many=True)
    finance = ChartDataSerializer(many=True)


# ========================================
# ADMIN SERIALIZERS
# ========================================


class CalculationParameterSerializer(serializers.Serializer):
    """Сериализатор одного параметра в расчёте."""

    name = serializers.CharField()
    verbose_name = serializers.CharField()
    formula = serializers.CharField()
    substituted = serializers.CharField()
    result = serializers.FloatField()


class CalculationGroupSerializer(serializers.Serializer):
    """Сериализатор группы расчётов."""

    group = serializers.CharField()
    group_name = serializers.CharField()
    parameters = CalculationParameterSerializer(many=True)


class AdminLoginSerializer(serializers.Serializer):
    """Сериализатор для входа администратора."""

    password = serializers.CharField(write_only=True)


class AdminSessionSerializer(serializers.Serializer):
    """Сериализатор сессии администратора."""

    is_admin = serializers.BooleanField()
    expires_at = serializers.DateTimeField(allow_null=True)


# ========================================
# BATCH PARAMETER SERIALIZERS
# ========================================


class BatchParameterInputSerializer(serializers.Serializer):
    """Сериализатор для пакетного обновления параметров."""
    parameters = serializers.DictField(
        child=serializers.FloatField(),
        help_text="Словарь {код_параметра: значение}"
    )
    minister = serializers.CharField(
        required=False,
        allow_null=True,
        help_text="Ключ министра (если отправка из таблицы министра)"
    )


class BatchParameterUpdateResponseSerializer(serializers.Serializer):
    """Ответ на пакетное обновление параметров."""
    success = serializers.BooleanField()
    updated_parameters = serializers.DictField(child=serializers.FloatField())
    auto_calculated = serializers.DictField(child=serializers.FloatField())
    errors = serializers.DictField(
        child=serializers.CharField(),
        help_text="Словарь {код_параметра: текст_ошибки}"
    )
    validation_state = serializers.DictField()
