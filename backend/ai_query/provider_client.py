import json
import re
import time
from typing import Iterable

import requests

from .models import AIProvider


def chat_completions_url(base_url):
    normalized = str(base_url or '').rstrip('/')
    if normalized.endswith('/chat/completions'):
        return normalized
    if normalized.endswith('/v1'):
        return f'{normalized}/chat/completions'
    return f'{normalized}/v1/chat/completions'


def sse_event(data):
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


def sse_comment(text=''):
    return f": {text}\n\n"


def extract_json_object(text):
    if isinstance(text, dict):
        return text
    content = (text or '').strip()
    if not content:
        return {}
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", content, re.S)
    if fenced:
        content = fenced.group(1)
    if not content.startswith('{'):
        start = content.find('{')
        end = content.rfind('}')
        if start >= 0 and end > start:
            content = content[start:end + 1]
    try:
        return json.loads(content)
    except Exception:
        return {'answer': text, 'summary': text}


class AIProviderClient:
    """Small OpenAI-compatible client shared by provider tests and AI Insights."""

    def __init__(self, provider: AIProvider | None):
        self.provider = provider

    @property
    def model(self):
        if not self.provider:
            return 'metadata-query'
        return self.provider.default_model or 'gpt-4.1-mini'

    @property
    def provider_type(self):
        if not self.provider:
            return 'local'
        return self.provider.provider_type

    def is_external(self):
        return bool(
            self.provider
            and self.provider.provider_type != AIProvider.PROVIDER_LOCAL
            and self.provider.get_decrypted_api_key()
        )

    def _headers(self):
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.provider.get_decrypted_api_key()}',
        }
        extra_headers = (self.provider.config or {}).get('headers') if isinstance(self.provider.config, dict) else None
        if isinstance(extra_headers, dict):
            headers.update({str(key): str(value) for key, value in extra_headers.items()})
        return headers

    def complete_json(self, messages, max_tokens=4096, temperature=0.2):
        if not self.is_external():
            raise ValueError('No external AI provider configured')
        payload = {
            'stream': False,
            'model': self.model,
            'messages': messages,
            'max_tokens': max_tokens,
            'temperature': temperature,
            'response_format': {'type': 'json_object'},
        }
        started = time.monotonic()
        response = requests.post(
            chat_completions_url(self.provider.base_url),
            headers=self._headers(),
            json=payload,
            timeout=max(5, min(int(self.provider.timeout_seconds or 60), 180)),
        )
        latency_ms = int((time.monotonic() - started) * 1000)
        response.raise_for_status()
        data = response.json()
        choices = data.get('choices') or []
        content = ''
        if choices:
            content = (choices[0].get('message') or {}).get('content') or choices[0].get('text') or ''
        result = extract_json_object(content)
        result.setdefault('provider', self.provider_type)
        result.setdefault('model', data.get('model') or self.model)
        result.setdefault('latency_ms', latency_ms)
        usage = data.get('usage') or {}
        if usage:
            result.setdefault('usage', usage)
            result.setdefault('tokens_used', usage.get('total_tokens') or 0)
        return result

    def stream_chat(self, messages, max_tokens=4096, temperature=0.2) -> Iterable[dict]:
        if not self.is_external():
            raise ValueError('No external AI provider configured')
        payload = {
            'stream': True,
            'model': self.model,
            'messages': messages,
            'max_tokens': max_tokens,
            'temperature': temperature,
        }
        started = time.monotonic()
        with requests.post(
            chat_completions_url(self.provider.base_url),
            headers=self._headers(),
            json=payload,
            stream=True,
            timeout=max(5, min(int(self.provider.timeout_seconds or 60), 180)),
        ) as response:
            latency_ms = int((time.monotonic() - started) * 1000)
            if response.status_code >= 400:
                yield {
                    'type': 'error',
                    'error': response.text[:1000],
                    'status_code': response.status_code,
                    'url': chat_completions_url(self.provider.base_url),
                }
                return
            model = self.model
            yield {
                'type': 'meta',
                'provider': self.provider_type,
                'model': model,
                'url': chat_completions_url(self.provider.base_url),
                'latency_ms': latency_ms,
            }
            for line in response.iter_lines(chunk_size=1, decode_unicode=True):
                if not line:
                    continue
                if line.startswith('data:'):
                    line = line[5:].strip()
                if line == '[DONE]':
                    break
                try:
                    chunk = json.loads(line)
                except json.JSONDecodeError:
                    continue
                model = chunk.get('model') or model
                choices = chunk.get('choices') or []
                if not choices:
                    continue
                delta = choices[0].get('delta') or {}
                message = choices[0].get('message') or {}
                content = delta.get('content') or message.get('content') or choices[0].get('text') or ''
                if content:
                    yield {'type': 'delta', 'content': content, 'model': model}
            yield {'type': 'done', 'model': model}
