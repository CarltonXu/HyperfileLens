"""Validate install packages published through /downloads/."""

from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


def required_packages():
    kopia_version = getattr(settings, "KOPIA_PACKAGE_VERSION", "0.22.3")
    return [
        f"packages/kopia/kopia_{kopia_version}_linux_amd64.deb",
        f"packages/kopia/kopia-{kopia_version}-linux-x64.tar.gz",
        f"packages/kopia/kopia-{kopia_version}-macOS-arm64.tar.gz",
        f"packages/kopia/kopia-{kopia_version}-macOS-x64.tar.gz",
        f"packages/kopia/kopia-{kopia_version}-windows-x64.zip",
        f"packages/kopia/kopia-{kopia_version}.x86_64.rpm",
        "packages/proxy/hyperfilelens-proxy-linux-amd64.tar.gz",
        "packages/gateway/hyperfilelens-gateway-linux-amd64.tar.gz",
    ]


class Command(BaseCommand):
    help = "Ensure required installer packages are available under STATIC_ROOT/downloads."

    def handle(self, *args, **options):
        downloads_root = Path(settings.STATIC_ROOT) / "downloads"
        missing = [
            str(downloads_root / package)
            for package in required_packages()
            if not (downloads_root / package).is_file()
        ]

        if missing:
            raise CommandError(
                "Missing install package files:\n"
                + "\n".join(f"  - {path}" for path in missing)
                + "\nRebuild the backend image so scripts/download-kopia-packages.sh "
                "can download third-party packages, then rerun control-init."
            )

        self.stdout.write(
            self.style.SUCCESS(f"Install packages ready: {downloads_root}")
        )
