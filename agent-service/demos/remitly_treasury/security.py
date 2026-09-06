from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class TreasuryAuthorizationError(PermissionError):
    """Raised when a Treasury agent requests a capability or data scope it does not own."""


class TreasuryCapability(str, Enum):
    ANALYZE_CASH_POSITION = "analyze_cash_position"
    ANALYZE_OBLIGATIONS = "analyze_obligations"
    RECONCILE_VARIANCE = "reconcile_variance"
    RECOMMEND_FUNDING = "recommend_funding"
    EVALUATE_APPROVAL = "evaluate_approval"


class TreasuryDataScope(str, Enum):
    BALANCE_SNAPSHOT = "balance_snapshot"
    SETTLEMENT_SNAPSHOT = "settlement_snapshot"
    CASH_POSITION_RESULT = "cash_position_result"
    OBLIGATIONS_RESULT = "obligations_result"
    VARIANCE_RESULT = "variance_result"
    FUNDING_POLICY = "funding_policy"
    FUNDING_RECOMMENDATION_RESULT = "funding_recommendation_result"


@dataclass(frozen=True)
class TreasuryAgentPermission:
    agent_name: str
    allowed_capabilities: frozenset[TreasuryCapability]
    allowed_data_scopes: frozenset[TreasuryDataScope]
    network_access: bool = False
    can_execute_funds: bool = False


TREASURY_AGENT_PERMISSIONS: dict[str, TreasuryAgentPermission] = {
    "cash_position_agent": TreasuryAgentPermission(
        agent_name="cash_position_agent",
        allowed_capabilities=frozenset({
            TreasuryCapability.ANALYZE_CASH_POSITION,
        }),
        allowed_data_scopes=frozenset({
            TreasuryDataScope.BALANCE_SNAPSHOT,
        }),
    ),
    "obligations_agent": TreasuryAgentPermission(
        agent_name="obligations_agent",
        allowed_capabilities=frozenset({
            TreasuryCapability.ANALYZE_OBLIGATIONS,
        }),
        allowed_data_scopes=frozenset({
            TreasuryDataScope.SETTLEMENT_SNAPSHOT,
        }),
    ),
    "variance_agent": TreasuryAgentPermission(
        agent_name="variance_agent",
        allowed_capabilities=frozenset({
            TreasuryCapability.RECONCILE_VARIANCE,
        }),
        allowed_data_scopes=frozenset({
            TreasuryDataScope.CASH_POSITION_RESULT,
            TreasuryDataScope.OBLIGATIONS_RESULT,
        }),
    ),
    "funding_recommendation_agent": TreasuryAgentPermission(
        agent_name="funding_recommendation_agent",
        allowed_capabilities=frozenset({
            TreasuryCapability.RECOMMEND_FUNDING,
        }),
        allowed_data_scopes=frozenset({
            TreasuryDataScope.CASH_POSITION_RESULT,
            TreasuryDataScope.VARIANCE_RESULT,
            TreasuryDataScope.FUNDING_POLICY,
        }),
    ),
    "treasury_approval_gate": TreasuryAgentPermission(
        agent_name="treasury_approval_gate",
        allowed_capabilities=frozenset({
            TreasuryCapability.EVALUATE_APPROVAL,
        }),
        allowed_data_scopes=frozenset({
            TreasuryDataScope.FUNDING_RECOMMENDATION_RESULT,
            TreasuryDataScope.FUNDING_POLICY,
        }),
    ),
}


class TreasuryCapabilityGuard:
    """Server-owned least-privilege authorization boundary for the demo runtime."""

    def permission_for(self, agent_name: str) -> TreasuryAgentPermission:
        permission = TREASURY_AGENT_PERMISSIONS.get(agent_name)
        if permission is None:
            raise TreasuryAuthorizationError(
                f"Unknown or unregistered Treasury agent: {agent_name}"
            )
        return permission

    def authorize(
        self,
        *,
        agent_name: str,
        capability: TreasuryCapability,
        data_scopes: set[TreasuryDataScope] | frozenset[TreasuryDataScope],
    ) -> TreasuryAgentPermission:
        permission = self.permission_for(agent_name)

        if capability not in permission.allowed_capabilities:
            raise TreasuryAuthorizationError(
                f"{agent_name} is not authorized for capability "
                f"{capability.value}."
            )

        requested_scopes = frozenset(data_scopes)
        unauthorized_scopes = requested_scopes - permission.allowed_data_scopes
        if unauthorized_scopes:
            names = ", ".join(sorted(scope.value for scope in unauthorized_scopes))
            raise TreasuryAuthorizationError(
                f"{agent_name} is not authorized to access data scope(s): {names}."
            )

        if permission.network_access:
            raise TreasuryAuthorizationError(
                f"{agent_name} unexpectedly has network access in the Treasury demo."
            )

        if permission.can_execute_funds:
            raise TreasuryAuthorizationError(
                f"{agent_name} unexpectedly has fund-execution permission."
            )

        return permission

    def assert_no_execution_capability(self) -> None:
        violators = [
            p.agent_name
            for p in TREASURY_AGENT_PERMISSIONS.values()
            if p.can_execute_funds
        ]
        if violators:
            raise TreasuryAuthorizationError(
                "Treasury demo must not grant fund-execution permission to: "
                + ", ".join(sorted(violators))
            )
