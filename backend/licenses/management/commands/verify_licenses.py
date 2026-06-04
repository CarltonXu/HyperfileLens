from django.core.management.base import BaseCommand

from licenses.models import License


class Command(BaseCommand):
    help = 'Verify signed license tokens and refresh verification status.'

    def handle(self, *args, **options):
        total = 0
        valid = 0
        invalid = 0

        for license_obj in License.objects.select_related('tenant').iterator():
            total += 1
            result = license_obj.verify_signed_payload(update_status=True)
            if result['is_valid']:
                valid += 1
            else:
                invalid += 1
            self.stdout.write(
                f"{license_obj.license_key}: {result['status']} {result['message']}".strip()
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Verified {total} license(s): {valid} valid, {invalid} invalid"
            )
        )
