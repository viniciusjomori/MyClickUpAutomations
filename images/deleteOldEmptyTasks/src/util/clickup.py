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


def get_tasks_created_before(created_before: datetime):
    tasks = []
    page = 0
    created_before_ms = int(created_before.timestamp() * 1000)

    while True:
        res = http_client.get(
            endpoint=f"team/{TEAM_ID}/task",
            params={
                "page": page,
                "subtasks": "true",
                "include_closed": "true",
                "date_created_lt": created_before_ms,
            }
        )
        tasks += res.data["tasks"]

        if res.data["last_page"]:
            break

        page += 1

    return [
        task for task in tasks
        if get_date_created_ms(task) is not None
        and get_date_created_ms(task) < created_before_ms
    ]


def get_task(task_id: str):
    res = http_client.get(
        endpoint=f"task/{task_id}",
        params={
            "include_subtasks": "true",
        }
    )

    return res.data


def get_date_created_ms(task: dict):
    date_created = task.get("date_created")

    if date_created in (None, ""):
        return None

    return int(date_created)


def has_comments(task_id: str) -> bool:
    res = http_client.get(endpoint=f"task/{task_id}/comment")
    return len(res.data.get("comments", [])) > 0


def delete_task(task_id: str):
    http_client.delete(endpoint=f"task/{task_id}")
