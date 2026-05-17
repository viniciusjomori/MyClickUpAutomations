import logging
from datetime import date, datetime, timedelta

from util import clickup, holiday

logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] [%(asctime)s] [%(name)s] %(message)s",
    encoding="utf-8",
    force=True
)
LOGGER = logging.getLogger(__name__)


def should_skip(event):
    holiday_mode = event.get("holidays", None)

    if holiday_mode is None:
        return False

    if holiday_mode not in ("ignore", "consider"):
        raise ValueError("holidays must be null, ignore or consider")

    today_is_holiday = holiday.is_holiday(date.today())

    LOGGER.info(
        "[HOLIDAY] today_is_holiday=%s; holidays=%s",
        today_is_holiday,
        holiday_mode
    )

    if holiday_mode == "ignore":
        return today_is_holiday

    return not today_is_holiday


def handler(event, context):
    tag = event["tag"]
    target_archived = event["archived"]
    current_archived = not target_archived
    today = datetime.combine(date.today(), datetime.min.time())
    tomorrow = today + timedelta(days=1)
    updated_tasks = 0

    if should_skip(event):
        return {
            "tasks_updated": 0,
            "message": "Skipped"
        }

    for space in clickup.get_spaces():
        LOGGER.info("[SPACE] %s", space["name"])

        for task_list in clickup.get_lists(space["id"]):
            LOGGER.info("[LIST] %s", task_list["name"])

            tasks = clickup.get_tasks(
                list_id=task_list["id"],
                tag=tag,
                archived=current_archived,
                due_date_gte=today,
                due_date_lt=tomorrow
            )

            for task in tasks:
                LOGGER.info(
                    "[TASK] setting archived=%s for %s",
                    target_archived,
                    task["id"]
                )
                clickup.update_task_archived(task["id"], target_archived)
                updated_tasks += 1

    result = {
        "tasks_updated": updated_tasks,
        "message": f"Updated archived={target_archived} for {updated_tasks} tasks due today with tag {tag}"
    }

    LOGGER.info("[RESULT] %s", result)

    return result
