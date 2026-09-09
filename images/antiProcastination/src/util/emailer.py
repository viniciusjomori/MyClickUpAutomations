import logging
import os
import smtplib
from datetime import datetime
from email.message import EmailMessage
from email.utils import formataddr
from html import escape

LOGGER = logging.getLogger(__name__)

STREAK_LEVELS = [
    {"min": 1, "max": 2, "name": "Spark", "fires": 1, "next_target": 3, "next_name": "Flame"},
    {"min": 3, "max": 6, "name": "Flame", "fires": 2, "next_target": 7, "next_name": "Blaze"},
    {"min": 7, "max": 13, "name": "Blaze", "fires": 3, "next_target": 14, "next_name": "Wildfire"},
    {"min": 14, "max": 29, "name": "Wildfire", "fires": 4, "next_target": 30, "next_name": "Legendary"},
    {"min": 30, "max": None, "name": "Legendary", "fires": 5, "next_target": None, "next_name": None},
]


def get_recipients() -> list[str]:
    return [
        recipient.strip()
        for recipient in os.getenv("SMTP_TO", "").split(",")
        if recipient.strip()
    ]


def is_configured() -> bool:
    return bool(
        os.getenv("SMTP_HOST")
        and os.getenv("SMTP_PORT")
        and os.getenv("SMTP_FROM")
        and get_recipients()
    )


def use_tls() -> bool:
    return os.getenv("SMTP_USE_TLS", "true").lower() in {"1", "true", "yes"}


def get_sender() -> str:
    name = os.getenv("SMTP_NAME", "").strip()
    address = os.getenv("SMTP_FROM", "").strip()

    if name:
        return formataddr((name, address))

    return address


def send_report(
    completed_tasks: list[dict],
    pending_tasks: list[dict],
    streak_days: int | None,
) -> bool:
    if not completed_tasks and not pending_tasks:
        return False

    if not is_configured():
        LOGGER.warning("[EMAIL] SMTP config incomplete, skipping report")
        return False

    message = EmailMessage()
    message["Subject"] = get_report_subject(completed_tasks, pending_tasks, streak_days)
    message["From"] = get_sender()
    message["To"] = ", ".join(get_recipients())
    message.set_content(render_report_text(completed_tasks, pending_tasks, streak_days))
    message.add_alternative(
        render_report_html(completed_tasks, pending_tasks, streak_days),
        subtype="html",
    )

    host = os.getenv("SMTP_HOST")
    port = int(os.getenv("SMTP_PORT", "587"))
    username = os.getenv("SMTP_USERNAME")
    password = os.getenv("SMTP_PASSWORD")

    with smtplib.SMTP(host, port, timeout=30) as smtp:
        if use_tls():
            smtp.starttls()
        if username and password:
            smtp.login(username, password)
        smtp.send_message(message)

    return True


def get_report_subject(
    completed_tasks: list[dict],
    pending_tasks: list[dict],
    streak_days: int | None,
) -> str:
    if completed_tasks:
        day_word = "day" if streak_days == 1 else "days"
        return (
            f"\U0001F525 Victory day: {len(completed_tasks)} completed, "
            f"{streak_days} {day_word} streak, {len(pending_tasks)} pending"
        )

    task_word = "task" if len(pending_tasks) == 1 else "tasks"
    return f"{len(pending_tasks)} {task_word} reached their strike threshold"


def render_report_text(
    completed_tasks: list[dict],
    pending_tasks: list[dict],
    streak_days: int | None,
) -> str:
    lines = ["AntiProcrastination report", ""]

    if completed_tasks:
        day_word = "day" if streak_days == 1 else "days"
        lines.extend([
            "Victory day!",
            f"You completed {len(completed_tasks)} procrastinated task(s).",
            f"Current victory streak: {streak_days} {day_word}",
            "",
            "Completed victories",
            "",
        ])
        lines.extend(render_task_text_rows(completed_tasks))

    if pending_tasks:
        lines.extend([
            "Tasks to solve",
            "Ordered by priority and strike quantity.",
            "",
        ])
        lines.extend(render_task_text_rows(pending_tasks))

    lines.append("This notification was generated automatically by AntiProcrastination.")
    return "\n".join(lines)


def render_task_text_rows(tasks: list[dict]) -> list[str]:
    lines = []
    for index, task in enumerate(tasks, start=1):
        lines.extend([
            f"Task {index}",
            f"Task: {task.get('task_name', task['task_id'])}",
            f"Status: {task.get('current_status', '')}",
            f"Due date: {format_timestamp_date(task.get('due_date', ''))}",
            f"Priority: {task.get('priority', '')}",
            f"Strikes: {format_strike_qnt(task.get('strike_qnt', ''))}",
            f"Strike threshold: {format_strike_qnt(task.get('required_strike_qnt', ''))}",
            f"URL: {task.get('task_url') or '(no url)'}",
            "",
        ])
    return lines


def render_report_html(
    completed_tasks: list[dict],
    pending_tasks: list[dict],
    streak_days: int | None,
) -> str:
    completed_section = ""
    if completed_tasks:
        completed_rows = "\n".join(
            render_task_html(index, task)
            for index, task in enumerate(completed_tasks, start=1)
        )
        completed_section = f"""
          <tr>
            <td style="padding: 28px 32px 10px;">
              {render_victory_summary_html(streak_days, len(completed_tasks))}
              <div style="font-size: 18px; font-weight: 700; color: #202124; margin: 28px 0 14px;">Completed victories</div>
              {completed_rows}
            </td>
          </tr>"""

    pending_section = ""
    if pending_tasks:
        pending_rows = "\n".join(
            render_task_html(index, task)
            for index, task in enumerate(pending_tasks, start=1)
        )
        pending_section = f"""
          <tr>
            <td style="padding: 28px 32px;">
              <div style="font-size: 18px; font-weight: 700; color: #202124; margin-bottom: 6px;">Tasks to solve</div>
              <div style="font-size: 13px; color: #7a7a7a; margin-bottom: 18px;">Ordered by priority and strike quantity.</div>
              {pending_rows}
            </td>
          </tr>"""

    title = "Victory day!" if completed_tasks else "Tasks need your attention"
    subtitle = (
        f"{len(completed_tasks)} procrastinated task(s) completed today."
        if completed_tasks
        else f"{len(pending_tasks)} task(s) reached their strike threshold."
    )

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>AntiProcrastination Report</title>
</head>
<body style="margin: 0; padding: 0; background-color: #f7f8fa; font-family: Arial, Helvetica, sans-serif; color: #242424;">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="background-color: #f7f8fa; padding: 32px 16px;">
    <tr>
      <td align="center">
        <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="max-width: 640px; background-color: #ffffff; border: 1px solid #e8e8e8; border-radius: 12px; overflow: hidden;">
          <tr>
            <td style="padding: 26px 32px; border-bottom: 1px solid #eeeeee;">
              <div style="font-size: 12px; font-weight: bold; text-transform: uppercase; letter-spacing: 1px; color: #7b68ee; margin-bottom: 8px;">AntiProcrastination</div>
              <div style="font-size: 24px; font-weight: 700; line-height: 1.3; color: #202020;">{title}</div>
              <div style="margin-top: 8px; font-size: 14px; line-height: 1.5; color: #7a7a7a;">{subtitle}</div>
            </td>
          </tr>
          {completed_section}
          {pending_section}
          <tr>
            <td style="padding: 18px 32px; background-color: #fafafa; border-top: 1px solid #eeeeee; font-size: 11px; color: #a0a0a0;">This notification was generated automatically by AntiProcrastination.</td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


def render_victory_summary_html(streak_days: int, completed_count: int) -> str:
    level = get_streak_level(streak_days)
    progress = get_streak_progress(streak_days)
    day_word = "day" if streak_days == 1 else "days"
    return f"""
              <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="border: 1px solid #e6e8eb; border-radius: 10px; background-color: #ffffff;">
                <tr>
                  <td align="center" style="padding: 26px 24px;">
                    <div style="font-size: 36px; line-height: 1.2; margin-bottom: 12px;">{render_fire_emojis(level)}</div>
                    <div style="font-size: 13px; font-weight: bold; color: #7b68ee; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px;">{level['name']} level</div>
                    <div style="font-size: 34px; line-height: 1; font-weight: 700; color: #202124; margin-bottom: 8px;">{streak_days}</div>
                    <div style="font-size: 15px; color: #7a7a7a; margin-bottom: 18px;">{day_word} victory streak · {completed_count} completed today</div>
                    {render_streak_progress_html(progress)}
                  </td>
                </tr>
              </table>"""


def get_streak_level(streak_days: int) -> dict:
    for level in STREAK_LEVELS:
        if level["max"] is None or streak_days <= level["max"]:
            return level

    return STREAK_LEVELS[-1]


def get_streak_progress(streak_days: int) -> dict:
    level = get_streak_level(streak_days)
    next_target = level["next_target"]

    if next_target is None:
        return {
            "max_level": True,
            "current": streak_days,
            "target": streak_days,
            "next_name": None,
            "percent": 100,
        }

    percent = min(100, max(0, int((streak_days / next_target) * 100)))
    return {
        "max_level": False,
        "current": streak_days,
        "target": next_target,
        "next_name": level["next_name"],
        "percent": percent,
    }


def render_streak_progress_html(progress: dict) -> str:
    if progress["max_level"]:
        return (
            '<div style="font-size: 13px; font-weight: bold; color: #7b68ee; '
            'text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px;">'
            "Max level reached</div>"
            '<div style="font-size: 14px; color: #7a7a7a;">'
            "Legendary status is active.</div>"
        )

    return f"""
                    <div style="width: 100%; max-width: 420px; text-align: left;">
                      <div style="font-size: 12px; font-weight: bold; color: #7b68ee; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px;">Next level</div>
                      <div style="font-size: 14px; color: #33363a; margin-bottom: 8px;">{progress['current']} / {progress['target']} days to {progress['next_name']}</div>
                      <div style="height: 10px; background-color: #eeeafd; border-radius: 999px; overflow: hidden;">
                        <div style="width: {progress['percent']}%; height: 10px; background-color: #7b68ee; border-radius: 999px;"></div>
                      </div>
                    </div>"""


def render_fire_emojis(level: dict) -> str:
    return " ".join(["&#128293;"] * int(level["fires"]))


def render_task_html(index: int, task: dict) -> str:
    task_name = escape(str(task.get("task_name", task["task_id"])))
    task_status = escape(str(task.get("current_status", "")))
    first_seen = escape(format_date(task.get("first_seen_at", "")))
    due_date = escape(format_timestamp_date(task.get("due_date", "")))
    space_name = escape(str(task.get("space_name") or task.get("space_id", "")))
    list_name = escape(str(task.get("list_name", "")))
    parent_task = render_parent_task_html(task)
    priority = escape(str(task.get("priority", "")))
    strikes = escape(format_strike_qnt(task.get("strike_qnt", "")))
    strike_threshold = escape(format_strike_qnt(task.get("required_strike_qnt", "")))
    time_estimate = escape(format_time_estimate(task.get("time_estimate", "")))
    task_url = escape(str(task.get("task_url") or "#"), quote=True)

    return f"""
              <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="border: 1px solid #e6e8eb; border-radius: 10px; background-color: #ffffff;">
                <tr>
                  <td style="padding: 22px 24px;">
                    <div style="font-size: 12px; color: #8b8f97; margin-bottom: 9px;">
                      <span style="font-weight: 600; color: #666b73;">{space_name}</span>
                      <span style="padding: 0 6px; color: #b6b8bd;">/</span>
                      <span>{list_name}</span>
                    </div>
                    <div style="font-size: 20px; line-height: 1.35; font-weight: 700; color: #202124; margin-bottom: 18px;">{task_name}</div>
                    <div style="margin-bottom: 22px;"><span style="display: inline-block; padding: 5px 9px; background-color: #f1efff; color: #5b48d6; border-radius: 5px; font-size: 11px; line-height: 1; font-weight: bold; text-transform: uppercase;">{task_status}</span></div>
                    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0">
                      <tr>
                        {render_detail_cell("Due date", due_date, "0 12px 20px 0")}
                        {render_detail_cell("Priority", priority.capitalize(), "0 0 20px 12px")}
                      </tr>
                      <tr>
                        {render_detail_cell("Strikes", strikes, "0 12px 20px 0")}
                        {render_detail_cell("Strike threshold", strike_threshold, "0 0 20px 12px")}
                      </tr>
                      <tr>
                        {render_detail_cell("First detected", first_seen, "0 12px 20px 0")}
                        {render_detail_cell("Time estimate", time_estimate, "0 0 20px 12px")}
                      </tr>
                      {render_parent_task_row(parent_task)}
                    </table>
                    <table role="presentation" cellspacing="0" cellpadding="0" border="0" style="margin-top: 2px;">
                      <tr>
                        <td bgcolor="#7b68ee" style="border-radius: 6px;">
                          <a href="{task_url}" target="_blank" style="display: inline-block; padding: 11px 17px; font-size: 13px; font-weight: bold; color: #ffffff; text-decoration: none;">Open in ClickUp</a>
                        </td>
                      </tr>
                    </table>
                  </td>
                </tr>
              </table>
              <div style="height: 18px; line-height: 18px;">&nbsp;</div>"""


def format_strike_qnt(value) -> str:
    if value in (None, ""):
        return ""

    try:
        strikes = int(value)
    except (TypeError, ValueError):
        return str(value)

    strike_word = "strike" if strikes == 1 else "strikes"
    return f"{strikes} {strike_word}"


def format_date(value: str) -> str:
    if not value:
        return ""

    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return str(value)

    return parsed.strftime("%d/%m/%Y")


def format_timestamp_date(value) -> str:
    if value in (None, ""):
        return ""

    try:
        timestamp_ms = int(value)
    except (TypeError, ValueError):
        return format_date(str(value))

    return datetime.fromtimestamp(timestamp_ms / 1000).strftime("%d/%m/%Y")


def format_time_estimate(value) -> str:
    if value in (None, ""):
        return ""

    try:
        total_minutes = int(value) // 1000 // 60
    except (TypeError, ValueError):
        return str(value)

    hours = total_minutes // 60
    minutes = total_minutes % 60
    return f"{hours:02d}h{minutes:02d}m"


def format_parent_task_text(task: dict) -> str:
    parent_task_name = task.get("parent_task_name", "")
    parent_task_url = task.get("parent_task_url", "")

    if parent_task_name and parent_task_url:
        return f"{parent_task_name} ({parent_task_url})"

    return parent_task_name or ""


def render_parent_task_html(task: dict) -> str:
    parent_task_name = escape(str(task.get("parent_task_name", "")))
    parent_task_url = escape(str(task.get("parent_task_url", "")), quote=True)

    if parent_task_name and parent_task_url:
        return (
            f'<a href="{parent_task_url}" target="_blank" '
            'style="color: #2563eb; text-decoration: none;">'
            f"{parent_task_name}</a>"
        )

    return parent_task_name


def render_detail_cell(label: str, value: str, padding: str) -> str:
    value = value or ""

    return f"""
                        <td width="50%" valign="top" style="padding: {padding};">
                          <div style="font-size: 11px; color: #9a9da3; margin-bottom: 5px;">{label}</div>
                          <div style="font-size: 14px; font-weight: 600; color: #33363a;">{value}</div>
                        </td>"""


def render_parent_task_row(value: str) -> str:
    if not value:
        return ""

    return f"""
                      <tr>
                        <td colspan="2" valign="top" style="padding: 0 0 20px;">
                          <div style="font-size: 11px; color: #9a9da3; margin-bottom: 5px;">Parent task</div>
                          <div style="font-size: 14px; font-weight: 600; color: #33363a;">{value}</div>
                        </td>
                      </tr>"""
