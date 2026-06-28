"""Django admin configuration for games and game periods."""

from django.contrib import admin

from .models import ConfigFile, Game, GamePeriod, GlobalGameSettings


class GamePeriodInline(admin.TabularInline):
    """Readonly inline list of periods on the game admin page."""

    model = GamePeriod
    extra = 0
    fields = ["period_number"]
    readonly_fields = ["period_number"]
    can_delete = False
    show_change_link = True


@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    """Admin page for game lifecycle, difficulty, and related team."""

    list_display = [
        "id",
        "team",
        "status",
        "difficulty",
        "current_period",
        "total_periods",
        "is_archived",
        "finished_at",
        "created_at",
        "updated_at",
    ]
    search_fields = ["team__name", "team__group__name"]
    list_filter = [
        "status",
        "difficulty",
        "is_archived",
        "created_at",
        "team__group__faculty",
    ]
    ordering = ["-created_at"]
    autocomplete_fields = ["team"]
    inlines = [GamePeriodInline]


@admin.register(GamePeriod)
class GamePeriodAdmin(admin.ModelAdmin):
    """Admin page for inspecting all parameter values in a period."""

    list_display = ["id", "game", "period_number"]
    search_fields = ["game__team__name", "period_number"]
    list_filter = ["game__status", "period_number"]
    ordering = ["game", "period_number"]
    autocomplete_fields = ["game"]

    fieldsets = (
        (
            "Основная информация",
            {"fields": ("game", "period_number")},
        ),
        (
            "Население (P)",
            {
                "fields": (
                    ("P1", "P2", "P3", "P4"),
                    ("P5", "P6", "P7", "P8"),
                    ("P9", "P10", "P11", "P12"),
                    ("P13",),
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "Энергетика (E)",
            {
                "fields": (
                    ("E1", "E2", "E3", "E4"),
                    ("E5", "E6", "E7", "E8"),
                    ("E9", "E10", "E11", "E12"),
                    ("E13", "E14", "E15", "E16"),
                    ("E17", "E18", "E19", "E20"),
                    ("E21", "E22", "E23", "E24"),
                    ("E25", "E26", "E27"),
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "Промышленность (G)",
            {
                "fields": (
                    ("G1", "G2", "G3", "G4"),
                    ("G5", "G6", "G7", "G8"),
                    ("G9", "G10", "G11", "G12"),
                    ("G13", "G14", "G15", "G16"),
                    ("G17", "G18", "G19"),
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "Сельское хозяйство (F)",
            {
                "fields": (
                    ("F1", "F2", "F3", "F4"),
                    ("F5", "F6", "F7", "F8"),
                    ("F9", "F10", "F11", "F12"),
                    ("F13", "F14", "F15"),
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "Торговля и финансы (TF)",
            {
                "fields": (
                    ("TF1", "TF2", "TF3", "TF4"),
                    ("TF5", "TF6", "TF7", "TF8"),
                    ("TF9", "TF10", "TF11", "TF12"),
                    ("TF13", "TF14", "TF15", "TF16"),
                    ("TF17", "TF18"),
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "Решения",
            {
                "fields": (
                    ("decision_capital", "decision_energy"),
                    ("decision_finance", "decision_import"),
                )
            },
        ),
    )


@admin.register(ConfigFile)
class ConfigFileAdmin(admin.ModelAdmin):
    list_display = ["filename", "version", "updated_at"]
    search_fields = ["filename", "content"]
    readonly_fields = ["version", "updated_at"]


@admin.register(GlobalGameSettings)
class GlobalGameSettingsAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "use_team_passwords",
        "auto_calculate_decision_residuals",
        "parallel_decision_mode",
        "updated_at",
    ]
    readonly_fields = ["updated_at"]
