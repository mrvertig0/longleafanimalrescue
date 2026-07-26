"""Automated medical timeline calculator.

Given an animal's intake date and estimated birth date, project due dates for
the standard protocol. All generated events are editable afterwards; regenerating
only replaces auto-generated events that are not yet completed.

Protocol (defaults, adjustable per-event afterwards):
- Core vaccine series (DHPP for dogs / FVRCP for cats):
    * Under 16 weeks: doses every 3 weeks starting at max(intake, 6 weeks old)
      until 16 weeks old.
    * 16 weeks+: one dose at intake, booster 3 weeks later.
- Rabies: due at max(intake, 12 weeks old). Mandatory for Available.
- Spay/Neuter: due at max(intake + 14 days, 6 months old). Mandatory for Available.
- Deworming: at intake + 2 days, repeat 14 days later.
- Microchip: aligned with spay/neuter date.
"""
import datetime
from datetime import timedelta

from .models import MedicalEvent, MilestoneType

CORE_VACCINE = {"dog": "dhpp", "cat": "fvrcp", "other": "core_vaccine"}

STANDARD_MILESTONES = [
    # code, name, species, mandatory, sort
    ("dhpp", "DHPP Vaccine", "dog", False, 10),
    ("fvrcp", "FVRCP Vaccine", "cat", False, 10),
    ("core_vaccine", "Core Vaccine", "", False, 10),
    ("rabies", "Rabies Vaccine", "", True, 20),
    ("spay_neuter", "Spay / Neuter", "", True, 30),
    ("deworm", "Deworming", "", False, 40),
    ("microchip", "Microchip", "", False, 50),
]


def ensure_milestone_types():
    for code, name, species, mandatory, sort in STANDARD_MILESTONES:
        MilestoneType.objects.get_or_create(
            code=code,
            defaults={
                "name": name,
                "species": species,
                "mandatory_for_available": mandatory,
                "sort": sort,
            },
        )


def generate_schedule(animal, replace=True):
    """(Re)build the auto-generated timeline for an animal."""
    ensure_milestone_types()
    types = {t.code: t for t in MilestoneType.objects.all()}
    intake = animal.intake_date
    birth = animal.estimated_birth_date

    if replace:
        animal.medical_events.filter(auto_generated=True, completed_date__isnull=True).delete()

    events = []

    def add(code, due, label=""):
        events.append(MedicalEvent(
            animal=animal, milestone_type=types[code], due_date=due,
            label=label, auto_generated=True,
        ))

    # --- core vaccine series ---
    vac_code = CORE_VACCINE.get(animal.species, "core_vaccine")
    vac_name = types[vac_code].name.replace(" Vaccine", "")
    sixteen_weeks = birth + timedelta(weeks=16)
    if intake < sixteen_weeks:
        dose_date = max(intake, birth + timedelta(weeks=6))
        dose = 1
        while dose_date < sixteen_weeks:
            add(vac_code, dose_date, f"{vac_name} #{dose}")
            dose += 1
            dose_date += timedelta(weeks=3)
        add(vac_code, sixteen_weeks, f"{vac_name} #{dose} (final)")
    else:
        add(vac_code, intake, f"{vac_name} #1")
        add(vac_code, intake + timedelta(weeks=3), f"{vac_name} booster")

    # --- rabies ---
    add("rabies", max(intake, birth + timedelta(weeks=12)))

    # --- spay/neuter + microchip ---
    fix_date = max(intake + timedelta(days=14), birth + timedelta(days=182))
    add("spay_neuter", fix_date)
    add("microchip", fix_date)

    # --- deworming ---
    add("deworm", intake + timedelta(days=2), "Deworm #1")
    add("deworm", intake + timedelta(days=16), "Deworm #2")

    # Skip auto events already satisfied by a completed event of the same type+label.
    existing = {
        (e.milestone_type_id, e.label)
        for e in animal.medical_events.all()
    }
    events = [e for e in events if (e.milestone_type_id, e.label) not in existing]
    MedicalEvent.objects.bulk_create(events)
    return events
