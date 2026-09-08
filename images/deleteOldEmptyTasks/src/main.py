import logging
import os
from datetime import date, datetime, timedelta

from util import clickup

logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] [%(asctime)s] [%(name)s] %(message)s",
    encoding="utf-8",
    force=True
)

LOGGER = logging.getLogger(__name__)


def get_retention_days() -> int:
    retention_days = int(os.getenv("DELETE_OLD_EMPTY_TASKS_DAYS", "30"))

    if retention_days <= 0:
        raise ValueError("DELETE_OLD_EMPTY_TASKS_DAYS must be greater than zero")

    return retention_days


def get_ignored_space_ids() -> set[str]:
    raw_space_ids = os.getenv("DELETE_OLD_EMPTY_TASKS_IGNORED_SPACE_IDS", "")
    return {
        space_id.strip()
        for space_id in raw_space_ids.split(",")
        if space_id.strip()
    }


def has_description(task: dict) -> bool:
    return any(
        bool(str(task.get(field) or "").strip())
        for field in ("description", "text_content")
    )


def has_subtasks(task: dict) -> bool:
    return len(task.get("subtasks", [])) > 0


def get_space_id(task: dict) -> str | None:
    space = task.get("space")

    if isinstance(space, dict):
        space_id = space.get("id")
        if space_id not in (None, ""):
            return str(space_id)

    space_id = task.get("space_id")
    if space_id not in (None, ""):
        return str(space_id)

    return None


def handler(event, context):
    retention_days = get_retention_days()
    ignored_space_ids = get_ignored_space_ids()
    created_before = datetime.combine(
        date.today() - timedelta(days=retention_days),
        datetime.min.time()
    )

    totals = {
        "tasks_checked": 0,
        "tasks_deleted": 0,
        "tasks_skipped_with_description": 0,
        "tasks_skipped_with_comments": 0,
        "tasks_skipped_with_subtasks": 0,
        "tasks_skipped_ignored_space": 0,
    }

    tasks = clickup.get_tasks_created_before(created_before=created_before)

    for task in tasks:
        totals["tasks_checked"] += 1

        if get_space_id(task) in ignored_space_ids:
            totals["tasks_skipped_ignored_space"] += 1
            continue

        if has_description(task):
            totals["tasks_skipped_with_description"] += 1
            continue

        if has_subtasks(task):
            totals["tasks_skipped_with_subtasks"] += 1
            continue

        detailed_task = clickup.get_task(task["id"])
        LOGGER.info("[TASK] checking %s", detailed_task["id"])

        if get_space_id(detailed_task) in ignored_space_ids:
            totals["tasks_skipped_ignored_space"] += 1
            continue

        if has_description(detailed_task):
            totals["tasks_skipped_with_description"] += 1
            continue

        if has_subtasks(detailed_task):
            totals["tasks_skipped_with_subtasks"] += 1
            continue

        if clickup.has_comments(detailed_task["id"]):
            totals["tasks_skipped_with_comments"] += 1
            continue

        LOGGER.info("[TASK] deleting %s", detailed_task["id"])
        clickup.delete_task(detailed_task["id"])
        totals["tasks_deleted"] += 1

    LOGGER.info("[RESULT] %s", totals)
    return totals
