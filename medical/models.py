import datetime

from django.db import models
from django.utils import timezone


class MilestoneType(models.Model):
    """Catalog of medical milestones (vaccines, procedures)."""

    code = models.SlugField(max_length=40, unique=True)
    name = models.CharField(max_length=80)
    species = models.CharField(
        max_length=10, blank=True, default="",
        help_text="Limit to 'dog' or 'cat'; blank = all species.",
    )
    mandatory_for_available = models.BooleanField(
        default=False,
        help_text="If set, animals cannot be marked Available until this is completed.",
    )
    sort = models.PositiveIntegerField(default=100)

    class Meta:
        ordering = ["sort", "name"]

    def __str__(self):
        return self.name


class MedicalEvent(models.Model):
    """A projected or completed milestone on an animal's medical timeline."""

    animal = models.ForeignKey("animals.Animal", on_delete=models.CASCADE, related_name="medical_events")
    milestone_type = models.ForeignKey(MilestoneType, on_delete=models.PROTECT, related_name="events")
    label = models.CharField(max_length=100, blank=True, default="", help_text="e.g. “DHPP #2”")
    due_date = models.DateField()
    completed_date = models.DateField(null=True, blank=True)
    completed_by = models.CharField(max_length=80, blank=True, default="")
    notes = models.CharField(max_length=200, blank=True, default="")
    auto_generated = models.BooleanField(default=False)

    class Meta:
        ordering = ["due_date"]

    def __str__(self):
        return f"{self.animal.name}: {self.display_label} due {self.due_date}"

    @property
    def display_label(self):
        return self.label or self.milestone_type.name

    @property
    def state(self):
        if self.completed_date:
            return "done"
        today = datetime.date.today()
        if self.due_date < today:
            return "overdue"
        if self.due_date <= today + datetime.timedelta(days=7):
            return "due"
        return "upcoming"


class Medication(models.Model):
    """An ongoing medication / daily treatment for an animal."""

    animal = models.ForeignKey("animals.Animal", on_delete=models.CASCADE, related_name="medications")
    name = models.CharField(max_length=80)
    dosage = models.CharField(max_length=80, blank=True, default="")
    frequency = models.CharField(max_length=80, default="Once daily")
    start_date = models.DateField(default=datetime.date.today)
    end_date = models.DateField(null=True, blank=True)
    instructions = models.CharField(max_length=200, blank=True, default="")

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} — {self.animal.name}"

    @property
    def is_active(self):
        today = datetime.date.today()
        return self.start_date <= today and (self.end_date is None or self.end_date >= today)

    def active_on(self, day):
        return self.start_date <= day and (self.end_date is None or self.end_date >= day)


def record_upload_path(instance, filename):
    return f"medical_records/{instance.animal_id}/{filename}"


class MedicalRecord(models.Model):
    """An uploaded document (vet report, lab result, discharge paperwork, etc)."""

    animal = models.ForeignKey("animals.Animal", on_delete=models.CASCADE, related_name="medical_records")
    file = models.FileField(upload_to=record_upload_path)
    label = models.CharField(max_length=120, blank=True, default="", help_text="e.g. “Spay discharge paperwork”")
    uploaded_at = models.DateTimeField(default=timezone.now)
    uploaded_by = models.CharField(max_length=80, blank=True, default="")

    class Meta:
        ordering = ["-uploaded_at"]

    def __str__(self):
        return self.label or self.filename

    @property
    def filename(self):
        return self.file.name.rsplit("/", 1)[-1]
