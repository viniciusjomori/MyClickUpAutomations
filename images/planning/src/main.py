import logging
import os
from datetime import date, datetime

from util import clickup, holiday
from strategies import PlanningContext, apply_first_triggered_strategy

logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] [%(asctime)s] [%(name)s] %(message)s",
    encoding="utf-8",
    force=True
)
LOGGER = logging.getLogger(__name__)

PLANNING_STATUS = "planning"


def get_workday_only_space_ids() -> set[str]:
    raw_space_ids = os.getenv("PLANNING_WORKDAY_ONLY_SPACE_IDS", "")
    return {
        space_id.strip()
        for space_id in raw_space_ids.split(",")
        if space_id.strip()
    }


def should_skip_space(
    space: dict,
    workday_only_space_ids: set[str],
    today_is_workday: bool
) -> bool:
    if str(space["id"]) not in workday_only_space_ids:
        return False

    return not today_is_workday


def is_workday(reference_date: date, has_workday_only_spaces: bool) -> bool:
    if not has_workday_only_spaces:
        return True

    if reference_date.weekday() >= 5:
        return False

    return not holiday.is_holiday(reference_date)


def add_metrics(totals: dict[str, int], metrics: dict[str, int]) -> None:
    for name, value in metrics.items():
        totals[name] = totals.get(name, 0) + value


def handler(event, context):
    today = date.today()
    due_date = datetime.combine(today, datetime.min.time())
    workday_only_space_ids = get_workday_only_space_ids()
    today_is_workday = is_workday(today, len(workday_only_space_ids) > 0)
    totals = {"subtasks_created": 0}
    strategies_applied = {}

    for space in clickup.get_spaces():
        LOGGER.info("[SPACE] %s", space["name"])

        if should_skip_space(space, workday_only_space_ids, today_is_workday):
            LOGGER.info("[SPACE] skipping non-workday space=%s", space["id"])
            continue

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
