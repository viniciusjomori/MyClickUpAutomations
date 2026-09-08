import os
import json
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import boto3

TABLE_NAME = os.getenv("ANTI_PROCASTINATION_TABLE_NAME")
STREAK_TASK_ID = "__anti_procastination_streak__"

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(TABLE_NAME)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_all_tasks() -> list[dict]:
    items = []
    response = table.scan()
    items.extend(response.get("Items", []))

    while "LastEvaluatedKey" in response:
        response = table.scan(ExclusiveStartKey=response["LastEvaluatedKey"])
        items.extend(response.get("Items", []))

    return [
        normalize_task(item) for item in items
        if not str(item.get("task_id", "")).startswith("__")
    ]


def get_task(task_id: str) -> dict | None:
    res = table.get_item(Key={"task_id": str(task_id)})
    item = res.get("Item")
    if not item:
        return None
    return normalize_task(item)


def normalize_task(item: dict) -> dict:
    return {
        **item,
        "strike_qnt": to_int(item.get("strike_qnt", 0)),
    }


def to_int(value) -> int:
    if value in (None, ""):
        return 0
    if isinstance(value, Decimal):
        return int(value)
    return int(value)


def record_success_day(reference_date: date) -> int:
    current_date = reference_date.isoformat()
    previous_date = (reference_date - timedelta(days=1)).isoformat()
    streak = get_streak()
    last_success_date = streak.get("last_success_date")

    if last_success_date == current_date:
        current_streak = int(streak.get("current_streak", 0))
    elif last_success_date == previous_date:
        current_streak = int(streak.get("current_streak", 0)) + 1
    else:
        current_streak = 1

    table.update_item(
        Key={"task_id": STREAK_TASK_ID},
        UpdateExpression=(
            "SET current_streak = :current_streak, "
            "last_success_date = :last_success_date, updated_at = :updated_at"
        ),
        ExpressionAttributeValues={
            ":current_streak": current_streak,
            ":last_success_date": current_date,
            ":updated_at": now_iso(),
        },
    )

    return current_streak


def reset_success_streak() -> None:
    table.update_item(
        Key={"task_id": STREAK_TASK_ID},
        UpdateExpression="SET current_streak = :current_streak, updated_at = :updated_at",
        ExpressionAttributeValues={
            ":current_streak": 0,
            ":updated_at": now_iso(),
        },
    )


def get_streak() -> dict:
    res = table.get_item(Key={"task_id": STREAK_TASK_ID})
    return res.get("Item", {})


def save_new_candidate(task: dict) -> dict:
    timestamp = now_iso()
    item = {
        "task_id": str(task["id"]),
        "task_name": task.get("name", ""),
        "task_url": task.get("url", ""),
        "space_id": get_space_id(task),
        "current_status": get_status_name(task),
        "current_status_type": get_status_type(task),
        "priority": get_priority_name(task),
        "strike_qnt": 0,
        "first_seen_at": timestamp,
        "last_seen_at": timestamp,
        "last_checked_at": timestamp,
        "task_snapshot_json": json.dumps(task, default=str),
    }
    table.put_item(Item=item)
    return normalize_task(item)


def get_priority_name(task: dict) -> str:
    priority = task.get("priority")

    if not priority:
        return "none"

    if isinstance(priority, dict):
        priority_name = str(priority.get("priority", "")).strip().lower()
        if priority_name in {"urgent", "high", "normal", "low"}:
            return priority_name

        priority_id = str(priority.get("id", "")).strip()
        return {
            "1": "urgent",
            "2": "high",
            "3": "normal",
            "4": "low",
        }.get(priority_id, "none")

    priority_value = str(priority).strip().lower()
    if priority_value in {"urgent", "high", "normal", "low"}:
        return priority_value

    return {
        "1": "urgent",
        "2": "high",
        "3": "normal",
        "4": "low",
    }.get(priority_value, "none")


def increment_strike(task_id: str) -> int:
    res = table.update_item(
        Key={"task_id": str(task_id)},
        UpdateExpression=(
            "SET strike_qnt = if_not_exists(strike_qnt, :zero) + :inc, "
            "last_seen_at = :last_seen_at, last_checked_at = :last_checked_at"
        ),
        ExpressionAttributeValues={
            ":zero": 0,
            ":inc": 1,
            ":last_seen_at": now_iso(),
            ":last_checked_at": now_iso(),
        },
        ReturnValues="UPDATED_NEW",
    )
    return to_int(res["Attributes"]["strike_qnt"])


def save_current_status(task_id: str, task: dict, strike_qnt: int | None = None) -> None:
    update_expression = (
        "SET task_name = :task_name, task_url = :task_url, "
        "space_id = :space_id, "
        "current_status = :current_status, current_status_type = :current_status_type, "
        "priority = :priority, "
        "last_checked_at = :last_checked_at"
    )
    values = {
        ":task_name": task.get("name", ""),
        ":task_url": task.get("url", ""),
        ":space_id": get_space_id(task),
        ":current_status": get_status_name(task),
        ":current_status_type": get_status_type(task),
        ":priority": get_priority_name(task),
        ":last_checked_at": now_iso(),
    }

    if strike_qnt is not None:
        update_expression += ", strike_qnt = :strike_qnt"
        values[":strike_qnt"] = int(strike_qnt)

    table.update_item(
        Key={"task_id": str(task_id)},
        UpdateExpression=update_expression,
        ExpressionAttributeValues=values,
    )


def delete_task(task_id: str) -> None:
    table.delete_item(Key={"task_id": str(task_id)})


def mark_email_sent(task_id: str) -> None:
    table.update_item(
        Key={"task_id": str(task_id)},
        UpdateExpression="SET last_email_sent_at = :last_email_sent_at",
        ExpressionAttributeValues={":last_email_sent_at": now_iso()},
    )


def get_status_name(task: dict) -> str:
    status = task.get("status")

    if isinstance(status, dict):
        return str(status.get("status", ""))

    return str(status or "")


def get_space_id(task: dict) -> str | None:
    space = task.get("space")

    if isinstance(space, dict):
        space_id = space.get("id")
        if space_id not in (None, ""):
            return str(space_id)

    space_id = task.get("space_id")
    if space_id not in (None, ""):
        return str(space_id)

    return None


def get_status_type(task: dict) -> str:
    status = task.get("status")

    if isinstance(status, dict):
        return str(status.get("type", ""))

    return ""
