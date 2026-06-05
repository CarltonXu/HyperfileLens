HyperFileLens Docker Deployment Guide
=====================================

Goal
----
After cloning this repository on a new host, you should be able to build and
start the control plane with Docker Compose, then open the web console from the
public Nginx port. Optional local Gateway and Proxy agents are available through
Compose profiles.


Repository Files
----------------
Main deployment files:

- docker-compose.yml
  Production/lab stack. Builds backend, frontend, gateway agent, and proxy agent
  images from local source. Starts Postgres, Redis, backend, Celery worker,
  Celery beat, frontend server, and Nginx by default.

- docker-compose.dev.yml
  Development stack. Runs Django and Vite development servers with source
  directories mounted.

- env.dev.sample
  Development environment template.

- env.prod.sample
  Production environment template.

- docker/nginx/nginx.conf
  Public HTTP entrypoint. Routes frontend, /api, /ws, /static, /media, and
  /downloads through one port.

- backend/static/downloads/
  Public installer scripts and package artifacts served by Nginx at /downloads/.


Production Quick Start
----------------------
1. Install Docker and Docker Compose plugin.

2. Clone the repository:

   git clone <repo-url> HyperFileLens
   cd HyperFileLens

3. Create production env file:

   cp env.prod.sample .env.prod

4. Edit .env.prod. At minimum change:

   SECRET_KEY
   POSTGRES_PASSWORD
   ALLOWED_HOSTS
   CSRF_TRUSTED_ORIGINS
   CORS_ALLOWED_ORIGINS
   PUBLIC_CONTROL_PLANE_URL
   PUBLIC_HTTP_PORT
   LICENSE_PUBLIC_KEY

   Example for plain HTTP lab deployment:

   ALLOWED_HOSTS=10.147.18.11,localhost,127.0.0.1,control
   CSRF_TRUSTED_ORIGINS=http://10.147.18.11:5001
   CORS_ALLOWED_ORIGINS=http://10.147.18.11:5001
   PUBLIC_CONTROL_PLANE_URL=http://10.147.18.11:5001
   PUBLIC_HTTP_PORT=5001
   SESSION_COOKIE_SECURE=false
   CSRF_COOKIE_SECURE=false
   GATEWAY_WS_PROTOCOL=ws

   Example for HTTPS production:

   ALLOWED_HOSTS=hyperfilelens.example.com,control
   CSRF_TRUSTED_ORIGINS=https://hyperfilelens.example.com
   CORS_ALLOWED_ORIGINS=https://hyperfilelens.example.com
   PUBLIC_CONTROL_PLANE_URL=https://hyperfilelens.example.com
   SESSION_COOKIE_SECURE=true
   CSRF_COOKIE_SECURE=true
   GATEWAY_WS_PROTOCOL=wss

5. Build and start the default platform:

   docker compose --env-file .env.prod up -d --build

6. Create the first administrator:

   docker compose --env-file .env.prod exec control python manage.py createsuperuser

7. Open:

   http://<host>:<PUBLIC_HTTP_PORT>

   Default lab URL:

   http://<host>:5001


Default Services
----------------
docker compose --env-file .env.prod up -d --build starts:

- postgres
- redis
- control-init
  Runs migrations, collectstatic, periodic task registration, and license
  verification once.
- control
  Django ASGI server through Daphne.
- celery-worker
- celery-beat
- frontend
  Built Vue static server.
- nginx
  Only public entrypoint by default.

Health endpoints:

- http://<host>:<PUBLIC_HTTP_PORT>/health/
- http://<host>:<PUBLIC_HTTP_PORT>/api/docs/


Optional Local Gateway Agent
----------------------------
Usually Gateway runs on a separate machine. For a lab or single-host deployment,
you can run it in the same Compose project.

1. Start the platform first.

2. Create a Gateway in the web UI and copy its ID/install token.

3. Edit .env.prod:

   GATEWAY_ID=<gateway-id>
   GATEWAY_INSTALL_TOKEN=<install-token>
   GATEWAY_NAME=gateway-01
   GATEWAY_WS_PROTOCOL=ws

4. Start the Gateway profile:

   docker compose --env-file .env.prod --profile gateway up -d --build gateway-agent


Optional Local Proxy Agent
--------------------------
Usually Proxy runs on source servers. For a lab deployment, you can run it on
the control-plane host and mount a local source path read-only.

1. Create a Proxy in the web UI and copy its API token.

2. Edit .env.prod:

   PROXY_API_TOKEN=<proxy-api-token>
   PROXY_ROLE=agent
   PROXY_SOURCE_PATH=/data

3. Start the Proxy profile:

   docker compose --env-file .env.prod --profile proxy up -d --build proxy-agent


Start Everything Including Local Agents
---------------------------------------
Only do this after you have valid Gateway and Proxy tokens configured:

   docker compose --env-file .env.prod --profile gateway --profile proxy up -d --build


Development Quick Start
-----------------------
1. Create development env file:

   cp env.dev.sample .env.dev

2. Start development stack:

   docker compose --env-file .env.dev -f docker-compose.dev.yml up -d --build

3. Open:

   Frontend: http://localhost:5173
   Backend:  http://localhost:8000

4. Create an administrator:

   docker compose --env-file .env.dev -f docker-compose.dev.yml exec backend python manage.py createsuperuser


Installer Scripts and Packages
------------------------------
Nginx serves public downloads from backend_static after collectstatic:

   http://<host>:<PUBLIC_HTTP_PORT>/downloads/

Source files are stored in:

   backend/static/downloads/

Important files:

- install-proxy.sh
- install-proxy-macos.sh
- install-proxy.ps1
- install-gateway.sh
- packages/proxy/
- packages/gateway/
- packages/kopia/

To rebuild Proxy package artifacts:

   cd proxy
   ./build.sh all


Operations
----------
View status:

   docker compose --env-file .env.prod ps

Logs:

   docker compose --env-file .env.prod logs -f nginx
   docker compose --env-file .env.prod logs -f control
   docker compose --env-file .env.prod logs -f celery-worker

Restart a service:

   docker compose --env-file .env.prod restart control

Stop services:

   docker compose --env-file .env.prod down

Stop and remove volumes:

   docker compose --env-file .env.prod down -v

Warning: down -v removes database, Redis data, media, logs, and agent data.


Backup Targets
--------------
At minimum back up these named volumes:

- postgres_data
- backend_media
- backend_logs

If local profiles are used:

- gateway_data
- gateway_mount
- gateway_logs
- proxy_data
- proxy_logs


Security Checklist
------------------
- Replace SECRET_KEY.
- Replace POSTGRES_PASSWORD.
- Set ALLOWED_HOSTS to only your real hostnames/IPs plus internal service names.
- Set CSRF_TRUSTED_ORIGINS and CORS_ALLOWED_ORIGINS to the exact public origin.
- Use HTTPS in production.
- Set SESSION_COOKIE_SECURE=true and CSRF_COOKIE_SECURE=true behind HTTPS.
- Put only the Ed25519 public license key in the deployment env.
- Never store the license private key in this repository or server env.
- Keep Postgres and Redis bound to localhost unless external access is required.


Known Compose Behavior
----------------------
- docker-compose.yml is the canonical production file. Docker Compose reads it
  automatically with docker compose.
- If your tooling specifically requires docker-compose.yaml, pass the file
  explicitly or create an environment-local copy.
- Gateway and Proxy services are behind profiles because they require tokens and
  may need privileged filesystem/mount access.
- The backend must run as ASGI. Do not replace Daphne with WSGI-only servers if
  WebSocket agents are required.


Troubleshooting
---------------
Frontend opens but API fails:

- Check PUBLIC_CONTROL_PLANE_URL.
- Check ALLOWED_HOSTS, CSRF_TRUSTED_ORIGINS, and CORS_ALLOWED_ORIGINS.
- Check nginx and control logs.

Agents cannot connect:

- Confirm PUBLIC_CONTROL_PLANE_URL is reachable from the agent host.
- Use ws for HTTP deployments and wss for HTTPS deployments.
- Confirm /ws/ is proxied by Nginx.
- Confirm Gateway/Proxy ID and tokens match the UI.

Static downloads return 404:

- Check control-init completed successfully.
- Check STATIC_ROOT=/app/staticfiles.
- Check backend_static volume is mounted into Nginx.
- Re-run:
  docker compose --env-file .env.prod run --rm control-init

Celery tasks do not run:

- Check Redis URL is redis://redis:6379/0 inside Compose.
- Check celery-worker and celery-beat logs.
- Re-run periodic task registration:
  docker compose --env-file .env.prod exec control python manage.py register_periodic_tasks

Database migration failed:

- Check postgres health.
- Check DATABASE_URL generated from POSTGRES_* variables.
- Check control-init logs:
  docker compose --env-file .env.prod logs control-init
