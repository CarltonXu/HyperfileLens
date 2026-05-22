"""
Helpers for public installation command generation.

Install commands must use the public control-plane URL exposed by Nginx,
Ingress, or a load balancer. They must not point target machines directly at
the Django backend port or at request-local addresses such as localhost.
"""

from __future__ import annotations

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


DOWNLOADS_PATH = "/downloads"
PACKAGES_PATH = f"{DOWNLOADS_PATH}/packages"
PROXY_INSTALL_SCRIPT = f"{DOWNLOADS_PATH}/install-proxy.sh"
GATEWAY_INSTALL_SCRIPT = f"{DOWNLOADS_PATH}/install-gateway.sh"


def _strip_trailing_slash(url: str) -> str:
    return url.rstrip("/")


def get_public_control_plane_url(request=None) -> str:
    """Return the externally reachable control-plane URL for installers."""
    configured = getattr(settings, "PUBLIC_CONTROL_PLANE_URL", "")
    if configured:
        return _strip_trailing_slash(configured)

    # Development convenience only. Production must configure the public URL.
    if getattr(settings, "DEBUG", False) and request is not None:
        return _strip_trailing_slash(request.build_absolute_uri("/"))

    raise ImproperlyConfigured(
        "PUBLIC_CONTROL_PLANE_URL is required to generate install commands. "
        "Set it to the public Nginx/Ingress/LB URL, for example "
        "https://hfl.example.com."
    )


def build_proxy_install_command(
    *,
    server_url: str,
    role: str,
    proxy_id,
    install_token: str,
    os_type: str,
    name: str,
) -> str:
    """Build the proxy install command using the standard public script path."""
    server_url = _strip_trailing_slash(server_url)
    if os_type == "windows":
        return (
            "# Windows installer is not published yet.\n"
            "# Use a Linux/macOS proxy host with the standard installer:\n"
            f"curl -sSL {server_url}{PROXY_INSTALL_SCRIPT} | bash -s -- \\\n"
            f"  --proxy-id {proxy_id} \\\n"
            f"  --role {role} \\\n"
            f"  --server {server_url} \\\n"
            f"  --token {install_token} \\\n"
            f'  --name "{name}"'
        )

    return f'''# Linux/macOS
curl -sSL {server_url}{PROXY_INSTALL_SCRIPT} | bash -s -- \\
  --proxy-id {proxy_id} \\
  --role {role} \\
  --server {server_url} \\
  --token {install_token} \\
  --name "{name}"'''


def build_gateway_install_command(
    *,
    server_url: str,
    gateway_id,
    install_token: str,
    name: str,
) -> str:
    """Build the gateway install command using the standard public script path."""
    server_url = _strip_trailing_slash(server_url)
    return f"""# Gateway Installation Script for Ubuntu 22.04
# Run this script on your Ubuntu 22.04 server

curl -sSL {server_url}{GATEWAY_INSTALL_SCRIPT} | bash -s -- \\
  --gateway-id {gateway_id} \\
  --server {server_url} \\
  --token {install_token} \\
  --name "{name}"

# After installation, the gateway will automatically register with the control plane.
# You can check the status with:
# systemctl status hyperfilelens-gateway
"""
