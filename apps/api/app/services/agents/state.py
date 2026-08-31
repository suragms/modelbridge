"""Agent execution state machine."""

from __future__ import annotations

from app.models.agent import ExecutionStatus

TERMINAL = frozenset({
    ExecutionStatus.COMPLETED,
    ExecutionStatus.FAILED,
    ExecutionStatus.CANCELLED,
    ExecutionStatus.TIMED_OUT,
})

ALLOWED: dict[str, frozenset[str]] = {
    ExecutionStatus.QUEUED: frozenset({
        ExecutionStatus.RUNNING,
        ExecutionStatus.CANCELLED,
    }),
    ExecutionStatus.RUNNING: frozenset({
        ExecutionStatus.COMPLETED,
        ExecutionStatus.FAILED,
        ExecutionStatus.CANCELLED,
        ExecutionStatus.TIMED_OUT,
        ExecutionStatus.WAITING_FOR_APPROVAL,
    }),
    ExecutionStatus.WAITING_FOR_APPROVAL: frozenset({
        ExecutionStatus.RUNNING,
        ExecutionStatus.CANCELLED,
        ExecutionStatus.FAILED,
    }),
}


class InvalidStateTransition(Exception):
    pass


def can_transition(current: str, new: str) -> bool:
    if current in TERMINAL:
        return False
    return new in ALLOWED.get(current, frozenset())


def assert_transition(current: str, new: str) -> None:
    if not can_transition(current, new):
        raise InvalidStateTransition(f"Cannot transition from {current} to {new}")
