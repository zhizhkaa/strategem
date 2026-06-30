import tempfile

from apps.management.models import Faculty, Group, Team
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from apps.game.configuration import get_active_config_contents
from apps.game.engine.calculator import get_calculator
from apps.game.engine.interpolation import interpolate
from apps.game.models import (
    ConfigFile,
    Document,
    Game,
    GameDifficulty,
    GamePeriod,
    GameStatus,
)


def create_team(name: str = "Команда", password: str = "team-secret") -> Team:
    faculty = Faculty.objects.create(name=f"Факультет {name}")
    group = Group.objects.create(name=f"Группа {name}", faculty=faculty, year=2026)
    return Team.objects.create(name=name, group=group, access_password=password)


def create_game(
    *,
    team: Team | None = None,
    difficulty: str = GameDifficulty.SIMPLE,
    total_periods: int = 10,
) -> Game:
    game = Game.objects.create(
        team=team or create_team(),
        status=GameStatus.ACTIVE,
        difficulty=difficulty,
        total_periods=total_periods,
        config_snapshot_label="Test",
    )
    initial_params = get_calculator().get_initial_parameters(difficulty)
    GamePeriod.objects.create(
        game=game,
        period_number=1,
        **{key: value for key, value in initial_params.items() if hasattr(GamePeriod, key)},
    )
    return game


class GameApiTests(APITestCase):
    def setUp(self):
        self.team = create_team(password="secret123")

    def login_admin(self) -> None:
        session = self.client.session
        session["is_admin"] = True
        session.save()

    def test_admin_creates_game_with_initial_period_and_config_snapshot(self):
        self.login_admin()

        response = self.client.post(
            "/api/games/",
            {
                "team": self.team.id,
                "difficulty": GameDifficulty.SIMPLE,
                "total_periods": 12,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        game = Game.objects.get(id=response.data["id"])
        period = game.periods.get(period_number=1)

        self.assertEqual(game.status, GameStatus.ACTIVE)
        self.assertEqual(game.current_period, 1)
        self.assertEqual(game.total_periods, 12)
        self.assertEqual(game.difficulty, GameDifficulty.SIMPLE)
        self.assertEqual(period.E7, 15000)
        self.assertIn("files", game.config_snapshot)
        self.assertIn("parameters.yaml", game.config_snapshot["files"])

    def test_game_creation_requires_admin_and_supported_period_count(self):
        response = self.client.post(
            "/api/games/",
            {"team": self.team.id, "difficulty": GameDifficulty.SIMPLE, "total_periods": 10},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        self.login_admin()
        response = self.client.post(
            "/api/games/",
            {"team": self.team.id, "difficulty": GameDifficulty.SIMPLE, "total_periods": 15},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("total_periods", response.data)

    def test_team_game_endpoint_checks_team_password_once_per_session(self):
        game = create_game(team=self.team)

        response = self.client.get(f"/api/teams/{self.team.id}/game/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        response = self.client.post(
            f"/api/teams/{self.team.id}/game/",
            {"password": "wrong"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        response = self.client.post(
            f"/api/teams/{self.team.id}/game/",
            {"password": "secret123"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["game"]["id"], game.id)

        response = self.client.get(f"/api/teams/{self.team.id}/game/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["game"]["id"], game.id)

    def test_game_state_and_decision_structure_are_available_for_frontend(self):
        game = create_game(team=self.team)

        state_response = self.client.get(f"/api/games/{game.id}/state/")
        self.assertEqual(state_response.status_code, status.HTTP_200_OK)
        self.assertEqual(state_response.data["game_info"]["current_period"], 1)
        self.assertEqual(state_response.data["parameters"]["P9"]["status"], "next_to_fill")
        self.assertIn("food_distribution", {stage["key"] for stage in state_response.data["available_stages"]})

        structure_response = self.client.get(
            f"/api/games/decision-structure/?game_id={game.id}"
        )
        self.assertEqual(structure_response.status_code, status.HTTP_200_OK)
        self.assertIn("summary_groups", structure_response.data)
        self.assertIn("population", structure_response.data["ministers"])

    def test_batch_saves_valid_population_decision(self):
        game = create_game(team=self.team)

        response = self.client.post(
            f"/api/games/{game.id}/parameters/batch/",
            {"parameters": {"P9": 1900, "P10": 1400}, "minister": "population"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"], msg=response.data)

        period = game.periods.get(period_number=1)
        self.assertEqual(period.P9, 1900)
        self.assertEqual(period.P10, 1400)
        self.assertIn("P9", period.user_inputs)
        self.assertIn("P10", period.user_inputs)

    def test_batch_reports_balance_error_without_advancing_decision_state(self):
        game = create_game(team=self.team, difficulty=GameDifficulty.STANDARD)

        response = self.client.post(
            f"/api/games/{game.id}/parameters/batch/",
            {"parameters": {"P9": 3000, "P10": 200}, "minister": "population"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data["success"])
        self.assertEqual(response.data["errors"]["P9"], "Баланс P2 не соблюдается")
        self.assertEqual(response.data["errors"]["P10"], "Баланс P2 не соблюдается")

        game.refresh_from_db()
        self.assertEqual(game.decision_finance, 0)

    def test_operator_controlled_foreign_aid_requires_admin_batch(self):
        game = create_game(team=self.team)
        game.decision_finance = 3
        game.save(update_fields=["decision_finance"])

        response = self.client.post(
            f"/api/games/{game.id}/parameters/batch/",
            {"parameters": {"TF9": 100}, "minister": "trade_finance"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("TF9", response.data["errors"])

    def test_validate_period_reports_invalid_entered_values(self):
        game = create_game(team=self.team)
        period = game.get_current_period_obj()
        period.P2 = 100
        period.P9 = 101
        period.user_inputs = ["P9"]
        period.save()

        response = self.client.post(f"/api/games/{game.id}/validate-period/", format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data["valid"])
        self.assertFalse(response.data["can_advance"])
        self.assertIn("P9", response.data["validation_state"]["errors"])

    def test_next_period_is_blocked_until_required_decisions_are_complete(self):
        game = create_game(team=self.team)

        response = self.client.post(f"/api/games/{game.id}/next-period/", format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["success"])
        self.assertEqual(response.data["current_period"], 1)

    def test_pause_resume_and_archive_are_admin_actions(self):
        game = create_game(team=self.team)

        response = self.client.post(f"/api/games/{game.id}/pause/", format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        self.login_admin()
        response = self.client.post(f"/api/games/{game.id}/pause/", format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], GameStatus.PAUSED)

        response = self.client.post(f"/api/games/{game.id}/resume/", format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], GameStatus.ACTIVE)

        response = self.client.post(f"/api/games/{game.id}/archive/", format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        list_response = self.client.get("/api/games/")
        self.assertEqual(list_response.data, [])

        archive_response = self.client.get("/api/games/?archived=1")
        self.assertEqual(len(archive_response.data), 1)

    def test_excel_export_returns_workbook(self):
        self.login_admin()
        game = create_game(team=self.team)

        game_response = self.client.get(f"/api/games/{game.id}/export/excel/")
        self.assertEqual(game_response.status_code, status.HTTP_200_OK)
        self.assertEqual(game_response.content[:2], b"PK")

        group_response = self.client.get(f"/api/groups/{self.team.group.id}/export/excel/")
        self.assertEqual(group_response.status_code, status.HTTP_200_OK)
        self.assertEqual(group_response.content[:2], b"PK")


class GameModelAndCalculatorTests(TestCase):
    def test_advance_period_creates_next_period_and_resets_decisions(self):
        game = create_game()
        game.set_decision_states({"capital": 4, "energy": 1, "finance": 3, "import": 3})
        game.save()

        advanced = game.advance_period()

        self.assertTrue(advanced)
        game.refresh_from_db()
        self.assertEqual(game.current_period, 2)
        self.assertEqual(game.get_decision_states(), {"capital": 0, "energy": 0, "finance": 0, "import": 0})
        self.assertTrue(game.periods.filter(period_number=2).exists())

    def test_calculator_matches_core_formula_rules(self):
        calculator = get_calculator()
        params = calculator.get_default_parameters()
        params.update({"P12": 1000, "E26": 0, "G18": 100, "F14": 100})

        is_valid, error, bounds = calculator.validate_input(params, "E27", 250, [])

        self.assertFalse(is_valid)
        self.assertIsNotNone(error)
        self.assertEqual(bounds, (0.0, 200.0))
        self.assertEqual(interpolate("P3", 1.0), 0.03)


class ConfigApiTests(APITestCase):
    def setUp(self):
        session = self.client.session
        session["is_admin"] = True
        session.save()

    def test_admin_can_validate_update_and_reset_yaml_config(self):
        content = get_active_config_contents()["parameters.yaml"]

        validate_response = self.client.post(
            "/api/admin/config-files/parameters.yaml/validate/",
            {"content": content},
            format="json",
        )
        self.assertEqual(validate_response.status_code, status.HTTP_200_OK)
        self.assertTrue(validate_response.data["valid"], msg=validate_response.data)

        patch_response = self.client.patch(
            "/api/admin/config-files/parameters.yaml/",
            {"content": content},
            format="json",
        )
        self.assertEqual(patch_response.status_code, status.HTTP_200_OK)
        self.assertEqual(ConfigFile.objects.get(filename="parameters.yaml").version, 1)

        reset_response = self.client.post(
            "/api/admin/config-files/parameters.yaml/reset/",
            format="json",
        )
        self.assertEqual(reset_response.status_code, status.HTTP_200_OK)
        self.assertFalse(ConfigFile.objects.filter(filename="parameters.yaml").exists())

    def test_global_settings_api_updates_runtime_flags(self):
        response = self.client.patch(
            "/api/admin/settings/",
            {
                "use_team_passwords": False,
                "auto_calculate_decision_residuals": True,
                "parallel_decision_mode": True,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data["use_team_passwords"])
        self.assertTrue(response.data["auto_calculate_decision_residuals"])
        self.assertTrue(response.data["parallel_decision_mode"])


class DocumentApiTests(APITestCase):
    def setUp(self):
        self.media_tmp = tempfile.TemporaryDirectory()
        self.settings_override = override_settings(MEDIA_ROOT=self.media_tmp.name)
        self.settings_override.enable()

        session = self.client.session
        session["is_admin"] = True
        session.save()

    def tearDown(self):
        self.settings_override.disable()
        self.media_tmp.cleanup()

    def test_builtin_documents_are_returned_for_players(self):
        response = self.client.get("/api/documents/?include_builtin=1")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        slots = {doc["slot"]: doc for doc in response.data["documents"]}
        self.assertIn("glossary", slots)
        self.assertIn("minister_energy", slots)
        self.assertTrue(slots["glossary"]["uses_default_file"])

    def test_admin_uploads_pdf_and_players_download_it(self):
        upload = SimpleUploadedFile(
            "guide.pdf",
            b"%PDF-1.4 guide",
            content_type="application/pdf",
        )

        response = self.client.post(
            "/api/documents/",
            {"file": upload, "title": "Памятка", "scope": "general"},
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        doc = Document.objects.get()

        download_response = self.client.get(f"/api/documents/{doc.id}/download/")
        self.assertEqual(download_response.status_code, status.HTTP_200_OK)
        self.assertIn("attachment", download_response.headers["Content-Disposition"])
        self.assertEqual(b"".join(download_response.streaming_content), b"%PDF-1.4 guide")

    def test_document_upload_rejects_non_pdf_files(self):
        upload = SimpleUploadedFile("guide.txt", b"text", content_type="text/plain")

        response = self.client.post(
            "/api/documents/",
            {"file": upload, "title": "Памятка", "scope": "general"},
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("PDF", response.data["error"])
