"""Configuration loading and runtime credential persistence."""

import os
import platform
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DEFAULT_CONFIG_PATHS = (
    '/etc/hyperfilelens/gateway/config.yaml',
    '/opt/hyperfilelens/gateway/config.yaml',
    './config.yaml',
)


def _parse_scalar(value: str) -> Any:
    value = value.strip()
    if not value:
        return ''
    if value[0:1] in ('"', "'") and value[-1:] == value[0]:
        return value[1:-1]
    lowered = value.lower()
    if lowered in ('true', 'yes'):
        return True
    if lowered in ('false', 'no'):
        return False
    try:
        return int(value)
    except ValueError:
        return value


def _load_simple_yaml(path: Path) -> dict[str, Any]:
    data: dict[str, Any] = {}
    current: dict[str, Any] | None = None
    for raw in path.read_text().splitlines():
        if not raw.strip() or raw.lstrip().startswith('#'):
            continue
        content = raw.split('#', 1)[0].rstrip()
        if not content:
            continue
        if not raw.startswith(' ') and content.endswith(':'):
            section = content[:-1].strip()
            current = {}
            data[section] = current
            continue
        if current is None or ':' not in content:
            continue
        key, value = content.split(':', 1)
        current[key.strip()] = _parse_scalar(value)
    return data


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except ValueError:
        return default


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.lower() in ('1', 'true', 'yes')


@dataclass
class GatewayConfig:
    """Gateway Agent configuration."""

    config_path: str = os.getenv('CONFIG_PATH', '')
    env_path: str = os.getenv('CONFIG_ENV_PATH', '/etc/hyperfilelens/gateway/env')

    server_url: str = 'http://localhost:8000'
    gateway_id: str = ''
    api_token: str = ''
    install_token: str = ''
    ws_protocol: str = 'ws'
    reconnect_delay: int = 5
    heartbeat_interval: int = 10

    name: str = 'gateway-01'
    hostname: str = platform.node()

    kopia_path: str = '/usr/bin/kopia'
    mount_base_path: str = '/mnt/kopia'
    max_concurrent_mounts: int = 10
    repo_path: str = '/var/lib/hyperfilelens/repository'
    repo_password: str = ''

    index_enabled: bool = True
    index_path: str = '/var/lib/hyperfilelens/index'

    ai_enabled: bool = True
    ai_provider: str = 'local'
    ai_base_url: str = 'https://api.openai.com/v1'
    ai_api_key: str = ''
    ai_model: str = 'gpt-4.1-mini'
    ai_timeout: int = 60

    log_level: str = 'INFO'
    log_file: str = '/var/log/hyperfilelens/gateway.log'

    @classmethod
    def load(cls, path: str | None = None) -> 'GatewayConfig':
        cfg = cls()
        cfg.config_path = path or os.getenv('CONFIG_PATH', cfg.config_path)
        selected_path = cfg.config_path
        if not selected_path:
            for candidate in DEFAULT_CONFIG_PATHS:
                if Path(candidate).exists():
                    selected_path = candidate
                    break
        if selected_path and Path(selected_path).exists():
            cfg.config_path = selected_path
            cfg._apply_file(_load_simple_yaml(Path(selected_path)))
        cfg._apply_environment()
        return cfg

    def _apply_file(self, data: dict[str, Any]) -> None:
        server = data.get('server') or {}
        gateway = data.get('gateway') or {}
        install = data.get('install') or {}
        kopia = data.get('kopia') or {}
        index = data.get('index') or {}
        ai = data.get('ai') or {}
        logging = data.get('logging') or {}

        self.server_url = str(server.get('url') or self.server_url)
        self.api_token = str(server.get('api_token') or self.api_token)
        self.ws_protocol = str(server.get('ws_protocol') or self.ws_protocol)
        self.reconnect_delay = int(server.get('reconnect_delay') or self.reconnect_delay)
        self.heartbeat_interval = int(server.get('heartbeat_interval') or self.heartbeat_interval)

        self.gateway_id = str(gateway.get('id') or self.gateway_id)
        self.name = str(gateway.get('name') or self.name)
        self.install_token = str(gateway.get('install_token') or install.get('token') or self.install_token)

        self.kopia_path = str(kopia.get('path') or self.kopia_path)
        self.mount_base_path = str(kopia.get('mount_base_path') or self.mount_base_path)
        self.max_concurrent_mounts = int(kopia.get('max_concurrent_mounts') or self.max_concurrent_mounts)
        self.repo_path = str(kopia.get('repository_path') or self.repo_path)
        self.repo_password = str(kopia.get('password') or self.repo_password)

        self.index_enabled = bool(index.get('enabled', self.index_enabled))
        self.index_path = str(index.get('index_path') or self.index_path)

        self.ai_enabled = bool(ai.get('enabled', self.ai_enabled))
        self.ai_provider = str(ai.get('provider') or self.ai_provider)
        self.ai_base_url = str(ai.get('base_url') or ai.get('api_endpoint') or self.ai_base_url)
        self.ai_api_key = str(ai.get('api_key') or self.ai_api_key)
        self.ai_model = str(ai.get('model') or self.ai_model)
        self.ai_timeout = int(ai.get('timeout') or self.ai_timeout)

        self.log_level = str(logging.get('level') or self.log_level).upper()
        self.log_file = str(logging.get('file') or self.log_file)

    def _apply_environment(self) -> None:
        self.server_url = os.getenv('SERVER_URL', self.server_url)
        self.gateway_id = os.getenv('GATEWAY_ID', self.gateway_id)
        self.api_token = os.getenv('API_TOKEN', self.api_token)
        self.install_token = os.getenv('INSTALL_TOKEN', self.install_token)
        self.ws_protocol = os.getenv('WS_PROTOCOL', self.ws_protocol)
        self.reconnect_delay = _env_int('RECONNECT_DELAY', self.reconnect_delay)
        self.heartbeat_interval = _env_int('HEARTBEAT_INTERVAL', self.heartbeat_interval)
        self.name = os.getenv('GATEWAY_NAME', self.name)
        self.kopia_path = os.getenv('KOPIA_PATH', self.kopia_path)
        self.mount_base_path = os.getenv('MOUNT_BASE_PATH', self.mount_base_path)
        self.max_concurrent_mounts = _env_int('MAX_MOUNTS', self.max_concurrent_mounts)
        self.repo_path = os.getenv('REPO_PATH', self.repo_path)
        self.repo_password = os.getenv('KOPIA_PASSWORD', self.repo_password)
        self.index_enabled = _env_bool('INDEX_ENABLED', self.index_enabled)
        self.index_path = os.getenv('INDEX_PATH', self.index_path)
        self.ai_enabled = _env_bool('AI_ENABLED', self.ai_enabled)
        self.ai_provider = os.getenv('AI_PROVIDER', self.ai_provider)
        self.ai_base_url = os.getenv('AI_BASE_URL', os.getenv('AI_API_URL', self.ai_base_url))
        self.ai_api_key = os.getenv('AI_API_KEY', self.ai_api_key)
        self.ai_model = os.getenv('AI_MODEL', self.ai_model)
        self.ai_timeout = _env_int('AI_TIMEOUT', self.ai_timeout)
        self.log_level = os.getenv('LOG_LEVEL', self.log_level).upper()
        self.log_file = os.getenv('LOG_FILE', self.log_file)

    def websocket_url(self) -> str:
        base = self.server_url.rstrip('/')
        if base.startswith('https://'):
            base = 'wss://' + base[len('https://'):]
        elif base.startswith('http://'):
            base = f'{self.ws_protocol}://' + base[len('http://'):]
        return f'{base}/ws/gateway/{self.gateway_id}/'

    def save_runtime_credentials(self, api_token: str | None = None, install_token: str | None = None) -> None:
        if api_token is not None:
            self.api_token = api_token
        if install_token is not None:
            self.install_token = install_token
        self._write_env_file()
        self._write_config_file()

    def _write_env_file(self) -> None:
        path = Path(self.env_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        values = {
            'SERVER_URL': self.server_url,
            'INSTALL_TOKEN': self.install_token,
            'API_TOKEN': self.api_token,
            'GATEWAY_ID': self.gateway_id,
            'GATEWAY_NAME': self.name,
        }
        existing: list[str] = []
        seen: set[str] = set()
        if path.exists():
            existing = path.read_text().splitlines()
        output: list[str] = []
        for line in existing:
            key = line.split('=', 1)[0] if '=' in line else ''
            if key in values:
                output.append(f'{key}={values[key]}')
                seen.add(key)
            else:
                output.append(line)
        for key, value in values.items():
            if key not in seen:
                output.append(f'{key}={value}')
        path.write_text('\n'.join(output) + '\n')
        try:
            path.chmod(0o600)
        except OSError:
            pass

    def _write_config_file(self) -> None:
        if not self.config_path:
            return
        path = Path(self.config_path)
        if not path.exists():
            return
        lines = path.read_text().splitlines()
        section = ''
        output: list[str] = []
        for line in lines:
            stripped = line.strip()
            if stripped and not line.startswith(' ') and stripped.endswith(':'):
                section = stripped[:-1]
            if section == 'server' and stripped.startswith('api_token:'):
                output.append(f'  api_token: "{self.api_token}"')
            elif section == 'gateway' and stripped.startswith('install_token:'):
                output.append(f'  install_token: "{self.install_token}"')
            elif section == 'install' and stripped.startswith('token:'):
                output.append(f'  token: "{self.install_token}"')
            else:
                output.append(line)
        path.write_text('\n'.join(output) + '\n')
