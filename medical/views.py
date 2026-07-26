import datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.views.decorators.http import require_POST

from animals.models import Animal

from .engine import generate_schedule
from .models import MedicalEvent, Medication, MedLogEntry


@login_required
def care_log(request):
    """Daily care log: animals in care x active medications, checkbox grid."""
    try:
        day = datetime.date.fromisoformat(request.GET.get("date", ""))
    except ValueError:
        day = datetime.date.today()

    animals = (
        Animal.objects.exclude(status=Animal.Status.ADOPTED)
        .prefetch_related("medications__log_entries", "placements__household")
    )
    rows = []
    for animal in animals:
        meds = [m for m in animal.medications.all() if m.active_on(day)]
        if not meds:
            continue
        med_rows = []
        for m in meds:
            entry = next((e for e in m.log_entries.all() if e.date == day), None)
            med_rows.append({"med": m, "entry": entry})
        rows.append({"animal": animal, "meds": med_rows})

    return render(request, "medical/care_log.html", {
        "rows": rows,
        "day": day,
        "prev_day": day - datetime.timedelta(days=1),
        "next_day": day + datetime.timedelta(days=1),
        "today": datetime.date.today(),
    })


@login_required
@require_POST
def toggle_med(request, med_id):
    """HTMX: toggle a medication's given-checkbox for a date."""
    med = get_object_or_404(Medication, pk=med_id)
    day = datetime.date.fromisoformat(request.POST["date"])
    entry, _ = MedLogEntry.objects.get_or_create(medication=med, date=day)
    entry.given = not entry.given
    entry.logged_by = request.user.get_username()
    if entry.given:
        entry.note = request.POST.get("note", entry.note)
    entry.save()
    html = render_to_string("medical/_med_checkbox.html", {
        "row": {"med": med, "entry": entry}, "day": day,
    }, request=request)
    return HttpResponse(html)


@login_required
@require_POST
def complete_event(request, event_id):
    """Mark a milestone complete (admin action feeding the gatekeeper)."""
    event = get_object_or_404(MedicalEvent.objects.select_related("animal", "milestone_type"), pk=event_id)
    if event.completed_date:
        event.completed_date = None
        event.completed_by = ""
        messages.info(request, f"Reopened “{event.display_label}”.")
    else:
        event.completed_date = datetime.date.today()
        event.completed_by = request.user.get_username()
        messages.success(request, f"“{event.display_label}” marked complete.")
    event.save()
    return redirect("animal_detail", pk=event.animal_id)


@login_required
@require_POST
def add_event(request, animal_id):
    animal = get_object_or_404(Animal, pk=animal_id)
    from .models import MilestoneType
    mt = get_object_or_404(MilestoneType, pk=request.POST.get("milestone_type"))
    due = datetime.date.fromisoformat(request.POST["due_date"])
    MedicalEvent.objects.create(
        animal=animal, milestone_type=mt, due_date=due,
        label=request.POST.get("label", "").strip(),
    )
    messages.success(request, "Milestone added to the timeline.")
    return redirect("animal_detail", pk=animal_id)


@login_required
@require_POST
def add_medication(request, animal_id):
    animal = get_object_or_404(Animal, pk=animal_id)
    end_raw = request.POST.get("end_date", "").strip()
    Medication.objects.create(
        animal=animal,
        name=request.POST["name"].strip(),
        dosage=request.POST.get("dosage", "").strip(),
        frequency=request.POST.get("frequency", "Once daily").strip() or "Once daily",
        start_date=datetime.date.fromisoformat(request.POST["start_date"]),
        end_date=datetime.date.fromisoformat(end_raw) if end_raw else None,
        instructions=request.POST.get("instructions", "").strip(),
    )
    messages.success(request, "Medication added — it now appears on the daily care log.")
    return redirect("animal_detail", pk=animal_id)


@login_required
@require_POST
def regenerate(request, animal_id):
    animal = get_object_or_404(Animal, pk=animal_id)
    generate_schedule(animal)
    messages.success(request, "Timeline re-projected from intake date and estimated age.")
    return redirect("animal_detail", pk=animal_id)
