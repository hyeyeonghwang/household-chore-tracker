# Shared Household Chore Assignment Tool

A Django-based web app for managing household chores with weekly rotation, manual reassignment, and household member tracking.

## Overview

This project helps a household:

- assign chores automatically on a weekly rotation
- keep one assignee per chore per week
- allow manual reassignment for the current week
- manage household members and chore lists
- use a simple household-based access model

## Project structure

- `config/` — Django project settings and URL configuration
- `chores/` — app logic, models, views, templates, and tests
- `manage.py` — Django management entry point
- `db.sqlite3` — SQLite database file
- `requirements.txt` — Python dependencies
- `plan.md` — product and MVP design notes

## Tech stack

- Python
- Django 5.2
- SQLite

## Requirements

Install Python and then install dependencies:

```bash
pip install -r requirements.txt
```

## Getting started

From the project root:

```bash
python manage.py migrate
python manage.py runserver
```

Then open:

```text
http://127.0.0.1:8000/
```

## Main app routes

The app includes routes for:

- login and logout
- signup
- household creation
- this week's assignments
- chore management
- member management
- household settings

These routes are defined in `chores/urls.py`.

## Django project settings

The project is configured in `config/settings.py` and includes the `chores` app in `INSTALLED_APPS`.

## Development notes

This app is designed around a single household per user flow and a weekly rotation model. The product requirements and scope are documented in `plan.md`.

## Testing

Run the test suite with:

```bash
python manage.py test
```

## Notes

- The project uses Django's built-in authentication system.
- SQLite is used as the default database.
- The project is intended for local development and prototype use.
