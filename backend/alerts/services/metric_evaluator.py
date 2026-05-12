"""Metric alert evaluation.

Phase one wires the evaluator entrypoint and keeps metric sampling conservative.
Concrete metric collectors can call fire_alert with the same policy contract.
"""


def evaluate_metric_policy(policy):
    return None
