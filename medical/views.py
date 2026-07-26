import datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST

from animals.models import Animal

from .engine import generate_schedule
from .models import MedicalEvent, MedicalRecord, Medication


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
    messages.success(request, "Medication added to this animal's record.")
    return redirect("animal_detail", pk=animal_id)


@login_required
@require_POST
def regenerate(request, animal_id):
    animal = get_object_or_404(Animal, pk=animal_id)
    generate_schedule(animal)
    messages.success(request, "Timeline re-projected from intake date and estimated age.")
    return redirect("animal_detail", pk=animal_id)


ALLOWED_RECORD_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".heic", ".doc", ".docx"}


@login_required
@require_POST
def upload_record(request, animal_id):
    animal = get_object_or_404(Animal, pk=animal_id)
    f = request.FILES.get("file")
    if not f:
        messages.error(request, "Choose a file to upload.")
        return redirect("animal_detail", pk=animal_id)
    ext = "." + f.name.rsplit(".", 1)[-1].lower() if "." in f.name else ""
    if ext not in ALLOWED_RECORD_EXTENSIONS:
        messages.error(request, f"“{f.name}” isn't a supported file type (PDF, image, or Word doc).")
        return redirect("animal_detail", pk=animal_id)
    MedicalRecord.objects.create(
        animal=animal, file=f,
        label=request.POST.get("label", "").strip(),
        uploaded_by=request.user.get_username(),
    )
    messages.success(request, "Medical record uploaded.")
    return redirect("animal_detail", pk=animal_id)


@login_required
@require_POST
def delete_record(request, record_id):
    record = get_object_or_404(MedicalRecord, pk=record_id)
    animal_id = record.animal_id
    record.file.delete(save=False)
    record.delete()
    messages.info(request, "Medical record removed.")
    return redirect("animal_detail", pk=animal_id)
