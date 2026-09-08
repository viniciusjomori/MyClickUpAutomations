import os
from datetime import date, datetime

from .https import HttpClient

API_KEY = os.getenv("CLICKUP_API_KEY")
TEAM_ID = os.getenv("CLICKUP_TEAM_ID")

TODO_STATUS = "to do"
PRIORITY_NAMES = {"urgent", "high", "normal", "low"}
PRIORITY_ID_TO_NAME = {
    "1": "urgent",
    "2": "high",
    "3": "normal",
    "4": "low",
}
_spaces_by_id = None

http_client = HttpClient(
    base="https://api.clickup.com/api/v2/",
    headers={
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": API_KEY
    },
    raises_exception=True
)


def get_tasks():
    tasks = []
    page = 0

    while True:
        res = http_client.get(
            endpoint=f"team/{TEAM_ID}/task",
            params={
                "page": page,
                "subtasks": "true",
                "include_closed": "false",
                "statuses[]": [TODO_STATUS],
            }
        )
        tasks += res.data["tasks"]

        if res.data["last_page"]:
            break

        page += 1

    today_end_ms = int(datetime.combine(date.today(), datetime.max.time()).timestamp() * 1000)

    return [
        task for task in tasks
        if is_to_do(task)
        and is_due_today_or_before(task, today_end_ms)
    ]


def get_task(task_id: str):
    res = http_client.get(
        endpoint=f"task/{task_id}",
        params={
            "include_subtasks": "true",
        }
    )

    return res.data


def get_space_name(space_id: str | None) -> str:
    if not space_id:
        return ""

    return get_spaces_by_id().get(str(space_id), str(space_id))


def get_spaces_by_id() -> dict[str, str]:
    global _spaces_by_id

    if _spaces_by_id is None:
        res = http_client.get(
            endpoint=f"team/{TEAM_ID}/space",
            params={"archived": "false"}
        )
        _spaces_by_id = {
            str(space["id"]): space.get("name", str(space["id"]))
            for space in res.data["spaces"]
        }

    return _spaces_by_id


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


def get_parent_task_id(task: dict) -> str | None:
    parent = task.get("parent")

    if isinstance(parent, dict):
        parent_id = parent.get("id")
        if parent_id not in (None, ""):
            return str(parent_id)

    if parent not in (None, ""):
        return str(parent)

    return None


def is_to_do(task: dict) -> bool:
    status = task.get("status")

    if isinstance(status, dict):
        return str(status.get("status", "")).lower() == TODO_STATUS

    return str(status or "").lower() == TODO_STATUS


def is_due_today_or_before(task: dict, today_end_ms: int) -> bool:
    due_date = task.get("due_date")

    if due_date in (None, ""):
        return False

    return int(due_date) <= today_end_ms


def get_priority_name(task: dict) -> str:
    priority = task.get("priority")

    if not priority:
        return "none"

    if isinstance(priority, dict):
        priority_name = str(priority.get("priority", "")).strip().lower()
        if priority_name in PRIORITY_NAMES:
            return priority_name

        priority_id = str(priority.get("id", "")).strip()
        return PRIORITY_ID_TO_NAME.get(priority_id, "none")

    priority_value = str(priority).strip().lower()
    if priority_value in PRIORITY_NAMES:
        return priority_value

    return PRIORITY_ID_TO_NAME.get(priority_value, "none")
