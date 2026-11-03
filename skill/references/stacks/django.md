---
id: django
name: Django (Python)
---

Notes from general knowledge, no versions pinned. Read the docs for the Django version in `requirements` before relying on a detail.

## Commands
- Run: python manage.py runserver
- Test: python manage.py test
- Lint / types: ruff check .
- Build: python manage.py check --deploy

## Start
- Create a virtual environment, install Django, then `django-admin startproject config .` and `python manage.py startapp <name>` per domain concept. Pin dependencies in `requirements.txt` or `pyproject.toml`.
- Settings come from the environment: `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, database URL. Then `python manage.py migrate` and `createsuperuser`.
- `ruff` is only a suggestion; use the project's linter if it has one, and update the Commands line.

## Conventions
- One app per domain concept. Models and migrations first; commit migrations.
- Validate with forms or serializers, not in views. Keep views thin.
- Use `select_related` and `prefetch_related` to avoid N+1 queries. Use the ORM; avoid raw SQL.
- Templates autoescape; avoid `mark_safe` on user-influenced data. The admin is for back-office use, not for end users.
- Static files: `collectstatic`, and a plan for serving them (for example WhiteNoise or the web server).

## Security
- Production: `DEBUG=False`, a real `SECRET_KEY` from the environment, correct `ALLOWED_HOSTS`, HTTPS settings. `python manage.py check --deploy` must be clean or explained.
- Object-level permissions: check that the user may see or change each record, not only that they are logged in. CSRF protection stays on.
- Enable the password validators. Run `pip-audit` (or the project's equivalent) before release.

## Testing
- `TestCase` with the test `Client`, factories or fixtures, and cases for denied (403 or 404), invalid (form errors) and success. Use a separate test database.

## Release
- `migrate`, `collectstatic`, an application server (gunicorn or uvicorn) behind a web server, environment variables on the host, backups of the database.
