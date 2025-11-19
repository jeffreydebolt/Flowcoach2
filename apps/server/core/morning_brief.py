from dataclasses import dataclass
from datetime import date
from typing import List, Dict, Optional


FLOW_TOP_TODAY_LABEL = "flow_top_today"  # or "@flow_top_today" depending on how you store it


@dataclass
class Task:
    id: str
    content: str
    priority: int  # 1 (P1), 2 (P2), 3 (P3), etc.
    due_date: Optional[date]
    labels: List[str]
    completed: bool
    project: Optional[str] = None  # optional, for display


def select_morning_brief_tasks(
    tasks: List[Task],
    today: date,
    max_undated_p1: int = 15,  # Increased from 5 to show more tasks
) -> Dict[str, List[Task]]:
    """
    Split all tasks into four lists for the Morning Brief modal:

    - carryover: open tasks with FLOW_TOP_TODAY_LABEL
    - overdue: open P1/P2 tasks with due_date < today (and NO FLOW_TOP_TODAY_LABEL)
    - today_p1: open P1 tasks with due_date == today (and NO FLOW_TOP_TODAY_LABEL)
    - suggested_p1: open P1 tasks with no due_date and NO FLOW_TOP_TODAY_LABEL,
                    limited to max_undated_p1

    Returns:
        {
          "carryover": [...],
          "overdue": [...],
          "today_p1": [...],
          "suggested_p1": [...],
        }
    """
    carryover = []
    overdue = []
    today_p1 = []
    undated_p1_candidates = []

    for t in tasks:
        if t.completed:
            continue

        has_label = FLOW_TOP_TODAY_LABEL in t.labels

        if has_label:
            carryover.append(t)
            continue

        if t.due_date is not None:
            if t.priority in (1, 2) and t.due_date < today:
                overdue.append(t)
                continue
            if t.priority == 1 and t.due_date == today:
                today_p1.append(t)
                continue
        else:
            # undated
            if t.priority == 1:
                undated_p1_candidates.append(t)

    # Sort: carryover we leave as-is (Todoist order)
    overdue.sort(key=lambda t: (t.due_date or today))
    today_p1.sort(key=lambda t: (t.due_date or today))

    # Undated P1 suggestions limited in count; oldest first if you track creation time later
    suggested_p1 = undated_p1_candidates[:max_undated_p1]

    return {
        "carryover": carryover,
        "overdue": overdue,
        "today_p1": today_p1,
        "suggested_p1": suggested_p1,
    }


def group_tasks_for_picker(tasks: List[Task]) -> Dict[str, List[Task]]:
    """
    Group tasks for the lightweight picker by priority bucket.

    Returns:
        {
          "p1": [...],
          "p2": [...],
          "p3": [...],
        }
    """
    p1 = []
    p2 = []
    p3 = []

    for t in tasks:
        if t.completed:
            continue

        if t.priority == 1:
            p1.append(t)
        elif t.priority == 2:
            p2.append(t)
        else:
            p3.append(t)

    # Sort inside buckets: overdue → today → undated, roughly; you can refine later
    def sorter(task: Task):
        # (overdue_flag, undated_flag, due_date_or_big_value)
        if task.due_date is None:
            return (1, 1, date.max)
        return (0 if task.due_date < date.today() else 1, 0, task.due_date)

    p1.sort(key=sorter)
    p2.sort(key=sorter)
    p3.sort(key=sorter)

    return {"p1": p1, "p2": p2, "p3": p3}


def apply_morning_brief_plan(
    user_id: str,
    plan: List[Dict],
    todoist_client,
    today: date,
):
    """
    plan is a list of dicts describing each task from the modal:

    {
      "id": "123",
      "include": True,
      "priority": 1,         # 1,2,3...
      "time": "09:00" or None,
    }

    todoist_client is expected to expose:

      - get_open_flow_top_today_tasks(user_id) -> list[Task-like dicts]
      - clear_label_from_task(task_id: str, label: str) -> None
      - update_task(task_id: str, payload: dict) -> None

    Behavior:
      1. Clear FLOW_TOP_TODAY_LABEL from all open tasks for this user
      2. For each task with include=True:
           - set priority
           - set due date = today (if not set)
           - set due time if provided
           - ensure FLOW_TOP_TODAY_LABEL is on labels
    """
    # 1) Clear old labels
    old_today_tasks = todoist_client.get_open_flow_top_today_tasks(user_id=user_id)
    for t in old_today_tasks:
        todoist_client.clear_label_from_task(t["id"], FLOW_TOP_TODAY_LABEL)

    # 2) Apply new plan
    for item in plan:
        if not item.get("include"):
            continue

        task_id = item["id"]
        priority = item.get("priority")
        time_str = item.get("time")

        payload = {}

        if priority:
            payload["priority"] = priority

        # due date & time
        due = {}
        if time_str:
            # always ensure date is today if we have time
            due["date"] = today.isoformat()
            due["time"] = time_str
        else:
            # you can choose to set date even if no time; for now we stay minimal
            pass

        if due:
            payload["due"] = due

        # labels
        # This assumes update_task merges labels; if not, you'll need to fetch and merge first.
        payload.setdefault("labels", []).append(FLOW_TOP_TODAY_LABEL)

        todoist_client.update_task(task_id, payload=payload)
