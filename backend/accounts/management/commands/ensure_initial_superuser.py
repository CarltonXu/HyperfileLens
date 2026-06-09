"""Create or ensure the initial deployment superuser."""

import os
import secrets
import string

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.db import transaction


DEFAULT_ADMIN_EMAIL = "admin@hyperfilelens.local"


def generate_password(length=24):
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*()-_=+"
    while True:
        password = "".join(secrets.choice(alphabet) for _ in range(length))
        if (
            any(char.islower() for char in password)
            and any(char.isupper() for char in password)
            and any(char.isdigit() for char in password)
            and any(char in "!@#$%^&*()-_=+" for char in password)
        ):
            return password


class Command(BaseCommand):
    help = "Create an initial superuser from environment variables if needed."

    def add_arguments(self, parser):
        parser.add_argument(
            "--email",
            default=os.environ.get("HFL_ADMIN_EMAIL", DEFAULT_ADMIN_EMAIL),
            help="Admin email. Defaults to HFL_ADMIN_EMAIL or admin@hyperfilelens.local.",
        )
        parser.add_argument(
            "--password",
            default=os.environ.get("HFL_ADMIN_PASSWORD", ""),
            help="Admin password. Defaults to HFL_ADMIN_PASSWORD or a generated password.",
        )

    def handle(self, *args, **options):
        email = (options["email"] or "").strip().lower()
        password = options["password"] or ""
        first_name = os.environ.get("HFL_ADMIN_FIRST_NAME", "System")
        last_name = os.environ.get("HFL_ADMIN_LAST_NAME", "Administrator")

        if not email:
            raise CommandError("Initial admin email is empty.")

        try:
            validate_email(email)
        except ValidationError as exc:
            raise CommandError(f"Invalid initial admin email: {email}") from exc

        generated_password = False
        if not password:
            password = generate_password()
            generated_password = True

        User = get_user_model()

        with transaction.atomic():
            user = User.objects.filter(email__iexact=email).first()
            if user:
                changed_fields = []
                if not user.is_staff:
                    user.is_staff = True
                    changed_fields.append("is_staff")
                if not user.is_superuser:
                    user.is_superuser = True
                    changed_fields.append("is_superuser")
                if not user.is_active:
                    user.is_active = True
                    changed_fields.append("is_active")
                if changed_fields:
                    user.save(update_fields=changed_fields)
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"Initial admin ensured: {email} (existing user promoted)"
                        )
                    )
                else:
                    self.stdout.write(
                        self.style.SUCCESS(f"Initial admin already exists: {email}")
                    )
                self.stdout.write(
                    "Initial admin password was not changed for the existing user."
                )
                return

            User.objects.create_superuser(
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
            )

        self.stdout.write(self.style.SUCCESS("Initial admin created successfully."))
        self.stdout.write(f"Initial admin email: {email}")
        if generated_password:
            self.stdout.write(f"Initial admin generated password: {password}")
            self.stdout.write(
                "Store this password now. It will not be printed again after the user exists."
            )
        else:
            self.stdout.write("Initial admin password: configured by HFL_ADMIN_PASSWORD")
