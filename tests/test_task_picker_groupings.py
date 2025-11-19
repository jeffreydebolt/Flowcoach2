from datetime import date, timedelta

from apps.server.core.morning_brief import Task, group_tasks_for_picker


def make_task(id, content, priority, due_date=None, completed=False):
    return Task(
        id=id,
        content=content,
        priority=priority,
        due_date=due_date,
        labels=[],
        completed=completed,
    )


def test_picker_groups_by_priority_and_skips_completed():
    today = date.today()
    yesterday = today - timedelta(days=1)

    tasks = [
        make_task("1", "P1 overdue", priority=1, due_date=yesterday),
        make_task("2", "P1 today", priority=1, due_date=today),
        make_task("3", "P2 undated", priority=2),
        make_task("4", "P3 today", priority=3, due_date=today),
        make_task("5", "Completed P1", priority=1, due_date=today, completed=True),
    ]

    groups = group_tasks_for_picker(tasks)

    assert [t.id for t in groups["p1"]] == ["1", "2"]
    assert [t.id for t in groups["p2"]] == ["3"]
    assert [t.id for t in groups["p3"]] == ["4"]
