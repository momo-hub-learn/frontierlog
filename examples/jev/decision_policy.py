"""Offline teaching policy. No network, model weights, credentials, or tool execution.

The probabilities and threshold in main() are fabricated fixtures for branch tests,
NOT calibrated recommendations or measured Jev predictions.
"""
from __future__ import annotations
from dataclasses import dataclass, replace
import json
import math


@dataclass(frozen=True)
class Signals:
    p_support: float
    remaining_rounds: int
    model_version: str = 'jev-1.13.0'
    rubric_version: str = 'evidence-v2'
    read_allowed: bool = True
    operation: str = 'read'
    response_valid: bool = True
    conflict: bool = False
    entity_match: bool = True
    evidence_current: bool = True

    def __post_init__(self):
        if type(self.p_support) not in (float, int) or not math.isfinite(self.p_support) or not 0 <= self.p_support <= 1:
            raise ValueError('p_support must be finite and within [0, 1]')
        if type(self.remaining_rounds) is not int or self.remaining_rounds < 0:
            raise ValueError('remaining_rounds must be a nonnegative integer')
        if self.operation not in {'read', 'write'}:
            raise ValueError('unknown operation')
        for value in (self.read_allowed, self.response_valid, self.conflict, self.entity_match, self.evidence_current):
            if type(value) is not bool:
                raise ValueError('hard constraints must be booleans, not truthy strings')
        if not self.model_version or not self.rubric_version:
            raise ValueError('version identifiers are required')


@dataclass(frozen=True)
class Policy:
    support_floor: float
    model_version: str = 'jev-1.13.0'
    rubric_version: str = 'evidence-v2'
    validated_for_domain: bool = False

    def __post_init__(self):
        if type(self.support_floor) not in (float, int) or not math.isfinite(self.support_floor) or not 0 <= self.support_floor <= 1:
            raise ValueError('invalid threshold')
        if type(self.validated_for_domain) is not bool:
            raise ValueError('validation flag must be boolean')

    def is_current(self, signals: Signals) -> bool:
        return (self.validated_for_domain
                and self.model_version == signals.model_version
                and self.rubric_version == signals.rubric_version)


def decide(signals, policy):
    if not signals.read_allowed:
        return 'deny'
    if signals.operation != 'read':
        return 'approval_required'
    if not policy.is_current(signals):
        return 'review'
    if not signals.response_valid or signals.conflict:
        return 'review'
    if not signals.entity_match or not signals.evidence_current:
        return 'retrieve' if signals.remaining_rounds > 0 else 'review'
    if signals.p_support >= policy.support_floor:
        return 'draft_with_citations'
    return 'retrieve' if signals.remaining_rounds > 0 else 'review'


def cost_threshold(error_cost: float, review_cost: float) -> float:
    """Simplified derivation only: perfect review, zero loss for correct automation."""
    if any(type(x) not in (float, int) or not math.isfinite(x) for x in (error_cost, review_cost)):
        raise ValueError('costs must be finite numbers')
    if error_cost <= 0 or review_cost < 0:
        raise ValueError('error cost must be positive and review cost nonnegative')
    return 1 - review_cost / error_cost


def main() -> None:
    # Marked as validated ONLY to exercise the teaching branches, not a deployment claim.
    teaching_policy = Policy(0.95, validated_for_domain=True)
    base = Signals(0.08, remaining_rounds=2)
    cases = [
        ('01_insufficient_evidence', base),
        ('02_wrong_batch', replace(base, p_support=0.99, entity_match=False)),
        ('03_conflicting_versions', replace(base, p_support=0.99, conflict=True)),
        ('04_write_request', replace(base, p_support=0.99, operation='write')),
        ('budget_exhausted', replace(base, remaining_rounds=0)),
        ('no_read_permission', replace(base, read_allowed=False)),
    ]
    print(json.dumps({'mode':'offline_policy_fixtures_NOT_model_evaluation',
        'cases':[{'case':name, 'decision':decide(signals,teaching_policy)} for name,signals in cases],
        'note':'All probabilities and the threshold are illustrative; no action is executed.'},
        ensure_ascii=False,indent=2))


if __name__ == '__main__':
    main()
