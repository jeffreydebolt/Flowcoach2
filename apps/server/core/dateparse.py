"""Natural language date parsing utilities."""

import logging
import re
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class DateParser:
    """Parse natural language dates into datetime objects."""

    def __init__(self):
        # Common date patterns
        self.patterns = [
            # MM/DD format
            (r"(\d{1,2})/(\d{1,2})", self._parse_mm_dd),
            # MM/DD/YY or MM/DD/YYYY
            (r"(\d{1,2})/(\d{1,2})/(\d{2,4})", self._parse_mm_dd_yy),
            # Month DD format (e.g., "Jan 15", "January 15")
            (
                r"(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+(\d{1,2})",
                self._parse_month_dd,
            ),
            # Relative dates
            (r"in\s+(\d+)\s+(day|week|month)s?", self._parse_relative),
            (r"(\d+)\s+(day|week|month)s?\s+from\s+now", self._parse_relative),
            # This/next week/month
            (r"(this|next)\s+(week|month)", self._parse_this_next),
            # Specific day names
            (r"(monday|tuesday|wednesday|thursday|friday|saturday|sunday)", self._parse_day_name),
            (
                r"next\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)",
                self._parse_next_day_name,
            ),
            # Common shortcuts
            (r"tomorrow", lambda m: datetime.now() + timedelta(days=1)),
            (r"(today|now)", lambda m: datetime.now()),
            (r"end\s+of\s+(week|month)", self._parse_end_of),
        ]

    def parse(self, text: str) -> datetime | None:
        """
        Parse natural language date from text.

        Args:
            text: Natural language text containing a date

        Returns:
            Parsed datetime object or None if no date found
        """
        if not text:
            return None

        text = text.lower().strip()

        for pattern, parser in self.patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    result = parser(match)
                    if isinstance(result, datetime):
                        logger.info(f"Parsed '{text}' as {result.strftime('%Y-%m-%d')}")
                        return result
                except Exception as e:
                    logger.warning(f"Failed to parse date pattern '{pattern}' in '{text}': {e}")
                    continue

        logger.debug(f"No date pattern matched for '{text}'")
        return None

    def _parse_mm_dd(self, match) -> datetime:
        """Parse MM/DD format (current year assumed)."""
        month, day = int(match.group(1)), int(match.group(2))
        current_year = datetime.now().year

        # Validate month/day
        if not (1 <= month <= 12) or not (1 <= day <= 31):
            raise ValueError(f"Invalid date: {month}/{day}")

        try:
            return datetime(current_year, month, day)
        except ValueError:
            # Try next year if date has passed
            return datetime(current_year + 1, month, day)

    def _parse_mm_dd_yy(self, match) -> datetime:
        """Parse MM/DD/YY or MM/DD/YYYY format."""
        month, day, year = int(match.group(1)), int(match.group(2)), int(match.group(3))

        # Handle 2-digit years
        if year < 100:
            if year < 50:
                year += 2000
            else:
                year += 1900

        # Validate
        if not (1 <= month <= 12) or not (1 <= day <= 31) or year < 2020:
            raise ValueError(f"Invalid date: {month}/{day}/{year}")

        return datetime(year, month, day)

    def _parse_month_dd(self, match) -> datetime:
        """Parse month name + day format."""
        month_str, day = match.group(1), int(match.group(2))

        # Month name mapping
        months = {
            "jan": 1,
            "feb": 2,
            "mar": 3,
            "apr": 4,
            "may": 5,
            "jun": 6,
            "jul": 7,
            "aug": 8,
            "sep": 9,
            "oct": 10,
            "nov": 11,
            "dec": 12,
        }

        month = months.get(month_str[:3])
        if not month or not (1 <= day <= 31):
            raise ValueError(f"Invalid date: {month_str} {day}")

        current_year = datetime.now().year
        current_date = datetime.now()

        try:
            parsed_date = datetime(current_year, month, day)
            # If date has passed this year, use next year
            if parsed_date < current_date:
                parsed_date = datetime(current_year + 1, month, day)
            return parsed_date
        except ValueError:
            raise ValueError(f"Invalid date: {month_str} {day}")

    def _parse_relative(self, match) -> datetime:
        """Parse relative dates like 'in 2 weeks' or '3 days from now'."""
        amount = int(match.group(1))
        unit = match.group(2).lower()

        if unit.startswith("day"):
            delta = timedelta(days=amount)
        elif unit.startswith("week"):
            delta = timedelta(weeks=amount)
        elif unit.startswith("month"):
            # Approximate months as 30 days
            delta = timedelta(days=amount * 30)
        else:
            raise ValueError(f"Unknown time unit: {unit}")

        return datetime.now() + delta

    def _parse_this_next(self, match) -> datetime:
        """Parse 'this week', 'next month', etc."""
        modifier, unit = match.group(1), match.group(2)
        current = datetime.now()

        if unit == "week":
            # End of week (Sunday)
            days_until_sunday = (6 - current.weekday()) % 7
            if modifier == "this":
                return current + timedelta(days=days_until_sunday)
            else:  # next
                return current + timedelta(days=days_until_sunday + 7)

        elif unit == "month":
            # End of month
            if modifier == "this":
                # Last day of current month
                if current.month == 12:
                    return datetime(current.year + 1, 1, 1) - timedelta(days=1)
                else:
                    return datetime(current.year, current.month + 1, 1) - timedelta(days=1)
            else:  # next
                # Last day of next month
                if current.month == 11:
                    return datetime(current.year + 1, 1, 1) - timedelta(days=1)
                elif current.month == 12:
                    return datetime(current.year + 1, 2, 1) - timedelta(days=1)
                else:
                    return datetime(current.year, current.month + 2, 1) - timedelta(days=1)

        raise ValueError(f"Unknown unit in this/next: {unit}")

    def _parse_day_name(self, match) -> datetime:
        """Parse day names like 'friday'."""
        day_name = match.group(1).lower()

        days = {
            "monday": 0,
            "tuesday": 1,
            "wednesday": 2,
            "thursday": 3,
            "friday": 4,
            "saturday": 5,
            "sunday": 6,
        }

        target_weekday = days.get(day_name)
        if target_weekday is None:
            raise ValueError(f"Unknown day: {day_name}")

        current = datetime.now()
        current_weekday = current.weekday()

        # Days until target day
        days_ahead = (target_weekday - current_weekday) % 7
        if days_ahead == 0:  # If it's the same day, use next week
            days_ahead = 7

        return current + timedelta(days=days_ahead)

    def _parse_next_day_name(self, match) -> datetime:
        """Parse 'next friday', etc."""
        day_name = match.group(1).lower()

        days = {
            "monday": 0,
            "tuesday": 1,
            "wednesday": 2,
            "thursday": 3,
            "friday": 4,
            "saturday": 5,
            "sunday": 6,
        }

        target_weekday = days.get(day_name)
        if target_weekday is None:
            raise ValueError(f"Unknown day: {day_name}")

        current = datetime.now()
        current_weekday = current.weekday()

        # Always next week
        days_ahead = (target_weekday - current_weekday) % 7
        if days_ahead == 0:
            days_ahead = 7
        else:
            days_ahead += 7

        return current + timedelta(days=days_ahead)

    def _parse_end_of(self, match) -> datetime:
        """Parse 'end of week', 'end of month'."""
        unit = match.group(1)
        current = datetime.now()

        if unit == "week":
            # End of current week (Sunday)
            days_until_sunday = (6 - current.weekday()) % 7
            return current + timedelta(days=days_until_sunday)

        elif unit == "month":
            # Last day of current month
            if current.month == 12:
                return datetime(current.year + 1, 1, 1) - timedelta(days=1)
            else:
                return datetime(current.year, current.month + 1, 1) - timedelta(days=1)

        raise ValueError(f"Unknown unit in end of: {unit}")

    def format_date_for_project_name(self, date_obj: datetime) -> str:
        """Format date for use in project names (MM/DD format)."""
        return date_obj.strftime("%m/%d")

    def validate_future_date(self, date_obj: datetime) -> tuple[bool, str]:
        """
        Validate that date is in the future and reasonable.

        Returns:
            (is_valid, error_message)
        """
        if not isinstance(date_obj, datetime):
            return False, "Invalid date object"

        current = datetime.now()

        # Check if in past
        if date_obj < current:
            return False, "Date cannot be in the past"

        # Check if too far in future (more than 2 years)
        two_years_ahead = current + timedelta(days=730)
        if date_obj > two_years_ahead:
            return False, "Date is too far in the future (more than 2 years)"

        return True, ""
