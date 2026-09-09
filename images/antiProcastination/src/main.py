import logging
import os
from datetime import date

from util import clickup, emailer, holiday, storage

logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] [%(asctime)s] [%(name)s] %(message)s",
    encoding="utf-8",
    force=True
)

LOGGER = logging.getLogger(__name__)

PRIORITY_RANK = {
    "urgent": 0,
    "high": 1,
    "normal": 2,
    "low": 3,
    "none": 4,
}


STRIKE_QNT_ENV_KEYS = {
    "urgent": "ANTI_PROCASTINATION_STRIKE_QNT_URGENT",
    "high": "ANTI_PROCASTINATION_STRIKE_QNT_HIGH",
    "normal": "ANTI_PROCASTINATION_STRIKE_QNT_NORMAL",
    "low": "ANTI_PROCASTINATION_STRIKE_QNT_LOW",
    "none": "ANTI_PROCASTINATION_STRIKE_QNT_NONE",
}


def get_strike_qnt_by_priority() -> dict[str, int]:
    strike_qnt_by_priority = {}

    for priority_name, env_key in STRIKE_QNT_ENV_KEYS.items():
        strike_qnt = int(os.getenv(env_key, "0"))
        if strike_qnt <= 0:
            raise ValueError(f"{env_key} must be greater than zero")
        strike_qnt_by_priority[priority_name] = strike_qnt

    return strike_qnt_by_priority


def get_required_strike_qnt(task: dict, strike_qnt_by_priority: dict[str, int]) -> int:
    priority_name = clickup.get_priority_name(task)
    return strike_qnt_by_priority.get(priority_name, strike_qnt_by_priority["none"])


def get_saved_required_strike_qnt(
    saved_task: dict,
    current_task: dict,
    strike_qnt_by_priority: dict[str, int],
) -> int:
    priority_name = saved_task.get("priority") or clickup.get_priority_name(current_task)
    return strike_qnt_by_priority.get(
        str(priority_name).lower(),
        strike_qnt_by_priority["none"],
    )


def get_workday_only_space_ids() -> set[str]:
    raw_space_ids = os.getenv("ANTI_PROCASTINATION_WORKDAY_ONLY_SPACE_IDS", "")
    return {
        space_id.strip()
        for space_id in raw_space_ids.split(",")
        if space_id.strip()
    }


def is_workday(reference_date: date, has_workday_only_spaces: bool) -> bool:
    if not has_workday_only_spaces:
        return True

    if reference_date.weekday() >= 5:
        return False

    return not holiday.is_holiday(reference_date)


def should_skip_space(
    space_id: str | None,
    workday_only_space_ids: set[str],
    today_is_workday: bool
) -> bool:
    if space_id not in workday_only_space_ids:
        return False

    return not today_is_workday


def is_complete(task: dict) -> bool:
    return not clickup.is_open(task)


def should_send_advice(strike_qnt: int, required_strike_qnt: int) -> bool:
    return strike_qnt >= required_strike_qnt


def sort_by_criticality(tasks: list[dict]) -> list[dict]:
    return sorted(
        tasks,
        key=lambda task: (
            PRIORITY_RANK.get(str(task.get("priority", "none")).lower(), PRIORITY_RANK["none"]),
            -int(task.get("strike_qnt", 0)),
        ),
    )


def build_email_task(saved_task: dict, current_task: dict) -> dict:
    task_id = saved_task["task_id"]
    parent_task = get_parent_task(current_task)
    space_id = clickup.get_space_id(current_task)

    return {
        **saved_task,
        "task_name": current_task.get("name", saved_task.get("task_name", task_id)),
        "task_url": current_task.get("url", saved_task.get("task_url", "")),
        "current_status": storage.get_status_name(current_task),
        "due_date": current_task.get("due_date", ""),
        "space_name": clickup.get_space_name(space_id),
        "space_id": space_id,
        "list_name": get_list_name(current_task),
        "parent_task_name": parent_task.get("name", "") if parent_task else "",
        "parent_task_url": parent_task.get("url", "") if parent_task else "",
        "priority": clickup.get_priority_name(current_task),
        "time_estimate": current_task.get("time_estimate", ""),
        "strike_qnt": saved_task.get("strike_qnt", 0),
        "required_strike_qnt": saved_task.get("required_strike_qnt", ""),
    }


def get_list_name(task: dict) -> str:
    task_list = task.get("list")

    if isinstance(task_list, dict):
        return str(task_list.get("name", ""))

    return ""


def get_parent_task(task: dict) -> dict | None:
    parent_task_id = clickup.get_parent_task_id(task)

    if not parent_task_id:
        return None

    try:
        return clickup.get_task(parent_task_id)
    except Exception:
        LOGGER.exception("[TASK] failed to get parent task=%s", parent_task_id)
        return None


def handler(event, context):
    strike_qnt_by_priority = get_strike_qnt_by_priority()
    workday_only_space_ids = get_workday_only_space_ids()
    today_is_workday = is_workday(date.today(), len(workday_only_space_ids) > 0)
    totals = {
        "candidate_tasks_saved": 0,
        "candidate_tasks_skipped_non_workday_space": 0,
        "candidate_tasks_already_saved": 0,
        "saved_tasks_checked": 0,
        "saved_tasks_skipped_non_workday_space": 0,
        "strikes_incremented": 0,
        "status_updates_saved": 0,
        "emails_sent": 0,
        "emails_skipped_incomplete_config": 0,
        "victory_tasks_completed": 0,
        "victory_streak_days": 0,
        "tasks_deleted_missing": 0,
        "tasks_deleted_completed": 0,
    }
    tasks_to_advise = []
    completed_procrastinated_tasks = []
    existing_task_ids_before_run = {
        saved_task["task_id"] for saved_task in storage.get_all_tasks()
    }

    for task in clickup.get_tasks():
        task_id = str(task["id"])

        if should_skip_space(clickup.get_space_id(task), workday_only_space_ids, today_is_workday):
            totals["candidate_tasks_skipped_non_workday_space"] += 1
            continue

        if task_id in existing_task_ids_before_run:
            totals["candidate_tasks_already_saved"] += 1
            continue

        storage.save_new_candidate(task)
        totals["candidate_tasks_saved"] += 1
        LOGGER.info("[TASK] saved candidate task=%s strike_qnt=0", task_id)

    for saved_task in storage.get_all_tasks():
        task_id = saved_task["task_id"]
        totals["saved_tasks_checked"] += 1

        try:
            current_task = clickup.get_task(task_id)
        except Exception as error:
            if clickup.task_not_found(error):
                storage.delete_task(task_id)
                totals["tasks_deleted_missing"] += 1
                LOGGER.info("[TASK] deleted missing task=%s from dynamodb", task_id)
                continue

            LOGGER.exception("[TASK] failed to get current status task=%s", task_id)
            continue

        if is_complete(current_task):
            required_strike_qnt = get_saved_required_strike_qnt(
                saved_task,
                current_task,
                strike_qnt_by_priority,
            )
            strike_qnt = int(saved_task.get("strike_qnt", 0))
            if should_send_advice(strike_qnt, required_strike_qnt):
                completed_procrastinated_tasks.append(build_email_task({
                    **saved_task,
                    "strike_qnt": strike_qnt,
                    "required_strike_qnt": required_strike_qnt,
                }, current_task))
                totals["victory_tasks_completed"] += 1

            storage.delete_task(task_id)
            totals["tasks_deleted_completed"] += 1
            LOGGER.info("[TASK] deleted completed task=%s from dynamodb", task_id)
            continue

        if should_skip_space(clickup.get_space_id(current_task), workday_only_space_ids, today_is_workday):
            totals["saved_tasks_skipped_non_workday_space"] += 1
            continue

        required_strike_qnt = get_required_strike_qnt(current_task, strike_qnt_by_priority)
        strike_qnt = int(saved_task.get("strike_qnt", 0))

        # New tasks saved in this run stay at 0. Already-tracked tasks get +1.
        if task_id in existing_task_ids_before_run:
            strike_qnt = storage.increment_strike(task_id)
            totals["strikes_incremented"] += 1

        storage.save_current_status(task_id, current_task, strike_qnt=strike_qnt)
        totals["status_updates_saved"] += 1

        if should_send_advice(strike_qnt, required_strike_qnt):
            tasks_to_advise.append(build_email_task({
                **saved_task,
                "strike_qnt": strike_qnt,
                "required_strike_qnt": required_strike_qnt,
            }, current_task))

    tasks_to_advise = sort_by_criticality(tasks_to_advise)
    completed_procrastinated_tasks = sort_by_criticality(completed_procrastinated_tasks)

    streak_days = None
    if completed_procrastinated_tasks:
        streak_days = storage.record_victory_day(date.today())
        totals["victory_streak_days"] = streak_days

    if completed_procrastinated_tasks or tasks_to_advise:
        LOGGER.info(
            "[EMAIL] sending report victories=%s pending=%s streak_days=%s",
            len(completed_procrastinated_tasks),
            len(tasks_to_advise),
            streak_days or 0,
        )
        email_sent = emailer.send_report(
            completed_tasks=completed_procrastinated_tasks,
            pending_tasks=tasks_to_advise,
            streak_days=streak_days,
        )
        if email_sent:
            for task in tasks_to_advise:
                storage.mark_email_sent(task["task_id"])
            totals["emails_sent"] = 1
        else:
            totals["emails_skipped_incomplete_config"] = 1

    LOGGER.info("[RESULT] %s", totals)
    return totals
