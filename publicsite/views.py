import json

from django.shortcuts import get_object_or_404, redirect, render

from animals.models import Animal
from people.models import Application, Household, Person, ResidentPet
from people.services import apply_auto_tags

from .forms import AdoptionForm, FosterForm


def gallery(request):
    animals = Animal.objects.filter(
        status__in=[Animal.Status.AVAILABLE, Animal.Status.PENDING]
    ).order_by("status", "-intake_date")
    species = request.GET.get("species", "")
    if species:
        animals = animals.filter(species=species)
    return render(request, "publicsite/gallery.html", {
        "animals": animals, "species_filter": species,
    })


def public_animal(request, pk):
    animal = get_object_or_404(
        Animal, pk=pk, status__in=[Animal.Status.AVAILABLE, Animal.Status.PENDING]
    )
    return render(request, "publicsite/animal.html", {"animal": animal})


def _pet_rows(request):
    names = request.POST.getlist("pet_name[]")
    species = request.POST.getlist("pet_species[]")
    ages = request.POST.getlist("pet_age[]")
    rows = []
    for i, name in enumerate(names):
        name = name.strip()
        if not name:
            continue
        rows.append({
            "name": name,
            "species": (species[i] if i < len(species) else "").strip() or "unknown",
            "age": (ages[i] if i < len(ages) else "").strip(),
        })
    return rows


def _rule_keys(data, pets, form_kind):
    keys = set()
    if data.get("has_fenced_yard"):
        keys.add("fenced_yard")
    if data.get("has_quarantine_room"):
        keys.add("quarantine_room")
    if data.get("special_needs_experience"):
        keys.add("special_needs")
    if data.get("medication_experience"):
        keys.add("medication")
    if data.get("bottle_feeding"):
        keys.add("bottle_feeder")
    if data.get("hours_home") == "most":
        keys.add("work_from_home")
    pet_species = {p["species"].lower() for p in pets}
    if any("dog" in s for s in pet_species):
        keys.add("has_dogs")
    if any("cat" in s for s in pet_species):
        keys.add("has_cats")
    if not pets:
        keys.add("only_pet_home")
    return keys


def _submit(request, form, app_type):
    data = form.cleaned_data
    pets = _pet_rows(request) if data.get("has_pets") == "yes" else []

    household, created = Household.objects.get_or_create(
        email=data["email"].lower(),
        defaults={
            "name": f"The {data['last_name']} Household",
            "primary_first_name": data["first_name"],
            "primary_last_name": data["last_name"],
        },
    )
    # Refresh contact/environment details on every submission.
    household.phone = data.get("phone") or household.phone
    household.address = data.get("address") or household.address
    household.city = data.get("city") or household.city
    household.state = (data.get("state") or household.state or "NC")[:2]
    household.zip_code = data.get("zip_code") or household.zip_code
    household.home_type = data["home_type"]
    household.owns_home = data["owns_home"] == "yes"
    household.has_fenced_yard = data["has_fenced_yard"]
    household.is_active = True
    household.save()

    if data.get("co_applicant_name") and not household.people.filter(
        first_name__iexact=data["co_applicant_name"].split(" ")[0]
    ).exists():
        parts = data["co_applicant_name"].split(" ", 1)
        Person.objects.create(
            household=household, first_name=parts[0],
            last_name=parts[1] if len(parts) > 1 else "", relationship="co-applicant",
        )

    for p in pets:
        if not household.resident_pets.filter(name__iexact=p["name"]).exists():
            ResidentPet.objects.create(
                household=household, name=p["name"], species=p["species"],
                age_years=int(p["age"]) if p["age"].isdigit() else None,
                spayed_neutered=data.get("pets_spayed", False),
                up_to_date_vaccines=data.get("pets_vaccinated", False),
            )

    applied = apply_auto_tags(household, _rule_keys(data, pets, app_type))

    answers = {k: v for k, v in data.items() if k != "animal"}
    answers["pets"] = pets
    answers["preferred_species"] = data.get("preferred_species", [])
    Application.objects.create(
        household=household,
        app_type=app_type,
        animal=data.get("animal"),
        stage=Application.Stage.NEW,
        answers=answers,
    )
    return render(request, "publicsite/thanks.html", {
        "household": household, "app_type": app_type,
    })


def foster_form(request):
    form = FosterForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        return _submit(request, form, "foster")
    return render(request, "publicsite/apply.html", {
        "form": form, "kind": "foster", "title": "Foster application",
        "pets_json": json.dumps(_pet_rows(request)) if request.method == "POST" else "[]",
    })


def adoption_form(request):
    initial = {}
    if request.GET.get("animal"):
        initial["animal"] = request.GET["animal"]
    form = AdoptionForm(request.POST or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        return _submit(request, form, "adoption")
    return render(request, "publicsite/apply.html", {
        "form": form, "kind": "adoption", "title": "Adoption application",
        "pets_json": json.dumps(_pet_rows(request)) if request.method == "POST" else "[]",
    })


