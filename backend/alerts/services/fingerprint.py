"""Alert fingerprint helpers."""

import hashlib


def build_fingerprint(policy, resource_id=None, alert_key="default"):
    raw = f"{policy.id}:{resource_id or ''}:{alert_key}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
