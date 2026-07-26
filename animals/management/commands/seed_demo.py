"""Seed demo data: staff login, milestone types, tags, animals, households,
placements, medications, and pipeline applications.

    python manage.py seed_demo
"""
import datetime
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from animals.models import Animal, Placement
from medical.engine import ensure_milestone_types, generate_schedule
from medical.models import MedicalEvent, Medication, MedLogEntry, MilestoneType
from people.models import Application, Household, Person, ResidentPet, Tag
from people.services import ensure_tags

TODAY = datetime.date.today()


class Command(BaseCommand):
    help = "Load demo data for Longleaf Animal Rescue."

    def handle(self, *args, **options):
        User = get_user_model()
        if not User.objects.filter(username="admin").exists():
            User.objects.create_superuser("admin", "admin@example.com", "longleaf-dev")
            self.stdout.write("Created staff login  admin / longleaf-dev  (change this!)")

        ensure_milestone_types()
        ensure_tags()
        Tag.objects.get_or_create(name="Experienced Foster", defaults={"category": "capability"})

        if Animal.objects.exists():
            self.stdout.write("Animals already exist — skipping demo data.")
            return

        # ---------- households ----------
        rivera = Household.objects.create(
            name="The Rivera Household", primary_first_name="Marisol", primary_last_name="Rivera",
            email="marisol@example.com", phone="919-555-0141", city="Durham", home_type="house",
            has_fenced_yard=True,
        )
        Person.objects.create(household=rivera, first_name="Teo", last_name="Rivera", relationship="spouse")
        ResidentPet.objects.create(household=rivera, name="Biscuit", species="dog", age_years=4,
                                   spayed_neutered=True, up_to_date_vaccines=True)
        rivera.tags.add(*Tag.objects.filter(auto_rule_key__in=["fenced_yard", "has_dogs", "medication"]))

        chen = Household.objects.create(
            name="The Chen Household", primary_first_name="Wei", primary_last_name="Chen",
            email="wei.chen@example.com", city="Raleigh", home_type="apartment", owns_home=False,
        )
        chen.tags.add(*Tag.objects.filter(auto_rule_key__in=["quarantine_room", "bottle_feeder", "work_from_home"]))

        okafor = Household.objects.create(
            name="The Okafor Household", primary_first_name="Ada", primary_last_name="Okafor",
            email="ada.okafor@example.com", city="Cary", home_type="house", has_fenced_yard=True,
        )
        okafor.tags.add(*Tag.objects.filter(auto_rule_key__in=["fenced_yard", "special_needs", "only_pet_home"]))

        blake = Household.objects.create(
            name="The Blake Household", primary_first_name="Jordan", primary_last_name="Blake",
            email="jordan.blake@example.com", city="Chapel Hill", home_type="house",
        )

        # ---------- animals ----------
        def animal(name, species, breed, sex, age_days, intake_days_ago, status, desc="", weight=None):
            a = Animal.objects.create(
                name=name, species=species, breed=breed, sex=sex,
                estimated_birth_date=TODAY - timedelta(days=age_days),
                intake_date=TODAY - timedelta(days=intake_days_ago),
                status=status, description=desc, weight_lbs=weight,
            )
            generate_schedule(a)
            return a

        # Kitten litter — young, mid vaccine series, one overdue
        clover = animal("Clover", "cat", "DSH", "f", 70, 28, Animal.Status.FOSTER,
                        "Curious tabby kitten from the Clover Creek litter. Purrs on contact.", 2.1)
        maple = animal("Maple", "cat", "DSH", "f", 70, 28, Animal.Status.FOSTER,
                       "Maple is the bold one — first to the food bowl, first up the cat tree.", 2.3)
        # Adult dog with overdue rabies (intake 3 weeks ago, nothing completed)
        banjo = animal("Banjo", "dog", "Hound mix", "m", 3 * 365, 21, Animal.Status.MEDICAL_HOLD,
                       "Banjo is a gentle three-year-old hound who loves porch naps.", 48)
        # Available dog — mandatory milestones completed
        pepper = animal("Pepper", "dog", "Lab mix", "f", 2 * 365, 90, Animal.Status.AVAILABLE,
                        "Pepper knows sit, shake, and how to steal your heart. Fully vetted.", 52)
        for code in ["rabies", "spay_neuter", "microchip"]:
            ev = pepper.medical_events.filter(milestone_type__code=code).first()
            if ev:
                ev.completed_date = TODAY - timedelta(days=30)
                ev.completed_by = "admin"
                ev.save()
        pepper.medical_events.filter(milestone_type__code__in=["dhpp", "deworm"]).update(
            completed_date=TODAY - timedelta(days=40), completed_by="admin")
        # Pending cat
        smokey = animal("Smokey", "cat", "Russian Blue mix", "m", 5 * 365, 120, Animal.Status.PENDING,
                        "Distinguished gentleman seeks sunny windowsill. Adoption pending!", 11)
        smokey.medical_events.update(completed_date=TODAY - timedelta(days=60), completed_by="admin")
        # Adopted (history)
        willow = animal("Willow", "dog", "Beagle", "f", 4 * 365, 200, Animal.Status.ADOPTED, "", 24)
        willow.medical_events.update(completed_date=TODAY - timedelta(days=150), completed_by="admin")
        # Fresh intake
        animal("Sprout", "dog", "Terrier mix", "u", 84, 1, Animal.Status.INTAKE,
               "Just arrived — more soon!", 9)

        # ---------- placements ----------
        Placement.objects.create(animal=clover, household=chen, placement_type="foster",
                                 start_date=TODAY - timedelta(days=25))
        Placement.objects.create(animal=maple, household=chen, placement_type="foster",
                                 start_date=TODAY - timedelta(days=25))
        Placement.objects.create(animal=banjo, household=rivera, placement_type="foster",
                                 start_date=TODAY - timedelta(days=14))
        Placement.objects.create(animal=willow, household=okafor, placement_type="adoption",
                                 start_date=TODAY - timedelta(days=160))
        Placement.objects.create(animal=willow, household=rivera, placement_type="foster",
                                 start_date=TODAY - timedelta(days=195), end_date=TODAY - timedelta(days=160))

        # ---------- medications + logs ----------
        panacur = Medication.objects.create(
            animal=clover, name="Panacur", dosage="0.5 ml", frequency="Once daily",
            start_date=TODAY - timedelta(days=3), end_date=TODAY + timedelta(days=2),
            instructions="With food; foster texts photo after dosing.")
        Medication.objects.create(
            animal=maple, name="Panacur", dosage="0.5 ml", frequency="Once daily",
            start_date=TODAY - timedelta(days=3), end_date=TODAY + timedelta(days=2))
        doxy = Medication.objects.create(
            animal=banjo, name="Doxycycline", dosage="100 mg", frequency="Twice daily",
            start_date=TODAY - timedelta(days=10), end_date=TODAY + timedelta(days=18),
            instructions="Heartworm treatment support — do not skip.")
        for d in range(1, 4):
            MedLogEntry.objects.create(medication=panacur, date=TODAY - timedelta(days=d),
                                       given=True, logged_by="admin", note="foster texted")
        MedLogEntry.objects.create(medication=doxy, date=TODAY - timedelta(days=1),
                                   given=True, logged_by="admin")

        # ---------- applications across the pipeline ----------
        Application.objects.create(household=blake, app_type="adoption", animal=pepper,
                                   stage="new", answers={"hours_home": "half"})
        Application.objects.create(household=okafor, app_type="adoption", animal=smokey,
                                   stage="approved", notes="Meet-and-greet went great; finalizing.")
        Application.objects.create(household=chen, app_type="foster", stage="approved",
                                   notes="Current foster — kitten room verified.")
        Application.objects.create(household=rivera, app_type="foster", stage="interview",
                                   notes="Wants medium/large dogs.")

        self.stdout.write(self.style.SUCCESS("Demo data loaded."))
        self.stdout.write("Log in at /login/ with  admin / longleaf-dev")
