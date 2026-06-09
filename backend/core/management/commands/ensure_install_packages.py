"""Validate install packages published through /downloads/."""

from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


REQUIRED_PACKAGES = [
    "packages/kopia/kopia_0.22.3_linux_amd64.deb",
    "packages/kopia/kopia-0.22.3.x86_64.rpm",
    "packages/proxy/hyperfilelens-proxy-linux-amd64.tar.gz",
    "packages/gateway/hyperfilelens-gateway-linux-amd64.tar.gz",
]


class Command(BaseCommand):
    help = "Ensure required installer packages are available under STATIC_ROOT/downloads."

    def handle(self, *args, **options):
        downloads_root = Path(settings.STATIC_ROOT) / "downloads"
        missing = [
            str(downloads_root / package)
            for package in REQUIRED_PACKAGES
            if not (downloads_root / package).is_file()
        ]

        if missing:
            raise CommandError(
                "Missing install package files:\n"
                + "\n".join(f"  - {path}" for path in missing)
                + "\nRun collectstatic after rebuilding the image, and make sure "
                "backend/static/downloads/packages is included in the deployment package."
            )

        self.stdout.write(
            self.style.SUCCESS(f"Install packages ready: {downloads_root}")
        )
