# Install Distribution

HyperFileLens proxy and gateway installers are distributed from the public
control-plane URL exposed by Nginx, Ingress, or a load balancer.

## Public URL

Set:

```env
PUBLIC_CONTROL_PLANE_URL=https://hfl.example.com
```

Install commands are generated from this value. Do not use backend-only
addresses such as `localhost:8000` or `control:8000` in production.

## URL Layout

Nginx should expose these paths:

```text
/downloads/install-proxy.sh
/downloads/install-gateway.sh
/downloads/uninstall.sh
/downloads/packages/proxy/hyperfilelens-proxy-linux-amd64.tar.gz
/downloads/packages/proxy/hyperfilelens-proxy-linux-arm64.tar.gz
/downloads/packages/gateway/hyperfilelens-gateway-linux-amd64.tar.gz
/downloads/packages/gateway/hyperfilelens-gateway-linux-arm64.tar.gz
/downloads/packages/kopia/kopia_0.22.3_linux_amd64.deb
```

The source directory in this repository is:

```text
backend/static/downloads/
```

Django `collectstatic` copies it to:

```text
STATIC_ROOT/downloads/
```

The production Nginx config serves that directory as:

```text
/downloads/ -> STATIC_ROOT/downloads/
```

## Uninstall

Use the common uninstaller:

```bash
curl -sSL https://hfl.example.com/downloads/uninstall.sh | sudo bash -s -- --component proxy
curl -sSL https://hfl.example.com/downloads/uninstall.sh | sudo bash -s -- --component gateway
curl -sSL https://hfl.example.com/downloads/uninstall.sh | sudo bash -s -- --component all
```

By default, configuration, logs, and data are preserved. To remove them too:

```bash
curl -sSL https://hfl.example.com/downloads/uninstall.sh | sudo bash -s -- --component gateway --purge
```

## Package Contents

Proxy package:

```text
hyperfilelens-proxy-linux-amd64.tar.gz
  hyperfilelens-proxy
```

Gateway package:

```text
hyperfilelens-gateway-linux-amd64.tar.gz
  agent/
    ...
```

Build gateway packages:

```bash
bash scripts/build-gateway-package.sh
```

This publishes:

```text
backend/static/downloads/install-gateway.sh
backend/static/downloads/packages/gateway/hyperfilelens-gateway-linux-amd64.tar.gz
backend/static/downloads/packages/gateway/hyperfilelens-gateway-linux-arm64.tar.gz
```

The installer scripts may keep legacy fallback behavior during migration, but
new builds should publish the `.tar.gz` packages above.
