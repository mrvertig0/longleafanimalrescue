from django import forms

from animals.models import Animal

HOURS_CHOICES = [
    ("most", "Home most of the day"),
    ("half", "Away part of the day"),
    ("full", "Away full workdays"),
]


class BaseInquiryForm(forms.Form):
    """Shared fields for foster + adoption intake. Conditional sections are
    toggled client-side with Alpine and validated server-side in clean()."""

    first_name = forms.CharField(max_length=60)
    last_name = forms.CharField(max_length=60)
    email = forms.EmailField()
    phone = forms.CharField(max_length=30, required=False)
    address = forms.CharField(max_length=200, required=False)
    city = forms.CharField(max_length=80, required=False)
    state = forms.CharField(max_length=2, required=False, initial="NC")
    zip_code = forms.CharField(max_length=10, required=False)

    co_applicant_name = forms.CharField(
        max_length=120, required=False,
        help_text="Another adult in your household applying with you, if any.",
    )

    home_type = forms.ChoiceField(choices=[
        ("house", "House"), ("apartment", "Apartment / Condo"),
        ("mobile", "Mobile home"), ("other", "Other"),
    ])
    owns_home = forms.ChoiceField(choices=[("yes", "Own"), ("no", "Rent")], initial="yes")
    landlord_permission = forms.BooleanField(
        required=False, label="I have my landlord's permission to keep animals",
    )
    has_fenced_yard = forms.BooleanField(required=False, label="We have a fully fenced yard")
    has_quarantine_room = forms.BooleanField(
        required=False, label="We can keep a new animal separated in its own room for 2 weeks",
    )
    hours_home = forms.ChoiceField(choices=HOURS_CHOICES, label="On a typical weekday, someone is…")

    has_pets = forms.ChoiceField(
        choices=[("no", "No"), ("yes", "Yes")], initial="no",
        label="Do you currently have pets at home?",
    )
    pets_spayed = forms.BooleanField(required=False, label="All our pets are spayed/neutered")
    pets_vaccinated = forms.BooleanField(required=False, label="All our pets are up to date on vaccines")

    special_needs_experience = forms.BooleanField(
        required=False, label="We have experience with special-needs or medically fragile animals",
    )
    medication_experience = forms.BooleanField(
        required=False, label="We're comfortable giving oral medication",
    )
    notes = forms.CharField(widget=forms.Textarea(attrs={"rows": 3}), required=False,
                            label="Anything else you'd like us to know?")

    def clean(self):
        data = super().clean()
        if data.get("owns_home") == "no" and not data.get("landlord_permission"):
            self.add_error("landlord_permission",
                           "Renters need landlord permission before we can place an animal.")
        return data


class FosterForm(BaseInquiryForm):
    bottle_feeding = forms.BooleanField(
        required=False, label="We can bottle-feed neonates (feedings every 2–4 hours)",
    )
    preferred_species = forms.MultipleChoiceField(
        choices=[("dog", "Dogs"), ("cat", "Cats"), ("other", "Other")],
        widget=forms.CheckboxSelectMultiple, required=False,
        label="I'm open to fostering…",
    )


class AdoptionForm(BaseInquiryForm):
    animal = forms.ModelChoiceField(
        queryset=Animal.objects.none(), required=False,
        label="Which animal are you interested in?",
        empty_label="No specific animal yet — just browsing",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["animal"].queryset = Animal.objects.filter(
            status=Animal.Status.AVAILABLE
        ).order_by("name")
