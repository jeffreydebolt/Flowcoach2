"""
Calendar service for FlowCoach.

This module provides a service for interacting with Google Calendar.
"""

import logging
import os
from datetime import datetime, timedelta, time
from typing import Dict, Any, List, Optional, Union

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

class CalendarService:
    """Service for interacting with Google Calendar API."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the Calendar service.
        
        Args:
            config: Calendar configuration
        """
        self.logger = logging.getLogger(__name__)
        self.config = config
        self.creds = None
        self._calendar_service = None
        
        # Google Calendar API scopes
        self.SCOPES = ['https://www.googleapis.com/auth/calendar']
        
        # Try to initialize the service
        self._initialize_service()
    
    def _initialize_service(self) -> None:
        """Initialize the Google Calendar service."""
        try:
            # Check for token file
            token_path = 'tokens/default_token.json'
            if os.path.exists(token_path):
                self.logger.info("Loading credentials from token file")
                try:
                    self.creds = Credentials.from_authorized_user_file(token_path, self.SCOPES)
                except Exception as e:
                    self.logger.error(f"Error loading credentials: {e}")
                    self.creds = None
            
            # If credentials are expired but have refresh token, refresh them
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.logger.info("Refreshing expired credentials")
                try:
                    self.creds.refresh(Request())
                    # Save refreshed credentials
                    with open(token_path, 'w') as token:
                        token.write(self.creds.to_json())
                except Exception as e:
                    self.logger.error(f"Error refreshing credentials: {e}")
                    self.creds = None
            
            # If no valid credentials, log warning
            if not self.creds or not self.creds.valid:
                self.logger.warning(
                    "No valid credentials found. Calendar functionality will be limited. "
                    "Run authenticate_calendar.py to set up Google Calendar access."
                )
                return
            
            # Build the service
            try:
                self._calendar_service = build('calendar', 'v3', credentials=self.creds)
                self.logger.info("Google Calendar service initialized successfully")
            except Exception as e:
                self.logger.error(f"Error building calendar service: {e}")
                self._calendar_service = None
                
        except Exception as e:
            self.logger.error(f"Error initializing Google Calendar service: {e}")
            self._calendar_service = None
    
    @property
    def calendar_service(self):
        """Get calendar service instance."""
        if not self._calendar_service:
            self.logger.error("Google Calendar service not initialized")
            raise ValueError("Google Calendar service not initialized")
        return self._calendar_service
    
    def get_events(
        self,
        user_id: str,
        start_date: Union[datetime, str],
        end_date: Union[datetime, str],
        calendar_id: str = 'primary'
    ) -> List[Dict[str, Any]]:
        """
        Get events from Google Calendar.
        
        Args:
            user_id: User ID (for future multi-user support)
            start_date: Start date/time
            end_date: End date/time
            calendar_id: Calendar ID
            
        Returns:
            List of processed calendar events
        """
        try:
            # Ensure we have a service
            if not self._calendar_service:
                self.logger.error("Calendar service not available")
                return []
            
            # Convert string dates to datetime if needed
            if isinstance(start_date, str):
                start_date = datetime.fromisoformat(start_date)
            if isinstance(end_date, str):
                end_date = datetime.fromisoformat(end_date)
            
            # Format dates for API
            start_date_str = start_date.isoformat()
            end_date_str = end_date.isoformat()
            
            # Call Google Calendar API
            events_result = self.calendar_service.events().list(
                calendarId=calendar_id,
                timeMin=start_date_str,
                timeMax=end_date_str,
                singleEvents=True,
                orderBy='startTime',
                maxResults=100
            ).execute()
            
            events = []
            items = events_result.get('items', [])
            self.logger.info(f"Retrieved {len(items)} events from Google Calendar")
            
            # Process each event
            for event in items:
                # Skip events marked as 'transparent' (free) availability
                if event.get('transparency') == 'transparent':
                    continue
                
                # Process event based on type (all-day or timed)
                if 'date' in event['start']:
                    processed_event = self._process_all_day_event(event)
                else:
                    processed_event = self._process_timed_event(event)
                
                events.append(processed_event)
            
            return events
            
        except Exception as e:
            self.logger.error(f"Error getting events: {e}")
            return []
    
    def _process_all_day_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process an all-day event.
        
        Args:
            event: Google Calendar event
            
        Returns:
            Processed event dictionary
        """
        # Parse the date strings
        start_date = datetime.fromisoformat(event['start']['date'])
        end_date = datetime.fromisoformat(event['end']['date'])
        
        # Google Calendar API returns the day after the end date for all-day events
        # So we need to subtract one day to get the actual end date
        end_date = end_date - timedelta(days=1)
        
        return {
            'id': event.get('id', ''),
            'summary': event.get('summary', 'No title'),
            'start_time': datetime.combine(start_date, time(0, 0)),
            'end_time': datetime.combine(end_date, time(23, 59, 59)),
            'duration_minutes': int(((end_date - start_date).days + 1) * 24 * 60),
            'is_all_day': True,
            'attendees': event.get('attendees', []),
            'description': event.get('description', '')
        }
    
    def _process_timed_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a timed event.
        
        Args:
            event: Google Calendar event
            
        Returns:
            Processed event dictionary
        """
        try:
            # Handle 'Z' UTC indicator by replacing with +00:00 for ISO format
            start_str = event['start']['dateTime'].replace('Z', '+00:00')
            end_str = event['end']['dateTime'].replace('Z', '+00:00')
            
            # Parse ISO format strings to datetime objects with timezone info
            start_time = datetime.fromisoformat(start_str)
            end_time = datetime.fromisoformat(end_str)
            
            return {
                'id': event.get('id', ''),
                'summary': event.get('summary', 'No title'),
                'start_time': start_time,
                'end_time': end_time,
                'duration_minutes': int((end_time - start_time).total_seconds() / 60),
                'is_all_day': False,
                'attendees': event.get('attendees', []),
                'description': event.get('description', '')
            }
        except Exception as e:
            self.logger.error(f"Error processing timed event: {e}")
            
            # Return a fallback event with minimal information
            return {
                'id': event.get('id', ''),
                'summary': event.get('summary', 'No title') + ' (Error processing time)',
                'start_time': datetime.now(),
                'end_time': datetime.now() + timedelta(minutes=30),
                'duration_minutes': 30,
                'is_all_day': False,
                'attendees': event.get('attendees', []),
                'description': event.get('description', '')
            }
    
    def create_event(
        self,
        user_id: str,
        summary: str,
        start_time: datetime,
        end_time: datetime,
        description: str = '',
        calendar_id: str = 'primary'
    ) -> Optional[Dict[str, Any]]:
        """
        Create a calendar event.
        
        Args:
            user_id: User ID (for future multi-user support)
            summary: Event summary/title
            start_time: Start time
            end_time: End time
            description: Event description
            calendar_id: Calendar ID
            
        Returns:
            Created event or None if creation failed
        """
        try:
            # Ensure we have a service
            if not self._calendar_service:
                self.logger.error("Calendar service not available")
                return None
            
            # Format times for API
            start_time_str = start_time.isoformat()
            end_time_str = end_time.isoformat()
            
            # Create event
            event = {
                'summary': summary,
                'description': description,
                'start': {
                    'dateTime': start_time_str,
                    'timeZone': 'UTC'  # Use user's timezone in a real implementation
                },
                'end': {
                    'dateTime': end_time_str,
                    'timeZone': 'UTC'  # Use user's timezone in a real implementation
                }
            }
            
            created_event = self.calendar_service.events().insert(
                calendarId=calendar_id,
                body=event
            ).execute()
            
            self.logger.info(f"Event created: {created_event.get('htmlLink')}")
            
            # Process the created event
            if 'date' in created_event['start']:
                return self._process_all_day_event(created_event)
            else:
                return self._process_timed_event(created_event)
            
        except Exception as e:
            self.logger.error(f"Error creating event: {e}")
            return None
    
    def find_focus_blocks(
        self,
        user_id: str,
        date: Optional[datetime] = None,
        work_start_hour: Optional[int] = None,
        work_end_hour: Optional[int] = None,
        min_block_minutes: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Find available focus blocks in calendar.
        
        Args:
            user_id: User ID
            date: Date to find focus blocks for (defaults to today)
            work_start_hour: Start of work day (defaults to config value)
            work_end_hour: End of work day (defaults to config value)
            min_block_minutes: Minimum duration in minutes (defaults to config value)
            
        Returns:
            List of focus blocks
        """
        try:
            # Use defaults from config if not provided
            if work_start_hour is None:
                work_start_hour = self.config["work_start_hour"]
            if work_end_hour is None:
                work_end_hour = self.config["work_end_hour"]
            if min_block_minutes is None:
                min_block_minutes = self.config["min_focus_block_minutes"]
            
            # Use today if date not provided
            if date is None:
                date = datetime.now().date()
            elif isinstance(date, datetime):
                date = date.date()
            
            # Set time boundaries for the day
            start_datetime = datetime.combine(date, time(0, 0, 0))
            end_datetime = datetime.combine(date, time(23, 59, 59))
            
            # Get events for the day
            events = self.get_events(user_id, start_datetime, end_datetime)
            
            # Calculate focus blocks
            focus_blocks = self._calculate_focus_blocks(
                events,
                work_start_hour,
                work_end_hour,
                min_block_minutes
            )
            
            return focus_blocks
            
        except Exception as e:
            self.logger.error(f"Error finding focus blocks: {e}")
            return []
    
    def _calculate_focus_blocks(
        self,
        events: List[Dict[str, Any]],
        work_start_hour: int,
        work_end_hour: int,
        min_block_minutes: int
    ) -> List[Dict[str, Any]]:
        """
        Calculate available focus blocks based on calendar events.
        
        Args:
            events: List of calendar events
            work_start_hour: Start of work day (e.g., 9 for 9 AM)
            work_end_hour: End of work day (e.g., 17 for 5 PM)
            min_block_minutes: Minimum duration in minutes to consider a block
            
        Returns:
            List of focus blocks with start and end times
        """
        # Get the date from the first event, or use today if no events
        if events:
            day = events[0]["start_time"].date()
        else:
            day = datetime.now().date()
        
        # Set work day boundaries
        work_start = datetime.combine(day, time(hour=work_start_hour))
        work_end = datetime.combine(day, time(hour=work_end_hour))
        
        # Initialize available time with full work day
        available_blocks = [{"start": work_start, "end": work_end}]
        
        # Sort events by start time
        sorted_events = sorted(events, key=lambda x: x["start_time"])
        
        # Remove event times from available blocks
        for event in sorted_events:
            event_start = max(event["start_time"], work_start)
            event_end = min(event["end_time"], work_end)
            
            # Skip events outside work hours
            if event_end <= work_start or event_start >= work_end:
                continue
            
            new_blocks = []
            for block in available_blocks:
                # Event is completely outside this block
                if event_end <= block["start"] or event_start >= block["end"]:
                    new_blocks.append(block)
                # Event splits block in two
                elif event_start > block["start"] and event_end < block["end"]:
                    new_blocks.append({"start": block["start"], "end": event_start})
                    new_blocks.append({"start": event_end, "end": block["end"]})
                # Event removes start of block
                elif event_start <= block["start"] and event_end > block["start"] and event_end < block["end"]:
                    new_blocks.append({"start": event_end, "end": block["end"]})
                # Event removes end of block
                elif event_start > block["start"] and event_start < block["end"] and event_end >= block["end"]:
                    new_blocks.append({"start": block["start"], "end": event_start})
                # Event completely covers block
                elif event_start <= block["start"] and event_end >= block["end"]:
                    pass  # Block is completely covered, don't add anything
            
            available_blocks = new_blocks
        
        # Filter blocks to find focus time (blocks >= min duration)
        focus_blocks = []
        for block in available_blocks:
            duration_minutes = int((block["end"] - block["start"]).total_seconds() / 60)
            
            if duration_minutes >= min_block_minutes:
                focus_blocks.append({
                    "start": block["start"],
                    "end": block["end"],
                    "duration_minutes": duration_minutes
                })
        
        return focus_blocks
    
    def update_event(
        self,
        event_id: str,
        user_id: str,
        summary: str = None,
        start_time: datetime = None,
        end_time: datetime = None,
        description: str = None,
        calendar_id: str = 'primary'
    ) -> Optional[Dict[str, Any]]:
        """
        Update an existing calendar event.
        
        Args:
            event_id: ID of event to update
            user_id: User ID (for future multi-user support)
            summary: New event summary/title
            start_time: New start time
            end_time: New end time
            description: New event description
            calendar_id: Calendar ID
            
        Returns:
            Updated event or None if update failed
        """
        try:
            if not self._calendar_service:
                self.logger.error("Calendar service not available")
                return None
            
            # Get the existing event
            try:
                existing_event = self.calendar_service.events().get(
                    calendarId=calendar_id,
                    eventId=event_id
                ).execute()
            except Exception as e:
                self.logger.error(f"Event not found: {e}")
                return None
            
            # Update only provided fields
            if summary is not None:
                existing_event['summary'] = summary
            if description is not None:
                existing_event['description'] = description
            if start_time is not None:
                existing_event['start'] = {
                    'dateTime': start_time.isoformat(),
                    'timeZone': 'UTC'
                }
            if end_time is not None:
                existing_event['end'] = {
                    'dateTime': end_time.isoformat(),
                    'timeZone': 'UTC'
                }
            
            # Update the event
            updated_event = self.calendar_service.events().update(
                calendarId=calendar_id,
                eventId=event_id,
                body=existing_event
            ).execute()
            
            self.logger.info(f"Event updated: {updated_event.get('htmlLink')}")
            
            # Process the updated event
            if 'date' in updated_event['start']:
                return self._process_all_day_event(updated_event)
            else:
                return self._process_timed_event(updated_event)
            
        except Exception as e:
            self.logger.error(f"Error updating event: {e}")
            return None
    
    def delete_event(
        self,
        event_id: str,
        user_id: str,
        calendar_id: str = 'primary'
    ) -> bool:
        """
        Delete a calendar event.
        
        Args:
            event_id: ID of event to delete
            user_id: User ID (for future multi-user support)
            calendar_id: Calendar ID
            
        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            if not self._calendar_service:
                self.logger.error("Calendar service not available")
                return False
            
            self.calendar_service.events().delete(
                calendarId=calendar_id,
                eventId=event_id
            ).execute()
            
            self.logger.info(f"Event deleted: {event_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error deleting event: {e}")
            return False
    
    def create_task_time_block(
        self,
        user_id: str,
        task_title: str,
        duration_minutes: int,
        preferred_time: datetime = None,
        description: str = None,
        context: str = None
    ) -> Optional[Dict[str, Any]]:
        """
        Create a time block for a specific task.
        
        Args:
            user_id: User ID
            task_title: Title of the task
            duration_minutes: How long the task should take
            preferred_time: Preferred start time (will find next available if None)
            description: Task description
            context: GTD context (@computer, @phone, etc.)
            
        Returns:
            Created calendar event or None if creation failed
        """
        try:
            # Find available time slot
            if preferred_time:
                start_time = preferred_time
            else:
                # Find next available focus block
                focus_blocks = self.find_focus_blocks(user_id, min_block_minutes=duration_minutes)
                if not focus_blocks:
                    self.logger.warning("No available focus blocks found")
                    return None
                
                start_time = focus_blocks[0]["start"]
            
            end_time = start_time + timedelta(minutes=duration_minutes)
            
            # Create event summary with context if provided
            summary = f"🎯 {task_title}"
            if context:
                summary += f" {context}"
            
            # Create event description
            event_description = description or ""
            if context:
                event_description += f"\n\nGTD Context: {context}"
            event_description += f"\nTime Estimate: {duration_minutes} minutes"
            event_description += "\n\nCreated by FlowCoach GTD Assistant"
            
            # Create the calendar event
            return self.create_event(
                user_id=user_id,
                summary=summary,
                start_time=start_time,
                end_time=end_time,
                description=event_description
            )
            
        except Exception as e:
            self.logger.error(f"Error creating task time block: {e}")
            return None
    
    def reschedule_event(
        self,
        event_id: str,
        user_id: str,
        new_start_time: datetime,
        duration_minutes: int = None,
        calendar_id: str = 'primary'
    ) -> Optional[Dict[str, Any]]:
        """
        Reschedule an event to a new time.
        
        Args:
            event_id: ID of event to reschedule
            user_id: User ID
            new_start_time: New start time
            duration_minutes: New duration (keeps original if None)
            calendar_id: Calendar ID
            
        Returns:
            Updated event or None if reschedule failed
        """
        try:
            if not self._calendar_service:
                self.logger.error("Calendar service not available")
                return None
            
            # Get existing event to preserve duration if needed
            existing_event = self.calendar_service.events().get(
                calendarId=calendar_id,
                eventId=event_id
            ).execute()
            
            # Calculate new end time
            if duration_minutes:
                new_end_time = new_start_time + timedelta(minutes=duration_minutes)
            else:
                # Keep original duration
                original_start = datetime.fromisoformat(existing_event['start']['dateTime'].replace('Z', '+00:00'))
                original_end = datetime.fromisoformat(existing_event['end']['dateTime'].replace('Z', '+00:00'))
                original_duration = original_end - original_start
                new_end_time = new_start_time + original_duration
            
            # Update the event
            return self.update_event(
                event_id=event_id,
                user_id=user_id,
                start_time=new_start_time,
                end_time=new_end_time,
                calendar_id=calendar_id
            )
            
        except Exception as e:
            self.logger.error(f"Error rescheduling event: {e}")
            return None
    
    def find_next_available_slot(
        self,
        user_id: str,
        duration_minutes: int,
        after_time: datetime = None,
        work_hours_only: bool = True
    ) -> Optional[datetime]:
        """
        Find the next available time slot for a given duration.
        
        Args:
            user_id: User ID
            duration_minutes: Required duration in minutes
            after_time: Start looking after this time (defaults to now)
            work_hours_only: Only look during work hours
            
        Returns:
            Start time of next available slot or None if none found
        """
        try:
            if after_time is None:
                after_time = datetime.now()
            
            # Look for slots in the next 7 days
            for days_ahead in range(7):
                search_date = (after_time + timedelta(days=days_ahead)).date()
                
                if work_hours_only:
                    focus_blocks = self.find_focus_blocks(
                        user_id=user_id,
                        date=search_date,
                        min_block_minutes=duration_minutes
                    )
                else:
                    # Look at entire day (simplified - could be enhanced)
                    focus_blocks = self.find_focus_blocks(
                        user_id=user_id,
                        date=search_date,
                        work_start_hour=0,
                        work_end_hour=23,
                        min_block_minutes=duration_minutes
                    )
                
                for block in focus_blocks:
                    # Make sure the slot is after our after_time
                    if block["start"] >= after_time:
                        return block["start"]
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error finding next available slot: {e}")
            return None
