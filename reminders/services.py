"""Gathers everything a foster household should be reminded about:
active medications, upcoming/overdue appointments (the vaccine/milestone
timeline), and check-ins — into one prioritized, de-duplicated list.

A reminder disappears from the list once it's marked sent for today
(ReminderSent), so staff aren't nagged about the same thing twice in a day.
"""
import datetime
from urllib.parse import quote

from django.conf import settings

from animals.models import Placement
from medical.models import MedicalEvent

from .models import ReminderSent

URGENCY_ORDER = {"overdue": 0, "due": 1, "upcoming": 2}


def _gmail_compose_url(to_email, subject, body):
    if not to_email:
        return None
    return (
        "https://mail.google.com/mail/?view=cm&fs=1"
        f"&to={quote(to_email)}&su={quote(subject)}&body={quote(body)}"
    )


def _sms_url(phone, body):
    if not phone:
        return None
    digits = "".join(ch for ch in phone if ch.isdigit() or ch == "+")
    return f"sms:{digits}?&body={quote(body)}"


def _add_links(reminder, household, subject):
    reminder["gmail_url"] = _gmail_compose_url(household.email, subject, reminder["body"])
    reminder["sms_url"] = _sms_url(household.phone, reminder["body"])
    return reminder


def _already_sent_today(kind, ref_id, placement_id):
    return ReminderSent.objects.filter(
        kind=kind, ref_id=ref_id, placement_id=placement_id, sent_date=datetime.date.today(),
    ).exists()


def _medication_reminders(placement):
    reminders = []
    for med in placement.animal.medications.all():
        if not med.is_active:
            continue
        if _already_sent_today(ReminderSent.Kind.MEDICATION, med.pk, placement.pk):
            continue
        body = (
            f"Hi {placement.household.primary_first_name}! Reminder for {placement.animal.name}: "
            f"{med.name}{f' ({med.dosage})' if med.dosage else ''} — {med.frequency}."
        )
        if med.instructions:
            body += f" {med.instructions}"
        reminders.append(_add_links({
            "kind": ReminderSent.Kind.MEDICATION, "ref_id": med.pk, "placement": placement,
            "urgency": "due", "label": f"{med.name} — {med.frequency}", "body": body,
        }, placement.household, f"{placement.animal.name}'s medication reminder"))
    return reminders


def _appointment_reminders(placement):
    reminders = []
    window = datetime.date.today() + datetime.timedelta(days=settings.MEDICAL_ALERT_WINDOW_DAYS)
    events = placement.animal.medical_events.filter(completed_date__isnull=True, due_date__lte=window)
    for event in events:
        if _already_sent_today(ReminderSent.Kind.APPOINTMENT, event.pk, placement.pk):
            continue
        state = event.state  # 'overdue' | 'due' | 'upcoming'
        when = "was due" if state == "overdue" else "is due"
        body = (
            f"Hi {placement.household.primary_first_name}! Heads up — {placement.animal.name}'s "
            f"{event.display_label} appointment {when} {event.due_date:%b %-d}. "
            f"Let us know if you need help scheduling."
        )
        reminders.append(_add_links({
            "kind": ReminderSent.Kind.APPOINTMENT, "ref_id": event.pk, "placement": placement,
            "urgency": state, "label": f"{event.display_label} — due {event.due_date}", "body": body,
        }, placement.household, f"{placement.animal.name}'s upcoming appointment"))
    return reminders


def _checkin_reminders(placement):
    state = placement.check_in_state
    if state not in ("overdue", "due"):
        return []
    if _already_sent_today(ReminderSent.Kind.CHECKIN, placement.pk, placement.pk):
        return []
    body = (
        f"Hi {placement.household.primary_first_name}! Just checking in on {placement.animal.name} — "
        f"how are things going? Let us know if you need anything."
    )
    return [_add_links({
        "kind": ReminderSent.Kind.CHECKIN, "ref_id": placement.pk, "placement": placement,
        "urgency": state, "label": f"Check-in — next due {placement.next_check_in_due}", "body": body,
    }, placement.household, f"Checking in about {placement.animal.name}")]


def gather_reminders():
    """All pending reminders across active foster placements, most urgent first."""
    placements = (
        Placement.objects.filter(end_date__isnull=True, placement_type=Placement.Type.FOSTER)
        .select_related("animal", "household")
        .prefetch_related("animal__medications", "animal__medical_events", "check_ins")
    )
    reminders = []
    for placement in placements:
        reminders += _medication_reminders(placement)
        reminders += _appointment_reminders(placement)
        reminders += _checkin_reminders(placement)
    reminders.sort(key=lambda r: URGENCY_ORDER.get(r["urgency"], 3))
    return reminders
