import logging
import time

from util import clickup

logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] [%(asctime)s] [%(name)s] %(message)s",
    encoding="utf-8",
    force=True
)

LOGGER = logging.getLogger(__name__)

def normalize_rules(event):
    rules = event.get("tags", [])

    if not isinstance(rules, list):
        raise ValueError("tags must be a list")

    normalized = []

    for rule in rules:
        tag = rule["tag"]
        delay_minutes = int(rule["delayMinutes"])

        if delay_minutes <= 0:
            raise ValueError("delayMinutes must be greater than zero")

        normalized.append({
            "tag": tag,
            "delay_ms": delay_minutes * 60 * 1000,
        })

    return normalized


def get_candidate_tasks(task_list_id: str, rules: list[dict], now_ms: int):
    candidates = {}

    for rule in rules:
        date_updated_lt_ms = now_ms - rule["delay_ms"] + 1
        tasks = clickup.get_tasks_by_tag(
            list_id=task_list_id,
            tag=rule["tag"],
            date_updated_lt_ms=date_updated_lt_ms
        )

        for task in tasks:
            candidates[task["id"]] = task

    return candidates.values()


def get_expired_tags(task: dict, rules: list[dict], now_ms: int):
    task_updated_ms = clickup.get_date_updated_ms(task)

    if task_updated_ms is None:
        return []

    task_tags = clickup.get_tag_names(task)

    return [
        rule["tag"]
        for rule in rules
        if rule["tag"] in task_tags
        and task_updated_ms <= now_ms - rule["delay_ms"]
    ]


def handler(event, context):
    rules = normalize_rules(event)
    now_ms = int(time.time() * 1000)
    removed_tags = 0

    for space in clickup.get_spaces():
        LOGGER.info("[SPACE] %s", space["name"])

        for task_list in clickup.get_lists(space["id"]):
            LOGGER.info("[LIST] %s", task_list["name"])

            tasks = get_candidate_tasks(
                task_list_id=task_list["id"],
                rules=rules,
                now_ms=now_ms
            )

            for task in tasks:
                for tag in get_expired_tags(task, rules, now_ms):
                    LOGGER.info("[TASK] removing tag=%s from %s", tag, task["id"])
                    clickup.remove_task_tag(task["id"], tag)
                    removed_tags += 1

    result = {
        "tags_removed": removed_tags,
        "message": f"Removed {removed_tags} reminder tags"
    }

    LOGGER.info("[RESULT] %s", result)

    return result
