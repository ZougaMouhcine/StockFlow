# Run the Django Stock App (Windows)

This guide explains how to run the project locally on Windows using PowerShell.

## 1. Open PowerShell in the project folder

```powershell
cd "c:\Users\AMLLAL Amine\Documents\Project code\gestion de stock"
```

## 2. Create virtual environment (first time only)

```powershell
python -m venv .venv
```

## 3. Install dependencies

If script activation is allowed on your machine:

```powershell
.venv\Scripts\activate
pip install -r requirements.txt
```

If PowerShell blocks activation, use Python from the venv directly:

```powershell
.\.venv\Scripts\python -m pip install -r requirements.txt
```

## 4. Apply database migrations

```powershell
.\.venv\Scripts\python manage.py makemigrations
.\.venv\Scripts\python manage.py migrate
```

## 5. Create admin user (first time only)

```powershell
.\.venv\Scripts\python manage.py createsuperuser
```

## 6. Run the development server

```powershell
.\.venv\Scripts\python manage.py runserver
```

Open:
- App: http://127.0.0.1:8000/
- Django admin: http://127.0.0.1:8000/admin/

## 7. Initial role setup in Django admin

After logging in to admin:

1. Create groups:
   - superadmin
   - admin
   - viewer
2. Create users and assign groups:
   - super1 -> superadmin
   - admin1 -> admin
   - user1 -> viewer

## Helpful commands

Check project health:

```powershell
.\.venv\Scripts\python manage.py check
```

Collect static files (optional in development):

```powershell
.\.venv\Scripts\python manage.py collectstatic
```

## Notes

- Product image uploads are stored in the `media\` folder.
- In development, media files are served automatically when `DEBUG=True`.
