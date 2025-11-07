"""Task scoring and deep work detection."""

import re
from typing import Dict, Optional, Tuple, List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class TaskScorer:
    """Handles task scoring for prioritization."""

    DURATION_PATTERNS = [
        (r'(\d+)\s*(?:hours?|hrs?|h)\b', lambda m: int(m.group(1)) * 60),
        (r'(\d+)\s*(?:minutes?|mins?|m)\b', lambda m: int(m.group(1))),
        (r'(\d+)min\b', lambda m: int(m.group(1))),
        (r'~(\d+)m\b', lambda m: int(m.group(1))),
    ]

    DEEP_WORK_KEYWORDS = [
        'plan', 'design', 'architect', 'analyze', 'research',
        'write', 'create', 'develop', 'implement', 'review',
        'presentation', 'proposal', 'strategy', 'report'
    ]

    @classmethod
    def extract_duration(cls, text: str) -> Optional[int]:
        """Extract duration in minutes from task text."""
        text = text.lower()

        for pattern, extractor in cls.DURATION_PATTERNS:
            match = re.search(pattern, text)
            if match:
                return extractor(match)

        # Check for deep work keywords
        for keyword in cls.DEEP_WORK_KEYWORDS:
            if keyword in text.lower():
                return 30  # Default deep work duration

        return None

    @classmethod
    def is_deep_work(cls, text: str, duration_minutes: Optional[int] = None) -> bool:
        """Determine if task qualifies as deep work."""
        if duration_minutes and duration_minutes >= 15:
            return True

        # Extract duration if not provided
        if duration_minutes is None:
            duration_minutes = cls.extract_duration(text)

        if duration_minutes and duration_minutes >= 15:
            return True

        # Check for deep work keywords
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in cls.DEEP_WORK_KEYWORDS)

    @classmethod
    def parse_score_input(cls, input_str: str) -> Optional[Tuple[int, int, str]]:
        """
        Parse scoring input like '4/3/am' into (impact, urgency, energy).

        Returns:
            Tuple of (impact, urgency, energy) or None if invalid
        """
        parts = input_str.strip().lower().split('/')
        if len(parts) != 3:
            return None

        try:
            impact = int(parts[0])
            urgency = int(parts[1])
            energy = parts[2]

            # Validate ranges
            if not (1 <= impact <= 5 and 1 <= urgency <= 5):
                return None

            if energy not in ('am', 'pm'):
                return None

            return (impact, urgency, energy)
        except (ValueError, IndexError):
            return None

    @classmethod
    def calculate_total_score(cls, impact: int, urgency: int, energy: str) -> int:
        """
        Calculate total task score.

        Args:
            impact: 1-5 scale
            urgency: 1-5 scale
            energy: 'am' or 'pm'

        Returns:
            Total score with energy fit bonus
        """
        total = impact + urgency

        # Add energy fit bonus
        current_hour = datetime.now().hour
        is_morning = 6 <= current_hour < 12

        if (is_morning and energy == 'am') or (not is_morning and energy == 'pm'):
            total += 1

        return total

    @classmethod
    def get_score_labels(cls, impact: int, urgency: int, energy: str) -> List[str]:
        """Generate Todoist labels for scores."""
        return [
            f"impact{impact}",
            f"urgency{urgency}",
            f"energy_{energy}"
        ]
