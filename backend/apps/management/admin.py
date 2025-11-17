from django.contrib import admin

from .models import Faculty, Group, Team


@admin.register(Faculty)
class FacultyAdmin(admin.ModelAdmin):
    list_display = ["name", "created_at", "updated_at"]
    search_fields = ["name"]
    list_filter = ["created_at"]
    ordering = ["name"]


@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = ["name", "faculty", "year", "created_at", "updated_at"]
    search_fields = ["name", "faculty__name"]
    list_filter = ["faculty", "year", "created_at"]
    ordering = ["faculty__name", "year", "name"]
    autocomplete_fields = ["faculty"]


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    def faculty(self, obj):
        return obj.group.faculty.name

    def year(self, obj):
        return obj.group.year

    list_display = ["name", "faculty", "group", "created_at", "updated_at"]
    search_fields = ["name", "group__name", "group__faculty__name"]
    list_filter = ["group__faculty", "group__year", "created_at"]
    ordering = ["group__faculty__name", "group__year", "group__name", "name"]
    autocomplete_fields = ["group"]

    faculty.short_description = "Факультет"
    year.short_description = "Год"
