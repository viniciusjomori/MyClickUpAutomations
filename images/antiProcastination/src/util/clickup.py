import os
from datetime import date, datetime

from .https import HttpClient, RequestException

API_KEY = os.getenv("CLICKUP_API_KEY")
TEAM_ID = os.getenv("CLICKUP_TEAM_ID")

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
    """Fetch open tasks due today, including archived tasks.

    ClickUp's team filtered tasks endpoint accepts `archived` the same way the
    list Get Tasks endpoint documents it. Non-archived and archived results are
    fetched separately and merged.
    """
    today_start_ms = int(datetime.combine(date.today(), datetime.min.time()).timestamp() * 1000)
    today_end_ms = int(datetime.combine(date.today(), datetime.max.time()).timestamp() * 1000)

    tasks_by_id = {}

    for archived in (False, True):
        for task in _get_open_tasks(archived=archived):
            if is_due_today(task, today_start_ms, today_end_ms):
                tasks_by_id[task["id"]] = task

    return list(tasks_by_id.values())


def _get_open_tasks(*, archived: bool):
    tasks = []
    page = 0

    while True:
        res = http_client.get(
            endpoint=f"team/{TEAM_ID}/task",
            params={
                "page": page,
                "subtasks": "true",
                "include_closed": "false",
                "archived": "true" if archived else "false",
            }
        )
        tasks += res.data["tasks"]

        if res.data["last_page"]:
            break

        page += 1

    return [task for task in tasks if is_open(task)]


def get_task(task_id: str):
    res = http_client.get(
        endpoint=f"task/{task_id}",
        params={
            "include_subtasks": "true",
        }
    )

    return res.data


def task_not_found(error: Exception) -> bool:
    return isinstance(error, RequestException) and error.status == 404


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


def is_open(task: dict) -> bool:
    status = task.get("status")

    if isinstance(status, dict):
        status_type = str(status.get("type", "")).lower()
        status_name = str(status.get("status", "")).lower()
        return status_type not in {"closed", "done"} and status_name not in {
            "complete", "completed", "closed", "done"
        }

    return str(status or "").lower() not in {"complete", "completed", "closed", "done"}


def is_due_today(task: dict, today_start_ms: int, today_end_ms: int) -> bool:
    due_date = task.get("due_date")

    if due_date in (None, ""):
        return False

    due_date_ms = int(due_date)
    return today_start_ms <= due_date_ms <= today_end_ms


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
