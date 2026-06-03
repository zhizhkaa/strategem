"""Django admin configuration for faculties, groups, and teams."""

from django.contrib import admin

from .models import Faculty, Group, Team


@admin.register(Faculty)
class FacultyAdmin(admin.ModelAdmin):
    """Admin page for faculties."""

    list_display = ["name", "created_at", "updated_at"]
    search_fields = ["name"]
    list_filter = ["created_at"]
    ordering = ["name"]


@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    """Admin page for student groups."""

    list_display = ["name", "faculty", "year", "created_at", "updated_at"]
    search_fields = ["name", "faculty__name"]
    list_filter = ["faculty", "year", "created_at"]
    ordering = ["faculty__name", "year", "name"]
    autocomplete_fields = ["faculty"]


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    """Admin page for teams with faculty and year helpers."""

    def faculty(self, obj):
        """Return the faculty name through the team's group."""
        return obj.group.faculty.name

    def year(self, obj):
        """Return the group year for list display."""
        return obj.group.year

    list_display = ["name", "faculty", "group", "created_at", "updated_at"]
    search_fields = ["name", "group__name", "group__faculty__name"]
    list_filter = ["group__faculty", "group__year", "created_at"]
    ordering = ["group__faculty__name", "group__year", "group__name", "name"]
    autocomplete_fields = ["group"]

    faculty.short_description = "Факультет"
    year.short_description = "Год"
