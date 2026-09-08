from util import clickup

from .base import PlanningContext
from .helpers import (
    has_open_subtasks,
    is_next_task_too_far_away,
)

NO_SUBTASKS_SUBTASK_NAME = "Next step!"
NEXT_TASK_TOO_FAR_AWAY_SUBTASK_NAME = "Next task is too far away!"


class NoOpenSubTasksStrategy:
    name = "create_plan_this_subtask"

    def trigger(self, context: PlanningContext) -> bool:
        return not has_open_subtasks(context)

    def apply(self, context: PlanningContext) -> dict[str, int]:
        clickup.create_subtask(
            list_id=context.task_list["id"],
            parent_task_id=context.task["id"],
            name=NO_SUBTASKS_SUBTASK_NAME,
            priority=1,
            due_date=context.due_date
        )

        return {"subtasks_created": 1}


class NextTaskTooFarAwayStrategy:
    name = "create_next_task_too_far_away_subtask"

    def trigger(self, context: PlanningContext) -> bool:
        return is_next_task_too_far_away(context)

    def apply(self, context: PlanningContext) -> dict[str, int]:
        clickup.create_subtask(
            list_id=context.task_list["id"],
            priority=1,
            parent_task_id=context.task["id"],
            name=NEXT_TASK_TOO_FAR_AWAY_SUBTASK_NAME,
            due_date=context.due_date
        )

        return {"subtasks_created": 1}
