from .base import PlanningContext, PlanningStrategy, StrategyApplication
from .rules import (
    PLAN_THIS_SUBTASK_NAME,
    PLANNING_PULSE_SUBTASK_NAME,
    PlanningPulseStrategy,
    NoOpenSubTasksStrategy,
)

PLANNING_STRATEGIES: tuple[PlanningStrategy, ...] = (
    NoOpenSubTasksStrategy(),
    PlanningPulseStrategy(),
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
    "PLAN_THIS_SUBTASK_NAME",
    "PLANNING_PULSE_SUBTASK_NAME",
    "PLANNING_STRATEGIES",
    "NoOpenSubTasksStrategy",
    "PlanningPulseStrategy",
    "PlanningContext",
    "PlanningStrategy",
    "StrategyApplication",
    "apply_first_triggered_strategy",
]
