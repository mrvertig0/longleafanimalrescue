import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .models import Application, Household, Person, ResidentPet, Tag


@login_required
def household_list(request):
    qs = Household.objects.prefetch_related("tags", "resident_pets").annotate(
        placement_count=Count("placements", distinct=True),
    )
    q = request.GET.get("q", "").strip()
    selected = [t for t in request.GET.getlist("tag") if t]
    if q:
        qs = qs.filter(
            Q(name__icontains=q) | Q(primary_first_name__icontains=q)
            | Q(primary_last_name__icontains=q) | Q(email__icontains=q)
        )
    for tag_id in selected:  # AND semantics: household must have every selected tag
        qs = qs.filter(tags__pk=tag_id)
    if request.GET.get("active", "1") == "1":
        qs = qs.filter(is_active=True)

    ctx = {
        "households": qs.distinct(),
        "tags": Tag.objects.all(),
        "selected_tags": [int(t) for t in selected],
        "q": q,
    }
    if request.headers.get("HX-Request"):
        return render(request, "people/_household_rows.html", ctx)
    return render(request, "people/household_list.html", ctx)


@login_required
def household_detail(request, pk):
    household = get_object_or_404(
        Household.objects.prefetch_related("tags", "people", "resident_pets", "placements__animal"),
        pk=pk,
    )
    return render(request, "people/household_detail.html", {
        "household": household,
        "all_tags": Tag.objects.all(),
        "applications": household.applications.select_related("animal"),
    })


@login_required
@require_POST
def toggle_tag(request, pk, tag_id):
    household = get_object_or_404(Household, pk=pk)
    tag = get_object_or_404(Tag, pk=tag_id)
    if household.tags.filter(pk=tag.pk).exists():
        household.tags.remove(tag)
    else:
        household.tags.add(tag)
    return render(request, "people/_tag_editor.html", {
        "household": household, "all_tags": Tag.objects.all(),
    })


@login_required
def kanban(request):
    apps = (
        Application.objects.select_related("household", "animal")
        .prefetch_related("household__tags")
    )
    app_type = request.GET.get("type", "")
    if app_type:
        apps = apps.filter(app_type=app_type)
    columns = []
    for stage in Application.STAGE_ORDER:
        columns.append({
            "stage": stage,
            "label": Application.Stage(stage).label,
            "apps": [a for a in apps if a.stage == stage],
        })
    return render(request, "people/kanban.html", {
        "columns": columns, "type_filter": app_type,
    })


@login_required
@require_POST
def move_application(request, pk):
    """HTMX/SortableJS drop target: persist stage + ordering."""
    app = get_object_or_404(Application, pk=pk)
    stage = request.POST.get("stage")
    if stage not in Application.Stage.values:
        return HttpResponseBadRequest("bad stage")
    app.stage = stage
    app.save(update_fields=["stage", "updated_at"])
    # Persist intra-column order from the posted id list.
    order = request.POST.get("order", "")
    ids = [int(i) for i in order.split(",") if i.strip().isdigit()]
    for idx, app_id in enumerate(ids):
        Application.objects.filter(pk=app_id, stage=stage).update(sort_order=idx)
    return HttpResponse(status=204)


@login_required
@require_POST
def application_note(request, pk):
    app = get_object_or_404(Application, pk=pk)
    app.notes = request.POST.get("notes", "")
    app.save(update_fields=["notes", "updated_at"])
    messages.success(request, "Note saved.")
    return redirect("household_detail", pk=app.household_id)
