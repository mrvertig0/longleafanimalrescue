import datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Prefetch, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.views.decorators.http import require_POST

from medical.engine import generate_schedule
from medical.models import MedicalEvent, MilestoneType

from .forms import AnimalForm, PlacementForm
from .models import Animal, Placement


def _dashboard_queryset():
    return (
        Animal.objects
        .prefetch_related(
            "medical_events__milestone_type",
            "medications__log_entries",
            Prefetch("placements", queryset=Placement.objects.select_related("household")),
        )
    )


@login_required
def dashboard(request):
    qs = _dashboard_queryset()
    status = request.GET.get("status", "active")
    species = request.GET.get("species", "")
    q = request.GET.get("q", "").strip()

    if status == "active":
        qs = qs.exclude(status=Animal.Status.ADOPTED)
    elif status:
        qs = qs.filter(status=status)
    if species:
        qs = qs.filter(species=species)
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(code__icontains=q) | Q(breed__icontains=q))

    animals = list(qs)
    alerts = sum(1 for a in animals if a.medical_alert)
    ctx = {
        "animals": animals,
        "alert_count": alerts,
        "status_filter": status,
        "species_filter": species,
        "q": q,
        "status_choices": Animal.Status.choices,
        "species_choices": Animal.Species.choices,
    }
    if request.headers.get("HX-Request"):
        return render(request, "animals/_dashboard_table.html", ctx)
    return render(request, "animals/dashboard.html", ctx)


@login_required
def animal_detail(request, pk):
    animal = get_object_or_404(_dashboard_queryset(), pk=pk)
    events = animal.medical_events.select_related("milestone_type").order_by("due_date")
    return render(request, "animals/detail.html", {
        "animal": animal,
        "events": events,
        "placements": animal.placements.select_related("household"),
        "placement_form": PlacementForm(),
        "status_choices": Animal.Status.choices,
        "milestone_types": MilestoneType.objects.all(),
        "today": datetime.date.today(),
    })


@login_required
def animal_create(request):
    form = AnimalForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        animal = form.save()
        generate_schedule(animal)
        messages.success(request, f"{animal.name} added — medical timeline projected automatically.")
        return redirect(animal)
    return render(request, "animals/form.html", {"form": form, "is_new": True})


@login_required
def animal_edit(request, pk):
    animal = get_object_or_404(Animal, pk=pk)
    form = AnimalForm(request.POST or None, request.FILES or None, instance=animal)
    if request.method == "POST" and form.is_valid():
        old = (animal.intake_date, animal.estimated_birth_date)
        animal = form.save()
        if (animal.intake_date, animal.estimated_birth_date) != old:
            generate_schedule(animal)
            messages.info(request, "Intake/age changed — pending auto-generated milestones re-projected.")
        messages.success(request, "Saved.")
        return redirect(animal)
    return render(request, "animals/form.html", {"form": form, "is_new": False, "animal": animal})


@login_required
@require_POST
def update_status(request, pk):
    """HTMX endpoint: inline status change with Medical Hold Gatekeeper."""
    animal = get_object_or_404(_dashboard_queryset(), pk=pk)
    new_status = request.POST.get("status", "")
    valid = dict(Animal.Status.choices)
    ok, reason = (False, "Unknown status.") if new_status not in valid else animal.can_set_status(new_status)
    if ok:
        animal.status = new_status
        animal.save(update_fields=["status"])
        toast = ""
    else:
        toast = reason
    html = render_to_string("animals/_status_cell.html", {
        "animal": animal, "status_choices": Animal.Status.choices, "toast": toast,
    }, request=request)
    return HttpResponse(html)


@login_required
@require_POST
def add_placement(request, pk):
    animal = get_object_or_404(Animal, pk=pk)
    form = PlacementForm(request.POST)
    if form.is_valid():
        # Close any open placement first — one active placement per animal.
        animal.placements.filter(end_date__isnull=True).update(end_date=form.cleaned_data["start_date"])
        placement = form.save(commit=False)
        placement.animal = animal
        placement.save()
        if placement.placement_type == Placement.Type.FOSTER and animal.status in (
            Animal.Status.INTAKE, Animal.Status.MEDICAL_HOLD,
        ):
            animal.status = Animal.Status.FOSTER
            animal.save(update_fields=["status"])
        messages.success(request, f"Placed {animal.name} with {placement.household}.")
    else:
        messages.error(request, "Could not save placement — check the fields.")
    return redirect(animal)


@login_required
@require_POST
def end_placement(request, pk, placement_id):
    animal = get_object_or_404(Animal, pk=pk)
    placement = get_object_or_404(Placement, pk=placement_id, animal=animal)
    placement.end_date = datetime.date.today()
    placement.save(update_fields=["end_date"])
    messages.success(request, "Placement ended — animal is back at the facility.")
    return redirect(animal)
