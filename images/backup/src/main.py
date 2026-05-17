import logging
from datetime import datetime
from util import clickup, s3

logging.basicConfig(
    level=logging.DEBUG,
    format="[%(levelname)s] [%(asctime)s] [%(name)s] %(message)s",
    encoding="utf-8",
    force=True
)
LOGGER = logging.getLogger(__name__)

def handler(event, context):
    list_qnt = 0
    task_qnt = 0

    spaces = clickup.get_spaces()

    for space in spaces:
        LOGGER.info(f"[SPACE] {space['name']}")
        lists = clickup.get_lists(space['id'])
        list_qnt += len(lists)

        for list in lists:
            LOGGER.info(f"[LIST] {list['name']}")
            tasks = clickup.get_tasks(
                list_id=list['id'],
            )
            task_qnt += len(tasks)
            LOGGER.info(f"[LIST] found {len(tasks)} tasks")
            list['tasks'] = tasks
        
        space['lists'] = lists
    
    now = datetime.now().strftime("%Y-%m-%d %Hh%M")
    LOGGER.info(f"[BACKUP] uploading snapshot backup {now}.json")
    s3.put_json("backups", f"backup {now}.json", spaces)

    return {
        "space_qnt": len(spaces),
        "list_qnt": list_qnt,
        "task_qnt": task_qnt
    }

