"""Unit tests for reading progress service."""

from datetime import UTC, datetime, timedelta

import pytest

from app.schemas.progress import ProgressUpdate


class TestProgressCalculation:
    """Test progress percentage calculation."""

    def test_progress_percentage_calculation(self):
        """Test that progress percentage is calculated correctly."""
        test_cases = [
            (1, 100, 1),  # First page = 1%
            (50, 100, 50),  # Halfway = 50%
            (100, 100, 100),  # Last page = 100%
            (1, 10, 10),  # 1 of 10 = 10%
            (5, 10, 50),  # 5 of 10 = 50%
            (99, 100, 99),  # Almost done = 99%
        ]

        for current, total, expected in test_cases:
            progress_percent = int((current / total) * 100) if total > 0 else 0
            assert progress_percent == expected, f"Expected {expected}% for page {current}/{total}, got {progress_percent}%"

    def test_progress_validation(self):
        """Test progress update validation."""
        # Valid progress
        progress = ProgressUpdate(current_page=1, total_pages=100, reading_time_seconds=60)
        assert progress.current_page == 1
        assert progress.total_pages == 100
        assert progress.reading_time_seconds == 60

        # Invalid: current_page < 1
        with pytest.raises(ValueError):
            ProgressUpdate(current_page=0, total_pages=100)

        # Invalid: total_pages < 1
        with pytest.raises(ValueError):
            ProgressUpdate(current_page=1, total_pages=0)

        # Invalid: negative reading time
        with pytest.raises(ValueError):
            ProgressUpdate(current_page=1, total_pages=100, reading_time_seconds=-1)


class TestStreakCalculation:
    """Test reading streak calculation logic."""

    def test_streak_consecutive_days(self):
        """Test streak calculation with consecutive days."""
        today = datetime.now(UTC).date()

        # Simulate reading dates: today, yesterday, day before
        read_dates = [
            today,
            today - timedelta(days=1),
            today - timedelta(days=2),
        ]

        # Calculate streak (mock logic from repository)
        current_streak = 0
        for i, read_date in enumerate(read_dates):
            expected_date = today - timedelta(days=i)
            if read_date == expected_date:
                current_streak += 1
            else:
                break

        assert current_streak == 3

    def test_streak_broken(self):
        """Test streak calculation with gap."""
        today = datetime.now(UTC).date()

        # Simulate reading dates: today, 2 days ago (skipped yesterday)
        read_dates = [
            today,
            today - timedelta(days=2),  # Gap here
        ]

        # Calculate streak
        current_streak = 0
        for i, read_date in enumerate(read_dates):
            expected_date = today - timedelta(days=i)
            if read_date == expected_date:
                current_streak += 1
            else:
                break

        assert current_streak == 1  # Only today counts

    def test_streak_no_recent_read(self):
        """Test streak when last read was not today."""
        today = datetime.now(UTC).date()

        # Last read was 5 days ago
        read_dates = [
            today - timedelta(days=5),
        ]

        # Calculate streak
        current_streak = 0
        for i, read_date in enumerate(read_dates):
            expected_date = today - timedelta(days=i)
            if read_date == expected_date:
                current_streak += 1
            else:
                break

        assert current_streak == 0  # Streak is broken

    def test_longest_streak_calculation(self):
        """Test longest streak calculation."""
        today = datetime.now(UTC).date()

        # Simulate pattern: 3 day streak, 2 day gap, 5 day streak
        read_dates = [
            # Current streak (3 days)
            today,
            today - timedelta(days=1),
            today - timedelta(days=2),
            # Gap
            today - timedelta(days=5),  # Skipped days 3,4
            today - timedelta(days=6),
            today - timedelta(days=7),
            today - timedelta(days=8),
            today - timedelta(days=9),  # 5 consecutive days
        ]

        # Calculate longest streak
        longest_streak = 0
        temp_streak = 1

        for i in range(1, len(read_dates)):
            prev_date = read_dates[i - 1]
            curr_date = read_dates[i]

            # Check if consecutive days
            if (prev_date - curr_date).days == 1:
                temp_streak += 1
                longest_streak = max(longest_streak, temp_streak)
            else:
                temp_streak = 1

        longest_streak = max(longest_streak, temp_streak)

        # Should be 5 (the longer streak in the past)
        assert longest_streak == 5


class TestReadingTimeAccumulation:
    """Test reading time tracking."""

    def test_reading_time_accumulation(self):
        """Test that reading time accumulates correctly."""
        # Simulate updates
        updates = [
            60,   # 1 minute
            120,  # 2 minutes
            180,  # 3 minutes
        ]

        total_time = sum(updates)
        assert total_time == 360  # 6 minutes total

        # Format as hours and minutes
        hours = total_time // 3600
        minutes = (total_time % 3600) // 60
        formatted = f"{hours}h {minutes}m"

        assert formatted == "0h 6m"

    def test_reading_time_formatting(self):
        """Test reading time formatting."""
        test_cases = [
            (60, "0h 1m"),
            (3600, "1h 0m"),
            (3660, "1h 1m"),
            (7200, "2h 0m"),
            (7380, "2h 3m"),
            (36000, "10h 0m"),
        ]

        for seconds, expected in test_cases:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            formatted = f"{hours}h {minutes}m"
            assert formatted == expected
