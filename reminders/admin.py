from django.contrib import admin

from .models import ReminderSent


@admin.register(ReminderSent)
class ReminderSentAdmin(admin.ModelAdmin):
    list_display = ["placement", "kind", "channel", "sent_date", "sent_by"]
    list_filter = ["kind", "channel"]
