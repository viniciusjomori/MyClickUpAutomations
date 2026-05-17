import os
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

def get_spaces():
    res = http_client.get(f"team/{TEAM_ID}/space")
    return res.data['spaces']

def get_lists(space_id):
    res = http_client.get(f"space/{space_id}/list")
    return res.data['lists']

def get_tasks(list_id):
    tasks = []
    page = 0
    while True:
        res = http_client.get(
            endpoint=f"list/{list_id}/task",
            params={
                'page':page,
                'substasks': True,
            }
        )
        tasks += res.data['tasks']

        if res.data['last_page']:
            break

        page += 1

    return tasks