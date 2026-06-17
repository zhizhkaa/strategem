"""Builds the decision-structure DTO returned by the game API."""

from pathlib import Path

import yaml

from .models import PARAMETERS_CONFIG


# Defines how decision stages are grouped on the summary sheet.
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
        "total": {"expr": "TF13 ≤ TF5", "ref": "TF5"},
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

SUMMARY_INFO_PARAMS = ["TF9"]

# Parameters shown as context on each minister sheet.
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
        "info_first": ["TF1", "TF9"],
        "situation": ["TF2", "TF3", "TF4", "TF5", "TF6", "TF7", "TF8"],
        "info": [],
    },
}

MINISTER_INTERPOLATION_KEYS = {
    "population": ["P1", "P2", "P3", "P4"],
    "energy": ["E1", "E2"],
    "industry": ["G1", "G2", "G3"],
    "agriculture": ["F1", "F2", "F3", "F4"],
    "trade_finance": ["TF1", "TF2"],
}

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


def build_decision_structure() -> dict:
    """Return decision metadata for summary and minister sheets."""
    data_dir = Path(__file__).resolve().parent / "data"
    with open(data_dir / "decision_order.yaml", "r", encoding="utf-8") as f:
        order_config = yaml.safe_load(f)

    auto_calculate_decision_residuals = bool(
        order_config.get("auto_calculate_decision_residuals", True)
    )
    stages = {
        k: v
        for k, v in order_config.items()
        if k not in ("calculation_order", "ministers", "parallel_mode", "auto_calculate_decision_residuals")
    }
    ministers_config = order_config.get("ministers", {})

    summary_groups = _build_summary_groups(stages, auto_calculate_decision_residuals)
    minister_configs = _build_minister_configs(
        stages,
        ministers_config,
        auto_calculate_decision_residuals,
    )
    parameters = _build_parameters(summary_groups, minister_configs)
    for code in SUMMARY_INFO_PARAMS:
        config = PARAMETERS_CONFIG.get(code, {})
        parameters[code] = {
            "verbose_name": config.get("verbose_name", code),
            "default": config.get("default", 0),
            "is_input": config.get("is_input", False),
            "category": config.get("category", ""),
            "target_value": PARAMETER_TARGETS.get(code),
        }

    return {
        "summary_groups": summary_groups,
        "summary_info": SUMMARY_INFO_PARAMS,
        "parameters": parameters,
        "ministers": minister_configs,
    }


def _is_team_stage(stage: dict) -> bool:
    """Check whether a stage is filled by the team, not an operator."""
    return stage.get("flow", "team") == "team"


def _get_team_inputs(stage: dict, auto_calculate_decision_residuals: bool) -> list[dict]:
    """Return only team-controlled input descriptors from a stage."""
    inputs = [
        inp
        for inp in stage.get("inputs", [])
        if inp.get("controller", "team") == "team"
    ]
    if not auto_calculate_decision_residuals and _is_team_stage(stage):
        inputs += [
            {
                "param": auto["param"],
                "note": auto.get("note"),
                "validation": auto.get("formula"),
            }
            for auto in stage.get("auto_calculated", [])
            if isinstance(auto, dict) and auto.get("param")
        ]
    return inputs


def _build_summary_groups(
    stages: dict,
    auto_calculate_decision_residuals: bool,
) -> list[dict]:
    """Build groups for the summary decision sheet."""
    summary_groups = []
    for group_def in SUMMARY_GROUP_DEFS:
        inputs_all = []
        auto_all = []
        first_minister = None
        stage_names = []

        for stage_key in group_def["stages"]:
            stage = stages.get(stage_key, {})
            if not _is_team_stage(stage):
                continue
            if first_minister is None:
                first_minister = stage.get("minister")
            stage_names.append(stage.get("name", stage_key))
            inputs_all += [
                inp["param"]
                for inp in _get_team_inputs(stage, auto_calculate_decision_residuals)
            ]
            if auto_calculate_decision_residuals:
                auto_all += [
                    ac["param"] for ac in stage.get("auto_calculated", [])
                ]

        if not inputs_all and not auto_all:
            continue

        label = group_def["label"] or " / ".join(stage_names)
        summary_groups.append(
            {
                "number": group_def["number"],
                "minister": first_minister,
                "label": label,
                "inputs": inputs_all,
                "auto": auto_all,
                "total": group_def["total"],
            }
        )

    return summary_groups


def _build_minister_configs(
    stages: dict,
    ministers_config: dict,
    auto_calculate_decision_residuals: bool,
) -> dict:
    """Build minister sections with context and decision inputs."""
    minister_configs = {}
    for minister_key, minister_data in ministers_config.items():
        context = MINISTER_CONTEXT_PARAMS.get(minister_key, {})
        decisions = []

        for stage_key in minister_data.get("decisions", []):
            stage = stages.get(stage_key, {})
            if not _is_team_stage(stage):
                continue

            team_inputs = _get_team_inputs(stage, auto_calculate_decision_residuals)
            inputs_with_notes = [
                {
                    "param": inp["param"],
                    "note": inp.get("note"),
                    "validation": inp.get("validation"),
                }
                for inp in team_inputs
            ]
            decisions.append(
                {
                    "key": stage_key,
                    "number": stage.get("order", 0),
                    "name": stage.get("name", stage_key),
                    "inputs": [inp["param"] for inp in team_inputs],
                    "inputs_detail": inputs_with_notes,
                    "auto": (
                        [
                            ac["param"]
                            for ac in stage.get("auto_calculated", [])
                        ]
                        if auto_calculate_decision_residuals
                        else []
                    ),
                    "total": next(
                        (
                            group_def["total"]
                            for group_def in SUMMARY_GROUP_DEFS
                            if stage_key in group_def["stages"]
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
            "interpolation_keys": MINISTER_INTERPOLATION_KEYS.get(
                minister_key, []
            ),
        }

    return minister_configs


def _build_parameters(
    summary_groups: list[dict],
    minister_configs: dict,
) -> dict:
    """Build parameter metadata needed by summary and minister sheets."""
    all_codes: set[str] = set()
    for group in summary_groups:
        all_codes.update(group["inputs"])
        all_codes.update(group["auto"])
        if group["total"]:
            all_codes.add(group["total"]["ref"])

    for minister_config in minister_configs.values():
        for section in ("info_first", "situation", "info"):
            all_codes.update(minister_config[section])

    parameters = {}
    for code in all_codes:
        config = PARAMETERS_CONFIG.get(code, {})
        parameters[code] = {
            "verbose_name": config.get("verbose_name", code),
            "default": config.get("default", 0),
            "is_input": config.get("is_input", False),
            "category": config.get("category", ""),
            "target_value": PARAMETER_TARGETS.get(code),
        }

    return parameters
