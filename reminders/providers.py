"""Where a real SMS/email provider gets wired in later.

Right now these are no-ops: the app drafts the message and a staff member
copies it to text or email the foster manually. When you have a Twilio (SMS)
and/or SendGrid/Postmark (email) account, replace the bodies of these two
functions with real API calls — nothing else in the app needs to change,
since every caller already goes through send_sms()/send_email() and treats
the return value as "did this actually go out."

Example Twilio wiring (once you have credentials in your .env):

    from twilio.rest import Client
    _client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)

    def send_sms(to_phone, body):
        _client.messages.create(to=to_phone, from_=settings.TWILIO_FROM_NUMBER, body=body)
        return True

Example email wiring with Django's built-in email backend (set EMAIL_* env
vars and swap DEBUG's console backend for smtp/sendgrid in settings.py):

    from django.core.mail import send_mail

    def send_email(to_email, subject, body):
        send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [to_email])
        return True
"""


def send_sms(to_phone, body):
    """Returns True if actually sent. Currently always returns False —
    no SMS provider configured yet."""
    return False


def send_email(to_email, subject, body):
    """Returns True if actually sent. Currently always returns False —
    no email provider configured yet."""
    return False


SENDING_CONFIGURED = False  # flip to True once send_sms/send_email do real work
