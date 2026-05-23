"""AI summary helpers for the Gateway agent."""

import asyncio
import json
import logging
import urllib.request
from typing import Optional

from .config import GatewayConfig

logger = logging.getLogger('gateway-agent')

class AIClient:
    """Gateway-side AI provider with a local fallback."""

    def __init__(self, config: GatewayConfig):
        self.config = config

    async def summarize_snapshot(self, snapshot_context: dict, language: str = 'zh-CN', provider_config: Optional[dict] = None) -> dict:
        provider_config = provider_config or {}
        enabled = provider_config.get('enabled', self.config.ai_enabled)
        provider = provider_config.get('provider') or self.config.ai_provider
        api_key = provider_config.get('api_key') or self.config.ai_api_key
        if enabled and api_key and provider in {'openai', 'openai_compatible'}:
            try:
                return await asyncio.to_thread(self._summarize_with_openai_compatible, snapshot_context, language, provider_config)
            except Exception as exc:
                logger.warning(f"AI provider failed, falling back to local summary: {exc}")
        return self._local_summary(snapshot_context, language)

    async def answer_query(self, query: str, context: dict, language: str = 'zh-CN', provider_config: Optional[dict] = None) -> dict:
        provider_config = provider_config or {}
        enabled = provider_config.get('enabled', self.config.ai_enabled)
        provider = provider_config.get('provider') or self.config.ai_provider
        api_key = provider_config.get('api_key') or self.config.ai_api_key
        if enabled and api_key and provider in {'openai', 'openai_compatible'}:
            try:
                return await asyncio.to_thread(self._query_with_openai_compatible, query, context, language, provider_config)
            except Exception as exc:
                logger.warning(f"AI query provider failed, falling back to local answer: {exc}")
        return self._local_query_answer(query, context, language)

    def _summarize_with_openai_compatible(self, snapshot_context: dict, language: str, provider_config: Optional[dict] = None) -> dict:
        provider_config = provider_config or {}
        prompt = self._build_prompt(snapshot_context, language)
        provider = provider_config.get('provider') or self.config.ai_provider
        base_url = provider_config.get('base_url') or self.config.ai_base_url
        api_key = provider_config.get('api_key') or self.config.ai_api_key
        model = provider_config.get('model') or self.config.ai_model
        timeout = int(provider_config.get('timeout') or self.config.ai_timeout)
        url = base_url.rstrip('/') + '/chat/completions'
        payload = {
            'model': model,
            'messages': [
                {
                    'role': 'system',
                    'content': 'You are a backup data intelligence analyst. Return concise JSON only.',
                },
                {'role': 'user', 'content': prompt},
            ],
            'temperature': 0.2,
            'response_format': {'type': 'json_object'},
        }
        request = urllib.request.Request(
            url,
            data=json.dumps(payload).encode('utf-8'),
            headers={
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json',
                **((provider_config.get('config') or {}).get('headers') or {}),
            },
            method='POST',
        )
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = json.loads(response.read().decode('utf-8'))
        content = data['choices'][0]['message']['content']
        result = json.loads(content)
        result.setdefault('provider', provider)
        result.setdefault('model', model)
        return result

    def _query_with_openai_compatible(self, query: str, context: dict, language: str, provider_config: Optional[dict] = None) -> dict:
        provider_config = provider_config or {}
        provider = provider_config.get('provider') or self.config.ai_provider
        base_url = provider_config.get('base_url') or self.config.ai_base_url
        api_key = provider_config.get('api_key') or self.config.ai_api_key
        model = provider_config.get('model') or self.config.ai_model
        timeout = int(provider_config.get('timeout') or self.config.ai_timeout)
        request = urllib.request.Request(
            base_url.rstrip('/') + '/chat/completions',
            data=json.dumps({
                'model': model,
                'messages': [
                    {
                        'role': 'system',
                        'content': 'You answer questions about backup snapshot data. Return concise JSON only.',
                    },
                    {'role': 'user', 'content': self._build_query_prompt(query, context, language)},
                ],
                'temperature': 0.1,
                'response_format': {'type': 'json_object'},
            }).encode('utf-8'),
            headers={
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json',
                **((provider_config.get('config') or {}).get('headers') or {}),
            },
            method='POST',
        )
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = json.loads(response.read().decode('utf-8'))
        result = json.loads(data['choices'][0]['message']['content'])
        result.setdefault('provider', provider)
        result.setdefault('model', model)
        return result

    def _build_prompt(self, snapshot_context: dict, language: str) -> str:
        compact = json.dumps(snapshot_context, ensure_ascii=False)[:24000]
        return f"""
Language: {language}

Analyze this backup snapshot using the structured rule insights below.
Return JSON with keys:
- title
- summary
- risk_level: info|warning|critical
- findings: array of {{title,severity,description,evidence}}
- recommended_actions: array of {{type,label,description}}
- related_paths: array of important paths

Snapshot context:
{compact}
"""

    def _build_query_prompt(self, query: str, context: dict, language: str) -> str:
        compact = json.dumps(context, ensure_ascii=False)[:28000]
        return f"""
Language: {language}

User question:
{query}

Use the indexed file metadata and any provided text samples from backup snapshots.
Return JSON with keys:
- answer
- summary
- confidence: number from 0 to 1
- sources: array of {{path,snapshot_name,repository_name,reason}}
- suggestions: array of follow-up questions or actions

Context:
{compact}
"""

    def _local_summary(self, snapshot_context: dict, language: str) -> dict:
        insights = {item.get('type'): item for item in snapshot_context.get('insights', [])}
        snapshot = snapshot_context.get('snapshot', {})
        categories = (insights.get('file_categories') or {}).get('evidence', {}).get('categories', [])
        duplicate_groups = (insights.get('duplicates') or {}).get('evidence', {}).get('groups', [])
        cold = (insights.get('cold_data') or {}).get('evidence', {})
        growth = (insights.get('growth') or {}).get('evidence', {})
        top_category = categories[0] if categories else {}
        findings = []
        if top_category:
            findings.append({
                'title': 'Dominant file category',
                'severity': 'info',
                'description': f"{top_category.get('category')} is the largest category with {top_category.get('count')} files.",
                'evidence': top_category,
            })
        if duplicate_groups:
            findings.append({
                'title': 'Duplicate candidates detected',
                'severity': 'warning',
                'description': f"{len(duplicate_groups)} duplicate candidate groups were found by name and size.",
                'evidence': {'groups': duplicate_groups[:5]},
            })
        if cold.get('count'):
            findings.append({
                'title': 'Cold data exists',
                'severity': 'warning',
                'description': f"{cold.get('count')} files have not changed for more than {cold.get('days', 90)} days.",
                'evidence': cold,
            })
        risk_level = 'warning' if duplicate_groups or cold.get('count') else 'info'
        return {
            'title': 'AI snapshot summary',
            'summary': f"Snapshot {snapshot.get('name') or snapshot.get('id')} contains {snapshot.get('file_count') or 0} files. Rule insights were analyzed by the Gateway local AI fallback.",
            'risk_level': risk_level,
            'findings': findings,
            'recommended_actions': [
                {'type': 'review_duplicates', 'label': 'Review duplicate candidates', 'description': 'Validate duplicate groups before cleanup.'},
                {'type': 'review_cold_data', 'label': 'Review cold data', 'description': 'Consider archive policy for long-unmodified data.'},
            ],
            'related_paths': [
                path
                for group in duplicate_groups[:3]
                for path in (group.get('paths') or [])[:2]
            ],
            'provider': 'local',
            'model': 'rule-summary',
            'growth': growth,
        }

    def _local_query_answer(self, query: str, context: dict, language: str) -> dict:
        candidates = context.get('candidate_files') or []
        samples = context.get('content_samples') or []
        sources = [
            {
                'path': item.get('path'),
                'snapshot_name': item.get('snapshot_name'),
                'repository_name': item.get('repository_name'),
                'reason': 'Matched indexed metadata',
            }
            for item in candidates[:10]
        ]
        answer = f"Found {len(candidates)} indexed file candidates for: {query}"
        if samples:
            answer += f". Read {len(samples)} content samples from the snapshot for additional context."
        return {
            'answer': answer,
            'summary': answer,
            'confidence': 0.45 if candidates else 0.1,
            'sources': sources,
            'suggestions': [
                'Index the target snapshot before asking content questions.',
                'Narrow the query by snapshot, repository, path, or file type.',
            ],
            'provider': 'local',
            'model': 'metadata-query',
        }
