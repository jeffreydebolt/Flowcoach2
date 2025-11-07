"""Tests for project audit classification logic."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

from apps.server.core.audit import ProjectAuditor, ProjectAuditItem
from apps.server.core.momentum import ProjectMomentum


class TestAuditClassification:
    """Test project audit classification logic."""

    def setup_method(self):
        """Set up test environment."""
        self.auditor = ProjectAuditor()

    def test_healthy_project_classification(self):
        """Test that healthy projects are classified correctly."""
        # Mock momentum tracker
        with patch.object(self.auditor.tracker, 'get_project_momentum') as mock_get_momentum:
            mock_get_momentum.return_value = ProjectMomentum(
                project_id="123",
                last_activity_at=datetime.now() - timedelta(hours=6),
                momentum_score=80,
                status="active",
                outcome_defined=True,
                due_date=datetime.now() + timedelta(days=7)
            )

            projects = [
                {"id": 123, "name": "Website Redesign"}
            ]

            categorized = self.auditor.classify_projects(projects)

            assert len(categorized['healthy']) == 1
            assert len(categorized['needs_definition']) == 0
            assert len(categorized['stalled']) == 0

            healthy_project = categorized['healthy'][0]
            assert healthy_project.project_name == "Website Redesign"
            assert healthy_project.momentum_score == 80
            assert healthy_project.category == "healthy"

    def test_needs_definition_classification(self):
        """Test that projects needing definition are classified correctly."""
        with patch.object(self.auditor.tracker, 'get_project_momentum') as mock_get_momentum:
            # Project without outcome defined
            mock_get_momentum.return_value = ProjectMomentum(
                project_id="456",
                last_activity_at=datetime.now() - timedelta(days=1),
                momentum_score=70,
                status="active",
                outcome_defined=False,  # Missing outcome
                due_date=None  # Missing due date
            )

            projects = [
                {"id": 456, "name": "Research Project"}
            ]

            categorized = self.auditor.classify_projects(projects)

            assert len(categorized['healthy']) == 0
            assert len(categorized['needs_definition']) == 1
            assert len(categorized['stalled']) == 0

            needs_def_project = categorized['needs_definition'][0]
            assert needs_def_project.project_name == "Research Project"
            assert needs_def_project.category == "needs_definition"

    def test_stalled_project_classification(self):
        """Test that stalled projects are classified correctly."""
        with patch.object(self.auditor.tracker, 'get_project_momentum') as mock_get_momentum:
            # Project with low momentum
            mock_get_momentum.return_value = ProjectMomentum(
                project_id="789",
                last_activity_at=datetime.now() - timedelta(days=5),
                momentum_score=30,  # Below 50 threshold
                status="stalled",
                outcome_defined=True,
                due_date=datetime.now() + timedelta(days=14)
            )

            projects = [
                {"id": 789, "name": "Mobile App"}
            ]

            categorized = self.auditor.classify_projects(projects)

            assert len(categorized['healthy']) == 0
            assert len(categorized['needs_definition']) == 0
            assert len(categorized['stalled']) == 1

            stalled_project = categorized['stalled'][0]
            assert stalled_project.project_name == "Mobile App"
            assert stalled_project.momentum_score == 30
            assert stalled_project.category == "stalled"

    def test_new_project_without_momentum_data(self):
        """Test classification of projects without momentum data."""
        with patch.object(self.auditor.tracker, 'get_project_momentum') as mock_get_momentum:
            # No momentum data (new project)
            mock_get_momentum.return_value = None

            projects = [
                {"id": 999, "name": "New Project"}
            ]

            categorized = self.auditor.classify_projects(projects)

            # New project should need definition (no outcome/due date)
            assert len(categorized['healthy']) == 0
            assert len(categorized['needs_definition']) == 1
            assert len(categorized['stalled']) == 0

            new_project = categorized['needs_definition'][0]
            assert new_project.project_name == "New Project"
            assert new_project.momentum_score == 100  # Default for new projects
            assert new_project.outcome_defined == False
            assert new_project.due_date is None

    def test_mixed_project_portfolio(self):
        """Test classification of a mixed portfolio of projects."""
        with patch.object(self.auditor.tracker, 'get_project_momentum') as mock_get_momentum:
            # Setup different momentum states
            momentum_data = {
                "100": ProjectMomentum("100", datetime.now(), 85, "active", True, datetime.now() + timedelta(days=7)),  # Healthy
                "200": ProjectMomentum("200", datetime.now() - timedelta(days=2), 65, "active", False, None),  # Needs definition
                "300": ProjectMomentum("300", datetime.now() - timedelta(days=7), 25, "stalled", True, datetime.now() + timedelta(days=3)),  # Stalled
                "400": None  # New project
            }

            def mock_momentum_lookup(project_id):
                return momentum_data.get(project_id)

            mock_get_momentum.side_effect = mock_momentum_lookup

            projects = [
                {"id": 100, "name": "Website Launch"},
                {"id": 200, "name": "Market Research"},
                {"id": 300, "name": "Old App Update"},
                {"id": 400, "name": "Brand New Project"}
            ]

            categorized = self.auditor.classify_projects(projects)

            # Check counts
            assert len(categorized['healthy']) == 1
            assert len(categorized['needs_definition']) == 2  # Research + New
            assert len(categorized['stalled']) == 1

            # Check healthy project
            assert categorized['healthy'][0].project_name == "Website Launch"

            # Check needs definition projects
            needs_def_names = [p.project_name for p in categorized['needs_definition']]
            assert "Market Research" in needs_def_names
            assert "Brand New Project" in needs_def_names

            # Check stalled project
            assert categorized['stalled'][0].project_name == "Old App Update"

    def test_audit_summary_statistics(self):
        """Test audit summary statistics calculation."""
        # Mock a categorized project set
        categorized = {
            'healthy': [Mock() for _ in range(3)],
            'needs_definition': [Mock() for _ in range(2)],
            'stalled': [Mock() for _ in range(1)]
        }

        summary = self.auditor.get_audit_summary(categorized)

        assert summary['total_projects'] == 6
        assert summary['healthy_count'] == 3
        assert summary['needs_definition_count'] == 2
        assert summary['stalled_count'] == 1
        assert summary['healthy_percentage'] == 50.0  # 3/6 * 100
        assert 'audit_timestamp' in summary

    def test_empty_portfolio_summary(self):
        """Test summary with no projects."""
        categorized = {
            'healthy': [],
            'needs_definition': [],
            'stalled': []
        }

        summary = self.auditor.get_audit_summary(categorized)

        assert summary['total_projects'] == 0
        assert summary['healthy_count'] == 0
        assert summary['healthy_percentage'] == 0.0

    def test_project_sorting_by_momentum(self):
        """Test that projects are sorted by momentum score."""
        with patch.object(self.auditor.tracker, 'get_project_momentum') as mock_get_momentum:
            # Setup projects with different momentum scores in same category
            momentum_data = {
                "1": ProjectMomentum("1", datetime.now(), 90, "active", True, datetime.now() + timedelta(days=7)),
                "2": ProjectMomentum("2", datetime.now(), 70, "active", True, datetime.now() + timedelta(days=14)),
                "3": ProjectMomentum("3", datetime.now(), 85, "active", True, datetime.now() + timedelta(days=21))
            }

            def mock_momentum_lookup(project_id):
                return momentum_data.get(project_id)

            mock_get_momentum.side_effect = mock_momentum_lookup

            projects = [
                {"id": 1, "name": "Project A"},  # Score 90
                {"id": 2, "name": "Project B"},  # Score 70
                {"id": 3, "name": "Project C"}   # Score 85
            ]

            categorized = self.auditor.classify_projects(projects)

            # All should be healthy, sorted by momentum descending
            healthy_projects = categorized['healthy']
            assert len(healthy_projects) == 3

            # Check sorting: 90, 85, 70
            assert healthy_projects[0].momentum_score == 90
            assert healthy_projects[1].momentum_score == 85
            assert healthy_projects[2].momentum_score == 70

    def test_action_recommendations(self):
        """Test action recommendations for different project types."""
        # Stalled project
        stalled_project = ProjectAuditItem(
            project_id="123",
            project_name="Stalled Project",
            momentum_score=25,
            status="stalled",
            outcome_defined=True,
            due_date=datetime.now() + timedelta(days=7),
            category="stalled",
            last_activity_days=5
        )

        stalled_actions = self.auditor.recommend_actions(stalled_project)
        assert "Recommit: Boost momentum and add next action" in stalled_actions
        assert "Pause: Put on hold until needed" in stalled_actions
        assert "Rewrite: Redefine outcome and timeline" in stalled_actions

        # Needs definition project
        needs_def_project = ProjectAuditItem(
            project_id="456",
            project_name="Undefined Project",
            momentum_score=80,
            status="active",
            outcome_defined=False,
            due_date=None,
            category="needs_definition",
            last_activity_days=2
        )

        def_actions = self.auditor.recommend_actions(needs_def_project)
        assert "Rewrite: Define concrete outcome and due date" in def_actions

        # Healthy project
        healthy_project = ProjectAuditItem(
            project_id="789",
            project_name="Healthy Project",
            momentum_score=85,
            status="active",
            outcome_defined=True,
            due_date=datetime.now() + timedelta(days=14),
            category="healthy",
            last_activity_days=1
        )

        healthy_actions = self.auditor.recommend_actions(healthy_project)
        assert "Keep going: Project is on track" in healthy_actions
