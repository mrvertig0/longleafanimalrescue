import datetime

from django import forms

from .models import Animal, Placement


class AnimalForm(forms.ModelForm):
    """Intake form: staff enter intake date + estimated age; we derive the
    estimated birth date that drives the medical timeline."""

    AGE_UNITS = [("weeks", "weeks"), ("months", "months"), ("years", "years")]
    est_age_value = forms.IntegerField(min_value=0, label="Estimated age")
    est_age_unit = forms.ChoiceField(choices=AGE_UNITS, initial="months", label="Unit")

    class Meta:
        model = Animal
        fields = [
            "name", "species", "breed", "sex", "intake_date",
            "weight_lbs", "photo", "description", "internal_notes",
        ]
        widgets = {
            "intake_date": forms.DateInput(attrs={"type": "date"}),
            "description": forms.Textarea(attrs={"rows": 4}),
            "internal_notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            days = (self.instance.intake_date - self.instance.estimated_birth_date).days
            if days < 120:
                self.fields["est_age_value"].initial = max(days // 7, 0)
                self.fields["est_age_unit"].initial = "weeks"
            elif days < 730:
                self.fields["est_age_value"].initial = days // 30
                self.fields["est_age_unit"].initial = "months"
            else:
                self.fields["est_age_value"].initial = days // 365
                self.fields["est_age_unit"].initial = "years"

    def save(self, commit=True):
        animal = super().save(commit=False)
        value = self.cleaned_data["est_age_value"]
        unit = self.cleaned_data["est_age_unit"]
        per = {"weeks": 7, "months": 30, "years": 365}[unit]
        animal.estimated_birth_date = animal.intake_date - datetime.timedelta(days=value * per)
        if commit:
            animal.save()
        return animal


class PlacementForm(forms.ModelForm):
    class Meta:
        model = Placement
        fields = ["household", "placement_type", "start_date", "notes"]
        widgets = {"start_date": forms.DateInput(attrs={"type": "date"})}
