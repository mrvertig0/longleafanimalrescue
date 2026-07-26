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
