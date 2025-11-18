"""
Тесты для приложения management
Cодержит тесты для моделей и API

Модели:
- Faculty: создание факультета и проверка валидаци
- Group: создание группы и проверка валидации (привязка к году)
- Team: создание команды и проверка валидации (привязка к группе)

API тесты:
- test_faculty_api:
    - POST создание факультета
    - GET получение списка факультетов
- test_group_api:
    - POST создание группы с привязкой к факультету
- test_team_api:
    - POST создание команды с привязкой к группе
"""

from apps.management.models import Faculty, Group, Team
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APITestCase


class FacultyTest(TestCase):
    faculty_name = "ИТ"

    def setUp(self):
        self.faculty = Faculty.objects.create(name=self.faculty_name)

    def test_create_faculty(self):
        self.assertEqual(self.faculty.name, self.faculty_name)

    def test_faculty_str(self):
        self.assertEqual(str(self.faculty), self.faculty_name)


class GroupTest(TestCase):
    faculty_name = "ИТ"
    group_name = "ИМК-101"
    group_year = 2024

    def setUp(self):
        self.faculty = Faculty.objects.create(name=self.faculty_name)
        self.group = Group.objects.create(
            name=self.group_name, faculty=self.faculty, year=self.group_year
        )

    def test_create_group(self):
        self.assertEqual(self.group.name, self.group_name)
        self.assertEqual(self.group.year, self.group_year)

    def test_group_str(self):
        self.assertEqual(str(self.group), f"{self.group_name} | {self.group_year}")


class TeamTest(TestCase):
    faculty_name = "ИТ"
    group_name = "ИМК-101"
    group_year = 2024
    team_name = "Команда A"

    def setUp(self):
        self.faculty = Faculty.objects.create(name=self.faculty_name)
        self.group = Group.objects.create(
            name=self.group_name, faculty=self.faculty, year=self.group_year
        )
        self.team = Team.objects.create(name=self.team_name, group=self.group)

    def test_create_team(self):
        self.assertEqual(self.team.name, self.team_name)
        self.assertEqual(self.team.group, self.group)

    def test_team_str(self):
        self.assertEqual(str(self.team), self.team_name)


class APITest(APITestCase):
    faculty_name = "ИТ"
    group_name = "ИМК-101"
    group_year = 2024
    team_name = "Команда A"

    def test_faculty_api(self):
        response = self.client.post("/api/faculties/", {"name": self.faculty_name})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        response = self.client.get("/api/faculties/")
        self.assertEqual(len(response.data), 1)

    def test_group_api(self):
        faculty = Faculty.objects.create(name=self.faculty_name)
        data = {"name": self.group_name, "faculty": faculty.id, "year": self.group_year}
        response = self.client.post("/api/groups/", data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_team_api(self):
        faculty = Faculty.objects.create(name=self.faculty_name)
        group = Group.objects.create(
            name=self.group_name, faculty=faculty, year=self.group_year
        )
        data = {"name": self.team_name, "group": group.id}
        response = self.client.post("/api/teams/", data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
