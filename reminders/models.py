import datetime

from django.db import models


class ReminderSent(models.Model):
    """Marks a specific reminder (medication / appointment / check-in) as
    handled for a given day, so it stops showing up as 'due' once sent.

    `kind` + `ref_id` identify the underlying thing (a Medication id, a
    MedicalEvent id, or a Placement id) without needing a generic FK — simple
    and enough for three known categories.
    """

    class Kind(models.TextChoices):
        MEDICATION = "medication", "Medication"
        APPOINTMENT = "appointment", "Appointment"
        CHECKIN = "checkin", "Check-in"

    kind = models.CharField(max_length=15, choices=Kind.choices)
    ref_id = models.PositiveIntegerField()
    placement = models.ForeignKey("animals.Placement", on_delete=models.CASCADE, related_name="reminders_sent")
    channel = models.CharField(max_length=10, default="sms")  # 'sms' or 'email' — which contact was used
    body = models.TextField(blank=True, default="")
    sent_by = models.CharField(max_length=80, blank=True, default="")
    sent_date = models.DateField(default=datetime.date.today)

    class Meta:
        unique_together = [("kind", "ref_id", "placement", "sent_date")]
        ordering = ["-sent_date"]

    def __str__(self):
        return f"{self.get_kind_display()} reminder for {self.placement} on {self.sent_date}"
