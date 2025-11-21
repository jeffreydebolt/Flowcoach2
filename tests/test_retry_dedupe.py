"""Tests for retry and deduplication handling (Phase 2.0)."""

from unittest.mock import Mock

from apps.server.slack.middleware import DeduplicationMiddleware, drop_slack_retries_middleware


class TestRetryDedupe:
    """Test duplicate action payload detection and dropping."""

    def test_drop_slack_retries_middleware_drops_retries(self):
        """Test that retry middleware drops requests with retry headers."""
        logger = Mock()
        middleware = drop_slack_retries_middleware(logger)
        next_called = Mock()

        # Request with retry header
        body_with_retry = {
            "headers": {"x-slack-retry-num": "2", "x-slack-retry-reason": "http_timeout"}
        }

        middleware(body_with_retry, next_called)

        # Should log the retry and not call next()
        logger.info.assert_called_once()
        assert "Dropping Slack retry #2" in logger.info.call_args[0][0]
        assert not next_called.called

    def test_drop_slack_retries_middleware_allows_normal_requests(self):
        """Test that retry middleware allows normal requests through."""
        logger = Mock()
        middleware = drop_slack_retries_middleware(logger)
        next_called = Mock()

        # Normal request without retry headers
        body_normal = {"headers": {}, "user": {"id": "user_123"}, "channel": {"id": "channel_123"}}

        middleware(body_normal, next_called)

        # Should call next() for normal requests
        assert next_called.called
        assert not logger.info.called

    def test_drop_slack_retries_handles_missing_headers(self):
        """Test retry middleware handles requests without headers."""
        logger = Mock()
        middleware = drop_slack_retries_middleware(logger)
        next_called = Mock()

        # Request without headers key
        body_no_headers = {"user": {"id": "user_123"}}

        middleware(body_no_headers, next_called)

        # Should proceed normally
        assert next_called.called

    def test_deduplication_middleware_prevents_duplicate_actions(self):
        """Test that deduplication middleware prevents duplicate action processing."""
        middleware = DeduplicationMiddleware(cache_size=10)
        next_called = Mock()

        # First action request
        action_body = {
            "actions": [{"action_id": "set_time_task123_10min"}],
            "trigger_id": "trigger_456",
        }

        # Process first time
        middleware(action_body, next_called)
        assert next_called.call_count == 1

        # Process same action again (duplicate)
        next_called.reset_mock()
        middleware(action_body, next_called)

        # Should be dropped
        assert not next_called.called

    def test_deduplication_middleware_allows_different_actions(self):
        """Test that deduplication allows different actions through."""
        middleware = DeduplicationMiddleware(cache_size=10)
        next_called = Mock()

        # First action
        action1 = {
            "actions": [{"action_id": "set_time_task123_10min"}],
            "trigger_id": "trigger_456",
        }

        # Different action
        action2 = {
            "actions": [{"action_id": "set_priority_task123_P1"}],
            "trigger_id": "trigger_789",
        }

        # Both should be processed
        middleware(action1, next_called)
        middleware(action2, next_called)

        assert next_called.call_count == 2

    def test_deduplication_middleware_handles_view_submissions(self):
        """Test deduplication works for view submissions."""
        middleware = DeduplicationMiddleware(cache_size=10)
        next_called = Mock()

        # View submission request
        view_body = {"view": {"callback_id": "morning_brief_submit", "id": "view_123"}}

        # Process first time
        middleware(view_body, next_called)
        assert next_called.call_count == 1

        # Process same submission again
        next_called.reset_mock()
        middleware(view_body, next_called)

        # Should be dropped
        assert not next_called.called

    def test_deduplication_middleware_handles_events(self):
        """Test deduplication works for events."""
        middleware = DeduplicationMiddleware(cache_size=10)
        next_called = Mock()

        # Event request
        event_body = {
            "event": {"type": "app_home_opened", "user": "user_123"},
            "event_id": "event_456",
        }

        # Process first time
        middleware(event_body, next_called)
        assert next_called.call_count == 1

        # Process same event again
        next_called.reset_mock()
        middleware(event_body, next_called)

        # Should be dropped
        assert not next_called.called

    def test_deduplication_cache_trimming(self):
        """Test that deduplication cache trims old entries."""
        middleware = DeduplicationMiddleware(cache_size=3)  # Small cache
        next_called = Mock()

        # Add 5 different actions (exceeds cache size)
        for i in range(5):
            action_body = {"actions": [{"action_id": f"action_{i}"}], "trigger_id": f"trigger_{i}"}
            middleware(action_body, next_called)

        # All should have been processed initially
        assert next_called.call_count == 5

        # Cache should have been trimmed to last 3
        assert len(middleware.processed_events) == 3

        # Re-submitting first action should work (was trimmed)
        next_called.reset_mock()
        first_action = {"actions": [{"action_id": "action_0"}], "trigger_id": "trigger_0"}
        middleware(first_action, next_called)

        # Should be processed again since it was evicted
        assert next_called.called

        # But re-submitting recent action should be blocked
        next_called.reset_mock()
        recent_action = {"actions": [{"action_id": "action_4"}], "trigger_id": "trigger_4"}
        middleware(recent_action, next_called)

        # Should be blocked since it's still in cache
        assert not next_called.called

    def test_deduplication_event_id_extraction_edge_cases(self):
        """Test edge cases in event ID extraction."""
        middleware = DeduplicationMiddleware(cache_size=10)

        # Request with no identifiable event ID
        no_id_body = {"user": {"id": "user_123"}}

        event_id = middleware._extract_event_id(no_id_body)
        assert event_id is None

        # Action with missing action_id
        incomplete_action = {"actions": [{}], "trigger_id": "trigger_123"}  # Missing action_id

        event_id = middleware._extract_event_id(incomplete_action)
        assert event_id == ":trigger_123"  # Should still extract trigger_id

        # View with missing callback_id
        incomplete_view = {"view": {"id": "view_123"}}  # Missing callback_id

        event_id = middleware._extract_event_id(incomplete_view)
        assert event_id == ":view_123"  # Should still extract view_id

    def test_combined_retry_and_deduplication(self):
        """Test that retry dropping and deduplication work together."""
        logger = Mock()
        retry_middleware = drop_slack_retries_middleware(logger)
        dedup_middleware = DeduplicationMiddleware(cache_size=10)

        next_called = Mock()

        # Request that's both a retry AND a duplicate
        retry_duplicate_body = {
            "headers": {"x-slack-retry-num": "1", "x-slack-retry-reason": "timeout"},
            "actions": [{"action_id": "test_action"}],
            "trigger_id": "test_trigger",
        }

        # Process normally first (establish in dedup cache)
        normal_body = {
            "headers": {},
            "actions": [{"action_id": "test_action"}],
            "trigger_id": "test_trigger",
        }

        # Chain the middlewares: retry → dedup → next
        def dedup_then_next():
            dedup_middleware(normal_body, next_called)

        retry_middleware(normal_body, dedup_then_next)

        # Should process normally
        assert next_called.call_count == 1

        # Now send the retry+duplicate
        next_called.reset_mock()
        logger.reset_mock()

        def dedup_then_next_retry():
            dedup_middleware(retry_duplicate_body, next_called)

        retry_middleware(retry_duplicate_body, dedup_then_next_retry)

        # Should be dropped by retry middleware (before reaching dedup)
        assert not next_called.called
        assert logger.info.called  # Retry was logged

    def test_action_id_uniqueness_across_tasks(self):
        """Test that action IDs from different tasks are treated as different events."""
        middleware = DeduplicationMiddleware(cache_size=10)
        next_called = Mock()

        # Same action type, different tasks
        action_task1 = {
            "actions": [{"action_id": "set_time_task111_10min"}],
            "trigger_id": "trigger_456",
        }

        action_task2 = {
            "actions": [{"action_id": "set_time_task222_10min"}],
            "trigger_id": "trigger_456",  # Same trigger, different task
        }

        # Both should be processed
        middleware(action_task1, next_called)
        middleware(action_task2, next_called)

        assert next_called.call_count == 2
