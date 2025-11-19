from datetime import date, timedelta

from apps.server.core.morning_brief import Task, select_morning_brief_tasks, FLOW_TOP_TODAY_LABEL


def make_task(
    id: str,
    content: str,
    priority: int = 1,
    due_date=None,
    labels=None,
    completed=False,
):
    return Task(
        id=id,
        content=content,
        priority=priority,
        due_date=due_date,
        labels=labels or [],
        completed=completed,
    )


def test_selection_groups_carryover_overdue_today_and_suggested():
    today = date.today()
    yesterday = today - timedelta(days=1)

    tasks = [
        # Carryover (has flow_top_today label)
        make_task(
            "1", "Carryover P1", priority=1, due_date=yesterday, labels=[FLOW_TOP_TODAY_LABEL]
        ),
        make_task("2", "Carryover P2", priority=2, labels=[FLOW_TOP_TODAY_LABEL]),
        # Overdue P1/P2
        make_task("3", "Overdue P1", priority=1, due_date=yesterday),
        make_task("4", "Overdue P2", priority=2, due_date=yesterday),
        # Today P1
        make_task("5", "Today P1-A", priority=1, due_date=today),
        make_task("6", "Today P1-B", priority=1, due_date=today),
        # Undated P1
        make_task("7", "Undated P1-A", priority=1),
        make_task("8", "Undated P1-B", priority=1),
        make_task("9", "Undated P1-C", priority=1),
        # Noise
        make_task("10", "Completed P1", priority=1, due_date=today, completed=True),
        make_task("11", "P2 not overdue", priority=2, due_date=today),
        make_task("12", "P3 whatever", priority=3),
    ]

    selection = select_morning_brief_tasks(tasks, today=today, max_undated_p1=2)

    assert [t.id for t in selection["carryover"]] == ["1", "2"]
    assert {t.id for t in selection["overdue"]} == {"3", "4"}
    assert {t.id for t in selection["today_p1"]} == {"5", "6"}
    # Only 2 undated P1s due to cap
    assert len(selection["suggested_p1"]) == 2
    assert {t.id for t in selection["suggested_p1"]}.issubset({"7", "8", "9"})
