from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from animals.models import Placement

from . import providers
from .models import ReminderSent
from .services import gather_reminders


@login_required
def reminder_list(request):
    reminders = gather_reminders()
    overdue_count = sum(1 for r in reminders if r["urgency"] == "overdue")
    return render(request, "reminders/list.html", {
        "reminders": reminders,
        "overdue_count": overdue_count,
        "sending_configured": providers.SENDING_CONFIGURED,
    })


@login_required
@require_POST
def mark_sent(request):
    """Log a reminder as handled for today. If a real provider is wired up
    (providers.SENDING_CONFIGURED), this also attempts to actually send it;
    otherwise it just records that staff handled it manually."""
    kind = request.POST.get("kind")
    ref_id = request.POST.get("ref_id")
    placement_id = request.POST.get("placement_id")
    body = request.POST.get("body", "")
    channel = request.POST.get("channel", "sms")
    placement = get_object_or_404(Placement, pk=placement_id)

    sent_ok = None
    if providers.SENDING_CONFIGURED:
        household = placement.household
        if channel == "sms" and household.phone:
            sent_ok = providers.send_sms(household.phone, body)
        elif household.email:
            sent_ok = providers.send_email(household.email, "Longleaf Animal Rescue", body)

    ReminderSent.objects.get_or_create(
        kind=kind, ref_id=ref_id, placement=placement,
        sent_date=timezone.localdate(),
        defaults={"channel": channel, "body": body, "sent_by": request.user.get_username()},
    )
    if sent_ok:
        messages.success(request, f"Sent to {placement.household} and logged.")
    else:
        messages.success(request, f"Logged as handled for {placement.household}.")
    return redirect("reminder_list")
