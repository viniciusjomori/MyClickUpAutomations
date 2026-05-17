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


def get_spaces(archived: bool = False):
    res = http_client.get(
        endpoint=f"team/{TEAM_ID}/space",
        params={"archived": "true" if archived else "false"}
    )

    return res.data["spaces"]


def get_lists(space_id: str, archived: bool = False):
    res = http_client.get(
        endpoint=f"space/{space_id}/list",
        params={"archived": "true" if archived else "false"}
    )

    return res.data["lists"]


def get_tasks(list_id: str, statuses: list[str]):
    tasks = []
    page = 0

    while True:
        res = http_client.get(
            endpoint=f"list/{list_id}/task",
            params={
                "page": page,
                "subtasks": "true",
                "include_closed": "false",
                "statuses[]": statuses,
            }
        )
        tasks += res.data["tasks"]

        if res.data["last_page"]:
            break

        page += 1

    return tasks


def get_task(task_id: str):
    res = http_client.get(
        endpoint=f"task/{task_id}",
        params={
            "include_subtasks": "true",
        }
    )

    return res.data


def create_subtask(
    list_id: str,
    parent_task_id: str,
    name: str,
    priority: int | None = None,
    due_date: datetime | None = None,
    status: str | None = None
):
    data = {
        "name": name,
        "parent": parent_task_id,
    }

    if priority is not None:
        data["priority"] = str(priority)

    if due_date is not None:
        data["due_date"] = int(due_date.timestamp() * 1000)

    if status is not None:
        data["status"] = status

    http_client.post(
        endpoint=f"list/{list_id}/task",
        data=data
    )
