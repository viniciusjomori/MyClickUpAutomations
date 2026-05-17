import logging
from datetime import date, datetime

from util import clickup
from strategies import PlanningContext, apply_first_triggered_strategy

logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] [%(asctime)s] [%(name)s] %(message)s",
    encoding="utf-8",
    force=True
)
LOGGER = logging.getLogger(__name__)

PLANNING_STATUS = "planning"


def add_metrics(totals: dict[str, int], metrics: dict[str, int]) -> None:
    for name, value in metrics.items():
        totals[name] = totals.get(name, 0) + value


def handler(event, context):
    due_date = datetime.combine(date.today(), datetime.min.time())
    totals = {"subtasks_created": 0}
    strategies_applied = {}

    for space in clickup.get_spaces():
        LOGGER.info("[SPACE] %s", space["name"])

        for task_list in clickup.get_lists(space["id"]):
            LOGGER.info("[LIST] %s", task_list["name"])

            tasks = clickup.get_tasks(
                list_id=task_list["id"],
                statuses=[PLANNING_STATUS]
            )

            for task in tasks:
                application = apply_first_triggered_strategy(
                    PlanningContext(
                        task=task,
                        task_list=task_list,
                        due_date=due_date
                    )
                )

                if application is None:
                    continue

                add_metrics(totals, application.metrics)
                strategies_applied[application.strategy_name] = (
                    strategies_applied.get(application.strategy_name, 0) + 1
                )
                LOGGER.info(
                    "[TASK] applied strategy=%s task=%s",
                    application.strategy_name,
                    task["id"]
                )

    return {
        **totals,
        "strategies_applied": strategies_applied
    }
