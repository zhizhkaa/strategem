import json
from pathlib import Path

from apps.management.models import Faculty, Group, Team
from apps.game.engine import FormulaValidator, get_calculator, get_state_manager
from apps.game.engine.state_manager import DecisionState
from apps.game.models import Game, GameDifficulty, GameStatus
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APITestCase


class GameApiTests(APITestCase):
    def setUp(self):
        self.faculty = Faculty.objects.create(name="ИТ")
        self.group = Group.objects.create(name="ИМК-101", faculty=self.faculty, year=2026)
        self.team_counter = 0
        self._set_admin_session()

    def _set_admin_session(self) -> None:
        session = self.client.session
        session["is_admin"] = True
        session.save()

    def _create_team(self) -> Team:
        self.team_counter += 1
        return Team.objects.create(name=f"Команда {self.team_counter}", group=self.group)

    def _create_game(
        self,
        difficulty: str = GameDifficulty.STANDARD,
        total_periods: int = 15,
    ) -> Game:
        team = self._create_team()
        response = self.client.post(
            "/api/games/",
            {
                "team": team.id,
                "difficulty": difficulty,
                "total_periods": total_periods,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        return Game.objects.get(team=team)

    def test_create_game_uses_standard_profile_and_15_periods(self):
        team = self._create_team()

        response = self.client.post(
            "/api/games/",
            {
                "team": team.id,
                "difficulty": GameDifficulty.STANDARD,
                "total_periods": 15,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        game = Game.objects.get(team=team)
        period = game.periods.get(period_number=1)

        self.assertEqual(game.status, GameStatus.ACTIVE)
        self.assertEqual(game.difficulty, GameDifficulty.STANDARD)
        self.assertEqual(game.total_periods, 15)
        self.assertEqual(period.E7, 14500)
        self.assertEqual(period.E17, 12000)
        self.assertEqual(period.E19, 1500)
        self.assertEqual(period.TF1, 1000)
        self.assertEqual(period.TF5, 0)

    def test_create_game_with_higheq_profile_sets_initial_period(self):
        team = self._create_team()

        response = self.client.post(
            "/api/games/",
            {
                "team": team.id,
                "difficulty": GameDifficulty.HIGHEQ,
                "total_periods": 10,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        game = Game.objects.get(team=team)
        period = game.periods.get(period_number=1)

        self.assertEqual(period.P1, 400)
        self.assertEqual(period.P3, 38530)
        self.assertEqual(period.E17, 25000)
        self.assertEqual(period.F7, 0.8)
        self.assertEqual(period.TF1, 5000)

    def test_create_game_with_simple_profile_matches_pdf_initial_values(self):
        team = self._create_team()

        response = self.client.post(
            "/api/games/",
            {
                "team": team.id,
                "difficulty": GameDifficulty.SIMPLE,
                "total_periods": 10,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        game = Game.objects.get(team=team)
        period = game.periods.get(period_number=1)

        self.assertEqual(period.E7, 15000)
        self.assertEqual(period.E17, 14500)
        self.assertEqual(period.E19, 500)
        self.assertEqual(period.TF1, 0)
        self.assertEqual(period.TF4, 300)
        self.assertEqual(period.TF5, 1000)

    def test_list_and_detail_include_difficulty(self):
        team = self._create_team()
        game = Game.objects.create(
            team=team,
            status=GameStatus.ACTIVE,
            difficulty=GameDifficulty.TOUGH,
            total_periods=10,
        )

        list_response = self.client.get("/api/games/")
        detail_response = self.client.get(f"/api/games/{game.id}/")

        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(detail_response.status_code, status.HTTP_200_OK)
        self.assertEqual(list_response.data[0]["difficulty"], GameDifficulty.TOUGH)
        self.assertEqual(list_response.data[0]["difficulty_display"], "Tough")
        self.assertEqual(detail_response.data["difficulty"], GameDifficulty.TOUGH)
        self.assertEqual(detail_response.data["difficulty_display"], "Tough")

    def test_rejects_legacy_12_periods(self):
        team = self._create_team()

        response = self.client.post(
            "/api/games/",
            {
                "team": team.id,
                "difficulty": GameDifficulty.STANDARD,
                "total_periods": 12,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("total_periods", response.data)

    def test_batch_parameter_submission_returns_blocking_incomplete_state(self):
        game = self._create_game()
        period = game.get_current_period_obj()
        calculator = get_calculator()
        state_manager = get_state_manager()

        response = self.client.post(
            f"/api/games/{game.id}/parameters/batch/",
            {"parameters": {"P9": 1000}, "minister": "population"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["updated_parameters"]["P9"], 1000)
        self.assertIn("validation_state", response.data)
        self.assertEqual(response.data["validation_state"]["errors"], [])

        decision_state = DecisionState()
        decision_state.from_dict(game.get_decision_states())
        decision_state.set("finance", 1)
        fillable_after_p9 = state_manager._get_fillable_params(decision_state)
        expected_incomplete = {
            param
            for param in fillable_after_p9
            if param != "P9" and not calculator.is_fixed_parameter(param)
        }
        actual_incomplete = set(response.data["validation_state"]["incomplete"])

        self.assertTrue(expected_incomplete)
        self.assertSetEqual(actual_incomplete, expected_incomplete)
        self.assertIn("population", response.data["validation_state"]["by_minister"])
        self.assertIn(
            "P11",
            response.data["validation_state"]["by_minister"]["population"]["incomplete"],
        )

        period.refresh_from_db()
        self.assertSetEqual(
            set(period.validation_state["incomplete"]),
            expected_incomplete,
        )

    def test_calculator_reset_restores_initial_period_when_periods_were_cleared(self):
        game = self._create_game(total_periods=10)
        game.periods.all().delete()

        reset_response = self.client.post(f"/api/admin/calculator/{game.id}/reset/")
        state_response = self.client.get(f"/api/admin/calculator/{game.id}/state/")

        self.assertEqual(reset_response.status_code, status.HTTP_200_OK)
        self.assertEqual(state_response.status_code, status.HTTP_200_OK)
        self.assertEqual(state_response.data["current_period"], 1)
        self.assertEqual(len(state_response.data["periods"]), 1)
        self.assertEqual(state_response.data["periods"][0]["period_number"], 1)

        game.refresh_from_db()
        self.assertEqual(game.current_period, 1)
        self.assertEqual(game.periods.count(), 1)

    def test_admin_calculator_preserves_completed_decision_snapshot(self):
        game = self._create_game(
            difficulty=GameDifficulty.SIMPLE,
            total_periods=10,
        )
        period_1_inputs = {
            "P9": 1900,
            "P10": 1400,
            "P11": 2000,
            "P12": 1500,
            "P13": 0,
            "E20": 400,
            "E21": 0,
            "E22": 0,
            "E23": 14600,
            "E24": 8000,
            "E25": 6600,
            "E26": 500,
            "E27": 300,
            "G18": 100,
            "G19": 400,
            "F14": 200,
            "F15": 0,
            "TF9": 0,
            "TF10": 0,
            "TF11": 0,
            "TF12": 1400,
            "TF13": 1000,
            "TF14": 0,
            "TF15": 2400,
            "TF16": 1000,
            "TF17": 1400,
            "TF18": 0,
        }

        response = self.client.post(
            f"/api/admin/calculator/{game.id}/calculate/",
            {"parameters": period_1_inputs},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        game.refresh_from_db()
        completed_period = game.periods.get(period_number=1)
        next_period = game.periods.get(period_number=2)

        self.assertEqual(game.current_period, 2)
        self.assertEqual(completed_period.P10, 1400)
        self.assertEqual(completed_period.P13, 0)
        self.assertEqual(completed_period.TF12, 1400)
        self.assertEqual(completed_period.TF15, 2400)
        self.assertEqual(next_period.P2, 2811)
        self.assertEqual(next_period.P9, 0)
        self.assertNotEqual(next_period.P10, 911)
        self.assertEqual(next_period.P10, 0)
        self.assertEqual(next_period.P11, 0)

    def test_admin_calculator_rejects_capital_investment_overrun(self):
        game = self._create_game(
            difficulty=GameDifficulty.SIMPLE,
            total_periods=10,
        )
        overspent_inputs = {
            "P9": 0,
            "P11": 0,
            "P12": 1000,
            "E21": 0,
            "E22": 0,
            "E24": 0,
            "E26": 700,
            "E27": 400,
            "G18": 200,
            "G19": 100,
            "F14": 115,
            "TF13": 0,
            "TF14": 0,
            "TF16": 0,
            "TF17": 0,
        }

        response = self.client.post(
            f"/api/admin/calculator/{game.id}/calculate/",
            {"parameters": overspent_inputs},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("F14", response.data["errors"])

        period = game.periods.get(period_number=1)
        self.assertEqual(period.F15, 0)

    def test_next_period_preserves_completed_decisions_and_resets_new_decisions(self):
        game = self._create_game(
            difficulty=GameDifficulty.SIMPLE,
            total_periods=10,
        )
        period_1_inputs = [
            ("P9", 1900),
            ("TF12", 1400),
            ("P11", 2000),
            ("P12", 1500),
            ("E21", 0),
            ("E22", 0),
            ("E24", 8000),
            ("E26", 500),
            ("G18", 100),
            ("F14", 200),
            ("E27", 300),
            ("G19", 400),
            ("TF13", 1000),
            ("TF14", 0),
            ("TF16", 1000),
            ("TF17", 1400),
        ]

        for param, value in period_1_inputs:
            response = self.client.post(
                f"/api/games/{game.id}/parameters/{param}/",
                {"value": value, "force": True},
                format="json",
            )
            self.assertEqual(
                response.status_code,
                status.HTTP_200_OK,
                f"{param}: {response.data}",
            )

        period_1 = game.periods.get(period_number=1)
        self.assertEqual(period_1.P10, 1400)
        self.assertEqual(period_1.TF12, 1400)

        response = self.client.post(f"/api/games/{game.id}/next-period/", format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        game.refresh_from_db()
        completed_period = game.periods.get(period_number=1)
        new_period = game.periods.get(period_number=2)

        self.assertEqual(game.current_period, 2)
        self.assertEqual(completed_period.P9, 1900)
        self.assertEqual(completed_period.P10, 1400)
        self.assertEqual(completed_period.TF12, 1400)
        self.assertEqual(new_period.P9, 0)
        self.assertEqual(new_period.P10, 0)
        self.assertEqual(new_period.P11, 0)
        self.assertEqual(new_period.P12, 0)
        self.assertEqual(new_period.TF12, 0)
        self.assertNotEqual(new_period.P10, 911)

    def test_batch_ignores_unchanged_already_filled_parameters(self):
        game = self._create_game(
            difficulty=GameDifficulty.STANDARD,
            total_periods=10,
        )

        first_response = self.client.post(
            f"/api/games/{game.id}/parameters/batch/",
            {"parameters": {"P9": 3300}, "minister": "population"},
            format="json",
        )
        self.assertEqual(first_response.status_code, status.HTTP_200_OK)

        second_response = self.client.post(
            f"/api/games/{game.id}/parameters/batch/",
            {"parameters": {"P9": 3300, "P11": 2000, "P12": 1500}, "minister": "population"},
            format="json",
        )

        self.assertEqual(
            second_response.status_code,
            status.HTTP_200_OK,
            msg=getattr(second_response, "data", second_response.content),
        )
        period = game.periods.get(period_number=1)
        self.assertEqual(period.P9, 3300)
        self.assertEqual(period.P11, 2000)
        self.assertEqual(period.P12, 1500)

    def test_batch_allows_editing_already_filled_parameters(self):
        game = self._create_game(
            difficulty=GameDifficulty.STANDARD,
            total_periods=10,
        )

        first_response = self.client.post(
            f"/api/games/{game.id}/parameters/batch/",
            {"parameters": {"P9": 3300}, "minister": "population"},
            format="json",
        )
        self.assertEqual(first_response.status_code, status.HTTP_200_OK)

        second_response = self.client.post(
            f"/api/games/{game.id}/parameters/batch/",
            {"parameters": {"P11": 2000, "P12": 1500}, "minister": "population"},
            format="json",
        )
        self.assertEqual(second_response.status_code, status.HTTP_200_OK)

        edit_response = self.client.post(
            f"/api/games/{game.id}/parameters/batch/",
            {"parameters": {"P9": 3200}, "minister": "population"},
            format="json",
        )

        self.assertEqual(
            edit_response.status_code,
            status.HTTP_200_OK,
            msg=getattr(edit_response, "data", edit_response.content),
        )
        period = game.periods.get(period_number=1)
        self.assertEqual(period.P9, 3200)
        self.assertEqual(period.P10, 100)

    def test_next_period_repairs_existing_negative_f15_before_using_history(self):
        game = self._create_game(
            difficulty=GameDifficulty.SIMPLE,
            total_periods=10,
        )
        period = game.periods.get(period_number=1)
        period.F6 = 900
        period.F4 = 150
        period.F15 = -515
        period.save()

        game.advance_period()

        period.refresh_from_db()
        next_period = game.periods.get(period_number=2)
        self.assertEqual(period.F15, 0)
        self.assertEqual(next_period.F6, 750)

    def test_validate_period_reports_capital_investment_overrun(self):
        game = self._create_game(
            difficulty=GameDifficulty.SIMPLE,
            total_periods=10,
        )
        period = game.periods.get(period_number=1)
        period.P12 = 1000
        period.E26 = 700
        period.E27 = 400
        period.G18 = 200
        period.G19 = 100
        period.F14 = 115
        period.F15 = 0
        period.user_inputs = ["E26", "E27", "G18", "G19", "F14"]
        period.save()

        response = self.client.post(f"/api/games/{game.id}/validate-period/", format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data["valid"])
        self.assertFalse(response.data["can_advance"])
        self.assertIn("F14", response.data["errors"])

    def test_validate_period_reports_all_decision_residual_overruns(self):
        cases = [
            (
                {"P2": 100, "P9": 101},
                ["P9"],
            ),
            (
                {"P3": 100, "P11": 60, "P12": 41},
                ["P11", "P12"],
            ),
            (
                {"E7": 100, "E20": 20, "E21": 40, "E22": 41},
                ["E20", "E21", "E22"],
            ),
            (
                {"E23": 100, "E24": 101},
                ["E24"],
            ),
            (
                {"TF9": 0, "TF10": 10, "TF11": 10, "TF12": 10, "TF13": 10, "TF14": 41},
                ["TF14"],
            ),
            (
                {"TF15": 100, "TF16": 60, "TF17": 41},
                ["TF16", "TF17"],
            ),
        ]

        for overrides, expected_errors in cases:
            with self.subTest(overrides=overrides):
                game = self._create_game(
                    difficulty=GameDifficulty.SIMPLE,
                    total_periods=10,
                )
                period = game.periods.get(period_number=1)
                for param_name, value in overrides.items():
                    setattr(period, param_name, value)
                period.user_inputs = list(overrides.keys())
                period.save()

                response = self.client.post(
                    f"/api/games/{game.id}/validate-period/",
                    format="json",
                )

                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertFalse(response.data["valid"])
                for param_name in expected_errors:
                    self.assertIn(param_name, response.data["errors"])

    def test_next_period_rejects_capital_investment_overrun(self):
        game = self._create_game(
            difficulty=GameDifficulty.SIMPLE,
            total_periods=10,
        )
        game.decision_capital = 4
        game.decision_energy = 1
        game.decision_finance = 3
        game.decision_import = 3
        game.save()

        period = game.periods.get(period_number=1)
        period.P12 = 1000
        period.E26 = 700
        period.E27 = 400
        period.G18 = 200
        period.G19 = 100
        period.F14 = 115
        period.F15 = 0
        period.user_inputs = [
            "P9",
            "P11",
            "P12",
            "E21",
            "E22",
            "E24",
            "E26",
            "E27",
            "G18",
            "G19",
            "F14",
            "TF13",
            "TF14",
            "TF16",
            "TF17",
        ]
        period.save()

        response = self.client.post(f"/api/games/{game.id}/next-period/", format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(game.periods.count(), 1)
        self.assertIn("F14", response.data["validation_state"]["errors"])

    def test_force_parameter_submission_preserves_explicit_fixed_input(self):
        game = self._create_game(
            difficulty=GameDifficulty.SIMPLE,
            total_periods=10,
        )

        response = self.client.post(
            f"/api/games/{game.id}/parameters/P11/",
            {"value": 2300, "force": True},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.client.post(
            f"/api/games/{game.id}/parameters/E20/",
            {"value": 458, "force": True},
            format="json",
        )
        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            msg=getattr(response, "data", response.content),
        )

        period = game.periods.get(period_number=1)
        self.assertEqual(period.E20, 458)
        self.assertNotEqual(period.E20, 460)

    def test_next_period_allows_forced_snapshot_values_that_differ_from_fixed_formulas(self):
        game = self._create_game(
            difficulty=GameDifficulty.SIMPLE,
            total_periods=10,
        )
        period_inputs = [
            ("P9", 1000),
            ("P10", 2300),
            ("P11", 2300),
            ("P12", 1000),
            ("P13", 200),
            ("E20", 458),
            ("E21", 0),
            ("E22", 0),
            ("E23", 14542),
            ("E24", 1000),
            ("E25", 13542),
            ("E26", 100),
            ("G18", 100),
            ("F14", 100),
            ("E27", 100),
            ("G19", 100),
            ("F15", 600),
            ("TF10", 0),
            ("TF11", 200),
            ("TF12", 2300),
            ("TF13", 0),
            ("TF14", 0),
            ("TF15", 2500),
            ("TF16", 1000),
            ("TF17", 1000),
            ("TF18", 500),
        ]

        for param, value in period_inputs:
            response = self.client.post(
                f"/api/games/{game.id}/parameters/{param}/",
                {"value": value, "force": True},
                format="json",
            )
            self.assertEqual(
                response.status_code,
                status.HTTP_200_OK,
                msg=f"{param}: {getattr(response, 'data', response.content)}",
            )

        period = game.periods.get(period_number=1)
        self.assertEqual(period.E20, 458)

        response = self.client.post(f"/api/games/{game.id}/next-period/", format="json")
        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            msg=getattr(response, "data", response.content),
        )

    def test_validate_period_returns_blocking_incomplete_by_minister(self):
        game = self._create_game()

        batch_response = self.client.post(
            f"/api/games/{game.id}/parameters/batch/",
            {"parameters": {"P9": 1000}, "minister": "population"},
            format="json",
        )
        self.assertEqual(batch_response.status_code, status.HTTP_200_OK)

        response = self.client.post(f"/api/games/{game.id}/validate-period/", format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["valid"])
        self.assertFalse(response.data["can_advance"])
        self.assertEqual(response.data["errors"], [])
        self.assertIn("validation_state", response.data)
        self.assertIn("population", response.data["validation_state"]["by_minister"])
        self.assertIn(
            "P11",
            response.data["validation_state"]["by_minister"]["population"]["incomplete"],
        )
        self.assertGreater(len(response.data["validation_state"]["incomplete"]), 0)

    def test_batch_validation_state_matches_validate_period_contract(self):
        game = self._create_game()

        batch_response = self.client.post(
            f"/api/games/{game.id}/parameters/batch/",
            {"parameters": {"P9": 1000}, "minister": "population"},
            format="json",
        )
        self.assertEqual(batch_response.status_code, status.HTTP_200_OK)

        validate_response = self.client.post(
            f"/api/games/{game.id}/validate-period/",
            format="json",
        )
        self.assertEqual(validate_response.status_code, status.HTTP_200_OK)

        self.assertEqual(
            batch_response.data["validation_state"]["errors"],
            validate_response.data["validation_state"]["errors"],
        )
        self.assertEqual(
            batch_response.data["validation_state"]["incomplete"],
            validate_response.data["validation_state"]["incomplete"],
        )
        self.assertEqual(
            batch_response.data["validation_state"]["by_minister"],
            validate_response.data["validation_state"]["by_minister"],
        )

    def test_batch_rejects_operator_controlled_foreign_aid(self):
        game = self._create_game()
        period = game.get_current_period_obj()

        response = self.client.post(
            f"/api/games/{game.id}/parameters/batch/",
            {"parameters": {"TF9": 100}, "minister": "trade_finance"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["success"])
        self.assertIn("TF9", response.data["errors"])

        period.refresh_from_db()
        self.assertEqual(period.TF9, 0)

    def test_operator_controlled_param_requires_admin_even_with_force(self):
        game = self._create_game()
        session = self.client.session
        session["is_admin"] = False
        session.save()

        response = self.client.post(
            f"/api/games/{game.id}/parameters/TF9/",
            {"value": 100, "force": True},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("оператор", response.data["error"])

        period = game.get_current_period_obj()
        period.refresh_from_db()
        self.assertEqual(period.TF9, 0)

    def test_admin_can_set_operator_controlled_foreign_aid(self):
        game = self._create_game()

        response = self.client.post(
            f"/api/games/{game.id}/parameters/TF9/",
            {"value": 100, "force": True},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        period = game.get_current_period_obj()
        period.refresh_from_db()
        self.assertEqual(period.TF9, 100)

    def test_decision_structure_hides_operator_controlled_params_from_players(self):
        response = self.client.get("/api/games/decision-structure/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        summary_inputs = {
            param
            for group in response.data["summary_groups"]
            for param in group["inputs"]
        }
        trade_finance_inputs = {
            param
            for decision in response.data["ministers"]["trade_finance"]["decisions"]
            for param in decision["inputs"]
        }
        trade_finance_decision_keys = {
            decision["key"]
            for decision in response.data["ministers"]["trade_finance"]["decisions"]
        }

        self.assertNotIn("TF9", summary_inputs)
        self.assertNotIn("TF9", trade_finance_inputs)
        self.assertNotIn("currency_revenue", trade_finance_decision_keys)

    def test_batch_is_atomic_when_dependent_value_is_invalid(self):
        game = self._create_game()
        period = game.get_current_period_obj()

        response = self.client.post(
            f"/api/games/{game.id}/parameters/batch/",
            {"parameters": {"P11": 3000, "P12": 600}, "minister": "population"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["success"])
        self.assertIn("P12", response.data["errors"])

        period.refresh_from_db()
        self.assertEqual(period.P11, 0)
        self.assertEqual(period.P12, 0)


class GameModelFallbackTests(TestCase):
    def setUp(self):
        faculty = Faculty.objects.create(name="Экономика")
        group = Group.objects.create(name="ЭК-201", faculty=faculty, year=2026)
        self.team = Team.objects.create(name="Команда fallback", group=group)

    def test_get_current_period_obj_uses_game_difficulty_profile(self):
        game = Game.objects.create(
            team=self.team,
            status=GameStatus.ACTIVE,
            difficulty=GameDifficulty.TOUGH,
            total_periods=10,
        )

        period = game.get_current_period_obj()

        self.assertEqual(period.P5, 20)
        self.assertEqual(period.F7, 0.6)


class GameCalculatorExcelAlignmentTests(TestCase):
    def setUp(self):
        self.calculator = get_calculator()
        self.calculator.reload_config()

    @staticmethod
    def _load_appendix_h_fixture() -> dict:
        fixture_path = (
            Path(__file__).resolve().parents[3]
            / "docs"
            / "regression"
            / "appendix_h_fixture.json"
        )
        with fixture_path.open(encoding="utf-8") as fixture_file:
            return json.load(fixture_file)

    def test_rounding_matches_excel_and_documented_precision(self):
        self.assertEqual(self.calculator._round_value(2.125, "G10"), 2.13)
        self.assertEqual(self.calculator._round_value(0.58, "E10"), 0.58)
        self.assertEqual(self.calculator._round_value(1810 / 5, "E9"), 360)
        self.assertEqual(self.calculator._round_value(1810 / 5, "E20"), 360)

    def test_goods_interpolation_tables_match_excel_reference_points(self):
        interpolator = self.calculator._interpolator

        self.assertEqual(interpolator.interpolate("G1", 1.0), 1.0)
        self.assertEqual(interpolator.interpolate("G3", 20.0), 14.4)

    def test_energy_interpolation_tables_match_excel_reference_curve(self):
        interpolator = self.calculator._interpolator

        self.assertEqual(interpolator.interpolate("E1", 0.0), 0.03)
        self.assertEqual(interpolator.interpolate("E1_LOW", 2.0), 20.0)

    def test_environment_recovery_edges_match_excel_percent_curve(self):
        interpolator = self.calculator._interpolator

        self.assertEqual(interpolator.interpolate("F4", 0.0), 0.0003)
        self.assertEqual(interpolator.interpolate("F4", 1.0), 0.0001)

    def test_population_formulas_use_excel_period_references(self):
        params = self.calculator.get_default_parameters()
        params.update({"P1": 220, "P6": 2, "P7": 10, "G6": 660})
        history = [{"P1": 200, "P7": 2}]

        p7 = self.calculator._evaluate_formula(
            self.calculator._formulas["calc_population"]["P7"],
            params,
            history,
        )
        p8 = self.calculator._round_value(
            self.calculator._evaluate_formula(
                self.calculator._formulas["calc_population"]["P8"],
                params,
                history,
            ),
            "P8",
        )

        self.assertEqual(p7, 3.3)
        self.assertEqual(p8, 36)

    def test_production_indicators_use_active_current_capital(self):
        params = self.calculator.get_default_parameters()
        params.update(
            {
                "F3": 2000,
                "F7": 0.8,
                "F10": 0.5,
                "G7": 8,
                "G11": 0.5,
            }
        )
        history = [{"F3": 800, "G3": 300}]

        g8 = self.calculator._evaluate_formula(
            self.calculator._formulas["calc_production_indicators"]["G8"],
            params,
            history,
        )
        f9 = self.calculator._evaluate_formula(
            self.calculator._formulas["calc_production_indicators"]["F9"],
            params,
            history,
        )

        self.assertEqual(g8, 7.2)
        self.assertEqual(f9, 5000.0)

    def test_trade_formulas_match_excel_loan_and_price_rules(self):
        params = self.calculator.get_initial_parameters(GameDifficulty.HIGHEQ)
        params["TF1"] = 100
        params["TF3"] = 1.5
        history = [
            {**params, "TF10": 100, "TF11": 200, "TF12": 700},
            {**params, "TF10": 100, "TF11": 200, "TF12": 700},
            {**params, "TF10": 100, "TF11": 200, "TF12": 700},
        ]

        max_loan = self.calculator._evaluate_formula("max_loan()", params, history)
        energy_price = self.calculator._evaluate_formula(
            self.calculator._formulas["calc_trade_finance"]["TF6"],
            params,
            history,
        )

        self.assertEqual(max_loan, 1000)
        self.assertEqual(energy_price, 1.5)

    def test_energy_output_uses_single_excel_reference_curve(self):
        params = self.calculator.get_initial_parameters(GameDifficulty.HIGHEQ)
        params["E3"] = 2000

        e17 = self.calculator._evaluate_formula(
            self.calculator._formulas["calc_energy_balance"]["E17"],
            params,
            [params],
        )

        self.assertEqual(e17, 20000)

    def test_energy_for_population_is_not_overwritten_by_current_decision(self):
        params = self.calculator.get_default_parameters()
        params["E9"] = 400
        params["P11"] = 4500
        params["E20"] = 900

        self.calculator.apply_decision_formulas(params, [])

        self.assertEqual(params["E9"], 400)

    def test_environmental_protection_investment_does_not_go_negative(self):
        params = self.calculator.get_default_parameters()
        params.update(
            {
                "P12": 1000,
                "E26": 700,
                "E27": 400,
                "G18": 200,
                "G19": 100,
                "F14": 115,
            }
        )

        self.calculator.apply_decision_formulas(params, [])

        self.assertEqual(params["F15"], 0)

    def test_high_debt_rule_uses_energy_in_threshold_and_keeps_debt_value(self):
        params = {"TF1": 600, "P2": 300, "P3": 300, "E7": 1000}

        self.calculator._apply_special_rules(params, [])

        self.assertEqual(params["P3"], 300)
        self.assertEqual(params["TF1"], 600)

        params["TF1"] = 900
        self.calculator._apply_special_rules(params, [])

        self.assertEqual(params["P3"], 270)
        self.assertEqual(params["TF1"], 900)

    def test_formula_validator_accepts_configured_formula_helpers(self):
        validator = FormulaValidator()

        errors, warnings = validator.validate_all()

        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])

    def test_initial_profiles_match_manual_appendix_g_core_values(self):
        expected_by_difficulty = {
            GameDifficulty.SIMPLE: {
                "P1": 200,
                "P2": 3300,
                "P3": 3500,
                "P5": 18,
                "P8": 41,
                "E7": 15000,
                "E16": 18.125,
                "E17": 14500,
                "E19": 500,
                "F7": 0.69,
                "F11": 3300,
                "G12": 3000,
                "TF1": 0,
                "TF4": 300,
                "TF5": 1000,
            },
            GameDifficulty.STANDARD: {
                "P1": 200,
                "P2": 3300,
                "P3": 3500,
                "P5": 18,
                "P8": 41,
                "E7": 14500,
                "E16": 15,
                "E17": 12000,
                "E19": 1500,
                "F7": 0.69,
                "F11": 3300,
                "G12": 3000,
                "TF1": 1000,
                "TF4": 300,
                "TF5": 0,
            },
            GameDifficulty.TOUGH: {
                "P2": 3300,
                "P5": 20,
                "E7": 14500,
                "E17": 12000,
                "F7": 0.6,
                "F11": 3300,
                "TF1": 1000,
                "TF5": 0,
            },
            GameDifficulty.VERYHARD: {
                "P2": 3000,
                "P5": 22,
                "E7": 14500,
                "E17": 12000,
                "F7": 0.5,
                "F11": 3000,
                "TF1": 1000,
                "TF5": 0,
            },
            GameDifficulty.HIGHEQ: {
                "P1": 400,
                "P2": 9000,
                "P3": 38530,
                "P4": 4.5,
                "P5": 10,
                "P6": 13.5,
                "P7": 16,
                "P8": 10,
                "E1": 1000,
                "E2": 4000,
                "E3": 5000,
                "E4": 290,
                "E5": 1160,
                "E6": 1450,
                "E7": 35400,
                "E9": 5400,
                "E16": 5,
                "E17": 25000,
                "E19": 10400,
                "F1": 320,
                "F2": 1280,
                "F3": 1600,
                "F4": 330,
                "F5": 1650,
                "F6": 1980,
                "F7": 0.8,
                "F8": 1.6,
                "F11": 8000,
                "F13": 1000,
                "G1": 400,
                "G2": 1600,
                "G3": 2000,
                "G4": 710,
                "G5": 5690,
                "G6": 6400,
                "G9": 16,
                "G12": 36530,
                "G14": 2000,
                "G16": 38530,
                "TF1": 5000,
                "TF4": 1000,
                "TF5": 5000,
            },
        }

        for difficulty, expected_values in expected_by_difficulty.items():
            with self.subTest(difficulty=difficulty):
                params = self.calculator.get_initial_parameters(difficulty)

                for param_name, expected_value in expected_values.items():
                    self.assertEqual(
                        params[param_name],
                        expected_value,
                        msg=f"{difficulty}.{param_name} differs from Appendix G",
                    )

    def test_validate_input_rejects_positive_value_when_dynamic_max_is_zero(self):
        params = self.calculator.get_default_parameters()
        params["E23"] = 0

        is_valid, error, bounds = self.calculator.validate_input(
            params,
            "E24",
            10,
            [],
        )

        self.assertFalse(is_valid)
        self.assertIsNotNone(error)
        self.assertEqual(bounds, (0.0, 0.0))

    def test_f4_and_f5_use_current_environmental_capital_like_legacy_stg(self):
        params = self.calculator.get_default_parameters()
        params["F6"] = 900
        history = [{"F6": 600}]

        f4 = self.calculator._evaluate_formula(
            self.calculator._formulas["calc_agriculture"]["F4"],
            params,
            history,
        )
        f5 = self.calculator._evaluate_formula(
            self.calculator._formulas["calc_capital"]["F5"],
            params,
            history,
        )

        self.assertEqual(f4, 150)
        self.assertEqual(f5, 750)

    def test_e27_is_limited_by_goods_and_food_investments(self):
        params = self.calculator.get_default_parameters()
        params.update(
            {
                "P12": 1000,
                "E26": 0,
                "G18": 100,
                "F14": 100,
            }
        )

        is_valid, error, bounds = self.calculator.validate_input(
            params,
            "E27",
            250,
            [],
        )

        self.assertFalse(is_valid)
        self.assertIsNotNone(error)
        self.assertEqual(bounds, (0.0, 200.0))

    def test_manual_regression_loan_limit_matches_appendix_h_history_logic(self):
        fixture = self._load_appendix_h_fixture()
        params = fixture["snapshot"]
        history = fixture["history"]

        loan_limit = self.calculator._evaluate_formula("max_loan()", params, history)

        self.assertEqual(loan_limit, 4340)

    def test_appendix_h_fixture_snapshot_matches_manual_targets(self):
        fixture = self._load_appendix_h_fixture()
        snapshot = fixture["snapshot"]
        expected = fixture["manual_expected"]

        for key, expected_value in expected.items():
            self.assertEqual(
                snapshot[key],
                expected_value,
                msg=f"{key} differs from Appendix H fixture target",
            )
