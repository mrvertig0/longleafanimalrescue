# Longleaf Animal Rescue — management platform

One Django project, four modules:

1. **Command dashboard** (`/app/`) — every active animal with ID, demographics,
   current placement (facility vs. foster household), inline status control, and
   an auto-computed **Medical alerts** column (red = overdue, amber = due within
   7 days or today's meds unlogged).
2. **CRM & people tracker** (`/app/people/`) — household profiles (co-applicants,
   resident pets, environment), a click-to-toggle capability tag system with
   AND-filtering, and a drag-and-drop **application pipeline** board
   (`/app/people/pipeline/`).
3. **Medical compliance engine** — intake date + estimated age auto-project the
   vaccine series, rabies, spay/neuter, deworming, and microchip due dates
   (`medical/engine.py`). A daily care log (`/app/medical/care-log/`) gives staff
   a checkbox grid per animal x medication. The **Medical Hold Gatekeeper**
   blocks the Available status until every milestone flagged
   `mandatory_for_available` (rabies, spay/neuter by default) is completed.
4. **Public site & dynamic forms** (`/`) — gallery auto-syncs from animal status
   (Available shows, Pending shows with a ribbon, everything else hidden).
   Foster/adoption forms expand conditionally (renting → landlord permission,
   has pets → per-pet rows) and on submit create/update the Household, add
   resident pets, apply capability tags automatically, and drop a card into the
   pipeline's **New Application** column. No double entry anywhere — households
   and animals are linked relationally through `Placement` rows.

## Run it

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo        # demo data + staff login admin / longleaf-dev
python manage.py runserver
```

- Public site: http://127.0.0.1:8000/
- Staff HQ:    http://127.0.0.1:8000/app/  (login: admin / longleaf-dev — change it)
- Django admin (escape hatch): http://127.0.0.1:8000/django-admin/

SQLite out of the box. For Postgres, copy `.env.example` to `.env` and set
`DATABASE_URL` — no other changes needed. Runs fine under WSL2 or in a
`python:3.12` container; all JS (htmx, SortableJS, Alpine) is vendored in
`static/vendor/`, so the internal tool works offline. The public site pulls the
Fraunces display font from Google Fonts and falls back to Georgia without it.

## Deploying to Render (live URL)

The project is set up to deploy as-is — `requirements.txt` includes gunicorn
(app server) and whitenoise (static files), and `render.yaml` describes the
service + free Postgres database as a Render "Blueprint."

1. Push this folder to a **GitHub repo** (private is fine):
   ```bash
   git init && git add -A && git commit -m "Longleaf Animal Rescue platform"
   # create a repo on github.com, then:
   git remote add origin https://github.com/<you>/longleaf-rescue.git
   git push -u origin main
   ```
2. On [render.com](https://render.com), **New > Blueprint**, point it at that repo.
   Render reads `render.yaml` and provisions the web service + database together.
3. Once it's built, open a **Shell** tab on the service (Render dashboard) and run
   once:
   ```bash
   python manage.py seed_demo
   ```
   or skip that and create your own admin user with `python manage.py createsuperuser`.
4. Your site is live at `https://<service-name>.onrender.com`.

**Two things worth knowing about the free tier:** the disk is ephemeral, so
animal photos uploaded through the app disappear on redeploy — fine for
testing, but before relying on this day-to-day, switch `MEDIA` storage to
something like Cloudflare R2 or AWS S3 (a `django-storages` swap, not a
rewrite). And the free web service spins down after inactivity, so the first
visit after a quiet stretch takes ~30 seconds to wake up — Render's paid tier
removes that.

If you'd rather not use Render: the same `Procfile` and `DATABASE_URL` env var
work unchanged on Railway or Fly.io, and PythonAnywhere is a good very-low-cost
option if you're comfortable with a bit more manual setup.

## Reminders (`/app/reminders/`)

Pulls together everything a foster household should hear about — active
medications, upcoming/overdue appointments (the vaccine/milestone timeline),
and overdue check-ins — into one prioritized list with a pre-written message
per item. No SMS/email provider is wired up yet, so right now staff copy the
message and text/email it manually, then click "Mark handled" so it won't
resurface today (`reminders/models.py` → `ReminderSent`).

To wire up real sending later: fill in `reminders/providers.py`'s
`send_sms`/`send_email` functions (a Twilio and a Django-email example are
sketched in that file's docstring) and flip `SENDING_CONFIGURED = True`. Every
call site already routes through those two functions, so nothing else in the
app needs to change.

## Where the business rules live

| Rule | File |
|---|---|
| Timeline projection protocol | `medical/engine.py` |
| Gatekeeper (blocks Available) | `animals/models.py` → `Animal.can_set_status` |
| Alert thresholds | `Animal.medical_alert` + `MEDICAL_ALERT_WINDOW_DAYS` |
| Auto-tag rules | `people/services.py` |
| Public visibility | `Animal.PUBLIC_STATUSES` |

Milestone types (incl. which are mandatory) and tags are editable data, not
code — manage them in the Django admin.
