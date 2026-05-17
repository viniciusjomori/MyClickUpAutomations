from util import clickup

from .base import PlanningContext
from .helpers import (
    has_open_subtasks,
    is_planning_pulse_stale,
)

NEXT_STEP_SUBTASK_NAME = "Next step!"
PLANNING_PULSE_SUBTASK_NAME = "Planning pulse!"


class NoOpenSubTasksStrategy:
    name = "create_plan_this_subtask"

    def trigger(self, context: PlanningContext) -> bool:
        return not has_open_subtasks(context)

    def apply(self, context: PlanningContext) -> dict[str, int]:
        clickup.create_subtask(
            list_id=context.task_list["id"],
            parent_task_id=context.task["id"],
            name=NEXT_STEP_SUBTASK_NAME,
            priority=1,
            due_date=context.due_date
        )

        return {"subtasks_created": 1}


class PlanningPulseStrategy:
    name = "create_planning_pulse_subtask"

    def trigger(self, context: PlanningContext) -> bool:
        return is_planning_pulse_stale(context)

    def apply(self, context: PlanningContext) -> dict[str, int]:
        clickup.create_subtask(
            list_id=context.task_list["id"],
            priority=1,
            parent_task_id=context.task["id"],
            name=PLANNING_PULSE_SUBTASK_NAME,
            due_date=context.due_date
        )

        return {"subtasks_created": 1}
