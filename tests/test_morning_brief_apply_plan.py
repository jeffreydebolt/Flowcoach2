from datetime import date
from unittest.mock import MagicMock

from apps.server.core.morning_brief import FLOW_TOP_TODAY_LABEL, apply_morning_brief_plan


def test_apply_plan_clears_old_labels_and_updates_only_included_tasks():
    todoist_client = MagicMock()

    # old "today" tasks
    todoist_client.get_open_flow_top_today_tasks.return_value = [
        {"id": "1"},
        {"id": "2"},
    ]

    plan = [
        {"id": "3", "include": True, "priority": 1, "time": "09:00"},
        {"id": "4", "include": False, "priority": 1, "time": None},
    ]

    today = date(2025, 11, 18)

    apply_morning_brief_plan(user_id="U123", plan=plan, todoist_client=todoist_client, today=today)

    # Clear label called for each old today task
    assert todoist_client.clear_label_from_task.call_count == 2
    cleared_ids = {
        args[0] for args, _ in [c for c in todoist_client.clear_label_from_task.call_args_list]
    }
    assert cleared_ids == {"1", "2"}

    # Only included task gets updated
    todoist_client.update_task.assert_called_once()
    (task_id,), kwargs = todoist_client.update_task.call_args
    assert task_id == "3"
    payload = kwargs["payload"]
    assert payload["priority"] == 1
    assert payload["due"]["date"] == today.isoformat()
    assert payload["due"]["time"] == "09:00"
    assert FLOW_TOP_TODAY_LABEL in payload["labels"]
