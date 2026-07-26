from django.db import models
from django.urls import reverse
from django.utils import timezone


class Tag(models.Model):
    """Capability / environment tags used to filter households."""

    class Category(models.TextChoices):
        CAPABILITY = "capability", "Capability"
        ENVIRONMENT = "environment", "Environment"
        OTHER = "other", "Other"

    name = models.CharField(max_length=60, unique=True)
    category = models.CharField(max_length=20, choices=Category.choices, default=Category.CAPABILITY)
    # Machine key used by the public-form auto-tagging rules (blank = manual-only tag).
    auto_rule_key = models.CharField(max_length=40, blank=True, default="")

    class Meta:
        ordering = ["category", "name"]

    def __str__(self):
        return self.name


class Household(models.Model):
    """A household profile: primary contact + co-applicants + resident pets."""

    name = models.CharField("Household name", max_length=120, help_text="e.g. “The Rivera Household”")
    primary_first_name = models.CharField(max_length=60)
    primary_last_name = models.CharField(max_length=60)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=30, blank=True, default="")
    address = models.CharField(max_length=200, blank=True, default="")
    city = models.CharField(max_length=80, blank=True, default="")
    state = models.CharField(max_length=2, blank=True, default="NC")
    zip_code = models.CharField(max_length=10, blank=True, default="")

    class HomeType(models.TextChoices):
        HOUSE = "house", "House"
        APARTMENT = "apartment", "Apartment / Condo"
        MOBILE = "mobile", "Mobile home"
        OTHER = "other", "Other"

    home_type = models.CharField(max_length=20, choices=HomeType.choices, default=HomeType.HOUSE)
    owns_home = models.BooleanField(default=True)
    has_fenced_yard = models.BooleanField(default=False)
    environment_notes = models.TextField(blank=True, default="")

    tags = models.ManyToManyField(Tag, blank=True, related_name="households")
    is_active = models.BooleanField(default=True)
    internal_notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("household_detail", args=[self.pk])

    @property
    def primary_contact(self):
        return f"{self.primary_first_name} {self.primary_last_name}"

    @property
    def placement_history(self):
        """Historical log of fosters/adoptions, newest first."""
        return self.placements.select_related("animal").order_by("-start_date")

    @property
    def current_animals(self):
        return [p.animal for p in self.placements.filter(end_date__isnull=True).select_related("animal")]


class Person(models.Model):
    """Co-applicants / other adults in the household."""

    household = models.ForeignKey(Household, on_delete=models.CASCADE, related_name="people")
    first_name = models.CharField(max_length=60)
    last_name = models.CharField(max_length=60)
    relationship = models.CharField(max_length=60, blank=True, default="", help_text="e.g. spouse, roommate")
    email = models.EmailField(blank=True, default="")
    phone = models.CharField(max_length=30, blank=True, default="")

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class ResidentPet(models.Model):
    household = models.ForeignKey(Household, on_delete=models.CASCADE, related_name="resident_pets")
    name = models.CharField(max_length=60)
    species = models.CharField(max_length=40)
    age_years = models.PositiveIntegerField(null=True, blank=True)
    spayed_neutered = models.BooleanField(default=False)
    up_to_date_vaccines = models.BooleanField(default=False)
    notes = models.CharField(max_length=200, blank=True, default="")

    def __str__(self):
        return f"{self.name} ({self.species})"


class Application(models.Model):
    """A foster or adoption application moving through the CRM pipeline."""

    class Type(models.TextChoices):
        FOSTER = "foster", "Foster"
        ADOPTION = "adoption", "Adoption"

    class Stage(models.TextChoices):
        NEW = "new", "New Application"
        REVIEW = "review", "Under Review"
        INTERVIEW = "interview", "Interview"
        APPROVED = "approved", "Approved / Matched"
        INACTIVE = "inactive", "Inactive"

    STAGE_ORDER = [Stage.NEW, Stage.REVIEW, Stage.INTERVIEW, Stage.APPROVED, Stage.INACTIVE]

    household = models.ForeignKey(Household, on_delete=models.CASCADE, related_name="applications")
    app_type = models.CharField(max_length=10, choices=Type.choices)
    animal = models.ForeignKey(
        "animals.Animal", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="applications", help_text="Animal of interest, if any",
    )
    stage = models.CharField(max_length=12, choices=Stage.choices, default=Stage.NEW)
    sort_order = models.PositiveIntegerField(default=0)
    answers = models.JSONField(default=dict, blank=True)  # raw public-form submission
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["stage", "sort_order", "-created_at"]

    def __str__(self):
        return f"{self.household} — {self.get_app_type_display()}"
