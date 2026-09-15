"""Admin credentials for the demo_quiz app.

Stored as plain constants by design (no DPAPI/encryption) so the same
password works across every machine running the exe. Edit the values below
directly to change the passwords.
"""

ADMIN_PASSWORD = "Naveen"
EXPORT_PASSWORD = "MS"


def get_admin_password() -> str:
    return ADMIN_PASSWORD


def get_export_password() -> str:
    return EXPORT_PASSWORD
