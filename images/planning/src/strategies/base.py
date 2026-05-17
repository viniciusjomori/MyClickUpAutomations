from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol

from util import clickup


@dataclass
class PlanningContext:
    task: dict
    task_list: dict
    due_date: datetime
    _detailed_task: dict | None = field(default=None, init=False, repr=False)

    @property
    def detailed_task(self) -> dict:
        if self._detailed_task is None:
            self._detailed_task = clickup.get_task(self.task["id"])

        return self._detailed_task


@dataclass(frozen=True)
class StrategyApplication:
    strategy_name: str
    metrics: dict[str, int]


class PlanningStrategy(Protocol):
    name: str

    def trigger(self, context: PlanningContext) -> bool:
        ...

    def apply(self, context: PlanningContext) -> dict[str, int]:
        ...
