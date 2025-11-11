"""Slack block rendering helpers for FlowCoach UI components."""

from typing import Dict, List, Any, Optional


def render_task_creation_message(
    task_content: str,
    task_id: str,
    current_time: Optional[str] = None,
    current_priority: Optional[int] = None,
    show_chips: bool = True,
) -> Dict[str, Any]:
    """
    Render task creation confirmation message with optional time/priority chips.

    Args:
        task_content: The task content to display
        task_id: Task ID for action button references
        current_time: Current time label ("2min", "10min", "30+min")
        current_priority: Current human priority (1-4)
        show_chips: Whether to show chip rows (False if both time and priority were parsed)

    Returns:
        Slack message payload with blocks
    """
    blocks = [
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f":white_check_mark: Added *{task_content}*"},
        }
    ]

    if show_chips:
        # Add time chips if no time was specified
        if current_time is None:
            current_time = "10min"  # Default

        time_blocks = render_time_chips(task_id, current_time)
        blocks.extend(time_blocks)

        # Add priority chips if no priority was specified
        if current_priority is None:
            current_priority = 3  # Default P3

        priority_blocks = render_priority_chips(task_id, current_priority)
        blocks.extend(priority_blocks)

    return {"blocks": blocks}


def render_time_chips(task_id: str, selected_time: str) -> List[Dict[str, Any]]:
    """
    Render time selection chip row.

    Args:
        task_id: Task ID for action button references
        selected_time: Currently selected time ("2min", "10min", "30+min")

    Returns:
        List of block elements for time chips
    """
    time_options = ["2min", "10min", "30+min"]
    time_display = {"2min": "2m", "10min": "10m", "30+min": "30m+"}

    elements = []
    for time_option in time_options:
        element = {
            "type": "button",
            "text": {"type": "plain_text", "text": time_display[time_option]},
            "action_id": f"set_time_{task_id}_{time_option}",
        }

        # Highlight selected option
        if time_option == selected_time:
            element["style"] = "primary"

        elements.append(element)

    return [{"type": "actions", "block_id": f"time_row_{task_id}", "elements": elements}]


def render_priority_chips(task_id: str, selected_priority: int) -> List[Dict[str, Any]]:
    """
    Render priority selection chip row.

    Args:
        task_id: Task ID for action button references
        selected_priority: Currently selected human priority (1-4)

    Returns:
        List of block elements for priority chips
    """
    priority_options = [
        {"level": 1, "label": "P1 🔴", "color": "danger"},
        {"level": 2, "label": "P2 🟠", "color": None},
        {"level": 3, "label": "P3 🟡", "color": None},
        {"level": 4, "label": "P4 ⚪", "color": None},
    ]

    elements = []
    for priority in priority_options:
        element = {
            "type": "button",
            "text": {"type": "plain_text", "text": priority["label"]},
            "action_id": f"set_priority_{task_id}_P{priority['level']}",
        }

        # Highlight selected option or use danger style for P1
        if priority["level"] == selected_priority:
            element["style"] = "primary"
        elif priority["level"] == 1 and selected_priority != 1:
            element["style"] = "danger"

        elements.append(element)

    return [{"type": "actions", "block_id": f"prio_row_{task_id}", "elements": elements}]


def render_bulk_priority_list(
    tasks: List[Dict[str, Any]], page: int = 0, total_pages: int = 1
) -> Dict[str, Any]:
    """
    Render bulk priority review list with per-task priority selectors.

    Args:
        tasks: List of task dicts with id, content, priority_human
        page: Current page (0-based)
        total_pages: Total number of pages

    Returns:
        Slack message payload with task list and pagination
    """
    blocks = [
        {"type": "header", "text": {"type": "plain_text", "text": "🎯 Adjust Task Priorities"}},
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"Page {page + 1} of {total_pages} • Click priority buttons to update",
            },
        },
        {"type": "divider"},
    ]

    # Add task rows
    for task in tasks:
        task_blocks = render_bulk_priority_row(task)
        blocks.extend(task_blocks)

    # Add pagination if needed
    if total_pages > 1:
        blocks.append({"type": "divider"})
        pagination_blocks = render_pagination(page, total_pages)
        blocks.extend(pagination_blocks)

    return {"blocks": blocks}


def render_bulk_priority_row(task: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Render a single task row in bulk priority view.

    Args:
        task: Task dict with id, content, priority_human

    Returns:
        List of block elements for the task row
    """
    task_id = task["id"]
    content = task["content"]
    current_priority = task.get("priority_human", 3)

    # Priority badge mapping
    priority_badges = {1: "🟥 P1", 2: "🟧 P2", 3: "🟨 P3", 4: "⬜ P4"}

    # Truncate content if too long
    if len(content) > 70:
        content = content[:67] + "..."

    badge = priority_badges.get(current_priority, "🟨 P3")

    # Task info section
    task_section = {
        "type": "section",
        "text": {"type": "mrkdwn", "text": f"{badge} {content}"},
        "accessory": {
            "type": "overflow",
            "action_id": f"task_overflow_{task_id}",
            "options": [
                {"text": {"type": "plain_text", "text": "View Details"}, "value": f"view_{task_id}"}
            ],
        },
    }

    # Priority selector buttons
    priority_elements = []
    for level in [1, 2, 3, 4]:
        element = {
            "type": "button",
            "text": {"type": "plain_text", "text": f"P{level}"},
            "action_id": f"bulk_set_priority_{task_id}_P{level}",
        }

        if level == current_priority:
            element["style"] = "primary"
        elif level == 1:
            element["style"] = "danger"

        priority_elements.append(element)

    priority_actions = {
        "type": "actions",
        "block_id": f"bulk_prio_{task_id}",
        "elements": priority_elements,
    }

    return [task_section, priority_actions, {"type": "divider"}]


def render_pagination(page: int, total_pages: int) -> List[Dict[str, Any]]:
    """
    Render pagination controls.

    Args:
        page: Current page (0-based)
        total_pages: Total number of pages

    Returns:
        List of block elements for pagination
    """
    elements = []

    # Previous button
    if page > 0:
        elements.append(
            {
                "type": "button",
                "text": {"type": "plain_text", "text": "◀ Previous"},
                "action_id": f"page_priorities_{page - 1}",
            }
        )

    # Page indicator (non-interactive)
    elements.append(
        {
            "type": "button",
            "text": {"type": "plain_text", "text": f"{page + 1}/{total_pages}"},
            "action_id": "page_info_noop",
            "style": "primary",
        }
    )

    # Next button
    if page < total_pages - 1:
        elements.append(
            {
                "type": "button",
                "text": {"type": "plain_text", "text": "Next ▶"},
                "action_id": f"page_priorities_{page + 1}",
            }
        )

    return [{"type": "actions", "block_id": "pagination_controls", "elements": elements}]
