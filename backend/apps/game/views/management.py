"""
ViewSets для управления организационной иерархией.

Включает FacultyViewSet, GroupViewSet, TeamViewSet.
"""

from apps.management.models import Faculty, Group, Team
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import status, viewsets
from rest_framework.request import Request
from rest_framework.response import Response

from ..serializers import (
    FacultyCreateSerializer,
    FacultySerializer,
    GroupCreateSerializer,
    GroupSerializer,
    TeamCreateSerializer,
    TeamSerializer,
)


class FacultyViewSet(viewsets.ModelViewSet):
    """ViewSet для управления факультетами."""

    queryset = Faculty.objects.all()

    def get_serializer_class(self):
        if self.action == "create":
            return FacultyCreateSerializer
        return FacultySerializer

    @extend_schema(
        summary="Список факультетов",
        description="Возвращает список всех факультетов",
        responses={200: FacultySerializer(many=True)},
    )
    def list(self, request: Request) -> Response:
        return super().list(request)

    @extend_schema(
        summary="Создать факультет",
        description="Создаёт новый факультет. Требуются права администратора.",
        request=FacultySerializer,
        responses={
            201: FacultySerializer,
            400: OpenApiResponse(description="Ошибка валидации"),
            403: OpenApiResponse(description="Требуются права администратора"),
        },
    )
    def create(self, request: Request) -> Response:
        if not request.session.get("is_admin", False):
            return Response(
                {"error": "Требуются права администратора"},
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().create(request)

    @extend_schema(
        summary="Удалить факультет",
        description="Удаляет факультет. Требуются права администратора.",
        responses={
            204: OpenApiResponse(description="Факультет удалён"),
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


class GroupViewSet(viewsets.ModelViewSet):
    """ViewSet для управления группами."""

    queryset = Group.objects.select_related("faculty").all()

    def get_serializer_class(self):
        if self.action == "create":
            return GroupCreateSerializer
        return GroupSerializer

    @extend_schema(
        summary="Список групп",
        description="Возвращает список групп. Можно фильтровать по факультету.",
        parameters=[
            OpenApiParameter(
                name="faculty",
                description="ID факультета для фильтрации",
                required=False,
                type=int,
            ),
        ],
        responses={200: GroupSerializer(many=True)},
    )
    def list(self, request: Request) -> Response:
        queryset = self.get_queryset()
        faculty_id = request.query_params.get("faculty")
        if faculty_id:
            queryset = queryset.filter(faculty_id=faculty_id)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @extend_schema(
        summary="Создать группу",
        description="Создаёт новую группу. Требуются права администратора.",
        request=GroupSerializer,
        responses={
            201: GroupSerializer,
            400: OpenApiResponse(description="Ошибка валидации"),
            403: OpenApiResponse(description="Требуются права администратора"),
        },
    )
    def create(self, request: Request) -> Response:
        if not request.session.get("is_admin", False):
            return Response(
                {"error": "Требуются права администратора"},
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().create(request)

    @extend_schema(
        summary="Удалить группу",
        description="Удаляет группу. Требуются права администратора.",
        responses={
            204: OpenApiResponse(description="Группа удалена"),
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


class TeamViewSet(viewsets.ModelViewSet):
    """ViewSet для управления командами."""

    queryset = Team.objects.select_related("group__faculty").all()

    def get_serializer_class(self):
        if self.action == "create":
            return TeamCreateSerializer
        return TeamSerializer

    @extend_schema(
        summary="Список команд",
        description="Возвращает список команд. Можно фильтровать по группе.",
        parameters=[
            OpenApiParameter(
                name="group",
                description="ID группы для фильтрации",
                required=False,
                type=int,
            ),
        ],
        responses={200: TeamSerializer(many=True)},
    )
    def list(self, request: Request) -> Response:
        queryset = self.get_queryset()
        group_id = request.query_params.get("group")
        if group_id:
            queryset = queryset.filter(group_id=group_id)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @extend_schema(
        summary="Создать команду",
        description="Создаёт новую команду. Требуются права администратора.",
        request=TeamSerializer,
        responses={
            201: TeamSerializer,
            400: OpenApiResponse(description="Ошибка валидации"),
            403: OpenApiResponse(description="Требуются права администратора"),
        },
    )
    def create(self, request: Request) -> Response:
        if not request.session.get("is_admin", False):
            return Response(
                {"error": "Требуются права администратора"},
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().create(request)

    @extend_schema(
        summary="Удалить команду",
        description="Удаляет команду. Требуются права администратора.",
        responses={
            204: OpenApiResponse(description="Команда удалена"),
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
