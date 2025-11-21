"""Tests for natural language date parsing."""

from datetime import datetime, timedelta

from apps.server.core.dateparse import DateParser


class TestDateParser:
    """Test date parsing functionality."""

    def setup_method(self):
        """Set up test environment."""
        self.parser = DateParser()

    def test_mm_dd_format(self):
        """Test MM/DD format parsing."""
        # Test current year
        result = self.parser.parse("12/25")
        assert result is not None
        assert result.month == 12
        assert result.day == 25
        assert result.year == datetime.now().year

        # Test invalid dates
        assert self.parser.parse("13/25") is None  # Invalid month
        assert self.parser.parse("12/32") is None  # Invalid day

    def test_mm_dd_yyyy_format(self):
        """Test MM/DD/YYYY format parsing."""
        result = self.parser.parse("3/15/2025")
        assert result is not None
        assert result.month == 3
        assert result.day == 15
        assert result.year == 2025

        # Test 2-digit year
        result = self.parser.parse("6/10/25")
        assert result is not None
        assert result.year == 2025

    def test_month_name_format(self):
        """Test month name + day format."""
        result = self.parser.parse("Jan 15")
        assert result is not None
        assert result.month == 1
        assert result.day == 15

        result = self.parser.parse("December 31")
        assert result is not None
        assert result.month == 12
        assert result.day == 31

        # Test abbreviated
        result = self.parser.parse("Feb 28")
        assert result is not None
        assert result.month == 2
        assert result.day == 28

    def test_relative_dates(self):
        """Test relative date parsing."""
        # in X days/weeks/months
        result = self.parser.parse("in 5 days")
        expected = datetime.now() + timedelta(days=5)
        assert result is not None
        assert abs((result - expected).days) <= 1  # Allow for small timing differences

        result = self.parser.parse("in 2 weeks")
        expected = datetime.now() + timedelta(weeks=2)
        assert result is not None
        assert abs((result - expected).days) <= 1

        result = self.parser.parse("in 3 months")
        expected = datetime.now() + timedelta(days=90)  # Approx 3 months
        assert result is not None
        assert abs((result - expected).days) <= 5  # Allow for month variation

        # X days/weeks from now
        result = self.parser.parse("7 days from now")
        expected = datetime.now() + timedelta(days=7)
        assert result is not None
        assert abs((result - expected).days) <= 1

    def test_day_names(self):
        """Test day name parsing."""
        # Basic day names should return next occurrence
        result = self.parser.parse("Friday")
        assert result is not None
        assert result.weekday() == 4  # Friday is weekday 4

        # Next Friday should be at least 7 days out
        result = self.parser.parse("next Friday")
        assert result is not None
        assert result.weekday() == 4
        days_ahead = (result - datetime.now()).days
        assert days_ahead >= 7  # Should be next week's Friday

    def test_special_keywords(self):
        """Test special keyword parsing."""
        # Tomorrow
        result = self.parser.parse("tomorrow")
        expected = datetime.now() + timedelta(days=1)
        assert result is not None
        assert result.date() == expected.date()

        # Today/now
        result = self.parser.parse("today")
        assert result is not None
        assert result.date() == datetime.now().date()

        result = self.parser.parse("now")
        assert result is not None
        assert result.date() == datetime.now().date()

    def test_this_next_periods(self):
        """Test 'this week', 'next month', etc."""
        result = self.parser.parse("this week")
        assert result is not None
        # Should be this Sunday
        assert result.weekday() == 6  # Sunday

        result = self.parser.parse("next week")
        assert result is not None
        # Should be next Sunday
        assert result.weekday() == 6

        result = self.parser.parse("this month")
        assert result is not None
        # Should be last day of current month

        result = self.parser.parse("next month")
        assert result is not None
        # Should be last day of next month

    def test_end_of_periods(self):
        """Test 'end of week', 'end of month'."""
        result = self.parser.parse("end of week")
        assert result is not None
        assert result.weekday() == 6  # Sunday

        result = self.parser.parse("end of month")
        assert result is not None
        # Should be last day of current month
        current_month = datetime.now().month
        current_year = datetime.now().year
        if current_month == 12:
            next_month = datetime(current_year + 1, 1, 1)
        else:
            next_month = datetime(current_year, current_month + 1, 1)
        last_day = next_month - timedelta(days=1)
        assert result.date() == last_day.date()

    def test_date_formatting(self):
        """Test date formatting for project names."""
        test_date = datetime(2025, 12, 25)
        formatted = self.parser.format_date_for_project_name(test_date)
        assert formatted == "12/25"

        test_date = datetime(2025, 3, 5)
        formatted = self.parser.format_date_for_project_name(test_date)
        assert formatted == "03/05"

    def test_future_date_validation(self):
        """Test future date validation."""
        # Future date should be valid
        future_date = datetime.now() + timedelta(days=30)
        is_valid, error = self.parser.validate_future_date(future_date)
        assert is_valid
        assert error == ""

        # Past date should be invalid
        past_date = datetime.now() - timedelta(days=1)
        is_valid, error = self.parser.validate_future_date(past_date)
        assert not is_valid
        assert "past" in error.lower()

        # Too far future should be invalid
        far_future = datetime.now() + timedelta(days=800)  # > 2 years
        is_valid, error = self.parser.validate_future_date(far_future)
        assert not is_valid
        assert "too far" in error.lower()

        # Invalid object
        is_valid, error = self.parser.validate_future_date("not a date")
        assert not is_valid
        assert "invalid" in error.lower()

    def test_edge_cases(self):
        """Test edge cases and error handling."""
        # Empty string
        assert self.parser.parse("") is None
        assert self.parser.parse(None) is None

        # Unrecognized pattern
        assert self.parser.parse("gibberish text") is None

        # Partial matches shouldn't break
        assert self.parser.parse("maybe in 5 days") is not None
        assert self.parser.parse("I want it by Friday") is not None

    def test_case_insensitive(self):
        """Test that parsing is case insensitive."""
        assert self.parser.parse("FRIDAY") is not None
        assert self.parser.parse("friday") is not None
        assert self.parser.parse("Friday") is not None

        assert self.parser.parse("JAN 15") is not None
        assert self.parser.parse("jan 15") is not None
        assert self.parser.parse("Jan 15") is not None
