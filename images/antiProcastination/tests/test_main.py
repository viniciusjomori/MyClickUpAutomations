import importlib
import os
import sys
import types
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch


SRC_DIR = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC_DIR))


class _UnusedTable:
    def update_item(self, **kwargs):
        return {}


class _FakeDynamoResource:
    def Table(self, table_name):
        return _UnusedTable()


sys.modules.setdefault(
    "boto3",
    types.SimpleNamespace(resource=lambda service: _FakeDynamoResource()),
)

main = importlib.import_module("main")
emailer = importlib.import_module("util.emailer")
storage = importlib.import_module("util.storage")


class AntiProcrastinationReportTest(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {
            "ANTI_PROCASTINATION_STRIKE_QNT_URGENT": "1",
            "ANTI_PROCASTINATION_STRIKE_QNT_HIGH": "2",
            "ANTI_PROCASTINATION_STRIKE_QNT_NORMAL": "3",
            "ANTI_PROCASTINATION_STRIKE_QNT_LOW": "4",
            "ANTI_PROCASTINATION_STRIKE_QNT_NONE": "5",
            "ANTI_PROCASTINATION_WORKDAY_ONLY_SPACE_IDS": "",
        })
        self.env.start()

    def tearDown(self):
        self.env.stop()

    def test_sorts_by_priority_then_strike_quantity(self):
        tasks = [
            {"task_id": "normal", "priority": "normal", "strike_qnt": 20},
            {"task_id": "urgent-low", "priority": "urgent", "strike_qnt": 2},
            {"task_id": "urgent-high", "priority": "urgent", "strike_qnt": 5},
            {"task_id": "high", "priority": "high", "strike_qnt": 10},
        ]

        sorted_tasks = main.sort_by_criticality(tasks)

        self.assertEqual(
            [task["task_id"] for task in sorted_tasks],
            ["urgent-high", "urgent-low", "high", "normal"],
        )

    def test_completed_procrastinated_task_creates_combined_victory_report(self):
        saved_tasks = [
            {
                "task_id": "completed",
                "task_name": "Completed task",
                "priority": "normal",
                "strike_qnt": 3,
            },
            {
                "task_id": "pending",
                "task_name": "Pending task",
                "priority": "urgent",
                "strike_qnt": 1,
            },
        ]
        current_tasks = {
            "completed": {
                "id": "completed",
                "name": "Completed task",
                "status": {"status": "complete", "type": "closed"},
                "priority": {"priority": "normal"},
            },
            "pending": {
                "id": "pending",
                "name": "Pending task",
                "status": {"status": "in progress", "type": "custom"},
                "priority": {"priority": "urgent"},
            },
        }

        with (
            patch.object(main.clickup, "get_tasks", return_value=[]),
            patch.object(main.clickup, "get_task", side_effect=lambda task_id: current_tasks[task_id]),
            patch.object(main.clickup, "get_space_name", return_value=""),
            patch.object(main.storage, "get_all_tasks", return_value=saved_tasks),
            patch.object(main.storage, "delete_task") as delete_task,
            patch.object(main.storage, "increment_strike", return_value=2),
            patch.object(main.storage, "save_current_status"),
            patch.object(main.storage, "record_victory_day", return_value=2) as record_victory_day,
            patch.object(main.storage, "mark_email_sent"),
            patch.object(main.emailer, "send_report", return_value=True) as send_report,
        ):
            result = main.handler({}, None)

        delete_task.assert_called_once_with("completed")
        record_victory_day.assert_called_once()
        report = send_report.call_args.kwargs
        self.assertEqual(report["streak_days"], 2)
        self.assertEqual([task["task_id"] for task in report["completed_tasks"]], ["completed"])
        self.assertEqual([task["task_id"] for task in report["pending_tasks"]], ["pending"])
        self.assertEqual(result["victory_tasks_completed"], 1)
        self.assertEqual(result["victory_streak_days"], 2)

    def test_report_contains_victory_and_pending_sections(self):
        completed = [{"task_id": "done", "task_name": "Done", "strike_qnt": 3}]
        pending = [{"task_id": "todo", "task_name": "Todo", "strike_qnt": 5}]

        text = emailer.render_report_text(completed, pending, streak_days=2)
        html = emailer.render_report_html(completed, pending, streak_days=2)

        self.assertIn("Victory day!", text)
        self.assertIn("Tasks to solve", text)
        self.assertIn("2 days", text)
        self.assertIn("Completed victories", html)
        self.assertIn("Tasks to solve", html)

    def test_victory_streak_increments_only_once_per_day_and_resets_after_gap(self):
        cases = [
            (
                {"last_victory_date": "2026-09-08", "current_victory_streak": 3},
                date(2026, 9, 8),
                3,
            ),
            (
                {"last_victory_date": "2026-09-07", "current_victory_streak": 3},
                date(2026, 9, 8),
                4,
            ),
            (
                {"last_victory_date": "2026-09-05", "current_victory_streak": 3},
                date(2026, 9, 8),
                1,
            ),
        ]

        for stored_streak, reference_date, expected in cases:
            with self.subTest(stored_streak=stored_streak):
                with (
                    patch.object(storage, "get_victory_streak", return_value=stored_streak),
                    patch.object(storage.table, "update_item"),
                ):
                    self.assertEqual(storage.record_victory_day(reference_date), expected)


if __name__ == "__main__":
    unittest.main()
