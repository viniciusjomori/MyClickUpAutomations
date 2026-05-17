import logging

LOGGER = logging.getLogger(__name__)

import os
from datetime import datetime


from .https import HttpClient

API_KEY = os.getenv("CLICKUP_API_KEY")
TEAM_ID = os.getenv("CLICKUP_TEAM_ID")

http_client = HttpClient(
    base='https://api.clickup.com/api/v2/',
    headers={
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": API_KEY
    },
    raises_exception=True
)

def get_spaces(archived=False):
    res = http_client.get(
        endpoint=f"team/{TEAM_ID}/space",
        params={ 'archived': 'true' if archived else 'false' }
    )

    return res.data['spaces']

def get_lists(space_id: str, archived=False):
    res = http_client.get(
        endpoint=f"space/{space_id}/list",
        params={'archived': 'true' if archived else 'false'}
    )
    
    return res.data['lists']

def get_tasks(list_id: str, due_date_lt: datetime):
    tasks = []
    page = 0
    
    while True:
        res = http_client.get(
            endpoint=f"list/{list_id}/task",
            params={
                'page': page,
                'subtasks': 'true'
            }
        )
        tasks += res.data['tasks']

        if res.data['last_page']:
            break
    
        page += 1

    seen_task_ids = set()
    expanded_tasks = []

    for task in tasks:
        expanded_tasks += get_task_family(task, seen_task_ids)

    return [
        task for task in expanded_tasks
        if is_due_date_before(task.get('due_date'), due_date_lt)
    ]

def get_task(task_id: str):
    res = http_client.get(
        endpoint=f"task/{task_id}",
        params={
            'subtasks': 'true'
        }
    )

    return res.data

def get_task_family(task: dict, seen_task_ids: set[str]):
    task_id = task['id']
    if task_id in seen_task_ids:
        return []

    seen_task_ids.add(task_id)

    detailed_task = get_task(task_id)
    task_family = [detailed_task]

    for subtask in detailed_task.get('subtasks', []):
        task_family += get_task_family(subtask, seen_task_ids)

    return task_family

def is_due_date_before(due_date, reference: datetime):
    if due_date in (None, ''):
        return False

    return int(due_date) < int(reference.timestamp() * 1000)

def update_task(task_id: str, due_date: datetime):
    due_date = int(due_date.timestamp() * 1000)
    http_client.put(
        endpoint=f"task/{task_id}",
        data={
            'due_date': due_date
        }
    )
