import os
from urllib.parse import quote

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


def get_tasks_by_tag(
    list_id: str,
    tag: str,
    date_updated_lt_ms: int
):
    tasks = []
    page = 0

    while True:
        res = http_client.get(
            endpoint=f"list/{list_id}/task",
            params={
                "page": page,
                "subtasks": "true",
                "include_closed": "false",
                "date_updated_lt": date_updated_lt_ms,
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
        and get_date_updated_ms(task) is not None
        and get_date_updated_ms(task) < date_updated_lt_ms
    ]


def has_tag(task: dict, tag: str):
    return tag in get_tag_names(task)


def get_tag_names(task: dict):
    return {
        task_tag.get("name") if isinstance(task_tag, dict) else task_tag
        for task_tag in task.get("tags", [])
    }


def get_date_updated_ms(task: dict):
    date_updated = task.get("date_updated")

    if date_updated in (None, ""):
        return None

    return int(date_updated)


def remove_task_tag(task_id: str, tag: str):
    http_client.delete(
        endpoint=f"task/{task_id}/tag/{quote(tag, safe='')}"
    )
