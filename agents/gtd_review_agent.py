"""
GTD Review Agent - BMAD-inspired implementation.

Facilitates GTD weekly reviews, system maintenance, and productivity analytics
following BMAD patterns for structured workflows and agent collaboration.
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import json

from framework.base_agent import BaseAgent

logger = logging.getLogger(__name__)


class GTDReviewAgent(BaseAgent):
    """
    GTD Review Agent implementing David Allen's Weekly Review process.
    
    Following BMAD patterns for:
    - Structured multi-step workflows
    - Analytics and insight generation
    - System maintenance automation
    - Context-aware recommendations
    """
    
    def __init__(self, config: Dict[str, Any], services: Dict[str, Any] = None):
        """Initialize GTD Review Agent with BMAD patterns."""
        super().__init__(config, services)
        
        # Service dependencies
        self.todoist = self.get_service("todoist")
        self.calendar = self.get_service("calendar")
        self.analytics_service = self.get_service("analytics_service")
        
        # Review configuration
        self.review_config = config.get("config", {}).get("weekly_review", {})
        self.analytics_config = config.get("config", {}).get("analytics", {})
        self.insights_config = config.get("config", {}).get("insights", {})
        
        # Review schedule
        self.default_day = self.review_config.get("default_day", "friday")
        self.default_time = self.review_config.get("default_time", "16:00")
        
        # Analytics thresholds
        thresholds = self.analytics_config.get("thresholds", {})
        self.stale_task_threshold = thresholds.get("stale_task_days", 14)
        self.low_completion_threshold = thresholds.get("low_completion_rate", 0.6)
        
        # Review checklist steps
        self.review_steps = self.review_config.get("steps", {})
        
        logger.info(f"Initialized {self.name} with weekly review workflows")
    
    def can_handle(self, message: Dict[str, Any]) -> bool:
        """
        Determine if this agent can handle review-related messages.
        
        BMAD pattern: Clear capability boundaries for review and analytics
        """
        text = message.get("text", "").strip().lower()
        
        if not text:
            return False
        
        # Review trigger patterns
        review_triggers = [
            "weekly review", "review my", "check my progress", "how am i doing",
            "productivity report", "show my stats"
        ]
        
        for trigger in review_triggers:
            if trigger in text:
                return True
        
        # Maintenance patterns
        maintenance_triggers = [
            "clean up", "organize my", "stale tasks", "old tasks", "stuck projects"
        ]
        
        for trigger in maintenance_triggers:
            if trigger in text:
                return True
        
        # Insight patterns
        insight_triggers = [
            "insights", "patterns", "trends", "how can i improve", 
            "what should i focus on"
        ]
        
        for trigger in insight_triggers:
            if trigger in text:
                return True
        
        return False
    
    def _process_agent_message(self, message: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process review message following BMAD patterns.
        
        BMAD pattern: Context-aware workflow routing
        """
        text = message.get("text", "").strip().lower()
        user_id = message.get("user", "unknown")
        
        # Check current review state
        review_state = self.get_context("review_state")
        review_step = self.get_context("review_step", 0)
        
        # Handle multi-step review workflows
        if review_state == "weekly_review_in_progress":
            return self._continue_weekly_review(text, user_id, review_step)
        elif review_state == "awaiting_review_confirmation":
            return self._handle_review_confirmation(text, user_id)
        
        # Handle new review requests
        if "weekly review" in text:
            return self._initiate_weekly_review(user_id)
        elif any(phrase in text for phrase in ["stale", "old tasks"]):
            return self._analyze_stale_tasks(user_id)
        elif any(phrase in text for phrase in ["progress", "report", "stats"]):
            return self._generate_progress_report(user_id)
        elif any(phrase in text for phrase in ["insights", "patterns"]):
            return self._generate_insights(user_id)
        else:
            return self._general_review_guidance(text, user_id)
    
    # BMAD-style command implementations
    
    def cmd_weekly_review(self, args: str, message: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Start guided GTD weekly review process.
        
        BMAD pattern: Structured workflow initiation
        """
        user_id = message.get("user", "unknown")
        review_type = args.strip() or "full"
        return self._initiate_weekly_review(user_id, review_type)
    
    def cmd_stale_tasks(self, args: str, message: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Identify and review stale tasks."""
        user_id = message.get("user", "unknown")
        threshold = args.strip() or "1week"
        return self._analyze_stale_tasks(user_id, threshold)
    
    def cmd_progress_report(self, args: str, message: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate productivity analytics."""
        user_id = message.get("user", "unknown")
        period = args.strip() or "week"
        return self._generate_progress_report(user_id, period)
    
    def cmd_insights(self, args: str, message: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate productivity insights."""
        user_id = message.get("user", "unknown")
        insight_type = args.strip() or "weekly"
        return self._generate_insights(user_id, insight_type)
    
    def cmd_project_health(self, args: str, message: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Check health of all active projects."""
        user_id = message.get("user", "unknown")
        return self._analyze_project_health(user_id)
    
    def cmd_celebrate(self, args: str, message: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Celebrate accomplishments."""
        user_id = message.get("user", "unknown")
        period = args.strip() or "week"
        return self._celebrate_accomplishments(user_id, period)
    
    # GTD Weekly Review Implementation (BMAD-inspired structured workflow)
    
    def _initiate_weekly_review(self, user_id: str, review_type: str = "full") -> Dict[str, Any]:
        """
        Start GTD weekly review following David Allen's process.
        
        BMAD pattern: Multi-step workflow with clear progression
        """
        logger.info(f"Starting weekly review for user: {user_id}, type: {review_type}")
        
        # Initialize review context
        review_data = {
            "review_type": review_type,
            "started_at": datetime.now().isoformat(),
            "steps_completed": [],
            "current_step": 1,
            "total_steps": 8 if review_type == "full" else 4
        }
        
        self.update_context({
            "review_state": "weekly_review_in_progress",
            "review_step": 1,
            "review_data": review_data
        })
        
        # Step 1: Collect Loose Papers/Items
        return {
            "response_type": "weekly_review_step_1",
            "step": "Collect Loose Papers",
            "step_number": 1,
            "total_steps": review_data["total_steps"],
            "message": f"🔍 **GTD Weekly Review Started** ({review_type})\n\n**Step 1: Collect Loose Papers & Items**\n\nGather all loose items from:\n\n✅ Physical inbox\n✅ Email inbox\n✅ Slack messages\n✅ Voice memos\n✅ Browser bookmarks\n✅ Meeting notes\n✅ Receipts and papers\n\nHave you collected all loose items?\n\n*Type 'yes' when ready to proceed.*",
            "context_update": {
                "review_state": "weekly_review_in_progress",
                "review_step": 1,
                "review_data": review_data,
                "current_agent": "gtd-review-agent"
            },
            "workflow": {
                "name": "weekly_review",
                "step": 1,
                "checklist": self.review_steps.get("collect_inputs", [])
            }
        }
    
    def _continue_weekly_review(self, response: str, user_id: str, current_step: int) -> Dict[str, Any]:
        """Continue weekly review workflow."""
        review_data = self.get_context("review_data", {})
        
        # Mark current step as completed
        step_name = f"step_{current_step}"
        if step_name not in review_data.get("steps_completed", []):
            review_data.setdefault("steps_completed", []).append(step_name)
        
        # Move to next step
        next_step = current_step + 1
        total_steps = review_data.get("total_steps", 8)
        
        if next_step > total_steps:
            return self._complete_weekly_review(user_id)
        
        # Update context
        self.update_context({
            "review_step": next_step,
            "review_data": review_data
        })
        
        # Route to appropriate step
        step_methods = {
            2: self._review_step_2_process_inbox,
            3: self._review_step_3_review_calendar,
            4: self._review_step_4_review_projects,
            5: self._review_step_5_review_next_actions,
            6: self._review_step_6_review_waiting_for,
            7: self._review_step_7_review_someday_maybe,
            8: self._review_step_8_plan_ahead
        }
        
        step_method = step_methods.get(next_step)
        if step_method:
            return step_method(user_id)
        else:
            return self._complete_weekly_review(user_id)
    
    def _review_step_2_process_inbox(self, user_id: str) -> Dict[str, Any]:
        """Step 2: Process Inbox to Zero."""
        return {
            "response_type": "weekly_review_step_2",
            "step": "Process Inbox",
            "step_number": 2,
            "message": "📥 **Step 2: Process Inbox to Zero**\n\nFor each captured item:\n\n1. **What is it?** - Clarify what this item represents\n2. **Is it actionable?** - Does it require action?\n3. **If yes:** Create task, project, or delegate\n4. **If no:** File as reference, someday/maybe, or delete\n\nProcess each item until all inboxes are empty.\n\n*Type 'done' when all inboxes are at zero.*",
            "workflow": {
                "step": 2,
                "checklist": self.review_steps.get("process_inboxes", [])
            }
        }
    
    def _review_step_3_review_calendar(self, user_id: str) -> Dict[str, Any]:
        """Step 3: Review Calendar."""
        # Get calendar data if available
        calendar_insights = self._get_calendar_insights(user_id)
        
        return {
            "response_type": "weekly_review_step_3", 
            "step": "Review Calendar",
            "step_number": 3,
            "message": f"📅 **Step 3: Review Calendar**\n\n**Past 2 weeks:** Look for any missed commitments or follow-ups\n**Next 4 weeks:** Prepare for upcoming events\n\n{calendar_insights}\n\nHave you:\n✅ Captured any tasks from past meetings?\n✅ Prepared for upcoming commitments?\n✅ Blocked focus time for important work?\n\n*Type 'done' when calendar review is complete.*"
        }
    
    def _review_step_4_review_projects(self, user_id: str) -> Dict[str, Any]:
        """Step 4: Review Active Projects."""
        project_health = self._get_project_health_summary(user_id)
        
        return {
            "response_type": "weekly_review_step_4",
            "step": "Review Projects", 
            "step_number": 4,
            "message": f"📋 **Step 4: Review Active Projects**\n\n{project_health}\n\nFor each project, ensure:\n✅ Clear outcome defined\n✅ Next action identified\n✅ Project is still relevant\n✅ No stalled projects\n\n*Type 'done' when project review is complete.*"
        }
    
    def _review_step_5_review_next_actions(self, user_id: str) -> Dict[str, Any]:
        """Step 5: Review Next Action Lists."""
        action_analysis = self._get_next_actions_analysis(user_id)
        
        return {
            "response_type": "weekly_review_step_5",
            "step": "Review Next Actions",
            "step_number": 5, 
            "message": f"⚡ **Step 5: Review Next Action Lists**\n\n{action_analysis}\n\nReview by context:\n✅ @computer tasks\n✅ @phone calls\n✅ @office tasks\n✅ @home tasks\n✅ @errands\n\nMark completed tasks and update descriptions as needed.\n\n*Type 'done' when next actions are reviewed.*"
        }
    
    def _review_step_6_review_waiting_for(self, user_id: str) -> Dict[str, Any]:
        """Step 6: Review Waiting For List."""
        return {
            "response_type": "weekly_review_step_6",
            "step": "Review Waiting For",
            "step_number": 6,
            "message": "⏳ **Step 6: Review Waiting For List**\n\nCheck items you're waiting for:\n\n✅ Follow up on overdue items\n✅ Update status of pending items\n✅ Set reminders for future follow-ups\n✅ Remove completed waiting items\n\nAny items need follow-up action?\n\n*Type 'done' when waiting-for review is complete.*"
        }
    
    def _review_step_7_review_someday_maybe(self, user_id: str) -> Dict[str, Any]:
        """Step 7: Review Someday/Maybe List."""
        return {
            "response_type": "weekly_review_step_7",
            "step": "Review Someday/Maybe",
            "step_number": 7,
            "message": "💡 **Step 7: Review Someday/Maybe List**\n\nReview your someday/maybe items:\n\n✅ Move any to active projects?\n✅ Delete items no longer interesting?\n✅ Add new possibilities?\n✅ Update or clarify existing items?\n\nKeep this list fresh and inspiring!\n\n*Type 'done' when someday/maybe review is complete.*"
        }
    
    def _review_step_8_plan_ahead(self, user_id: str) -> Dict[str, Any]:
        """Step 8: Plan Ahead."""
        upcoming_insights = self._get_upcoming_week_insights(user_id)
        
        return {
            "response_type": "weekly_review_step_8",
            "step": "Plan Ahead",
            "step_number": 8,
            "message": f"🎯 **Step 8: Plan Ahead**\n\n{upcoming_insights}\n\nFor next week:\n✅ Key priorities identified\n✅ Focus time blocked\n✅ Energy and availability considered\n✅ Potential obstacles anticipated\n\n*Type 'done' to complete your weekly review.*"
        }
    
    def _complete_weekly_review(self, user_id: str) -> Dict[str, Any]:
        """Complete weekly review workflow."""
        review_data = self.get_context("review_data", {})
        
        # Calculate completion stats
        completed_at = datetime.now()
        started_at = datetime.fromisoformat(review_data.get("started_at", completed_at.isoformat()))
        duration = (completed_at - started_at).total_seconds() / 60  # minutes
        
        # Generate completion insights
        insights = self._generate_review_completion_insights(user_id, review_data)
        
        # Clear review state
        self.update_context({
            "review_state": "completed",
            "last_review_date": completed_at.isoformat(),
            "review_duration": duration
        })
        
        return {
            "response_type": "weekly_review_complete",
            "completion_time": completed_at.isoformat(),
            "duration_minutes": round(duration, 1),
            "insights": insights,
            "message": f"🎉 **Weekly Review Complete!** \n\nGreat job maintaining your trusted GTD system!\n\n⏱️ **Duration:** {round(duration, 1)} minutes\n📊 **Steps completed:** {len(review_data.get('steps_completed', []))}\n\n{insights}\n\n**Next Review:** Schedule for next {self.default_day} at {self.default_time}",
            "celebration": True,
            "next_review_reminder": True
        }
    
    # Analytics and Insights (BMAD-inspired data-driven approach)
    
    def _analyze_stale_tasks(self, user_id: str, threshold: str = "1week") -> Dict[str, Any]:
        """Analyze and identify stale tasks."""
        # Parse threshold
        threshold_days = self._parse_time_threshold(threshold)
        cutoff_date = datetime.now() - timedelta(days=threshold_days)
        
        # Mock stale task analysis (replace with real Todoist data)
        stale_tasks = self._get_stale_tasks(user_id, cutoff_date)
        
        if not stale_tasks:
            return {
                "response_type": "no_stale_tasks",
                "message": f"🌟 **Excellent!** No stale tasks found.\n\nAll your tasks have been active within the last {threshold}. Your GTD system is healthy!"
            }
        
        # Format stale tasks display
        stale_display = "\n".join([
            f"• **{task['title']}** (stale for {task['stale_days']} days)"
            for task in stale_tasks[:10]  # Limit display
        ])
        
        return {
            "response_type": "stale_tasks_found",
            "stale_count": len(stale_tasks),
            "threshold_days": threshold_days,
            "stale_tasks": stale_tasks,
            "message": f"🧹 **Found {len(stale_tasks)} stale tasks** (inactive > {threshold})\n\n{stale_display}\n\nWould you like to:\n1. **Review and update** these tasks\n2. **Delete** completed ones\n3. **Break down** complex ones\n4. **Reschedule** for later",
            "actions": [
                {"label": "🔄 Review & Update", "value": "review_stale"},
                {"label": "🗑️ Clean Up", "value": "cleanup_stale"},
                {"label": "📋 Break Down", "value": "breakdown_stale"}
            ]
        }
    
    def _generate_progress_report(self, user_id: str, period: str = "week") -> Dict[str, Any]:
        """Generate productivity analytics report."""
        # Get analytics data
        analytics = self._get_productivity_analytics(user_id, period)
        
        # Format report
        report_sections = []
        
        # Completion stats
        completed = analytics.get("tasks_completed", 0)
        created = analytics.get("tasks_created", 0)
        completion_rate = (completed / max(created, 1)) * 100
        
        report_sections.append(f"📈 **Productivity Report - {period.title()}**")
        report_sections.append(f"✅ **Tasks Completed:** {completed}")
        report_sections.append(f"📝 **Tasks Created:** {created}")
        report_sections.append(f"🎯 **Completion Rate:** {completion_rate:.1f}%")
        
        # Context distribution
        context_dist = analytics.get("context_distribution", {})
        if context_dist:
            report_sections.append("\n📊 **Work by Context:**")
            for context, count in context_dist.items():
                report_sections.append(f"   {context}: {count} tasks")
        
        # Project velocity
        project_stats = analytics.get("project_stats", {})
        if project_stats:
            report_sections.append(f"\n🚀 **Projects:** {project_stats.get('active', 0)} active, {project_stats.get('completed', 0)} completed")
        
        # Generate insights
        insights = self._generate_analytics_insights(analytics, period)
        if insights:
            report_sections.append(f"\n💡 **Insights:**\n{insights}")
        
        return {
            "response_type": "progress_report",
            "period": period,
            "analytics": analytics,
            "message": "\n".join(report_sections)
        }
    
    def _generate_insights(self, user_id: str, insight_type: str = "weekly") -> Dict[str, Any]:
        """Generate personalized productivity insights from real Todoist data."""
        if not self.todoist:
            return {
                "response_type": "productivity_insights", 
                "message": "📊 **Todoist connection required for real insights.** Please check your Todoist integration."
            }
        
        try:
            # Get real data from Todoist
            tasks = self.todoist.get_tasks()
            projects = self.todoist.get_projects()
            
            insights = []
            
            # Analyze task patterns
            if tasks:
                # Count tasks by labels/contexts
                contexts = {}
                time_estimates = {}
                overdue_count = 0
                
                for task in tasks:
                    # Count contexts (@phone, @computer, etc.)
                    task_content = task.get('content', '') if isinstance(task, dict) else str(task)
                    for word in task_content.split():
                        if word.startswith('@'):
                            contexts[word] = contexts.get(word, 0) + 1
                    
                    # Count time estimates
                    for label in task.get('labels', []):
                        if 'min' in label:
                            time_estimates[label] = time_estimates.get(label, 0) + 1
                    
                    # Check if overdue
                    if task.get('due') and task['due'].get('date'):
                        from datetime import datetime
                        try:
                            due_date = datetime.fromisoformat(task['due']['date'].replace('Z', '+00:00'))
                            if due_date < datetime.now():
                                overdue_count += 1
                        except:
                            pass
                
                # Generate real insights
                insights.append(f"📋 **Task Overview:** You have {len(tasks)} active tasks")
                
                if overdue_count > 0:
                    insights.append(f"⚠️ **Attention:** {overdue_count} overdue tasks need immediate attention")
                
                if contexts:
                    top_context = max(contexts, key=contexts.get)
                    insights.append(f"📍 **Context Focus:** Most tasks are in {top_context} ({contexts[top_context]} tasks)")
                
                if time_estimates:
                    insights.append(f"⏱️ **Time Distribution:** {dict(time_estimates)}")
                
                # Project insights
                if projects:
                    active_projects = [p for p in projects if not p.get('is_archived', False)]
                    insights.append(f"🎯 **Active Projects:** {len(active_projects)} projects in progress")
            else:
                insights.append("📭 **Clean Slate:** No active tasks - great job staying current!")
            
            # Generate recommendations based on real data
            recommendations = []
            if overdue_count > 3:
                recommendations.append("• Consider a quick overdue task cleanup session")
            if len(tasks) > 20:
                recommendations.append("• You might want to break down some larger tasks")
            if not contexts:
                recommendations.append("• Try adding GTD contexts (@computer, @phone, @errands) to your tasks")
            
            recommendations_text = "\n".join(recommendations) if recommendations else "• Keep up the great work with your GTD system!"
            
            insights_text = "\n".join(insights)
            
            return {
                "response_type": "productivity_insights",
                "insight_type": insight_type,
                "insights": insights,
                "message": f"🧠 **Real Productivity Insights**\n\n{insights_text}\n\n**Recommendations:**\n{recommendations_text}"
            }
            
        except Exception as e:
            logger.error(f"Error generating insights: {e}")
            return {
                "response_type": "productivity_insights",
                "message": f"🔧 **Error getting insights:** {str(e)}\n\nTry reconnecting your Todoist integration."
            }
    
    # Helper methods for data analysis
    
    def _get_stale_tasks(self, user_id: str, cutoff_date: datetime) -> List[Dict[str, Any]]:
        """Get tasks that haven't been updated recently."""
        # Mock implementation - replace with real Todoist API calls
        return [
            {"title": "Review Q3 budget analysis", "stale_days": 18, "context": "@computer"},
            {"title": "Call insurance company", "stale_days": 12, "context": "@phone"},
            {"title": "Organize home office", "stale_days": 25, "context": "@home"}
        ]
    
    def _get_productivity_analytics(self, user_id: str, period: str) -> Dict[str, Any]:
        """Get comprehensive productivity analytics."""
        # Mock implementation - replace with real analytics
        return {
            "tasks_completed": 23,
            "tasks_created": 28,
            "completion_rate": 0.82,
            "context_distribution": {
                "@computer": 15,
                "@phone": 4,
                "@office": 3,
                "@errands": 1
            },
            "project_stats": {
                "active": 5,
                "completed": 2,
                "stalled": 1
            },
            "average_completion_time": "2.3 days"
        }
    
    def _generate_analytics_insights(self, analytics: Dict[str, Any], period: str) -> str:
        """Generate insights from analytics data."""
        insights = []
        
        completion_rate = analytics.get("completion_rate", 0)
        if completion_rate > 0.8:
            insights.append("• Excellent completion rate! You're staying on top of your commitments.")
        elif completion_rate < 0.6:
            insights.append("• Consider breaking down tasks into smaller, more manageable actions.")
        
        return "\n".join(insights)
    
    def _generate_personalized_recommendations(self, analytics: Dict[str, Any]) -> str:
        """Generate personalized recommendations."""
        recommendations = [
            "• Schedule weekly reviews consistently to maintain system health",
            "• Focus on your most productive contexts for important work", 
            "• Review and update stale tasks weekly to keep momentum"
        ]
        
        return "\n".join(recommendations)
    
    def _parse_time_threshold(self, threshold: str) -> int:
        """Parse time threshold string to days."""
        threshold_map = {
            "1week": 7,
            "2weeks": 14,
            "1month": 30,
            "3days": 3,
            "1day": 1
        }
        return threshold_map.get(threshold, 7)
    
    def _get_calendar_insights(self, user_id: str) -> str:
        """Get calendar-based insights."""
        return "📅 **Calendar Insights:** 3 meetings this week, 2 deadlines approaching."
    
    def _get_project_health_summary(self, user_id: str) -> str:
        """Get project health summary."""
        return "📋 **Project Health:** 5 active projects, 1 needs attention (Website Redesign - no progress in 2 weeks)."
    
    def _get_next_actions_analysis(self, user_id: str) -> str:
        """Analyze next actions by context.""" 
        return "⚡ **Next Actions:** 12 @computer, 3 @phone, 2 @errands. Consider batching @computer tasks."
    
    def _get_upcoming_week_insights(self, user_id: str) -> str:
        """Get insights for upcoming week."""
        return "🎯 **Next Week:** Focus on Website Redesign project. You have 3 days with light calendar - perfect for deep work."
    
    def _generate_review_completion_insights(self, user_id: str, review_data: Dict[str, Any]) -> str:
        """Generate insights after review completion."""
        return "💡 **Review Insights:** System is healthy! Consider batching @computer tasks for better focus."