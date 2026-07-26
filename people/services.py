"""Auto-tagging: map public-form answers to capability tags."""
from .models import Tag

# rule_key -> (tag name, category)
AUTO_TAG_RULES = {
    "fenced_yard": ("Fenced Yard", Tag.Category.ENVIRONMENT),
    "quarantine_room": ("Quarantine Room", Tag.Category.ENVIRONMENT),
    "only_pet_home": ("Only-Pet Home", Tag.Category.ENVIRONMENT),
    "has_dogs": ("Has Resident Dogs", Tag.Category.ENVIRONMENT),
    "has_cats": ("Has Resident Cats", Tag.Category.ENVIRONMENT),
    "special_needs": ("Special-Needs Capable", Tag.Category.CAPABILITY),
    "medication": ("Medication Capable", Tag.Category.CAPABILITY),
    "bottle_feeder": ("Bottle Feeder Capable", Tag.Category.CAPABILITY),
    "neonatal": ("Neonatal Capable", Tag.Category.CAPABILITY),
    "large_dogs": ("Large-Dog Capable", Tag.Category.CAPABILITY),
    "work_from_home": ("Home During Day", Tag.Category.CAPABILITY),
}


def ensure_tags():
    for key, (name, category) in AUTO_TAG_RULES.items():
        Tag.objects.get_or_create(
            auto_rule_key=key, defaults={"name": name, "category": category}
        )


def apply_auto_tags(household, rule_keys):
    """Attach tags whose auto_rule_key appears in rule_keys."""
    ensure_tags()
    tags = Tag.objects.filter(auto_rule_key__in=list(rule_keys))
    household.tags.add(*tags)
    return tags
