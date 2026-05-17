import logging

logging.basicConfig(
    level=logging.DEBUG,
    format="[%(levelname)s] [%(asctime)s] [%(name)s] %(message)s",
    encoding="utf-8",
    force=True
)
LOGGER = logging.getLogger(__name__)

from datetime import date, datetime
from util import clickup

def handler(event, context):
    today = datetime.combine(date.today(), datetime.min.time())
    tasks = []

    spaces = clickup.get_spaces()
    for space in spaces:
        LOGGER.info(f"[SPACE] {space['name']}")

        lists = clickup.get_lists(space['id'])
        
        for list in lists:
            LOGGER.info(f"[LIST] {list['name']}")

            tasks += clickup.get_tasks(
                list_id=list['id'],
                due_date_lt=today
            )
    
    for task in tasks:
        LOGGER.info(f"[TASK] {task['id']}")
        clickup.update_task(task['id'], due_date=today)

    return { 'tasks': len(tasks) }
