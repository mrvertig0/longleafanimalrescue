from django.contrib import admin

from .models import MedicalEvent, MedicalRecord, Medication, MilestoneType


@admin.register(MilestoneType)
class MilestoneTypeAdmin(admin.ModelAdmin):
    list_display = ["name", "code", "species", "mandatory_for_available", "sort"]


@admin.register(MedicalEvent)
class MedicalEventAdmin(admin.ModelAdmin):
    list_display = ["animal", "display_label", "due_date", "completed_date"]
    list_filter = ["milestone_type"]


@admin.register(Medication)
class MedicationAdmin(admin.ModelAdmin):
    list_display = ["name", "animal", "frequency", "start_date", "end_date"]


@admin.register(MedicalRecord)
class MedicalRecordAdmin(admin.ModelAdmin):
    list_display = ["animal", "label", "uploaded_at", "uploaded_by"]
