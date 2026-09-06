from __future__ import annotations

from dataclasses import dataclass


class ToolPermissionDenied(PermissionError):
    pass


@dataclass(frozen=True)
class AgentPermission:
    agent_name: str
    allowed_tools: frozenset[str]


TREASURY_PERMISSIONS: dict[str, AgentPermission] = {
    "cash_position_agent": AgentPermission(
        "cash_position_agent", frozenset({"read_balances"})
    ),
    "obligations_agent": AgentPermission(
        "obligations_agent", frozenset({"read_settlements"})
    ),
    "variance_agent": AgentPermission("variance_agent", frozenset()),
    "funding_recommendation_agent": AgentPermission(
        "funding_recommendation_agent", frozenset({"create_recommendation"})
    ),
}


def require_tool(agent_name: str, tool_name: str) -> None:
    permission = TREASURY_PERMISSIONS.get(agent_name)
    if permission is None or tool_name not in permission.allowed_tools:
        raise ToolPermissionDenied(
            f"TOOL_PERMISSION_DENIED: {agent_name} cannot call {tool_name}"
        )
