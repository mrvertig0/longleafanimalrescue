from django.contrib import admin

from .models import MedicalEvent, Medication, MedLogEntry, MilestoneType


@admin.register(MilestoneType)
class MilestoneTypeAdmin(admin.ModelAdmin):
    list_display = ["name", "code", "species", "mandatory_for_available", "sort"]


@admin.register(MedicalEvent)
class MedicalEventAdmin(admin.ModelAdmin):
    list_display = ["animal", "display_label", "due_date", "completed_date"]
    list_filter = ["milestone_type"]


class MedLogInline(admin.TabularInline):
    model = MedLogEntry
    extra = 0


@admin.register(Medication)
class MedicationAdmin(admin.ModelAdmin):
    list_display = ["name", "animal", "frequency", "start_date", "end_date"]
    inlines = [MedLogInline]
