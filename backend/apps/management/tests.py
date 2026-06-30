from django.test import TestCase
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Faculty, Group, Team


class ManagementModelTests(TestCase):
    def test_faculty_group_and_team_have_readable_names(self):
        faculty = Faculty.objects.create(name="Экономический факультет")
        group = Group.objects.create(name="ЭК-01", faculty=faculty, year=2026)
        team = Team.objects.create(name="Команда 1", group=group)

        self.assertEqual(str(faculty), "Экономический факультет")
        self.assertEqual(str(group), "ЭК-01 | 2026")
        self.assertEqual(str(team), "Команда 1")

    def test_team_password_is_hashed_and_checked(self):
        faculty = Faculty.objects.create(name="Факультет")
        group = Group.objects.create(name="Группа", faculty=faculty, year=2026)
        team = Team.objects.create(name="Команда", group=group, access_password="secret123")

        self.assertNotEqual(team.access_password, "secret123")
        self.assertTrue(team.access_password_is_hashed())
        self.assertTrue(team.check_access_password("secret123"))
        self.assertFalse(team.check_access_password("wrong"))


class ManagementApiTests(APITestCase):
    def test_management_api_creates_and_lists_hierarchy(self):
        faculty_response = self.client.post(
            "/api/management/faculties/",
            {"name": "Факультет"},
            format="json",
        )
        self.assertEqual(faculty_response.status_code, status.HTTP_201_CREATED)

        group_response = self.client.post(
            "/api/management/groups/",
            {
                "name": "Группа",
                "faculty": faculty_response.data["id"],
                "year": 2026,
            },
            format="json",
        )
        self.assertEqual(group_response.status_code, status.HTTP_201_CREATED)

        team_response = self.client.post(
            "/api/management/teams/",
            {"name": "Команда", "group": group_response.data["id"]},
            format="json",
        )
        self.assertEqual(team_response.status_code, status.HTTP_201_CREATED)

        list_response = self.client.get("/api/management/teams/")
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(list_response.data[0]["name"], "Команда")
