import os
from datetime import datetime

from .https import HttpClient

API_KEY = os.getenv("CLICKUP_API_KEY")
TEAM_ID = os.getenv("CLICKUP_TEAM_ID")

http_client = HttpClient(
    base="https://api.clickup.com/api/v2/",
    headers={
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": API_KEY
    },
    raises_exception=True
)


def get_spaces():
    res = http_client.get(f"team/{TEAM_ID}/space")
    return res.data["spaces"]


def get_lists(space_id):
    res = http_client.get(f"space/{space_id}/list")
    return res.data["lists"]


def get_tasks(
    list_id: str,
    tag: str,
    archived: bool,
    due_date_gte: datetime,
    due_date_lt: datetime
):
    tasks = []
    page = 0
    due_date_gte_ms = int(due_date_gte.timestamp() * 1000) - 1
    due_date_lt_ms = int(due_date_lt.timestamp() * 1000)

    while True:
        res = http_client.get(
            endpoint=f"list/{list_id}/task",
            params={
                "page": page,
                "subtasks": "true",
                "include_closed": "false",
                "archived": "true" if archived else "false",
                "due_date_gt": due_date_gte_ms,
                "due_date_lt": due_date_lt_ms,
                "tags[]": [tag],
            }
        )
        tasks += res.data["tasks"]

        if res.data["last_page"]:
            break

        page += 1

    return [
        task for task in tasks
        if has_tag(task, tag)
        and is_due_date_between(task.get("due_date"), due_date_gte, due_date_lt)
    ]


def has_tag(task: dict, tag: str):
    return any(
        (task_tag.get("name") if isinstance(task_tag, dict) else task_tag) == tag
        for task_tag in task.get("tags", [])
    )


def is_due_date_between(due_date, start: datetime, end: datetime):
    if due_date in (None, ""):
        return False

    due_date_ms = int(due_date)
    return int(start.timestamp() * 1000) <= due_date_ms < int(end.timestamp() * 1000)


def update_task_archived(task_id: str, archived: bool):
    http_client.put(
        endpoint=f"task/{task_id}",
        data={
            "archived": archived
        }
    )
