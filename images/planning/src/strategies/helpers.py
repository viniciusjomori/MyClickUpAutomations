import os
from datetime import date, datetime, timedelta

from .base import PlanningContext

DEFAULT_PLANNING_PULSE_RANGES = {
    "urgent": 1,
    "high": 3,
    "normal": 7,
    "low": 14,
    "none": 21,
}
PRIORITY_ID_TO_NAME = {
    "1": "urgent",
    "2": "high",
    "3": "normal",
    "4": "low",
}


def is_open_status(status: dict | None) -> bool:
    if not status:
        return True

    if status.get("type") == "closed":
        return False

    return str(status.get("status", "")).strip().lower() not in {"closed"}


def get_subtasks(context: PlanningContext) -> list[dict]:
    return context.detailed_task.get("subtasks", [])


def has_open_subtasks(context: PlanningContext) -> bool:
    return any(is_open_status(subtask.get("status")) for subtask in get_subtasks(context))


def parse_due_date(due_date) -> date | None:
    if due_date in (None, ""):
        return None

    return datetime.fromtimestamp(int(due_date) / 1000).date()


def nearest_open_subtask_due_date(context: PlanningContext) -> date | None:
    due_dates = [
        due_date
        for subtask in get_subtasks(context)
        if is_open_status(subtask.get("status"))
        for due_date in [parse_due_date(subtask.get("due_date"))]
        if due_date is not None
    ]

    if not due_dates:
        return None

    return min(due_dates)


def get_parent_priority_name(context: PlanningContext) -> str:
    priority = context.task.get("priority") or context.detailed_task.get("priority")

    if not priority:
        return "none"

    if isinstance(priority, dict):
        priority_name = str(priority.get("priority", "")).strip().lower()
        if priority_name in DEFAULT_PLANNING_PULSE_RANGES:
            return priority_name

        priority_id = str(priority.get("id", "")).strip()
        return PRIORITY_ID_TO_NAME.get(priority_id, "none")

    priority_value = str(priority).strip().lower()
    if priority_value in DEFAULT_PLANNING_PULSE_RANGES:
        return priority_value

    return PRIORITY_ID_TO_NAME.get(priority_value, "none")


def get_planning_pulse_range(priority_name: str) -> int:
    env_key = f"PLANNING_PULSE_RANGE_{priority_name.upper()}"
    raw_value = os.getenv(env_key)

    if raw_value in (None, ""):
        return DEFAULT_PLANNING_PULSE_RANGES[priority_name]

    return int(raw_value)


def is_planning_pulse_stale(context: PlanningContext) -> bool:
    nearest_due_date = nearest_open_subtask_due_date(context)
    if nearest_due_date is None:
        return False

    priority_name = get_parent_priority_name(context)
    allowed_range = get_planning_pulse_range(priority_name)
    threshold = context.due_date.date() + timedelta(days=allowed_range)

    return nearest_due_date > threshold
