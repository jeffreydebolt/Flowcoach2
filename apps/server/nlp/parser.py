"""Natural language parser for task input with time and priority extraction."""

import re
from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass
class ParsedTask:
    """Parsed task with extracted time and priority."""

    content: str
    time_label: Optional[str] = None  # "2min" | "10min" | "30+min"
    user_priority: Optional[int] = None  # 1-4 (P1=highest)


def parse_task_input(raw_text: str) -> ParsedTask:
    """
    Parse conversational task input to extract content, time, and priority.

    Format: <task> — <time> — P<1-4>

    Args:
        raw_text: Raw user input like "Call doctor — 10m — P2"

    Returns:
        ParsedTask with cleaned content and optional time/priority

    Examples:
        >>> parse_task_input("Build plan for 2026 insurance — 30m+ — P2")
        ParsedTask(content="Build plan for 2026 insurance", time_label="30+min", user_priority=2)

        >>> parse_task_input("Call Banner Med with insurance info")
        ParsedTask(content="Call Banner Med with insurance info", time_label=None, user_priority=None)

        >>> parse_task_input("Remind me to review contract — urgent")
        ParsedTask(content="review contract", time_label=None, user_priority=1)
    """
    # Keep original for content extraction, lowercase for detection
    original = raw_text.strip()
    lower_text = original.lower()

    # Strip common task prefixes
    content = _strip_prefixes(original)

    # Split by separators and extract tokens
    parts = _split_by_separators(content)

    # Extract time and priority from parts
    time_label = None
    user_priority = None
    content_parts = []

    for part in parts:
        part_stripped = part.strip()
        if not part_stripped:
            continue

        # Check for time token
        detected_time = _detect_time_token(part_stripped.lower())
        if detected_time:
            time_label = detected_time
            continue

        # Check for priority token
        detected_priority = _detect_priority_token(part_stripped.lower())
        if detected_priority:
            user_priority = detected_priority
            continue

        # Not a time/priority token, keep as content
        content_parts.append(part_stripped)

    # Reconstruct content from remaining parts
    final_content = " ".join(content_parts).strip()

    # Fallback: if no content extracted, use original (minus prefixes)
    if not final_content:
        final_content = _strip_prefixes(original)

    return ParsedTask(content=final_content, time_label=time_label, user_priority=user_priority)


def _strip_prefixes(text: str) -> str:
    """Strip common task creation prefixes."""
    prefixes = [
        r"^(create|add|make)\s+(a\s+|an\s+)?(task\s+(to\s+|for\s+)?)?",
        r"^(remind me to|i need to|i want to|i should)\s+",
        r"^(task:?|todo:?)\s*",
        r"^please\s+",
        r"^[✓✔️]\s*",
        r"^\d+[\.\)]\s*",
        r"^[-\*]\s*",
    ]

    cleaned = text
    for pattern in prefixes:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE).strip()

    return cleaned if cleaned else text


def _split_by_separators(text: str) -> list[str]:
    """Split text by common separators."""
    # Split by —, -, |, ;, ,, but be careful with hyphens in content
    # Use negative lookbehind/lookahead to avoid splitting normal hyphens
    separators = r"—|(?<!\w)-(?!\w)|\|(?!\w)|;|,(?=\s*(?:P[1-4]|\d+m|\d+min|\d+\+|urgent|critical|high|low|normal|medium))"
    parts = re.split(separators, text, flags=re.IGNORECASE)
    return [part.strip() for part in parts if part.strip()]


def _detect_time_token(text: str) -> Optional[str]:
    """
    Detect and normalize time tokens.

    Accepts: 2m, 2min, 2, 10m, 10, 30m+, 30+, 30min+
    Returns: "2min" | "10min" | "30+min"
    """
    # Remove extra whitespace
    text = text.strip()

    # Patterns for time detection
    patterns = [
        (r"^2(m|min)?$", "2min"),
        (r"^10(m|min)?$", "10min"),
        (r"^30(m|min)?\+?$", "30+min"),
        (r"^30\+(m|min)?$", "30+min"),
    ]

    for pattern, normalized in patterns:
        if re.match(pattern, text, re.IGNORECASE):
            return normalized

    return None


def _detect_priority_token(text: str) -> Optional[int]:
    """
    Detect priority tokens and return human priority (1-4).

    P1..P4 takes precedence over word mappings.

    Returns:
        1-4 for P1-P4, or None if not detected
    """
    text = text.strip().lower()

    # Check for P1-P4 format first (takes precedence)
    p_match = re.match(r"^p([1-4])$", text)
    if p_match:
        return int(p_match.group(1))

    # Word mappings
    priority_words = {
        # P1: urgent, critical, must do today
        "urgent": 1,
        "critical": 1,
        "must do today": 1,
        "mustdo": 1,
        "asap": 1,
        # P2: high, today or tomorrow
        "high": 2,
        "today": 2,
        "tomorrow": 2,
        "soon": 2,
        # P3: normal, medium, next 2 days
        "normal": 3,
        "medium": 3,
        "med": 3,
        "regular": 3,
        # P4: low, this week
        "low": 4,
        "week": 4,
        "later": 4,
        "someday": 4,
    }

    # Check for exact word matches
    if text in priority_words:
        return priority_words[text]

    # Check for phrase matches (like "must do today")
    for phrase, priority in priority_words.items():
        if phrase in text:
            return priority

    return None
