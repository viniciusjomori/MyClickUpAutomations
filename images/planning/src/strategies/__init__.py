from .base import PlanningContext, PlanningStrategy, StrategyApplication
from .rules import (
    NO_SUBTASKS_SUBTASK_NAME,
    NEXT_TASK_TOO_FAR_AWAY_SUBTASK_NAME,
    NextTaskTooFarAwayStrategy,
    NoOpenSubTasksStrategy,
)

PLANNING_STRATEGIES: tuple[PlanningStrategy, ...] = (
    NoOpenSubTasksStrategy(),
    NextTaskTooFarAwayStrategy(),
)


def apply_first_triggered_strategy(
    context: PlanningContext,
    strategies: tuple[PlanningStrategy, ...] | list[PlanningStrategy] = PLANNING_STRATEGIES
) -> StrategyApplication | None:
    for strategy in strategies:
        if not strategy.trigger(context):
            continue

        metrics = strategy.apply(context)
        return StrategyApplication(
            strategy_name=strategy.name,
            metrics=metrics
        )

    return None

__all__ = [
    "NO_SUBTASKS_SUBTASK_NAME",
    "NEXT_TASK_TOO_FAR_AWAY_SUBTASK_NAME",
    "PLANNING_STRATEGIES",
    "NoOpenSubTasksStrategy",
    "NextTaskTooFarAwayStrategy",
    "PlanningContext",
    "PlanningStrategy",
    "StrategyApplication",
    "apply_first_triggered_strategy",
]
