import datetime

from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone


class Animal(models.Model):
    class Species(models.TextChoices):
        DOG = "dog", "Dog"
        CAT = "cat", "Cat"
        OTHER = "other", "Other"

    class Sex(models.TextChoices):
        MALE = "m", "Male"
        FEMALE = "f", "Female"
        UNKNOWN = "u", "Unknown"

    class Status(models.TextChoices):
        INTAKE = "intake", "Intake"
        MEDICAL_HOLD = "medical_hold", "Medical Hold"
        FOSTER = "foster", "In Foster"
        AVAILABLE = "available", "Available"
        PENDING = "pending", "Pending"
        ADOPTED = "adopted", "Adopted"

    # Statuses that appear on the public site.
    PUBLIC_STATUSES = {Status.AVAILABLE, Status.PENDING}

    code = models.CharField("Animal ID", max_length=20, unique=True, blank=True)
    name = models.CharField(max_length=80)
    species = models.CharField(max_length=10, choices=Species.choices)
    breed = models.CharField(max_length=80, blank=True, default="")
    sex = models.CharField(max_length=1, choices=Sex.choices, default=Sex.UNKNOWN)
    estimated_birth_date = models.DateField(
        help_text="Derived from estimated age at intake; drives the medical timeline."
    )
    intake_date = models.DateField(default=datetime.date.today)
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.INTAKE)
    photo = models.ImageField(upload_to="animals/", blank=True, null=True)
    description = models.TextField(blank=True, default="", help_text="Public-facing bio.")
    weight_lbs = models.DecimalField(max_digits=6, decimal_places=1, null=True, blank=True)
    internal_notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-intake_date", "name"]

    def __str__(self):
        return f"{self.name} ({self.code})"

    def save(self, *args, **kwargs):
        if not self.code:
            year = self.intake_date.year
            n = Animal.objects.filter(code__startswith=f"LAR-{year}-").count() + 1
            code = f"LAR-{year}-{n:03d}"
            while Animal.objects.filter(code=code).exists():
                n += 1
                code = f"LAR-{year}-{n:03d}"
            self.code = code
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("animal_detail", args=[self.pk])

    # ---- demographics ----
    @property
    def age_display(self):
        days = (datetime.date.today() - self.estimated_birth_date).days
        if days < 0:
            return "—"
        if days < 7 * 16:
            return f"{days // 7} wks"
        months = days // 30
        if months < 24:
            return f"{months} mos"
        return f"{days // 365} yrs"

    @property
    def age_weeks(self):
        return (datetime.date.today() - self.estimated_birth_date).days // 7

    # ---- placement ----
    @property
    def current_placement(self):
        return self.placements.filter(end_date__isnull=True).select_related("household").first()

    @property
    def placement_display(self):
        p = self.current_placement
        return str(p.household) if p else "Facility"

    # ---- medical rollup ----
    @property
    def medical_alert(self):
        """Returns 'overdue' | 'due' | None for the dashboard alert column."""
        today = datetime.date.today()
        window = today + datetime.timedelta(days=settings.MEDICAL_ALERT_WINDOW_DAYS)
        events = [e for e in self.medical_events.all() if e.completed_date is None]
        meds_due = [
            m for m in self.medications.all()
            if m.is_active and not any(
                log.date == today and log.given for log in m.log_entries.all()
            )
        ]
        if any(e.due_date < today for e in events):
            return "overdue"
        if any(e.due_date <= window for e in events) or meds_due:
            return "due"
        return None

    @property
    def incomplete_mandatory_milestones(self):
        """Milestone types that block the Available status and aren't done yet."""
        done_types = {
            e.milestone_type_id for e in self.medical_events.all() if e.completed_date
        }
        pending = {}
        for e in self.medical_events.all():
            if e.milestone_type.mandatory_for_available and e.milestone_type_id not in done_types:
                pending[e.milestone_type_id] = e.milestone_type
        return list(pending.values())

    def can_set_status(self, new_status):
        """Medical Hold Gatekeeper: block 'Available' until mandatory milestones done.

        Returns (ok: bool, reason: str)."""
        if new_status == self.Status.AVAILABLE:
            missing = self.incomplete_mandatory_milestones
            if missing:
                names = ", ".join(m.name for m in missing)
                return False, f"Blocked by Medical Hold Gatekeeper — incomplete: {names}."
        return True, ""


class Placement(models.Model):
    """Relational link between an animal and a household (foster or adoption)."""

    class Type(models.TextChoices):
        FOSTER = "foster", "Foster"
        ADOPTION = "adoption", "Adoption"

    animal = models.ForeignKey(Animal, on_delete=models.CASCADE, related_name="placements")
    household = models.ForeignKey("people.Household", on_delete=models.CASCADE, related_name="placements")
    placement_type = models.CharField(max_length=10, choices=Type.choices)
    start_date = models.DateField(default=datetime.date.today)
    end_date = models.DateField(null=True, blank=True)
    notes = models.CharField(max_length=200, blank=True, default="")

    class Meta:
        ordering = ["-start_date"]

    def __str__(self):
        return f"{self.animal.name} → {self.household.name} ({self.get_placement_type_display()})"

    @property
    def is_active(self):
        return self.end_date is None
