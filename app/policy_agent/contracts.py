"""Serializable contracts. No UI, SDK, model, or dataset dependency."""
from dataclasses import dataclass, field, asdict
from typing import Protocol, Callable

STATUSES = ["success", "unsupported", "insufficient_data", "out_of_scope", "not_ready"]


@dataclass
class PolicyToolResult:
    tool_name: str
    status: str = "success"
    data: dict = field(default_factory=dict)
    evidence: list = field(default_factory=list)
    sources: list = field(default_factory=list)
    data_period: dict = field(default_factory=dict)
    reliability: list = field(default_factory=list)
    limitations: list = field(default_factory=list)

    def to_dict(self):
        return asdict(self)


@dataclass
class SessionContext:
    active_districts: list[str] = field(default_factory=list)
    active_metric: str | None = None
    previous_intent: str | None = None


@dataclass
class ToolCall:
    name: str
    arguments: dict = field(default_factory=dict)


@dataclass
class AgentPlan:
    calls: list[ToolCall] = field(default_factory=list)
    intent: str = "unsupported"
    status: str = "success"
    districts: list[str] = field(default_factory=list)
    metric: str | None = None


class AgentPlanner(Protocol):
    def plan(self, question: str, session: SessionContext, districts: list[str]) -> AgentPlan: ...


class EnginePort(Protocol):
    def snapshot(self) -> dict: ...
    def lookup(self, district: str, context: dict) -> dict: ...
    def compare(self, districts: list[str], context: dict) -> dict: ...


class KnowledgeSearch(Protocol):
    def search(self, query: str) -> list[dict]: ...


class AgentOrchestrator(Protocol):
    def run(self, question: str, session: SessionContext | None = None) -> dict: ...
