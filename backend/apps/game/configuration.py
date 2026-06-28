"""Runtime game configuration loaded from built-in YAML files and DB overrides."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

import yaml
from django.utils import timezone

from .models import CONFIG_FILE_CHOICES, ConfigFile, GlobalGameSettings, read_builtin_config_file

CONFIG_FILENAMES = [filename for filename, _label in CONFIG_FILE_CHOICES]
CONFIG_LABELS = dict(CONFIG_FILE_CHOICES)


def parse_yaml(content: str) -> Any:
    return yaml.safe_load(content) or {}


def get_builtin_config_contents() -> dict[str, str]:
    return {filename: read_builtin_config_file(filename) for filename in CONFIG_FILENAMES}


def get_active_config_contents() -> dict[str, str]:
    contents = get_builtin_config_contents()
    for override in ConfigFile.objects.all():
        if override.filename in contents:
            contents[override.filename] = override.content
    return contents


def get_active_config_data() -> dict[str, Any]:
    return {filename: parse_yaml(content) for filename, content in get_active_config_contents().items()}


def get_game_config_snapshot() -> dict[str, Any]:
    return {
        "created_at": timezone.now().isoformat(),
        "files": get_active_config_contents(),
        "settings": settings_payload(GlobalGameSettings.get_solo()),
    }


def get_config_label() -> str:
    max_version = 0
    for override in ConfigFile.objects.all():
        max_version = max(max_version, override.version)
    if max_version:
        return f"Изменённая v{max_version}"
    settings_obj = GlobalGameSettings.get_solo()
    if (
        not settings_obj.use_team_passwords
        or settings_obj.auto_calculate_decision_residuals
        or settings_obj.parallel_decision_mode
    ):
        return "Настроенная"
    return "Исходная"


def settings_payload(settings_obj: GlobalGameSettings) -> dict[str, bool]:
    return {
        "use_team_passwords": settings_obj.use_team_passwords,
        "auto_calculate_decision_residuals": settings_obj.auto_calculate_decision_residuals,
        "parallel_decision_mode": settings_obj.parallel_decision_mode,
    }


def apply_runtime_settings(config_data: dict[str, Any], runtime_settings: dict[str, bool] | None) -> dict[str, Any]:
    data = deepcopy(config_data)
    runtime_settings = runtime_settings or {}
    decision_order = data.setdefault("decision_order.yaml", {})
    if isinstance(decision_order, dict):
        if "auto_calculate_decision_residuals" in runtime_settings:
            decision_order["auto_calculate_decision_residuals"] = bool(
                runtime_settings["auto_calculate_decision_residuals"]
            )
        if "parallel_decision_mode" in runtime_settings:
            decision_order["parallel_mode"] = bool(runtime_settings["parallel_decision_mode"])
    return data


def config_data_from_snapshot(snapshot: dict[str, Any] | None) -> dict[str, Any] | None:
    if not snapshot:
        return None
    files = snapshot.get("files")
    if not isinstance(files, dict):
        return None
    data = {
        filename: parse_yaml(str(files.get(filename, "")))
        for filename in CONFIG_FILENAMES
        if filename in files
    }
    return apply_runtime_settings(data, snapshot.get("settings") or {})


def get_game_config_data(game) -> dict[str, Any] | None:
    snapshot_data = config_data_from_snapshot(getattr(game, "config_snapshot", None))
    if snapshot_data is not None:
        return snapshot_data
    return None


def get_active_config_data_with_settings() -> dict[str, Any]:
    return apply_runtime_settings(
        get_active_config_data(),
        settings_payload(GlobalGameSettings.get_solo()),
    )


def get_calculator_for_game(game):
    from .engine.calculator import GameCalculator, get_calculator

    config_data = get_game_config_data(game)
    if config_data is None:
        return get_calculator()
    return GameCalculator(config_data=config_data)


def get_state_manager_for_game(game):
    from .engine.state_manager import GameStateManager, get_state_manager

    config_data = get_game_config_data(game)
    if config_data is None:
        return get_state_manager()
    calculator = get_calculator_for_game(game)
    return GameStateManager(calculator=calculator, config_data=config_data)


def bump_or_create_config(filename: str, content: str) -> ConfigFile:
    config_file = ConfigFile.objects.filter(filename=filename).first()
    if config_file is None:
        return ConfigFile.objects.create(filename=filename, content=content, version=1)
    config_file.content = content
    config_file.version += 1
    config_file.save(update_fields=["content", "version", "updated_at"])
    return config_file
